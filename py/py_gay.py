# -*- coding: utf-8 -*-
# @Author  : Doubebly
# @Time    : 2025/9/9 20:36
import sys
import requests
from lxml import etree
from urllib.parse import quote, unquote
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
sys.path.append('..')
from base.spider import Spider


class Spider(Spider):
    def getName(self):
        return self.vod.name

    def init(self, extend):
        self.vod = Vod(extend, self.getProxyUrl())

    def getDependence(self):
        return []

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def liveContent(self, url):
        return self.vod.liveContent(url)

    def homeContent(self, filter):
        return self.vod.homeContent(filter)

    def homeVideoContent(self):
        return self.vod.homeVideoContent()

    def categoryContent(self, cid, page, filter, ext):
        return self.vod.categoryContent(cid, page, filter, ext)

    def detailContent(self, did):
        return self.vod.detailContent(did)

    def searchContent(self, key, quick, page='1'):
        return self.vod.searchContent(key, quick, page)

    def playerContent(self, flag, pid, vipFlags):
        return self.vod.playerContent(flag, pid, vipFlags)

    def localProxy(self, params):
        if params['type'] == 'img':
            try:
                content = self.vod.decrypt_img(unquote(params['url']))
                return [200, "application/octet-stream", content]
            except Exception as e:
                print(f"Image decryption failed: {e}")
                return [500, "text/plain", b"Image Error"]
        return [404, "text/plain", b""]
        pass

    def destroy(self):
        return '正在Destroy'


