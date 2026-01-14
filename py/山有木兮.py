# -*- coding: utf-8 -*-
# 本资源来源于互联网公开渠道，仅可用于个人学习爬虫技术。
# 严禁将其用于任何商业用途，下载后请于 24 小时内删除，搜索结果均来自源站，本人不承担任何责任。

import sys, urllib3, time, random
from urllib.parse import quote
sys.path.append('..')
from base.spider import Spider
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class Spider(Spider):
    headers, host = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'Connection': 'keep-alive',
        'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'Referer': 'https://film.symx.club/',
        'Origin': 'https://film.symx.club'
    }, 'https://film.symx.club'
    
    # 请求相关配置
    last_request_time = 0
    request_interval = 1.5  # 请求间隔（秒）
    max_retries = 3  # 最大重试次数
    retry_delay = 3  # 重试延迟（秒）

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

    def _request_with_retry(self, url, method='GET', data=None, headers=None):
        """带重试机制的请求函数"""
        if headers is None:
            headers = self.headers.copy()
        
        for retry in range(self.max_retries):
            try:
                # 控制请求频率
                current_time = time.time()
                time_since_last = current_time - self.last_request_time
                if time_since_last < self.request_interval:
                    sleep_time = self.request_interval - time_since_last + random.uniform(0.1, 0.5)
                    time.sleep(sleep_time)
                
                self.last_request_time = time.time()
                
                # 添加随机延迟
                time.sleep(random.uniform(0.1, 0.3))
                
                # 执行请求
                if method.upper() == 'GET':
                    response = self.fetch(url, headers=headers, verify=False, timeout=10)
                else:
                    response = self.fetch(url, headers=headers, data=data, verify=False, timeout=10)
                
                if response.status_code == 200:
                    try:
                        return response.json()
                    except:
                        return response.text
                elif response.status_code == 429:  # 请求过多
                    wait_time = self.retry_delay * (retry + 1) + random.uniform(1, 3)
                    print(f'请求频繁，等待 {wait_time:.1f} 秒后重试 ({retry+1}/{self.max_retries})')
                    time.sleep(wait_time)
                    continue
                elif response.status_code == 403:  # 被禁止访问
                    print(f'访问被拒绝，状态码: {response.status_code}')
                    # 更新User-Agent
                    headers['User-Agent'] = self._get_random_user_agent()
                    time.sleep(self.retry_delay)
                    continue
                else:
                    print(f'请求失败，状态码: {response.status_code}, URL: {url}')
                    if retry < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                        continue
                    return None
                    
            except Exception as e:
                print(f'请求异常: {e}, URL: {url}')
                if retry < self.max_retries - 1:
                    wait_time = self.retry_delay * (retry + 1)
                    time.sleep(wait_time)
                    continue
                return None
        
        return None

    def _get_random_user_agent(self):
        """获取随机User-Agent"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
        ]
        return random.choice(user_agents)

    def homeContent(self, filter):
        try:
            url = f'{self.host}/api/category/top'
            response_data = self._request_with_retry(url)
            
            if not response_data:
                return {'class': []}
            
            classes = []
            if 'data' in response_data and isinstance(response_data['data'], list):
                for item in response_data['data']:
                    if isinstance(item, dict) and 'id' in item and 'name' in item:
                        classes.append({
                            'type_id': str(item['id']),
                            'type_name': str(item['name'])
                        })
            
            # 如果没获取到数据，返回默认分类
            if not classes:
                classes = [
                    {'type_id': '1', 'type_name': '电影'},
                    {'type_id': '2', 'type_name': '电视剧'},
                    {'type_id': '3', 'type_name': '动漫'},
                    {'type_id': '4', 'type_name': '综艺'}
                ]
            
            return {'class': classes}
        except Exception as e:
            print(f'homeContent异常：{e}')
            return {'class': []}

    def homeVideoContent(self):
        try:
            url = f'{self.host}/api/film/category'
            response_data = self._request_with_retry(url)
            
            if not response_data:
                return {'list': []}
            
            videos = []
            if 'data' in response_data and isinstance(response_data['data'], list):
                for category in response_data['data']:
                    if isinstance(category, dict) and 'filmList' in category:
                        film_list = category.get('filmList', [])
                        for film in film_list:
                            if isinstance(film, dict):
                                videos.append({
                                    'vod_id': str(film.get('id', '')),
                                    'vod_name': str(film.get('name', '')).strip(),
                                    'vod_pic': str(film.get('cover', '')),
                                    'vod_remarks': str(film.get('doubanScore', film.get('score', ''))),
                                    'vod_year': str(film.get('year', ''))
                                })
            
            return {'list': videos[:30]}  # 限制首页显示数量
        except Exception as e:
            print(f'homeVideoContent异常：{e}')
            return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            base_url = f'{self.host}/api/film/category/list'
            params = {
                'categoryId': tid,
                'pageNum': pg,
                'pageSize': 20,
                'sort': 'updateTime'
            }
            
            # 处理扩展参数
            if extend:
                try:
                    import json
                    extend_dict = json.loads(extend)
                    params.update(extend_dict)
                except:
                    pass
            
            # 构建查询字符串
            query_parts = []
            for key, value in params.items():
                if value:
                    query_parts.append(f'{key}={quote(str(value))}')
            
            url = f'{base_url}?{"&".join(query_parts)}'
            
            response_data = self._request_with_retry(url)
            
            if not response_data:
                return {'list': [], 'page': int(pg), 'total': 0}
            
            videos = []
            total = 0
            
            if 'data' in response_data:
                data = response_data['data']
                if 'list' in data and isinstance(data['list'], list):
                    film_list = data['list']
                    for film in film_list:
                        if isinstance(film, dict):
                            videos.append({
                                'vod_id': str(film.get('id', '')),
                                'vod_name': str(film.get('name', '')).strip(),
                                'vod_pic': str(film.get('cover', '')),
                                'vod_remarks': str(film.get('updateStatus', film.get('score', film.get('remarks', '')))),
                                'vod_year': str(film.get('year', '')),
                                'vod_area': str(film.get('area', ''))
                            })
                
                if 'total' in data:
                    total = int(data.get('total', 0))
            
            return {
                'list': videos,
                'page': int(pg),
                'total': total,
                'limit': 20,
                'pagecount': (total + 19) // 20 if total > 0 else 1
            }
        except Exception as e:
            print(f'categoryContent异常：{e}, tid={tid}, pg={pg}')
            return {'list': [], 'page': int(pg), 'total': 0}

    def searchContent(self, key, quick, pg='1'):
        try:
            if not key or key.strip() == '':
                return {'list': [], 'page': int(pg), 'total': 0}
            
            encoded_key = quote(key.strip())
            url = f'{self.host}/api/film/search?keyword={encoded_key}&pageNum={pg}&pageSize=15'
            
            response_data = self._request_with_retry(url)
            
            if not response_data:
                return {'list': [], 'page': int(pg), 'total': 0}
            
            videos = []
            total = 0
            
            if 'data' in response_data and 'list' in response_data['data']:
                film_list = response_data['data']['list']
                for film in film_list:
                    if isinstance(film, dict):
                        videos.append({
                            'vod_id': str(film.get('id', '')),
                            'vod_name': str(film.get('name', '')).strip(),
                            'vod_pic': str(film.get('cover', '')),
                            'vod_remarks': str(film.get('updateStatus', '')),
                            'vod_year': str(film.get('year', '')),
                            'vod_area': str(film.get('area', '')),
                            'vod_director': str(film.get('director', '')),
                            'vod_actor': str(film.get('actor', ''))
                        })
                
                if 'total' in response_data['data']:
                    total = int(response_data['data'].get('total', 0))
            
            return {
                'list': videos,
                'page': int(pg),
                'total': total,
                'limit': 15,
                'pagecount': (total + 14) // 15 if total > 0 else 1
            }
        except Exception as e:
            print(f'searchContent异常：{e}, key={key}')
            return {'list': [], 'page': int(pg), 'total': 0}

    def detailContent(self, ids):
        try:
            if not ids or not ids[0]:
                return {'list': []}
            
            vod_id = ids[0]
            url = f'{self.host}/api/film/detail?id={vod_id}'
            
            response_data = self._request_with_retry(url)
            
            if not response_data or 'data' not in response_data:
                return {'list': []}
            
            film_data = response_data['data']
            show, play_urls = [], []
            
            # 处理播放线路
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
                                    line_name = line.get('name', '').strip()
                                    line_id = line.get('id', '')
                                    if line_name and line_id:
                                        play_url.append(f"{line_name}${line_id}")
                        
                        if play_url:
                            play_urls.append('#'.join(play_url))
            
            # 处理剧集信息
            vod_play_from = '$$$'.join(show) if show else '线路一'
            vod_play_url = '$$$'.join(play_urls) if play_urls else ''
            
            # 如果没有播放线路，尝试从其他字段获取
            if not vod_play_url and 'playUrl' in film_data:
                vod_play_url = str(film_data.get('playUrl', ''))
            
            video = {
                'vod_id': str(film_data.get('id', vod_id)),
                'vod_name': str(film_data.get('name', '')).strip(),
                'vod_pic': str(film_data.get('cover', '')),
                'vod_year': str(film_data.get('year', '')),
                'vod_area': str(film_data.get('area', film_data.get('other', ''))),
                'vod_actor': str(film_data.get('actor', '')).replace('\n', ' ').strip(),
                'vod_director': str(film_data.get('director', '')).replace('\n', ' ').strip(),
                'vod_content': str(film_data.get('blurb', film_data.get('description', ''))).strip(),
                'vod_score': str(film_data.get('doubanScore', film_data.get('score', ''))),
                'vod_type': str(film_data.get('categoryName', '')),
                'vod_play_from': vod_play_from,
                'vod_play_url': vod_play_url,
                'vod_tag': str(film_data.get('tags', '')),
                'vod_lang': str(film_data.get('language', ''))
            }
            
            return {'list': [video]}
        except Exception as e:
            print(f'detailContent异常：{e}, id={ids[0] if ids else ""}')
            return {'list': []}

    def playerContent(self, flag, id, vipflags):
        try:
            if not id:
                return {
                    'jx': '0',
                    'parse': '0',
                    'url': '',
                    'header': {
                        'User-Agent': self.headers['User-Agent'],
                        'Referer': f'{self.host}/'
                    }
                }
            
            url = f'{self.host}/api/line/play/parse?lineId={id}'
            response_data = self._request_with_retry(url)
            
            play_url = ''
            if response_data and 'data' in response_data:
                play_url = str(response_data.get('data', ''))
            
            # 如果API没有返回播放地址，尝试其他方式
            if not play_url:
                # 可以尝试其他解析方式
                pass
            
            return {
                'jx': '0',
                'parse': '0',
                'url': play_url,
                'header': {
                    'User-Agent': self.headers['User-Agent'],
                    'Referer': f'{self.host}/',
                    'Origin': self.host
                }
            }
        except Exception as e:
            print(f'playerContent异常：{e}, id={id}')
            return {
                'jx': '0',
                'parse': '0',
                'url': '',
                'header': {
                    'User-Agent': self.headers['User-Agent'],
                    'Referer': f'{self.host}/'
                }
            }

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
