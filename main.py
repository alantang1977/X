import re
import asyncio
import logging
import json
import os
import random
import time
from collections import OrderedDict
from datetime import datetime, timedelta
import difflib
import hashlib
from urllib.parse import urlparse, urlunparse, parse_qs

# 检查 aiohttp 是否安装
try:
    import aiohttp
    from aiohttp import TCPConnector
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

# 随机User-Agent列表
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 10; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36'
]

# 获取随机请求头
def get_random_headers():
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
    }

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

def remove_unnecessary_params(url):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    # 假设只保留必要的参数，这里可以根据实际情况修改
    necessary_params = {}
    for param, values in query_params.items():
        if param in ['必要参数1', '必要参数2']:  # 替换为实际必要的参数名
            necessary_params[param] = values
    new_query = '&'.join([f'{param}={value[0]}' for param, value in necessary_params.items()])
    new_url = urlunparse((parsed_url.scheme, parsed_url.netloc, parsed_url.path, parsed_url.params, new_query, parsed_url.fragment))
    return new_url

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
        max_retries = 3
        retry_delay = 2
        for attempt in range(max_retries):
            try:
                # 使用随机请求头
                headers = get_random_headers()
                
                # 设置超时和重定向
                timeout = aiohttp.ClientTimeout(total=15, connect=10)
                
                # 使用浏览器请求头发送请求
                async with session.get(url, headers=headers, timeout=timeout, allow_redirects=True) as response:
                    # 检查状态码
                    if response.status in [403, 401]:
                        logging.warning(f"url: {url} 访问受限 (状态码: {response.status}), 尝试更换User-Agent...")
                        headers = get_random_headers()
                        continue
                    
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
                    break  # 成功获取后跳出重试循环

            except aiohttp.ClientResponseError as e:
                if e.status in [403, 401] and attempt < max_retries - 1:
                    logging.warning(f"url: {url} 访问受限 (状态码: {e.status}), 重试 {attempt+1}/{max_retries}...")
                    await asyncio.sleep(retry_delay)
                else:
                    logging.error(f"url: {url} 失败❌ (状态码: {e.status}), Error: {e}")
                    break
                    
            except (aiohttp.ClientConnectionError, asyncio.TimeoutError) as e:
                if attempt < max_retries - 1:
                    logging.warning(f"url: {url} 连接超时, 重试 {attempt+1}/{max_retries}...")
                    await asyncio.sleep(retry_delay)
                else:
                    logging.error(f"url: {url} 连接失败❌, Error: {e}")
                    break
                    
            except Exception as e:
                logging.error(f"url: {url} 失败❌, Error: {e}")
                break

    # 再次检查并去除重复的频道
    for category, channel_list in channels.items():
        new_channel_list = []
        seen_channels = set()
        for channel_name, url in channel_list:
            if (channel_name, url) not in seen_channels:
                new_channel_list.append((channel_name, url))
                seen_channels.add((channel_name, url))
        channels[category] = new_channel_list

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

    # 创建连接池和会话
    connector = TCPConnector(limit_per_host=5, ttl_dns_cache=300)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch_channels(session, url, cache) for url in source_urls]
        fetched_channels_list = await asyncio.gather(*tasks)

    all_channels = OrderedDict()
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

# 每个频道最大URL数量
MAX_URLS_PER_CHANNEL = 20

async def measure_response_time(session, url):
    """测量URL的响应时间（毫秒）"""
    try:
        start_time = asyncio.get_event_loop().time()
        async with session.head(url, headers=get_random_headers(), timeout=5) as response:
            await response.read()  # 确保完全读取响应
            elapsed = (asyncio.get_event_loop().time() - start_time) * 1000
            return url, round(elapsed, 2)
    except Exception:
        return url, float('inf')  # 超时或错误返回无限大

