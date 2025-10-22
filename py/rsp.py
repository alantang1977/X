# -*- coding: utf-8 -*-
# by @嗷呜
import json
import sys
import requests
from pyquery import PyQuery as pq
sys.path.append('..')
from base.spider import Spider


class Spider(Spider):

    def init(self, extend='{}'):
        config=json.loads(extend)
        self.proxies=config.get('proxies',{})
        self.plp=config.get('plp','')
        self.session=requests.session()
        self.session.proxies=self.proxies
        pass

    def getName(self):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    host='https://rou.video'

    headers = {
        'referer': f'{host}/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
    }

    def homeContent(self, filter):
        cdata=self.getpq(self.session.get(f'{self.host}/cat', headers=self.headers))
        result = {}
        classes = []
        filters = {}
        for k in cdata('.space-y-8 section').items():
            id=k('h2 a').attr('href')
            classes.append({
                'type_name': k('h2').text(),
                'type_id': id
            })
            filters[id]=[{'key':'order','name':'order','value':[{'n':'观看','v':'viewCount'},{'n':'点赞','v':'likeCount'}]}].copy()
            if k('.grid.grid-cols-2 a'):
                filters[id].append({
                    'key': 'type',
                    'name': 'type',
                    'value': [{
                        'n': i.text(),
                        'v': i.attr('href')
                    }for i in k('.grid.grid-cols-2 a').items()]
                })
        result['class'] = classes
        result['filters'] = filters
        return result

    def homeVideoContent(self):
        res = self.getpq(self.session.get(f'{self.host}/home', headers=self.headers))
        videos=self.getlist(res('.grid.grid-cols-2.lg\\:grid-cols-4 div.aspect-video.relative'))
        return {'list':videos}

    def categoryContent(self, tid, pg, filter, extend):
        tid=extend.get('type') or tid
        params= {
            'order': extend.get('order',''),
            'page': pg,
        }
        data=self.getpq(self.session.get(f'{self.host}{tid}',params=params, headers=self.headers))
        result = {}
        result['list'] = self.getlist(data('.grid.grid-cols-2 div.aspect-video.relative'))
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        return result

    def detailContent(self, ids):
        data=self.getpq(self.session.get(f'{self.host}{ids[0]}', headers=self.headers))
        url=self.session.get(f"{self.host}/api{ids[0]}",headers=self.headers).json()['video']['videoUrl']
        n=data('.md\\:col-span-2 .px-2 .hidden').eq(0).text() or 'xxxx'
        vod = {
            'vod_content': ' '.join(['[a=cr:' + json.dumps({'id': j.attr('href'), 'name': j.text()}) + '/]' + j.text() + '[/a]' for j in data('.flex.justify-between div a').items()]),
            'vod_play_from': '书生玩剣ⁱ·*₁＇',
            'vod_play_url': f"{n}${url}"
        }
        return {'list':[vod]}

    def searchContent(self, key, quick, pg="1"):
        params = {'q': key,'page': pg}
        data=self.getpq(self.session.get(f'{self.host}/search',params=params, headers=self.headers))
        return {'list':self.getlist(data('.grid.grid-cols-2 div.aspect-video.relative')),'page':pg}

    def playerContent(self, flag, id, vipFlags):
        return  {'parse': 0, 'url': f"{self.plp}{id}", 'header': self.headers}

    def localProxy(self, param):
        pass

    def liveContent(self, url):
        pass

    def getlist(self,data):
        videos = []
        for i in data.items():
            videos.append({
                'vod_id': i('a').attr('href'),
                'vod_name': i('img.relative.w-full').attr('alt'),
                'vod_pic': i('img.relative.w-full').attr('src'),
                'vod_year': i('.absolute.top-1').text(),
                'vod_remarks': i('.absolute.bottom-1').text(),
                'style': {"type": "rect", "ratio": 1.33}
            })
        return  videos

    def getpq(self, data):
        try:
            return pq(data.text)
        except Exception as e:
            print(f"{str(e)}")

            return pq(data.text.encode('utf-8'))
