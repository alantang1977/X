# -*- coding: utf-8 -*-
# 麦田影院 - 精简优化版
import re
import sys
import json
from urllib.parse import quote, unquote, urljoin
from pyquery import PyQuery as pq
from xml.etree import ElementTree as ET
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def init(self, extend=""):
        self.host = "https://www.mtyy5.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 11; MI 11) AppleWebKit/537.36 TVBox/1.0',
            'Accept': 'text/html,application/xml;q=0.9,*/*;q=0.8',
            'Referer': self.host,
            'Connection': 'keep-alive'
        }
        self.source_map = {"NBY":"高清NB源","1080zyk":"超清YZ源","ffm3u8":"极速FF源","lzm3u8":"稳定LZ源","yzzy":"YZ源"}
        self.DEFAULT_PIC = "https://pic.rmb.bdstatic.com/bjh/1d0b02d0f57f0a4212da8865de018520.jpeg"

    def getName(self):
        return "麦田影院"

    # 合并工具方法：编码修复+文本清理
    def clean_text(self, text):
        if not text: return ""
        try:
            if isinstance(text, bytes):
                text = text.decode('utf-8', errors='ignore') if 'utf-8' in str(text) else text.decode('gbk', errors='ignore')
            if '\\u' in text: text = text.encode('utf-8').decode('unicode_escape', errors='ignore')
            return re.sub(r'[\x00-\x1f\x7f]', '', text).strip()
        except:
            return str(text)

    # 简化请求方法
    def fetch_page(self, url, headers=None):
        try:
            resp = self.fetch(url, headers=headers or self.headers, timeout=15)
            resp.encoding = 'utf-8'
            if resp.status_code != 200: raise Exception(f"HTTP {resp.status_code}")
            return resp.text
        except Exception as e:
            self.log(f"Fetch err: {str(e)}")
            return ""

    # 首页内容
    def homeContent(self, filter):
        html = self.fetch_page(self.host)
        doc = pq(html) if html else pq('')
        result = {'class': [], 'list': []}

        # 提取分类
        for a in doc('div.head-nav a[href*="/vodtype/"]').items():
            if (cid := re.search(r'/vodtype/(\d+)\.html', a.attr('href'))):
                result['class'].append({'type_name': self.clean_text(a.text()), 'type_id': cid.group(1)})

        # 提取首页影片
        for box in doc('.public-list-box.public-pic-b').items():
            if (link := box.find('a.public-list-exp')) and (vid := re.search(r'/voddetail/(\d+)\.html', link.attr('href'))):
                img = link.find('img')
                result['list'].append({
                    'vod_id': vid.group(1),
                    'vod_name': self.clean_text(link.attr('title') or img.attr('alt')),
                    'vod_pic': urljoin(self.host, img.attr('data-src') or img.attr('src') or ""),
                    'vod_remarks': self.clean_text(box.find('.public-prt').text())
                })
        return result

    # 分类内容
    def categoryContent(self, tid, pg, filter, extend):
        url = f"{self.host}/vodtype/{tid}-{pg}.html" if int(pg) > 1 else f"{self.host}/vodtype/{tid}.html"
        html = self.fetch_page(url)
        doc = pq(html) if html else pq('')
        videos = []

        for box in doc('.public-list-box.public-pic-b').items():
            if (link := box.find('a')) and (vid := re.search(r'/voddetail/(\d+)\.html', link.attr('href'))):
                img = link.find('img')
                videos.append({
                    'vod_id': vid.group(1),
                    'vod_name': self.clean_text(link.attr('title') or img.attr('alt')),
                    'vod_pic': urljoin(self.host, img.attr('data-src') or img.attr('src') or ""),
                    'vod_remarks': self.clean_text(box.find('.public-prt').text())
                })
        return {'list': videos, 'page': pg, 'pagecount': 999, 'limit': 20, 'total': 9999}

    # 影片详情
    def detailContent(self, ids):
        if not ids: return {"list": []}
        vid = ids[0]
        html = self.fetch_page(f"{self.host}/voddetail/{vid}.html")
        doc = pq(html) if html else pq('')
        vod_info = {
            "vod_id": vid,
            "vod_name": self.clean_text(doc('h1.player-title-link').text()),
            "vod_pic": urljoin(self.host, doc('.role-card img').attr('data-src') or ""),
            "vod_content": self.clean_text(doc('.card-text').text()),
            "vod_play_from": "",
            "vod_play_url": ""
        }

        # 解析播放源
        play_url = urljoin(self.host, doc('.anthology-list-play a:first').attr('href') or f"/vodplay/{vid}-1-1.html")
        play_html = self.fetch_page(play_url)
        play_doc = pq(play_html) if play_html else pq('')
        sources = {}

        for tab in play_doc('a.vod-playerUrl[data-form]').items():
            form = tab.attr('data-form')
            sname = self.source_map.get(form, self.clean_text(tab.text()))
            idx = list(play_doc('a.vod-playerUrl[data-form]')).index(tab[0])
            eps = [f"{self.clean_text(e.text())}${urljoin(self.host, e.attr('href'))}" 
                   for e in play_doc('.anthology-list-box').eq(idx).find('a').items() if e.text() and e.attr('href')]
            if eps: sources[sname] = '#'.join(eps)

        # 排序播放源
        final_from, final_url = [], []
        if "高清NB源" in sources:
            final_from.append("高清NB源")
            final_url.append(sources.pop("高清NB源"))
        final_from.extend(sources.keys())
        final_url.extend(sources.values())
        
        vod_info["vod_play_from"] = "$$$".join(final_from)
        vod_info["vod_play_url"] = "$$$".join(final_url)
        return {"list": [vod_info]}

    # 搜索功能（XML解析+网页兜底）
    def searchContent(self, key, quick, pg="1"):
        # 1. RSS搜索
        try:
            rss_url = f"{self.host}/rss.xml?wd={quote(key)}"
            if (html := self.fetch_page(rss_url, headers={**self.headers, 'Accept': 'application/xml'})):
                root = ET.fromstring(html)
                videos = []
                seen = set()
                for item in root.findall('.//item'):
                    if (link := self.clean_text(item.findtext('link'))) and (vid := re.search(r'/voddetail/(\d+)\.html', link)):
                        if vid.group(1) in seen: continue
                        seen.add(vid.group(1))
                        title = self.clean_text(item.findtext('title'))
                        if title:
                            videos.append({
                                "vod_id": vid.group(1),
                                "vod_name": title,
                                "vod_pic": self.DEFAULT_PIC,
                                "vod_remarks": f"主演: {self.clean_text(item.findtext('author'))[:15]}..." if item.findtext('author') else ""
                            })
                if videos: return {"list": videos, "page": int(pg)}
        except Exception as e:
            self.log(f"RSS err: {str(e)}")

        # 2. 网页兜底搜索
        try:
            search_url = f"{self.host}/vodsearch/{quote(key)}---{pg}---.html"
            html = self.fetch_page(search_url)
            doc = pq(html) if html else pq('')
            videos = []
            seen = set()
            for box in doc('.public-list-box.public-pic-b').items():
                if (link := box.find('a')) and (vid := re.search(r'/voddetail/(\d+)\.html', link.attr('href'))):
                    if vid.group(1) in seen: continue
                    seen.add(vid.group(1))
                    img = link.find('img')
                    videos.append({
                        "vod_id": vid.group(1),
                        "vod_name": self.clean_text(link.attr('title') or img.attr('alt')),
                        "vod_pic": urljoin(self.host, img.attr('data-src') or img.attr('src') or self.DEFAULT_PIC),
                        "vod_remarks": self.clean_text(box.find('.public-prt').text())
                    })
            return {"list": videos, "page": int(pg)}
        except Exception as e:
            self.log(f"Web search err: {str(e)}")
            return {"list": [], "page": int(pg)}

    # 播放解析
    def isVideoUrl(self, url):
        return any(ext in url.lower() for ext in ['.mp4', '.m3u8', '.flv'])

    def playerContent(self, flag, id, vipFlags):
        play_url = urljoin(self.host, id)
        if not play_url.startswith(('http', 'https')):
            return {"parse": 1, "url": play_url, "header": self.headers}

        if (html := self.fetch_page(play_url)) and (match := re.search(r'var player_aaaa=({[^}]+?url:[^}]+})', html, re.DOTALL)):
            try:
                data = json.loads(re.sub(r',\s*([}\]])', r'\1', match.group(1)))
                main = unquote(data.get('url', '')).strip()
                backup = unquote(data.get('url_next', '')).strip()
                play_addr = main if self.isVideoUrl(main) else backup if self.isVideoUrl(backup) else play_url
                return {
                    "parse": 0 if self.isVideoUrl(play_addr) else 1,
                    "url": play_addr,
                    "header": {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Referer": play_url}
                }
            except Exception as e:
                self.log(f"Player parse err: {str(e)}")
        return {"parse": 1, "url": play_url, "header": self.headers}
