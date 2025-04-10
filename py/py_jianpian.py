# -*- coding: utf-8 -*-
# @Author  : Doubebly
# @Time    : 2025/1/21 20:57
# JianPian
import sys
import requests
sys.path.append('..')
from base.spider import Spider


class Spider(Spider):
    def getName(self):
        return "JianPian"

    def init(self, extend):
        self.home_url = 'http://apijp.jianpianedge.com'
        self.headers = {
            "User-Agent": "jianpian-android/365",
            'Host': 'apijp.jianpianedge.com',
            'JPAUTH': 'bhhxAK8WwQNOcZk9C4+mO4H+W3IdMN52/XBD3ND0yr4C',
            'Connection': 'keep-alive',
            'Accept-Encoding': 'gzip',
        }

    def getDependence(self):
        return []

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def homeContent(self, filter):

        return {'class': [
            {
                'type_id': '1',
                'type_name': '电影'
            },
            {
                'type_id': '2',
                'type_name': '电视剧'
            },
            {
                'type_id': '3',
                'type_name': '动漫'
            },
            {
                'type_id': '4',
                'type_name': '综艺'
            }
        ]}

    def homeVideoContent(self):
        a = []
        try:
            res = requests.get(url=self.home_url + '/api/crumb/list?area=0&code=unknownbe2a5c4162bb5528&category_id=0&year=0&limit=24&channel=wandoujia&page=1&sort=hot&type=0', headers=self.headers)
            if res.status_code != 200:
                return {'list': [], 'parse': 0, 'jx': 0, 'msg': f'status_code: {res.status_code}'}
            data_list = res.json()['data']
            for i in data_list:
                a.append(
                    {
                        'vod_id': i['id'],
                        'vod_name': i['title'],
                        'vod_pic': i['path'],
                        'vod_remarks': i['playlist']['title'],
                        'vod_year': i['score'],
                    }
                )
            return {'list': a, 'parse': 0, 'jx': 0}
        except requests.exceptions.RequestException as e:
            return {'list': [], 'parse': 0, 'jx': 0, 'msg': str(e)}

    def categoryContent(self, cid, page, filter, ext):
        a = []
        try:
            res = requests.get(url=self.home_url + f'/api/crumb/list?area=0&code=unknownbe2a5c4162bb5528&category_id={cid}&year=0&limit=24&channel=wandoujia&page={page}&sort=hot&type=0',
                               headers=self.headers)
            if res.status_code != 200:
                return {'list': [], 'parse': 0, 'jx': 0, 'msg': f'status_code: {res.status_code}'}
            data_list = res.json()['data']
            for i in data_list:
                a.append(
                    {
                        'vod_id': i['id'],
                        'vod_name': i['title'],
                        'vod_pic': i['path'],
                        'vod_remarks': i['playlist']['title'],
                        'vod_year': i['score'],
                    }
                )
            return {'list': a, 'parse': 0, 'jx': 0}
        except requests.exceptions.RequestException as e:
            return {'list': [], 'parse': 0, 'jx': 0, 'msg': str(e)}


    def detailContent(self, did):
        ids = did[0]
        video_list = []
        try:
            res = requests.get(f'{self.home_url}/api/node/detail?channel=wandoujia&token=&id={ids}', headers=self.headers)
            if res.status_code != 200:
                return {"list": video_list, 'parse': 0, 'jx': 0}
            video_list.append(
                {
                    'type_name': ' '.join(i['name'] for i in res.json()['data']['types']),
                    'vod_id': ids,
                    'vod_name': res.json()['data']['title'],
                    'vod_remarks': res.json()['data']['mask'],
                    'vod_year': res.json()['data']['year']['title'],
                    'vod_area': ' '.join(i['title'] for i in res.json()['data']['category']),
                    'vod_actor': ' '.join(i['name'] for i in res.json()['data']['actors']),
                    'vod_director': res.json()['data']['directors'][0]['name'],
                    'vod_content': res.json()['data']['description'],
                    'vod_play_from': '边下边播超清版',
                    'vod_play_url': '#'.join([i['val'] for i in res.json()['data']['m3u8_downlist']])
                }
            )
            return {"list": video_list, 'parse': 0, 'jx': 0}
        except requests.RequestException as e:
            return {'list': [], 'msg': str(e)}

    def searchContent(self, key, quick, page='1'):
        a = []
        try:
            res = requests.get(url=self.home_url + f'/api/video/search?page={page}&key={key}',headers=self.headers)
            if res.status_code != 200:
                return {'list': [], 'parse': 0, 'jx': 0, 'msg': f'status_code: {res.status_code}'}
            data_list = res.json()['data']
            for i in data_list:
                a.append(
                    {
                        'vod_id': i['id'],
                        'vod_name': i['title'],
                        'vod_pic': i['tvimg'],
                        'vod_remarks': i['mask'],
                        'vod_year': i['score'],
                    }
                )
            return {'list': a, 'parse': 0, 'jx': 0}
        except requests.exceptions.RequestException as e:
            return {'list': [], 'parse': 0, 'jx': 0, 'msg': str(e)}

    def playerContent(self, flag, pid, vipFlags):
        h = {
            'User-Agent': 'jianpian-android/365',
        }
        return {'url': pid, 'header': h, 'parse': 0, 'jx': 0}

    def localProxy(self, params):
        pass

    def destroy(self):
        return '正在Destroy'

if __name__ == '__main__':
    pass
