"""
异步测速模块
使用aiohttp实现高性能批量测速
"""
import aiohttp
import asyncio
from dataclasses import dataclass
from config import config
import m3u8  # 需要安装m3u8库

@dataclass
class SpeedTestResult:
    url: str
    latency: int | None       # 响应延迟（毫秒）
    resolution: str           # 流分辨率（如1080p）
    packet_loss: float        # 丢包率（0-1）
    success: bool             # 测速是否成功

async def measure_latency(session: aiohttp.ClientSession, url: str, retry_times: int) -> SpeedTestResult:
    """测量单个URL的延迟和分辨率"""
    start_time = asyncio.get_running_loop().time()
    resolution = await _get_resolution(session, url)
    failures = 0

    for _ in range(retry_times + 1):
        try:
            async with session.head(url, allow_redirects=True, timeout=config.SPEED_TEST["TIMEOUT"]) as resp:
                latency = int((asyncio.get_running_loop().time() - start_time) * 1000)
                packet_loss = failures / (retry_times + 1)
                return SpeedTestResult(url, latency, resolution, packet_loss, True)
        except Exception as e:
            failures += 1

    packet_loss = 1.0
    return SpeedTestResult(url, None, resolution, packet_loss, False)

async def _get_resolution(session: aiohttp.ClientSession, url: str) -> str:
    """从m3u8文件内容解析分辨率"""
    try:
        async with session.get(url) as resp:
            content = await resp.text()
            m3u8_obj = m3u8.loads(content)
            if m3u8_obj.is_variant:
                for playlist in m3u8_obj.playlists:
                    if playlist.stream_info.resolution:
                        width, height = playlist.stream_info.resolution
                        return f"{height}p"
    except Exception as e:
        pass
    return _get_resolution_from_url(url)

def _get_resolution_from_url(url: str) -> str:
    """从URL或流内容解析分辨率（简化实现）"""
    if "1080" in url:
        return "1080p"
    elif "720" in url:
        return "720p"
    elif "480" in url:
        return "480p"
    else:
        return "unknown"

async def batch_speed_test(urls: list[str]) -> list[SpeedTestResult]:
    """批量测速（带并发控制和重试机制）"""
    results = []
    semaphore = asyncio.Semaphore(config.SPEED_TEST["CONCURRENT_LIMIT"])

    async def worker(url):
        nonlocal results
        result = await measure_latency(session, url, config.SPEED_TEST["RETRY_TIMES"])
        results.append(result)

    async with aiohttp.ClientSession() as session:
        tasks = [worker(url) for url in urls]
        await asyncio.gather(*tasks)

    return results

async def multi_node_speed_test(urls: list[str], nodes: list[str]) -> list[SpeedTestResult]:
    """多节点测速"""
    all_results = []
    for node in nodes:
        async with aiohttp.ClientSession(headers={"X-Node": node}) as session:
            results = await batch_speed_test(urls)
            all_results.extend(results)

    # 合并多个节点的结果
    final_results = {}
    for result in all_results:
        if result.url not in final_results:
            final_results[result.url] = result
        else:
            existing_result = final_results[result.url]
            if result.latency is not None and (existing_result.latency is None or result.latency < existing_result.latency):
                final_results[result.url] = result

    return list(final_results.values())
