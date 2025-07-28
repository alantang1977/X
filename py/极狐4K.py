# -*- coding: utf-8 -*-
import json
import sys
import time
import requests
from base64 import b64decode, b64encode
from Crypto.Hash import MD5
from pyquery import PyQuery as pq
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def init(self, extend=""):
        pass

    def getName(self):
        return "4kfox影视"

    def isVideoFormat(self, url):
        return any(url.endswith(ext) for ext in ['.mp4', '.m3u8', '.flv', '.avi', '.mov'])

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    host = 'https://4kfox.com'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
        'Connection': 'keep-alive'
    }

    def homeContent(self, filter):
        """从导航栏提取分类"""
        result = {'class': [], 'filters': {}}
        try:
            resp = requests.get(self.host, headers=self.headers, timeout=10)
            doc = pq(resp.text)
            
            # 提取导航栏分类
            categories = doc('.nav-item a').items()
            for item in categories:
                href = item.attr('href')
                if href and '/category/' in href:
                    type_id = href.split('/')[-2] if href.endswith('/') else href.split('/')[-1]
                    type_name = item.text().strip()
                    if type_name and type_id:
                        result['class'].append({
                            'type_name': type_name,
                            'type_id': type_id
                        })
                        # 初始化空过滤器
                        result['filters'][type_id] = []
        except Exception as e:
            print(f"首页分类提取错误: {e}")
        return result

    def homeVideoContent(self):
        """从列表区域提取首页推荐视频"""
        try:
            resp = requests.get(self.host, headers=self.headers, timeout=10)
            doc = pq(resp.text)
            video_items = doc('.video-item').items()
            return {'list': self.parse_video_items(video_items)}
        except Exception as e:
            print(f"首页推荐提取错误: {e}")
            return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        """分类视频列表（支持分页）"""
        result = {'list': [], 'page': pg, 'pagecount': 0, 'limit': 20, 'total': 0}
        try:
            url = f"{self.host}/category/{tid}/page/{pg}/"
            resp = requests.get(url, headers=self.headers, timeout=10)
            doc = pq(resp.text)
            
            # 解析视频列表
            video_items = doc('.video-item').items()
            result['list'] = self.parse_video_items(video_items)
            
            # 解析分页信息
            total_pages = doc('.pagination .page-item:last-child a').attr('href')
            if total_pages:
                result['pagecount'] = int(total_pages.split('/')[-2])
                result['total'] = result['pagecount'] * result['limit']
        except Exception as e:
            print(f"分类列表提取错误: {e}")
        return result

    def detailContent(self, ids):
        """视频详情解析"""
        result = {'list': []}
        try:
            url = f"{self.host}/movies/{ids[0]}/"
            resp = requests.get(url, headers=self.headers, timeout=10)
            doc = pq(resp.text)
            
            # 解析基本信息
            vod = {
                'vod_name': doc('h1').text().strip(),
                'vod_pic': doc('.movie-poster img').attr('src') or '',
                'vod_content': doc('.movie-description').text().strip(),
                'type_name': doc('.movie-meta .genre a').text().strip(),
                'vod_year': doc('.movie-meta .year').text().strip(),
                'vod_area': doc('.movie-meta .country').text().strip(),
                'vod_actor': doc('.movie-meta .cast').text().strip(),
                'vod_director': doc('.movie-meta .director').text().strip(),
                'vod_remarks': doc('.movie-meta .quality').text().strip()
            }
            
            # 解析播放链接
            play_from = []
            play_urls = []
            sources = doc('.playlists .playlist').items()
            for idx, source in enumerate(sources):
                source_name = f"线路{idx+1}"
                play_from.append(source_name)
                
                episodes = []
                for ep in source('.episode').items():
                    ep_name = ep.text().strip()
                    ep_url = ep.attr('data-src') or ep.attr('href')
                    if ep_url and not ep_url.startswith('http'):
                        ep_url = f"{self.host}{ep_url}"
                    episodes.append(f"{ep_name}${self.e64(json.dumps({'url': ep_url}))}")
                
                play_urls.append('#'.join(episodes))
            
            vod['vod_play_from'] = '$$$'.join(play_from)
            vod['vod_play_url'] = '$$$'.join(play_urls)
            result['list'].append(vod)
        except Exception as e:
            print(f"视频详情提取错误: {e}")
        return result

    def searchContent(self, key, quick, pg="1"):
        """搜索功能"""
        result = {'list': [], 'page': pg}
        try:
            url = f"{self.host}/search/?q={key}&page={pg}"
            resp = requests.get(url, headers=self.headers, timeout=10)
            doc = pq(resp.text)
            
            video_items = doc('.video-item').items()
            result['list'] = self.parse_video_items(video_items)
        except Exception as e:
            print(f"搜索错误: {e}")
        return result

    def playerContent(self, flag, id, vipFlags):
        """播放解析"""
        try:
            ids = json.loads(self.d64(id))
            url = ids['url']
            headers = {
                'Referer': self.host,
                'User-Agent': self.headers['User-Agent']
            }
            return {'parse': 0, 'url': url, 'header': headers}
        except Exception as e:
            print(f"播放解析错误: {e}")
            return {'parse': 0, 'url': '', 'header': {}}

    def localProxy(self, param):
        try:
            data = json.loads(self.d64(param['data']))
            headers = {
                'Referer': data.get('r', self.host),
                'User-Agent': data.get('u', self.headers['User-Agent'])
            }
            resp = self.fetch(data['url'], headers=headers)
            return [200, 'video/mp4', resp.content, {}]
        except Exception as e:
            print(f"本地代理错误: {e}")
            return [500, 'text/plain', str(e).encode(), {}]

    def liveContent(self, url):
        return {}

    def parse_video_items(self, items):
        """解析视频列表项"""
        videos = []
        for item in items:
            link = item('a').attr('href')
            if not link or '/movies/' not in link:
                continue
                
            vod_id = link.split('/')[-2] if link.endswith('/') else link.split('/')[-1]
            if not vod_id:
                continue
                
            videos.append({
                'vod_id': vod_id,
                'vod_name': item('.video-title').text().strip(),
                'vod_pic': item('.video-img img').attr('src') or item('.video-img img').attr('data-src') or '',
                'vod_year': item('.video-meta .year').text().strip(),
                'vod_remarks': item('.video-meta .quality').text().strip()
            })
        return videos

    def e64(self, text):
        try:
            return b64encode(text.encode('utf-8')).decode('utf-8')
        except Exception as e:
            return ""

    def d64(self, encoded_text):
        try:
            return b64decode(encoded_text.encode('utf-8')).decode('utf-8')
        except Exception as e:
            return ""
