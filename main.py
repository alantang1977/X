# main.py

import re
import asyncio
import logging
import json
import os
import time
from collections import OrderedDict
from datetime import datetime, timedelta
import difflib
import hashlib

# 检查 aiohttp 是否安装
try:
    import aiohttp
except ImportError:
    print("错误: 缺少必要的依赖库 'aiohttp'。")
    print("请使用: pip install aiohttp")
    import sys
    sys.exit(1)

# 检查 config 是否存在并验证结构
try:
    import config
    required_attrs = [
        'source_urls', 'epg_urls', 'announcements',
        'url_blacklist', 'ip_version_priority',
        'max_links_per_channel', 'speed_test_timeout',
        'speed_test_concurrency'
    ]
    for attr in required_attrs:
        if not hasattr(config, attr):
            raise AttributeError(f"配置文件缺少必要属性: {attr}")
except ImportError:
    print("错误: 找不到配置模块 'config.py'。")
    print("请确保项目目录下有 config.py，示例如下：")
    print("""
# config.py 示例

# 1. 流源 URL 列表（M3U 或 TXT）
source_urls = [
    "https://example.com/source1.m3u",
    "https://example.com/source2.m3u"
]

# 2. EPG（电子节目表）URL 列表
epg_urls = [
    "https://epg.example.com/epg.xml"
]

# 3. 公告（Announcements）
#    格式：[{ "channel": "分类名", "entries": [ { "name": None 或 固定名称, "url": 播放 URL, "logo": 图标 URL }, ... ] }, ...]
announcements = [
    {
        "channel": "公告",
        "entries": [
            {
                "name": None,  # None 会自动用当天日期替代
                "url": "https://live.example.com/notice",
                "logo": "https://picsum.photos/100/100?random=1"
            }
        ]
    }
]

# 4. URL 黑名单：若 URL 包含其中任意字符串，视为无效流，早期过滤
url_blacklist = [
    "test.bad.domain",
    "unwanted_stream"
]

# 5. IP 版本优先级（此版本只支持 ipv4）
ip_version_priority = "ipv4"

# 6. 每个频道最多保留的链接数量
max_links_per_channel = 10  # 例如：CCTV-1 只保留最快的 10 条链接

# 7. 速度测试超时时间（秒）
speed_test_timeout = 3.0     # 单个 URL 的测速超时（秒），超时视为不可用

# 8. 并发测速最大并行数
speed_test_concurrency = 20  # 同时对最多 20 条 URL 发起测试，避免瞬时过多连接
""")
    import sys
    sys.exit(1)
except AttributeError as e:
    print(f"配置文件错误: {e}")
    import sys
    sys.exit(1)

# 日志：只记录 ERROR 级别到文件和控制台
logging.basicConfig(level=logging.ERROR,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("./live/function.log", "w", encoding="utf-8"),
                        logging.StreamHandler()
                    ])

# 确保输出文件夹存在
output_folder = "live"
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# 缓存文件及配置
cache_folder = os.path.join(output_folder, "cache")
cache_file = os.path.join(cache_folder, "url_cache.json")
cache_valid_days = 7  # 缓存有效期（天）

if not os.path.exists(cache_folder):
    os.makedirs(cache_folder)

def load_cache():
    """
    加载本地缓存（包含每个源 URL 的解析结果和时间戳）。
    """
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"加载缓存失败: {e}")
    return {"urls": {}, "timestamp": datetime.now().isoformat()}

def save_cache(cache):
    """
    保存缓存至本地，同时更新时间戳。
    """
    cache["timestamp"] = datetime.now().isoformat()
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"保存缓存失败: {e}")

def is_cache_valid(cache):
    """
    判断缓存是否在有效期内：
    若当前时间距缓存 timestamp 小于 cache_valid_days 天，则视为有效。
    """
    if not cache:
        return False
    try:
        ts = datetime.fromisoformat(cache.get("timestamp", datetime.now().isoformat()))
        return (datetime.now() - ts).days < cache_valid_days
    except Exception:
        return False

