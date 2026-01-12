import sys
import json
import re
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def __init__(self):
        self.name = "电影云集"
        self.host = "https://dyyjpro.com"
        self.timeout = 10000
        self.limit = 20
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        self.default_image = "https://picsum.photos/300/400"
    
    def getName(self):
        return self.name
    
    def init(self, extend=""):
        print(f"============{extend}============")
    
    def homeContent(self, filter):
        return {
            'class': [
                {"type_name": "电影", "type_id": "dianying"},
                {"type_name": "剧集", "type_id": "剧集"},
                {"type_name": "动漫", "type_id": "dongman"},
                {"type_name": "综艺", "type_id": "zongyi"},
                {"type_name": "短剧", "type_id": "短剧"},
                {"type_name": "学习", "type_id": "xuexi"},
                {"type_name": "读物", "type_id": "读物"},
                {"type_name": "音频", "type_id": "音频"}
            ]
        }
    
    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        url = f"{self.host}/category/{tid}/" if pg == 1 else f"{self.host}/category/{tid}/page/{pg}/"
            
        try:
            rsp = self.fetch(url, headers=self.headers, timeout=self.timeout)
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
            pattern = r'<article[^>]*class="[^"]*post-item[^"]*"[^>]*>(.*?)</article>'
            for match in re.finditer(pattern, html_text, re.S):
                item_html = match.group(1)
                href_match = re.search(r'<a[^>]*href="([^"]*)"[^>]*>', item_html, re.S)
                if not href_match:
                    continue
                href = href_match.group(1)
                title_match = re.search(r'<a[^>]*title="([^"]*)"', item_html, re.S)
                title = title_match.group(1).strip() if title_match else ""
                
                if not title:
                    h2_match = re.search(r'<h2[^>]*>(.*?)</h2>', item_html, re.S)
                    if h2_match:
                        title = re.sub(r'<[^>]+>', '', h2_match.group(1)).strip()
                
                if not href or not title:
                    continue
                img_match = re.search(r'<img[^>]*src="([^"]*)"[^>]*>', item_html, re.S)
                if not img_match:
                    img_match = re.search(r'data-bg="([^"]*)"', item_html, re.S)
                
                img_url = img_match.group(1) if img_match else self.default_image
                
                videos.append({
                    "vod_id": build_full_url(href),
                    "vod_name": title,
                    "vod_pic": build_full_url(img_url) if img_url.startswith("/") else img_url,
                    "vod_remarks": "",
                    "vod_content": title
                })
        except Exception as e:
            print(f"Parse video list error: {e}")
        return videos[:self.limit]
    
    def detailContent(self, array):
        result = {'list': []}
        if array:
            try:
                vod_id = array[0]
                detail_url = vod_id if vod_id.startswith("http") else f"{self.host}{vod_id}"
                rsp = self.fetch(detail_url, headers=self.headers, timeout=self.timeout)
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
            title = re.sub(r'<[^>]+>', '', title).strip()
            content_match = re.search(r'<div[^>]*class="[^"]*post-content[^"]*"[^>]*>.*?<p>(.*?)</p>', html_text, re.S)
            content = content_match.group(1).strip() if content_match else title
            img_match = re.search(r'<meta[^>]*property="og:image"[^>]*content="([^"]*)"', html_text, re.S)
            if not img_match:
                img_match = re.search(r'<img[^>]*class="[^"]*wp-post-image[^"]*"[^>]*src="([^"]*)"', html_text, re.S)
            img_url = img_match.group(1) if img_match else self.default_image
            if img_url and not img_url.startswith("http"):
                img_url = f"{self.host}{img_url}" if img_url.startswith("/") else f"{self.host}/{img_url}"
            pan_links = []
            link_pattern = r'<a[^>]*href="([^"]*)"[^>]*>.*?</a>'
            for match in re.finditer(link_pattern, html_text, re.S):
                href = match.group(1)
                if href and ("pan.baidu.com" in href or "pan.quark.cn" in href):
                    pan_links.append(href)
            play_from = []
            play_url = []
            baidu_links = [link for link in pan_links if "pan.baidu.com" in link]
            quark_links = [link for link in pan_links if "pan.quark.cn" in link]
            all_links = []
            if baidu_links:
                all_links.extend([f"百度网盘${link}" for link in baidu_links])
            if quark_links:
                all_links.extend([f"夸克网盘${link}" for link in quark_links])
            if all_links:
                play_from.append("电影云集")
                play_url.append("#".join(all_links))
            else:
                play_from = ["无资源"]
                play_url = ["暂无资源$#"]
            
            return {
                "vod_id": detail_url,
                "vod_name": title,
                "vod_pic": img_url,
                "vod_content": content,
                "vod_remarks": f"共{len(pan_links)}个网盘源" if pan_links else "暂无网盘资源",
                "vod_play_from": "$$$".join(play_from),
                "vod_play_url": "$$$".join(play_url)
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
            encoded_key = key.replace(" ", "+")
            url = f"{self.host}/?cat=&s={encoded_key}" if pg == 1 else f"{self.host}/page/{pg}?cat=&s={encoded_key}"
            rsp = self.fetch(url, headers=self.headers, timeout=self.timeout)
            if rsp:
                result['list'] = self._parse_video_list(rsp.text)
        except Exception as e:
            print(f"Search error: {e}")
        return result
    
    def playerContent(self, flag, id, vipFlags):
        if id.startswith("http"):
            return {
                "parse": 0,
                "playUrl": "",
                "url": f"push://{id}",
                "header": json.dumps(self.headers)
            }
        return {
            "parse": 0,
            "playUrl": "",
            "url": id,
            "header": json.dumps(self.headers)
        }
    
    def homeVideoContent(self):
        return {
            'list': []
        }
    
    def isVideoFormat(self, url):
        video_formats = ['.mp4', '.m3u8', '.flv', '.avi', '.mkv', '.wmv', '.rmvb', '.mov']
        return any(url.lower().endswith(fmt) for fmt in video_formats)
    
    def localProxy(self, url, param):
        return {
            "parse": 0,
            "playUrl": "",
            "url": url,
            "header": ""
        }
    
    def manualVideoCheck(self, url):
        return True
