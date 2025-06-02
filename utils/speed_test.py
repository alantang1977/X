import asyncio
import time
import aiohttp

async def test_url(url, timeout=10):
    """
    测试单个URL的响应速度。
    返回：(耗时秒, 是否可用)
    """
    start = time.monotonic()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=timeout) as resp:
                if resp.status == 200:
                    await resp.read(32)  # 只读一点点数据
                    return (time.monotonic() - start, True)
                else:
                    return (float('inf'), False)
    except Exception:
        return (float('inf'), False)

async def speed_test_channels(channels, timeout=3, max_concurrent=10):
    """
    对 channels 结构（OrderedDict{分类: {频道名: [url, ...]}}）中的所有URL进行测速。
    返回：{url: (耗时, 是否可用)}
    """
    # 收集所有url
    all_urls = []
    for category in channels.values():
        for urls in category.values():
            all_urls.extend(urls)
    all_urls = list(set(all_urls))  # 去重

    # 并发测速
    sem = asyncio.Semaphore(max_concurrent)
    results = {}

    async def sem_test(url):
        async with sem:
            results[url] = await test_url(url, timeout=timeout)

    tasks = [asyncio.create_task(sem_test(url)) for url in all_urls]
    await asyncio.gather(*tasks)
    return results