def calculate_hash(content):
    """
    计算字符串 content 的 MD5 哈希值，用于缓存键。
    """
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def parse_template(template_file):
    """
    解析模板文件（demo.txt / subscribe.txt），生成 OrderedDict:
    { 分类名: [频道名1, 频道名2, ...], ... }
    """
    template_channels = OrderedDict()
    current_category = None

    with open(template_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "#genre#" in line:
                # 新的分类行：格式示例 “央视,#genre#”
                current_category = line.split(",")[0].strip()
                template_channels[current_category] = []
            elif current_category:
                # 本行是该分类下的频道名称
                channel_name = line.split(",")[0].strip()
                template_channels[current_category].append(channel_name)
    return template_channels

def clean_channel_name(channel_name):
    """
    清洗频道名称：
    1. 去掉 $, 「」, - 等无效字符
    2. 删除所有空白
    3. 将“频道名+数字”规范为大写形式，如 CCTV-1 → CCTV1
    """
    cleaned = re.sub(r'[$「」-]', '', channel_name)
    cleaned = re.sub(r'\s+', '', cleaned)
    cleaned = re.sub(r'(\D*)(\d+)', lambda m: m.group(1) + str(int(m.group(2))), cleaned)
    return cleaned.upper()

def is_valid_url(url):
    """
    仅保留以 http:// 或 https:// 开头的 URL
    """
    return bool(re.match(r'^https?://', url))

async def fetch_channels(session, url, cache):
    """
    异步请求并解析单个源 URL，返回 OrderedDict{分类: [(频道名, URL), ...], ...}。
    如缓存未命中，则发起网络请求，否则直接返回缓存解析结果。
    """
    channels = OrderedDict()
    unique_urls = set()
    cache_hit = False

    url_hash = calculate_hash(url)
    if url_hash in cache["urls"]:
        entry = cache["urls"][url_hash]
        try:
            ts = datetime.fromisoformat(entry.get("timestamp", datetime.now().isoformat()))
        except Exception:
            ts = datetime.now()
        if (datetime.now() - ts).days <= cache_valid_days:
            try:
                # 从缓存直接读取
                channels = OrderedDict(entry["channels"])
                unique_urls = set(entry["unique_urls"])
                cache_hit = True
                # logging.info(f"缓存命中: {url}")
            except Exception:
                cache_hit = False

    if not cache_hit:
        try:
            async with session.get(url) as resp:
                resp.raise_for_status()
                text = await resp.text()
                lines = text.split("\n")
                # 判断是 M3U 还是纯文本格式
                is_m3u = any(line.startswith("#EXTINF") for line in lines[:15])
                if is_m3u:
                    parsed = parse_m3u_lines(lines, unique_urls)
                else:
                    parsed = parse_txt_lines(lines, unique_urls)
                if parsed:
                    channels = parsed
                    # 写入缓存
                    cache["urls"][url_hash] = {
                        "url": url,
                        "channels": dict(channels),
                        "unique_urls": list(unique_urls),
                        "timestamp": datetime.now().isoformat(),
                        "content_hash": calculate_hash(text)
                    }
                    save_cache(cache)
        except Exception as e:
            logging.error(f"[抓取失败] URL={url}, Error={e}")

    return channels

def parse_m3u_lines(lines, unique_urls):
    """
    解析 M3U 格式:
    - 遇到 #EXTINF 行时提取 group-title、频道名称；
    - 下一行（非注释）即为该频道对应的播放链接。
    返回 OrderedDict{分类: [(频道名, URL), ...], ...}。
    """
    channels = OrderedDict()
    current_category = None
    current_channel_name = None

    for line in lines:
        line = line.strip()
        if line.startswith("#EXTINF"):
            # 例：#EXTINF:-1 tvg-id="..." tvg-name="CCTV-1" tvg-logo="..." group-title="央视",CCTV-1
            match = re.search(r'group-title="(.*?)",(.*)', line)
            if match:
                current_category = match.group(1).strip()
                name = match.group(2).strip()
                name = clean_channel_name(name) if name else name
                current_channel_name = name
                if current_category not in channels:
                    channels[current_category] = []
        elif line and not line.startswith("#"):
            # 非注释行即 URL
            url = line
            if is_valid_url(url) and url not in unique_urls and current_category and current_channel_name:
                unique_urls.add(url)
                channels[current_category].append((current_channel_name, url))
    return channels

def parse_txt_lines(lines, unique_urls):
    """
    解析纯文本格式:
    - 格式为“分类,#genre#”行，后续为“频道名,URL#URL#…”或仅“频道名”。
    返回 OrderedDict{分类: [(频道名, URL), ...], ...}。
    """
    channels = OrderedDict()
    current_category = None

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if "#genre#" in line:
            # 新分类
            current_category = line.split(",")[0].strip()
            channels[current_category] = []
        elif current_category:
            # 本行可能是“频道名,链接1#链接2#链接3”，也可能仅是“频道名”
            match = re.match(r"^(.*?),(.*?)$", line)
            if match:
                raw_name = match.group(1).strip()
                raw_name = clean_channel_name(raw_name)
                url_list = match.group(2).strip().split('#')
                for url in url_list:
                    url = url.strip()
                    if is_valid_url(url) and url not in unique_urls:
                        unique_urls.add(url)
                        channels[current_category].append((raw_name, url))
            else:
                # 仅频道名，不带 URL
                name = clean_channel_name(line)
                channels[current_category].append((name, ""))
    return channels

def find_similar_name(target_name, name_list):
    """
    在 name_list 中寻找与 target_name 最相似的一个，使用 difflib.get_close_matches，
    阈值 cutoff=0.6。返回最相似的名字或 None。
    """
    matches = difflib.get_close_matches(target_name, name_list, n=1, cutoff=0.6)
    return matches[0] if matches else None

def merge_channels(target, source):
    """
    将 source（OrderedDict{分类: [(频道名, URL), ...] }）合并到 target 中。
    """
    for category, lst in source.items():
        if category in target:
            target[category].extend(lst)
        else:
            target[category] = lst

async def filter_source_urls(template_file):
    """
    1. 解析模板文件，得到 {分类: [频道名列表]}；
    2. 并发抓取 config.source_urls 中的每个流源，获取 {分类: [(频道名, URL), ...]}；
    3. 合并多个源，并做频道名称的模糊匹配，得到 matched_channels:
       OrderedDict{分类: OrderedDict{模板频道名: [URL 列表]} }。
    """
    template_channels = parse_template(template_file)
    source_urls = config.source_urls
    cache = load_cache()

    all_channels = OrderedDict()
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_channels(session, url, cache) for url in source_urls]
        results = await asyncio.gather(*tasks)

    for fetched in results:
        merge_channels(all_channels, fetched)

    # 准备在线所有频道名称的大列表（去重一次）
    all_online_names = []
    for cat, lst in all_channels.items():
        for name, _ in lst:
            all_online_names.append(name)
    all_online_names = list(set(all_online_names))

    # 根据模板文件进行模糊匹配，构建 matched
    matched = OrderedDict()
    for cat, channel_list in template_channels.items():
        matched[cat] = OrderedDict()
        for tpl_name in channel_list:
            clean_tpl = clean_channel_name(tpl_name)
            sim = find_similar_name(clean_tpl, [clean_channel_name(n) for n in all_online_names])
            if not sim:
                continue
            # 找到在线名称中与 sim 对应的原始名称
            orig_name = next((n for n in all_online_names if clean_channel_name(n) == sim), None)
            if not orig_name:
                continue
            # 遍历 all_channels，把匹配到的 URL 收集过来
            for online_cat, lst in all_channels.items():
                for online_name, url in lst:
                    if online_name == orig_name:
                        matched[cat].setdefault(tpl_name, []).append(url)

    return matched, template_channels, cache

