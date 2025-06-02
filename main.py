import os
import sys
import logging
import json
import aiohttp
import asyncio
import traceback
from collections import OrderedDict
from datetime import datetime

# 全局抑制 aiohttp cookies 警告
import warnings
warnings.filterwarnings("ignore", message="Can not load response cookies: Illegal key")

try:
    import config
except ImportError:
    print("错误: 找不到配置模块 'config.py'")
    sys.exit(1)

# 导入模块化功能（从utils文件夹）
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "utils"))
import parser
import speed_test

# 日志设置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("./live/function.log", "w", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

output_folder = "live"
os.makedirs(output_folder, exist_ok=True)
cache_folder = "./live/cache"
os.makedirs(cache_folder, exist_ok=True)
cache_file = os.path.join(cache_folder, "url_cache.json")
cache_valid_days = getattr(config, "cache_valid_days", 1)

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

async def fetch_channels(session, url, cache, retry_times=3, retry_delay=2):
    from aiohttp import ClientError
    url_hash = parser.calculate_hash(url)
    if url_hash in cache["urls"]:
        cached_entry = cache["urls"][url_hash]
        timestamp = cached_entry.get("timestamp", datetime.now().isoformat())
        elapsed = (datetime.now() - datetime.fromisoformat(timestamp)).total_seconds() / (3600 * 24)
        if elapsed < cache_valid_days:
            logging.info(f"从缓存加载: {url}")
            return OrderedDict(cached_entry["channels"])

    headers = {"User-Agent": "okhttp"}

    attempt = 0
    while attempt < retry_times:
        try:
            async with session.get(
                url, headers=headers, timeout=getattr(config, "fetch_url_timeout", 10)
            ) as response:
                response.raise_for_status()
                content = await response.text()
                channels = parser.parse_channels_auto(content)
                if channels:
                    cache["urls"][url_hash] = {
                        "url": url,
                        "channels": dict(channels),
                        "timestamp": datetime.now().isoformat(),
                        "content_hash": parser.calculate_hash(content)
                    }
                    save_cache(cache)
                return channels
        except asyncio.TimeoutError:
            attempt += 1
            logging.warning(
                f"url: {url} 请求超时({attempt}/{retry_times})，请检查目标服务器或增大超时时间（当前{getattr(config, 'fetch_url_timeout', 10)}秒）"
            )
        except ClientError as e:
            attempt += 1
            logging.warning(f"url: {url} 客户端异常({attempt}/{retry_times}), Error: {repr(e)}")
        except Exception as e:
            attempt += 1
            logging.warning(
                f"url: {url} 其它异常({attempt}/{retry_times}), Error: {repr(e)}\nTraceback:\n{traceback.format_exc()}"
            )
        if attempt < retry_times:
            await asyncio.sleep(retry_delay)
    logging.error(f"url: {url} 跳过，重试多次仍失败")
    return OrderedDict()

def print_report(success_urls, failed_urls):
    logging.info(f"采集成功源站数量: {len(success_urls)}")
    logging.info(f"采集失败源站数量: {len(failed_urls)}")
    if failed_urls:
        logging.info("失败源站清单:")
        for url in failed_urls:
            logging.info(f"  - {url}")

def filter_channels_by_template(merged_channels, template_channels):
    """
    只保留demo.txt（模板）中出现的分类和频道
    """
    filtered = OrderedDict()
    # 解析模板可用频道
    template_map = OrderedDict()
    for category, channels in template_channels.items():
        template_map[category] = set()
        for channel_name, url in channels:
            template_map[category].add(channel_name.strip())
    # 过滤主频道
    for category in merged_channels:
        if category not in template_map:
            continue
        for channel_name in merged_channels[category]:
            if channel_name in template_map[category]:
                if category not in filtered:
                    filtered[category] = OrderedDict()
                filtered[category][channel_name] = merged_channels[category][channel_name]
    return filtered

async def main(template_file):
    template_channels = parser.parse_template(template_file)
    source_urls = getattr(config, "source_urls", [])
    cache = load_cache()

    all_channels = OrderedDict()
    failed_urls = []
    success_urls = []
    async with aiohttp.ClientSession() as session:
        fetch_tasks = [fetch_channels(session, url, cache) for url in source_urls]
        results = await asyncio.gather(*fetch_tasks)
        for idx, fetched_channels in enumerate(results):
            if fetched_channels:
                parser.merge_channels(all_channels, fetched_channels)
                success_urls.append(source_urls[idx])
            else:
                failed_urls.append(source_urls[idx])

    print_report(success_urls, failed_urls)

    # 合并模板与抓取，并去重/规范化
    merged_channels = parser.merge_with_template(all_channels, template_channels)
    parser.deduplicate_and_alias_channels(merged_channels)

    # 只保留模板里的分类和频道
    merged_channels = filter_channels_by_template(merged_channels, template_channels)

    # 提取所有url，对最终输出内容测速并排序
    print("开始对所有频道的所有地址进行实际测速，请稍候……")
    speed_map = await speed_test.speed_test_channels(
        merged_channels,
        timeout=getattr(config, "speed_test_timeout", 3),
        max_concurrent=getattr(config, "max_concurrent_speed_tests", 10)
    )
    print("测速完成，正在基于测速结果排序并生成最终输出文件……")

    parser.optimize_and_output_files(merged_channels, speed_map, output_folder)
    print("操作完成！结果已保存到live文件夹。")
    if failed_urls:
        print(f"采集失败源站数量: {len(failed_urls)}，请检查日志 function.log")

if __name__ == "__main__":
    template_file = "demo.txt"
    try:
        if not os.path.exists(template_file):
            print(f"错误: 找不到模板文件 '{template_file}'。")
            print("请确保项目目录下有 demo.txt 文件。")
            sys.exit(1)
        asyncio.run(main(template_file))
    except Exception as e:
        print(f"执行过程中发生错误: {e}")
        logging.error(f"程序运行失败: {e}")
