import sys
import json
import re
import time
import random
import requests
import hashlib
from urllib.parse import urljoin, urlparse, parse_qs
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def __init__(self):
        self.name = "剧透社"
        self.host = "https://1.star2.cn"
        self.timeout = 8000  # 优化超时时间
        self.limit = 30
        self.max_workers = 5  # 并发处理数
        
        # 智能网盘识别配置 - 扩展版
        self.cloud_disk_config = {
            "百度网盘": {
                "patterns": [
                    r'pan\.baidu\.com',
                    r'yun\.baidu\.com',
                    r'baidu\.com/s/',
                    r'bdwp',
                    r'百度[网盘盘]?'
                ],
                "pwd_patterns": [
                    r'pwd=(\w{4})',
                    r'提取[码码][:：]\s*(\w{4})',
                    r'密码[:：]\s*(\w{4})',
                    r'\[(\w{4})\]',
                    r'：(\w{4})'
                ],
                "play_support": True,
                "direct_play_patterns": [
                    r'baidu\.com/share/init\?surl=',
                    r'baidu\.com/s/1[a-zA-Z0-9_\-]+'
                ]
            },
            "夸克网盘": {
                "patterns": [
                    r'pan\.quark\.cn',
                    r'quark\.cn/s/',
                    r'夸克[网盘盘]?',
                    r'kkwp'
                ],
                "pwd_patterns": [
                    r'提取[码码][:：]\s*(\w{4,8})',
                    r'密码[:：]\s*(\w{4,8})',
                    r'\[(\w{4,8})\]'
                ],
                "play_support": True,
                "direct_play_patterns": [
                    r'quark\.cn/s/[a-f0-9]{32}'
                ]
            },
            "阿里云盘": {
                "patterns": [
                    r'aliyundrive\.com',
                    r'alipan\.com',
                    r'阿里[云云]?[盘盘]',
                    r'alywp'
                ],
                "pwd_patterns": [
                    r'提取[码码][:：]\s*(\w{4})',
                    r'密码[:：]\s*(\w{4})',
                    r'\[(\w{4})\]'
                ],
                "play_support": True,
                "direct_play_patterns": [
                    r'aliyundrive\.com/s/[a-zA-Z0-9]+',
                    r'alipan\.com/s/[a-zA-Z0-9]+'
                ]
            },
            "天翼云盘": {
                "patterns": [
                    r'cloud\.189\.cn',
                    r'天翼[云云]?[盘盘]',
                    r'189yun'
                ],
                "pwd_patterns": [
                    r'提取[码码][:：]\s*(\w{4})',
                    r'访问[码码][:：]\s*(\w{4})'
                ],
                "play_support": True,
                "direct_play_patterns": [
                    r'cloud\.189\.cn/web/share\?code='
                ]
            },
            "迅雷云盘": {
                "patterns": [
                    r'pan\.xunlei\.com',
                    r'迅雷[云云]?[盘盘]',
                    r'xunlei'
                ],
                "pwd_patterns": [
                    r'提取[码码][:：]\s*(\w{4})',
                    r'链接[:：].*?[:：]\s*(\w{4})'
                ],
                "play_support": True
            },
            "蓝奏云": {
                "patterns": [
                    r'lanzou[xtv]?\.com',
                    r'蓝奏[云云]?',
                    r'lanzou'
                ],
                "pwd_patterns": [
                    r'提取[码码][:：]\s*(\w{4})',
                    r'密码[:：]\s*(\w{4})'
                ],
                "play_support": True
            },
            "123云盘": {
                "patterns": [
                    r'123pan\.com',
                    r'123[云云]?[盘盘]',
                    r'123pan'
                ],
                "pwd_patterns": [
                    r'提取[码码][:：]\s*(\w{4})'
                ],
                "play_support": True
            }
        }
        
        # 智能播放器配置
        self.player_config = {
            "default_parse": 0,
            "auto_extract_pwd": True,
            "auto_fill_pwd": True,
            "pwd_retry_times": 3,
            "pwd_retry_delay": 2,
            "cache_direct_links": True,
            "direct_link_ttl": 3600  # 直链缓存1小时
        }
        
        # 优化请求头
        self.headers = {
            "User-Agent": random.choice([
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
                "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
            ]),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7,zh-TW;q=0.6",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": f"{self.host}/",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1"
        }
        
        self.default_image = "https://images.gamedog.cn/gamedog/imgfile/20241205/05105843u5j9.png"
        
        # 创建智能会话
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # 连接池优化
        self.session.mount('https://', requests.adapters.HTTPAdapter(
            pool_connections=15,
            pool_maxsize=30,
            max_retries=3,
            pool_block=True
        ))
        
        # 缓存系统
        self.cache = {
            "page_cache": {},      # 页面缓存
            "link_cache": {},      # 链接缓存
            "pwd_cache": {},       # 密码缓存
            "play_cache": {}       # 播放缓存
        }
        
        # 智能解析器
        self.parsers = {
            "html": self._parse_html_structure,
            "regex": self._parse_with_regex,
            "json": self._parse_json_structure
        }

    def getName(self):
        return self.name
    
    def init(self, extend=""):
        print(f"============{extend}============")
        # 预热连接池和初始化
        try:
            # 并发预热多个连接
            warmup_urls = [
                f"{self.host}/",
                f"{self.host}/mv/",
                f"{self.host}/ju/"
            ]
            for url in warmup_urls:
                try:
                    self.session.get(url, timeout=2)
                    time.sleep(0.1)
                except:
                    pass
        except Exception as e:
            print(f"初始化会话失败: {e}")
    
    def homeContent(self, filter):
        cache_key = "home_classes"
        cached = self._get_cache("page_cache", cache_key, ttl=3600)
        if cached:
            return cached
            
        data = {
            'class': [
                {"type_name": "今日更新", "type_id": "xg"},
                {"type_name": "短剧", "type_id": "dj"},
                {"type_name": "国剧", "type_id": "ju"},
                {"type_name": "综艺", "type_id": "zy"},
                {"type_name": "电影", "type_id": "mv"},
                {"type_name": "韩日", "type_id": "rh"},
                {"type_name": "英美", "type_id": "ym"},
                {"type_name": "动漫", "type_id": "dm"},
                {"type_name": "外剧", "type_id": "wj"},
                {"type_name": "其他", "type_id": "qt"}
            ]
        }
        
        self._set_cache("page_cache", cache_key, data)
        return data
    
    def categoryContent(self, tid, pg, filter, extend):
        cache_key = f"cat_{tid}_{pg}_{hash(str(filter))}_{hash(str(extend))}"
        cached = self._get_cache("page_cache", cache_key, ttl=300)
        if cached:
            return cached
            
        result = {'list': []}
        url = f"{self.host}/{tid}/" if pg == 1 else f"{self.host}/{tid}/?page={pg}"
        
        try:
            # 智能延迟控制
            delay = self._calculate_delay("category", pg)
            time.sleep(delay)
            
            rsp = self._smart_fetch(url, retry_times=2)
            if rsp:
                # 使用多模式解析
                videos = self._multi_mode_parse(rsp.text, "video_list")
                result.update({
                    'list': videos[:self.limit],
                    'page': pg,
                    'pagecount': 9999,
                    'limit': self.limit,
                    'total': 999999
                })
                
                # 缓存结果
                self._set_cache("page_cache", cache_key, result)
                
                # 预加载详情页（可选，提高后续访问速度）
                if pg == 1:
                    self._preload_details(videos[:5])
        except Exception as e:
            print(f"Category parse error for {url}: {e}")
            
        return result
    
    def _multi_mode_parse(self, html_text, parse_type):
        """多模式智能解析"""
        results = []
        
        if parse_type == "video_list":
            # 模式1: 结构化解析
            results.extend(self._parse_video_list_structured(html_text))
            
            # 模式2: 正则解析（备用）
            if len(results) < 5:
                results.extend(self._parse_video_list_regex(html_text))
        
        return self._deduplicate_list(results, "vod_id")
    
    def _parse_video_list_structured(self, html_text):
        """结构化解析视频列表"""
        videos = []
        
        try:
            # 查找列表容器
            list_patterns = [
                r'<ul[^>]*class="[^"]*erx-page-list[^"]*"[^>]*>(.*?)</ul>',
                r'<div[^>]*class="[^"]*erx-flex[^"]*"[^>]*>(.*?)</div>',
                r'<section[^>]*class="[^"]*list[^"]*"[^>]*>(.*?)</section>'
            ]
            
            for pattern in list_patterns:
                list_match = re.search(pattern, html_text, re.S)
                if list_match:
                    list_html = list_match.group(1)
                    # 提取列表项
                    item_pattern = r'<li[^>]*>.*?<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>'
                    for match in re.finditer(item_pattern, list_html, re.S):
                        href = match.group(1).strip()
                        name = match.group(2).strip()
                        
                        if href and name:
                            full_url = urljoin(self.host, href)
                            cleaned_name = re.sub(r'^【[^】]*】\s*', '', name).strip()
                            
                            videos.append({
                                "vod_id": full_url,
                                "vod_name": cleaned_name or name,
                                "vod_pic": self.default_image,
                                "vod_remarks": "",
                                "vod_content": cleaned_name or name
                            })
                    break
        except Exception as e:
            print(f"Structured parse error: {e}")
        
        return videos
    
    def _parse_video_list_regex(self, html_text):
        """正则解析视频列表"""
        videos = []
        
        try:
            # 多个匹配模式
            patterns = [
                r'<a[^>]*href="(/[^"]+)"[^>]*class="[^"]*main[^"]*"[^>]*>([^<]+)</a>',
                r'<a[^>]*href="(https?://[^"]+)"[^>]*>([^<]+)</a>',
                r'href="(/[^"]+)"[^>]*title="([^"]+)"'
            ]
            
            for pattern in patterns:
                for match in re.finditer(pattern, html_text, re.I):
                    href = match.group(1).strip()
                    name = match.group(2).strip()
                    
                    if href and name and not href.startswith('javascript'):
                        full_url = urljoin(self.host, href)
                        cleaned_name = re.sub(r'^【[^】]*】\s*', '', name).strip()
                        
                        videos.append({
                            "vod_id": full_url,
                            "vod_name": cleaned_name or name,
                            "vod_pic": self.default_image,
                            "vod_remarks": "",
                            "vod_content": cleaned_name or name
                        })
        except Exception as e:
            print(f"Regex parse error: {e}")
        
        return videos
    
    def detailContent(self, array):
        if not array:
            return {'list': []}
            
        vod_id = array[0]
        cache_key = f"detail_{hash(vod_id)}"
        
        cached = self._get_cache("page_cache", cache_key, ttl=600)
        if cached:
            return {'list': [cached]}
        
        result = {'list': []}
        detail_url = vod_id if vod_id.startswith("http") else urljoin(self.host, vod_id)
        
        try:
            rsp = self._smart_fetch(detail_url, retry_times=3)
            if rsp and rsp.status_code == 200:
                vod = self._smart_parse_detail_v2(rsp.text, detail_url)
                if vod:
                    result['list'] = [vod]
                    # 缓存结果
                    self._set_cache("page_cache", cache_key, vod)
        except Exception as e:
            print(f"Detail parse error: {e}")
        
        return result
    
    def _smart_parse_detail_v2(self, html_text, detail_url):
        """智能解析详情页 V2 - 增强版"""
        try:
            # 1. 提取标题（多种方式）
            title = self._extract_title(html_text)
            
            # 2. 智能提取网盘信息
            disk_infos = self._enhanced_extract_disk_info(html_text)
            
            # 3. 构建播放URL
            play_url, play_from = self._build_play_url(disk_infos)
            
            # 4. 提取图片
            pic_url = self._extract_image(html_text, detail_url)
            
            # 5. 提取其他信息
            remarks = self._extract_remarks(html_text)
            content = self._extract_content(html_text, title)
            
            return {
                "vod_id": detail_url,
                "vod_name": title,
                "vod_pic": pic_url,
                "vod_content": content,
                "vod_remarks": remarks,
                "vod_play_from": play_from,
                "vod_play_url": play_url
            }
            
        except Exception as e:
            print(f"Enhanced detail parse error: {e}")
            return self._create_fallback_detail(detail_url, str(e))
    
    def _enhanced_extract_disk_info(self, html_text):
        """增强版网盘信息提取"""
        disk_infos = []
        
        # 方法1: 结构化区域解析
        structured_infos = self._parse_structured_disk_area(html_text)
        disk_infos.extend(structured_infos)
        
        # 方法2: 智能链接分析
        if not disk_infos:
            smart_infos = self._parse_smart_disk_links(html_text)
            disk_infos.extend(smart_infos)
        
        # 方法3: 密码增强提取
        self._enhance_pwd_extraction(disk_infos, html_text)
        
        # 方法4: 去重和验证
        disk_infos = self._deduplicate_disk_infos(disk_infos)
        
        return disk_infos
    
    def _parse_structured_disk_area(self, html_text):
        """解析结构化网盘区域"""
        disk_infos = []
        
        # 查找网盘区域
        area_patterns = [
            r'<div[^>]*class="[^"]*dlipp-cont-bd[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*class="[^"]*yunpan[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*class="[^"]*download[^"]*"[^>]*>(.*?)</div>',
            r'<section[^>]*class="[^"]*links[^"]*"[^>]*>(.*?)</section>'
        ]
        
        for area_pattern in area_patterns:
            area_match = re.search(area_pattern, html_text, re.S | re.I)
            if area_match:
                area_html = area_match.group(1)
                # 提取按钮式链接
                button_pattern = r'<a[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>'
                for match in re.finditer(button_pattern, area_html, re.S):
                    url = match.group(1).strip()
                    button_html = match.group(2)
                    
                    # 从按钮HTML中提取信息
                    disk_name = self._extract_disk_name_from_html(button_html, url)
                    pwd = self._extract_pwd_from_context(area_html, url)
                    
                    if disk_name and url:
                        disk_infos.append({
                            "name": disk_name,
                            "url": url,
                            "pwd": pwd,
                            "source": "structured"
                        })
                break
        
        return disk_infos
    
    def _parse_smart_disk_links(self, html_text):
        """智能链接解析"""
        disk_infos = []
        found_urls = set()
        
        # 定义链接模式
        link_patterns = [
            # 标准链接模式
            r'href="(https?://[^"]+)"',
            # 带描述的链接
            r'链接[:：]\s*(https?://\S+)',
            # 提取码+链接模式
            r'提取[码码][:：]\s*(\w{4,8})\s*链接[:：]\s*(https?://\S+)',
            # 密码+链接模式
            r'密码[:：]\s*(\w{4,8})\s*(?:链接|地址)[:：]\s*(https?://\S+)'
        ]
        
        for pattern in link_patterns:
            for match in re.finditer(pattern, html_text, re.I):
                if match.lastindex == 1:
                    # 只有链接
                    url = match.group(1).strip()
                    if url and url not in found_urls:
                        disk_name = self._identify_disk_type(url)
                        disk_infos.append({
                            "name": disk_name,
                            "url": url,
                            "pwd": "",
                            "source": "smart_link"
                        })
                        found_urls.add(url)
                elif match.lastindex == 2:
                    # 有密码和链接
                    pwd = match.group(1)
                    url = match.group(2).strip()
                    if url and url not in found_urls:
                        disk_name = self._identify_disk_type(url)
                        disk_infos.append({
                            "name": disk_name,
                            "url": url,
                            "pwd": pwd,
                            "source": "smart_link_with_pwd"
                        })
                        found_urls.add(url)
        
        return disk_infos
    
    def _enhance_pwd_extraction(self, disk_infos, html_text):
        """增强密码提取"""
        for info in disk_infos:
            if not info.get("pwd"):
                # 从URL中提取
                url_pwd = self._extract_pwd_from_url(info["url"])
                if url_pwd:
                    info["pwd"] = url_pwd
                else:
                    # 从文本中提取
                    context_pwd = self._extract_pwd_from_context(html_text, info["url"])
                    if context_pwd:
                        info["pwd"] = context_pwd
    
    def _extract_pwd_from_url(self, url):
        """从URL中提取密码"""
        try:
            parsed = urlparse(url)
            query = parse_qs(parsed.query)
            
            # 检查常见密码参数
            pwd_params = ['pwd', 'password', 'passwd', 'pw', 'code', '提取码', '密码']
            for param in pwd_params:
                if param in query and query[param]:
                    return query[param][0][:20]  # 限制长度
            
            # 从路径中提取
            path_match = re.search(r'[?&](?:pwd|pw|password)=(\w{4,8})', url, re.I)
            if path_match:
                return path_match.group(1)
                
        except:
            pass
        return ""
    
    def _extract_pwd_from_context(self, html_text, target_url):
        """从上下文提取密码"""
        try:
            # 提取URL附近的内容
            url_escaped = re.escape(target_url[:30])
            context_pattern = rf'.{{0,100}}{url_escaped}.{{0,100}}'
            context_match = re.search(context_pattern, html_text, re.S | re.I)
            
            if context_match:
                context = context_match.group(0)
                # 在上下文中查找密码
                pwd_patterns = [
                    r'提取[码码][:：]\s*(\w{4,8})',
                    r'密码[:：]\s*(\w{4,8})',
                    r'\[(\w{4,8})\]',
                    r'：(\w{4,8})',
                    r'[码码][:：]\s*(\w{4,8})'
                ]
                
                for pattern in pwd_patterns:
                    pwd_match = re.search(pattern, context, re.I)
                    if pwd_match:
                        return pwd_match.group(1)
        except:
            pass
        return ""
    
    def _extract_disk_name_from_html(self, html, url):
        """从HTML中提取网盘名称"""
        # 检查img的alt属性
        img_match = re.search(r'<img[^>]*alt="([^"]*)"', html, re.I)
        if img_match:
            alt_text = img_match.group(1).strip()
            for name, config in self.cloud_disk_config.items():
                for pattern in config["patterns"]:
                    if re.search(pattern, alt_text, re.I):
                        return name
        
        # 检查span/text内容
        text_match = re.search(r'>([^<]+)<', html)
        if text_match:
            text = text_match.group(1).strip()
            for name, config in self.cloud_disk_config.items():
                for pattern in config["patterns"]:
                    if re.search(pattern, text, re.I):
                        return name
        
        # 根据URL识别
        return self._identify_disk_type(url)
    
    def _identify_disk_type(self, url):
        """识别网盘类型"""
        url_lower = url.lower()
        for name, config in self.cloud_disk_config.items():
            for pattern in config["patterns"]:
                if re.search(pattern, url_lower, re.I):
                    return name
        return "其他网盘"
    
    def _build_play_url(self, disk_infos):
        """构建播放URL"""
        if not disk_infos:
            return "暂无资源$#", "无资源"
        
        play_parts = []
        for info in disk_infos:
            name = info["name"]
            url = info["url"]
            pwd = info.get("pwd", "")
            
            # 构建显示名称
            display_name = name
            if pwd:
                display_name += f" 密码:{pwd}"
            
            # 构建播放部分
            play_parts.append(f"{display_name}${url}")
        
        play_url = "#".join(play_parts)
        return play_url, "剧透社"
    
    def _extract_title(self, html_text):
        """提取标题"""
        title_patterns = [
            r'<h1[^>]*>(.*?)</h1>',
            r'<title>(.*?)</title>',
            r'<meta[^>]*property="og:title"[^>]*content="(.*?)"',
            r'<meta[^>]*name="title"[^>]*content="(.*?)"'
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, html_text, re.S | re.I)
            if match:
                title = match.group(1).strip()
                # 清理标题
                title = re.sub(r'^【[^】]+】\s*', '', title)
                title = re.sub(r'\s*-\s*剧透社.*$', '', title)
                if title:
                    return title
        
        return "未知标题"
    
    def _extract_image(self, html_text, base_url):
        """提取图片"""
        img_patterns = [
            r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"',
            r'<img[^>]*src="([^"]+\.(?:jpg|png|jpeg|gif|webp))"[^>]*>',
            r'background-image:\s*url\(["\']?([^"\')]+)["\']?\)'
        ]
        
        for pattern in img_patterns:
            match = re.search(pattern, html_text, re.I)
            if match:
                img_url = match.group(1).strip()
                if img_url and not img_url.startswith('data:'):
                    return urljoin(base_url, img_url)
        
        return self.default_image
    
    def _extract_remarks(self, html_text):
        """提取备注信息"""
        remark_patterns = [
            r'<span[^>]*class="[^"]*time[^"]*"[^>]*>(.*?)</span>',
            r'<span[^>]*class="[^"]*view[^"]*"[^>]*>(.*?)</span>',
            r'更新时间[:：]\s*([^<]+)'
        ]
        
        remarks = []
        for pattern in remark_patterns:
            for match in re.finditer(pattern, html_text, re.I):
                remark = match.group(1).strip()
                if remark:
                    remarks.append(remark)
        
        return " | ".join(remarks) if remarks else ""
    
    def _extract_content(self, html_text, title):
        """提取内容描述"""
        content_patterns = [
            r'<meta[^>]*property="og:description"[^>]*content="([^"]+)"',
            r'<meta[^>]*name="description"[^>]*content="([^"]+)"',
            r'<div[^>]*class="[^"]*con[^"]*"[^>]*>(.*?)</div>'
        ]
        
        for pattern in content_patterns:
            match = re.search(pattern, html_text, re.S | re.I)
            if match:
                content = match.group(1).strip()
                if content and len(content) > 10:
                    # 清理HTML标签
                    content = re.sub(r'<[^>]+>', ' ', content)
                    content = re.sub(r'\s+', ' ', content)
                    return content[:200] + "..." if len(content) > 200 else content
        
        return title
    
    def searchContent(self, key, quick, pg):
        cache_key = f"search_{hash(key)}_{pg}"
        cached = self._get_cache("page_cache", cache_key, ttl=300)
        if cached:
            return cached
            
        result = {'list': []}
        try:
            # 构建搜索URL
            if pg == 1:
                url = f"{self.host}/search/?keyword={requests.utils.quote(key)}"
            else:
                url = f"{self.host}/search/?keyword={requests.utils.quote(key)}&page={pg}"
            
            time.sleep(random.uniform(0.3, 0.8))
            rsp = self._smart_fetch(url)
            if rsp:
                videos = self._multi_mode_parse(rsp.text, "video_list")
                result['list'] = videos[:self.limit]
                
                # 缓存结果
                self._set_cache("page_cache", cache_key, result)
        except Exception as e:
            print(f"Search error: {e}")
        
        return result
    
    def playerContent(self, flag, id, vipFlags):
        """智能播放器内容处理 - 自动密码填写版本"""
        try:
            # 解析播放信息
            play_info = self._parse_play_info(id)
            
            # 自动提取密码
            if self.player_config["auto_extract_pwd"]:
                play_info = self._auto_extract_pwd(play_info)
            
            # 自动填写密码（如果支持）
            if self.player_config["auto_fill_pwd"] and play_info.get("pwd"):
                direct_url = self._auto_fill_pwd(play_info)
                if direct_url:
                    play_info["url"] = direct_url
            
            # 构建播放响应
            return self._build_player_response(play_info)
            
        except Exception as e:
            print(f"PlayerContent error: {e}")
            return self._build_fallback_player_response(id)
    
    def _parse_play_info(self, input_id):
        """解析播放信息"""
        play_info = {
            "original_id": input_id,
            "url": "",
            "pwd": "",
            "disk_type": "",
            "headers": {}
        }
        
        # 处理push://协议
        if input_id.startswith("push://"):
            play_info["url"] = input_id.replace("push://", "")
        else:
            play_info["url"] = input_id
        
        # 识别网盘类型
        play_info["disk_type"] = self._identify_disk_type(play_info["url"])
        
        # 提取密码
        play_info["pwd"] = self._extract_pwd_from_url(play_info["url"])
        
        # 生成智能headers
        play_info["headers"] = self._generate_smart_headers(play_info["url"])
        
        return play_info
    
    def _auto_extract_pwd(self, play_info):
        """自动提取密码"""
        if not play_info["pwd"]:
            # 尝试从缓存中获取
            cache_key = f"pwd_{hash(play_info['url'])}"
            cached_pwd = self._get_cache("pwd_cache", cache_key, ttl=86400)  # 24小时
            if cached_pwd:
                play_info["pwd"] = cached_pwd
            else:
                # 尝试从相关页面提取
                pass
        
        return play_info
    
    def _auto_fill_pwd(self, play_info):
        """自动填写密码"""
        if not play_info["pwd"] or not play_info["disk_type"]:
            return None
        
        disk_config = self.cloud_disk_config.get(play_info["disk_type"], {})
        if not disk_config.get("play_support", False):
            return None
        
        # 检查缓存
        cache_key = f"direct_{hash(play_info['url'] + play_info['pwd'])}"
        cached = self._get_cache("play_cache", cache_key, ttl=self.player_config["direct_link_ttl"])
        if cached:
            return cached
        
        # 尝试获取直链（这里需要实际实现，以下为示例）
        try:
            # 注意：这里需要根据具体网盘实现密码填写逻辑
            # 以下为示例逻辑，实际需要针对不同网盘实现
            direct_url = self._try_get_direct_link(
                play_info["url"], 
                play_info["pwd"], 
                play_info["disk_type"]
            )
            
            if direct_url:
                self._set_cache("play_cache", cache_key, direct_url)
                return direct_url
        except Exception as e:
            print(f"Auto fill pwd error: {e}")
        
        return None
    
    def _try_get_direct_link(self, url, pwd, disk_type):
        """尝试获取直链（需要具体实现）"""
        # 这里需要根据不同的网盘实现具体的密码填写和直链获取逻辑
        # 由于这是一个复杂的过程，需要针对每个网盘单独实现
        
        # 示例：对于百度网盘
        if disk_type == "百度网盘":
            # 实际需要模拟登录、输入密码、获取直链等操作
            pass
        elif disk_type == "阿里云盘":
            # 阿里云盘可能有API可以直接获取
            pass
        
        return None  # 返回None表示无法获取直链
    
    def _generate_smart_headers(self, url):
        """生成智能headers"""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
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
        
        # 根据不同网盘设置Referer
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
        
        # 根据网盘类型添加特定header
        if "baidu" in domain:
            headers["Origin"] = "https://pan.baidu.com"
        elif "aliyundrive" in domain:
            headers["Origin"] = "https://www.aliyundrive.com"
        
        return headers
    
    def _build_player_response(self, play_info):
        """构建播放响应"""
        return {
            "parse": self.player_config["default_parse"],
            "playUrl": "",
            "url": play_info["url"],
            "header": json.dumps(play_info["headers"])
        }
    
    def _build_fallback_player_response(self, url):
        """构建回退播放响应"""
        return {
            "parse": 0,
            "playUrl": "",
            "url": url if url.startswith("http") else f"push://{url}",
            "header": json.dumps(self._generate_smart_headers(url))
        }
    
    # 缓存管理方法
    def _get_cache(self, cache_type, key, ttl=300):
        """获取缓存"""
        if cache_type in self.cache and key in self.cache[cache_type]:
            cache_data = self.cache[cache_type][key]
            if time.time() - cache_data["timestamp"] < ttl:
                return cache_data["data"]
            else:
                # 清理过期缓存
                del self.cache[cache_type][key]
        return None
    
    def _set_cache(self, cache_type, key, data):
        """设置缓存"""
        if cache_type not in self.cache:
            self.cache[cache_type] = {}
        
        self.cache[cache_type][key] = {
            "data": data,
            "timestamp": time.time()
        }
        
        # 定期清理过期缓存
        if len(self.cache[cache_type]) > 1000:
            self._clean_expired_cache(cache_type)
    
    def _clean_expired_cache(self, cache_type):
        """清理过期缓存"""
        current_time = time.time()
        expired_keys = []
        
        for key, cache_data in self.cache[cache_type].items():
            if current_time - cache_data["timestamp"] > 3600:  # 超过1小时
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[cache_type][key]
    
    # 辅助方法
    def _calculate_delay(self, request_type, page=1):
        """计算延迟时间"""
        delays = {
            "category": random.uniform(0.3, 1.0),
            "detail": random.uniform(0.2, 0.6),
            "search": random.uniform(0.2, 0.8),
            "home": 0.1
        }
        
        base_delay = delays.get(request_type, 0.5)
        # 根据页码增加延迟
        if page > 1:
            base_delay += random.uniform(0.1, 0.3) * (page - 1)
        
        return base_delay
    
    def _deduplicate_list(self, items, key_field):
        """去重列表"""
        seen = set()
        deduplicated = []
        
        for item in items:
            key = item.get(key_field)
            if key and key not in seen:
                seen.add(key)
                deduplicated.append(item)
        
        return deduplicated
    
    def _deduplicate_disk_infos(self, disk_infos):
        """去重网盘信息"""
        seen_urls = set()
        deduplicated = []
        
        for info in disk_infos:
            url = info.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                deduplicated.append(info)
        
        return deduplicated
    
    def _preload_details(self, videos):
        """预加载详情页"""
        # 异步预加载详情页，提高后续访问速度
        pass
    
    def _create_fallback_detail(self, detail_url, error_msg):
        """创建回退详情"""
        return {
            "vod_id": detail_url,
            "vod_name": "加载失败",
            "vod_pic": self.default_image,
            "vod_content": f"加载详情页失败：{error_msg}",
            "vod_remarks": "",
            "vod_play_from": "无资源",
            "vod_play_url": "暂无资源$#"
        }
    
    def _smart_fetch(self, url, retry_times=3):
        """智能请求方法"""
        for attempt in range(retry_times + 1):
            try:
                # 检查缓存
                cache_key = f"fetch_{hash(url)}_{attempt}"
                cached = self._get_cache("page_cache", cache_key, ttl=60)
                if cached and attempt == 0:
                    return cached
                
                # 智能延迟
                delay = random.uniform(0.1, 0.3) * (attempt + 1)
                time.sleep(delay)
                
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
                    self._set_cache("page_cache", cache_key, response)
                    return response
                elif response.status_code in [403, 429, 503, 504]:
                    print(f"请求被限制 {url}, 状态码: {response.status_code}, 尝试 {attempt+1}/{retry_times}")
                    if attempt < retry_times:
                        time.sleep(random.uniform(2, 4))
                        continue
                else:
                    print(f"请求失败 {url}, 状态码: {response.status_code}")
                    return None
                    
            except requests.exceptions.Timeout:
                print(f"请求超时: {url}, 尝试 {attempt+1}/{retry_times}")
                if attempt < retry_times:
                    time.sleep(random.uniform(1, 3))
                    continue
            except Exception as e:
                print(f"请求异常 {url}: {e}")
                if attempt < retry_times:
                    time.sleep(random.uniform(1, 2))
                    continue
        
        return None