async def test_and_sort_urls(session, urls):
    """测试并排序URL列表（响应时间短的优先）"""
    if not urls:
        return []
    
    # 创建测速任务
    tasks = [measure_response_time(session, url) for url in urls]
    results = await asyncio.gather(*tasks)
    
    # 过滤无效URL并排序
    valid_results = [item for item in results if item[1] < float('inf')]
    sorted_results = sorted(valid_results, key=lambda x: x[1])  # 按响应时间升序排序
    
    # 只返回URL列表
    return [url for url, _ in sorted_results]

async def updateChannelUrlsM3U(channels, template_channels, cache):
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

    # 创建连接池和会话
    connector = TCPConnector(limit_per_host=10, ttl_dns_cache=300)
    async with aiohttp.ClientSession(connector=connector) as session:
        with open(ipv4_m3u_path, "w", encoding="utf-8") as f_m3u_ipv4, \
                open(ipv4_txt_path, "w", encoding="utf-8") as f_txt_ipv4, \
                open(ipv6_m3u_path, "w", encoding="utf-8") as f_m3u_ipv6, \
                open(ipv6_txt_path, "w", encoding="utf-8") as f_txt_ipv6:

            f_m3u_ipv4.write(f"""#EXTM3U x-tvg-url={",".join(f'"{epg_url}"' for epg_url in config.epg_urls)}\n""")
            f_m3u_ipv6.write(f"""#EXTM3U x-tvg-url={",".join(f'"{epg_url}"' for epg_url in config.epg_urls)}\n""")

            # 写入公告频道
            for group in config.announcements:
                f_txt_ipv4.write(f"{group['channel']},#genre#\n")
                f_txt_ipv6.write(f"{group['channel']},#genre#\n")
                for announcement in group['entries']:
                    url = announcement['url']
                    url = remove_unnecessary_params(url)
                    if is_ipv6(url):
                        if url not in written_urls_ipv6 and is_valid_url(url):
                            written_urls_ipv6.add(url)
                            write_to_files(f_m3u_ipv6, f_txt_ipv6, group['channel'], announcement['name'], 1, url)
                    else:
                        if url not in written_urls_ipv4 and is_valid_url(url):
                            written_urls_ipv4.add(url)
                            write_to_files(f_m3u_ipv4, f_txt_ipv4, group['channel'], announcement['name'], 1, url)

            # 创建频道URL测速任务
            channel_tasks = []
            for category, channel_list in template_channels.items():
                if category in channels:
                    for channel_name in channel_list:
                        if channel_name in channels[category]:
                            urls = channels[category][channel_name]
                            # 去重和清理
                            unique_urls = set()
                            cleaned_urls = []
                            for url in urls:
                                cleaned_url = remove_unnecessary_params(url)
                                if cleaned_url not in unique_urls and is_valid_url(cleaned_url) and not any(blacklist in cleaned_url for blacklist in config.url_blacklist):
                                    cleaned_urls.append(cleaned_url)
                                    unique_urls.add(cleaned_url)
                            channel_tasks.append((category, channel_name, cleaned_urls))
            
            # 批量处理所有频道的URL测速和排序
            sorted_results = {}
            for category, channel_name, urls in channel_tasks:
                if urls:
                    sorted_urls = await test_and_sort_urls(session, urls)
                    # 限制每个频道最多MAX_URLS_PER_CHANNEL条URL
                    sorted_results[(category, channel_name)] = sorted_urls[:MAX_URLS_PER_CHANNEL]
                else:
                    sorted_results[(category, channel_name)] = []
            
            # 先写入分类标题
            for category in template_channels:
                f_txt_ipv4.write(f"{category},#genre#\n")
                f_txt_ipv6.write(f"{category},#genre#\n")
            
            # 写入排序后的频道URL
            for (category, channel_name), sorted_urls in sorted_results.items():
                # 分离IPv4和IPv6
                ipv4_urls = [url for url in sorted_urls if not is_ipv6(url)]
                ipv6_urls = [url for url in sorted_urls if is_ipv6(url)]
                
                total_urls_ipv4 = len(ipv4_urls)
                total_urls_ipv6 = len(ipv6_urls)
                
                # 写入IPv4 URL
                for index
