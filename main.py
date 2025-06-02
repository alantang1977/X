import os
import re
import json
import asyncio
import logging
from collections import OrderedDict
from datetime import datetime, timedelta
import difflib
import hashlib

# 检查 config.py 并读取配置
CONFIG_VARS = [
    'source_urls', 'epg_urls', 'announcements', 'url_blacklist', 'ip_version_priority'
]
def load_config():
    try:
        import config
        for var in CONFIG_VARS:
            if not hasattr(config, var):
                raise AttributeError(f"配置文件缺少必要的属性: {var}")
        return config
    except ImportError:
        print("错误: 找不到配置模块 'config.py'。")
        print("请确保项目目录下有 config.py 文件，内容示例如下:")
        print("""
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
        exit(1)
    except AttributeError as e:
        print(f"配置文件错误: {e}")
        exit(1)

config = load_config()

# 日志配置
os.makedirs("live", exist_ok=True)
os.makedirs("live/cache", exist_ok=True)
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("./live/function.log", "w", encoding="utf-8"), logging.StreamHandler()])

# 缓存相关
CACHE_FILE = "./live/cache/url_cache.json"
CACHE_DAYS = 7

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"加载缓存失败: {e}")
    return {"urls": {}, "timestamp": datetime.now().isoformat()}

def save_cache(cache):
    cache["timestamp"] = datetime.now().isoformat()
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"保存缓存失败: {e}")

def is_cache_valid(cache):
    if not cache: return False
    timestamp = cache.get("timestamp", datetime.now().isoformat())
    timestamp = datetime.fromisoformat(timestamp)
    return (datetime.now() - timestamp).days < CACHE_DAYS

def calculate_hash(content):
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def clean_channel_name(name):
    # 去除特殊字符、空格、将数字规范化
    name = re.sub(r'[$「」-]', '', name)
    name = re.sub(r'\s+', '', name)
    name = re.sub(r'(\D*)(\d+)', lambda m: m.group(1) + str(int(m.group(2))), name)
    return name.upper()

def is_valid_url(url):
    return bool(re.match(r'^https?://', url))

def is_ipv6(url):
    return re.match(r'^http:\/\/\[[0-9a-fA-F:]+\]', url) is not None

def parse_template(template_file):
    template_channels = OrderedDict()
    current_category = None
    with open(template_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"): continue
            if "#genre#" in line:
                current_category = line.split(",", 1)[0].strip()
                template_channels[current_category] = []
            elif current_category:
                channel_name = line.split(",", 1)[0].strip()
                template_channels[current_category].append(channel_name)
    return template_channels

async def fetch_channels(session, url, cache):
    channels = OrderedDict()
    unique_urls = set()
    url_hash = calculate_hash(url)
    cache_entry = cache["urls"].get(url_hash)
    if cache_entry:
        if datetime.now() - datetime.fromisoformat(cache_entry["timestamp"]) <= timedelta(days=CACHE_DAYS):
            channels = OrderedDict(cache_entry["channels"])
            unique_urls = set(cache_entry["unique_urls"])
            return channels
    try:
        async with session.get(url) as resp:
            resp.raise_for_status()
            content = await resp.text()
            lines = content.splitlines()
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
    current_category, channel_name = None, None
    for line in lines:
        line = line.strip()
        if line.startswith("#EXTINF"):
            match = re.search(r'group-title="(.*?)",(.*)', line)
            if match:
                current_category = match.group(1).strip()
                channel_name = match.group(2).strip()
                if channel_name.startswith("CCTV"):
                    channel_name = clean_channel_name(channel_name)
                if current_category not in channels:
                    channels[current_category] = []
        elif line and not line.startswith("#"):
            channel_url = line
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
                if channel_name.startswith("CCTV"):
                    channel_name = clean_channel_name(channel_name)
                urls = [u.strip() for u in match.group(2).split('#')]
                for url in urls:
                    if is_valid_url(url) and url not in unique_urls:
                        unique_urls.add(url)
                        channels[current_category].append((channel_name, url))
            elif line:
                channels[current_category].append((line, ""))
    return channels

def find_similar_name(target, name_list):
    matches = difflib.get_close_matches(target, name_list, n=1, cutoff=0.6)
    return matches[0] if matches else None

def merge_channels(target, source):
    for cat, lst in source.items():
        if cat in target: target[cat].extend(lst)
        else: target[cat] = lst

def match_channels(template_channels, all_channels):
    matched = OrderedDict()
    all_online_names = []
    for cat, lst in all_channels.items():
        for n, _ in lst:
            all_online_names.append(n)
    for cat, clist in template_channels.items():
        matched[cat] = OrderedDict()
        for cname in clist:
            similar = find_similar_name(clean_channel_name(cname), [clean_channel_name(n) for n in all_online_names])
            if similar:
                orig = next((n for n in all_online_names if clean_channel_name(n) == similar), None)
                if orig:
                    for ocat, olist in all_channels.items():
                        for n, url in olist:
                            if n == orig:
                                matched[cat].setdefault(cname, []).append(url)
    return matched

async def filter_source_urls(template_file):
    template_channels = parse_template(template_file)
    cache = load_cache()
    all_channels = OrderedDict()
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_channels(session, url, cache) for url in config.source_urls]
        fetched = await asyncio.gather(*tasks)
    for ch in fetched:
        merge_channels(all_channels, ch)
    matched = match_channels(template_channels, all_channels)
    return matched, template_channels, cache

def add_url_suffix(url, idx, total, ipver):
    suffix = f"${ipver}" if total == 1 else f"${ipver}•线路{idx}"
    base = url.split('$', 1)[0] if '$' in url else url
    return f"{base}{suffix}"

def write_to_files(f_m3u, f_txt, cat, cname, idx, url):
    logo_url = f"https://gitee.com/IIII-9306/PAV/raw/master/logos/{cname}.png"
    f_m3u.write(f"#EXTINF:-1 tvg-id=\"{idx}\" tvg-name=\"{cname}\" tvg-logo=\"{logo_url}\" group-title=\"{cat}\",{cname}\n")
    f_m3u.write(url + "\n")
    f_txt.write(f"{cname},{url}\n")

def updateChannelUrlsM3U(channels, template_channels, cache):
    written4, written6 = set(), set()
    ipv4_m3u_path = os.path.join("live", "live_ipv4.m3u")
    ipv4_txt_path = os.path.join("live", "live_ipv4.txt")
    ipv6_m3u_path = os.path.join("live", "live_ipv6.m3u")
    ipv6_txt_path = os.path.join("live", "live_ipv6.txt")
    current_date = datetime.now().strftime("%Y-%m-%d")
    for group in config.announcements:
        for ann in group['entries']:
            if ann['name'] is None:
                ann['name'] = current_date
    with open(ipv4_m3u_path, "w", encoding="utf-8") as f4m, \
         open(ipv4_txt_path, "w", encoding="utf-8") as f4t, \
         open(ipv6_m3u_path, "w", encoding="utf-8") as f6m, \
         open(ipv6_txt_path, "w", encoding="utf-8") as f6t:
        f4m.write(f"""#EXTM3U x-tvg-url={",".join(f'"{e}"' for e in config.epg_urls)}\n""")
        f6m.write(f"""#EXTM3U x-tvg-url={",".join(f'"{e}"' for e in config.epg_urls)}\n""")
        for group in config.announcements:
            f4t.write(f"{group['channel']},#genre#\n")
            f6t.write(f"{group['channel']},#genre#\n")
            for ann in group['entries']:
                url = ann['url']
                if is_ipv6(url):
                    if url not in written6 and is_valid_url(url):
                        written6.add(url)
                        f6m.write(f"""#EXTINF:-1 tvg-id="1" tvg-name="{ann['name']}" tvg-logo="{ann['logo']}" group-title="{group['channel']}",{ann['name']}\n""")
                        f6m.write(f"{url}\n")
                        f6t.write(f"{ann['name']},{url}\n")
                else:
                    if url not in written4 and is_valid_url(url):
                        written4.add(url)
                        f4m.write(f"""#EXTINF:-1 tvg-id="1" tvg-name="{ann['name']}" tvg-logo="{ann['logo']}" group-title="{group['channel']}",{ann['name']}\n""")
                        f4m.write(f"{url}\n")
                        f4t.write(f"{ann['name']},{url}\n")
        for cat, clist in template_channels.items():
            f4t.write(f"{cat},#genre#\n")
            f6t.write(f"{cat},#genre#\n")
            if cat in channels:
                for cname in clist:
                    if cname in channels[cat]:
                        sorted4, sorted6 = [], []
                        for url in channels[cat][cname]:
                            if is_ipv6(url):
                                if url not in written6 and is_valid_url(url):
                                    sorted6.append(url)
                                    written6.add(url)
                            else:
                                if url not in written4 and is_valid_url(url):
                                    sorted4.append(url)
                                    written4.add(url)
                        total4 = len(sorted4)
                        total6 = len(sorted6)
                        for idx, url in enumerate(sorted4, 1):
                            new_url = add_url_suffix(url, idx, total4, "IPV4")
                            write_to_files(f4m, f4t, cat, cname, idx, new_url)
                        for idx, url in enumerate(sorted6, 1):
                            new_url = add_url_suffix(url, idx, total6, "IPV6")
                            write_to_files(f6m, f6t, cat, cname, idx, new_url)
        f4t.write("\n")
        f6t.write("\n")

if __name__ == "__main__":
    try:
        import aiohttp
    except ImportError:
        print("错误: 缺少必要的依赖库 'aiohttp'。\n请运行: pip install aiohttp")
        exit(1)
    template_file = "demo.txt"
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
        exit(1)
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        channels, template_channels, cache = loop.run_until_complete(filter_source_urls(template_file))
        updateChannelUrlsM3U(channels, template_channels, cache)
        print("操作完成！结果已保存到 live 文件夹。")
    except Exception as e:
        print(f"执行过程中发生错误: {e}")
        logging.error(f"程序运行失败: {e}")
