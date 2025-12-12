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
            try:
                vod_id = array[0]
                detail_url = vod_id if vod_id.startswith("http") else f"{self.host}{vod_id}"
                time.sleep(random.uniform(1, 2))  # 详情页请求延迟
                rsp = self.fetch(detail_url)
                if rsp:
                    vod = self._parse_detail_page(rsp.text, detail_url)
                    if vod:
                        result['list'] = [vod]
            except Exception as e:
                print(f"Detail parse error: {e}")
        return result
    
    def _parse_detail_page(self, html_text, detail_url):
        try:
            title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html_text, re.S)
            title = title_match.group(1).strip() if title_match else "未知标题"
            title = re.sub(r'^【[^】]+】', '', title).strip() or "未知标题"
            
            # 优化资源链接提取规则，支持更多网盘链接识别
            play_links = []
            # 扩展链接匹配模式，支持更多可能的网盘链接格式
            link_pattern = r'<a[^>]*href="(https?://[^\s"]+?)"[^>]*>(?:百度|夸克|阿里云|天翼|迅雷|蓝奏|123|城通|微云)[^<]*</a>|href="(https?://[^\s"]+?)"'
            for match in re.finditer(link_pattern, html_text, re.I | re.S):
                # 提取匹配到的链接（处理两个捕获组的情况）
                href = match.group(1) if match.group(1) else match.group(2)
                if href:
                    # 过滤无效链接
                    if any(domain in href for domain in [
                        "pan.baidu.com", "pan.quark.cn", "aliyundrive.com",
                        "cloud.189.cn", "pan.xunlei.com", "lanzou.com",
                        "123pan.com", "ctfile.com", "share.weiyun.com"
                    ]):
                        play_links.append(href)
            
            # 完善网盘类型识别逻辑，支持更多网盘类型
            play_url = "#".join([
                f"百度${link}" if "pan.baidu.com" in link else
                f"夸克${link}" if "pan.quark.cn" in link else
                f"阿里云${link}" if "aliyundrive.com" in link else
                f"天翼云${link}" if "cloud.189.cn" in link else
                f"迅雷${link}" if "pan.xunlei.com" in link else
                f"蓝奏云${link}" if "lanzou.com" in link else
                f"123云${link}" if "123pan.com" in link else
                f"城通${link}" if "ctfile.com" in link else
                f"微云${link}" if "share.weiyun.com" in link else
                f"其他网盘${link}"
                for link in play_links
            ]) or "暂无资源$#"
            
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
        if id.startswith("push://"):
            return {"parse": 0, "playUrl": "", "url": id, "header": ""}
        return {
            "parse": 0,
            "playUrl": "",
            "url": f"push://{id}",
            "header": json.dumps(dict(self.session.headers))  # 使用会话 headers
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
