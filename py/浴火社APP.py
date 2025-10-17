# -*- coding: utf-8 -*-
# by @嗷呜
import json
import re
import sys
import threading
import time
from base64 import b64decode, b64encode
import requests
from Crypto.Cipher import AES
from Crypto.Hash import MD5
from Crypto.Util.Padding import unpad
sys.path.append('..')
from base.spider import Spider


class Spider(Spider):

    def init(self, extend=""):
        self.did = self.getdid()
        self.token=self.gettoken()
        domain=self.domain()
        self.phost=self.host_late(domain['domain_preview'])
        self.bhost=domain['domain_original']
        self.names=domain['name_original']
        pass

    def getName(self):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    host = 'https://lulu-api-92mizw.jcdwn.com'

    headers = {
        'User-Agent': 'okhttp/4.11.0',
        'referer': 'https://app.nova-traffic-1688.com',
    }

    def homeContent(self, filter):
        BASE_CATEGORIES = [
            {'type_name': '片商', 'type_id': 'makers'},
            {'type_name': '演员', 'type_id': 'actor'}
        ]

        SORT_OPTIONS = {
            'key': 'sortby',
            'name': 'sortby',
            'value': [
                {'n': '最新', 'v': 'on_shelf_at'},
                {'n': '最热', 'v': 'hot'}
            ]
        }

        tags = self.getdata('/api/v1/video/tag?current=1&pageSize=100&level=1')
        producers = self.getdata('/api/v1/video/producer?current=1&pageSize=100&status=1')
        regions = self.getdata('/api/v1/video/region?current=1&pageSize=100')
        result = {'class': [], 'filters': {}}
        result['class'].extend(BASE_CATEGORIES)
        for category in BASE_CATEGORIES:
            result['filters'][category['type_id']] = [SORT_OPTIONS]
        if tags.get('data'):
            main_tag = tags['data'][0]
            result['class'].append({
                'type_name': '发现',
                'type_id': f'{main_tag["id"]}_tag'
            })
            tag_values = [
                {'n': tag['name'], 'v': f"{tag['id']}_tag"}
                for tag in tags['data'][1:]
                if tag.get('id')
            ]
            result['filters'][f'{main_tag["id"]}_tag'] = [
                {'key': 'tagtype', 'name': 'tagtype', 'value': tag_values},
                SORT_OPTIONS
            ]

        region_filter = {
            'key': 'region_ids',
            'name': 'region_ids',
            'value': [
                {'n': region['name'], 'v': region['id']}
                for region in regions['data'][1:]
                if region.get('id')
            ]
        }
        self.aid=regions['data'][0]['id']
        result['filters']['actor'].append({
            'key': 'region_id',
            'name': 'region_id',
            'value': region_filter['value'][:2]
        })
        complex_sort = {
            'key': 'sortby',
            'name': 'sortby',
            'value': [
                {'n': '综合', 'v': 'complex'},
                *SORT_OPTIONS['value']
            ]
        }
        producer_filters = [region_filter, complex_sort]
        for producer in producers['data']:
            result['class'].append({
                'type_name': producer['name'],
                'type_id': f'{producer["id"]}_sx'
            })
            result['filters'][f'{producer["id"]}_sx'] = producer_filters
        return result

    def homeVideoContent(self):
        data=self.getdata('/api/v1/video?current=1&pageSize=60&region_ids=&sortby=complex')
        return {'list':self.getlist(data)}

    def categoryContent(self, tid, pg, filter, extend):
        if 'act' in tid:
            data=self.getact(tid, pg, filter, extend)
        elif 'tag' in tid:
            data=self.gettag(tid, pg, filter, extend)
        elif 'sx' in tid:
            data=self.getsx(tid, pg, filter, extend)
        elif 'make' in tid:
            data=self.getmake(tid, pg, filter, extend)
        result = {}
        result['list'] = data
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        return result

    def detailContent(self, ids):
        v=self.getdata(f'/api/v1/video?current=1&pageSize=1&id={ids[0]}&detail=1')
        v=v['data'][0]
        vod = {
            'vod_name': v.get('title'),
            'type_name': '/'.join(v.get('tag_names',[])),
            'vod_play_from': '浴火社',
            'vod_play_url': ''
        }
        p=[]
        for i,j in enumerate(self.bhost):
            p.append(f'{self.names[i]}${j}{v.get("highres_url") or v.get("preview_url")}@@@{v["id"]}')
        vod['vod_play_url'] = '#'.join(p)
        return {'list':[vod]}

    def searchContent(self, key, quick, pg="1"):
        data=self.getdata(f'/api/v1/video?current={pg}&pageSize=30&title={key}')
        return {'list':self.getlist(data),'page':pg}

    def playerContent(self, flag, id, vipFlags):
        url=f'{self.getProxyUrl()}&url={self.e64(id)}&type=m3u8'
        return {'parse': 0, 'url': url, 'header': self.headers}

    def localProxy(self, param):
        if param.get('type')=='image':
            data=self.fetch(param.get('url'), headers=self.headers).text
            content=b64decode(data.encode('utf-8'))
            return [200, 'image/png', content]
        if param.get('type')=='m3u8':
            ids=self.d64(param.get('url')).split('@@@')
            data=self.fetch(ids[0], headers=self.headers).text
            lines = data.strip().split('\n')
            for index, string in enumerate(lines):
                if 'URI=' in string:
                    replacement = f'URI="{self.getProxyUrl()}&id={ids[1]}&type=mkey"'
                    lines[index]=re.sub(r'URI="[^"]+"', replacement, string)
                    continue
                if '#EXT' not in string and 'http' not in string:
                    last_slash_index = ids[0].rfind('/')
                    lpath = ids[0][:last_slash_index + 1]
                    lines[index] = f'{lpath}{string}'
            data = '\n'.join(lines)
            return [200, 'audio/x-mpegurl', data]
        if param.get('type')=='mkey':
            id=param.get('id')
            headers = {
                'User-Agent': 'Mozilla/5.0 (Linux; Android 11; M2012K10C Build/RP1A.200720.011; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/87.0.4280.141 Mobile Safari/537.36',
                'authdog': self.token
            }
            response = self.fetch(f'{self.host}/api/v1/video/key/{id}', headers=headers)
            type=response.headers.get('Content-Type')
            return [200, type, response.content]

    def e64(self, text):
        try:
            text_bytes = text.encode('utf-8')
            encoded_bytes = b64encode(text_bytes)
            return encoded_bytes.decode('utf-8')
        except Exception as e:
            print(f"Base64编码错误: {str(e)}")
            return ""

    def d64(self,encoded_text):
        try:
            encoded_bytes = encoded_text.encode('utf-8')
            decoded_bytes = b64decode(encoded_bytes)
            return decoded_bytes.decode('utf-8')
        except Exception as e:
            print(f"Base64解码错误: {str(e)}")
            return ""

    def getdid(self):
        did = self.md5(str(int(time.time() * 1000)))
        try:
            if self.getCache('did'):
                return self.getCache('did')
            else:
                self.setCache('did', did)
                return did
        except Exception as e:
            self.setCache('did', did)
            return did

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

    def domain(self):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 11; M2012K10C Build/RP1A.200720.011; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/87.0.4280.141 Mobile Safari/537.36',
        }
        response = self.fetch(f'{self.host}/api/v1/system/domain', headers=headers)
        return self.aes(response.content)

    def aes(self, word):
        key = b64decode("amtvaWc5ZnJ2Ym5taml1eQ==")
        iv = b64decode("AAEFAwQFCQcICQoLDA0ODw==")
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = unpad(cipher.decrypt(word), AES.block_size)
        return json.loads(decrypted.decode('utf-8'))

    def md5(self, text):
        h = MD5.new()
        h.update(text.encode('utf-8'))
        return h.hexdigest()

    def gettoken(self):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 11; M2012K10C Build/RP1A.200720.011; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/87.0.4280.141 Mobile Safari/537.36',
            'cookei': self.md5(f'{self.did}+android'),
            'siteid': '11',
            'siteauthority': 'lls888.tv'
        }

        json_data = {
            'app_id': 'jukjoe.zqgpi.hfzvde.sdot',
            'phone_device': 'Redmi M2012K10C',
            'device_id': self.did,
            'device_type': 'android',
            'invite_code': 'oi1o',
            'is_first': 1,
            'os_version': '11',
            'version': '8.59',
        }
        response = self.post(f'{self.host}/api/v1/member/device', headers=headers, json=json_data)
        tdata = self.aes(response.content)
        return f'{tdata["token_type"]} {tdata["access_token"]}'

    def getdata(self, path):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 11; M2012K10C Build/RP1A.200720.011; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/87.0.4280.141 Mobile Safari/537.36',
            'authdog': self.token
        }
        response = self.fetch(f'{self.host}{path}', headers=headers)
        return self.aes(response.content)

    def getimg(self, path):
        if not path.startswith('/'):
            path = f'/{path}'
        return f'{self.getProxyUrl()}&url={self.phost}{path}&type=image'

    def getlist(self,data):
        videos = []
        for i in data['data']:
            videos.append({
                'vod_id': i['id'],
                'vod_name': i['title'],
                'vod_pic': self.getimg(i.get('coverphoto_h' or i.get('coverphoto_v'))),
                'style': {"type": "rect", "ratio": 1.33}})
        return videos

    def geticon(self, data, st='',style=None):
        if style is None:style = {"type": "oval"}
        videos = []
        for i in data['data']:
            videos.append({
                'vod_id': f'{i["id"]}{st}',
                'vod_name': i['name'],
                'vod_pic': self.getimg(i.get('icon_path')),
                'vod_tag': 'folder',
                'style': style})
        return videos

    def getact(self, tid, pg, filter, extend):
        if tid == 'actor' and pg=='1':
            data = self.getdata(f'/api/v1/video/actor?current=1&pageSize=999&region_id={extend.get("region_id",self.aid)}&discover_page={pg}')
            return self.geticon(data, '_act')
        elif '_act' in tid:
            data = self.getdata(f'/api/v1/video?current={pg}&pageSize=50&actor_ids={tid.split("_")[0]}&sortby={extend.get("sortby","on_shelf_at")}')
            return self.getlist(data)

    def gettag(self, tid, pg, filter, extend):
        if '_tag' in tid:
            tid=extend.get('tagtype',tid)
            data=self.getdata(f'/api/v1/video/tag?current={pg}&pageSize=100&level=2&parent_id={tid.split("_")[0]}')
            return self.geticon(data, '_stag',{"type": "rect", "ratio": 1.33})
        elif '_stag' in tid:
            data = self.getdata(f'/api/v1/video?current={pg}&pageSize=50&tag_ids={tid.split("_")[0]}&sortby={extend.get("sortby","on_shelf_at")}')
            return self.getlist(data)

    def getsx(self, tid, pg, filter, extend):
        data=self.getdata(f'/api/v1/video?current={pg}&pageSize=20&producer_ids={tid.split("_")[0]}&region_ids={extend.get("region_ids","")}&sortby={extend.get("sortby","complex")}')
        return self.getlist(data)

    def getmake(self, tid, pg, filter, extend):
        if pg=='1':
            data=self.getdata('/api/v1/video/producer?current=1&pageSize=100&status=1')
            return self.geticon(data, '_sx',{"type": "rect", "ratio": 1.33})

