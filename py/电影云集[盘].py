"""
@header({
  searchable: 1,
  filterable: 1,
  quickSearch: 1,
  title: '电影云集',
  lang: 'hipy'
})
"""

import sys
import re
import json
import requests
import urllib.parse
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def __init__(self):
        self.name = "电影云集"
        self.host = "https://dyyjpro.com"
        self.timeout = 10
        self.limit = 20
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        self.default_image = "https://picsum.photos/300/400"
    
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
            if rsp.status_code != 200:
                return result
            html = rsp.text
            videos = []
            pattern = r'<article[^>]*>.*?<a[^>]*href="([^"]+)".*?<img[^>]*data-bg="([^"]+)".*?<h2[^>]*class="entry-title">.*?<a[^>]*href="([^"]+)"[^>]*title="([^"]+)".*?</h2>.*?</article>'
            matches = re.findall(pattern, html, re.S)
            if matches:
                for match in matches:
                    if len(match) >= 4:
                        videos.append({
                            "vod_id": match[2],
                            "vod_name": match[3],
                            "vod_pic": match[1],
                            "vod_remarks": "",
                            "vod_content": match[3]
                        })
                result['list'] = videos[:self.limit]
                return result
            
            pattern = r'<article[^>]*class="post-item[^>]*>.*?<a[^>]*href="([^"]+)"[^>]*title="([^"]+)".*?data-bg="([^"]+)".*?</article>'
            matches = re.findall(pattern, html, re.S)
            if matches:
                for match in matches:
                    if len(match) >= 3:
                        href, name, pic = match
                        if not href.startswith(('http://', 'https://')):
                            href = f"{self.host}{href}" if href.startswith('/') else f"{self.host}/{href}"
                        
                        if not pic.startswith(('http://', 'https://')):
                            pic = f"{self.host}{pic}" if pic.startswith('/') else f"https://{pic}"
                        
                        videos.append({
                                "vod_id": href,
                                "vod_name": name,
                                "vod_pic": pic or self.default_image,
                                "vod_remarks": "",
                                "vod_content": name
                            })
            
            result['list'] = videos[:self.limit]
        except Exception:
            pass
        return result
    
    def detailContent(self, array):
        result = {'list': []}
        if not array:
            return result
        
        try:
            vod_id = array[0]
            url = vod_id if vod_id.startswith('http') else f"{self.host}{vod_id}"
            rsp = requests.get(url, headers=self.headers, timeout=self.timeout)
            if rsp.status_code != 200:
                raise Exception(f"HTTP状态码: {rsp.status_code}")
            html = rsp.text

            title = "电影云集资源"
            for pattern in [
                r'<h1[^>]*class="post-title[^>]*>(.*?)</h1>',
                r'<title[^>]*>(.*?)</title>'
            ]:
                match = re.search(pattern, html, re.S | re.I)
                if match:
                    title = match.group(1).strip()
                    title = re.sub(r'<[^>]+>', '', title)
                    title = re.sub(r'_电影云集.*$', '', title)
                    break

            content_html = ""
            for pattern in [
                r'<div[^>]*class="post-content"[^>]*>(.*?)</div>',
                r'<article[^>]*class="post[^"]*"[^>]*>(.*?)</article>',
                r'<div[^>]*class="entry-content"[^>]*>(.*?)</div>'
            ]:
                match = re.search(pattern, html, re.S)
                if match:
                    content_html = match.group(1)
                    break
            
            if not content_html:
                content_html = html

            netdisk_patterns = [
                ('百度网盘', r'(https?://pan\.baidu\.com/s/[a-zA-Z0-9_-]+(?:\?[a-zA-Z0-9_=&-]*)?)'),
                ('夸克网盘', r'(https?://pan\.quark\.cn/s/[a-zA-Z0-9]+(?:\?[a-zA-Z0-9_=&-]*)?)')
            ]
            
            play_items = {}
            
            for netdisk_name, pattern in netdisk_patterns:
                matches = re.findall(pattern, content_html, re.I)
                if matches:
                    unique_links = list(dict.fromkeys(matches))
                    formatted_links = []
                    for full_link in unique_links:
                        if not full_link.startswith(('http://', 'https://')):
                            full_link = f"https://{full_link}"
                        display_name = f"{netdisk_name}"
                        push_link = f"push://{full_link}"
                        formatted_links.append(f"{display_name}${push_link}")
                    
                    if formatted_links:
                        play_items[netdisk_name] = formatted_links

            all_links = []

            for links in play_items.values():
                all_links.extend(links)

            if not all_links:
                http_links = re.findall(r'href=["\'](https?://[^"\']+)["\']', content_html)
                if http_links:
                    for i, link in enumerate(http_links[:3], 1):
                        all_links.append(f"链接{i}${link}")
                else:
                    all_links.append('暂无资源$#')
            
            play_from = '电影云集'
            play_url = '#'.join(all_links)

            vod_content = title
            if content_html:
                text_content = re.sub(r'<[^>]+>', ' ', content_html)
                text_content = re.sub(r'\s+', ' ', text_content).strip()
                if len(text_content) > 50:
                    vod_content = text_content[:150] + "..."

            vod_pic = self.default_image
            article_match = re.search(r'<article[^>]*class="post-content[^>]*>(.*?)</article>', html, re.S)
            if article_match:
                img_match = re.search(r'<img[^>]*src="([^"]*)"[^>]*>', article_match.group(1), re.I)
                if img_match:
                    pic_url = img_match.group(1).strip()
                    if pic_url and not pic_url.startswith('data:'):
                        if not pic_url.startswith(('http://', 'https://')):
                            if pic_url.startswith('./'):
                                pic_url = f"https://dyyjpro.com{pic_url[1:]}"
                            else:
                                pic_url = f"https://{pic_url}"
                        vod_pic = pic_url

            if vod_pic == self.default_image:
                for pattern in [
                    r'<meta[^>]*property="og:image"[^>]*content="([^"]*)"',
                    r'<meta[^>]*name="og:image"[^>]*content="([^"]*)"'
                ]:
                    match = re.search(pattern, html, re.I)
                    if match:
                        pic_url = match.group(1).strip()
                        if pic_url and not pic_url.startswith('data:'):
                            if not pic_url.startswith(('http://', 'https://')):
                                pic_url = f"https://{pic_url}"
                            vod_pic = pic_url
                            break

            vod_item = {
                'vod_id': url,
                'vod_name': title,
                'vod_pic': vod_pic,
                'vod_content': vod_content,
                'vod_remarks': f"共{len(play_items)}个网盘源" if play_items else "暂无网盘资源",
                'vod_play_from': play_from,
                'vod_play_url': play_url
            }
            
            result['list'].append(vod_item)
            
        except Exception as e:
            result['list'].append({
                'vod_id': 'error',
                'vod_name': '电影云集资源',
                'vod_pic': self.default_image,
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
            search_url = f"{self.host}/?s={encoded_key}" if pg == 1 else f"{self.host}/page/{pg}/?s={encoded_key}"
            
            rsp = requests.get(search_url, headers=self.headers, timeout=self.timeout)
            if rsp.status_code == 200:
                html = rsp.text
                videos = []
                pattern = r'<article[^>]*>.*?<a[^>]*href="([^"]+)".*?<img[^>]*data-bg="([^"]+)".*?</article>'
                matches = re.findall(pattern, html, re.S)
                
                for match in matches:
                    if len(match) >= 3:
                        href, pic, name = match
                        
                        if not href.startswith('http'):
                            href = f"{self.host}{href}" if href.startswith('/') else f"{self.host}/{href}"
                        
                        if not pic.startswith('http'):
                            pic = f"{self.host}{pic}" if pic.startswith('/') else f"{self.host}/{pic}"
                        
                        if href and name:
                            name = re.sub(r'<[^>]+>', '', name).strip()
                            videos.append({
                                "vod_id": href,
                                "vod_name": name,
                                "vod_pic": pic or self.default_image,
                                "vod_remarks": "",
                                "vod_content": name
                            })
                
                result['list'] = videos
                
        except Exception:
            pass
        
        return result
    
    def playerContent(self, flag, id, vipFlags):
        return {
            "parse": 0,
            "playUrl": "",
            "url": f"push://{id}",
            "header": ""
        }