async def test_url_speed(session, url, timeout):
    """
    对单个 URL 发起 HEAD 请求或低流量 GET 请求，测量响应时间。
    - 若成功响应，返回 (url, elapsed_time)；否则返回 (url, None)。
    """
    start = time.monotonic()
    try:
        # 只请求响应头，降低流量；如果目标服务器不支持 HEAD，可改为 GET 并立刻关闭
        async with session.head(url, timeout=timeout) as resp:
            resp.raise_for_status()
        elapsed = time.monotonic() - start
        return url, elapsed
    except Exception:
        return url, None

async def rank_channel_urls(channels):
    """
    异步并发对每个频道的多个 URL 进行测速，然后取用响应最快的前 N 条，
    并在测速前完成去重和黑名单过滤。
    输入:
      channels: OrderedDict{分类: OrderedDict{频道名: [原始 URL 列表]} }
    输出:
      OrderedDict{分类: OrderedDict{频道名: [按响应速度排序后的前 N 条 URL]} }
    """
    timeout = config.speed_test_timeout
    sem = asyncio.Semaphore(config.speed_test_concurrency)

    async with aiohttp.ClientSession() as session:
        new_channels = OrderedDict()
        for category, ch_dict in channels.items():
            new_channels[category] = OrderedDict()
            for channel_name, url_list in ch_dict.items():
                # 1. 去重 + 黑名单过滤 + 仅保留 IPv4（去掉 [:: ] IPv6 格式）
                filtered = []
                seen = set()
                for u in url_list:
                    if not is_valid_url(u):
                        continue
                    if u in seen:
                        continue
                    if any(bad in u for bad in config.url_blacklist):
                        continue
                    # 仅保留 IPv4，IPv6 地址格式形如 "http://[xxxx]", 用正则或简单判断去掉
                    if u.startswith("http://[") or u.startswith("https://["):
                        continue
                    seen.add(u)
                    filtered.append(u)

                if not filtered:
                    continue

                # 2. 异步并发测速
                async def bound_test(u):
                    async with sem:
                        return await test_url_speed(session, u, timeout)

                tasks = [bound_test(u) for u in filtered]
                results = await asyncio.gather(*tasks)

                # 3. 筛选出成功响应的 URL，并按时间排序
                valid_times = [(u, t) for u, t in results if t is not None]
                if not valid_times:
                    continue

                valid_times.sort(key=lambda x: x[1])  # 按响应时间升序
                # 4. 取前 N 条最快的 URL
                top_n = valid_times[:config.max_links_per_channel]
                sorted_urls = [u for u, _ in top_n]

                new_channels[category][channel_name] = sorted_urls

        return new_channels

