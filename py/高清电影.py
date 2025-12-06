from pyquery import PyQuery
import requests
import sys
import re
sys.path.append('..')
from base.spider import Spider as BaseSpider

class Spider(BaseSpider):
    def __init__(self):
        super(Spider, self).__init__()
        self.debug = True
        self.baseUrl = "https://www.gaoqing888.com"
        self.siteUrl = self.baseUrl
        self.name = '高清电影',
        self.headers = {
            'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
            'Referer': self.baseUrl + '/',
            'X-Requested-With': 'XMLHttpRequest',
        }

    def getName(self):
        return self.name

    def init(self, extend=""):
        pass

    def homeContent(self, filter):
        return {
            'class': [
                {'type_id': '1', 'type_name': '每日更新'},
                {'type_id': '2', 'type_name': '选电影'},
            ],
            'filters': {},
        }

    def homeVideoContent(self):
        return {'list': [], 'parse': 0, 'jx': 0}

    def categoryContent(self, tid, page, filter, extend):
        result = {'list': [], 'parse': 0, 'jx': 0}
        doc = None
        if tid == "1":
            url = f"{self.baseUrl}/?page={page}"
            try:
                headers = self.headers.copy()
                headers['Accept'] = 'application/json, text/javascript, */*; q=0.01'
                response = requests.get(url, headers=headers)
                ii = response.json()['content']
                doc = PyQuery(ii)
            except Exception as e:
                print(e)
        elif tid == "2":
            url = f"{self.baseUrl}/movie?sort=recommend&page={page}"
            try:
                headers = self.headers.copy()
                headers['Accept'] = 'text/html, */*; q=0.01'
                response = requests.get(url, headers=headers)
                doc = PyQuery(response.text)
            except Exception as e:
                print(e)
        if doc:
            for i in doc('a.video-item').items():
                result['list'].append({
                    "vod_id": i('a').attr('href').split("/")[-2],
                    "vod_name": i('img').attr('alt'),
                    "vod_pic": self.getProxyUrl() + '&img_url=' + i('img').attr('src'),
                    "vod_remarks": "评分:" + i('p strong').text(),
                })
        return result

    def detailContent(self, did):
        return_data = {'list': [], 'parse': 0, 'jx': 0}
        ids = did[0]
        url = self.baseUrl + f'/{ids}/detail'
        try:
            response = requests.get(url, headers=self.headers)
            html = response.text
            doc = PyQuery(html)
            title_match = re.search(r'<h1[^>]*class="page-title"[^>]*>(.*?)</h1>', html, re.S)
            if not title_match:
                title_match = re.search(r'<title>(.*?)</title>', html, re.S)
                if title_match:
                    title = title_match.group(1).strip()
                    title = re.sub(r'_.*|迅雷下载.*|高清下载.*|高清电影天堂.*', '', title)
                else:
                    title = doc('div.info ul.list-unstyled li').eq(7).text().replace('\xa0', '')
            else:
                title = title_match.group(1).strip()

            d = {
                'type_name': doc('div.info ul.list-unstyled li').eq(3).text().replace('\xa0', ''),
                'vod_id': ids,
                'vod_name': title,
                'vod_remarks': doc('div.info ul.list-unstyled li').eq(6).text().replace('\xa0', ''),
                'vod_year': doc('div.info ul.list-unstyled li').eq(5).text().replace('\xa0', ''),
                'vod_area': doc('div.info ul.list-unstyled li').eq(4).text().replace('\xa0', ''),
                'vod_actor': doc('div.info ul.list-unstyled li').eq(2).text().replace('\xa0', ''),
                'vod_director': doc('div.info ul.list-unstyled li').eq(0).text().replace('\xa0', ''),
                'vod_content': doc('div.video-detail > p').text(),
                'vod_play_from': '',
                'vod_play_url': ''
            }
            play_lines = self._extract_play_resources(html)
            if not play_lines:
                play_lines = ["暂无资源$暂无资源"]
            play_from = []
            if any("夸克网盘" in line for line in play_lines):
                play_from.append("夸克网盘")
            if any("磁力链接" in line for line in play_lines):
                play_from.append("磁力链接")
            if not play_from:
                play_from = ["其他资源"]
            d['vod_play_from'] = '$$$'.join(play_from)
            d['vod_play_url'] = '#'.join(play_lines)
            return_data['list'].append(d)
        except Exception as e:
            print(e)
        return return_data

    def searchContent(self, key, quick, pg='1'):
        return_data = {'list': [], 'parse': 0, 'jx': 0}
        url = self.baseUrl + f'/search?kw={key}'
        if pg == '1':
            response = requests.get(url, headers=self.headers)
            doc = PyQuery(response.text)
            for i in doc('div.search-list div.video-row').items():
                return_data['list'].append({
                    "vod_id": i('a').attr('href').split("/")[-2],
                    "vod_name": i('img').attr('alt'),
                    "vod_pic": self.getProxyUrl() + '&img_url=' + i('img').attr('src'),
                    "vod_remarks": "评分:" + i('span.rate-num').text(),
                })
        return return_data

    def playerContent(self, flag, id, vipFlags):
        if id == "暂无资源":
            return {"parse": 0, "url": ""}
        if id.startswith('magnet:'):
            return {"parse": 1, "url": id}
        return {"parse": 1, "url": id, "header": self.headers}

    def localProxy(self, params):
        img_url = params['img_url']
        return [200, 'application/octet-stream', self.proxy_img(img_url)]

    def proxy_img(self, url):
        try:
            response = requests.get(url, headers=self.headers)
            return response.content
        except Exception as e:
            print(e)
        return b''
    
    def _extract_quark_url(self, url):
        try:
            if not url:
                return None
            url = url.strip()
            if '/go/play' in url:
                match = re.search(r'url=([^&]+)', url)
                if match:
                    return f"push://{match.group(1)}"
            if 'pan.quark.cn' in url:
                return f"push://{url}"
            return None
        except Exception as e:
            print(f"Error extracting quark URL: {str(e)}")
            return None
    
    def _extract_play_resources(self, html):
        play_lines = []
        quark_pattern = r'<a[^>]*href="([^"]*pan\.quark\.cn[^"]*)"[^>]*>'
        quark_matches = re.findall(quark_pattern, html, re.S)
        for i, resource_url in enumerate(quark_matches[:5], 1):
            play_url = self._extract_quark_url(resource_url)
            if play_url:
                play_lines.append(f"夸克网盘{i}${play_url}")
        magnet_patterns = [
            r'href="(magnet:\?[^"]+)"',
            r'<a[^>]*href="(magnet:[^"]+)"[^>]*>'
        ]
        for pattern in magnet_patterns:
            matches = re.findall(pattern, html, re.S)
            for i, match in enumerate(matches[:5], 1):
                if isinstance(match, str) and match.startswith('magnet:'):
                    play_lines.append(f"磁力链接{i}${match}")
        
        return play_lines
    
    def isVideoFormat(self, url):
        video_formats = ['.mp4', '.m3u8', '.flv', '.avi', '.mkv', '.wmv', '.rmvb', '.mov']
        return any(url.lower().endswith(fmt) for fmt in video_formats)
    
    def manualVideoCheck(self, url):
        return True


if __name__ == '__main__':
    pass
