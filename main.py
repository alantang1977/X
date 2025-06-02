import re
import asyncio
import logging
import json
import os
from collections import OrderedDict, defaultdict
from datetime import datetime, timedelta
import difflib
import hashlib
import time

try:
    import aiohttp
except ImportError:
    print("错误: 缺少必要的依赖库 'aiohttp'。")
    print("请使用以下命令安装:")
    print("pip install aiohttp")
    import sys
    sys.exit(1)

try:
    import config
    required_attrs = ['source_urls', 'epg_urls', 'announcements', 'url_blacklist', 'ip_version_priority']
    for attr in required_attrs:
        if not hasattr(config, attr):
            raise AttributeError(f"配置文件缺少必要的属性: {attr}")
except ImportError:
    print("错误: 找不到配置模块 'config.py'。")
    import sys
    sys.exit(1)
except AttributeError as e:
    print(f"配置文件错误: {e}")
    import sys
    sys.exit(1)

logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler("./live/function.log", "w", encoding="utf-8"), logging.StreamHandler()])

output_folder = "live"
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

cache_folder = "./live/cache"
cache_file = os.path.join(cache_folder, "url_cache.json")
cache_valid_days = 7

if not os.path.exists(cache_folder):
    os.makedirs(cache_folder)

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
    return (datetime.now() - timestamp).days < cache_valid_days

