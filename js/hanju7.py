import re
import sys
import json
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
        
    def homeContent(self, filter):
        result = {}
        classes = []
        
        try:
            # 基础分类
            base_classes = [
                {'type_id': '1', 'type_name': '韩剧'},
                {'type_id': '3', 'type_name': '韩国电影'},
                {'type_id': '4', 'type_name': '韩国综艺'}
            ]
            
            classes.extend(base_classes)
            
            # 热门分类
            hot_classes = [
                {'type_id': 'hot', 'type_name': '排行榜'},
                {'type_id': 'new', 'type_name': '最近更新'}
            ]
            
            classes.extend(hot_classes)
            
        except Exception as e:
            print(f"homeContent error: {e}")
            
        result['class'] = classes
        return result

    def homeVideoContent(self):
        result = {}
        try:
            videos = []
            rsp = self.fetch(self.baseUrl, headers=self.header)
            if rsp and rsp.text:
                doc = pq(rsp.text)
                
                # 提取首页三个板块的视频
                sections = [
                    ('.box:nth-child(1) .list li', '韩剧'),
                    ('.box:nth-child(2) .list li', '韩影'),
                    ('.box:nth-child(3) .list li', '韩综')
                ]
                
                for selector, vod_type in sections:
                    items = doc(selector)
                    for item in items.items():
                        video = self._parse_video_item(item)
                        if video:
                            video['vod_type'] = vod_type
                            videos.append(video)
                
                # 限制数量
                videos = videos[:30]
            
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
            if vod_actor and vod_actor.endswith('…'):
                vod_actor = vod_actor[:-1]
            
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
            # 构建URL
            if tid == 'hot':
                url = f"{self.baseUrl}/hot.html"
            elif tid == 'new':
                url = f"{self.baseUrl}/new.html"
            else:
                # 解析过滤参数
                year = filter.get('year', '') if filter else ''
                sort = filter.get('sort', '') if filter else ''
                
                # 构建分类URL
                url = self._build_category_url(tid, pg, year, sort)
            
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
                if tid in ['1', '3', '4']:
                    filters = self._parse_filter_options(doc, tid)
                    result['filters'] = filters
                
        except Exception as e:
            print(f"categoryContent error: {e}")
            
        result['list'] = videos
        result['page'] = int(pg) if pg and pg.isdigit() else 1
        result['pagecount'] = pagecount if 'pagecount' in locals() else 1
        result['limit'] = 20
        result['total'] = len(videos) * result['pagecount']
        
        return result

    def _build_category_url(self, tid, pg, year='', sort=''):
        """构建分类页URL"""
        # 默认值处理
        if not pg or not pg.isdigit():
            pg = '1'
        
        # 将页码转换为URL格式（从0开始）
        page_num = int(pg) - 1 if int(pg) > 0 else 0
        
        # 构建URL
        url = f"{self.baseUrl}/list/{tid}-{year}-{sort}-{page_num}.html"
        
        # 清理多余的横线
        url = re.sub(r'-+', '-', url)
        url = url.replace('-.html', '.html')
        
        return url

    def _parse_page_count(self, doc):
        """解析总页数"""
        try:
            page_text = doc('.page').text() or ''
            if page_text:
                # 匹配数字
                numbers = re.findall(r'\d+', page_text)
                if numbers:
                    return int(max(numbers))
        except:
            pass
        return 1

    def _parse_filter_options(self, doc, tid):
        """解析过滤选项"""
        filters = {}
        
        try:
            # 年份过滤器
            year_filter = {
                'key': 'year',
                'name': '年份',
                'value': [{'n': '全部', 'v': ''}]
            }
            
            # 排序过滤器
            sort_filter = {
                'key': 'sort',
                'name': '排序',
                'value': [
                    {'n': '最新', 'v': 'newstime'},
                    {'n': '热门', 'v': 'onclick'}
                ]
            }
            
            # 提取年份选项
            year_elements = doc('.category:contains("年份") a, dl:contains("年份") a')
            for element in year_elements.items():
                text = element.text().strip()
                href = element.attr('href')
                if href and text:
                    # 从URL中提取年份值
                    match = re.search(r'/list/\d+-(\d+[^\-]*)', href)
                    if match:
                        year_value = match.group(1)
                        year_filter['value'].append({
                            'n': text,
                            'v': year_value
                        })
            
            # 提取排序选项
            sort_elements = doc('.category:contains("排序") a, dl:contains("排序") a')
            for element in sort_elements.items():
                text = element.text().strip()
                href = element.attr('href')
                if href and text:
                    # 从URL中提取排序值
                    match = re.search(r'/list/\d+[^\-]*-([^\-]+)-', href)
                    if match:
                        sort_value = match.group(1)
                        sort_filter['value'].append({
                            'n': text,
                            'v': sort_value
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
                # 尝试解析ID
                match = re.search(r'(\d+)', aid)
                if match:
                    url = f"{self.baseUrl}/detail/{match.group(1)}.html"
                else:
                    return result
            
            rsp = self.fetch(url, headers=self.header)
            if not rsp or not rsp.text:
                return result
                
            doc = pq(rsp.text)
            
            # 提取标题
            title = doc('#m').text() or doc('h1').text() or doc('.detail-title').text() or ''
            
            # 提取图片
            vod_pic = ''
            img_el = doc('.pic img')
            if img_el:
                vod_pic = img_el.attr('data-original') or img_el.attr('src') or ''
            
            # 如果没有找到图片，使用默认格式
            if not vod_pic and aid.isdigit():
                vod_pic = f'//pics.hanju7.com/pics/{aid}.jpg'
            
            # 从script标签提取信息
            vod_info = self._extract_info_from_script(doc)
            
            # 提取详细信息
            vod_area = vod_info.get('area', '')
            vod_year = vod_info.get('year', '')
            vod_actor = vod_info.get('actor', '')
            vod_director = vod_info.get('director', '')
            vod_remarks = vod_info.get('remarks', '')
            vod_lang = vod_info.get('lang', '韩语')
            vod_content = vod_info.get('content', '')
            
            # 提取其他信息
            info_items = doc('.info dl')
            for item in info_items.items():
                dt_text = item.find('dt').text().strip()
                dd_text = item.find('dd').text().strip()
                
                if '主演：' in dt_text or '主演' in dt_text:
                    vod_actor = dd_text
                elif '状态：' in dt_text or '状态' in dt_text:
                    vod_remarks = dd_text.replace('<em>', '').replace('</em>', '').strip()
                elif '上映：' in dt_text:
                    if not vod_year and dd_text:
                        match = re.search(r'(\d{4})', dd_text)
                        if match:
                            vod_year = match.group(1)
                elif '集数：' in dt_text:
                    vod_total_episodes = dd_text
            
            # 提取剧情介绍
            content_el = doc('.juqing')
            if content_el:
                vod_content = content_el.text().strip()
            
            # 提取播放列表（关键优化）
            playlists = self._extract_playlists(doc, aid)
            
            # 构建播放信息
            if playlists:
                vod_play_from = '$$$'.join([p['title'] for p in playlists])
                vod_play_url = '$$$'.join(['#'.join(p['episodes']) for p in playlists])
            else:
                vod_play_from = '韩剧网'
                vod_play_url = f'正片${url}'
            
            # 确定类型
            type_name = self._get_type_name(url)
            
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
                'vod_lang': vod_lang,
                'vod_content': vod_content,
                'vod_play_from': vod_play_from,
                'vod_play_url': vod_play_url,
                'type_name': type_name
            }
            
            result['list'] = [vod]
            
        except Exception as e:
            print(f"detailContent error: {e}")
            
        return result

    def _extract_info_from_script(self, doc):
        """从script标签提取视频信息"""
        info = {}
        
        try:
            # 查找包含korcms的script标签
            scripts = doc('script')
            for script in scripts.items():
                text = script.text()
                if 'korcms' in text:
                    # 提取JSON数据
                    match = re.search(r'korcms\s*=\s*({[^}]+})', text)
                    if match:
                        data_str = match.group(1)
                        # 修复JSON格式
                        data_str = data_str.replace('"', "'")
                        data_str = data_str.replace("'", '"')
                        
                        try:
                            data = json.loads(data_str)
                            info['year'] = data.get('year', '')
                        except:
                            pass
        except:
            pass
        
        return info

    def _extract_playlists(self, doc, vid):
        """提取播放列表（关键优化）"""
        playlists = []
        
        try:
            # 查找播放列表容器
            play_section = doc('.box:contains("在线云播")')
            if not play_section:
                play_section = doc('.playlist, .play-list')
            
            if play_section:
                # 提取剧集
                episode_items = play_section.find('li')
                episodes = []
                
                for item in episode_items.items():
                    a_tag = item.find('a')
                    if a_tag:
                        episode_name = a_tag.text().strip()
                        onclick = a_tag.attr('onclick') or ''
                        
                        # 从onclick中提取播放参数
                        match = re.search(r"bb_a\('([^']+)','([^']+)'", onclick)
                        if match:
                            play_params = match.group(1)  # 3544_1_1 这样的格式
                            episode_name = match.group(2) or episode_name
                            
                            # 构建播放URL
                            play_url = self._build_play_url(vid, play_params)
                            if play_url:
                                episodes.append(f"{episode_name}${play_url}")
                        else:
                            # 如果没有onclick，尝试使用href
                            href = a_tag.attr('href')
                            if href and href != '#':
                                if not href.startswith('http'):
                                    href = self.baseUrl + ('' if href.startswith('/') else '/') + href
                                episodes.append(f"{episode_name}${href}")
                
                if episodes:
                    playlists.append({
                        'title': '在线播放',
                        'episodes': episodes
                    })
            
            # 如果没有找到，尝试其他选择器
            if not playlists:
                all_episodes = doc('a[onclick*="bb_a"], a[href*="play"]')
                if all_episodes:
                    episodes = []
                    for ep in all_episodes.items():
                        episode_name = ep.text().strip()
                        onclick = ep.attr('onclick') or ''
                        href = ep.attr('href') or ''
                        
                        if onclick:
                            match = re.search(r"bb_a\('([^']+)','([^']+)'", onclick)
                            if match:
                                play_params = match.group(1)
                                episode_name = match.group(2) or episode_name
                                play_url = self._build_play_url(vid, play_params)
                                if play_url:
                                    episodes.append(f"{episode_name}${play_url}")
                        elif href:
                            if not href.startswith('http'):
                                href = self.baseUrl + ('' if href.startswith('/') else '/') + href
                            episodes.append(f"{episode_name}${href}")
                    
                    if episodes:
                        playlists.append({
                            'title': '播放列表',
                            'episodes': episodes
                        })
            
        except Exception as e:
            print(f"_extract_playlists error: {e}")
        
        return playlists

    def _build_play_url(self, vid, play_params):
        """构建播放URL"""
        try:
            # 解析参数格式：3544_1_1
            parts = play_params.split('_')
            if len(parts) >= 3:
                video_id = parts[0]  # 视频ID
                source_id = parts[1]  # 源ID
                episode_id = parts[2]  # 剧集ID
                
                # 构建播放URL（根据网站实际播放地址格式调整）
                # 这里使用通用的播放器地址
                play_url = f"{self.baseUrl}/player/{video_id}/{source_id}/{episode_id}.html"
                return play_url
        except:
            pass
        
        return None

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
        return '韩剧'

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
                    if video:
                        # 检查是否包含搜索关键词
                        if key.lower() in video['vod_name'].lower() or not key:
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
                # 如果id是剧集参数，构建播放URL
                if '_' in id:
                    # 格式：3544_1_1
                    parts = id.split('_')
                    if len(parts) >= 3:
                        video_id = parts[0]
                        play_url = f"{self.baseUrl}/player/{video_id}/{parts[1]}/{parts[2]}.html"
                    else:
                        play_url = f"{self.baseUrl}/detail/{id}.html"
                elif id.isdigit():
                    play_url = f"{self.baseUrl}/player/{id}/1/1.html"
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
