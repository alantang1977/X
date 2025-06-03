import asyncio
import aiohttp
import time

# 对单个URL测速，返回(频道名, url, 响应耗时)
async def test_url(session, channel_name, url, timeout=3):
    try:
        start = time.monotonic()
        async with session.head(url, timeout=timeout) as resp:
            if resp.status == 200:
                cost = time.monotonic() - start
                return (channel_name, url, cost, True)
    except Exception:
        pass
    return (channel_name, url, None, False)

# 对所有频道源批量测速，返回测速结果
async def test_all_channel_urls(channel_urls_dict, test_timeout=3, concurrency=30):
    """
    channel_urls_dict: {channel_name: [url1, url2, ...]}
    返回: {channel_name: [(url, cost), ...]}，已按响应耗时升序，失效源不包含
    """
    result = {}
    semaphore = asyncio.Semaphore(concurrency)
    async with aiohttp.ClientSession() as session:
        tasks = []
        for channel, urls in channel_urls_dict.items():
            for url in urls:
                async def sem_test_url(channel=channel, url=url):
                    async with semaphore:
                        return await test_url(session, channel, url, test_timeout)
                tasks.append(sem_test_url())
        all_ping = await asyncio.gather(*tasks)
    # 聚合结果
    for channel, url, cost, ok in all_ping:
        if ok:
            result.setdefault(channel, []).append((url, cost))
    # 按响应耗时排序
    for channel in result:
        result[channel].sort(key=lambda x: x[1])
    return result