def write_to_files(f_m3u, f_txt, category, channel_name, url, index, total):
    """
    生成 #EXTINF 行和 URL（写入 M3U），以及 TXT 行。
    仅保留 IPv4 情况下的拼接后缀：
      - 如果 total == 1，则 $IPV4；
      - 否则 $IPV4•线路{index}。
    """
    # 可选：如果不需要 logo，可以改为 logo_url = ""
    logo_url = f"https://gitee.com/IIII-9306/PAV/raw/master/logos/{channel_name}.png"
    suffix = "$IPV4" if total == 1 else f"$IPV4•线路{index}"
    final_url = f"{url.split('$', 1)[0]}{suffix}"

    # 写 M3U
    f_m3u.write(
        f'#EXTINF:-1 tvg-id="{index}" tvg-name="{channel_name}" tvg-logo="{logo_url}" '
        f'group-title="{category}",{channel_name}\n'
    )
    f_m3u.write(final_url + "\n")
    # 写 TXT
    f_txt.write(f"{channel_name},{final_url}\n")

def write_output_files(channels, template_channels, cache):
    """
    结合已测速并筛选后的 channels（OrderedDict{分类: OrderedDict{频道名: [URL 列表]} }），
    生成以下两个文件：
      - live/live_ipv4.m3u
      - live/live_ipv4.txt
    并记录 URL 的“新增/移除”到 url_changes.log。
    """
    written_urls = set()
    url_changes = {"added": [], "removed": []}

    # 对比缓存，找出“新增/移除” URL
    if is_cache_valid(cache):
        prev_urls = {}
        for uh, entry in cache["urls"].items():
            for cat, lst in entry["channels"].items():
                for name, u in lst:
                    prev_urls[u] = (cat, name)

        curr_urls = {}
        for cat, ch_dict in channels.items():
            for name, urls in ch_dict.items():
                for u in urls:
                    curr_urls[u] = (cat, name)

        for u, info in curr_urls.items():
            if u not in prev_urls:
                url_changes["added"].append((info[0], info[1], u))
        for u, info in prev_urls.items():
            if u not in curr_urls:
                url_changes["removed"].append((info[0], info[1], u))

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    ipv4_m3u_path = os.path.join(output_folder, "live_ipv4.m3u")
    ipv4_txt_path = os.path.join(output_folder, "live_ipv4.txt")

    with open(ipv4_m3u_path, "w", encoding="utf-8") as f_m3u, \
         open(ipv4_txt_path, "w", encoding="utf-8") as f_txt:

        # 写 M3U 头，包含所有 EPG URL
        epg_list = ",".join(f'"{url}"' for url in config.epg_urls)
        f_m3u.write(f'#EXTM3U x-tvg-url={epg_list}\n')

        # 写入公告（Announcements）
        for grp in config.announcements:
            f_txt.write(f"{grp['channel']},#genre#\n")
            for ent in grp['entries']:
                name = ent['name'] or now_str.split(" ")[0]
                url = ent['url']
                if not is_valid_url(url) or url in written_urls:
                    continue
                written_urls.add(url)
                logo_url = ent.get('logo', "")
                f_m3u.write(
                    f'#EXTINF:-1 tvg-id="1" tvg-name="{name}" tvg-logo="{logo_url}" '
                    f'group-title="{grp["channel"]}",{name}\n'
                )
                f_m3u.write(url + "\n")
                f_txt.write(f"{name},{url}\n")

        # 遍历模板中的分类和频道，写入已筛选的 URL
        for category, tpl_list in template_channels.items():
            f_txt.write(f"{category},#genre#\n")
            if category not in channels:
                continue
            for tpl_name in tpl_list:
                if tpl_name not in channels[category]:
                    continue
                url_list = channels[category][tpl_name]
                total = len(url_list)
                if total == 0:
                    continue
                for idx, u in enumerate(url_list, start=1):
                    if u in written_urls:
                        continue
                    written_urls.add(u)
                    write_to_files(f_m3u, f_txt, category, tpl_name, u, idx, total)

    # 写 URL 变化日志
    if url_changes["added"] or url_changes["removed"]:
        log_path = os.path.join(output_folder, "url_changes.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n=== 更新时间: {now_str} ===\n")
            if url_changes["added"]:
                f.write("新增 URL:\n")
                for cat, name, u in url_changes["added"]:
                    f.write(f"- {cat} - {name}: {u}\n")
            if url_changes["removed"]:
                f.write("移除 URL:\n")
                for cat, name, u in url_changes["removed"]:
                    f.write(f"- {cat} - {name}: {u}\n")

