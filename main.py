# main.py
import re
import asyncio
import logging
import json
import os
from collections import OrderedDict
from datetime import datetime, timedelta
import difflib
import hashlib

# 检查 aiohttp 是否安装
try:
    import aiohttp
except ImportError:
    print("错误: 缺少必要的依赖库 'aiohttp'。")
    print("请使用以下命令安装:")
    print("pip install aiohttp")
    import sys
    sys.exit(1)

# 检查 config 是否存在
try:
    import config
    # 验证配置文件的基本结构
    required_attrs = ['source_urls', 'epg_urls', 'announcements', 'url_blacklist', 'ip_version_priority']
    for attr in required_attrs:
        if not hasattr(config, attr):
            raise AttributeError(f"配置文件缺少必要的属性: {attr}")
except ImportError:
    print("错误: 找不到配置模块 'config.py'。")
    print("请确保项目目录下有 config.py 文件，内容示例如下:")
    print("""
# config.py 示例内容
source_urls = [
    "https://example.com/source1.m3u",
    "https://example.com/source2.m3u"
]
epg_urls = ["https://example.com/epg.xml"]
announcements = [
    {
        "channel": "公告",
        "entries": [
            {
                "name": None,
                "url": "https://example.com/notice",
                "logo": "https://picsum.photos/100/100?random=1"
            }
        ]
    }
]
url_blacklist = []
ip_version_priority = "ipv4"
""")
    import sys
    sys.exit(1)
except AttributeError as e:
    print(f"配置文件错误: {e}")
    import sys
    sys.exit(1)

# 日志记录，只记录错误信息
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler("./live/function.log", "w", encoding="utf-8"), logging.StreamHandler()])

# 确保 live 文件夹存在
output_folder = "live"
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# 缓存文件夹和文件
cache_folder = "./live/cache"
cache_file = os.path.join(cache_folder, "url_cache.json")
cache_valid_days = 7  # 缓存有效期（天）

# 确保缓存文件夹存在
if not os.path.exists(cache_folder):
    os.makedirs(cache_folder)

# 加载缓存
def load_cache():
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"加载缓存失败: {e}")
    return {"urls": {}, "timestamp": datetime.now().isoformat()}

# 保存缓存
def save_cache(cache):
    cache["timestamp"] = datetime.now().isoformat()
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"保存缓存失败: {e}")

# 检查缓存是否有效
def is_cache_valid(cache):
    if not cache:
        return False
    timestamp = datetime.fromisoformat(cache.get("timestamp", datetime.now().isoformat()))
    return (datetime.now() - timestamp).days < cache_valid_days

# 计算URL内容的哈希值
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

async def fetch_channels(session, url, cache):
    channels = OrderedDict()
    unique_urls = set()
    cache_hit = False

    # 检查URL是否在缓存中且有效
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
                source_type = "m3u" if is_m3u else "txt"

                if is_m3u:
                    channels.update(parse_m3u_lines(lines, unique_urls))
                else:
                    channels.update(parse_txt_lines(lines, unique_urls))

                if channels:
                    # 更新缓存
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

def find_similar_name(target_name, name_list):
    matches = difflib.get_close_matches(target_name, name_list, n=1, cutoff=0.6)
    return matches[0] if matches else None

async def filter_source_urls(template_file):
    template_channels = parse_template(template_file)
    source_urls = config.source_urls
    cache = load_cache()

    all_channels = OrderedDict()
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_channels(session, url, cache) for url in source_urls]
        fetched_channels_list = await asyncio.gather(*tasks)

    for fetched_channels in fetched_channels_list:
        merge_channels(all_channels, fetched_channels)

    matched_channels = match_channels(template_channels, all_channels)

    return matched_channels, template_channels, cache

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

def merge_channels(target, source):
    for category, channel_list in source.items():
        if category in target:
            target[category].extend(channel_list)
        else:
            target[category] = channel_list

def is_ipv6(url):
    return re.match(r'^http:\/\/\[[0-9a-fA-F:]+\]', url) is not None

def updateChannelUrlsM3U(channels, template_channels, cache):
    written_urls_ipv4 = set()
    written_urls_ipv6 = set()
    url_changes = {"added": [], "removed": [], "modified": []}

    # 检查缓存中的URL状态
    if is_cache_valid(cache):
        previous_urls = {}
        for url_hash, entry in cache["urls"].items():
            for category, channel_list in entry["channels"].items():
                for channel_name, url in channel_list:
                    previous_urls[url] = (category, channel_name)

        # 检测URL变化
        current_urls = {}
        for category, channel_dict in channels.items():
            for channel_name, urls in channel_dict.items():
                for url in urls:
                    current_urls[url] = (category, channel_name)

        # 新增的URL
        for url, (category, channel_name) in current_urls.items():
            if url not in previous_urls:
                url_changes["added"].append((category, channel_name, url))

        # 移除的URL
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

    # 保存URL变化日志
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

def sort_and_filter_urls(urls, written_urls):
    filtered_urls = [
        url for url in sorted(urls, key=lambda u: not is_ipv6(u) if config.ip_version_priority == "ipv6" else is_ipv6(u))
        if url and url not in written_urls and not any(blacklist in url for blacklist in config.url_blacklist)
    ]
    written_urls.update(filtered_urls)
    return filtered_urls

def add_url_suffix(url, index, total_urls, ip_version):
    suffix = f"${ip_version}" if total_urls == 1 else f"${ip_version}•线路{index}"
    base_url = url.split('$', 1)[0] if '$' in url else url
    return f"{base_url}{suffix}"

def write_to_files(f_m3u, f_txt, category, channel_name, index, new_url):
    logo_url = f"https://gitee.com/IIII-9306/PAV/raw/master/logos/{channel_name}.png"
    f_m3u.write(f"#EXTINF:-1 tvg-id=\"{index}\" tvg-name=\"{channel_name}\" tvg-logo=\"{logo_url}\" group-title=\"{category}\",{channel_name}\n")
    f_m3u.write(new_url + "\n")
    f_txt.write(f"{channel_name},{new_url}\n")

if __name__ == "__main__":
    template_file = "demo.txt"
    try:
        # 检查模板文件是否存在
        if not os.path.exists(template_file):
            print(f"错误: 找不到模板文件 '{template_file}'。")
            print("请确保项目目录下有 demo.txt 文件。")
            print("示例内容如下:")
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
            import sys
            sys.exit(1)

        loop = asyncio.get_event_loop()
        channels, template_channels, cache = loop.run_until_complete(filter_source_urls(template_file))
        updateChannelUrlsM3U(channels, template_channels, cache)
        loop.close()
        print("操作完成！结果已保存到live文件夹。")
    except Exception as e:
        print(f"执行过程中发生错误: {e}")
        logging.error(f"程序运行失败: {e}")
