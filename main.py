import re
import asyncio
import logging
import json
import os
from collections import OrderedDict
from datetime import datetime, timedelta
import difflib
import hashlib
import time
import sys
import traceback

# 检查 aiohttp 是否安装
try:
    import aiohttp
except ImportError:
    print("缺少 aiohttp，请先 pip install aiohttp")
    sys.exit(1)

# 检查 config 是否存在
try:
    import config
    for attr in ['source_urls', 'epg_urls', 'announcements', 'url_blacklist', 'ip_version_priority']:
        if not hasattr(config, attr):
            raise AttributeError(f"配置文件缺少: {attr}")
except ImportError:
    print("缺少 config.py，请参考示例自行创建。")
    sys.exit(1)
except AttributeError as e:
    print(f"配置文件错误: {e}")
    sys.exit(1)

# 日志和目录
output_folder = "live"
cache_folder = os.path.join(output_folder, "cache")
cache_file = os.path.join(cache_folder, "url_cache.json")
cache_valid_days = 7
os.makedirs(output_folder, exist_ok=True)
os.makedirs(cache_folder, exist_ok=True)

# 日志配置（调整：把常见异常降为WARNING，简化栈输出）
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(output_folder, "function.log"), "w", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

def load_cache():
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"加载缓存失败: {repr(e)}")
    return {"urls": {}, "timestamp": datetime.now().isoformat()}

def save_cache(cache):
    cache["timestamp"] = datetime.now().isoformat()
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"保存缓存失败: {repr(e)}")

def is_cache_valid(cache):
    if not cache:
        return False
    try:
        timestamp = datetime.fromisoformat(cache.get("timestamp", datetime.now().isoformat()))
        return (datetime.now() - timestamp).days < cache_valid_days
    except Exception as e:
        logging.error(f"检测缓存有效性失败: {repr(e)}")
        return False

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
    cleaned_name = re.sub(r'[$「」-]', '', channel_name)
    cleaned_name = re.sub(r'\s+', '', cleaned_name)
    cleaned_name = re.sub(r'(\D*)(\d+)', lambda m: m.group(1) + str(int(m.group(2))), cleaned_name)
    return cleaned_name.upper()

def is_valid_url(url):
    return bool(re.match(r'^https?://', url))

def is_ipv6(url):
    return re.match(r'^http:\/\/\[[0-9a-fA-F:]+\]', url) is not None

def find_similar_name(target_name, name_list):
    matches = difflib.get_close_matches(target_name, name_list, n=1, cutoff=0.6)
    return matches[0] if matches else None

# 优化后的fetch_with_retry
async def fetch_with_retry(session, url, retries=1, headers=None, timeout=5):
    last_exc = None
    for attempt in range(retries + 1):
        try:
            async with session.get(url, headers=headers, timeout=timeout) as response:
                response.raise_for_status()
                return await response.text()
        except aiohttp.ClientResponseError as e:
            if e.status in [401, 403, 404, 429]:
                logging.warning(f"url: {url} 失败({e.status}), 跳过")
                return None
            last_exc = e
            break
        except (asyncio.TimeoutError, aiohttp.ClientConnectorError) as e:
            logging.warning(f"url: {url} 请求超时或连接失败，跳过")
            last_exc = e
            break
        except Exception as e:
            last_exc = e
            await asyncio.sleep(0.3)
    logging.error(f"url: {url} 失败❌, Error: {repr(last_exc)}")
    return None

# fetch_channels 支持失败/跳过逻辑
async def fetch_channels(session, url, cache):
    channels = OrderedDict()
    unique_urls = set()
    cache_hit = False
    url_hash = calculate_hash(url)
    if url_hash in cache["urls"]:
        try:
            cached_entry = cache["urls"][url_hash]
            if datetime.now() - datetime.fromisoformat(cached_entry["timestamp"]) <= timedelta(days=cache_valid_days):
                channels = OrderedDict(cached_entry["channels"])
                unique_urls = set(cached_entry["unique_urls"])
                cache_hit = True
        except Exception as e:
            logging.error(f"读取缓存异常: {repr(e)}")
    if not cache_hit:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; IPTVBot/1.0; +https://github.com/alantang1977/X)"
            }
            content = await fetch_with_retry(session, url, headers=headers)
            if content is None:
                return channels  # 跳过该源
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
            logging.error(f"url: {url} 失败❌, Error: {repr(e)}")
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

def match_channels(template_channels, all_channels):
    matched_channels = OrderedDict()
    all_online_channel_names = []
    for online_category, online_channel_list in all_channels.items():
        for online_channel_name, _ in online_channel_list:
            all_online_channel_names.append(online_channel_name)
    for category, channel_list in template_channels.items():
        matched_channels[category] = OrderedDict()
        for channel_name in channel_list:
            similar_name = find_similar_name(clean_channel_name(channel_name), [clean_channel_name(name) for name in all_online_channel_names])
            if similar_name:
                original_name = next((name for name in all_online_channel_names if clean_channel_name(name) == similar_name), None)
                if original_name:
                    for online_category, online_channel_list in all_channels.items():
                        for online_channel_name, online_channel_url in online_channel_list:
                            if online_channel_name == original_name:
                                matched_channels[category].setdefault(channel_name, []).append(online_channel_url)
    return matched_channels

async def test_url(session, url, timeout=3):
    try:
        start = time.monotonic()
        async with session.head(url, timeout=timeout, allow_redirects=True) as resp:
            if resp.status == 200:
                cost = time.monotonic() - start
                return (url, cost, True)
    except Exception:
        pass
    return (url, None, False)

