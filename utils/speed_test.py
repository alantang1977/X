import asyncio
import aiohttp
import time
import logging
import os
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple, Optional

# 配置类
class Config:
    CONCURRENT_LIMIT = 10  # 并发限制
    TIMEOUT = 10  # 超时时间（秒）
    RETRY_TIMES = 3  # 重试次数
    OUTPUT_DIR = "output"  # 输出目录
    LOG_FILE = "speed_test.log"  # 日志文件

config = Config()

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 数据类
@dataclass
class SpeedTestResult:
    url: str
    latency: Optional[float] = None  # 延迟（毫秒）
    resolution: Optional[str] = None  # 分辨率
    success: bool = False  # 是否成功
    error: Optional[str] = None  # 错误信息
    test_time: float = 0  # 测试时间戳

# 速度测试工具类
class SpeedTester:
    def __init__(self):
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=config.TIMEOUT))
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def measure_latency(self, url: str, retry_times: int = 3) -> SpeedTestResult:
        """测量单个URL的延迟和分辨率"""
        result = SpeedTestResult(url=url, test_time=time.time())
        
        for attempt in range(retry_times):
            try:
                start_time = time.time()
                async with self.session.get(url, headers={"User-Agent": "Mozilla/5.0"}) as response:
                    if response.status == 200:
                        # 简单测量响应时间作为延迟
                        latency = (time.time() - start_time) * 1000  # 转换为毫秒
                        
                        # 尝试从响应头或内容中提取分辨率信息（简化处理）
                        resolution = None
                        content_type = response.headers.get("Content-Type", "")
                        if "video" in content_type or "application/vnd.apple.mpegurl" in content_type:
                            # 实际应用中可能需要解析m3u8内容获取分辨率
                            resolution = "unknown"
                        
                        result.latency = latency
                        result.resolution = resolution
                        result.success = True
                        logger.info(f"URL: {url} 测试成功，延迟: {latency:.2f}ms")
                        break
                    else:
                        result.error = f"HTTP状态码: {response.status}"
            except Exception as e:
                result.error = str(e)
                logger.warning(f"URL: {url} 尝试 {attempt+1}/{retry_times} 失败: {e}")
                await asyncio.sleep(1)  # 重试前等待1秒
        
        return result
    
    async def batch_speed_test(self, urls: List[str]) -> List[SpeedTestResult]:
        """批量测速（带并发控制）"""
        results = []
        semaphore = asyncio.Semaphore(config.CONCURRENT_LIMIT)

        async def worker(url):
            nonlocal results
            async with semaphore:
                result = await self.measure_latency(url, config.RETRY_TIMES)
                results.append(result)

        tasks = [worker(url) for url in urls]
        await asyncio.gather(*tasks)
        
        # 按延迟排序结果（升序）
        return sorted(results, key=lambda x: x.latency if x.latency is not None else float('inf'))

# M3U文件处理类
class M3UProcessor:
    @staticmethod
    def parse_m3u(file_path: str) -> List[Tuple[str, str]]:
        """解析M3U文件，返回[(名称, URL), ...]"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            live_sources = []
            current_name = None
            
            for line in lines:
                line = line.strip()
                if line.startswith('#EXTINF:'):
                    # 提取名称
                    name_start = line.find(',') + 1
                    current_name = line[name_start:] if name_start > 0 else "未知频道"
                elif line.startswith('http') and current_name:
                    # 添加到源列表
                    live_sources.append((current_name, line))
                    current_name = None
            
            return live_sources
        except Exception as e:
            logger.error(f"解析M3U文件失败: {e}")
            return []
    
    @staticmethod
    def generate_m3u(live_sources: List[Tuple[str, str]], output_path: str) -> None:
        """生成M3U文件"""
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('#EXTM3U\n')
                for name, url in live_sources:
                    f.write(f'#EXTINF:-1,{name}\n')
                    f.write(f'{url}\n')
            
            logger.info(f"已生成M3U文件: {output_path}")
        except Exception as e:
            logger.error(f"生成M3U文件失败: {e}")

# 主程序
async def main():
    # 输入输出文件路径
    input_file = "input/live_sources.m3u"
    output_file = f"{config.OUTPUT_DIR}/live_sources_sorted_{int(time.time())}.m3u"
    
    # 解析M3U文件
    logger.info(f"开始解析M3U文件: {input_file}")
    m3u_processor = M3UProcessor()
    live_sources = m3u_processor.parse_m3u(input_file)
    
    if not live_sources:
        logger.error("未找到有效的直播源")
        return
    
    logger.info(f"找到 {len(live_sources)} 个直播源")
    
    # 执行速度测试
    logger.info("开始速度测试...")
    async with SpeedTester() as tester:
        urls = [source[1] for source in live_sources]
        results = await tester.batch_speed_test(urls)
    
    # 根据测试结果排序直播源
    url_to_result = {result.url: result for result in results}
    sorted_live_sources = sorted(
        live_sources,
        key=lambda x: url_to_result[x[1]].latency if url_to_result[x[1]].latency is not None else float('inf')
    )
    
    # 生成报告
    success_count = sum(1 for r in results if r.success)
    total_count = len(results)
    
    logger.info(f"速度测试完成: 成功 {success_count}/{total_count}")
    logger.info("前5个最快的直播源:")
    for i, (name, url) in enumerate(sorted_live_sources[:5], 1):
        latency = url_to_result[url].latency
        logger.info(f"{i}. {name} - 延迟: {latency:.2f}ms")
    
    # 生成排序后的M3U文件
    m3u_processor.generate_m3u(sorted_live_sources, output_file)
    
    # 生成速度测试报告
    report_file = f"{config.OUTPUT_DIR}/speed_test_report_{int(time.time())}.txt"
    try:
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("IPTV直播源速度测试报告\n")
            f.write(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"总测试数量: {total_count}\n")
            f.write(f"成功数量: {success_count}\n\n")
            
            f.write("排序后的直播源列表:\n")
            for i, (name, url) in enumerate(sorted_live_sources, 1):
                result = url_to_result[url]
                latency = result.latency if result.latency is not None else "N/A"
                status = "成功" if result.success else f"失败 ({result.error})"
                f.write(f"{i}. {name} - 延迟: {latency}ms - 状态: {status}\n")
        
        logger.info(f"已生成测试报告: {report_file}")
    except Exception as e:
        logger.error(f"生成测试报告失败: {e}")

if __name__ == "__main__":
    asyncio.run(main())    
