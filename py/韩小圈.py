# -*- coding: utf-8 -*-
import sys
import re
from bs4 import BeautifulSoup
import requests as rq
from urllib.parse import quote

sys.path.append('..')
try:
    from base.spider import Spider
except ImportError:
    class Spider:
        def fetch(self, url, headers=None, **kw):
            kw.pop('timeout', None)
            r = rq.get(url, headers=headers, timeout=15, **kw)
            r.encoding = 'utf-8'
            return r

HOST = "https://www.jennyhow.com"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

CLASS_MAP = {
    "/hxq/1.html": "最新韩剧",
    "/hxq/2.html": "韩国电影",
    "/hxq/3.html": "韩国综艺",
    "/hxq/4.html": "韩国动漫"
}

class Spider(Spider):
    def init(self, extend=""):
        self._session = rq.Session()
        self._session.headers.update({
            "User-Agent": UA,
            "Referer": HOST
        })

    def getName(self):
        return "韩小圈"

    def isVideoFormat(self, url):
        return ".m3u8" in url or ".mp4" in url

    def manualVideoCheck(self):
        return False

    def _get(self, url, timeout=10):
        try:
            r = self._session.get(url, timeout=timeout)
            r.encoding = 'utf-8'
            return r.text
        except Exception as e:
            print(f"网络请求失败: {e}")
            return ""

    def _format_pic(self, pic_url):
        if not pic_url: return ""
        if pic_url.startswith('//'):
            return "https:" + pic_url
        if pic_url.startswith('/'):
            return HOST + pic_url
        return pic_url

    def homeContent(self, filter=False):
        classes = []
        for tid, name in CLASS_MAP.items():
            classes.append({"type_id": tid, "type_name": name})
        return {"class": classes}

    def homeVideoContent(self):
        html = self._get(HOST)
        soup = BeautifulSoup(html, 'html.parser')
        videos = []
        
        items = soup.find_all('div', class_='module-item')
        for item in items:
            a_tag = item.find('a', class_='module-item-title') or item.find('a')
            img_tag = item.find('img')
            
            if a_tag:
                name = a_tag.get('title') or a_tag.get_text(strip=True)
                href = a_tag.get('href', '')
                pic = ""
                if img_tag:
                    pic = img_tag.get('data-src') or img_tag.get('data-original') or img_tag.get('src', '')
                
                videos.append({
                    "vod_id": href,
                    "vod_name": name,
                    "vod_pic": self._format_pic(pic),
                    "vod_remarks": ""
                })
        return {"list": videos}

    def categoryContent(self, tid, pg=1, filter=False, extend=None):
        try:
            pn = max(int(str(pg)), 1)
            
            # 拦截缓存
            if tid in ["20", "1"]: tid = "/hxq/1.html"
            elif tid in ["21", "2"]: tid = "/hxq/2.html"
            elif tid in ["22", "3"]: tid = "/hxq/3.html"
            elif tid in ["23", "4"]: tid = "/hxq/4.html"

            url = tid
            if pn > 1 and url.endswith('.html'):
                url = url.replace('.html', f'-{pn}.html')

            if not url.startswith('http'):
                url = HOST + url
                
            html = self._get(url)
            soup = BeautifulSoup(html, 'html.parser')
            videos = []
            
            for item in soup.find_all('div', class_='module-item'):
                a_tag = item.find('a', class_='module-item-pic') or item.find('a')
                if not a_tag: continue
                
                img_tag = item.find('img')
                name = a_tag.get('title')
                if not name and img_tag: name = img_tag.get('alt')
                if not name: name = a_tag.get_text(strip=True)
                
                href = a_tag.get('href', '')
                pic = ""
                if img_tag:
                    pic = img_tag.get('data-src') or img_tag.get('data-original') or img_tag.get('src', '')
                    
                remarks_tag = item.find(class_='module-item-text') or item.find(class_='module-item-note')
                remarks = remarks_tag.get_text(strip=True) if remarks_tag else ""

                if href:
                    videos.append({
                        "vod_id": href,
                        "vod_name": name,
                        "vod_pic": self._format_pic(pic),
                        "vod_remarks": remarks
                    })
            
            pagecount = pn + 1 if len(videos) > 0 else pn
            return {"list": videos, "page": pn, "pagecount": pagecount, "limit": 24, "total": 0}
        except:
            return {"list": [], "page": pg}

    # ================= 详情页大升级 =================
    def detailContent(self, ids):
        detail_url = ids[0] if ids[0].startswith('http') else HOST + ids[0]
        html = self._get(detail_url)
        if not html: return {"list": []}

        soup = BeautifulSoup(html, 'html.parser')
        
        title_tag = soup.find('h1')
        title = title_tag.get_text(strip=True) if title_tag else "未知名称"
        
        pic_tag = soup.find('img', class_='lazyload') or soup.find('img', class_='lazy')
        pic = ""
        if pic_tag:
            pic = pic_tag.get('data-src') or pic_tag.get('data-original') or pic_tag.get('src', '')

        # --- 新增：智能文本猎手，自动抓取导演/主演/剧情等信息 ---
        vod_director, vod_actor, vod_year, vod_content = "", "", "", ""
        
        # 遍历所有文本节点寻找关键词
        for tag in soup.find_all(text=re.compile(r'导演|主演|上映|年份|剧情|简介')):
            text_str = tag.strip()
            parent = tag.parent
            
            # 过滤掉系统标签
            if parent.name in ['title', 'meta', 'script', 'style']: continue
            
            # 往上找包裹着文字的容器
            container = parent.parent if parent.name in ['span', 'strong', 'b', 'font'] else parent
            full_text = container.get_text(separator=' ', strip=True)
            
            if '导演' in text_str and not vod_director:
                vod_director = re.sub(r'.*?导演[：:]?\s*', '', full_text)
            elif '主演' in text_str and not vod_actor:
                vod_actor = re.sub(r'.*?主演[：:]?\s*', '', full_text)
            elif ('上映' in text_str or '年份' in text_str) and not vod_year:
                vod_year = re.sub(r'.*?(上映|年份)[：:]?\s*', '', full_text)
            elif ('剧情' in text_str or '简介' in text_str) and not vod_content:
                vod_content = re.sub(r'.*?(剧情|简介)[：:]?\s*', '', full_text)

        # 简介兜底：有的网站把简介放进了一个很隐蔽的 class 里
        if not vod_content:
            intro_tag = soup.find(class_='module-info-introduction-content') or soup.find(class_='module-info-introduction')
            if intro_tag:
                vod_content = intro_tag.get_text(strip=True)

        # 抓取播放列表
        play_from = []
        play_url = []

        tabs_ul = soup.find('ul', class_='nav-tabs')
        if tabs_ul:
            for li in tabs_ul.find_all('li'):
                a_tag = li.find('a')
                if not a_tag: continue

                line_name = a_tag.get_text(strip=True)
                target_id = a_tag.get('href', '').replace('#', '')

                playlist_div = soup.find('div', id=target_id)
                if playlist_div:
                    episodes = []
                    for ep in playlist_div.find_all('a'):
                        ep_name = ep.get('title') or ep.get_text(strip=True)
                        ep_href = ep.get('href', '')
                        if ep_href:
                            episodes.append(f"{ep_name}${ep_href}")
                    
                    if episodes:
                        play_from.append(line_name)
                        play_url.append("#".join(episodes))

        vod = {
            "vod_id": ids[0],
            "vod_name": title,
            "vod_pic": self._format_pic(pic),
            "vod_director": vod_director,       # 🌟 给 APP 喂进去导演
            "vod_actor": vod_actor,             # 🌟 给 APP 喂进去主演
            "vod_year": vod_year,               # 🌟 给 APP 喂进去年份
            "vod_content": vod_content,         # 🌟 给 APP 喂进去简介
            "vod_play_from": "$$$".join(play_from),
            "vod_play_url": "$$$".join(play_url),
        }
        return {"list": [vod]}

    def playerContent(self, flag, id, vipFlags=None):
        play_url = id if id.startswith('http') else HOST + id
        html = self._get(play_url)
        if not html: return {"url": ""}

        match = re.search(r'var now=[\'"](.*?)[\'"];', html)
        if match:
            m3u8_url = match.group(1)
            return {
                "url": m3u8_url,
                "header": {"User-Agent": UA}
            }
        
        match_json = re.search(r'player_aaaa\s*=\s*(\{[^}]+\})', html)
        if match_json:
            import json
            try:
                data = json.loads(match_json.group(1))
                return {"url": data.get("url", ""), "header": {"User-Agent": UA}}
            except:
                pass

        return {"url": ""}

    def searchContent(self, key, quick=False, pg=1):
        try:
            url = f"{HOST}/vodsearch/{quote(key)}----------{pg}---.html"
            html = self._get(url)
            soup = BeautifulSoup(html, 'html.parser')
            videos = []

            for item in soup.find_all('div', class_='module-search-item') or soup.find_all('div', class_='module-item'):
                a_tag = item.find('a')
                img_tag = item.find('img')
                if a_tag and img_tag:
                    name = img_tag.get('alt', '') or a_tag.get('title', '')
                    href = a_tag.get('href', '')
                    pic = img_tag.get('data-src') or img_tag.get('data-original') or img_tag.get('src', '')
                    videos.append({
                        "vod_id": href,
                        "vod_name": name,
                        "vod_pic": self._format_pic(pic)
                    })
            return {"list": videos}
        except:
            return {"list": []}

    def localProxy(self, param):
        pass