import re
import sys
import urllib.parse
from pyquery import PyQuery as pq

sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def getName(self):
        return "韩剧网"
    
    def init(self, extend):
        self.baseUrl = "https://www.hanju7.com"
        self.cookies = ""
        self.header = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': self.baseUrl
        }
        # 分类配置
        self.classes = [
            {'type_id': '1', 'type_name': '韩剧'},
            {'type_id': '3', 'type_name': '韩国电影'},
            {'type_id': '4', 'type_name': '韩国综艺'}
        ]
        
    def homeContent(self, filter):
        result = {}
        result['class'] = self.classes
        return result

    def homeVideoContent(self):
        result = {}
        try:
            videos = []
            rsp = self.fetch(self.baseUrl, headers=self.header)
            if rsp and rsp.text:
                doc = pq(rsp.text)
                
                # 提取首页视频
                items = doc('.box .list li')
                for item in items.items():
                    video = self._parse_video_item(item)
                    if video:
                        videos.append(video)
            
            result['list'] = videos
        except Exception as e:
            print(f"homeVideoContent error: {e}")
            
        return result

    def _parse_video_item(self, item):
        """解析视频列表项"""
        try:
            # 提取基本信息
            link_el = item.find('a.tu')
            title_el = item.find('p a')
            tip_el = item.find('.tip')
            actor_el = item.find('p:nth-child(3)')
            
            # 标题
            vod_name = ''
            if title_el:
                vod_name = title_el.text().strip()
            elif link_el:
                vod_name = link_el.attr('title') or ''
            
            if not vod_name:
                return None
                
            # 图片
            vod_pic = ''
            if link_el:
                data_original = link_el.attr('data-original')
                if data_original:
                    vod_pic = data_original
                else:
                    style = link_el.attr('style') or ''
                    if 'background-image:' in style:
                        match = re.search(r'url\(["\']?(.*?)["\']?\)', style)
                        if match:
                            vod_pic = match.group(1)
            
            # 详情页链接
            vod_href = ''
            if link_el and link_el.attr('href'):
                href = link_el.attr('href')
                vod_href = self.baseUrl + ('' if href.startswith('/') else '/') + href
            elif title_el and title_el.attr('href'):
                href = title_el.attr('href')
                vod_href = self.baseUrl + ('' if href.startswith('/') else '/') + href
            
            # 视频ID
            vod_id = ''
            if vod_href:
                match = re.search(r'/detail/(\d+)\.html', vod_href)
                if match:
                    vod_id = match.group(1)
            
            if not vod_id:
                vod_id = re.sub(r'[^\w]', '_', vod_name)
            
            # 备注
            vod_remarks = tip_el.text().strip() if tip_el else ''
            
            # 演员
            vod_actor = actor_el.text().strip() if actor_el else ''
            
            return {
                'vod_id': vod_id,
                'vod_name': vod_name,
                'vod_pic': vod_pic,
                'vod_remarks': vod_remarks,
                'vod_actor': vod_actor,
                'vod_href': vod_href
            }
            
        except Exception as e:
            print(f"_parse_video_item error: {e}")
            return None

    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        videos = []
        try:
            # 解析过滤条件
            year = ''
            sort = ''
            category = ''
            
            if filter:
                # 解析年份
                if 'year' in filter:
                    year = filter['year']
                # 解析排序
                if 'sort' in filter:
                    sort = filter['sort']
                # 解析分类
                if 'category' in filter:
                    category = filter['category']
            
            # 构建URL
            url = self._build_category_url(tid, pg, year, sort, category)
            
            rsp = self.fetch(url, headers=self.header)
            if rsp and rsp.text:
                doc = pq(rsp.text)
                
                # 提取视频列表
                items = doc('.list li')
                for item in items.items():
                    video = self._parse_video_item(item)
                    if video:
                        videos.append(video)
                
                # 提取分页信息
                page = int(pg) if pg and pg.isdigit() else 1
                pagecount = self._parse_page_count(doc)
                
                # 提取过滤选项
                filters = self._parse_filter_options(doc, tid)
                
        except Exception as e:
            print(f"categoryContent error: {e}")
            
        result['list'] = videos
        result['page'] = int(pg) if pg and pg.isdigit() else 1
        result['pagecount'] = pagecount if 'pagecount' in locals() else 1
        result['limit'] = 20
        result['total'] = len(videos)
        
        # 如果有过滤选项，添加到结果中
        if 'filters' in locals() and filters:
            result['filters'] = filters
            
        return result

    def _build_category_url(self, tid, pg, year='', sort='', category=''):
        """构建分类页URL"""
        # 基础URL模式: /list/{type}-{year}-{sort}-{page}.html
        
        # 处理年份
        year_part = year if year else ''
        
        # 处理排序
        sort_part = ''
        if sort == 'newstime':
            sort_part = 'newstime'
        elif sort == 'onclick':
            sort_part = 'onclick'
        
        # 构建URL
        url = f"{self.baseUrl}/list/{tid}-{year_part}-{sort_part}-{int(pg)-1 if pg and pg.isdigit() else ''}.html"
        
        # 清理多余的横线
        url = re.sub(r'-+', '-', url)
        url = re.sub(r'\.html$', '.html', url.replace('-.html', '.html'))
        
        return url

    def _parse_page_count(self, doc):
        """解析总页数"""
        try:
            page_links = doc('.page a')
            if page_links:
                last_page = 0
                for link in page_links.items():
                    text = link.text().strip()
                    if text.isdigit():
                        num = int(text)
                        if num > last_page:
                            last_page = num
                if last_page > 0:
                    return last_page
        except:
            pass
        return 1

    def _parse_filter_options(self, doc, tid):
        """解析过滤选项"""
        filters = {}
        
        try:
            # 解析年份过滤
            year_filter = {
                'key': 'year',
                'name': '年份',
                'value': [{'n': '全部', 'v': ''}]
            }
            
            # 解析分类过滤
            category_filter = {
                'key': 'category',
                'name': '分类',
                'value': [{'n': '全部', 'v': ''}]
            }
            
            # 解析排序过滤
            sort_filter = {
                'key': 'sort',
                'name': '排序',
                'value': [
                    {'n': '最新', 'v': 'newstime'},
                    {'n': '热门', 'v': 'onclick'}
                ]
            }
            
            # 提取年份选项
            year_elements = doc('.category:contains("年份") a')
            for element in year_elements.items():
                text = element.text().strip()
                href = element.attr('href')
                if href:
                    # 从URL中提取年份值
                    match = re.search(r'/list/\d+-(\d+[^\-]*)', href)
                    if match:
                        year_value = match.group(1)
                        year_filter['value'].append({
                            'n': text,
                            'v': year_value
                        })
            
            # 添加过滤器
            filters[tid] = [year_filter, sort_filter]
            
        except Exception as e:
            print(f"_parse_filter_options error: {e}")
        
        return filters

    def detailContent(self, array):
        result = {}
        if not array or not array[0]:
            return result
            
        try:
            aid = array[0]
            
            # 构建详情页URL
            if aid.startswith('http'):
                url = aid
            elif aid.isdigit():
                url = f"{self.baseUrl}/detail/{aid}.html"
            else:
                url = f"{self.baseUrl}/detail/{aid}.html"
            
            rsp = self.fetch(url, headers=self.header)
            if not rsp or not rsp.text:
                return result
                
            doc = pq(rsp.text)
            
            # 提取标题
            title = doc('h1').text() or doc('.title').text() or doc('.detail-title').text() or ''
            
            # 提取图片
            vod_pic = ''
            img_el = doc('.pic img, .detail-pic img, .thumb img')
            if img_el:
                vod_pic = img_el.attr('src') or img_el.attr('data-src') or img_el.attr('data-original') or ''
            
            # 如果没有找到图片，使用默认格式
            if not vod_pic and aid.isdigit():
                vod_pic = f'//pics.hanju7.com/pics/{aid}.jpg'
            
            # 提取详细信息
            vod_area = vod_year = vod_actor = vod_director = vod_remarks = vod_lang = vod_content = ''
            
            # 尝试多种信息选择器
            info_items = doc('.info p, .detail-info p, .info li, .data p, .vodinfo p')
            for item in info_items.items():
                text = item.text().strip()
                if '地区：' in text:
                    vod_area = text.replace('地区：', '').strip()
                elif '年份：' in text:
                    vod_year = text.replace('年份：', '').strip()
                elif '主演：' in text:
                    vod_actor = text.replace('主演：', '').strip()
                elif '导演：' in text:
                    vod_director = text.replace('导演：', '').strip()
                elif '语言：' in text:
                    vod_lang = text.replace('语言：', '').strip()
                elif '状态：' in text or '更新：' in text:
                    vod_remarks = text.replace('状态：', '').replace('更新：', '').strip()
            
            # 提取简介
            content_el = doc('.content, .intro, .detail-content, .sketch')
            if content_el:
                vod_content = content_el.text().strip()
            
            # 提取播放列表
            playlists = []
            
            # 查找所有可能的播放列表容器
            playlist_containers = doc('.playlist, .play-list, .downlist, .stui-content__playlist, .player')
            
            for container in playlist_containers.items():
                # 提取线路标题
                line_title = container.prev('h3, h4, .head, .title').text() or '线路1'
                
                # 提取剧集
                episodes = []
                links = container.find('a')
                
                for link in links.items():
                    episode_name = link.text().strip()
                    episode_url = link.attr('href') or ''
                    
                    if episode_url and not episode_url.startswith('http'):
                        episode_url = self.baseUrl + ('' if episode_url.startswith('/') else '/') + episode_url
                    
                    if episode_name and episode_url:
                        episodes.append(f"{episode_name}${episode_url}")
                
                if episodes:
                    playlists.append({
                        'title': line_title,
                        'episodes': episodes
                    })
            
            # 如果没有找到播放列表，尝试查找播放按钮
            if not playlists:
                play_buttons = doc('a[href*="play"], a:contains("播放"), .playbtn, .player-btn')
                if play_buttons:
                    episodes = []
                    for btn in play_buttons.items():
                        episode_name = btn.text().strip() or '播放'
                        episode_url = btn.attr('href') or ''
                        
                        if episode_url and not episode_url.startswith('http'):
                            episode_url = self.baseUrl + ('' if episode_url.startswith('/') else '/') + episode_url
                        
                        if episode_url:
                            episodes.append(f"{episode_name}${episode_url}")
                    
                    if episodes:
                        playlists.append({
                            'title': '在线播放',
                            'episodes': episodes
                        })
            
            # 构建播放信息
            vod_play_from = '$$$'.join([p['title'] for p in playlists]) if playlists else '韩剧网'
            vod_play_url = '$$$'.join(['#'.join(p['episodes']) for p in playlists]) if playlists else f'正片${url}'
            
            # 构建视频对象
            vod = {
                'vod_id': aid if aid.isdigit() else re.sub(r'[^\w]', '_', aid),
                'vod_name': title,
                'vod_pic': vod_pic,
                'vod_remarks': vod_remarks,
                'vod_year': vod_year,
                'vod_actor': vod_actor,
                'vod_director': vod_director,
                'vod_area': vod_area,
                'vod_lang': vod_lang or '韩语',
                'vod_content': vod_content,
                'vod_play_from': vod_play_from,
                'vod_play_url': vod_play_url,
                'type_name': self._get_type_name(url)
            }
            
            result['list'] = [vod]
            
        except Exception as e:
            print(f"detailContent error: {e}")
            
        return result

    def _get_type_name(self, url):
        """从URL获取类型名称"""
        match = re.search(r'/list/(\d+)', url)
        if match:
            type_id = match.group(1)
            if type_id == '1':
                return '韩剧'
            elif type_id == '3':
                return '韩国电影'
            elif type_id == '4':
                return '韩国综艺'
        return ''

    def searchContent(self, key, quick, page='1'):
        result = {}
        videos = []
        try:
            if not key:
                return result
                
            # 构建搜索URL
            encoded_key = urllib.parse.quote(key.encode('utf-8'))
            url = f"{self.baseUrl}/search/?wd={encoded_key}&page={page}"
            
            rsp = self.fetch(url, headers=self.header)
            if rsp and rsp.text:
                doc = pq(rsp.text)
                
                # 尝试多种搜索结果选择器
                items = doc('.search-list li, .list li, .vodlist li')
                
                for item in items.items():
                    video = self._parse_video_item(item)
                    if video and key.lower() in video['vod_name'].lower():
                        videos.append(video)
                
        except Exception as e:
            print(f"searchContent error: {e}")
            
        result['list'] = videos
        return result

    def playerContent(self, flag, id, vipFlags):
        result = {}
        try:
            if not id:
                return result
            
            # 处理播放URL
            if id.startswith('http'):
                play_url = id
            else:
                # 如果id是数字，尝试获取详情页
                if id.isdigit():
                    detail_url = f"{self.baseUrl}/detail/{id}.html"
                    rsp = self.fetch(detail_url, headers=self.header)
                    if rsp and rsp.text:
                        doc = pq(rsp.text)
                        # 查找播放地址
                        play_link = doc('a[href*="play"], .playbtn, iframe[src*="player"], video source')
                        if play_link:
                            play_url = play_link.attr('href') or play_link.attr('src') or ''
                            if play_url and not play_url.startswith('http'):
                                play_url = self.baseUrl + ('' if play_url.startswith('/') else '/') + play_url
                        else:
                            # 如果没有找到播放地址，使用详情页作为播放页
                            play_url = detail_url
                else:
                    play_url = id
            
            # 设置播放参数
            result["parse"] = 1  # 需要解析
            result["playUrl"] = ''
            result["url"] = play_url
            result["header"] = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': self.baseUrl
            }
            
        except Exception as e:
            print(f"playerContent error: {e}")
            
        return result

    def isVideoFormat(self, url):
        # 检查URL是否为视频格式
        video_extensions = ['.mp4', '.m3u8', '.flv', '.avi', '.mkv', '.mov', '.wmv', '.mpg', '.ts']
        return any(ext in url.lower() for ext in video_extensions)

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return {}
