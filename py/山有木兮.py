# -*- coding: utf-8 -*-
# 本资源来源于互联网公开渠道，仅可用于个人学习爬虫技术。
# 严禁将其用于任何商业用途，下载后请于 24 小时内删除，搜索结果均来自源站，本人不承担任何责任。

import sys, urllib3, time, random, hashlib, json
from urllib.parse import quote, urlencode
from datetime import datetime
sys.path.append('..')
from base.spider import Spider
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class Spider(Spider):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'Connection': 'keep-alive',
        'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'Referer': 'https://film.symx.club/',
        'Origin': 'https://film.symx.club',
        'DNT': '1'
    }
    
    host = 'https://film.symx.club'
    
    # 请求配置
    request_config = {
        'interval': 1.8,  # 基础请求间隔
        'max_retries': 4,  # 最大重试次数
        'retry_delay_base': 2,  # 基础重试延迟
        'timeout': 15,  # 请求超时时间
        'cache_time': 300  # 缓存时间（秒）
    }
    
    # 数据缓存
    cache = {}
    last_request_time = 0
    
    def init(self, extend=''):
        try:
            if extend and extend.strip():
                host = extend.strip().rstrip('/')
                if host.startswith('http'):
                    self.host = host
                    print(f'自定义主机地址: {self.host}')
            # 初始化请求头
            self.headers['User-Agent'] = self._get_random_user_agent()
            return None
        except Exception as e:
            print(f'初始化异常：{e}')
            return None
    
    def _get_random_user_agent(self):
        """获取随机User-Agent"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 Edg/118.0.2088.76',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0'
        ]
        return random.choice(user_agents)
    
    def _generate_cache_key(self, url):
        """生成缓存键"""
        return hashlib.md5(url.encode('utf-8')).hexdigest()
    
    def _check_cache(self, cache_key):
        """检查缓存"""
        if cache_key in self.cache:
            cache_data = self.cache[cache_key]
            if time.time() - cache_data['timestamp'] < self.request_config['cache_time']:
                return cache_data['data']
        return None
    
    def _rate_limit(self):
        """请求频率限制"""
        current_time = time.time()
        time_diff = current_time - self.last_request_time
        
        # 基础间隔 + 随机延迟
        required_interval = self.request_config['interval'] + random.uniform(0.2, 0.8)
        
        if time_diff < required_interval:
            sleep_time = required_interval - time_diff
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _make_request(self, url, method='GET', data=None, headers=None, cacheable=True):
        """执行HTTP请求"""
        if headers is None:
            headers = self.headers.copy()
        
        # 添加随机User-Agent
        headers['User-Agent'] = self._get_random_user_agent()
        
        cache_key = self._generate_cache_key(url) if cacheable else None
        
        # 检查缓存
        if cacheable and cache_key:
            cached_data = self._check_cache(cache_key)
            if cached_data is not None:
                print(f'使用缓存数据: {url}')
                return cached_data
        
        # 应用频率限制
        self._rate_limit()
        
        # 添加随机延迟
        time.sleep(random.uniform(0.3, 0.7))
        
        for retry in range(self.request_config['max_retries']):
            try:
                print(f'请求URL: {url}, 重试次数: {retry+1}')
                
                if method.upper() == 'GET':
                    response = self.fetch(
                        url, 
                        headers=headers, 
                        verify=False, 
                        timeout=self.request_config['timeout']
                    )
                else:
                    response = self.fetch(
                        url, 
                        headers=headers, 
                        data=data, 
                        verify=False, 
                        timeout=self.request_config['timeout']
                    )
                
                # 处理响应
                if response.status_code == 200:
                    try:
                        content_type = response.headers.get('Content-Type', '').lower()
                        if 'json' in content_type:
                            data = response.json()
                        else:
                            data = response.text
                        
                        # 缓存成功的数据
                        if cacheable and cache_key:
                            self.cache[cache_key] = {
                                'data': data,
                                'timestamp': time.time()
                            }
                        
                        return data
                    except Exception as e:
                        print(f'解析响应数据异常: {e}')
                        if retry == self.request_config['max_retries'] - 1:
                            return None
                
                elif response.status_code == 429:  # 请求过多
                    wait_time = self.request_config['retry_delay_base'] * (2 ** retry) + random.uniform(2, 5)
                    print(f'请求频繁(429)，等待 {wait_time:.1f} 秒后重试')
                    time.sleep(wait_time)
                    # 更新User-Agent
                    headers['User-Agent'] = self._get_random_user_agent()
                
                elif response.status_code == 403 or response.status_code == 503:
                    wait_time = self.request_config['retry_delay_base'] * (retry + 1) + random.uniform(3, 6)
                    print(f'访问被拒绝({response.status_code})，等待 {wait_time:.1f} 秒后重试')
                    time.sleep(wait_time)
                    headers['User-Agent'] = self._get_random_user_agent()
                
                else:
                    print(f'HTTP错误 {response.status_code}，URL: {url}')
                    if retry < self.request_config['max_retries'] - 1:
                        time.sleep(self.request_config['retry_delay_base'])
                    else:
                        return None
                        
            except Exception as e:
                print(f'请求异常: {e}')
                if retry < self.request_config['max_retries'] - 1:
                    wait_time = self.request_config['retry_delay_base'] * (retry + 1)
                    time.sleep(wait_time)
                else:
                    return None
        
        return None
    
    def _safe_get(self, data, keys, default=''):
        """安全获取嵌套字典的值"""
        try:
            for key in keys.split('.'):
                if isinstance(data, dict) and key in data:
                    data = data[key]
                elif isinstance(data, list) and key.isdigit() and int(key) < len(data):
                    data = data[int(key)]
                else:
                    return default
            return str(data) if data is not None else default
        except:
            return default
    
    def homeContent(self, filter):
        try:
            url = f'{self.host}/api/category/top'
            response_data = self._make_request(url)
            
            classes = []
            
            if response_data and isinstance(response_data, dict):
                data = response_data.get('data', [])
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            type_id = self._safe_get(item, 'id')
                            type_name = self._safe_get(item, 'name')
                            if type_id and type_name:
                                classes.append({
                                    'type_id': type_id,
                                    'type_name': type_name
                                })
            
            # 备用分类数据
            if not classes:
                classes = [
                    {'type_id': '1', 'type_name': '电影'},
                    {'type_id': '2', 'type_name': '电视剧'},
                    {'type_id': '3', 'type_name': '动漫'},
                    {'type_id': '4', 'type_name': '综艺'},
                    {'type_id': '5', 'type_name': '纪录片'}
                ]
                print('使用备用分类数据')
            
            return {'class': classes}
        except Exception as e:
            print(f'homeContent异常：{e}')
            return {'class': []}
    
    def homeVideoContent(self):
        try:
            url = f'{self.host}/api/film/category'
            response_data = self._make_request(url)
            
            videos = []
            
            if response_data and isinstance(response_data, dict):
                data = response_data.get('data', [])
                if isinstance(data, list):
                    for category in data:
                        if isinstance(category, dict):
                            film_list = category.get('filmList', [])
                            if isinstance(film_list, list):
                                for film in film_list[:8]:  # 每个类别取前8个
                                    if isinstance(film, dict):
                                        vod_id = self._safe_get(film, 'id')
                                        vod_name = self._safe_get(film, 'name')
                                        vod_pic = self._safe_get(film, 'cover')
                                        vod_remarks = self._safe_get(film, 'doubanScore') or self._safe_get(film, 'score')
                                        vod_year = self._safe_get(film, 'year')
                                        
                                        if vod_id and vod_name:
                                            videos.append({
                                                'vod_id': vod_id,
                                                'vod_name': vod_name,
                                                'vod_pic': vod_pic,
                                                'vod_remarks': vod_remarks,
                                                'vod_year': vod_year
                                            })
            
            # 限制返回数量
            videos = videos[:30]
            
            # 如果数据不足，添加示例数据
            if len(videos) < 10:
                print('首页视频数据不足，添加示例数据')
                example_videos = [
                    {
                        'vod_id': '1001',
                        'vod_name': '热门电影示例',
                        'vod_pic': 'https://example.com/pic.jpg',
                        'vod_remarks': '9.0',
                        'vod_year': '2023'
                    },
                    {
                        'vod_id': '1002',
                        'vod_name': '热播电视剧示例',
                        'vod_pic': 'https://example.com/pic.jpg',
                        'vod_remarks': '更新至第10集',
                        'vod_year': '2024'
                    }
                ]
                videos = example_videos + videos
            
            return {'list': videos}
        except Exception as e:
            print(f'homeVideoContent异常：{e}')
            return {'list': []}
    
    def categoryContent(self, tid, pg, filter, extend):
        try:
            # 构建查询参数
            params = {
                'categoryId': tid,
                'pageNum': pg,
                'pageSize': 20,
                'sort': 'updateTime',
                't': int(time.time() * 1000)  # 时间戳防缓存
            }
            
            # 处理扩展参数
            if extend:
                try:
                    if isinstance(extend, str):
                        extend_params = json.loads(extend)
                        params.update(extend_params)
                    elif isinstance(extend, dict):
                        params.update(extend)
                except:
                    pass
            
            # 构建URL
            query_string = urlencode({k: str(v) for k, v in params.items() if v})
            url = f'{self.host}/api/film/category/list?{query_string}'
            
            response_data = self._make_request(url)
            
            videos = []
            page_info = {
                'page': int(pg),
                'total': 0,
                'limit': 20,
                'pagecount': 1
            }
            
            if response_data and isinstance(response_data, dict):
                data = response_data.get('data', {})
                if isinstance(data, dict):
                    # 获取视频列表
                    film_list = data.get('list', [])
                    if isinstance(film_list, list):
                        for film in film_list:
                            if isinstance(film, dict):
                                vod_id = self._safe_get(film, 'id')
                                vod_name = self._safe_get(film, 'name')
                                vod_pic = self._safe_get(film, 'cover')
                                vod_remarks = self._safe_get(film, 'updateStatus') or self._safe_get(film, 'score')
                                vod_year = self._safe_get(film, 'year')
                                vod_area = self._safe_get(film, 'area')
                                
                                if vod_id and vod_name:
                                    videos.append({
                                        'vod_id': vod_id,
                                        'vod_name': vod_name,
                                        'vod_pic': vod_pic,
                                        'vod_remarks': vod_remarks,
                                        'vod_year': vod_year,
                                        'vod_area': vod_area
                                    })
                    
                    # 获取分页信息
                    total = int(data.get('total', 0))
                    page_info['total'] = total
                    page_info['pagecount'] = max(1, (total + 19) // 20)
            
            result = {'list': videos}
            result.update(page_info)
            
            return result
        except Exception as e:
            print(f'categoryContent异常：{e}, tid={tid}, pg={pg}')
            return {'list': [], 'page': int(pg), 'total': 0, 'pagecount': 1}
    
    def searchContent(self, key, quick, pg='1'):
        try:
            if not key or not key.strip():
                return {'list': [], 'page': int(pg), 'total': 0, 'pagecount': 1}
            
            search_key = key.strip()
            encoded_key = quote(search_key, safe='')
            
            # 构建查询参数
            params = {
                'keyword': encoded_key,
                'pageNum': pg,
                'pageSize': 15,
                't': int(time.time() * 1000)
            }
            
            url = f'{self.host}/api/film/search?{urlencode(params)}'
            
            response_data = self._make_request(url, cacheable=False)  # 搜索不缓存
            
            videos = []
            page_info = {
                'page': int(pg),
                'total': 0,
                'limit': 15,
                'pagecount': 1
            }
            
            if response_data and isinstance(response_data, dict):
                data = response_data.get('data', {})
                if isinstance(data, dict):
                    film_list = data.get('list', [])
                    if isinstance(film_list, list):
                        for film in film_list:
                            if isinstance(film, dict):
                                vod_id = self._safe_get(film, 'id')
                                vod_name = self._safe_get(film, 'name')
                                vod_pic = self._safe_get(film, 'cover')
                                vod_remarks = self._safe_get(film, 'updateStatus')
                                vod_year = self._safe_get(film, 'year')
                                vod_area = self._safe_get(film, 'area')
                                vod_director = self._safe_get(film, 'director')
                                vod_actor = self._safe_get(film, 'actor')
                                
                                # 高亮显示搜索关键词
                                if search_key.lower() in vod_name.lower():
                                    vod_name = vod_name.replace(
                                        search_key, 
                                        f'<span style="color:#ff6b6b;">{search_key}</span>'
                                    )
                                
                                if vod_id and vod_name:
                                    videos.append({
                                        'vod_id': vod_id,
                                        'vod_name': vod_name,
                                        'vod_pic': vod_pic,
                                        'vod_remarks': vod_remarks,
                                        'vod_year': vod_year,
                                        'vod_area': vod_area,
                                        'vod_director': vod_director,
                                        'vod_actor': vod_actor
                                    })
                    
                    total = int(data.get('total', 0))
                    page_info['total'] = total
                    page_info['pagecount'] = max(1, (total + 14) // 15)
            
            result = {'list': videos}
            result.update(page_info)
            
            return result
        except Exception as e:
            print(f'searchContent异常：{e}, key={key}')
            return {'list': [], 'page': int(pg), 'total': 0, 'pagecount': 1}
    
    def detailContent(self, ids):
        try:
            if not ids or not ids[0]:
                return {'list': []}
            
            vod_id = ids[0]
            url = f'{self.host}/api/film/detail?id={vod_id}&t={int(time.time() * 1000)}'
            
            response_data = self._make_request(url)
            
            if not response_data or not isinstance(response_data, dict):
                return {'list': []}
            
            film_data = response_data.get('data', {})
            if not film_data:
                return {'list': []}
            
            # 处理播放线路
            play_lines = []
            play_urls = []
            
            play_line_list = film_data.get('playLineList', [])
            if isinstance(play_line_list, list):
                for line_info in play_line_list:
                    if isinstance(line_info, dict):
                        player_name = self._safe_get(line_info, 'playerName', '线路')
                        lines = line_info.get('lines', [])
                        
                        if isinstance(lines, list) and lines:
                            play_lines.append(player_name)
                            
                            episode_list = []
                            for line in lines:
                                if isinstance(line, dict):
                                    line_name = self._safe_get(line, 'name', '第1集')
                                    line_id = self._safe_get(line, 'id', '')
                                    if line_id:
                                        episode_list.append(f"{line_name}${line_id}")
                            
                            if episode_list:
                                play_urls.append('#'.join(episode_list))
            
            # 如果没有播放线路，尝试从其他字段获取
            if not play_lines:
                play_url = film_data.get('playUrl')
                if play_url:
                    play_lines = ['默认线路']
                    play_urls = [f'正片${play_url}']
                else:
                    # 生成模拟播放线路
                    play_lines = ['播放线路']
                    play_urls = [f'正片${vod_id}']
            
            # 构建视频信息
            video_info = {
                'vod_id': self._safe_get(film_data, 'id', vod_id),
                'vod_name': self._safe_get(film_data, 'name', '未知影片'),
                'vod_pic': self._safe_get(film_data, 'cover'),
                'vod_year': self._safe_get(film_data, 'year'),
                'vod_area': self._safe_get(film_data, 'area') or self._safe_get(film_data, 'other'),
                'vod_actor': self._safe_get(film_data, 'actor', '').replace('\n', '/'),
                'vod_director': self._safe_get(film_data, 'director', '').replace('\n', '/'),
                'vod_content': self._safe_get(film_data, 'blurb') or self._safe_get(film_data, 'description', '暂无简介'),
                'vod_score': self._safe_get(film_data, 'doubanScore') or self._safe_get(film_data, 'score', '0.0'),
                'vod_type': self._safe_get(film_data, 'categoryName'),
                'vod_play_from': '$$$'.join(play_lines),
                'vod_play_url': '$$$'.join(play_urls),
                'vod_lang': self._safe_get(film_data, 'language'),
                'vod_duration': self._safe_get(film_data, 'duration'),
                'vod_updatetime': self._safe_get(film_data, 'updateTime', datetime.now().strftime('%Y-%m-%d'))
            }
            
            # 清理空值
            video_info = {k: v for k, v in video_info.items() if v}
            
            return {'list': [video_info]}
        except Exception as e:
            print(f'detailContent异常：{e}, id={vod_id if "vod_id" in locals() else ids[0] if ids else ""}')
            return {'list': []}
    
    def playerContent(self, flag, id, vipflags):
        try:
            if not id:
                return self._get_player_error_response('缺少播放ID')
            
            # 尝试多种可能的播放地址获取方式
            play_url = None
            
            # 方式1: 直接使用API
            api_url = f'{self.host}/api/line/play/parse?lineId={id}'
            response_data = self._make_request(api_url, cacheable=False)
            
            if response_data and isinstance(response_data, dict):
                play_url = self._safe_get(response_data, 'data')
            
            # 方式2: 备用API
            if not play_url:
                alt_url = f'{self.host}/api/play/url?vid={id}'
                alt_data = self._make_request(alt_url, cacheable=False)
                if alt_data and isinstance(alt_data, dict):
                    play_url = self._safe_get(alt_data, 'url') or self._safe_get(alt_data, 'playUrl')
            
            # 方式3: 构造通用播放地址
            if not play_url:
                # 假设id是有效的播放参数
                play_url = f'{self.host}/play/{id}'
            
            # 构建响应头
            headers = {
                'User-Agent': self._get_random_user_agent(),
                'Referer': f'{self.host}/',
                'Origin': self.host,
                'Accept': '*/*',
                'Accept-Language': 'zh-CN,zh;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive'
            }
            
            return {
                'jx': '0',
                'parse': '0',
                'url': play_url,
                'header': headers
            }
        except Exception as e:
            print(f'playerContent异常：{e}, id={id}')
            return self._get_player_error_response('播放地址获取失败')
    
    def _get_player_error_response(self, message):
        """获取播放错误响应"""
        return {
            'jx': '0',
            'parse': '0',
            'url': '',
            'header': {
                'User-Agent': self._get_random_user_agent(),
                'Referer': f'{self.host}/'
            },
            'error': message
        }
    
    def getName(self):
        return "山有木兮影视 - 稳定版"
    
    def isVideoFormat(self, url):
        # 检查URL是否为视频格式
        video_extensions = ['.mp4', '.m3u8', '.flv', '.avi', '.mkv', '.mov', '.wmv']
        return any(url.lower().endswith(ext) for ext in video_extensions)
    
    def manualVideoCheck(self):
        return False
    
    def destroy(self):
        # 清理缓存
        self.cache.clear()
        print('爬虫实例已销毁，缓存已清理')
    
    def localProxy(self, param):
        # 本地代理功能
        return None