class Vod:
    def __init__(self, extend='{}', proxy_url=""):
        self.debug = False
        self.getProxyUrl = proxy_url
        self.log(f'{proxy_url}')
        self.name = 'GAY'
        self.error_play_url = 'https://sf1-cdn-tos.huoshanstatic.com/obj/media-fe/xgplayer_doc_video/mp4/xgplayer-demo-720p.mp4'
        self.home_url = 'https://91nt.com'
        self.headers = {
            'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
            'Accept': "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            'accept-language': "zh-CN,zh;q=0.9",
            'cache-control': "no-cache",
            'pragma': "no-cache",
            'priority': "u=0, i",
            'referer': "https://91nt.com/",
            'sec-ch-ua': "\"Chromium\";v=\"140\", \"Not=A?Brand\";v=\"24\", \"Google Chrome\";v=\"140\"",
            'sec-ch-ua-mobile': "?0",
            'sec-ch-ua-platform': "\"Windows\"",
            'sec-fetch-dest': "document",
            'sec-fetch-mode': "navigate",
            'sec-fetch-site': "same-origin",
            'sec-fetch-user': "?1",
            'upgrade-insecure-requests': "1",
        }

    def homeContent(self, filter):
        self.log('执行了， homeContent')
        return {'class': [{'type_id': 'play', 'type_name': '精选G片'},
                          {'type_id': 'xrbj', 'type_name': '鲜肉薄肌'},
                          {'type_id': 'wtns', 'type_name': '无套内射'},
                          {'type_id': 'zfyh', 'type_name': '制服诱惑'},
                          {'type_id': 'dmfj', 'type_name': '耽美天菜'},
                          {'type_id': 'jrmn', 'type_name': '肌肉猛男'},
                          {'type_id': 'rhgv', 'type_name': '日韩GV'},
                          {'type_id': 'omjd', 'type_name': '欧美巨屌'},
                          {'type_id': 'drqp', 'type_name': '多人群交'},
                          {'type_id': 'kjys', 'type_name': '口交颜射'},
                          {'type_id': 'tjsm', 'type_name': '调教SM'}],
                'filters': {'play': [{'key': 'tag',
                                      'name': '分类',
                                      'value': [{'n': '当前最热', 'v': 'popular'},
                                                {'n': '最近更新', 'v': 'new'},
                                                {'n': '正在播放', 'v': 'watchings'},
                                                {'n': '小蓝原创', 'v': 'xiaolan'},
                                                {'n': '本月最热', 'v': 'mon'},
                                                {'n': '10分钟以上', 'v': '10min'},
                                                {'n': '20分钟以上', 'v': '20min'},
                                                {'n': '本月收藏', 'v': 'collect'},
                                                {'n': '高清', 'v': 'hd'},
                                                {'n': '每月最热', 'v': 'every'},
                                                {'n': '本月讨论', 'v': 'current'},
                                                {'n': '收藏最多', 'v': 'most'}]}]}}

    def homeVideoContent(self):
        self.log('执行了， homeVideoContent')
        data_list = []
        url = f'{self.home_url}/videos/all/new'
        res = requests.get(url, headers=self.headers)
        root = etree.HTML(res.text.encode('utf-8'))
        data = root.xpath('//li/div[@class="video-item"]')
        for i in data:
            data_list.append(
                {
                    'vod_id': i.xpath('./div[1]/a/@href')[0].strip(),
                    'vod_name': i.xpath('./div[1]/a/text()')[0].strip(),
                    'vod_pic': f"{self.getProxyUrl}&type=img&url={quote(i.xpath('.//img/@data-src')[0])}",
                    'vod_remarks': i.xpath('.//div[contains(@class, "text-sm")]/text()')[0]
                }
            )
        return {'list': data_list, 'parse': 0, 'jx': 0}

    def categoryContent(self, cid, page, filter, ext):
        self.log('执行了， categoryContent')
        data_list = []
        if cid == 'play':
            url = f'{self.home_url}/videos/all/watchings/{page}'
        else:
            url = f'{self.home_url}/videos/category/{cid}/{page}'
        res = requests.get(url, headers=self.headers)
        root = etree.HTML(res.text.encode('utf-8'))
        data = root.xpath('//li/div[@class="video-item"]')
        for i in data:
            data_list.append(
                {
                    'vod_id': i.xpath('./div[1]/a/@href')[0].strip(),
                    'vod_name': i.xpath('./div[1]/a/text()')[0].strip(),
                    'vod_pic': f"{self.getProxyUrl}&type=img&url={quote(i.xpath('.//img/@data-src')[0])}",
                    'vod_remarks': i.xpath('.//div[contains(@class, "text-sm")]/text()')[0]
                }
            )
        return {'list': data_list, 'parse': 0, 'jx': 0}

    def detailContent(self, did):
        ids = did[0]
        url = f'{self.home_url}{ids}'
        res = requests.get(url, headers=self.headers)
        root = etree.HTML(res.text.encode('utf-8'))
        play_url = root.xpath('//div[@class="player-container"]/div/@data-url')[0]
        play_name = root.xpath('//div[@class="player-container"]/div/@data-video')[0]
        video_list = []
        video_list.append(
            {
                'type_name': '',
                'vod_id': ids,
                'vod_name': '',
                'vod_remarks': '',
                'vod_year': '',
                'vod_area': '',
                'vod_actor': '',
                'vod_director': '',
                'vod_content': '',
                'vod_play_from': self.name,
                'vod_play_url': f'{play_name}${play_url}'

            }
        )
        return {"list": video_list, 'parse': 0, 'jx': 0}

    def searchContent(self, key, quick, page='1'):
        self.log('执行了， searchContent')
        data_list = []
        url = f'{self.home_url}/videos/search/{key}/{page}'
        res = requests.get(url, headers=self.headers)
        root = etree.HTML(res.text.encode('utf-8'))
        data = root.xpath('//li/div[@class="video-item"]')
        for i in data:
            # vod_id = i.xpath('./div[1]/a/@href')[0].strip()
            # vod_name = i.xpath('./div[1]/a/text()')[0].strip()
            # vod_pic = i.xpath('.//img/@data-src')[0]
            # vod_remarks = i.xpath('.//div[contains(@class, "text-sm")]/text()')[0]
            # self.log(f"{vod_id}, {vod_name}, {vod_pic}, {vod_remarks}")
            data_list.append(
                {
                    'vod_id': i.xpath('./div[1]/a/@href')[0].strip(),
                    'vod_name': i.xpath('./div[1]/a/text()')[0].strip().decode('utf-8'),
                    'vod_pic': f"{self.getProxyUrl}&type=img&url={quote(i.xpath('.//img/@data-src')[0])}",
                    'vod_remarks': i.xpath('.//div[contains(@class, "text-sm")]/text()')[0]
                }
            )
        return {'list': data_list, 'parse': 0, 'jx': 0}

    def playerContent(self, flag, pid, vipFlags):
        return {'url': pid, 'parse': 0, 'jx': 0}

    def liveContent(self, url):
        pass

    def decrypt_img(self, url):
        self.log('执行了， decrypt_img')
        key_str = 'f5d965df75336270'
        iv_str = '97b60394abc2fbe1'
        key = key_str.encode('utf-8')
        iv = iv_str.encode('utf-8')
        encrypted_bytes = requests.get(url, timeout=5).content
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted_bytes = cipher.decrypt(encrypted_bytes)
        final_data = unpad(decrypted_bytes, AES.block_size)
        return final_data

    def log(self,  msg):
        if self.debug:
            try:
                requests.post('http://192.168.31.12:5000/log', data=msg, timeout=1)
            except Exception as e:
                print(e)

if __name__ == '__main__':
    pass