async def main():
    """
    主流程：
    1. 解析模板（demo.txt）；
    2. 并发抓取各流源并合并 → matched_channels；
    3. 对每个频道 URL 列表并发测速 → 得到前 N 条最快的 URL；
    4. 写入最终的 M3U / TXT 文件，并记录 URL 变化日志。
    """
    template_file = "demo.txt"
    if not os.path.exists(template_file):
        print(f"错误: 找不到模板文件 '{template_file}'，请确保存在。")
        print("demo.txt 示例内容：\n"
              "央视,#genre#\n"
              "CCTV-1\n"
              "CCTV-2\n"
              "卫视,#genre#\n"
              "北京卫视\n"
              "上海卫视\n")
        return

    try:
        # 1. 并发抓取并匹配
        matched_blacklist, template_channels, cache = await filter_source_urls(template_file)

        # 2. 并发测速选出每频道最快前 N 条
        channels_ranked = await rank_channel_urls(matched_blacklist)

        # 3. 同步写出文件
        write_output_files(channels_ranked, template_channels, cache)

        print("操作完成！结果已保存到 live/live_ipv4.m3u 和 live/live_ipv4.txt。")
    except Exception as e:
        print(f"执行过程中发生错误: {e}")
        logging.error(f"程序运行失败: {e}")

if __name__ == "__main__":
    # 以 asyncio.run 启动主流程
    asyncio.run(main())
