#author Kyle
import sys
import time
import json
import re
import urllib.parse
from base64 import b64decode, b64encode
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def init(self, extend=""):
        self.host = "https://www.eporner.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': self.host + '/',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
        }
        self.timeout = 10
        self.retries = 2
        self.cookies = {"EPRNS": "1"}

    def getName(self):
        return "EP涩"

    def isVideoFormat(self, url): 
        return True

    def manualVideoCheck(self): 
        return False

    def destroy(self): 
        pass

    def homeContent(self, filter):
        result = {}
        result['class'] = [
            {"type_id": "/cat/all/", "type_name": "最新"},
            {"type_id": "/best-videos/", "type_name": "最佳视频"},
            {"type_id": "/top-rated/", "type_name": "最高评分"},
            {"type_id": "/cat/4k-porn/", "type_name": "4K"},
        ]
        return result

    def homeVideoContent(self):
        result = {}
        videos = self._api_search(query="all", page=1, order="latest", gay="0", per_page=20)
        result['list'] = videos
        return result

    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        params = self._map_tid_to_api(tid)
        videos = self._api_search(page=int(pg), **params)
        result['list'] = videos
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = len(videos) or 20
        result['total'] = 999999
        return result

    def searchContent(self, key, quick, pg="1"):
        result = {}
        videos = self._api_search(query=key or "all", page=int(pg), order="latest", gay="0")
        result['list'] = videos
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = len(videos) or 20
        result['total'] = 999999
        return result

    def detailContent(self, ids):
        result = {}
        url = ids[0]
        if not url.startswith('http'): 
            url = self.host + url
        r = self.fetch(url, headers=self.headers)
        root = self.html(r.text)
        og_title = root.xpath('//meta[@property="og:title"]/@content')
        if og_title:
            title = og_title[0].replace(' - EPORNER', '').strip()
        else:
            h1 = "".join(root.xpath('//h1//text()'))
            title = re.sub(r"\s*(\d+\s*min.*)$", "", h1).strip() or "爱看AV"
        img_elem = root.xpath('//meta[@property="og:image"]/@content') or root.xpath('//img[@id="mainvideoimg"]/@src')
        thumbnail = img_elem[0] if img_elem else ""
        meta_desc = (root.xpath('//meta[@name="description"]/@content') or root.xpath('//meta[@property="og:description"]/@content'))
        desc_text = meta_desc[0] if meta_desc else ""
        dur_match = re.search(r"Duration:\s*([0-9:]+)", desc_text)
        duration = dur_match.group(1) if dur_match else ""
        encoded_url = self.e64(url)
        play_url = f"播放${encoded_url}"
        vod = {
            "vod_id": url,
            "vod_name": title,
            "vod_pic": thumbnail,
            "vod_remarks": duration,
            "vod_content": desc_text.strip(),
            "vod_play_from": "🍑Play",
            "vod_play_url": play_url
        }
        result['list'] = [vod]
        return result

    def playerContent(self, flag, id, vipFlags):
        result = {}
        url = self.d64(id)
        if not url.startswith('http'):
            url = self.host + url
        r = self.fetch(url, headers=self.headers)
        html_content = r.text
        pattern = r"vid\s*=\s*'([^']+)';\s*[\w*\.]+hash\s*=\s*['\"]([\da-f]{32})"
        match = re.search(pattern, html_content)
        if match:
            vid, hash_val = match.groups()
            hash_code = ''.join((self.encode_base_n(int(hash_val[i:i + 8], 16), 36) for i in range(0, 32, 8)))
            xhr_url = f"{self.host}/xhr/video/{vid}?hash={hash_code}&device=generic&domain=www.eporner.com&fallback=false&embed=false&supportedFormats=mp4"
            xhr_headers = {
                **self.headers,
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json, text/javascript, */*; q=0.01'
            }
            resp = self.fetch(xhr_url, headers=xhr_headers)
            data = json.loads(resp.text)
            if data.get("available", True):
                sources_block = data.get("sources", {})
                sources = sources_block.get("mp4", {})
                final_url = None
                if sources:
                    quality_sorted = sorted(sources.keys(), key=lambda q: int(re.sub(r"\D", "", q) or 0), reverse=True)
                    best_quality = quality_sorted[0]
                    final_url = sources[best_quality].get("src")
                else:
                    hls = sources_block.get("hls")
                    if isinstance(hls, dict):
                        final_url = hls.get("src")
                    elif isinstance(hls, list) and hls:
                        final_url = hls[0].get("src")
                    best_quality = "hls"
                if final_url:
                    result["parse"] = 0
                    result["url"] = final_url
                    result["header"] = {
                        'User-Agent': self.headers['User-Agent'],
                        'Referer': url,
                        'Origin': self.host,
                        'Accept': '*/*'
                    }
        return result

    def encode_base_n(self, num, n, table=None):
        FULL_TABLE = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        if not table:
            table = FULL_TABLE[:n]
        if n > len(table):
            raise ValueError('base %d exceeds table length %d' % (n, len(table)))
        if num == 0:
            return table[0]
        ret = ''
        while num:
            ret = table[num % n] + ret
            num = num // n
        return ret

    def e64(self, text):
        return b64encode(text.encode()).decode()

    def d64(self, encoded_text):
        return b64decode(encoded_text.encode()).decode()

    def html(self, content):
        from lxml import etree
        return etree.HTML(content)

    def fetch(self, url, headers=None, timeout=None):
        import requests, ssl
        ssl._create_default_https_context = ssl._create_unverified_context
        if headers is None:
            headers = self.headers
        if timeout is None:
            timeout = self.timeout
        for _ in range(self.retries + 1):
            resp = requests.get(url, headers=headers, timeout=timeout, verify=False, cookies=getattr(self, 'cookies', None))
            resp.encoding = 'utf-8'
            return resp
            time.sleep(1)
        raise Exception("Fetch failed")

    def _parse_video_list(self, root):
        videos = []
        items = root.xpath('//div[contains(@class, "mb") and @data-id]')
        for item in items:
            link = item.xpath('.//a[contains(@href, "/video-")]/@href')
            if not link: 
                continue
            vod_id = self.host + link[0]
            title = "".join(item.xpath('.//p[contains(@class, "mbtit")]//text()')).strip()
            img = item.xpath('.//img/@src')
            thumbnail = img[0] if img else ""
            duration = "".join(item.xpath('.//span[contains(@class,"mbtim")]/text()')).strip()
            videos.append({
                "vod_id": vod_id,
                "vod_name": title or "爱看AV",
                "vod_pic": thumbnail,
                "vod_remarks": duration
            })
        return videos

    def _map_tid_to_api(self, tid: str):
        params = {"query": "all", "order": "latest", "gay": "0", "per_page": 30}
        t = (tid or '').strip('/').lower()
        if t.startswith('best-videos'):
            params["order"] = "most-popular"
        elif t.startswith('top-rated'):
            params["order"] = "top-rated"
        elif t.startswith('cat/4k-porn'):
            params["query"] = "4k"
        elif t.startswith('cat/gay'):
            params["gay"] = "2"
            params["order"] = "latest"
        else:
            params["gay"] = "0"
        return params

    def _api_search(self, query="all", page=1, order="latest", gay="0", per_page=30, thumbsize="medium"):
        base = f"{self.host}/api/v2/video/search/"
        q = {
            "query": query,
            "per_page": per_page,
            "page": page,
            "thumbsize": thumbsize,
            "order": order,
            "format": "json"
        }
        if gay is not None:
            q["gay"] = gay
        url = base + "?" + urllib.parse.urlencode(q)
        r = self.fetch(url, headers={**self.headers, 'X-Requested-With': 'XMLHttpRequest'})
        data = json.loads(r.text)
        return self._parse_api_list(data)

    def _parse_api_list(self, data: dict):
        videos = []
        for v in (data or {}).get('videos', []):
            vurl = v.get('url') or ''
            title = v.get('title') or ''
            thumb = (v.get('default_thumb') or {}).get('src') or ''
            remarks = v.get('length_min') or ''
            videos.append({
                "vod_id": vurl if vurl.startswith('http') else (self.host + vurl),
                "vod_name": title or "爱看AV",
                "vod_pic": thumb,
                "vod_remarks": remarks
            })
        return videos