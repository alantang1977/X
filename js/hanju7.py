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
        
    def homeContent(self, filter):
        result = {}
        classes = []
        try:
            rsp = self.fetch(self.baseUrl, headers=self.header)
            if rsp and rsp.text:
                doc = pq(rsp.text)
                
                # 从导航菜单提取分类
                menu_items = doc('.menu a')
                for item in menu_items.items():
                    name = item.text()
                    href = item.attr('href')
                    
                    # 过滤无效项
                    if name and href and name not in ["首页", "排行榜", "最近更新", "韩娱", "留言反馈"]:
                        # 提取分类ID
                        if '/list/' in href:
                            match = re.search(r'/list/(\d+)', href)
                            if match:
                                type_id = match.group(1)
                                type_name = name
                                
                                # 映射分类名称
                                if type_id == '1':
                                    type_name = '韩剧'
                                elif type_id == '3':
                                    type_name = '韩国电影'
                                elif type_id == '4':
                                    type_name = '韩国综艺'
                                
                                # 避免重复
                                if not any(c['type_id'] == type_id for c in classes):
                                    classes.append({
                                        'type_name': type_name,
                                        'type_id': type_id
                                    })
                
                # 添加热门分类
                if not any(c['type_id'] == 'hot' for c in classes):
                    classes.append({
                        'type_name': '排行榜',
                        'type_id': 'hot'
                    })
                
                if not any(c['type_id'] == 'new' for c in classes):
                    classes.append({
                        'type_name': '最近更新',
                        'type_id': 'new'
                    })
                
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
                            continue
                            
                        # 图片
                        vod_pic = ''
                        if link_el:
                            data_original = link_el.attr('data-original')
                            if data_original:
                                vod_pic = data_original
                            else:
                                # 从背景图片中提取
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
                        
                        videos.append({
                            'vod_id': vod_id,
                            'vod_name': vod_name,
                            'vod_pic': vod_pic,
                            'vod_remarks': vod_remarks,
                            'vod_actor': vod_actor,
                            'vod_type': vod_type,
                            'vod_href': vod_href
                        })
                
                # 提取排行榜数据
                rank_sections = [
                    ('.box:nth-child(1) .list_txt li', '韩剧榜'),
                    ('.box:nth-child(2) .list_txt li', '韩影榜'),
                    ('.box:nth-child(3) .list_txt li', '韩综榜')
                ]
                
                for selector, rank_type in rank_sections:
                    items = doc(selector)
                    for item in items.items():
                        span_el = item.find('span')
                        a_el = item.find('a')
                        i_el = item.find('i')
                        
                        if a_el:
                            href = a_el.attr('href') or ''
                            vod_name = a_el.text().strip()
                            
                            # 清理排名数字
                            vod_name = re.sub(r'^\d+\s*', '', vod_name)
                            
                            if href and vod_name:
                                # 提取ID
                                vod_id = ''
                                match = re.search(r'/detail/(\d+)\.html', href)
                                if match:
                                    vod_id = match.group(1)
                                
                                if vod_id:
                                    vod_pic = f'//pics.hanju7.com/pics/{vod_id}.jpg'
                                    vod_href = self.baseUrl + ('' if href.startswith('/') else '/') + href
                                    
                                    videos.append({
                                        'vod_id': vod_id,
                                        'vod_name': vod_name,
                                        'vod_pic': vod_pic,
                                        'vod_remarks': span_el.text().strip() if span_el else '',
                                        'vod_actor': '',
                                        'vod_type': f'{rank_type}第{i_el.text().strip() if i_el else ""}名',
                                        'vod_href': vod_href
                                    })
            
            result['list'] = videos
        except Exception as e:
            print(f"homeVideoContent error: {e}")
            
        return result

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
                url = f"{self.baseUrl}/list/{tid}---{pg}---.html"
            
            rsp = self.fetch(url, headers=self.header)
            if rsp and rsp.text:
                doc = pq(rsp.text)
                
                # 提取列表项
                items = doc('.list li, .vodlist li, .stui-vodlist li')
                
                for item in items.items():
                    # 尝试多种选择器获取信息
                    link_el = item.find('a.tu, .tu a, .thumb a')
                    title_el = item.find('p a, .title a, h3 a')
                    tip_el = item.find('.tip, .pic-text, .remarks')
                    actor_el = item.find('p:nth-child(3), .actor, .star')
                    
                    # 标题
                    vod_name = ''
                    if title_el:
                        vod_name = title_el.attr('title') or title_el.text().strip()
                    elif link_el:
                        vod_name = link_el.attr('title') or ''
                    
                    if not vod_name:
                        continue
                    
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
                    
                    videos.append({
                        'vod_id': vod_id,
                        'vod_name': vod_name,
                        'vod_pic': vod_pic,
                        'vod_remarks': vod_remarks,
                        'vod_actor': vod_actor,
                        'vod_href': vod_href
                    })
                
                # 提取分页信息
                page = int(pg) if pg and pg.isdigit() else 1
                pagecount = 1
                
                # 查找分页元素
                pages_el = doc('.pages, .page, .pagination')
                if pages_el:
                    page_links = pages_el.find('a')
                    if page_links:
                        last_page = 0
                        for link in page_links.items():
                            text = link.text().strip()
                            if text.isdigit():
                                num = int(text)
                                if num > last_page:
                                    last_page = num
                        if last_page > 0:
                            pagecount = last_page
                
        except Exception as e:
            print(f"categoryContent error: {e}")
            
        result['list'] = videos
        result['page'] = int(pg) if pg and pg.isdigit() else 1
        result['pagecount'] = pagecount
        result['limit'] = 20
        result['total'] = len(videos)
        return result

    def detailContent(self, array):
        result = {}
        if not array or not array[0]:
            return result
            
        try:
            aid = array[0]
            
            # 构建URL
            if aid.startswith('http'):
                url = aid
            elif aid.isdigit():
                url = f"{self.baseUrl}/detail/{aid}.html"
            else:
                # 假设是包含URL的字符串
                if '/detail/' in aid:
                    url = aid if aid.startswith('http') else f"{self.baseUrl}{'' if aid.startswith('/') else '/'}{aid}"
                else:
                    # 尝试从vod_href中提取
                    if hasattr(self, 'last_video_data') and aid in self.last_video_data:
                        url = self.last_video_data[aid]
                    else:
                        url = f"{self.baseUrl}/detail/{aid}.html"
            
            rsp = self.fetch(url, headers=self.header)
            if not rsp or not rsp.text:
                return result
                
            html = rsp.text
            doc = pq(html)
            
            # 提取基本信息
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
            info_selectors = ['.info p', '.detail-info p', '.info li', '.data p', '.vodinfo p']
            for selector in info_selectors:
                info_items = doc(selector)
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
            content_selectors = ['.content', '.intro', '.detail-content', '.sketch']
            for selector in content_selectors:
                content_el = doc(selector)
                if content_el:
                    vod_content = content_el.text().strip()
                    if vod_content:
                        break
            
            # 提取播放列表
            playlists = []
            playlist_selectors = ['.playlist', '.play-list', '.downlist', '.stui-content__playlist']
            
            for selector in playlist_selectors:
                playlist_el = doc(selector)
                if playlist_el:
                    lines = playlist_el.find('h3, h4, .head')
                    episodes_el = playlist_el.find('ul, .list, .episodes')
                    
                    if lines and episodes_el:
                        for i, line in enumerate(lines.items()):
                            title = line.text().strip()
                            if title:
                                episodes = []
                                links = episodes_el.eq(i).find('a') if episodes_el.length > i else episodes_el.find('a')
                                
                                for link in links.items():
                                    episode_name = link.text().strip()
                                    episode_url = link.attr('href') or ''
                                    
                                    if episode_url and not episode_url.startswith('http'):
                                        episode_url = self.baseUrl + ('' if episode_url.startswith('/') else '/') + episode_url
                                    
                                    if episode_name and episode_url:
                                        episodes.append(f"{episode_name}${episode_url}")
                                
                                if episodes:
                                    playlists.append({
                                        'title': title,
                                        'episodes': episodes
                                    })
            
            # 如果没有找到播放列表，尝试查找播放按钮
            if not playlists:
                play_buttons = doc('a[href*="play"], a:contains("播放"), .playbtn')
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
            vod_play_from = '$$$'.join([p['title'] for p in playlists])
            vod_play_url = '$$$'.join(['#'.join(p['episodes']) for p in playlists])
            
            # 确定类型
            type_name = ''
            if tid := re.search(r'/list/(\d+)', url):
                type_id = tid.group(1)
                if type_id == '1':
                    type_name = '韩剧'
                elif type_id == '3':
                    type_name = '韩国电影'
                elif type_id == '4':
                    type_name = '韩国综艺'
            
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
                'vod_play_from': vod_play_from or '韩剧网',
                'vod_play_url': vod_play_url or f'正片${url}',
                'type_name': type_name
            }
            
            result['list'] = [vod]
            
        except Exception as e:
            print(f"detailContent error: {e}")
            
        return result

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
                selectors = ['.search-list li', '.list li', '.vodlist li', '.stui-vodlist li']
                
                for selector in selectors:
                    items = doc(selector)
                    if items:
                        for item in items.items():
                            link_el = item.find('a.tu, .tu a, .thumb a')
                            title_el = item.find('p a, .title a, h3 a')
                            tip_el = item.find('.tip, .pic-text, .remarks')
                            
                            # 标题
                            vod_name = ''
                            if title_el:
                                vod_name = title_el.attr('title') or title_el.text().strip()
                            elif link_el:
                                vod_name = link_el.attr('title') or ''
                            
                            if not vod_name:
                                continue
                            
                            # 检查是否包含搜索关键词（不区分大小写）
                            if key.lower() not in vod_name.lower():
                                continue
                            
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
                            
                            videos.append({
                                'vod_id': vod_id,
                                'vod_name': vod_name,
                                'vod_pic': vod_pic,
                                'vod_remarks': vod_remarks,
                                'vod_href': vod_href
                            })
                        break
                
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
                # 尝试从详情页提取真实播放地址
                detail_url = f"{self.baseUrl}/detail/{id}.html" if id.isdigit() else id
                rsp = self.fetch(detail_url, headers=self.header)
                if rsp and rsp.text:
                    doc = pq(rsp.text)
                    # 查找播放地址
                    play_link = doc('a[href*="play"], .playbtn, iframe[src*="player"]')
                    if play_link:
                        play_url = play_link.attr('href') or play_link.attr('src') or ''
                        if play_url and not play_url.startswith('http'):
                            play_url = self.baseUrl + ('' if play_url.startswith('/') else '/') + play_url
                    else:
                        play_url = detail_url
                else:
                    play_url = detail_url
            
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
        video_extensions = ['.mp4', '.m3u8', '.flv', '.avi', '.mkv', '.mov', '.wmv', '.mpg']
        return any(ext in url.lower() for ext in video_extensions)

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return {}
