import re
import requests
import urllib.parse
from base.spider import Spider

class Spider(Spider):
    def __init__(self):
        self.name = "电影云集"
        self.host = "https://dyyjpro.com"
        self.timeout = 10
        self.limit = 20
        self.headers = {"User-Agent": "Mozilla/5.0"}
    
    def getName(self):
        return self.name
    
    def init(self, extend=""):
        pass
    
    def homeContent(self, filter):
        return {
            'class': [
                {"type_name": "电影", "type_id": "dianying"},
                {"type_name": "剧集", "type_id": "%e5%89%a7%e9%9b%86"},
                {"type_name": "动漫", "type_id": "dongman"},
                {"type_name": "综艺", "type_id": "zongyi"},
                {"type_name": "短剧", "type_id": "%e7%9f%ad%e5%89%a7"},
                {"type_name": "学习", "type_id": "xuexi"},
                {"type_name": "读物", "type_id": "%e8%af%bb%e7%89%a7"},
                {"type_name": "音频", "type_id": "%e9%9f%b3%e9%a2%91"}
            ]
        }
    
    def categoryContent(self, tid, pg, filter, extend):
        result = {'list': [], 'page': pg, 'pagecount': 9999, 'limit': self.limit, 'total': 999999}
        
        try:
            url = f"{self.host}/category/{tid}" if pg == 1 else f"{self.host}/category/{tid}/page/{pg}"
            rsp = requests.get(url, headers=self.headers, timeout=self.timeout)
            if rsp.status_code != 200: return result
            
            html = rsp.text
            videos = []
            
            # 提取文章块
            pattern = r'<article[^>]*>.*?<a[^>]*href="([^"]+)"[^>]*title="([^"]+)".*?data-bg="([^"]+)".*?</article>'
            matches = re.findall(pattern, html, re.S)
            
            for href, title, pic in matches:
                if not href.startswith('http'): href = f"{self.host}{href}" if href.startswith('/') else f"{self.host}/{href}"
                if pic and not pic.startswith('http'): pic = f"{self.host}{pic}" if pic.startswith('/') else pic
                videos.append({"vod_id": href, "vod_name": title, "vod_pic": pic or "https://picsum.photos/300/400", "vod_remarks": "", "vod_content": title})
            
            result['list'] = videos[:self.limit]
        except Exception:
            pass
        return result
    
    def detailContent(self, array):
        result = {'list': []}
        if not array: return result
        
        try:
            vod_id = array[0]
            url = vod_id if vod_id.startswith('http') else f"{self.host}{vod_id}"
            rsp = requests.get(url, headers=self.headers, timeout=self.timeout)
            if rsp.status_code != 200: raise Exception(f"HTTP状态码: {rsp.status_code}")
            
            html = rsp.text
            
            # 提取标题
            title = "电影云集资源"
            for pattern in [r'<h1[^>]*class="post-title[^>]*>(.*?)</h1>', r'<title[^>]*>(.*?)</title>']:
                match = re.search(pattern, html, re.S | re.I)
                if match:
                    title = match.group(1).strip()
                    title = re.sub(r'<[^>]+>', '', title)
                    title = re.sub(r'[_-].*$', '', title).strip()
                    break
            
            # 提取内容区域
            content_html = ""
            for pattern in [r'<div[^>]*class="post-content"[^>]*>(.*?)</div>', r'<article[^>]*class="post[^"]*"[^>]*>(.*?)</article>']:
                match = re.search(pattern, html, re.S)
                if match: content_html = match.group(1); break
            
            if not content_html: content_html = html
            
            # 提取网盘链接
            play_items = []
            
            # 夸克网盘
            quark_pattern = r'https?://pan\.quark\.cn/s/[a-zA-Z0-9]+(?:\?[^"\'\s]*)?'
            for link in list(dict.fromkeys(re.findall(quark_pattern, content_html, re.I))):
                play_items.append(('夸克网盘', link))
            
            # 百度网盘（提取码处理）
            baidu_pattern = r'https?://pan\.baidu\.com/s/[a-zA-Z0-9_-]+(?:\?[^"\'\s]*)?'
            baidu_matches = re.findall(baidu_pattern, content_html, re.I)
            for link in list(dict.fromkeys(baidu_matches)):
                # 提取码处理
                if '?pwd=' not in link and 'pwd=' not in link:
                    link_pos = content_html.find(link)
                    if link_pos != -1:
                        start, end = max(0, link_pos-100), min(len(content_html), link_pos+len(link)+100)
                        nearby = content_html[start:end]
                        pwd_match = re.search(r'[提取码密码pwd][：:]\s*([a-zA-Z0-9]{4})', nearby, re.I)
                        if pwd_match:
                            password = pwd_match.group(1)
                            separator = '?' if '?' not in link else '&'
                            link = f"{link}{separator}pwd={password}"
                play_items.append(('百度网盘', link))
            
            # 其他网盘
            other_patterns = [
                ('阿里云盘', r'https?://(?:www\.)?aliyundrive\.com/s/[a-zA-Z0-9]+'),
                ('迅雷云盘', r'https?://pan\.xunlei\.com/s/[a-zA-Z0-9]+'),
                ('115网盘', r'https?://115\.com/s/[a-zA-Z0-9]+'),
                ('磁力链接', r'magnet:\?xt=urn:btih:[a-zA-Z0-9]{32,}')
            ]
            for netdisk_name, pattern in other_patterns:
                matches = re.findall(pattern, content_html, re.I)
                for link in list(dict.fromkeys(matches)):
                    play_items.append((netdisk_name, link))
            
            # 构建播放链接
            if play_items:
                play_items.sort(key=lambda x: (0 if x[0] == '夸克网盘' else 1 if x[0] == '百度网盘' else 2))
                play_urls = [f"{name}$push://{link}" for i, (name, link) in enumerate(play_items, 1)]
                play_url = '#'.join(play_urls)
                play_from = '电影云集'
            else:
                play_url = '暂无资源$#'
                play_from = '电影云集'
            
            # 提取图片
            vod_pic = "https://picsum.photos/300/400"
            for pattern in [r'<meta[^>]*property="og:image"[^>]*content="([^"]*)"', r'<img[^>]*class="[^"]*wp-post-image[^"]*"[^>]*src="([^"]+)"']:
                match = re.search(pattern, html, re.I)
                if match:
                    img_url = match.group(1).strip()
                    if img_url and not img_url.startswith('data:'):
                        if not img_url.startswith('http'): img_url = f"{self.host}{img_url}" if img_url.startswith('/') else f"{self.host}/{img_url}"
                        vod_pic = img_url
                        break
            
            # 创建视频项
            result['list'].append({
                'vod_id': url,
                'vod_name': title,
                'vod_pic': vod_pic,
                'vod_content': title,
                'vod_remarks': f"共{len(play_items)}个网盘源" if play_items else "暂无网盘资源",
                'vod_play_from': play_from,
                'vod_play_url': play_url
            })
            
        except Exception as e:
            result['list'].append({
                'vod_id': 'error',
                'vod_name': '电影云集资源',
                'vod_pic': "https://picsum.photos/300/400",
                'vod_content': f'访问失败: {str(e)}',
                'vod_remarks': '',
                'vod_play_from': '电影云集',
                'vod_play_url': '暂无资源$#'
            })
        
        return result
    
    def searchContent(self, key, quick, pg):
        result = {'list': []}
        
        try:
            encoded_key = urllib.parse.quote(key)
            url = f"{self.host}/?s={encoded_key}" if pg == 1 else f"{self.host}/page/{pg}/?s={encoded_key}"
            rsp = requests.get(url, headers=self.headers, timeout=self.timeout)
            if rsp.status_code != 200: return result
            
            html = rsp.text
            videos = []
            
            pattern = r'<article[^>]*>.*?<a[^>]*href="([^"]+)"[^>]*title="([^"]+)".*?data-bg="([^"]+)".*?</article>'
            matches = re.findall(pattern, html, re.S)
            
            for href, title, pic in matches:
                if not href.startswith('http'): href = f"{self.host}{href}" if href.startswith('/') else f"{self.host}/{href}"
                if pic and not pic.startswith('http'): pic = f"{self.host}{pic}" if pic.startswith('/') else pic
                videos.append({"vod_id": href, "vod_name": title, "vod_pic": pic or "https://picsum.photos/300/400", "vod_remarks": "", "vod_content": title})
            
            result['list'] = videos
                
        except Exception:
            pass
        
        return result
    
    def playerContent(self, flag, id, vipFlags):
        try:
            id = str(id).strip()
            if id.startswith('push://'): id = id[7:]
            
            # 对百度网盘特殊处理
            headers = {}
            if "pan.baidu.com" in id:
                if not id.startswith('http'): id = f"https://{id}"
                headers = {"User-Agent": "Mozilla/5.0"}
                return {"parse": 0, "playUrl": "", "url": f"push://{id}", "header": str(headers)}
            else:
                if not id.startswith('http'): id = f"https://{id}"
                if not id.startswith('push://'): id = f"push://{id}"
                return {"parse": 0, "playUrl": "", "url": id, "header": ""}
            
        except Exception:
            return {"parse": 0, "playUrl": "", "url": "push://https://dyyjpro.com", "header": ""}