# -*- coding: utf-8 -*-
# @Author  : Doubebly
# @Time    : 2025/1/20 14:55

import sys
import requests
import urllib.parse
from lxml import etree
sys.path.append('..')
from base.spider import Spider


class Spider(Spider):
    def getName(self):
        return "Rou"

    def init(self, extend):
        self.home_url = 'https://rouvz3.xyz'
        self.proxy_base = 'https://vpsdn.leuse.top/proxy?single=true&url='
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"}

    def getDependence(self):
        return []

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def _get_with_proxy(self, url, headers=None):
        """使用代理发送请求的辅助方法"""
        if headers is None:
            headers = self.headers
            
        proxy_url = self.proxy_base + urllib.parse.quote(url)
        try:
            res = requests.get(proxy_url, headers=headers, timeout=10)
            return res
        except requests.exceptions.RequestException as e:
            print(f"请求失败: {e}")
            return None

    def homeContent(self, filter):
        url = self.home_url+'/cat'
        try:
            res = self._get_with_proxy(url)
            if res is None or res.status_code != 200:
                return {'class': [], 'msg': f'请求失败: {res.status_code if res else "网络错误"}'}
            root = etree.HTML(res.text.encode('utf-8'))
            name_list = root.xpath('//div[@class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3"]/a/text()')
            url_list = root.xpath('//div[@class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3"]/a/@href')
            if len(name_list) < 1 or len(url_list) < 1:
                return {'class': [], 'msg': '获取的数据为空'}
            a = []
            for name ,url in zip(name_list, url_list):
                a.append({'type_name': name, 'type_id': url})
            return {'class': a}
        except Exception as e:
            return {'class': [], 'msg': str(e)}

    def homeVideoContent(self):
        url = self.home_url + '/home'
        try:
            res = self._get_with_proxy(url)
            if res is None or res.status_code != 200:
                return {'list': [], 'parse': 0, 'jx': 0, 'msg': f'请求失败: {res.status_code if res else "网络错误"}'}
            root = etree.HTML(res.text.encode('utf-8'))
            data_list = root.xpath('//div[@class="aspect-video relative"]/a')
            if len(data_list) < 1:
                return {'list': [], 'parse': 0, 'jx': 0, 'msg': '获取的数据为空'}
            a = []
            for i in data_list:
                vod_remarks = i.xpath('./div[2]/text()')
                vod_year = i.xpath('./div[3]/text()')
                a.append(
                    {
                        'vod_id': i.xpath('./@href')[0],
                        'vod_name': i.xpath('./img/@alt')[-1],
                        'vod_pic': i.xpath('./img/@src')[0],
                        'vod_remarks': vod_remarks[0] if vod_remarks else '',
                        'vod_year': vod_year[0] if vod_year else '',
                        'style': {"type": "rect", "ratio": 1.5}
                    }
                )
            return {'list': a, 'parse': 0, 'jx': 0}
        except Exception as e:
            return {'list': [], 'parse': 0, 'jx': 0, 'msg': str(e)}

    def categoryContent(self, cid, page, filter, ext):
        url = f'{self.home_url}{cid}?order=createdAt&page={page}'
        try:
            res = self._get_with_proxy(url)
            if res is None or res.status_code != 200:
                return {'list': [], 'parse': 0, 'jx': 0, 'msg': f'请求失败: {res.status_code if res else "网络错误"}'}
            root = etree.HTML(res.text.encode('utf-8'))
            data_list = root.xpath('//div[@class="aspect-video relative"]/a')
            if len(data_list) < 1:
                return {'list': [], 'parse': 0, 'jx': 0, 'msg': '获取的数据为空'}
            a = []
            for i in data_list:
                vod_remarks = i.xpath('./div[2]/text()')
                vod_year = i.xpath('./div[3]/text()')
                a.append(
                    {
                        'vod_id': i.xpath('./@href')[0],
                        'vod_name': i.xpath('./img/@alt')[-1],
                        'vod_pic': i.xpath('./img/@src')[0],
                        'vod_remarks': vod_remarks[0] if vod_remarks else '',
                        'vod_year': vod_year[0] if vod_year else '',
                        'style': {"type": "rect", "ratio": 1.5}
                    }
                )
            return {'list': a, 'parse': 0, 'jx': 0}
        except Exception as e:
            return {'list': [], 'parse': 0, 'jx': 0, 'msg': str(e)}

    def detailContent(self, did):
        ids = did[0]
        video_list = []
        url = self.home_url + f'/api{ids}'
        h = {
            'accept': '*/*',
            'accept-language': 'zh-CN,zh;q=0.9',
            'cache-control': 'no-cache',
            'content-type': 'application/json',
            'referer': 'https://rou.video',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        }
        try:
            res = self._get_with_proxy(url, headers=h)
            if res is None or res.status_code != 200:
                return {'list': [], 'parse': 0, 'jx': 0, 'msg': f'请求失败: {res.status_code if res else "网络错误"}'}
            play_url = res.json()['video']['videoUrl']
            video_list.append(
                {
                    'type_name': '',
                    'vod_id': ids,
                    'vod_name': '',
                    'vod_remarks': '',
                    'vod_year': '',
                    'vod_area': '',
                    'vod_actor': '',
                    'vod_director': '大家好我叫撸出血！',
                    'vod_content': '',
                    'vod_play_from': 'Rou',
                    'vod_play_url': f'1${play_url}',
                    'msearch': True

                }
            )
            return {"list": video_list, 'parse': 0, 'jx': 0,'msearch': True}
        except Exception as e:
            return {'list': [], 'msg': str(e)}

    def searchContent(self, key, quick, page='1'):
        url = f'{self.home_url}/search?q={key}&page={page}'
        try:
            res = self._get_with_proxy(url)
            if res is None or res.status_code != 200:
                return {'list': [], 'parse': 0, 'jx': 0, 'msg': f'请求失败: {res.status_code if res else "网络错误"}'}
            root = etree.HTML(res.text.encode('utf-8'))
            data_list = root.xpath('//div[@class="aspect-video relative"]/a')
            if len(data_list) < 1:
                return {'list': [], 'parse': 0, 'jx': 0, 'msg': '获取的数据为空'}
            a = []
            for i in data_list:
                vod_remarks = i.xpath('./div[2]/text()')
                vod_year = i.xpath('./div[3]/text()')
                a.append(
                    {
                        'vod_id': i.xpath('./@href')[0],
                        'vod_name': i.xpath('./img/@alt')[-1],
                        'vod_pic': i.xpath('./img/@src')[0],
                        'vod_remarks': vod_remarks[0] if vod_remarks else '',
                        'vod_year': vod_year[0] if vod_year else '',
                        'style': {"type": "rect", "ratio": 1.5}
                    }
                )
            return {'list': a, 'parse': 0, 'jx': 0}
        except Exception as e:
            return {'list': [], 'parse': 0, 'jx': 0, 'msg': str(e)}

    def playerContent(self, flag, pid, vipFlags):
        return {'url': pid, "header": self.headers, 'parse': 0, 'jx': 0}

    def localProxy(self, params):
        pass

    def destroy(self):
        return '正在Destroy'

if __name__ == '__main__':
    pass