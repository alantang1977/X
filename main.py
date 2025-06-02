import re
import asyncio
import logging
import json
import os
import threading
from collections import OrderedDict, defaultdict
from datetime import datetime
import difflib
import hashlib
import time
import subprocess

try:
    import aiohttp
except ImportError:
    print("错误: 缺少依赖库 'aiohttp'，请先安装 (pip install aiohttp)")
    import sys
    sys.exit(1)

try:
    import config
except ImportError:
    print("错误: 找不到配置模块 'config.py'")
    import sys
    sys.exit(1)

logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler("./live/function.log", "w", encoding="utf-8"), logging.StreamHandler()])

output_folder = "live"
os.makedirs(output_folder, exist_ok=True)

cache_folder = "./live/cache"
os.makedirs(cache_folder, exist_ok=True)
cache_file = os.path.join(cache_folder, "url_cache.json")
cache_valid_days = getattr(config, "cache_valid_days", 1)

# ------ 频道别名及LOGO/EPG补全 ------
CHANNEL_ALIASES = {
    "CCTV-1": ["CCTV1", "CCTV 1", "央视一台", "CCTV-1 综合", "CCTV 1综合", "CCTV-1HD"],
    "CCTV-2": ["CCTV2", "CCTV 2", "央视二台", "CCTV-2 财经", "CCTV 2财经"],
    "北京卫视": ["BTV", "北京台", "BTV-1"],
    "湖南卫视": ["HUNANTV", "湖南台", "MangoTV"],
}
CHANNEL_LOGOS = {
    "CCTV-1": "https://example.com/logos/cctv-1.png",
    "CCTV-2": "https://example.com/logos/cctv-2.png",
    "北京卫视": "https://example.com/logos/btv.png",
    "湖南卫视": "https://example.com/logos/hunantv.png",
}
CHANNEL_EPGS = {
    "CCTV-1": "https://example.com/epg/cctv-1.xml",
    "CCTV-2": "https://example.com/epg/cctv-2.xml",
    "北京卫视": "https://example.com/epg/btv.xml",
    "湖南卫视": "https://example.com/epg/hunantv.xml",
}

def get_standard_channel_name(name):
    name_norm = normalize_channel_name(name)
    for std, aliases in CHANNEL_ALIASES.items():
        if name_norm == normalize_channel_name(std):
            return std
        for a in aliases:
            if name_norm == normalize_channel_name(a):
                return std
    all_names = list(CHANNEL_ALIASES.keys()) + sum([v for v in CHANNEL_ALIASES.values()], [])
    match = difflib.get_close_matches(name_norm, [normalize_channel_name(n) for n in all_names], n=1, cutoff=0.8)
    if match:
        for std, aliases in CHANNEL_ALIASES.items():
            if normalize_channel_name(std) == match[0]:
                return std
            for a in aliases:
                if normalize_channel_name(a) == match[0]:
                    return std
    return name_norm

def get_logo(channel_name):
    std = get_standard_channel_name(channel_name)
    return CHANNEL_LOGOS.get(std, f"https://gitee.com/IIII-9306/PAV/raw/master/logos/{std}.png")

def get_epg(channel_name):
    std = get_standard_channel_name(channel_name)
    return CHANNEL_EPGS.get(std, "")

# -------- 缓存 --------
def load_cache():
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"加载缓存失败: {e}")
    return {"urls": {}, "timestamp": datetime.now().isoformat()}

def save_cache(cache):
    cache["timestamp"] = datetime.now().isoformat()
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"保存缓存失败: {e}")

def is_cache_valid(cache):
    if not cache:
        return False
    timestamp = datetime.fromisoformat(cache.get("timestamp", datetime.now().isoformat()))
    elapsed = (datetime.now() - timestamp).total_seconds() / (3600 * 24)
    return elapsed < cache_valid_days

def calculate_hash(content):
    return hashlib.md5(content.encode('utf-8')).hexdigest()

