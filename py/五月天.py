# -*- coding: utf-8 -*-
import json
import re
import sys
from base.spider import Spider
from pyquery import PyQuery as pq

class Spider(Spider):
    def init(self, extend=""):
        self.host = "https://qswyt4444.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': f'{self.host}/',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }

    def getName(self):
        return "QS五月天"

    def isVideoFormat(self, url):
        return url.lower().endswith('.m3u8')

    def manualVideoCheck(self):
        return True

    def destroy(self):
        pass

    def homeContent(self, filter):
        result = {}
        classes = []
        seen_ids = set()
        try:
            res = self.fetch(self.host, headers=self.headers)
            d = pq(res.text)
            items = d('a[href^="/movie/block/"]')
            for item in items.items():
                href = item.attr('href')
                match = re.search(r'/movie/block/(\d+)', href)
                if match:
                    tid = match.group(1)
                    name = item.text().strip() or item.find('span').text().strip()
                    if tid and name and tid not in seen_ids:
                        classes.append({'type_name': name, 'type_id': tid})
                        seen_ids.add(tid)
        except Exception:
            pass

        if not classes:
            cateManual = {
                "最新": "newest",
                "国产": "50",
                "淫荡少妇": "21",
                "人妻诱惑": "22",
                "大奶萝莉": "23",
                "丝袜制服": "24",
                "强奸": "45",
                "群P": "46"
            }
            for k, v in cateManual.items():
                classes.append({'type_name': k, 'type_id': v})

        result['class'] = classes
        result['filters'] = {}
        return result

    def homeVideoContent(self):
        try:
            res = self.fetch(self.host, headers=self.headers)
            return {'list': self.parse_list(res.text)}
        except Exception:
            return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        if tid.isdigit():
            url = f'{self.host}/movie/block/{tid}?page={pg}'
        else:
            url = f'{self.host}/movie/{tid}?page={pg}'
        try:
            res = self.fetch(url, headers=self.headers)
            result['list'] = self.parse_list(res.text)
            result['page'] = int(pg)
            result['pagecount'] = 999
            result['limit'] = 20
            result['total'] = 9999
        except Exception:
            result['list'] = []
        return result

    def detailContent(self, ids):
        tid = ids[0]
        url = tid if tid.startswith('http') else (f'{self.host}{tid}' if tid.startswith('/') else f'{self.host}/movie/detail/{tid}')
        res = self.fetch(url, headers=self.headers)
        content = res.text
        title = ""
        pic = ""
        
        title_match = re.search(r'<meta property="og:title" content="(.*?)">', content)
        if title_match:
            title = title_match.group(1).split(' - ')[0]
        
        pic_match = re.search(r'<meta property="og:image" content="(.*?)">', content)
        if pic_match:
            pic = pic_match.group(1)

        vod_play_from_list = []
        vod_play_url_list = []
        pat = r'(/api/m3u8/p/[a-zA-Z0-9]+\.m3u8)'
        matches = re.findall(pat, content)
        unique_urls = []
        seen = set()
        
        for m in matches:
            full_url = m if m.startswith('http') else f"{self.host}{m}"
            if full_url not in seen:
                seen.add(full_url)
                unique_urls.append(full_url)

        for index, u in enumerate(unique_urls):
            vod_play_from_list.append(f"线路{index + 1}")
            vod_play_url_list.append(u)

        vod = {
            'vod_id': tid,
            'vod_name': title,
            'vod_pic': pic,
            'type_name': '',
            'vod_year': '',
            'vod_area': '',
            'vod_remarks': '',
            'vod_actor': '',
            'vod_director': '',
            'vod_content': '',
            'vod_play_from': '$$$'.join(vod_play_from_list),
            'vod_play_url': '$$$'.join(vod_play_url_list)
        }
        return {'list': [vod]}

    def searchContent(self, key, quick, pg="1"):
        url = f'{self.host}/search/{key}?page={pg}'
        try:
            res = self.fetch(url, headers=self.headers)
            return {'list': self.parse_list(res.text)}
        except:
            return {'list': []}

    def playerContent(self, flag, id, vipFlags):
        return {
            'parse': 0,
            'url': id,
            'header': {
                'User-Agent': self.headers['User-Agent']
            }
        }

    def localProxy(self, param):
        pass

    def parse_list(self, html):
        videos = []
        d = pq(html)
        items = d('a[href^="/movie/detail/"]')
        seen_ids = set()
        for item in items.items():
            href = item.attr('href')
            if href in seen_ids:
                continue
            title = item.attr('title')
            if not title:
                title = item.find('span').text() or item.text()
            img_tag = item.find('img')
            pic = img_tag.attr('data-src') or img_tag.attr('src') or ""
            remarks = item.find('.duration').text()
            if href and title:
                seen_ids.add(href)
                videos.append({
                    'vod_id': href,
                    'vod_name': title.strip(),
                    'vod_pic': pic,
                    'vod_remarks': remarks
                })
        return videos