async def speedtest_channel_urls(channel_urls_dict, test_timeout=3, concurrency=30):
    result = {}
    semaphore = asyncio.Semaphore(concurrency)
    async with aiohttp.ClientSession() as session:
        tasks = []
        for channel, urls in channel_urls_dict.items():
            for url in urls:
                async def sem_test_url(channel=channel, url=url):
                    async with semaphore:
                        return channel, *await test_url(session, url, test_timeout)
                tasks.append(sem_test_url())
        all_ping = await asyncio.gather(*tasks)
    for channel, url, cost, ok in all_ping:
        if ok:
            result.setdefault(channel, []).append((url, cost))
    for channel in result:
        result[channel].sort(key=lambda x: x[1])
    return result

def get_logo_url(channel_name):
    # 可自定义logo库
    return f"https://gitee.com/IIII-9306/PAV/raw/master/logos/{channel_name}.png"

def write_to_files(f_m3u, f_txt, category, channel_name, index, new_url):
    logo_url = get_logo_url(channel_name)
    f_m3u.write(f"#EXTINF:-1 tvg-id=\"{index}\" tvg-name=\"{channel_name}\" tvg-logo=\"{logo_url}\" group-title=\"{category}\",{channel_name}\n")
    f_m3u.write(new_url + "\n")
    f_txt.write(f"{channel_name},{new_url}\n")

def add_url_suffix(url, index, total_urls, ip_version):
    suffix = f"${ip_version}" if total_urls == 1 else f"${ip_version}•线路{index}"
    base_url = url.split('$', 1)[0] if '$' in url else url
    return f"{base_url}{suffix}"

def updateChannelUrlsM3U(channels, template_channels, cache):
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
        for category, channel_list in template_channels.items():
            f_txt_ipv4.write(f"{category},#genre#\n")
            f_txt_ipv6.write(f"{category},#genre#\n")
            if category in channels:
                for channel_name in channel_list:
                    if channel_name in channels[category]:
                        sorted_urls_ipv4 = []
                        sorted_urls_ipv6 = []
                        for url in channels[category][channel_name]:
                            if is_ipv6(url):
                                if url not in written_urls_ipv6 and is_valid_url(url):
                                    sorted_urls_ipv6.append(url)
                                    written_urls_ipv6.add(url)
                            else:
                                if url not in written_urls_ipv4 and is_valid_url(url):
                                    sorted_urls_ipv4.append(url)
                                    written_urls_ipv4.add(url)
                        total_urls_ipv4 = len(sorted_urls_ipv4)
                        total_urls_ipv6 = len(sorted_urls_ipv6)
                        for index, url in enumerate(sorted_urls_ipv4, start=1):
                            new_url = add_url_suffix(url, index, total_urls_ipv4, "IPV4")
                            write_to_files(f_m3u_ipv4, f_txt_ipv4, category, channel_name, index, new_url)
                        for index, url in enumerate(sorted_urls_ipv6, start=1):
                            new_url = add_url_suffix(url, index, total_urls_ipv6, "IPV6")
                            write_to_files(f_m3u_ipv6, f_txt_ipv6, category, channel_name, index, new_url)
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

# fetch_channels 加限流
async def fetch_channels_limited(session, url, cache, semaphore):
    async with semaphore:
        return await fetch_channels(session, url, cache)

# 全局源并发控制在10
async def filter_source_urls(template_file):
    template_channels = parse_template(template_file)
    source_urls = config.source_urls
    cache = load_cache()
    all_channels = OrderedDict()
    semaphore = asyncio.Semaphore(10)
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_channels_limited(session, url, cache, semaphore) for url in source_urls]
        fetched_channels_list = await asyncio.gather(*tasks)
    for fetched_channels in fetched_channels_list:
        merge_channels(all_channels, fetched_channels)
    matched_channels = match_channels(template_channels, all_channels)
    return matched_channels, template_channels, cache

async def filter_and_speedtest_channels(template_file):
    matched_channels, template_channels, cache = await filter_source_urls(template_file)
    channel_urls_dict = {}
    for category, ch_dict in matched_channels.items():
        for ch, url_list in ch_dict.items():
            url_list = [u for u in url_list if not any(blk in u for blk in config.url_blacklist)]
            url_list = list(dict.fromkeys(url_list))
            channel_urls_dict.setdefault(ch, []).extend(url_list)
    print("正在对所有频道源测速、优选，请稍候...")
    speedtest_result = await speedtest_channel_urls(channel_urls_dict)
    for category, ch_dict in matched_channels.items():
        for ch in ch_dict:
            urlcosts = speedtest_result.get(ch, [])
            if urlcosts:
                ch_dict[ch] = [url for url, _ in urlcosts]
            else:
                ch_dict[ch] = []
    print("测速优选完成，正在输出文件...")
    return matched_channels, template_channels, cache

if __name__ == "__main__":
    template_file = "demo.txt"
    try:
        if not os.path.exists(template_file):
            print(f"错误: 找不到模板文件 '{template_file}'。")
            print("请确保项目目录下有 demo.txt 文件。")
            print("""
# demo.txt 示例内容
央视,#genre#
CCTV-1
CCTV-2
卫视,#genre#
北京卫视
上海卫视
广东卫视
""")
            sys.exit(1)
        loop = asyncio.get_event_loop()
        channels, template_channels, cache = loop.run_until_complete(
            filter_and_speedtest_channels(template_file)
        )
        updateChannelUrlsM3U(channels, template_channels, cache)
        loop.close()
        print("操作完成！结果已保存到live文件夹。")
    except Exception as e:
        print(f"执行过程中发生错误: {repr(e)}")
        logging.error(f"程序运行失败: {repr(e)}\n{traceback.format_exc()}")
