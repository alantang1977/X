# -*- coding: utf-8 -*-
# 本资源来源于互联网公开渠道，仅可用于个人学习爬虫技术。
# 严禁将其用于任何商业用途，下载后请于 24 小时内删除，搜索结果均来自源站，本人不承担任何责任。

import sys, urllib3
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
        'sec-fetch-site': 'same-origin',
        'Referer': 'https://film.symx.club/'
    }, 'https://film.symx.club'

    def init(self, extend=''):
        try:
            if extend and extend.strip():
                host = extend.strip().rstrip('/')
                if host.startswith('http'):
                    self.host = host
            return None
        except Exception as e:
            print(f'初始化异常：{e}')
            return None

    def homeContent(self, filter):
        try:
            response = self.fetch(f'{self.host}/api/category/top', headers=self.headers, verify=False)
            if response.status_code != 200:
                return {'class': []}
            
            data = response.json()
            classes = []
            if 'data' in data and isinstance(data['data'], list):
                for item in data['data']:
                    if isinstance(item, dict) and 'id' in item and 'name' in item:
                        classes.append({
                            'type_id': str(item['id']),
                            'type_name': str(item['name'])
                        })
            return {'class': classes}
        except Exception as e:
            print(f'homeContent异常：{e}')
            return {'class': []}

    def homeVideoContent(self):
        try:
            response = self.fetch(f'{self.host}/api/film/category', headers=self.headers, verify=False)
            if response.status_code != 200:
                return {'list': []}
            
            data = response.json()
            videos = []
            if 'data' in data and isinstance(data['data'], list):
                for category in data['data']:
                    if isinstance(category, dict) and 'filmList' in category:
                        film_list = category.get('filmList', [])
                        for film in film_list:
                            if isinstance(film, dict):
                                videos.append({
                                    'vod_id': str(film.get('id', '')),
                                    'vod_name': str(film.get('name', '')),
                                    'vod_pic': str(film.get('cover', '')),
                                    'vod_remarks': str(film.get('doubanScore', ''))
                                })
            return {'list': videos}
        except Exception as e:
            print(f'homeVideoContent异常：{e}')
            return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            url = f'{self.host}/api/film/category/list?categoryId={tid}&pageNum={pg}&pageSize=15'
            if extend:
                url += f'&{extend}'
                
            response = self.fetch(url, headers=self.headers, verify=False)
            if response.status_code != 200:
                return {'list': [], 'page': int(pg)}
            
            data = response.json()
            videos = []
            if 'data' in data and 'list' in data['data']:
                film_list = data['data']['list']
                for film in film_list:
                    if isinstance(film, dict):
                        videos.append({
                            'vod_id': str(film.get('id', '')),
                            'vod_name': str(film.get('name', '')),
                            'vod_pic': str(film.get('cover', '')),
                            'vod_remarks': str(film.get('updateStatus', ''))
                        })
            return {'list': videos, 'page': int(pg)}
        except Exception as e:
            print(f'categoryContent异常：{e}')
            return {'list': [], 'page': int(pg)}

    def searchContent(self, key, quick, pg='1'):
        try:
            url = f'{self.host}/api/film/search?keyword={key}&pageNum={pg}&pageSize=10'
            response = self.fetch(url, headers=self.headers, verify=False)
            if response.status_code != 200:
                return {'list': [], 'page': int(pg)}
            
            data = response.json()
            videos = []
            if 'data' in data and 'list' in data['data']:
                film_list = data['data']['list']
                for film in film_list:
                    if isinstance(film, dict):
                        videos.append({
                            'vod_id': str(film.get('id', '')),
                            'vod_name': str(film.get('name', '')),
                            'vod_pic': str(film.get('cover', '')),
                            'vod_remarks': str(film.get('updateStatus', '')),
                            'vod_year': str(film.get('year', '')),
                            'vod_area': str(film.get('area', '')),
                            'vod_director': str(film.get('director', ''))
                        })
            return {'list': videos, 'page': int(pg)}
        except Exception as e:
            print(f'searchContent异常：{e}')
            return {'list': [], 'page': int(pg)}

    def detailContent(self, ids):
        try:
            if not ids or not ids[0]:
                return {'list': []}
                
            url = f'{self.host}/api/film/detail?id={ids[0]}'
            response = self.fetch(url, headers=self.headers, verify=False)
            if response.status_code != 200:
                return {'list': []}
            
            data = response.json()
            if 'data' not in data:
                return {'list': []}
                
            film_data = data['data']
            show, play_urls = [], []
            
            if 'playLineList' in film_data and isinstance(film_data['playLineList'], list):
                for play_line in film_data['playLineList']:
                    if isinstance(play_line, dict):
                        player_name = play_line.get('playerName', '')
                        if player_name:
                            show.append(player_name)
                            
                        play_url = []
                        if 'lines' in play_line and isinstance(play_line['lines'], list):
                            for line in play_line['lines']:
                                if isinstance(line, dict) and 'name' in line and 'id' in line:
                                    play_url.append(f"{line['name']}${line['id']}")
                        
                        if play_url:
                            play_urls.append('#'.join(play_url))
            
            video = {
                'vod_id': str(film_data.get('id', '')),
                'vod_name': str(film_data.get('name', '')),
                'vod_pic': str(film_data.get('cover', '')),
                'vod_year': str(film_data.get('year', '')),
                'vod_area': str(film_data.get('other', film_data.get('area', ''))),
                'vod_actor': str(film_data.get('actor', '')),
                'vod_director': str(film_data.get('director', '')),
                'vod_content': str(film_data.get('blurb', '')),
                'vod_score': str(film_data.get('doubanScore', '')),
                'vod_play_from': '$$$'.join(show) if show else '',
                'vod_play_url': '$$$'.join(play_urls) if play_urls else ''
            }
            
            return {'list': [video]}
        except Exception as e:
            print(f'detailContent异常：{e}')
            return {'list': []}

    def playerContent(self, flag, id, vipflags):
        try:
            url = f'{self.host}/api/line/play/parse?lineId={id}'
            response = self.fetch(url, headers=self.headers, verify=False)
            if response.status_code != 200:
                return {'jx': '0', 'parse': '0', 'url': '', 'header': {'User-Agent': self.headers['User-Agent']}}
            
            data = response.json()
            play_url = data.get('data', '') if 'data' in data else ''
            
            return {
                'jx': '0',
                'parse': '0',
                'url': str(play_url),
                'header': {
                    'User-Agent': self.headers['User-Agent'],
                    'Referer': f'{self.host}/'
                }
            }
        except Exception as e:
            print(f'playerContent异常：{e}')
            return {'jx': '0', 'parse': '0', 'url': '', 'header': {'User-Agent': self.headers['User-Agent']}}

    def getName(self):
        return "山有木兮影视"

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    def localProxy(self, param):
        pass
