import sys
import json
import re
import time
import random
import requests
import concurrent.futures
from urllib.parse import urlparse, urljoin
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def __init__(self):
        self.name = "剧透社"
        self.host = "https://1.star2.cn"
        self.timeout = 8000  # 优化超时时间
        self.limit = 30
        self.cache_timeout = 300  # 缓存5分钟
        self.cache = {}
        
        # 智能网盘识别配置
        self.cloud_disk_patterns = {
            "百度网盘": [
                r'pan\.baidu\.com',
                r'yun\.baidu\.com',
                r'baidu\.com/s/',
                r'pwd=(\w{4})',
                r'提取[码码][:：]\s*(\w{4})'
            ],
            "夸克网盘": [
                r'pan\.quark\.cn',
                r'quark\.cn/s/',
                r'夸克.*[网盘盘]'
            ],
            "阿里云盘": [
                r'aliyundrive\.com',
                r'alipan\.com',
                r'阿里[云云]?[盘盘]'
            ],
            "天翼云盘": [
                r'cloud\.189\.cn',
                r'天翼[云云]?[盘盘]'
            ],
            "迅雷云盘": [
                r'pan\.xunlei\.com',
                r'迅雷[云云]?[盘盘]'
            ],
            "蓝奏云": [
                r'lanzou[xtv]?\.com',
                r'蓝奏[云云]?'
            ],
            "123云盘": [
                r'123pan\.com',
                r'123[云云]?[盘盘]'
            ],
            "其他网盘": [
                r'ctfile\.com',
                r'share\.weiyun\.com',
                r'weiyun\.com',
                r'城通[网网]?[盘盘]',
                r'微[信云][盘盘]'
            ]
        }
        
        # 优化请求头
        self.headers = {
            "User-Agent": random.choice([
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
            ]),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": f"{self.host}/",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache"
        }
        
        self.default_image = "https://images.gamedog.cn/gamedog/imgfile/20241205/05105843u5j9.png"
        
        # 创建智能会话
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.session.mount('https://', requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=30,
            max_retries=2
        ))

    def getName(self):
        return self.name
    
    def init(self, extend=""):
        print(f"============{extend}============")
        # 预热连接池
        try:
            self.session.get(f"{self.host}/", timeout=3)
        except:
            pass
    
    def homeContent(self, filter):
        # 使用缓存提高响应速度
        cache_key = "home_classes"
        if cache_key in self.cache and time.time() - self.cache[cache_key]['timestamp'] < self.cache_timeout:
            return self.cache[cache_key]['data']
            
        data = {
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
        
        self.cache[cache_key] = {
            'data': data,
            'timestamp': time.time()
        }
        
        return data
    
    def categoryContent(self, tid, pg, filter, extend):
        # 生成缓存键
        cache_key = f"category_{tid}_{pg}"
        if cache_key in self.cache and time.time() - self.cache[cache_key]['timestamp'] < self.cache_timeout:
            return self.cache[cache_key]['data']
            
        result = {'list': []}
        url = f"{self.host}/{tid}/" if pg == 1 else f"{self.host}/{tid}/?page={pg}"
        
        try:
            # 使用更短的延迟
            time.sleep(random.uniform(0.5, 1.5))
            rsp = self._smart_fetch(url)
            if rsp:
                # 使用快速解析方法
                videos = self._fast_parse_video_list(rsp.text)
                result.update({
                    'list': videos,
                    'page': pg,
                    'pagecount': 9999,
                    'limit': self.limit,
                    'total': 999999
                })
                
                # 缓存结果
                self.cache[cache_key] = {
                    'data': result,
                    'timestamp': time.time()
                }
        except Exception as e:
            print(f"Category parse error for {url}: {e}")
            
        return result
    
    def _fast_parse_video_list(self, html_text):
        """快速解析视频列表"""
        videos = []
        
        try:
            # 使用更高效的正则匹配
            # 匹配包含链接和标题的模式
            link_pattern = r'<a[^>]*href="([^"]*)"[^>]*class="[^"]*main[^"]*"[^>]*>([^<]+)</a>'
            
            for match in re.finditer(link_pattern, html_text, re.I):
                href = match.group(1).strip()
                name = match.group(2).strip()
                
                if href and name and not href.startswith('http'):
                    # 清理标题
                    cleaned_name = re.sub(r'^【[^】]*】\s*', '', name).strip()
                    if not cleaned_name:
                        cleaned_name = name
                    
                    # 构建完整URL
                    full_url = urljoin(self.host, href) if not href.startswith('http') else href
                    
                    videos.append({
                        "vod_id": full_url,
                        "vod_name": cleaned_name,
                        "vod_pic": self.default_image,
                        "vod_remarks": "",
                        "vod_content": cleaned_name
                    })
                    
                    # 限制数量
                    if len(videos) >= self.limit * 2:  # 稍微多取一些用于缓存
                        break
        except Exception as e:
            print(f"Fast parse error: {e}")
        
        return videos[:self.limit]  # 返回限制数量的结果
    
    def detailContent(self, array):
        if not array:
            return {'list': []}
            
        vod_id = array[0]
        cache_key = f"detail_{hash(vod_id)}"
        
        # 检查缓存
        if cache_key in self.cache and time.time() - self.cache[cache_key]['timestamp'] < self.cache_timeout:
            return {'list': [self.cache[cache_key]['data']]}
        
        result = {'list': []}
        detail_url = vod_id if vod_id.startswith("http") else urljoin(self.host, vod_id)
        
        max_retries = 2
        for attempt in range(max_retries):
            try:
                time.sleep(random.uniform(0.3, 0.8) * (attempt + 1))
                rsp = self._smart_fetch(detail_url)
                
                if rsp and rsp.status_code == 200:
                    vod = self._smart_parse_detail(rsp.text, detail_url)
                    if vod and vod.get("vod_play_url") != "暂无资源$#":
                        result['list'] = [vod]
                        # 缓存结果
                        self.cache[cache_key] = {
                            'data': vod,
                            'timestamp': time.time()
                        }
                        break
            except Exception as e:
                print(f"Detail parse error (attempt {attempt + 1}): {e}")
        
        return result
    
    def _smart_parse_detail(self, html_text, detail_url):
        """智能解析详情页"""
        try:
            # 1. 提取标题
            title = "未知标题"
            title_patterns = [
                r'<h1[^>]*>(.*?)</h1>',
                r'<title>(.*?)</title>',
                r'<meta[^>]*property="og:title"[^>]*content="(.*?)"'
            ]
            
            for pattern in title_patterns:
                match = re.search(pattern, html_text, re.S | re.I)
                if match:
                    title = match.group(1).strip()
                    title = re.sub(r'^【[^】]+】\s*', '', title)
                    break
            
            # 2. 智能网盘链接识别
            disk_links = self._extract_cloud_disk_links(html_text)
            
            # 3. 构建播放URL
            if disk_links:
                play_parts = []
                for disk_name, link, pwd in disk_links:
                    display_text = f"{disk_name}"
                    if pwd:
                        display_text += f" 密码:{pwd}"
                    play_parts.append(f"{display_text}${link}")
                
                play_url = "#".join(play_parts)
                play_from = "剧透社"
            else:
                play_url = "暂无资源$#"
                play_from = "无资源"
            
            # 4. 尝试提取图片
            pic_url = self.default_image
            pic_patterns = [
                r'<img[^>]*src="([^"]*\.(?:jpg|png|jpeg|gif|webp))"[^>]*>',
                r'meta[^>]*property="og:image"[^>]*content="([^"]+)"'
            ]
            
            for pattern in pic_patterns:
                match = re.search(pattern, html_text, re.I)
                if match:
                    found_pic = match.group(1).strip()
                    if found_pic and not found_pic.startswith('data:'):
                        pic_url = urljoin(detail_url, found_pic)
                        break
            
            return {
                "vod_id": detail_url,
                "vod_name": title,
                "vod_pic": pic_url,
                "vod_content": title,
                "vod_remarks": "",
                "vod_play_from": play_from,
                "vod_play_url": play_url
            }
            
        except Exception as e:
            print(f"Smart parse detail error: {e}")
            return {
                "vod_id": detail_url,
                "vod_name": "未知标题",
                "vod_pic": self.default_image,
                "vod_content": f"解析失败：{str(e)}",
                "vod_remarks": "",
                "vod_play_from": "无资源",
                "vod_play_url": "暂无资源$#"
            }
    
    def _extract_cloud_disk_links(self, html_text):
        """智能提取网盘链接"""
        disk_links = []
        found_urls = set()  # 用于去重
        
        # 方法1: 从特定HTML结构中提取
        # 查找dlipp-cont-bd区域
        content_section = re.search(r'<div[^>]*class="[^"]*dlipp-cont-bd[^"]*"[^>]*>(.*?)</div>', html_text, re.S | re.I)
        if content_section:
            section_html = content_section.group(1)
            # 提取所有链接
            link_pattern = r'<a[^>]*href="(https?://[^"]+)"[^>]*>(?:.*?<img[^>]*alt="([^"]*)"[^>]*>)?.*?<span>(.*?)</span>'
            
            for match in re.finditer(link_pattern, section_html, re.S | re.I):
                url = match.group(1).strip()
                alt_text = match.group(2) if match.group(2) else ""
                span_text = match.group(3).strip() if match.group(3) else ""
                
                if url and url not in found_urls:
                    # 识别网盘类型
                    disk_name = self._identify_cloud_disk(url, alt_text, span_text)
                    # 提取密码
                    pwd = self._extract_password(html_text, url)
                    disk_links.append((disk_name, url, pwd))
                    found_urls.add(url)
        
        # 方法2: 通用提取（如果方法1没找到）
        if not disk_links:
            # 查找所有可能的网盘链接
            link_pattern = r'(?:href|src)="(https?://[^"]*(?:baidu|quark|aliyun|189|xunlei|lanzou|123pan|ctfile|weiyun)[^"]*)"'
            for match in re.finditer(link_pattern, html_text, re.I):
                url = match.group(1).strip()
                if url and url not in found_urls:
                    disk_name = self._identify_cloud_disk(url)
                    if disk_name != "未知网盘":
                        pwd = self._extract_password(html_text, url)
                        disk_links.append((disk_name, url, pwd))
                        found_urls.add(url)
        
        # 方法3: 提取注释中的链接
        if not disk_links:
            # 查找可能的提取码+链接模式
            pwd_link_pattern = r'提取[码码][:：]\s*(\w{4})\s*(?:链接|地址)[:：]\s*(https?://\S+)'
            for match in re.finditer(pwd_link_pattern, html_text, re.I):
                pwd = match.group(1)
                url = match.group(2).strip()
                if url and url not in found_urls:
                    disk_name = self._identify_cloud_disk(url)
                    disk_links.append((disk_name, url, pwd))
                    found_urls.add(url)
        
        return disk_links
    
    def _identify_cloud_disk(self, url, alt_text="", span_text=""):
        """智能识别网盘类型"""
        # 首先检查alt_text和span_text
        text_to_check = f"{alt_text} {span_text}".lower()
        
        for disk_name, patterns in self.cloud_disk_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_to_check, re.I):
                    return disk_name
        
        # 然后检查URL
        for disk_name, patterns in self.cloud_disk_patterns.items():
            for pattern in patterns:
                if re.search(pattern, url, re.I):
                    return disk_name
        
        return "其他网盘"
    
    def _extract_password(self, html_text, url):
        """提取网盘密码"""
        # 在url附近查找密码
        url_escaped = re.escape(url[:50])  # 只匹配前50个字符
        patterns = [
            rf'{url_escaped}.*?[码码][:：]\s*(\w{{4}})',
            rf'密码[:：]\s*(\w{{4}}).*?{url_escaped}',
            rf'提取码[:：]\s*(\w{{4}})',
            rf'pwd=(\w{{4}})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html_text, re.S | re.I)
            if match:
                return match.group(1)
        
        return ""
    
    def searchContent(self, key, quick, pg):
        cache_key = f"search_{key}_{pg}"
        if cache_key in self.cache and time.time() - self.cache[cache_key]['timestamp'] < self.cache_timeout:
            return self.cache[cache_key]['data']
            
        result = {'list': []}
        try:
            url = f"{self.host}/search/?keyword={key}"
            if pg > 1:
                url = f"{self.host}/search/?keyword={key}&page={pg}"
                
            time.sleep(random.uniform(0.5, 1.0))
            rsp = self._smart_fetch(url)
            if rsp:
                result['list'] = self._fast_parse_video_list(rsp.text)
                # 缓存搜索结果
                self.cache[cache_key] = {
                    'data': result,
                    'timestamp': time.time()
                }
        except Exception as e:
            print(f"Search error: {e}")
        return result
    
    def playerContent(self, flag, id, vipFlags):
        """播放内容处理"""
        # 处理push协议
        if id.startswith("push://"):
            id = id.replace("push://", "")
        
        # 确保URL格式正确
        if not id.startswith(("http://", "https://")):
            if id.startswith("//"):
                id = "https:" + id
            else:
                id = "https://" + id
        
        # 智能获取合适的请求头
        headers = self._get_smart_headers(id)
        
        return {
            "parse": 0,  # 直连播放
            "playUrl": "",
            "url": id,
            "header": json.dumps(headers)
        }
    
    def _get_smart_headers(self, url):
        """根据URL智能生成请求头"""
        parsed = urlparse(url)
        domain = parsed.netloc
        
        headers = {
            "User-Agent": random.choice([
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
            ]),
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache"
        }
        
        # 为不同网盘设置特定Referer
        referer_map = {
            "pan.baidu.com": "https://pan.baidu.com/",
            "pan.quark.cn": "https://pan.quark.cn/",
            "aliyundrive.com": "https://www.aliyundrive.com/",
            "cloud.189.cn": "https://cloud.189.cn/",
            "pan.xunlei.com": "https://pan.xunlei.com/",
            "lanzou": "https://www.lanzou.com/",
            "123pan.com": "https://www.123pan.com/"
        }
        
        for key, ref in referer_map.items():
            if key in domain:
                headers["Referer"] = ref
                break
        else:
            headers["Referer"] = f"{self.host}/"
        
        return headers
    
    def _smart_fetch(self, url):
        """智能请求方法"""
        try:
            # 检查缓存
            cache_key = f"fetch_{hash(url)}"
            if cache_key in self.cache:
                cached = self.cache[cache_key]
                if time.time() - cached['timestamp'] < 60:  # 缓存1分钟
                    return cached['response']
            
            # 随机延迟
            time.sleep(random.uniform(0.1, 0.5))
            
            # 发送请求
            response = self.session.get(
                url,
                timeout=self.timeout/1000,
                verify=False,
                allow_redirects=True
            )
            
            if response.status_code == 200:
                response.encoding = response.apparent_encoding or 'utf-8'
                # 缓存成功响应
                self.cache[cache_key] = {
                    'response': response,
                    'timestamp': time.time()
                }
                return response
            elif response.status_code in [403, 429, 503]:
                print(f"被限制访问 {url}, 状态码: {response.status_code}")
                # 延迟后重试
                time.sleep(random.uniform(2, 4))
                return self._smart_fetch(url)
            else:
                print(f"请求失败 {url}, 状态码: {response.status_code}")
                return None
                
        except requests.exceptions.Timeout:
            print(f"请求超时: {url}")
            return None
        except Exception as e:
            print(f"请求异常 {url}: {e}")
            return None
    
    def clear_cache(self):
        """清理过期缓存"""
        current_time = time.time()
        expired_keys = []
        
        for key, value in self.cache.items():
            if current_time - value['timestamp'] > self.cache_timeout:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            print(f"清理了 {len(expired_keys)} 个过期缓存")
