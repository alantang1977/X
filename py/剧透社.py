import sys
import json
import re
import time
import random
import requests
from urllib.parse import urljoin
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def __init__(self):
        self.name = "剧透社"
        self.host = "https://1.star2.cn"
        self.timeout = 10000
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
        # 将默认图片替换为指定固定图片
        self.default_image = "https://cnb.cool/junchao.tang/jtv/-/git/raw/main/Pictures/Chao.png"
        
        # 智能网盘识别配置
        self.cloud_disk_rules = {
            "百度网盘": [
                r'pan\.baidu\.com',
                r'yun\.baidu\.com',
                r'baidu\.com/s/',
                r'百度[网盘盘]?',
                r'bdpan'
            ],
            "夸克网盘": [
                r'pan\.quark\.cn',
                r'quark\.cn/s/',
                r'夸克[网盘盘]?',
                r'kkpan'
            ],
            "阿里云盘": [
                r'aliyundrive\.com',
                r'alipan\.com',
                r'阿里[云云]?[盘盘]',
                r'alypan'
            ],
            "天翼云盘": [
                r'cloud\.189\.cn',
                r'天翼[云云]?[盘盘]',
                r'189yun'
            ],
            "迅雷云盘": [
                r'pan\.xunlei\.com',
                r'迅雷[云云]?[盘盘]',
                r'xunlei'
            ],
            "蓝奏云": [
                r'lanzou[xtv]?\.com',
                r'蓝奏[云云]?',
                r'lanzou'
            ],
            "123云盘": [
                r'123pan\.com',
                r'123[云云]?[盘盘]',
                r'123pan'
            ],
            "城通网盘": [
                r'ctfile\.com',
                r'城通[网网]?[盘盘]',
                r'ctpan'
            ],
            "微云": [
                r'share\.weiyun\.com',
                r'weiyun\.com',
                r'微[信云][盘盘]'
            ]
        }
        
        # 创建会话保持
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # 请求缓存
        self.cache = {}
        self.cache_timeout = 300  # 5分钟缓存

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
        
        # 检查缓存
        cache_key = f"cat_{tid}_{pg}"
        if cache_key in self.cache and time.time() - self.cache[cache_key]['time'] < self.cache_timeout:
            return self.cache[cache_key]['data']
        
        try:
            # 添加随机延迟，避免请求过于频繁
            time.sleep(random.uniform(0.5, 1.5))  # 降低延迟提高速度
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
                
                # 缓存结果
                self.cache[cache_key] = {
                    'data': result,
                    'time': time.time()
                }
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
            # 检查缓存
            cache_key = f"detail_{array[0]}"
            if cache_key in self.cache and time.time() - self.cache[cache_key]['time'] < self.cache_timeout:
                return {'list': [self.cache[cache_key]['data']]}
            
            try:
                vod_id = array[0]
                detail_url = vod_id if vod_id.startswith("http") else f"{self.host}{vod_id}"
                time.sleep(random.uniform(0.3, 1))  # 降低延迟
                rsp = self.fetch(detail_url)
                if rsp:
                    vod = self._parse_detail_page(rsp.text, detail_url)
                    if vod:
                        result['list'] = [vod]
                        # 缓存结果
                        self.cache[cache_key] = {
                            'data': vod,
                            'time': time.time()
                        }
            except Exception as e:
                print(f"Detail parse error: {e}")
        return result
    
    def _parse_detail_page(self, html_text, detail_url):
        try:
            title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html_text, re.S)
            title = title_match.group(1).strip() if title_match else "未知标题"
            title = re.sub(r'^【[^】]+】', '', title).strip() or "未知标题"
            
            # 智能网盘链接识别
            disk_links = self._smart_extract_disk_links(html_text)
            
            # 构建播放URL
            if disk_links:
                play_parts = []
                for disk_info in disk_links:
                    disk_name = disk_info['name']
                    disk_url = disk_info['url']
                    disk_pwd = disk_info.get('pwd', '')
                    
                    display_name = disk_name
                    if disk_pwd:
                        display_name += f" 密码:{disk_pwd}"
                    play_parts.append(f"{display_name}${disk_url}")
                
                play_url = "#".join(play_parts)
                play_from = "剧透社"
            else:
                play_url = "暂无资源$#"
                play_from = "无资源"
            
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
    
    def _smart_extract_disk_links(self, html_text):
        """智能提取网盘链接"""
        disk_links = []
        found_urls = set()
        
        # 方法1: 从特定HTML结构中提取（针对剧透社网站结构）
        # 查找dlipp-cont-bd区域（根据提供的HTML代码）
        content_match = re.search(r'<div[^>]*class="[^"]*dlipp-cont-bd[^"]*"[^>]*>(.*?)</div>', html_text, re.S)
        if content_match:
            section_html = content_match.group(1)
            # 提取链接按钮
            button_pattern = r'<a[^>]*href="(https?://[^"]+)"[^>]*>.*?<img[^>]*alt="([^"]*)"[^>]*>.*?<span>([^<]+)</span>'
            for match in re.finditer(button_pattern, section_html, re.S):
                url = match.group(1).strip()
                alt_text = match.group(2).strip() if match.group(2) else ""
                span_text = match.group(3).strip() if match.group(3) else ""
                
                if url and url not in found_urls:
                    disk_name = self._identify_disk_type(url, alt_text, span_text)
                    # 提取密码
                    pwd = self._extract_password(url, html_text)
                    disk_links.append({
                        'name': disk_name,
                        'url': url,
                        'pwd': pwd
                    })
                    found_urls.add(url)
        
        # 方法2: 提取所有可能的网盘链接
        if not disk_links:
            link_pattern = r'href="(https?://[^"]+?(?:baidu|quark|aliyun|189|xunlei|lanzou|123pan|ctfile|weiyun)[^"]*)"'
            for match in re.finditer(link_pattern, html_text, re.I):
                url = match.group(1).strip()
                if url and url not in found_urls:
                    disk_name = self._identify_disk_type(url)
                    if disk_name != "其他网盘":
                        pwd = self._extract_password(url, html_text)
                        disk_links.append({
                            'name': disk_name,
                            'url': url,
                            'pwd': pwd
                        })
                        found_urls.add(url)
        
        # 方法3: 查找提取码模式
        if not disk_links:
            # 查找提取码和链接的组合
            pwd_link_pattern = r'提取[码码][:：]\s*(\w{4})\s*(?:链接|地址)[:：]\s*(https?://\S+)'
            for match in re.finditer(pwd_link_pattern, html_text, re.I):
                pwd = match.group(1)
                url = match.group(2).strip()
                if url and url not in found_urls:
                    disk_name = self._identify_disk_type(url)
                    disk_links.append({
                        'name': disk_name,
                        'url': url,
                        'pwd': pwd
                    })
                    found_urls.add(url)
        
        return disk_links
    
    def _identify_disk_type(self, url, alt_text="", span_text=""):
        """识别网盘类型"""
        # 优先从文本中识别
        text_to_check = f"{alt_text} {span_text}".lower()
        for disk_name, patterns in self.cloud_disk_rules.items():
            for pattern in patterns:
                if re.search(pattern, text_to_check, re.I):
                    return disk_name
        
        # 从URL中识别
        url_lower = url.lower()
        for disk_name, patterns in self.cloud_disk_rules.items():
            for pattern in patterns:
                if re.search(pattern, url_lower, re.I):
                    return disk_name
        
        return "其他网盘"
    
    def _extract_password(self, url, html_text):
        """提取网盘密码"""
        # 从URL中提取
        pwd_match = re.search(r'[?&]pwd=(\w{4})', url, re.I)
        if pwd_match:
            return pwd_match.group(1)
        
        # 从文本中提取
        # 在链接附近查找密码
        url_short = url[:50]  # 只匹配前50个字符
        pattern = rf'{re.escape(url_short)}.*?[码码][:：]\s*(\w{{4}})'
        match = re.search(pattern, html_text, re.S | re.I)
        if match:
            return match.group(1)
        
        return ""
    
    def searchContent(self, key, quick, pg):
        result = {'list': []}
        
        # 检查缓存
        cache_key = f"search_{key}_{pg}"
        if cache_key in self.cache and time.time() - self.cache[cache_key]['time'] < self.cache_timeout:
            return self.cache[cache_key]['data']
        
        try:
            url = f"{self.host}/search/?keyword={key}"
            if pg > 1:
                url = f"{self.host}/search/?keyword={key}&page={pg}"
                
            time.sleep(random.uniform(0.3, 1))  # 降低延迟
            rsp = self.fetch(url)
            if rsp:
                result['list'] = self._parse_video_list(rsp.text)
                # 缓存结果
                self.cache[cache_key] = {
                    'data': result,
                    'time': time.time()
                }
        except Exception as e:
            print(f"Search error: {e}")
        return result
    
    def playerContent(self, flag, id, vipFlags):
        """播放内容处理 - 保持原有推送逻辑"""
        if id.startswith("push://"):
            # 移除push://前缀
            play_url = id.replace("push://", "")
            return {
                "parse": 0, 
                "playUrl": "", 
                "url": play_url, 
                "header": ""
            }
        
        # 非push://链接，添加push://前缀（保持原有逻辑）
        return {
            "parse": 0,
            "playUrl": "",
            "url": f"push://{id}",
            "header": json.dumps(dict(self.session.headers))  # 使用会话headers
        }
    
    def fetch(self, url):
        """重写fetch方法，使用会话请求并处理反爬"""
        try:
            # 随机更换User-Agent
            self.session.headers["User-Agent"] = random.choice([
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
            ])
            
            response = self.session.get(
                url,
                timeout=self.timeout/1000,
                verify=False,
                allow_redirects=True
            )
            response.encoding = response.apparent_encoding  # 自动识别编码
            if response.status_code == 200:
                return response
            elif response.status_code in [403, 503]:
                print(f"被反爬拦截，状态码: {response.status_code}，尝试重试...")
                # 遇到反爬时延迟后重试一次
                time.sleep(random.uniform(2, 4))
                return self.fetch(url)
            else:
                print(f"请求失败，状态码: {response.status_code}")
                return None
        except Exception as e:
            print(f"请求异常: {e}")
            return None
    
    def clear_old_cache(self):
        """清理过期缓存"""
        current_time = time.time()
        expired_keys = []
        for key, cache_data in self.cache.items():
            if current_time - cache_data['time'] > self.cache_timeout:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            print(f"清理了 {len(expired_keys)} 个过期缓存")