def calculate_hash(content):
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def parse_template(template_file):
    template_channels = OrderedDict()
    current_category = None
    with open(template_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                if "#genre#" in line:
                    current_category = line.split(",")[0].strip()
                    template_channels[current_category] = []
                elif current_category:
                    channel_name = line.split(",")[0].strip()
                    template_channels[current_category].append(channel_name)
    return template_channels

def clean_channel_name(channel_name):
    cleaned_name = re.sub(r'[$\u300c\u300d-]', '', channel_name)
    cleaned_name = re.sub(r'\s+', '', cleaned_name)
    cleaned_name = re.sub(r'(\D*)(\d+)', lambda m: m.group(1) + str(int(m.group(2))), cleaned_name)
    return cleaned_name.upper()

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
    return bool(re.match(r'^https?://', url))

async def fetch_channels(session, url, cache):
    channels = OrderedDict()
    unique_urls = set()
    cache_hit = False
    url_hash = calculate_hash(url)
    if url_hash in cache["urls"]:
        cached_entry = cache["urls"][url_hash]
        if datetime.now() - datetime.fromisoformat(cached_entry["timestamp"]) <= timedelta(days=cache_valid_days):
            logging.info(f"从缓存加载: {url}")
            channels = OrderedDict(cached_entry["channels"])
            unique_urls = set(cached_entry["unique_urls"])
            cache_hit = True

    if not cache_hit:
        try:
            async with session.get(url) as response:
                response.raise_for_status()
                content = await response.text()
                response.encoding = 'utf-8'
                lines = content.split("\n")
                current_category = None
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
                if channel_name and channel_name.startswith("CCTV"):
                    channel_name = clean_channel_name(channel_name)
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
        if "#genre#" in line:
            current_category = line.split(",")[0].strip()
            channels[current_category] = []
        elif current_category:
            match = re.match(r"^(.*?),(.*?)$", line)
            if match:
                channel_name = match.group(1).strip()
                if channel_name and channel_name.startswith("CCTV"):
                    channel_name = clean_channel_name(channel_name)
                channel_urls = match.group(2).strip().split('#')
                for channel_url in channel_urls:
                    channel_url = channel_url.strip()
                    if is_valid_url(channel_url) and channel_url not in unique_urls:
                        unique_urls.add(channel_url)
                        channels[current_category].append((channel_name, channel_url))
            elif line:
                channels[current_category].append((line, ''))
    return channels

def merge_channels(target, source):
    for category, channel_list in source.items():
        if category in target:
            target[category].extend(channel_list)
        else:
            target[category] = channel_list

def deduplicate_channel_urls(channels_dict):
    for category in channels_dict:
        for channel_name in channels_dict[category]:
            seen = set()
            unique_urls = []
            for url in channels_dict[category][channel_name]:
                if url not in seen:
                    unique_urls.append(url)
                    seen.add(url)
            channels_dict[category][channel_name] = unique_urls

def deduplicate_global_channels(channels_dict):
    global_channel_map = {}
    for category in list(channels_dict.keys()):
        for channel_name in list(channels_dict[category].keys()):
            key = normalize_channel_name(channel_name)
            if key not in global_channel_map:
                global_channel_map[key] = {
                    "category": category,
                    "channel_name": channel_name,
                    "urls": set(channels_dict[category][channel_name])
                }
            else:
                global_channel_map[key]["urls"].update(channels_dict[category][channel_name])
                del channels_dict[category][channel_name]
    for category in channels_dict:
        channels_dict[category] = {}
    for info in global_channel_map.values():
        cat = info["category"]
        name = info["channel_name"]
        if cat not in channels_dict:
            channels_dict[cat] = {}
        channels_dict[cat][name] = list(info["urls"])

#######################
# 并发测速功能相关代码 #
#######################
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
            # 多次测速取最小值
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

def filter_and_sort_urls_by_speed(urls_speed, max_keep=2, speed_threshold=3.0):
    # 只保留测速快且可用的线路，速度单位秒
    filtered = [url for url, t in sorted(urls_speed.items(), key=lambda x: x[1]) if t < speed_threshold]
    return filtered[:max_keep]

def extract_all_channel_urls(channels_dict):
    # 返回: { (category, channel_name): [url1, url2, ...] }
    channel_urls = defaultdict(list)
    for category in channels_dict:
        for channel_name in channels_dict[category]:
            for url in channels_dict[category][channel_name]:
                channel_urls[(category, channel_name)].append(url)
    return channel_urls

############################
# 主流程与输出文件生成部分  #
############################

def add_url_suffix(url, index, total_urls, ip_version):
    suffix = f"${ip_version}" if total_urls == 1 else f"${ip_version}•线路{index}"
    base_url = url.split('$', 1)[0] if '$' in url else url
    return f"{base_url}{suffix}"

def write_to_files(f_m3u, f_txt, category, channel_name, index, new_url):
    logo_url = f"https://gitee.com/IIII-9306/PAV/raw/master/logos/{channel_name}.png"
    f_m3u.write(f"#EXTINF:-1 tvg-id=\"{index}\" tvg-name=\"{channel_name}\" tvg-logo=\"{logo_url}\" group-title=\"{category}\",{channel_name}\n")
    f_m3u.write(new_url + "\n")
    f_txt.write(f"{channel_name},{new_url}\n")

def is_ipv6(url):
    return re.match(r'^http:\/\/\[[0-9a-fA-F:]+\]', url) is not None

def optimize_and_output_files(channels, template_channels, cache):
    written_urls_ipv4 = set()
    written_urls_ipv6 = set()
    url_changes = {"added": [], "removed": [], "modified": []}
    if is_cache_valid(cache):
        previous_urls = {}
        for url_hash, entry in cache["urls"].items():
            for category, channel_list in entry["channels"].items():
                for channel_name, url in channel_list:
                    previous_urls[url] = (category, channel_name)
        current_urls = {}
        for category, channel_dict in channels.items():
            for channel_name, urls in channel_dict.items():
                for url in urls:
                    current_urls[url] = (category, channel_name)
        for url, (category, channel_name) in current_urls.items():
            if url not in previous_urls:
                url_changes["added"].append((category, channel_name, url))
        for url, (category, channel_name) in previous_urls.items():
            if url not in current_urls:
                url_changes["removed"].append((category, channel_name, url))

    current_date = datetime.now().strftime("%Y-%m-%d")
    for group in config.announcements:
        for announcement in group['entries']:
            if announcement['name'] is None:
                announcement['name'] = current_date

    ipv4_m3u_path = os.path.join(output_folder, "live_ipv4.m3u")
    ipv4_txt_path = os.path.join(output_folder, "live_ipv4.txt")
    ipv6_m3u_path = os.path.join(output_folder, "live_ipv6.m3u")
    ipv6_txt_path = os.path.join(output_folder, "live_ipv6.txt")

    with open(ipv4_m3u_path, "w", encoding="utf-8") as f_m3u_ipv4, \
         open(ipv4_txt_path, "w", encoding="utf-8") as f_txt_ipv4, \
         open(ipv6_m3u_path, "w", encoding="utf-8") as f_m3u_ipv6, \
         open(ipv6_txt_path, "w", encoding="utf-8") as f_txt_ipv6:

        f_m3u_ipv4.write(f"""#EXTM3U x-tvg-url={",".join(f'"{epg_url}"' for epg_url in config.epg_urls)}\n""")
        f_m3u_ipv6.write(f"""#EXTM3U x-tvg-url={",".join(f'"{epg_url}"' for epg_url in config.epg_urls)}\n""")

        for group in config.announcements:
            f_txt_ipv4.write(f"{group['channel']},#genre#\n")
            f_txt_ipv6.write(f"{group['channel']},#genre#\n")
            for announcement in group['entries']:
                url = announcement['url']
                if is_ipv6(url):
                    if url not in written_urls_ipv6 and is_valid_url(url):
                        written_urls_ipv6.add(url)
                        f_m3u_ipv6.write(f"""#EXTINF:-1 tvg-id="1" tvg-name="{announcement['name']}" tvg-logo="{announcement['logo']}" group-title="{group['channel']}",{announcement['name']}\n""")
                        f_m3u_ipv6.write(f"{url}\n")
                        f_txt_ipv6.write(f"{announcement['name']},{url}\n")
                else:
                    if url not in written_urls_ipv4 and is_valid_url(url):
                        written_urls_ipv4.add(url)
                        f_m3u_ipv4.write(f"""#EXTINF:-1 tvg-id="1" tvg-name="{announcement['name']}" tvg-logo="{announcement['logo']}" group-title="{group['channel']}",{announcement['name']}\n""")
                        f_m3u_ipv4.write(f"{url}\n")
                        f_txt_ipv4.write(f"{announcement['name']},{url}\n")

        for category, channel_dict in channels.items():
            f_txt_ipv4.write(f"{category},#genre#\n")
            f_txt_ipv6.write(f"{category},#genre#\n")
            for channel_name, url_list in channel_dict.items():
                # 只保留测速最快的N条线路
                ipv4_urls = [u for u in url_list if not is_ipv6(u)]
                ipv6_urls = [u for u in url_list if is_ipv6(u)]
                total_urls_ipv4 = len(ipv4_urls)
                total_urls_ipv6 = len(ipv6_urls)
                for index, url in enumerate(ipv4_urls, start=1):
                    if url not in written_urls_ipv4 and is_valid_url(url):
                        new_url = add_url_suffix(url, index, total_urls_ipv4, "IPV4")
                        write_to_files(f_m3u_ipv4, f_txt_ipv4, category, channel_name, index, new_url)
                        written_urls_ipv4.add(url)
                for index, url in enumerate(ipv6_urls, start=1):
                    if url not in written_urls_ipv6 and is_valid_url(url):
                        new_url = add_url_suffix(url, index, total_urls_ipv6, "IPV6")
                        write_to_files(f_m3u_ipv6, f_txt_ipv6, category, channel_name, index, new_url)
                        written_urls_ipv6.add(url)
            f_txt_ipv4.write("\n")
            f_txt_ipv6.write("\n")

    if url_changes["added"] or url_changes["removed"] or url_changes["modified"]:
        with open(os.path.join(output_folder, "url_changes.log"), "a", encoding="utf-8") as f:
            f.write(f"\n=== 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
            if url_changes["added"]:
                f.write("\n新增URL:\n")
                for category, channel_name, url in url_changes["added"]:
                    f.write(f"- {category} - {channel_name}: {url}\n")
            if url_changes["removed"]:
                f.write("\n移除URL:\n")
                for category, channel_name, url in url_changes["removed"]:
                    f.write(f"- {category} - {channel_name}: {url}\n")
            if url_changes["modified"]:
                f.write("\n修改URL:\n")
                for category, channel_name, old_url, new_url in url_changes["modified"]:
                    f.write(f"- {category} - {channel_name}: {old_url} → {new_url}\n")

#######################
# 主入口
#######################

async def main(template_file):
    # 解析模板和源
    template_channels = parse_template(template_file)
    source_urls = config.source_urls
    cache = load_cache()

    all_channels = OrderedDict()
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_channels(session, url, cache) for url in source_urls]
        fetched_channels_list = await asyncio.gather(*tasks)
    for fetched_channels in fetched_channels_list:
        merge_channels(all_channels, fetched_channels)

    # 转化为 {分组: {频道名: [url, ...]}}
    merged_channels = OrderedDict()
    for category, channel_list in all_channels.items():
        if category not in merged_channels:
            merged_channels[category] = OrderedDict()
        for channel_name, url in channel_list:
            merged_channels[category].setdefault(channel_name, []).append(url)

    # 去重、全局频道名归一
    deduplicate_channel_urls(merged_channels)
    deduplicate_global_channels(merged_channels)
    # 并发测速，筛选最快有效线路
    channel_urls = extract_all_channel_urls(merged_channels)
    all_urls = list({url for urls in channel_urls.values() for url in urls})
    print("开始并发测速，请稍候……")
    urls_speed = await speed_test_for_channel_urls(all_urls, max_concurrent=20, timeout=2, repeat=2)
    print("测速完成，正在筛选有效线路并写入文件……")
    # 保留每频道最快2条、速度小于3秒的线路
    for key, urls in channel_urls.items():
        fast_urls = filter_and_sort_urls_by_speed({u: urls_speed[u] for u in urls if u in urls_speed}, max_keep=2, speed_threshold=3.0)
        category, channel_name = key
        merged_channels[category][channel_name] = fast_urls

    optimize_and_output_files(merged_channels, template_channels, cache)
    print("操作完成！结果已保存到live文件夹。")

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
