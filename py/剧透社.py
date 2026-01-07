import sys
import json
import re
import time
import random
import requests
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def __init__(self):
        self.name = "剧透社"
        self.host = "https://1.star2.cn"
        self.timeout = 10000  # 延长超时时间
        self.limit = 20
        # 增强请求头，模拟真实浏览器
        self.headers = {
            "User-Agent": random.choice([
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0"
            ]),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": f"{self.host}/",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0"
        }
        self.default_image = "https://images.gamedog.cn/gamedog/imgfile/20241205/05105843u5j9.png"
        # 创建会话保持
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def getName(self):
        return self.name
    
    def init(self, extend=""):
        print(f"============{extend}============")
        # 初始化时先获取首页Cookie
        try:
            self.session.get(self.host, timeout=self.timeout/1000)
            time.sleep(random.uniform(1, 2))  # 初始延迟
        except Exception as e:
            print(f"初始化会话失败: {e}")
    
    def homeContent(self, filter):
        return {
            'class': [
                {"type_name": "国剧", "type_id": "ju"},
                {"type_name": "电影", "type_id": "mv"},
                {"type_name": "动漫", "type_id": "dm"},
                {"type_name": "短剧", "type_id": "dj"},
                {"type_name": "综艺", "type_id": "zy"},
                {"type_name": "韩日", "type_id": "rh"},
                {"type_name": "英美", "type_id": "ym"},
                {"type_name": "外剧", "type_id": "wj"}
            ]
        }
    
    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        url = f"{self.host}/{tid}/" if pg == 1 else f"{self.host}/{tid}/?page={pg}"
        
        try:
            # 添加随机延迟，避免请求过于频繁
            time.sleep(random.uniform(1.5, 3.5))
            rsp = self.fetch(url)
            if rsp:
                videos = self._parse_video_list(rsp.text)
                result.update({
                    'list': videos,
                    'page': pg,
                    'pagecount': 9999,
                    'limit': self.limit,
                    'total': 999999
                })
        except Exception as e:
            print(f"Category parse error: {e}")
            
        return result
    
    def _parse_video_list(self, html_text):
        videos = []
        
        def build_full_url(href):
            if href.startswith("http"):
                return href
            return f"{self.host}{href}" if href.startswith("/") else f"{self.host}/{href}"
        
        try:
            # 优化正则表达式，适应可能的HTML结构变化
            pattern = r'<li[^>]*>.*?<a[^>]*href="([^"]+)"[^>]*class="main"[^>]*>(.*?)</a>.*?</li>'
            for match in re.finditer(pattern, html_text, re.S):
                href = match.group(1).strip()
                name = match.group(2).strip()
                
                if href and name and href.startswith("/"):
                    cleaned_name = re.sub(r'^【[^】]*】', '', name).strip()
                    final_name = cleaned_name if cleaned_name else name
                    videos.append({
                        "vod_id": build_full_url(href),
                        "vod_name": final_name,
                        "vod_pic": self.default_image,
                        "vod_remarks": "",
                        "vod_content": final_name
                    })
        except Exception as e:
            print(f"Parse video list error: {e}")
        
        return videos
    
    def detailContent(self, array):
        result = {'list': []}
        if array:
            max_retries = 2
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    vod_id = array[0]
                    detail_url = vod_id if vod_id.startswith("http") else f"{self.host}{vod_id}"
                    time.sleep(random.uniform(1, 2) * (retry_count + 1))  # 重试时增加延迟
                    rsp = self.fetch(detail_url)
                    
                    if rsp and rsp.status_code == 200:
                        vod = self._parse_detail_page(rsp.text, detail_url)
                        if vod and vod.get("vod_play_url", "") != "暂无资源$#":
                            result['list'] = [vod]
                            break
                    
                    retry_count += 1
                except Exception as e:
                    print(f"Detail parse error (attempt {retry_count + 1}): {e}")
                    retry_count += 1
            
            # 如果重试后仍然失败，返回空结果
            if not result['list']:
                print(f"无法获取详情页内容: {array[0]}")
        
        return result
    
    def _parse_detail_page(self, html_text, detail_url):
        try:
            title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html_text, re.S)
            title = title_match.group(1).strip() if title_match else "未知标题"
            title = re.sub(r'^【[^】]+】', '', title).strip() or "未知标题"
            
            # 增强链接提取，支持更多网盘链接格式
            play_links = []
            # 扩展链接匹配模式，增加对更多网盘链接的识别
            link_patterns = [
                r'href="(https?://[^\s"]+?(?:pan\.baidu\.com|yun\.baidu\.com)[^\s"]*)"',
                r'href="(https?://[^\s"]+?pan\.quark\.cn[^\s"]*)"',
                r'href="(https?://[^\s"]+?aliyundrive\.com[^\s"]*)"',
                r'href="(https?://[^\s"]+?cloud\.189\.cn[^\s"]*)"',
                r'href="(https?://[^\s"]+?pan\.xunlei\.com[^\s"]*)"',
                r'href="(https?://[^\s"]+?lanzou[^\s"]*)"',
                r'href="(https?://[^\s"]+?123pan\.com[^\s"]*)"',
                r'提取码[：:]\s*\w{4}\s*链接[：:]\s*(https?://[^\s"]+)',
                r'链接[：:]\s*(https?://[^\s"]+)\s*提取码[：:]\s*\w{4}',
                # 通用匹配
                r'href="(https?://[^\s"]+?(?:百度|夸克|阿里云|天翼|迅雷|蓝奏|123|城通|微云)[^\s"]*)"'
            ]
            
            for pattern in link_patterns:
                for match in re.finditer(pattern, html_text, re.I | re.S):
                    href = match.group(1)
                    if href and href not in play_links:
                        # 清洗链接，移除可能的HTML标签
                        href = re.sub(r'["\'<>]', '', href.strip())
                        if self._validate_link(href):
                            play_links.append(href)
            
            # 处理播放链接格式
            if play_links:
                play_url = "#".join([
                    f"百度网盘${link}" if "baidu" in link else
                    f"夸克网盘${link}" if "quark" in link else
                    f"阿里云盘${link}" if "aliyun" in link else
                    f"天翼云盘${link}" if "189.cn" in link else
                    f"迅雷云盘${link}" if "xunlei" in link else
                    f"蓝奏云${link}" if "lanzou" in link else
                    f"123云盘${link}" if "123pan" in link else
                    f"城通网盘${link}" if "ctfile" in link else
                    f"微云${link}" if "weiyun" in link else
                    f"其他网盘${link}"
                    for link in play_links
                ])
            else:
                play_url = "暂无资源$#"
            
            play_from = "剧透社" if play_links else "无资源"
            
            return {
                "vod_id": detail_url,
                "vod_name": title,
                "vod_pic": self.default_image,
                "vod_content": title,
                "vod_remarks": "",
                "vod_play_from": play_from,
                "vod_play_url": play_url
            }
        except Exception as e:
            print(f"Parse detail page error: {e}")
            return {
                "vod_id": detail_url,
                "vod_name": "未知标题",
                "vod_pic": self.default_image,
                "vod_content": f"加载详情页失败：{str(e)}",
                "vod_remarks": "",
                "vod_play_from": "无资源",
                "vod_play_url": "暂无资源$#"
            }
    
    def _validate_link(self, url):
        """验证链接是否有效"""
        try:
            if not url.startswith(('http://', 'https://')):
                return False
            
            # 检查是否是支持的网盘链接
            supported_domains = [
                'pan.baidu.com', 'yun.baidu.com', 
                'pan.quark.cn', 'aliyundrive.com',
                'cloud.189.cn', 'pan.xunlei.com',
                'lanzou.com', 'lanzouv.com', 'lanzoux.com',
                '123pan.com', 'ctfile.com', 'share.weiyun.com',
                'weiyun.com'
            ]
            
            for domain in supported_domains:
                if domain in url:
                    return True
            return False
        except:
            return False
    
    def searchContent(self, key, quick, pg):
        result = {'list': []}
        try:
            url = f"{self.host}/search/?keyword={key}"
            time.sleep(random.uniform(1, 2))
            rsp = self.fetch(url)
            if rsp:
                result['list'] = self._parse_video_list(rsp.text)
        except Exception as e:
            print(f"Search error: {e}")
        return result
    
    def playerContent(self, flag, id, vipFlags):
        # 处理 push:// 协议的情况
        if id.startswith("push://"):
            return {
                "parse": 0,
                "playUrl": "",
                "url": id.replace("push://", ""),  # 移除 push:// 前缀
                "header": json.dumps(self._get_player_headers())
            }
        
        # 对于普通链接，确保正确的格式
        play_url = id
        if not play_url.startswith(("http://", "https://")):
            play_url = f"https://{play_url}" if not play_url.startswith("//") else f"https:{play_url}"
        
        return {
            "parse": 0,  # 使用直连播放
            "playUrl": "",
            "url": play_url,
            "header": json.dumps(self._get_player_headers())
        }
    
    def _get_player_headers(self):
        """获取播放器专用头部信息"""
        return {
            **dict(self.session.headers),
            "User-Agent": random.choice([
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0"
            ]),
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": f"{self.host}/",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "video",
            "Sec-Fetch-Mode": "no-cors",
            "Sec-Fetch-Site": "cross-site",
            "Origin": f"{self.host}"
        }
    
    # 重写fetch方法，使用会话请求并处理反爬
    def fetch(self, url):
        try:
            # 随机更换User-Agent
            self.session.headers["User-Agent"] = random.choice([
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0"
            ])
            
            response = self.session.get(
                url,
                timeout=self.timeout/1000,
                verify=False,  # 跳过SSL验证（根据实际情况调整）
                allow_redirects=True
            )
            response.encoding = response.apparent_encoding  # 自动识别编码
            if response.status_code == 200:
                return response
            elif response.status_code in [403, 503]:
                print(f"被反爬拦截，状态码: {response.status_code}，尝试重试...")
                # 遇到反爬时延迟后重试一次
                time.sleep(random.uniform(3, 5))
                return self.fetch(url)
            else:
                print(f"请求失败，状态码: {response.status_code}")
                return None
        except Exception as e:
            print(f"请求异常: {e}")
            return None
