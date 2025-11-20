# -*- coding: utf-8 -*-
# by @你猜
import json
import sys
import requests
import re
# Ensure bs4 is available or handled in your environment
try:
    from bs4 import BeautifulSoup
except ImportError:
    sys.exit("BeautifulSoup4 is required. Please install it via 'pip install beautifulsoup4'")

sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def init(self, extend=""):
        self.host = "https://www.iyf.lv"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 11; SAMSUNG SM-G973U) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/14.2 Chrome/87.0.4280.141 Mobile Safari/537.36',
            'Referer': self.host + '/',
            'Origin': self.host
        }

    def getName(self):
        return "爱壹帆"

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    def homeContent(self, filter):
        # Mapping from JS: class_name='电影&剧集&综艺&动漫&更新&热榜', class_url='1&2&3&4&new&hot'
        classes = [
            {"type_name": "电影", "type_id": "1"},
            {"type_name": "剧集", "type_id": "2"},
            {"type_name": "综艺", "type_id": "3"},
            {"type_name": "动漫", "type_id": "4"},
            {"type_name": "更新", "type_id": "new"},
            {"type_name": "热榜", "type_id": "hot"}
        ]
        # JS says filterable: 0, so we return empty filters
        return {'class': classes, 'filters': {}}

    def homeVideoContent(self):
        # JS Recommendation rule: .tab-list.active;a.module-poster-item.module-item
        try:
            html = self.fetch(self.host, headers=self.headers).text
            soup = BeautifulSoup(html, 'html.parser')
            
            # Locate the active tab list or default recommendation section
            items = soup.select('.tab-list.active a.module-poster-item.module-item')
            if not items:
                items = soup.select('a.module-poster-item.module-item')[:10] # Fallback
            
            vods = []
            for item in items:
                vod = self._parse_vod_item(item)
                if vod:
                    vods.append(vod)
            return {'list': vods}
        except Exception as e:
            return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        # JS Logic: 
        # if new -> /label/new/
        # if hot -> /label/hot/
        # else -> /t/tid/
        # paging -> url + 'page/' + pg + '/'
        
        url = ""
        if tid == 'new':
            url = f"{self.host}/label/new/"
        elif tid == 'hot':
            url = f"{self.host}/label/hot/"
        else:
            url = f"{self.host}/t/{tid}/"
            
        if int(pg) > 1:
            url += f"page/{pg}/"

        try:
            html = self.fetch(url, headers=self.headers).text
            soup = BeautifulSoup(html, 'html.parser')
            items = soup.select('a.module-poster-item.module-item')
            
            vods = []
            for item in items:
                vod = self._parse_vod_item(item)
                if vod:
                    vods.append(vod)
            
            return {
                'list': vods,
                'page': pg,
                'pagecount': 9999,
                'limit': 20,
                'total': 99999
            }
        except Exception as e:
            return {'list': []}

    def detailContent(self, ids):
        # JS Rule 二级 (Detail)
        # title: h1
        # img: .lazyload -> data-original
        # content: .module-info-introduction
        # tabs: .module-tab-item
        # lists: .module-play-list
        
        try:
            url = ids[0]
            if not url.startswith('http'):
                url = self.host + url
                
            html = self.fetch(url, headers=self.headers).text
            soup = BeautifulSoup(html, 'html.parser')
            
            vod = {}
            vod['vod_id'] = ids[0]
            
            # 标题
            title_elem = soup.select_one('h1')
            vod['vod_name'] = title_elem.get_text(strip=True) if title_elem else "未知"
            
            # 图片 - 修复图片获取逻辑
            img_elem = soup.select_one('.module-info-poster img.lazyload')
            if not img_elem:
                img_elem = soup.select_one('.module-item-pic img.lazyload')
            if not img_elem:
                img_elem = soup.select_one('.lazyload')
            
            if img_elem:
                # 优先获取data-original，如果没有则获取src
                vod['vod_pic'] = img_elem.get('data-original') or img_elem.get('src') or ""
                # 确保图片URL完整
                if vod['vod_pic'] and not vod['vod_pic'].startswith('http'):
                    vod['vod_pic'] = self.host + vod['vod_pic']
            else:
                vod['vod_pic'] = ""
            
            # 描述内容
            desc_elem = soup.select_one('.module-info-introduction-content')
            vod['vod_content'] = desc_elem.get_text(strip=True) if desc_elem else ""
            
            # 提取详细信息
            info_items = {}
            info_elems = soup.select('.module-info-item')
            for elem in info_elems:
                title_elem = elem.select_one('.module-info-item-title')
                content_elem = elem.select_one('.module-info-item-content')
                if title_elem and content_elem:
                    title = title_elem.get_text(strip=True).replace('：', '').replace(':', '')
                    info_items[title] = content_elem.get_text(strip=True)
            
            # 构建详细信息字符串
            vod['vod_actor'] = info_items.get('主演', '')
            vod['vod_director'] = info_items.get('导演', '')
            vod['vod_area'] = info_items.get('地区', '')
            vod['vod_year'] = info_items.get('年份', '') or info_items.get('上映', '')
            vod['vod_remarks'] = info_items.get('更新', '') or info_items.get('集数', '')
            
            # Play Lists
            tabs = [t.get_text(strip=True) for t in soup.select('.module-tab-item')]
            play_lists = soup.select('.module-play-list')
            
            vod_play_from = []
            vod_play_url = []
            
            for i, play_list in enumerate(play_lists):
                # If tabs count matches lists, use tab name, else default
                from_name = tabs[i] if i < len(tabs) else f"线路{i+1}"
                vod_play_from.append(from_name)
                
                links = []
                for a in play_list.select('a'):
                    name = a.get_text(strip=True)
                    href = a.get('href')
                    if href:
                        if not href.startswith('http'):
                            href = self.host + href
                        links.append(f"{name}${href}")
                
                if links:
                    vod_play_url.append("#".join(links))
            
            if vod_play_from and vod_play_url:
                vod['vod_play_from'] = "$$$".join(vod_play_from)
                vod['vod_play_url'] = "$$$".join(vod_play_url)
            
            return {'list': [vod]}
        except Exception as e:
            return {'list': []}

    def searchContent(self, key, quick, pg="1"):
        # JS SearchUrl: /s/**-------------/
        url = f"{self.host}/s/{key}-------------.html"
        if int(pg) > 1:
            url += f"page/{pg}/"

        try:
            html = self.fetch(url, headers=self.headers).text
            soup = BeautifulSoup(html, 'html.parser')
            
            # 多种搜索结果选择器
            items = soup.select('.module-search-item, .module-poster-item, .module-item')
            if not items:
                items = soup.select('a[href*="/iyftv/"]')
            
            vods = []
            for item in items:
                vod = self._parse_vod_item(item, is_search=True)
                if vod and vod.get('vod_id'):
                    vods.append(vod)
            
            return {'list': vods, 'page': pg}
        except Exception as e:
            return {'list': []}

    def playerContent(self, flag, id, vipFlags):
        # JS Lazy Rule:
        # 1. Match .m3u8
        # 2. Match .mp4
        
        url = id
        if not url.startswith('http'):
            url = self.host + url
            
        try:
            html = self.fetch(url, headers=self.headers).text
            
            # 首先尝试从播放器配置中提取
            player_match = re.search(r'var player_aaaa=({[^;]+});', html)
            if player_match:
                try:
                    player_data = json.loads(player_match.group(1))
                    if player_data.get('url'):
                        return {'parse': 0, 'url': player_data['url'], 'header': self.headers}
                except:
                    pass
            
            # 正则匹配视频地址
            m3u8_match = re.search(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', html)
            if m3u8_match:
                return {'parse': 0, 'url': m3u8_match.group(1), 'header': self.headers}
            
            mp4_match = re.search(r'(https?://[^\s"\'<>]+\.(mp4|m4a)[^\s"\'<>]*)', html)
            if mp4_match:
                return {'parse': 0, 'url': mp4_match.group(1), 'header': self.headers}
                
            # Fallback: Return original url to let the player sniff it
            return {'parse': 1, 'url': url, 'header': self.headers}
            
        except Exception as e:
            return {'parse': 1, 'url': url, 'header': self.headers}

    def _parse_vod_item(self, item, is_search=False):
        # Helper to extract vod data from a list item (<a> or div)
        try:
            link = item if item.name == 'a' else item.select_one('a')
            if not link:
                return {}
                
            url = link.get('href')
            if not url:
                return {}
            
            # 处理图片 - 修复图片获取逻辑
            pic = ""
            # 多种图片选择器
            img_selectors = [
                '.lazyload',
                '.module-item-pic img',
                '.module-item-cover img',
                'img'
            ]
            
            for selector in img_selectors:
                img_elem = item.select_one(selector)
                if img_elem:
                    # 优先获取data-original，如果没有则获取src
                    pic = img_elem.get('data-original') or img_elem.get('src') or ""
                    if pic:
                        break
            
            # 确保图片URL完整
            if pic and not pic.startswith('http'):
                pic = self.host + pic
            
            # 标题
            title = ""
            if is_search:
                title_selectors = ['.module-card-item-title', '.module-poster-item-title', '.module-item-title']
                for selector in title_selectors:
                    title_elem = item.select_one(selector)
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        break
            else:
                title = link.get('title') or ""
                if not title:
                    title_elem = item.select_one('.module-poster-item-title')
                    title = title_elem.get_text(strip=True) if title_elem else ""
            
            # 备注/更新信息
            remarks = ""
            remarks_selectors = ['.module-item-note', '.module-card-item-note', '.pic-text']
            for selector in remarks_selectors:
                remarks_elem = item.select_one(selector)
                if remarks_elem:
                    remarks = remarks_elem.get_text(strip=True)
                    break

            return {
                'vod_id': url,
                'vod_name': title,
                'vod_pic': pic,
                'vod_remarks': remarks
            }
        except Exception as e:
            return {}

    def localProxy(self, param):
        pass