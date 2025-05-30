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
    from aiohttp import ClientSSLError
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
    if config.ip_version_priority not in ("ipv4", "ipv6"):
        raise AttributeError("ip_version_priority 必须为 'ipv4' 或 'ipv6'")
except ImportError:
    print("错误: 找不到配置模块 'config.py'。请参考示例创建一个。")
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
                current_category = line.split(",")[0].strip()
                template_channels[current_category] = []
            elif current_category:
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


def is_ipv6(url):
    """
    简单判断 URL 是否为 IPv6
    （通常 IPv6 URL 形如 http://[2001:db8::1]/xxx）
    """
    return bool(re.match(r'^https?://\[[0-9a-fA-F:]+\]', url))


async def fetch_channels(session, url, cache):
    """
    异步请求并解析单个源 URL，返回 OrderedDict{分类: [(频道名, URL), ...], ...}。
    - 带统一请求头；
    - 捕获 401/403 直接跳过；
    - 对 Connection reset 和 SSL 错误做简单重试（最多 2 次）。
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
                channels = OrderedDict(entry["channels"])
                unique_urls = set(entry["unique_urls"])
                cache_hit = True
            except Exception:
                cache_hit = False

    if not cache_hit:
        common_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/112.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9"
            # 如果需要 Referer 或 Cookie，可在 config.py 中设置后放进来
        }

        max_retries = 2
        for attempt in range(max_retries):
            try:
                async with session.get(url, headers=common_headers, timeout=10) as resp:
                    if resp.status in (401, 403):
                        logging.error(f"[抓取失败-权限受限] URL={url}, Status={resp.status}")
                        return channels

                    resp.raise_for_status()
                    text = await resp.text()
                    lines = text.split("\n")
                    is_m3u = any(line.startswith("#EXTINF") for line in lines[:15])
                    if is_m3u:
                        parsed = parse_m3u_lines(lines, unique_urls)
                    else:
                        parsed = parse_txt_lines(lines, unique_urls)

                    if parsed:
                        channels = parsed
                        cache["urls"][url_hash] = {
                            "url": url,
                            "channels": dict(channels),
                            "unique_urls": list(unique_urls),
                            "timestamp": datetime.now().isoformat(),
                            "content_hash": calculate_hash(text)
                        }
                        save_cache(cache)
                    return channels

            except ClientSSLError as ssl_err:
                logging.error(f"[抓取失败-SSL错误] URL={url}, Error={ssl_err}")
                # 不再重试，直接跳过
                return channels
            except aiohttp.ClientResponseError as cre:
                logging.error(f"[抓取失败-HTTP错误] URL={url}, Status={cre.status}, Message={cre.message}")
                return channels
            except aiohttp.client_exceptions.ClientConnectionError as cce:
                # Connection reset, 可能重试
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                logging.error(f"[抓取失败-连接错误] URL={url}, Error={cce}")
                return channels
            except asyncio.TimeoutError:
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                logging.error(f"[抓取失败-超时] URL={url}")
                return channels
            except Exception as e:
                logging.error(f"[抓取失败-未知错误] URL={url}, Error={e}")
                return channels

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
            match = re.search(r'group-title="(.*?)",(.*)', line)
            if match:
                current_category = match.group(1).strip()
                name = match.group(2).strip()
                name = clean_channel_name(name) if name else name
                current_channel_name = name
                if current_category not in channels:
                    channels[current_category] = []
        elif line and not line.startswith("#"):
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
            current_category = line.split(",")[0].strip()
            channels[current_category] = []
        elif current_category:
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
                name = clean_channel_name(line)
                channels[current_category].append((name, ""))
    return channels


def find_similar_name(target_name, name_list):
    matches = difflib.get_close_matches(target_name, name_list, n=1, cutoff=0.6)
    return matches[0] if matches else None


def merge_channels(target, source):
    for category, lst in source.items():
        if category in target:
            target[category].extend(lst)
        else:
            target[category] = lst


async def filter_source_urls(template_file):
    template_channels = parse_template(template_file)
    source_urls = config.source_urls
    cache = load_cache()

    all_channels = OrderedDict()
    # 创建 ClientSession 时禁用 SSL 验证
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch_channels(session, url, cache) for url in source_urls]
        results = await asyncio.gather(*tasks)

    for fetched in results:
        merge_channels(all_channels, fetched)

    all_online_names = []
    for cat, lst in all_channels.items():
        for name, _ in lst:
            all_online_names.append(name)
    all_online_names = list(set(all_online_names))

    matched = OrderedDict()
    for cat, channel_list in template_channels.items():
        matched[cat] = OrderedDict()
        for tpl_name in channel_list:
            clean_tpl = clean_channel_name(tpl_name)
            sim = find_similar_name(clean_tpl, [clean_channel_name(n) for n in all_online_names])
            if not sim:
                continue
            orig_name = next((n for n in all_online_names if clean_channel_name(n) == sim), None)
            if not orig_name:
                continue
            for online_cat, lst in all_channels.items():
                for online_name, url in lst:
                    if online_name == orig_name:
                        matched[cat].setdefault(tpl_name, []).append(url)

    return matched, template_channels, cache


async def test_url_speed(session, url, timeout):
    """
    对单个 URL 发起 HEAD 请求测时延，带上常见请求头。
    """
    start = time.monotonic()
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/112.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9"
        }
        try:
            async with session.head(url, headers=headers, timeout=timeout) as resp:
                resp.raise_for_status()
            elapsed = time.monotonic() - start
            return url, elapsed
        except Exception:
            # 捕获包括超时、SSL、连接重置等所有异常，返回 None 表示测速失败
            return url, None
    except Exception:
        # 任何意外也返回 None，避免未捕获的 Future 异常
        return url, None


async def rank_channel_urls(channels_raw):
    timeout = config.speed_test_timeout
    sem = asyncio.Semaphore(config.speed_test_concurrency)

    # 同样在这里禁用 SSL 验证
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        new_channels = OrderedDict()
        for category, ch_dict in channels_raw.items():
            new_channels[category] = OrderedDict()
            for channel_name, url_list in ch_dict.items():
                ipv4_candidates = []
                ipv6_candidates = []
                seen = set()
                for u in url_list:
                    if not is_valid_url(u):
                        continue
                    if u in seen:
                        continue
                    seen.add(u)
                    if any(bad in u for bad in config.url_blacklist):
                        continue
                    if is_ipv6(u):
                        ipv6_candidates.append(u)
                    else:
                        ipv4_candidates.append(u)

                if not ipv4_candidates and not ipv6_candidates:
                    continue

                async def bound_test(u):
                    async with sem:
                        return await test_url_speed(session, u, timeout)

                ipv4_results = []
                if ipv4_candidates:
                    tasks4 = [bound_test(u) for u in ipv4_candidates]
                    res4 = await asyncio.gather(*tasks4)
                    ipv4_results = [(u, t) for u, t in res4 if t is not None]
                    ipv4_results.sort(key=lambda x: x[1])

                ipv6_results = []
                if ipv6_candidates:
                    tasks6 = [bound_test(u) for u in ipv6_candidates]
                    res6 = await asyncio.gather(*tasks6)
                    ipv6_results = [(u, t) for u, t in res6 if t is not None]
                    ipv6_results.sort(key=lambda x: x[1])

                N = config.max_links_per_channel
                merged = []
                if config.ip_version_priority == "ipv4":
                    merged += [u for u, _ in ipv4_results]
                    merged += [u for u, _ in ipv6_results]
                else:
                    merged += [u for u, _ in ipv6_results]
                    merged += [u for u, _ in ipv4_results]
                final_list = merged[:N]

                if final_list:
                    new_channels[category][channel_name] = final_list

        return new_channels


def write_to_files(f_m3u, f_txt, category, channel_name, url, index, total):
    logo_url = f"https://gitee.com/IIII-9306/PAV/raw/master/logos/{channel_name}.png"
    if is_ipv6(url):
        suffix = "$IPV6" if total == 1 else f"$IPV6•线路{index}"
    else:
        suffix = "$IPV4" if total == 1 else f"$IPV4•线路{index}"
    final_url = f"{url.split('$', 1)[0]}{suffix}"

    f_m3u.write(
        f'#EXTINF:-1 tvg-id="{index}" tvg-name="{channel_name}" tvg-logo="{logo_url}" '
        f'group-title="{category}",{channel_name}\n'
    )
    f_m3u.write(final_url + "\n")
    f_txt.write(f"{channel_name},{final_url}\n")


def write_output_files(channels, template_channels, cache):
    written_urls = set()
    url_changes = {"added": [], "removed": []}

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

    m3u_path = os.path.join(output_folder, "live.m3u")
    txt_path = os.path.join(output_folder, "live.txt")

    with open(m3u_path, "w", encoding="utf-8") as f_m3u, \
         open(txt_path, "w", encoding="utf-8") as f_txt:

        epg_list = ",".join(f'"{url}"' for url in config.epg_urls)
        f_m3u.write(f'#EXTM3U x-tvg-url={epg_list}\n')

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
        matched_raw, template_channels, cache = await filter_source_urls(template_file)
        channels_ranked = await rank_channel_urls(matched_raw)
        write_output_files(channels_ranked, template_channels, cache)
        print("操作完成！结果已保存到 live/live.m3u 和 live/live.txt。")
    except Exception as e:
        print(f"执行过程中发生错误: {e}")
        logging.error(f"程序运行失败: {e}")


if __name__ == "__main__":
    asyncio.run(main())
