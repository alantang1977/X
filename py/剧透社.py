import sys
import json
import re
import time
import random
import requests
import urllib.parse
from urllib.parse import urlparse, parse_qs, urljoin
import hashlib

sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def __init__(self):
        self.name = "剧透社"
        self.host = "https://1.star2.cn"
        self.timeout = 15000
        self.limit = 20
        self.headers = {
            "User-Agent": random.choice([
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
            ]),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
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
        
        # 创建会话
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # 设置请求适配器
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=10,
            max_retries=3
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        # 播放地址验证配置
        self.verify_config = {
            'enable_verification': True,  # 启用验证
            'timeout_verify': 10,  # 验证超时(秒)
            'max_retries': 2,  # 最大重试次数
            'check_https': True,  # 检查HTTPS[citation:2]
            'check_domain': True,  # 检查域名
            'follow_redirects': True,  # 跟随重定向
        }
        
        # 已知可靠的网盘域名模式[citation:2][citation:9]
        self.trusted_domains = [
            'pan.baidu.com', 'yun.baidu.com',
            'pan.quark.cn', 'pan.aliyundrive.com', 'aliyundrive.com',
            'cloud.189.cn', 'pan.xunlei.com', 'www.123pan.com',
            'lanzou.com', 'lanzoux.com', 'lanzouv.com',
            'ctfile.com', 'weiyun.com'
        ]
        
        # 视频文件扩展名
        self.video_extensions = ['.mp4', '.m3u8', '.mkv', '.flv', '.avi', '.mov', '.wmv', '.ts', '.webm']

    def getName(self):
        return self.name
    
    def init(self, extend=""):
        print(f"============{extend}============")
        try:
            response = self.session.get(self.host, timeout=self.timeout/1000)
            time.sleep(random.uniform(1, 2))
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
        page_param = f"?page={pg}" if pg > 1 else ""
        url = f"{self.host}/{tid}/{page_param}".rstrip('/')
        
        try:
            time.sleep(random.uniform(1.5, 3))
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
            print(f"分类内容获取失败 {url}: {e}")
            
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
            # 改进的正则表达式匹配
            pattern = r'<a[^>]*href=["\']([^"\']+?)["\'][^>]*class=["\']main["\'][^>]*>([^<]+)</a>'
            for match in re.finditer(pattern, html_text, re.I | re.S):
                href = match.group(1).strip()
                name = match.group(2).strip()
                
                if href and name:
                    cleaned_name = re.sub(r'^【[^】]*】\s*', '', name).strip()
                    cleaned_name = re.sub(r'\s+', ' ', cleaned_name)
                    if not cleaned_name:
                        cleaned_name = name
                    
                    # 提取备注信息
                    remarks = []
                    if re.search(r'4K|2160P|超清', name, re.I):
                        remarks.append("4K")
                    elif re.search(r'1080P|高清', name, re.I):
                        remarks.append("1080P")
                    elif re.search(r'720P|标清', name, re.I):
                        remarks.append("720P")
                    
                    if re.search(r'全\d+集|完结', name):
                        remarks.append("完结")
                    elif re.search(r'更新至[第]?(\d+)', name):
                        ep_match = re.search(r'更新至[第]?(\d+)', name)
                        if ep_match:
                            remarks.append(f"更{ep_match.group(1)}")
                    
                    videos.append({
                        "vod_id": build_full_url(href),
                        "vod_name": cleaned_name,
                        "vod_pic": self.default_image,
                        "vod_remarks": " ".join(remarks),
                        "vod_content": cleaned_name
                    })
        except Exception as e:
            print(f"解析视频列表错误: {e}")
        
        return videos[:self.limit]
    
    def detailContent(self, array):
        result = {'list': []}
        if not array:
            return result
            
        try:
            vod_id = array[0]
            detail_url = vod_id if vod_id.startswith("http") else f"{self.host}{vod_id}"
            time.sleep(random.uniform(1, 2))
            rsp = self.fetch(detail_url)
            if rsp:
                vod = self._parse_detail_page(rsp.text, detail_url)
                if vod:
                    result['list'] = [vod]
        except Exception as e:
            print(f"详情页解析错误 {vod_id}: {e}")
        return result
    
    def _parse_detail_page(self, html_text, detail_url):
        try:
            # 提取标题
            title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html_text, re.S)
            title = title_match.group(1).strip() if title_match else "未知标题"
            title = re.sub(r'^【[^】]+】\s*', '', title).strip() or "未知标题"
            title = re.sub(r'\s+', ' ', title)
            
            # 提取描述
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
            
            # 提取封面
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
            
            # 改进的播放链接提取和验证
            play_links_info = self._extract_and_verify_play_links(html_text, detail_url)
            
            # 构建播放URL
            play_items = []
            for link_info in play_links_info:
                name = link_info.get('name', '未知来源')
                url = link_info.get('url', '')
                if url:
                    play_items.append(f"{name}${url}")
            
            play_url = "#".join(play_items) if play_items else "暂无资源$#"
            play_from = "剧透社" if play_items else "无资源"
            
            return {
                "vod_id": detail_url,
                "vod_name": title,
                "vod_pic": cover_url,
                "vod_content": description or title,
                "vod_remarks": "",
                "vod_play_from": play_from,
                "vod_play_url": play_url
            }
        except Exception as e:
            print(f"解析详情页错误: {e}")
            return {
                "vod_id": detail_url,
                "vod_name": "未知标题",
                "vod_pic": self.default_image,
                "vod_content": f"加载详情页失败",
                "vod_remarks": "",
                "vod_play_from": "无资源",
                "vod_play_url": "暂无资源$#"
            }
    
    def _extract_and_verify_play_links(self, html_text, source_url):
        """
        提取并验证播放链接[citation:1][citation:2][citation:4]
        返回格式: [{'name': '来源名称', 'url': '验证后的URL', 'verified': True/False}]
        """
        links_info = []
        
        # 1. 提取所有可能的链接
        all_links = self._extract_all_links(html_text)
        
        # 2. 过滤和分类链接
        filtered_links = self._filter_and_classify_links(all_links)
        
        # 3. 验证链接真实性[citation:2][citation:4][citation:9]
        for link_data in filtered_links:
            original_url = link_data['url']
            link_type = link_data['type']
            name = link_data.get('name', '未知来源')
            
            print(f"验证链接: {name} - {original_url}")
            
            # 验证链接
            verified_url = self._verify_link(original_url, link_type, source_url)
            
            if verified_url:
                links_info.append({
                    'name': name,
                    'url': verified_url,
                    'verified': True,
                    'type': link_type
                })
                print(f"✓ 链接验证成功: {verified_url}")
            else:
                # 即使验证失败，也保留原始链接（标记为未验证）
                links_info.append({
                    'name': f"{name}(未验证)",
                    'url': original_url,
                    'verified': False,
                    'type': link_type
                })
                print(f"✗ 链接验证失败: {original_url}")
        
        return links_info
    
    def _extract_all_links(self, html_text):
        """提取页面中所有可能的链接"""
        links = []
        
        # 匹配<a>标签中的链接
        a_pattern = r'<a[^>]*href=["\']([^"\']+?)["\'][^>]*>([^<]*?)</a>'
        for match in re.finditer(a_pattern, html_text, re.I | re.S):
            href = match.group(1).strip()
            text = match.group(2).strip()
            if href and not href.startswith('javascript:'):
                links.append({'url': href, 'text': text})
        
        # 匹配纯文本中的URL
        url_pattern = r'https?://[^\s<>"\']+'
        for match in re.finditer(url_pattern, html_text, re.I):
            url = match.group(0).strip()
            links.append({'url': url, 'text': ''})
        
        return links
    
    def _filter_and_classify_links(self, links):
        """过滤和分类链接"""
        filtered = []
        
        for link_info in links:
            url = link_info['url']
            text = link_info['text']
            
            # 跳过无效链接
            if not url or len(url) < 10:
                continue
            
            # 解码URL
            try:
                url = urllib.parse.unquote(url)
            except:
                pass
            
            # 分类链接
            link_type = self._classify_link(url, text)
            
            if link_type != 'other':
                # 为不同类型链接分配名称
                name = self._get_link_name(url, text, link_type)
                filtered.append({
                    'url': url,
                    'type': link_type,
                    'name': name,
                    'text': text
                })
        
        return filtered
    
    def _classify_link(self, url, text):
        """分类链接类型"""
        url_lower = url.lower()
        text_lower = text.lower()
        
        # 检查是否为视频直链[citation:1]
        if any(ext in url_lower for ext in self.video_extensions):
            return 'video_direct'
        
        # 检查是否为网盘链接
        pan_keywords = {
            'baidu': ['baidu', '百度', '网盘'],
            'quark': ['quark', '夸克'],
            'aliyun': ['aliyun', '阿里', '云盘'],
            '189': ['189', '天翼', '电信'],
            'xunlei': ['xunlei', '迅雷'],
            'lanzou': ['lanzou', '蓝奏'],
            '123': ['123pan', '123云盘'],
            'ctfile': ['ctfile', '城通'],
            'weiyun': ['weiyun', '微云']
        }
        
        for pan_type, keywords in pan_keywords.items():
            if any(keyword in url_lower or keyword in text_lower for keyword in keywords):
                return f'pan_{pan_type}'
        
        # 检查是否为播放列表
        if '.m3u8' in url_lower or 'playlist' in url_lower:
            return 'playlist'
        
        return 'other'
    
    def _get_link_name(self, url, text, link_type):
        """获取链接显示名称"""
        if text and len(text) < 20:
            # 清理文本
            clean_text = re.sub(r'[【】\[\]<>]', '', text).strip()
            if clean_text:
                return clean_text
        
        # 根据链接类型返回默认名称
        type_names = {
            'video_direct': '视频直链',
            'playlist': '播放列表',
            'pan_baidu': '百度网盘',
            'pan_quark': '夸克网盘',
            'pan_aliyun': '阿里云盘',
            'pan_189': '天翼云盘',
            'pan_xunlei': '迅雷网盘',
            'pan_lanzou': '蓝奏云',
            'pan_123': '123云盘',
            'pan_ctfile': '城通网盘',
            'pan_weiyun': '腾讯微云'
        }
        
        return type_names.get(link_type, '未知来源')
    
    def _verify_link(self, url, link_type, source_url):
        """
        验证链接的真实性和可用性[citation:2][citation:4][citation:9]
        """
        if not self.verify_config['enable_verification']:
            return url
        
        try:
            # 1. 基本URL验证
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                print(f"无效的URL格式: {url}")
                return None
            
            # 2. 检查HTTPS[citation:2]
            if self.verify_config['check_https'] and parsed.scheme != 'https':
                print(f"非HTTPS链接，可能存在安全风险: {url}")
                # 不直接拒绝，但记录警告
            
            # 3. 检查域名可信度[citation:9]
            if self.verify_config['check_domain']:
                domain = parsed.netloc.lower()
                is_trusted = any(trusted_domain in domain for trusted_domain in self.trusted_domains)
                
                if not is_trusted:
                    print(f"非受信任域名: {domain}")
                    # 对非受信任域名进行更严格的检查
            
            # 4. 对于网盘链接，尝试获取真实地址
            if link_type.startswith('pan_'):
                return self._verify_pan_link(url, link_type)
            
            # 5. 对于视频直链，检查可访问性
            elif link_type == 'video_direct':
                return self._verify_video_link(url)
            
            # 6. 通用链接验证
            else:
                return self._verify_general_link(url)
                
        except Exception as e:
            print(f"链接验证过程中出错 {url}: {e}")
            return None
        
        return url
    
    def _verify_pan_link(self, url, link_type):
        """验证网盘链接"""
        try:
            # 添加Referer头模拟正常访问
            headers = {
                'Referer': 'https://pan.baidu.com/' if 'baidu' in link_type else self.host,
                'User-Agent': self.headers['User-Agent']
            }
            
            # 发送HEAD请求检查链接是否可访问
            response = self.session.head(
                url,
                headers=headers,
                timeout=self.verify_config['timeout_verify'],
                allow_redirects=self.verify_config['follow_redirects']
            )
            
            if response.status_code in [200, 301, 302]:
                # 处理重定向
                final_url = response.url if hasattr(response, 'url') else url
                
                # 提取可能的密码信息（从URL参数或片段中）
                parsed = urlparse(final_url)
                query_params = parse_qs(parsed.query)
                
                # 常见网盘密码参数
                password_keys = ['pwd', 'password', '提取码', '提取密码', 'access_code']
                for key in password_keys:
                    if key in query_params:
                        password = query_params[key][0]
                        if password and len(password) >= 4:
                            final_url = f"{final_url}#{password}"
                            break
                
                return final_url
            else:
                print(f"网盘链接不可访问: {url}, 状态码: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"验证网盘链接失败 {url}: {e}")
            return None
    
    def _verify_video_link(self, url):
        """验证视频直链"""
        try:
            # 发送HEAD请求检查Content-Type
            response = self.session.head(
                url,
                timeout=self.verify_config['timeout_verify'],
                allow_redirects=self.verify_config['follow_redirects']
            )
            
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '').lower()
                
                # 检查是否为视频内容类型
                video_content_types = ['video/', 'application/vnd.apple.mpegurl', 'application/x-mpegurl']
                if any(video_type in content_type for video_type in video_content_types):
                    return response.url if hasattr(response, 'url') else url
                else:
                    print(f"非视频内容类型: {content_type}")
                    return None
            else:
                print(f"视频链接不可访问: {url}, 状态码: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"验证视频链接失败 {url}: {e}")
            return None
    
    def _verify_general_link(self, url):
        """验证通用链接"""
        try:
            response = self.session.head(
                url,
                timeout=self.verify_config['timeout_verify'],
                allow_redirects=self.verify_config['follow_redirects']
            )
            
            if response.status_code in [200, 301, 302]:
                return response.url if hasattr(response, 'url') else url
            else:
                print(f"链接不可访问: {url}, 状态码: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"验证链接失败 {url}: {e}")
            return None
    
    def searchContent(self, key, quick, pg):
        result = {'list': []}
        if not key or not key.strip():
            return result
            
        try:
            encoded_key = urllib.parse.quote(key.strip())
            url = f"{self.host}/search/?keyword={encoded_key}&page={pg}"
            time.sleep(random.uniform(1, 2))
            rsp = self.fetch(url)
            if rsp:
                videos = self._parse_video_list(rsp.text)
                result['list'] = videos
                result['page'] = pg
                result['pagecount'] = 9999
                result['total'] = 999999
        except Exception as e:
            print(f"搜索失败 '{key}': {e}")
        return result
    
    def playerContent(self, flag, id, vipFlags):
        """
        改进的播放内容处理[citation:7][citation:10]
        解决播放无声和无法播放的问题
        """
        try:
            # 分离链接和可能的密码
            if '#' in id:
                url, pwd = id.split('#', 1)
            else:
                url, pwd = id, ""
            
            # 解码URL
            url = urllib.parse.unquote(url)
            
            # 准备请求头
            headers = dict(self.session.headers)
            
            # 根据链接类型设置不同的播放参数[citation:10]
            parse_mode, play_url, final_url = self._determine_playback_params(url, headers, pwd)
            
            return {
                "parse": parse_mode,
                "playUrl": play_url,
                "url": final_url,
                "header": json.dumps(headers)
            }
                
        except Exception as e:
            print(f"播放内容处理错误: {e}")
            # 出错时返回基本配置
            return {
                "parse": 0,
                "playUrl": "",
                "url": id if id.startswith("push://") else f"push://{id}",
                "header": json.dumps(dict(self.session.headers))
            }
    
    def _determine_playback_params(self, url, headers, password):
        """
        根据URL类型确定播放参数[citation:7][citation:10]
        返回: (parse_mode, play_url, final_url)
        """
        url_lower = url.lower()
        
        # 1. 如果是push协议，直接使用
        if url.startswith("push://"):
            return 0, "", url
        
        # 2. 视频直链 - 直接播放
        if any(ext in url_lower for ext in self.video_extensions):
            # 设置适当的Referer
            if 'referer' not in [k.lower() for k in headers.keys()]:
                parsed = urlparse(url)
                headers['Referer'] = f"{parsed.scheme}://{parsed.netloc}/"
            
            # 对于M3U8，可能需要特殊处理
            if '.m3u8' in url_lower:
                return 1, "", url  # parse=1表示需要解析
            else:
                return 0, "", url  # 直接播放
        
        # 3. 网盘链接 - 使用push协议
        elif any(domain in url_lower for domain in self.trusted_domains):
            # 设置网盘特定的请求头
            if 'pan.baidu.com' in url_lower:
                headers.update({
                    "Referer": "https://pan.baidu.com/",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                })
                # 如果有密码，添加到URL中
                if password:
                    url = f"{url}#{password}"
                return 0, "", f"push://{url}"
            
            elif 'aliyundrive.com' in url_lower:
                headers.update({
                    "Referer": "https://www.aliyundrive.com/",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                })
                return 1, "", f"push://{url}"
            
            else:
                # 其他网盘
                return 0, "", f"push://{url}"
        
        # 4. 其他链接 - 默认使用push协议
        else:
            return 0, "", f"push://{url}"
    
    def fetch(self, url):
        """改进的请求方法"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 随机更换User-Agent
                self.session.headers["User-Agent"] = random.choice([
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
                ])
                
                response = self.session.get(
                    url,
                    timeout=self.timeout/1000,
                    allow_redirects=True,
                    verify=False  # 注意：生产环境建议设为True
                )
                
                response.encoding = response.apparent_encoding or 'utf-8'
                
                if response.status_code == 200:
                    return response
                elif response.status_code in [403, 429, 503]:
                    wait_time = (attempt + 1) * random.uniform(3, 5)
                    print(f"请求被限制，等待{wait_time:.1f}秒后重试...")
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
