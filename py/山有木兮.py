# -*- coding: utf-8 -*-
# 本资源来源于互联网公开渠道，仅可用于个人学习爬虫技术。
# 严禁将其用于任何商业用途，下载后请于 24 小时内删除，搜索结果均来自源站，本人不承担任何责任。

import sys,urllib3
sys.path.append('..')
from base.spider import Spider
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class Spider(Spider):
    headers, host = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'accept-language': 'zh-CN,zh;q=0.9',
        'cache-control': 'no-cache',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin'
    }, 'https://film.symx.club'

    def init(self, extend=''):
        try:
            host = extend.strip().rstrip('/')
            if host.startswith('http'):
                self.host = host
                return None
            return None
        except Exception as e:
            print(f'初始化异常：{e}')
            return None

    def homeContent(self, filter):
        response = self.fetch(f'{self.host}/api/category/top', headers=self.headers, verify=False).json()
        classes = []
        for i in  response['data']:
            if isinstance(i,dict):
                classes.append({'type_id': i['id'], 'type_name': i['name']})
        return {'class': classes}

    def homeVideoContent(self):
        response = self.fetch(f'{self.host}/api/film/category',headers=self.headers, verify=False).json()
        videos = []
        for i in response['data']:
            for j in i.get('filmList',[]):
                videos.append({
                    'vod_id': j.get('id'),
                    'vod_name': j.get('name'),
                    'vod_pic': j.get('cover'),
                    'vod_remarks': j.get('doubanScore')
                    })
        return {'list': videos}

    def categoryContent(self, tid, pg, filter, extend):
        response = self.fetch(f'{self.host}/api/film/category/list?area=&categoryId={tid}&language=&pageNum={pg}&pageSize=15&sort=updateTime&year=', headers=self.headers, verify=False).json()
        videos = []
        for i in response['data']['list']:
            videos.append({
                'vod_id': i.get('id'),
                'vod_name': i.get('name'),
                'vod_pic': i.get('cover'),
                'vod_remarks': i.get('updateStatus')
            })
        return {'list': videos, 'page': pg}

    def searchContent(self, key, quick, pg='1'):
        response = self.fetch(f'{self.host}/api/film/search?keyword={key}&pageNum={pg}&pageSize=10', headers=self.headers, verify=False).json()
        videos = []
        for i in response['data']['list']:
            videos.append({
                'vod_id': i.get('id'),
                'vod_name': i.get('name'),
                'vod_pic': i.get('cover'),
                'vod_remarks': i.get('updateStatus'),
                'vod_year': i.get('year'),
                'vod_area': i.get('area'),
                'vod_director': i.get('director')
        })
        return {'list': videos, 'page': pg}

    def detailContent(self, ids):
        response = self.fetch(f'{self.host}/api/film/detail?id={ids[0]}',headers=self.headers, verify=False).json()
        data = response['data']
        video, show, play_urls, = {}, [], []
        for i in data['playLineList']:
            show.append(i['playerName'])
            play_url = []
            for j in i['lines']:
                play_url.append(f"{j['name']}${j['id']}")
            play_urls.append('#'.join(play_url))
        video.update({
            'vod_id': data.get('id'),
            'vod_name': data.get('name'),
            'vod_pic': data.get('cover'),
            'vod_year': data.get('year'),
            'vod_area': data.get('other'),
            'vod_actor': data.get('actor'),
            'vod_director': data.get('director'),
            'vod_content': data.get('blurb'),
            'vod_score': data.get('doubanScore'),
            'vod_play_from': '$$$'.join(show),
            'vod_play_url': '$$$'.join(play_urls)
        })
        return {'list': [video]}

    def playerContent(self, flag, id, vipflags):
        response = self.fetch(f'{self.host}/api/line/play/parse?lineId={id}', headers=self.headers).json()
        return { 'jx': '0', 'parse': '0', 'url': response['data'], 'header': {'User-Agent': self.headers['User-Agent']}}


    def getName(self):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    def localProxy(self, param):
        pass