import sys
import json
import re
import time
import random
import requests
import urllib.parse
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def __init__(self):
        self.name = "剧透社"
        self.host = "https://1.star2.cn"
        self.timeout = 15000  # 延长超时时间
        self.limit = 20
        # 增强请求头，模拟真实浏览器
        self.headers = {
            "User-Agent": random.choice([
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
            ]),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,zh-TW;q=0.8,zh-HK;q=0.7,en-US;q=0.6,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": f"{self.host}/",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "DNT": "1"
        }
        self.default_image = "https://images.gamedog.cn/gamedog/imgfile/20241205/05105843u5j9.png"
        # 创建会话保持
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        # 设置请求适配器，增加重试次数
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=10,
            max_retries=3
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

    def getName(self):
        return self.name
    
    def init(self, extend=""):
        print(f"============{extend}============")
        # 初始化时先获取首页Cookie
        try:
            response = self.session.get(self.host, timeout=self.timeout/1000)
            # 更新可能的动态Cookie
            if 'Set-Cookie' in response.headers:
                for cookie in response.headers.get_list('Set-Cookie'):
                    if '=' in cookie:
                        name, value = cookie.split('=', 1)
                        value = value.split(';', 1)[0]
                        self.session.cookies.set(name.strip(), value.strip())
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
        # 添加页码处理
        page_param = f"?page={pg}" if pg > 1 else ""
        url = f"{self.host}/{tid}/{page_param}".rstrip('/')
        
        try:
            # 添加随机延迟，避免请求过于频繁
            time.sleep(random.uniform(2, 4))
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
            print(f"Category parse error for {url}: {e}")
            
        return result
    
    def _parse_video_list(self, html_text):
        videos = []
        
        def build_full_url(href):
            if not href:
                return ""
            if href.startswith("http"):
                return href
            return f"{self.host}{href}" if href.startswith("/") else f"{self.host}/{href}"
        
        try:
            # 改进正则表达式，提高匹配精度
            pattern = r'<a[^>]*href=["\']([^"\']+)["\'][^>]*class=["\']main["\'][^>]*>([^<]+)</a>'
            for match in re.finditer(pattern, html_text, re.I | re.S):
                href = match.group(1).strip()
                name = match.group(2).strip()
                
                if href and name:
                    # 清理标题中的多余符号
                    cleaned_name = re.sub(r'^【[^】]*】\s*', '', name).strip()
                    cleaned_name = re.sub(r'\s+', ' ', cleaned_name)
                    if not cleaned_name:
                        cleaned_name = name
                    
                    videos.append({
                        "vod_id": build_full_url(href),
                        "vod_name": cleaned_name,
                        "vod_pic": self.default_image,
                        "vod_remarks": self._extract_remarks(name),
                        "vod_content": cleaned_name
                    })
        except Exception as e:
            print(f"Parse video list error: {e}")
        
        return videos[:self.limit]  # 限制返回数量
    
    def _extract_remarks(self, title):
        """从标题中提取备注信息（如更新状态、清晰度等）"""
        remarks = []
        # 提取清晰度
        if re.search(r'4K|2160P|超清', title, re.I):
            remarks.append("4K")
        elif re.search(r'1080P|高清', title, re.I):
            remarks.append("1080P")
        elif re.search(r'720P|标清', title, re.I):
            remarks.append("720P")
        
        # 提取更新状态
        if re.search(r'全\d+集|完结', title):
            remarks.append("完结")
        elif re.search(r'更新至|连载', title):
            match = re.search(r'更新至[第]?(\d+)', title)
            if match:
                remarks.append(f"更{match.group(1)}")
        
        return " ".join(remarks) if remarks else ""
    
    def detailContent(self, array):
        result = {'list': []}
        if not array:
            return result
            
        try:
            vod_id = array[0]
            detail_url = vod_id if vod_id.startswith("http") else f"{self.host}{vod_id}"
            time.sleep(random.uniform(1.5, 2.5))  # 详情页请求延迟
            rsp = self.fetch(detail_url)
            if rsp:
                vod = self._parse_detail_page(rsp.text, detail_url)
                if vod:
                    result['list'] = [vod]
        except Exception as e:
            print(f"Detail parse error for {vod_id}: {e}")
        return result
    
    def _parse_detail_page(self, html_text, detail_url):
        try:
            # 提取标题
            title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html_text, re.S)
            title = title_match.group(1).strip() if title_match else "未知标题"
            title = re.sub(r'^【[^】]+】\s*', '', title).strip() or "未知标题"
            title = re.sub(r'\s+', ' ', title)
            
            # 提取描述信息
            desc_patterns = [
                r'<div[^>]*class=["\']content["\'][^>]*>(.*?)</div>',
                r'<p[^>]*class=["\']desc["\'][^>]*>(.*?)</p>',
                r'简介[：:]\s*(.*?)(?:<br|<p|<div|$)'
            ]
            description = ""
            for pattern in desc_patterns:
                match = re.search(pattern, html_text, re.S | re.I)
                if match:
                    desc = re.sub(r'<[^>]+>', '', match.group(1)).strip()
                    if desc and len(desc) > 10:
                        description = desc[:200] + "..." if len(desc) > 200 else desc
                        break
            
            # 提取封面图片
            cover_patterns = [
                r'<img[^>]*src=["\']([^"\']+?\.(?:jpg|jpeg|png|gif|webp))["\'][^>]*>',
                r'data-original=["\']([^"\']+?)["\']',
                r'background-image:\s*url\(["\']?([^"\'\)]+)["\']?\)'
            ]
            cover_url = self.default_image
            for pattern in cover_patterns:
                match = re.search(pattern, html_text, re.I | re.S)
                if match:
                    img_url = match.group(1).strip()
                    if img_url and not img_url.startswith('data:'):
                        cover_url = img_url if img_url.startswith('http') else f"{self.host}{img_url}"
                        break
            
            # 优化资源链接提取规则
            play_links = self._extract_play_links(html_text)
            
            # 构建播放URL
            play_url = self._build_play_url(play_links)
            play_from = "剧透社" if play_links else "无资源"
            
            return {
                "vod_id": detail_url,
                "vod_name": title,
                "vod_pic": cover_url,
                "vod_content": description or title,
                "vod_remarks": self._extract_remarks(title),
                "vod_play_from": play_from,
                "vod_play_url": play_url
            }
        except Exception as e:
            print(f"Parse detail page error: {e}")
            return {
                "vod_id": detail_url,
                "vod_name": "未知标题",
                "vod_pic": self.default_image,
                "vod_content": f"加载详情页失败：{str(e)[:50]}",
                "vod_remarks": "",
                "vod_play_from": "无资源",
                "vod_play_url": "暂无资源$#"
            }
    
    def _extract_play_links(self, html_text):
        """提取播放链接，包括网盘链接和可能的直链"""
        play_links = []
        
        # 网盘链接模式
        pan_patterns = [
            r'(https?://[^\s"\']*pan\.baidu\.com[^\s"\']+)',
            r'(https?://[^\s"\']*pan\.quark\.cn[^\s"\']+)',
            r'(https?://[^\s"\']*aliyundrive\.com[^\s"\']+)',
            r'(https?://[^\s"\']*cloud\.189\.cn[^\s"\']+)',
            r'(https?://[^\s"\']*pan\.xunlei\.com[^\s"\']+)',
            r'(https?://[^\s"\']*lanzou[^\.]*\.com[^\s"\']+)',
            r'(https?://[^\s"\']*123pan\.com[^\s"\']+)',
            r'(https?://[^\s"\']*ctfile\.com[^\s"\']+)',
            r'(https?://[^\s"\']*weiyun\.com[^\s"\']+)'
        ]
        
        for pattern in pan_patterns:
            for match in re.finditer(pattern, html_text, re.I):
                link = match.group(1).strip()
                if link and link not in play_links:
                    # 清理链接中的多余字符
                    link = re.sub(r'["\'<>]', '', link)
                    play_links.append(link)
        
        # 提取密码信息
        pwd_patterns = [
            r'提取码[：:]\s*(\w{4})',
            r'密码[：:]\s*(\w{4})',
            r'码[：:]\s*(\w{4})',
            r'[提取]?码\s*[:：]?\s*(\w{4})'
        ]
        passwords = []
        for pattern in pwd_patterns:
            for match in re.finditer(pattern, html_text):
                pwd = match.group(1).strip()
                if pwd and pwd not in passwords:
                    passwords.append(pwd)
        
        # 将密码附加到链接中
        if passwords and play_links:
            for i, link in enumerate(play_links):
                if i < len(passwords):
                    play_links[i] = f"{link}#{passwords[i]}"
        
        return play_links
    
    def _build_play_url(self, play_links):
        """构建播放URL格式"""
        if not play_links:
            return "暂无资源$#"
        
        play_items = []
        for i, link in enumerate(play_links):
            # 判断网盘类型
            if "pan.baidu.com" in link:
                name = f"百度网盘{i+1}"
            elif "pan.quark.cn" in link:
                name = f"夸克网盘{i+1}"
            elif "aliyundrive.com" in link:
                name = f"阿里云盘{i+1}"
            elif "cloud.189.cn" in link:
                name = f"天翼云盘{i+1}"
            elif "pan.xunlei.com" in link:
                name = f"迅雷网盘{i+1}"
            elif "lanzou" in link:
                name = f"蓝奏云{i+1}"
            elif "123pan.com" in link:
                name = f"123云盘{i+1}"
            elif "ctfile.com" in link:
                name = f"城通网盘{i+1}"
            elif "weiyun.com" in link:
                name = f"微云{i+1}"
            else:
                name = f"资源{i+1}"
            
            # 确保链接格式正确
            if not link.startswith("http"):
                link = f"http://{link}"
            
            play_items.append(f"{name}${link}")
        
        return "#".join(play_items)
    
    def searchContent(self, key, quick, pg):
        result = {'list': []}
        if not key or not key.strip():
            return result
            
        try:
            encoded_key = urllib.parse.quote(key.strip())
            url = f"{self.host}/search/?keyword={encoded_key}&page={pg}"
            time.sleep(random.uniform(1.5, 2.5))
            rsp = self.fetch(url)
            if rsp:
                videos = self._parse_video_list(rsp.text)
                result['list'] = videos
                result['page'] = pg
                result['pagecount'] = 9999
                result['total'] = 999999
        except Exception as e:
            print(f"Search error for '{key}': {e}")
        return result
    
    def playerContent(self, flag, id, vipFlags):
        """
        改进播放内容处理，解决无声问题
        flag: 播放来源标记
        id: 播放链接（可能包含密码）
        vipFlags: VIP标记
        """
        try:
            # 分离链接和密码
            if '#' in id:
                url, pwd = id.split('#', 1)
            else:
                url, pwd = id, ""
            
            # 解码URL
            url = urllib.parse.unquote(url)
            
            # 根据不同网盘类型返回不同的播放参数
            headers = dict(self.session.headers)
            
            # 根据网盘类型设置特定的Referer和User-Agent
            if "pan.baidu.com" in url:
                headers.update({
                    "Referer": "https://pan.baidu.com/",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                })
                parse = 0  # 百度网盘通常需要外部解析
            elif "aliyundrive.com" in url:
                headers.update({
                    "Referer": "https://www.aliyundrive.com/",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                })
                parse = 1  # 阿里云盘通常可以直接播放
            elif "pan.quark.cn" in url:
                headers.update({
                    "Referer": "https://pan.quark.cn/",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                })
                parse = 0
            else:
                parse = 0  # 默认不解析
            
            # 如果链接已经是push协议，直接使用
            if url.startswith("push://"):
                return {
                    "parse": parse,
                    "playUrl": "",
                    "url": url,
                    "header": json.dumps(headers)
                }
            
            # 对于网盘链接，使用push协议推送
            # 如果是视频直链，则直接播放
            if any(ext in url.lower() for ext in ['.mp4', '.m3u8', '.flv', '.avi', '.mkv', '.ts']):
                return {
                    "parse": 0,  # 直链直接播放
                    "playUrl": "",
                    "url": url,
                    "header": json.dumps(headers)
                }
            else:
                # 网盘链接使用push协议
                return {
                    "parse": parse,
                    "playUrl": "",
                    "url": f"push://{url}",
                    "header": json.dumps(headers)
                }
                
        except Exception as e:
            print(f"Player content error: {e}")
            # 出错时返回基本配置
            return {
                "parse": 0,
                "playUrl": "",
                "url": f"push://{id}" if not id.startswith("push://") else id,
                "header": json.dumps(dict(self.session.headers))
            }
    
    def fetch(self, url):
        """改进的请求方法，增加重试和错误处理"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 随机更换User-Agent
                self.session.headers["User-Agent"] = random.choice([
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0"
                ])
                
                # 动态设置Referer
                if not self.session.headers.get("Referer") or random.random() > 0.5:
                    self.session.headers["Referer"] = self.host
                
                response = self.session.get(
                    url,
                    timeout=self.timeout/1000,
                    allow_redirects=True,
                    verify=False  # 注意：生产环境建议设为True
                )
                
                # 处理重定向
                if response.history:
                    for resp in response.history:
                        if 'Set-Cookie' in resp.headers:
                            self._update_cookies(resp.headers.get_list('Set-Cookie'))
                
                response.encoding = response.apparent_encoding or 'utf-8'
                
                if response.status_code == 200:
                    return response
                elif response.status_code in [403, 429, 503]:
                    wait_time = (attempt + 1) * random.uniform(3, 5)
                    print(f"请求被限制，状态码: {response.status_code}，等待{wait_time:.1f}秒后重试...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"请求失败，状态码: {response.status_code}")
                    if attempt == max_retries - 1:
                        return None
                    time.sleep(random.uniform(2, 4))
                    
            except requests.exceptions.Timeout:
                print(f"请求超时，第{attempt+1}次重试...")
                if attempt == max_retries - 1:
                    return None
                time.sleep(random.uniform(3, 5))
            except Exception as e:
                print(f"请求异常: {e}")
                if attempt == max_retries - 1:
                    return None
                time.sleep(random.uniform(2, 4))
        
        return None
    
    def _update_cookies(self, cookie_list):
        """更新会话Cookie"""
        for cookie in cookie_list:
            if '=' in cookie:
                name, value = cookie.split('=', 1)
                value = value.split(';', 1)[0]
                self.session.cookies.set(name.strip(), value.strip())
    
    def isVideoFormat(self, url):
        """判断是否为视频格式链接"""
        video_extensions = ['.mp4', '.m3u8', '.flv', '.avi', '.mkv', '.mov', '.wmv', '.ts']
        return any(url.lower().endswith(ext) for ext in video_extensions)
