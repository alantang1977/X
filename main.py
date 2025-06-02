import os
import sys
import logging
import json
import aiohttp
import asyncio
import traceback
from collections import OrderedDict
from datetime import datetime

import warnings
warnings.filterwarnings("ignore", message="Can not load response cookies: Illegal key")

try:
    import config
except ImportError:
    print("Error: Missing 'config.py'.")
    sys.exit(1)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "utils"))
try:
    import parser
    import speed_test
except ImportError:
    print("Error: Missing required modules in 'utils'.")
    sys.exit(1)

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

def validate_template(template_file):
    """Validate the template file."""
    if not os.path.exists(template_file):
        logging.error(f"Template file '{template_file}' not found.")
        return None
    with open(template_file, "r", encoding="utf-8") as f:
        content = f.read()
    if not content.strip():
        logging.error("Template file is empty.")
        return None
    return parser.parse_template(template_file)

def validate_source_urls(urls):
    """Validate source URLs."""
    valid_urls = []
    for url in urls:
        if url.startswith(("http://", "https://")):
            valid_urls.append(url)
        else:
            logging.warning(f"Invalid URL skipped: {url}")
    return valid_urls

def load_cache():
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Failed to load cache: {e}")
    return {"urls": {}, "timestamp": datetime.now().isoformat()}

def save_cache(cache):
    cache["timestamp"] = datetime.now().isoformat()
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Failed to save cache: {e}")

async def fetch_channels(session, url, cache, retry_times=3, retry_delay=2):
    """Fetch channels asynchronously."""
    url_hash = parser.calculate_hash(url)
    if url_hash in cache["urls"]:
        cached_entry = cache["urls"][url_hash]
        timestamp = cached_entry.get("timestamp", datetime.now().isoformat())
        elapsed = (datetime.now() - datetime.fromisoformat(timestamp)).total_seconds() / (3600 * 24)
        if elapsed < cache_valid_days:
            logging.info(f"Loaded from cache: {url}")
            return OrderedDict(cached_entry["channels"])
    headers = {"User-Agent": "okhttp"}
    attempt = 0
    while attempt < retry_times:
        try:
            async with session.get(url, headers=headers, timeout=getattr(config, "fetch_url_timeout", 10)) as response:
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
        except Exception as e:
            attempt += 1
            logging.warning(f"URL: {url}, Attempt {attempt}/{retry_times}: {e}")
            if attempt < retry_times:
                await asyncio.sleep(retry_delay)
    logging.error(f"Failed to fetch URL: {url}")
    return OrderedDict()

def write_final_files(merged_channels, speed_map, output_folder):
    """Write final output files."""
    txt_path = os.path.join(output_folder, "output.txt")
    m3u_path = os.path.join(output_folder, "output.m3u")
    total_lines = 0
    with open(txt_path, "w", encoding="utf-8") as f:
        for category, chans in merged_channels.items():
            if not chans: continue
            f.write(f'[{category}]\n')
            for channel_name, urls in chans.items():
                if not urls: continue
                urls_sorted = sorted(urls, key=lambda u: speed_map.get(u, (float('inf'), False))[0])
                for url in urls_sorted:
                    f.write(f"{channel_name},{url}\n")
                    total_lines += 1
    with open(m3u_path, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for category, chans in merged_channels.items():
            if not chans: continue
            f.write(f"#------ {category} ------\n")
            for channel_name, urls in chans.items():
                if not urls: continue
                urls_sorted = sorted(urls, key=lambda u: speed_map.get(u, (float('inf'), False))[0])
                for url in urls_sorted:
                    f.write(f'#EXTINF:-1 group-title="{category}",{channel_name}\n')
                    f.write(f"{url}\n")
    print(f"Successfully wrote output.txt and output.m3u with {total_lines} channels.")

async def main():
    template_file = "demo.txt"
    template_channels = validate_template(template_file)
    if not template_channels:
        return
    source_urls = validate_source_urls(getattr(config, "source_urls", []))
    if not source_urls:
        logging.error("No valid source URLs found.")
        return
    cache = load_cache()
    all_channels = OrderedDict()
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_channels(session, url, cache) for url in source_urls]
        results = await asyncio.gather(*tasks)
        for idx, channels in enumerate(results):
            if channels:
                parser.merge_channels(all_channels, channels)
    speed_map = await speed_test.speed_test_channels(
        all_channels, timeout=getattr(config, "speed_test_timeout", 3),
        max_concurrent=getattr(config, "max_concurrent_speed_tests", 10)
    )
    write_final_files(all_channels, speed_map, output_folder)

if __name__ == "__main__":
    asyncio.run(main())
