import sys
import json
import re
import time
import random
import requests
from urllib.parse import urljoin, urlparse, parse_qs
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def __init__(self):
        self.name = "剧透社"
        self.host = "https://1.star2.cn"
        self.timeout = 15  # 秒
        self.limit = 20
        
        # 增强请求头
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
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.session.verify = False

    def getName(self):
        return self.name
    
    def init(self, extend=""):
        print(f"============{extend}============")
        try:
            self.session.get(self.host, timeout=self.timeout)
            time.sleep(random.uniform(1, 2))
        except Exception as e:
            print(f"初始化会话失败: {e}")
    
    def homeContent(self, filter):
        return {
            'class': [
                {"type_name": "今日更新", "type_id": "xg"},
                {"type_name": "短剧", "type_id": "dj"},
                {"type_name": "国剧", "type_id": "ju"},
                {"type_name": "综艺", "type_id": "zy"},
                {"type_name": "电影", "type_id": "mv"},
                {"type_name": "韩日", "type_id": "rh"},
                {"type_name": "英美", "type_id": "ym"},
                {"type_name": "外剧", "type_id": "wj"},
                {"type_name": "动漫", "type_id": "dm"},
                {"type_name": "其他", "type_id": "qt"}
            ]
        }
    
    def categoryContent(self, tid, pg, filter, extend):
        result = {'list': []}
        try:
            if pg == 1:
                url = f"{self.host}/{tid}/"
            else:
                url = f"{self.host}/{tid}/?page={pg}"
            
            time.sleep(random.uniform(1.5, 3.5))
            rsp = self.fetch(url)
            
            if rsp:
                # 解析分类页面的视频列表
                videos = self._parse_category_list(rsp.text)
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
    
    def _parse_category_list(self, html_text):
        """解析分类页面的视频列表"""
        videos = []
        
        # 尝试多种匹配模式
        patterns = [
            r'<li[^>]*>.*?<a[^>]*href="([^"]+)"[^>]*class="[^"]*main[^"]*"[^>]*>([^<]+)</a>.*?</li>',
            r'<li[^>]*>.*?<a[^>]*href="([^"]+)"[^>]*title="([^"]+)"[^>]*>',
            r'<li[^>]*>.*?<a[^>]*href="([^"]+)"[^>]*>([^<]+)</a>.*?<span[^>]*class="[^"]*hot[^"]*"[^>]*>',
            r'<h2>\s*<a[^>]*href="([^"]+)"[^>]*title="([^"]+)"[^>]*>',
            r'<a[^>]*href="([^"]+)"[^>]*title="([^"]+)"[^>]*>\s*<span[^>]*class="[^"]*num[^"]*"[^>]*>'
        ]
        
        for pattern in patterns:
            try:
                for match in re.finditer(pattern, html_text, re.S):
                    href = match.group(1).strip()
                    name = match.group(2).strip()
                    
                    if href and name:
                        # 清理名称
                        cleaned_name = re.sub(r'^【[^】]*】', '', name).strip()
                        final_name = cleaned_name if cleaned_name else name
                        
                        # 构建完整URL
                        full_url = urljoin(self.host, href)
                        
                        videos.append({
                            "vod_id": full_url,
                            "vod_name": final_name,
                            "vod_pic": self.default_image,
                            "vod_remarks": "",
                            "vod_content": final_name
                        })
                
                if videos:
                    break
            except Exception as e:
                print(f"Parse pattern error: {e}")
                continue
        
        return videos
    
    def detailContent(self, array):
        result = {'list': []}
        if not array:
            return result
            
        try:
            vod_id = array[0]
            detail_url = vod_id
            
            time.sleep(random.uniform(1, 2))
            rsp = self.fetch(detail_url)
            
            if rsp:
                vod = self._parse_detail_page(rsp.text, detail_url)
                if vod:
                    result['list'] = [vod]
        except Exception as e:
            print(f"Detail parse error: {e}")
            
        return result
    
    def _parse_detail_page(self, html_text, detail_url):
        """解析详情页面"""
        try:
            # 提取标题
            title = "未知标题"
            title_patterns = [
                r'<h1[^>]*>(.*?)</h1>',
                r'<title[^>]*>(.*?)</title>',
                r'<h2[^>]*>(.*?)</h2>'
            ]
            
            for pattern in title_patterns:
                match = re.search(pattern, html_text, re.S)
                if match:
                    title = match.group(1).strip()
                    title = re.sub(r'^【[^】]+】', '', title).strip()
                    if title and title != "剧透社":
                        break
            
            # 提取所有网盘链接
            play_links = []
            
            # 查找所有a标签
            a_pattern = r'<a[^>]*href="([^"]+)"[^>]*>([^<]+)</a>'
            for match in re.finditer(a_pattern, html_text, re.I):
                href = match.group(1).strip()
                text = match.group(2).strip()
                
                # 检查是否是网盘链接
                if any(keyword in text for keyword in ['百度', '夸克', '阿里', '天翼', '迅雷', '蓝奏', '123', '城通', '微云', '网盘']):
                    play_links.append(href)
                elif any(domain in href for domain in [
                    'pan.baidu.com', 'pan.quark.cn', 'aliyundrive.com',
                    'cloud.189.cn', 'pan.xunlei.com', 'lanzou.com',
                    '123pan.com', 'ctfile.com', 'share.weiyun.com',
                    'www.aliyundrive.com'
                ]):
                    play_links.append(href)
            
            # 去重
            play_links = list(dict.fromkeys(play_links))
            
            # 构建播放链接
            play_parts = []
            for link in play_links:
                link = link.strip()
                if not link:
                    continue
                    
                # 识别网盘类型
                if 'pan.baidu.com' in link:
                    play_parts.append(f"百度网盘${link}")
                elif 'pan.quark.cn' in link:
                    play_parts.append(f"夸克网盘${link}")
                elif 'aliyundrive.com' in link:
                    play_parts.append(f"阿里云盘${link}")
                elif 'cloud.189.cn' in link:
                    play_parts.append(f"天翼云盘${link}")
                elif 'pan.xunlei.com' in link:
                    play_parts.append(f"迅雷网盘${link}")
                elif 'lanzou.com' in link:
                    play_parts.append(f"蓝奏云${link}")
                elif '123pan.com' in link:
                    play_parts.append(f"123云盘${link}")
                elif 'ctfile.com' in link:
                    play_parts.append(f"城通网盘${link}")
                elif 'share.weiyun.com' in link:
                    play_parts.append(f"微云${link}")
                else:
                    play_parts.append(f"网盘资源${link}")
            
            play_url = "#".join(play_parts) if play_parts else "暂无资源$#"
            play_from = "剧透社" if play_parts else "无资源"
            
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
            if pg > 1:
                url += f"&page={pg}"
                
            time.sleep(random.uniform(1, 2))
            rsp = self.fetch(url)
            
            if rsp:
                result['list'] = self._parse_category_list(rsp.text)
        except Exception as e:
            print(f"Search error: {e}")
            
        return result
    
    def playerContent(self, flag, id, vipFlags):
        """修复播放无声音问题 - 直接返回原始链接"""
        try:
            # 如果已经是完整链接，直接返回
            if id.startswith(('http://', 'https://')):
                return {
                    "parse": 0,  # 0表示不解析，直接播放
                    "playUrl": "",
                    "url": id,  # 直接返回原始网盘链接
                    "header": json.dumps({
                        "User-Agent": self.headers["User-Agent"],
                        "Referer": self.host,
                        "Accept": "*/*",
                        "Accept-Language": "zh-CN,zh;q=0.9",
                        "Connection": "keep-alive"
                    })
                }
            
            # 如果是push://协议，去掉协议头
            if id.startswith('push://'):
                real_url = id[7:]  # 去掉push://
                return {
                    "parse": 0,
                    "playUrl": "",
                    "url": real_url,
                    "header": json.dumps({
                        "User-Agent": self.headers["User-Agent"],
                        "Referer": self.host,
                        "Accept": "*/*",
                        "Accept-Language": "zh-CN,zh;q=0.9",
                        "Connection": "keep-alive"
                    })
                }
            
            # 默认情况
            return {
                "parse": 0,
                "playUrl": "",
                "url": id,
                "header": json.dumps({
                    "User-Agent": self.headers["User-Agent"],
                    "Referer": self.host,
                    "Accept": "*/*",
                    "Accept-Language": "zh-CN,zh;q=0.9",
                    "Connection": "keep-alive"
                })
            }
            
        except Exception as e:
            print(f"Player content error: {e}")
            return {
                "parse": 0,
                "playUrl": "",
                "url": id,
                "header": ""
            }
    
    def fetch(self, url, max_retries=2):
        """优化的请求方法"""
        for retry in range(max_retries):
            try:
                # 随机延迟，避免被反爬
                delay = random.uniform(1.0, 3.0)
                time.sleep(delay)
                
                # 更新User-Agent
                self.session.headers["User-Agent"] = random.choice([
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0"
                ])
                
                response = self.session.get(
                    url,
                    timeout=self.timeout,
                    verify=False,
                    allow_redirects=True,
                    headers=self.session.headers
                )
                
                # 尝试多种编码方式
                if response.encoding == 'ISO-8859-1':
                    response.encoding = 'utf-8'
                else:
                    response.encoding = response.apparent_encoding
                
                if response.status_code == 200:
                    return response
                elif response.status_code in [403, 429, 503]:
                    print(f"被反爬拦截，状态码: {response.status_code}，重试 {retry+1}/{max_retries}")
                    time.sleep(random.uniform(3, 5))
                else:
                    print(f"请求失败，状态码: {response.status_code}")
                    return None
                    
            except requests.exceptions.Timeout:
                print(f"请求超时，重试 {retry+1}/{max_retries}")
                time.sleep(random.uniform(2, 4))
            except Exception as e:
                print(f"请求异常: {e}")
                if retry == max_retries - 1:
                    return None
                time.sleep(random.uniform(2, 4))
        
        return None
