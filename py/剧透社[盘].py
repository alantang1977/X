import sys
import json
import re
sys.path.append('..')
from base.spider import Spider
class Spider(Spider):
    def __init__(self):
        self.name = "剧透社"
        self.host = "https://1.star2.cn"
        self.timeout = 5000
        self.limit = 20
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        self.default_image = "https://images.gamedog.cn/gamedog/imgfile/20241205/05105843u5j9.png"
    
    def getName(self):
        return self.name
    
    def init(self, extend=""):
        print(f"============{extend}============")
    
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
            pattern = r'<li[^>]*>.*?<a[^>]*href="([^"]*)"[^>]*class="main"[^>]*>(.*?)</a>.*?</li>'
            for match in re.finditer(pattern, html_text, re.S):
                href = match.group(1)
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
            title = re.sub(r'^【[^】]+】', '', title).strip() or "未知标题"
            baidu_links = []
            quark_links = []
            
            link_pattern = r'<a[^>]*href="([^"]*)"[^>]*>.*?</a>'
            for match in re.finditer(link_pattern, html_text, re.S):
                href = match.group(1)
                if href:
                    if "pan.baidu.com" in href:
                        baidu_links.append(href)
                    elif "pan.quark.cn" in href:
                        quark_links.append(href)

            play_links = baidu_links + quark_links
            play_from = "剧透社" if play_links else "无资源"

            play_url_parts = []
            for link in play_links:
                if "pan.baidu.com" in link:
                    play_url_parts.append(f"百度${link}")
                else:
                    play_url_parts.append(f"夸克${link}")
            
            play_url = "#".join(play_url_parts) or "暂无资源$#"
            
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
            rsp = self.fetch(url, headers=self.headers, timeout=self.timeout)
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
            "header": json.dumps(self.headers)
        }
    
    def homeVideoContent(self):
        return {"list": []}
    
    def isVideoFormat(self, url):
        return False
    
    def localProxy(self, url, param):
        return {"parse": 0, "playUrl": "", "url": url}
    
    def manualVideoCheck(self, url):
        return {"parse": 0, "playUrl": "", "url": url}

        
