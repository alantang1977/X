# -*- coding: utf-8 -*-
# by @嗷呜
import json
import random
import re
import sys
import threading
import time
from base64 import b64decode
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from pyquery import PyQuery as pq
sys.path.append('..')
from base.spider import Spider


class Spider(Spider):

    def init(self, extend=""):
        self.host=self.host_late(self.get_domains())
        pass

    def getName(self):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="134", "Google Chrome";v="134"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'dnt': '1',
        'upgrade-insecure-requests': '1',
        'sec-fetch-site': 'cross-site',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-user': '?1',
        'sec-fetch-dest': 'document',
        'accept-language': 'zh-CN,zh;q=0.9',
        'priority': 'u=0, i'
    }

    def homeContent(self, filter):
        data=self.getpq(self.fetch(self.host, headers=self.headers).text)
        result = {}
        classes = []
        for k in data('.category-list ul li').items():
            classes.append({
                'type_name': k('a').text(),
                'type_id': k('a').attr('href')
            })
        result['class'] = classes
        result['list'] = self.getlist(data('#index article a'))
        return result

    def homeVideoContent(self):
        pass

    def categoryContent(self, tid, pg, filter, extend):
        data=self.getpq(self.fetch(f"{self.host}{tid}{pg}", headers=self.headers).text)
        result = {}
        result['list'] = self.getlist(data('#archive article a'))
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        return result

    def detailContent(self, ids):
        url=f"{self.host}{ids[0]}"
        data=self.getpq(self.fetch(url, headers=self.headers).text)
        vod = {
            'vod_content': data('.post-title').text(),
            'vod_play_from': '51吸瓜',
            'vod_play_url': f"请停止活塞运动，可能没有视频${url}"
        }
        try:
            clist = []
            if data('.tags .keywords a'):
                for k in data('.tags .keywords a').items():
                    title = k.text()
                    href = k.attr('href')
                    clist.append('[a=cr:' + json.dumps({'id': href, 'name': title}) + '/]' + title + '[/a]')
            vod['vod_content'] = ' '.join(clist)
        except:
            pass
        try:
            plist=[]
            if data('.dplayer'):
                for c, k in enumerate(data('.dplayer').items(), start=1):
                    config = json.loads(k.attr('data-config'))
                    plist.append(f"视频{c}${config['video']['url']}")
            vod['vod_play_url']='#'.join(plist)
        except:
            pass
        return {'list':[vod]}

    def searchContent(self, key, quick, pg="1"):
        data=self.getpq(self.fetch(f"{self.host}/search/{key}/{pg}", headers=self.headers).text)
        return {'list':self.getlist(data('#archive article a')),'page':pg}

    def playerContent(self, flag, id, vipFlags):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
            'sec-ch-ua-platform': '"macOS"',
            'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="134", "Google Chrome";v="134"',
            'DNT': '1',
            'sec-ch-ua-mobile': '?0',
            'Origin': self.host,
            'Sec-Fetch-Site': 'cross-site',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }
        return  {'parse': 1, 'url': id, 'header': headers}

    def localProxy(self, param):
        res=self.fetch(param['url'], headers=self.headers, timeout=10)
        return [200,res.headers.get('Content-Type'),self.aesimg(res.content)]

    def get_domains(self):
        html = self.getpq(self.fetch("https://www.qcbtifw.xyz", headers=self.headers).text)
        html_pattern = r"Base64\.decode\('([^']+)'\)"
        html_match = re.search(html_pattern, html('script').eq(-1).text(), re.DOTALL)
        if not html_match:
            raise Exception("未找到html_match")
        html = b64decode(html_match.group(1)).decode()
        words_pattern = r"words\s*=\s*'([^']+)'"
        words_match = re.search(words_pattern, html)
        if not words_match:
            raise Exception("未找到words")
        words = words_match.group(1).split(',')
        main_pattern = r"lineAry\s*=.*?words\.random\(\)\s*\+\s*'\.([^']+)'"
        domain_match = re.search(main_pattern, html, re.DOTALL)
        if not domain_match:
            raise Exception("未找到主域名")
        domain_suffix = domain_match.group(1)
        domains = []
        for _ in range(3):
            random_word = random.choice(words)
            domain = f"https://{random_word}.{domain_suffix}"
            domains.append(domain)
        return domains

    def host_late(self, url_list):
        if isinstance(url_list, str):
            urls = [u.strip() for u in url_list.split(',')]
        else:
            urls = url_list

        if len(urls) <= 1:
            return urls[0] if urls else ''

        results = {}
        threads = []

        def test_host(url):
            try:
                start_time = time.time()
                response = requests.head(url, timeout=1.0, allow_redirects=False)
                delay = (time.time() - start_time) * 1000
                results[url] = delay
            except Exception as e:
                results[url] = float('inf')

        for url in urls:
            t = threading.Thread(target=test_host, args=(url,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        return min(results.items(), key=lambda x: x[1])[0]

    def getlist(self,data):
        videos = []
        for k in data.items():
            a=k.attr('href')
            b=k('h2').text()
            c=k('span[itemprop="datePublished"]').text()
            if a and b and c:
                videos.append({
                    'vod_id': a,
                    'vod_name': b.replace('\n', ' '),
                    'vod_pic': self.getimg(k('script').text()),
                    'vod_remarks': c,
                    'style': {"type": "rect", "ratio": 1.33}
                })
        return videos

    def getimg(self, text):
        match = re.search(r"loadBannerDirect\('([^']+)'", text)
        if match:
            url = match.group(1)
            return f"{self.getProxyUrl()}&url={url}&type=img"
        else:
            return ''

    def aesimg(self, word):
        key = b'f5d965df75336270'
        iv = b'97b60394abc2fbe1'
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = unpad(cipher.decrypt(word), AES.block_size)
        return decrypted

    def getpq(self, data):
        try:
            return pq(data)
        except Exception as e:
            print(f"{str(e)}")
            return pq(data.encode('utf-8'))