# -------- 模板解析，支持频道名/频道名+URL --------
def parse_template(template_file):
    template_channels = OrderedDict()
    current_category = None
    with open(template_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "#genre#" in line:
                current_category = line.split(",")[0].strip()
                template_channels[current_category] = []
            elif current_category:
                if "," in line:
                    channel_name, url = line.split(",", 1)
                    template_channels[current_category].append((channel_name.strip(), url.strip()))
                else:
                    template_channels[current_category].append((line, ""))
    return template_channels

def normalize_channel_name(name):
    name = name.upper()
    name = re.sub(r'[^\w\s-]', '', name)
    name = name.replace("高清", "").replace("HD", "")
    name = re.sub(r'综合|频道', '', name)
    name = re.sub(r'[\s_]', '', name)
    name = re.sub(r'CCTV[-\s]?(\d+)', r'CCTV-\1', name)
    name = re.sub(r'(-)+', '-', name)
    name = name.strip('-')
    return name

def is_valid_url(url):
    if not url or not url.startswith("http"):
        return False
    for black in config.url_blacklist:
        if black in url:
            return False
    return True

# -------- 网络采集与解析 --------
async def fetch_channels(session, url, cache):
    channels = OrderedDict()
    unique_urls = set()
    cache_hit = False
    url_hash = calculate_hash(url)
    if url_hash in cache["urls"]:
        cached_entry = cache["urls"][url_hash]
        timestamp = cached_entry.get("timestamp", datetime.now().isoformat())
        elapsed = (datetime.now() - datetime.fromisoformat(timestamp)).total_seconds() / (3600 * 24)
        if elapsed < cache_valid_days:
            logging.info(f"从缓存加载: {url}")
            channels = OrderedDict(cached_entry["channels"])
            unique_urls = set(cached_entry["unique_urls"])
            cache_hit = True

    if not cache_hit:
        try:
            async with session.get(url) as response:
                response.raise_for_status()
                content = await response.text()
                lines = content.split("\n")
                is_m3u = any(line.startswith("#EXTINF") for line in lines[:15])
                if is_m3u:
                    channels.update(parse_m3u_lines(lines, unique_urls))
                else:
                    channels.update(parse_txt_lines(lines, unique_urls))
                if channels:
                    cache["urls"][url_hash] = {
                        "url": url,
                        "channels": dict(channels),
                        "unique_urls": list(unique_urls),
                        "timestamp": datetime.now().isoformat(),
                        "content_hash": calculate_hash(content)
                    }
                    save_cache(cache)
        except Exception as e:
            logging.error(f"url: {url} 失败❌, Error: {e}")
    return channels

def parse_m3u_lines(lines, unique_urls):
    channels = OrderedDict()
    current_category = None
    channel_name = None
    for line in lines:
        line = line.strip()
        if line.startswith("#EXTINF"):
            match = re.search(r'group-title="(.*?)",(.*)', line)
            if match:
                current_category = match.group(1).strip()
                channel_name = match.group(2).strip()
                if current_category not in channels:
                    channels[current_category] = []
        elif line and not line.startswith("#"):
            channel_url = line.strip()
            if is_valid_url(channel_url) and channel_url not in unique_urls:
                unique_urls.add(channel_url)
                if current_category and channel_name:
                    channels[current_category].append((channel_name, channel_url))
    return channels

def parse_txt_lines(lines, unique_urls):
    channels = OrderedDict()
    current_category = None
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "#genre#" in line:
            current_category = line.split(",")[0].strip()
            channels[current_category] = []
        elif current_category:
            if "," in line:
                channel_name, url = line.split(",", 1)
                channel_name = channel_name.strip()
                url = url.strip()
                if is_valid_url(url):
                    if url not in unique_urls:
                        unique_urls.add(url)
                        channels[current_category].append((channel_name, url))
                else:
                    channels[current_category].append((channel_name, ""))
            else:
                channels[current_category].append((line, ""))
    return channels

def merge_channels(target, source):
    for category, channel_list in source.items():
        if category in target:
            target[category].extend(channel_list)
        else:
            target[category] = channel_list

def deduplicate_and_alias_channels(channels_dict):
    global_channel_map = {}
    for category in list(channels_dict.keys()):
        for channel_name in list(channels_dict[category].keys()):
            std_name = get_standard_channel_name(channel_name)
            key = (category, std_name)
            if key not in global_channel_map:
                global_channel_map[key] = set(channels_dict[category][channel_name])
            else:
                global_channel_map[key].update(channels_dict[category][channel_name])
            if channel_name != std_name:
                del channels_dict[category][channel_name]
    for category in channels_dict:
        channels_dict[category] = {}
    for (cat, std_name), urls in global_channel_map.items():
        channels_dict[cat][std_name] = list(urls)

async def test_url_speed(session, url, timeout=2):
    try:
        start = time.perf_counter()
        async with session.get(url, timeout=timeout) as resp:
            await resp.content.read(1024)
        elapsed = time.perf_counter() - start
        return url, elapsed
    except Exception:
        return url, float('inf')

async def speed_test_for_channel_urls(url_list, max_concurrent=10, timeout=2, repeat=1):
    results = {}
    sem = asyncio.Semaphore(max_concurrent)
    async with aiohttp.ClientSession() as session:
        async def sem_test(url):
            times = []
            for _ in range(repeat):
                async with sem:
                    _, t = await test_url_speed(session, url, timeout)
                    times.append(t)
            return url, min(times)
        tasks = [sem_test(url) for url in url_list]
        for res in await asyncio.gather(*tasks):
            results[res[0]] = res[1]
    return results

def filter_and_sort_urls_by_speed(urls_speed, max_keep=10, speed_threshold=3.0):
    filtered = [url for url, t in sorted(urls_speed.items(), key=lambda x: x[1]) if t < speed_threshold]
    return filtered[:max_keep]

def extract_all_channel_urls(channels_dict):
    channel_urls = defaultdict(list)
    for category in channels_dict:
        for channel_name in channels_dict[category]:
            for url in channels_dict[category][channel_name]:
                channel_urls[(category, channel_name)].append(url)
    return channel_urls

def add_url_suffix(url, index, total_urls, ip_version):
    suffix = f"${ip_version}" if total_urls == 1 else f"${ip_version}•线路{index}"
    base_url = url.split('$', 1)[0] if '$' in url else url
    return f"{base_url}{suffix}"

def write_to_files(f_m3u, f_txt, category, channel_name, index, new_url, epg_url, health):
    logo_url = get_logo(channel_name)
    extinf = f"#EXTINF:-1 tvg-id=\"{index}\" tvg-name=\"{channel_name}\" tvg-logo=\"{logo_url}\" group-title=\"{category}\""
    if epg_url:
        extinf += f" epg-url=\"{epg_url}\""
    extinf += f" health=\"{health}\""
    f_m3u.write(f"{extinf},{channel_name}\n")
    f_m3u.write(new_url + "\n")
    f_txt.write(f"{channel_name},{new_url},{health}\n")

def is_ipv6(url):
    return re.match(r'^http:\/\/\[[0-9a-fA-F:]+\]', url) is not None

def optimize_and_output_files(channels, health_dict, rtmp_map=None):
    written_urls_ipv4 = set()
    written_urls_ipv6 = set()
    ipv4_m3u_path = os.path.join(output_folder, "live_ipv4.m3u")
    ipv4_txt_path = os.path.join(output_folder, "live_ipv4.txt")
    ipv6_m3u_path = os.path.join(output_folder, "live_ipv6.m3u")
    ipv6_txt_path = os.path.join(output_folder, "live_ipv6.txt")

    with open(ipv4_m3u_path, "w", encoding="utf-8") as f_m3u_ipv4, \
         open(ipv4_txt_path, "w", encoding="utf-8") as f_txt_ipv4, \
         open(ipv6_m3u_path, "w", encoding="utf-8") as f_m3u_ipv6, \
         open(ipv6_txt_path, "w", encoding="utf-8") as f_txt_ipv6:

        for category, channel_dict in channels.items():
            f_txt_ipv4.write(f"{category},#genre#\n")
            f_txt_ipv6.write(f"{category},#genre#\n")
            for channel_name, url_list in channel_dict.items():
                epg_url = get_epg(channel_name)
                # 优先写入本地推流（RTMP/HLS）地址
                if rtmp_map and (category, channel_name) in rtmp_map:
                    local_urls = rtmp_map[(category, channel_name)]
                    for local_url in local_urls:
                        health = "local"
                        new_url = local_url
                        write_to_files(f_m3u_ipv4, f_txt_ipv4, category, channel_name, 0, new_url, epg_url, health)
                ipv4_urls = [u for u in url_list if not is_ipv6(u)]
                ipv6_urls = [u for u in url_list if is_ipv6(u)]
                total_urls_ipv4 = len(ipv4_urls)
                total_urls_ipv6 = len(ipv6_urls)
                for index, url in enumerate(ipv4_urls, start=1):
                    if url not in written_urls_ipv4 and is_valid_url(url):
                        health = health_dict.get(url, "fail" if health_dict.get(url, float('inf')) == float('inf') else "ok")
                        new_url = add_url_suffix(url, index, total_urls_ipv4, "IPV4")
                        write_to_files(f_m3u_ipv4, f_txt_ipv4, category, channel_name, index, new_url, epg_url, health)
                        written_urls_ipv4.add(url)
                for index, url in enumerate(ipv6_urls, start=1):
                    if url not in written_urls_ipv6 and is_valid_url(url):
                        health = health_dict.get(url, "fail" if health_dict.get(url, float('inf')) == float('inf') else "ok")
                        new_url = add_url_suffix(url, index, total_urls_ipv6, "IPV6")
                        write_to_files(f_m3u_ipv6, f_txt_ipv6, category, channel_name, index, new_url, epg_url, health)
                        written_urls_ipv6.add(url)
            f_txt_ipv4.write("\n")
            f_txt_ipv6.write("\n")

# --------- RTMP 推流管理 ---------
def push_stream_ffmpeg(src_url, out_url, hls_dir=None):
    # 死循环守护推流
    args = [
        'ffmpeg', '-re', '-i', src_url, '-c', 'copy', '-f', 'flv', out_url
    ]
    if hls_dir:  # 可选生成HLS
        hls_path = os.path.join(hls_dir, out_url.split("/")[-1] + ".m3u8")
        args += ['-c', 'copy', '-f', 'hls', '-hls_time', '6', '-hls_list_size', '5', hls_path]
    while True:
        print(f"推流: {src_url} -> {out_url}")
        p = subprocess.Popen(args)
        p.wait()
        print("推流中断，10秒后重启...")
        time.sleep(10)

def start_rtmp_push(selected_channels, rtmp_server, hls_dir=None):
    rtmp_map = {}
    threads = []
    for (category, channel_name), src_url in selected_channels.items():
        if not is_valid_url(src_url):
            continue
        safe_name = re.sub(r"[^\w]", "", channel_name)
        out_url = f"{rtmp_server}/{safe_name}"
        # 可选 HLS 地址
        hls_url = None
        if hls_dir:
            os.makedirs(hls_dir, exist_ok=True)
            hls_url = f"{getattr(config, 'hls_url_prefix', 'http://localhost/hls')}/{safe_name}.m3u8"
            rtmp_map[(category, channel_name)] = [out_url, hls_url]
        else:
            rtmp_map[(category, channel_name)] = [out_url]
        t = threading.Thread(target=push_stream_ffmpeg, args=(src_url, out_url, hls_dir))
        t.daemon = True
        t.start()
        threads.append(t)
        time.sleep(2)
    return rtmp_map, threads

# --------- 主流程 ---------
async def main(template_file):
    template_channels = parse_template(template_file)
    source_urls = getattr(config, "source_urls", [])
    cache = load_cache()

    all_channels = OrderedDict()
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_channels(session, url, cache) for url in source_urls]
        fetched_channels_list = await asyncio.gather(*tasks)
    for fetched_channels in fetched_channels_list:
        merge_channels(all_channels, fetched_channels)

    merged_channels = OrderedDict()
    for category, channel_list in all_channels.items():
        if category not in merged_channels:
            merged_channels[category] = OrderedDict()
        for channel_name, url in channel_list:
            merged_channels[category].setdefault(channel_name, []).append(url)
    deduplicate_and_alias_channels(merged_channels)

    # 把模板文件中的频道名+URL也并入
    for category, channels in template_channels.items():
        if category not in merged_channels:
            merged_channels[category] = OrderedDict()
        for channel_name, url in channels:
            if url and is_valid_url(url):
                merged_channels[category].setdefault(channel_name, []).append(url)
            else:
                merged_channels[category].setdefault(channel_name, [])

    # 并发测速，筛选最快有效线路
    channel_urls = extract_all_channel_urls(merged_channels)
    all_urls = list({url for urls in channel_urls.values() for url in urls if is_valid_url(url)})
    print("开始并发测速，请稍候……")
    max_concurrent = getattr(config, "max_concurrent_speed_tests", 10)
    speed_test_timeout = getattr(config, "speed_test_timeout", 3)
    speed_test_repeat = getattr(config, "speed_test_repeat", 2)
    max_lines_per_channel = getattr(config, "max_lines_per_channel", 10)
    urls_speed = await speed_test_for_channel_urls(
        all_urls,
        max_concurrent=max_concurrent,
        timeout=speed_test_timeout,
        repeat=speed_test_repeat
    )
    print("测速完成，正在筛选有效线路并写入文件……")
    health_dict = {}
    for url, t in urls_speed.items():
        health_dict[url] = t if t < speed_test_timeout else float('inf')
    for key, urls in channel_urls.items():
        filtered = filter_and_sort_urls_by_speed(
            {u: urls_speed.get(u, float('inf')) for u in urls},
            max_keep=max_lines_per_channel,
            speed_threshold=speed_test_timeout
        )
        category, channel_name = key
        merged_channels[category][channel_name] = filtered

    # ------- RTMP 推流（可选） -------
    rtmp_map = None
    rtmp_threads = []
    if getattr(config, "enable_rtmp_push", False):
        # 每频道取测速最快的线路推流
        selected_channels = {}
        for (category, channel_name), urls in channel_urls.items():
            best_urls = filter_and_sort_urls_by_speed(
                {u: urls_speed.get(u, float('inf')) for u in urls},
                max_keep=1,
                speed_threshold=speed_test_timeout
            )
            if best_urls:
                selected_channels[(category, channel_name)] = best_urls[0]
        hls_dir = getattr(config, "hls_output_dir", None) if hasattr(config, "hls_output_dir") else None
        rtmp_server = getattr(config, "rtmp_server_url", "rtmp://localhost/live")
        print("启动推流到本地 RTMP...")
        rtmp_map, rtmp_threads = start_rtmp_push(selected_channels, rtmp_server, hls_dir=hls_dir)
        print("推流线程已启动。")

    optimize_and_output_files(merged_channels, health_dict, rtmp_map=rtmp_map)
    print("操作完成！结果已保存到live文件夹。")
    # 保持推流线程（如启用）
    if rtmp_threads:
        while True:
            time.sleep(60)

if __name__ == "__main__":
    template_file = "demo.txt"
    try:
        if not os.path.exists(template_file):
            print(f"错误: 找不到模板文件 '{template_file}'。")
            print("请确保项目目录下有 demo.txt 文件。")
            import sys
            sys.exit(1)
        asyncio.run(main(template_file))
    except Exception as e:
        print(f"执行过程中发生错误: {e}")
        logging.error(f"程序运行失败: {e}")
