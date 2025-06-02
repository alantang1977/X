import asyncio

async def speed_test_channels(merged_channels, timeout=3, max_concurrent=10):
    # 假测速：全部返回无限大+False（无效）
    urls = []
    for category in merged_channels:
        for channel in merged_channels[category]:
            urls.extend(merged_channels[category][channel])
    return {u: (float('inf'), False) for u in urls}
