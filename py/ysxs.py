# coding: utf-8

import sys
import re
import json
from urllib.parse import quote, unquote
from lxml import etree

sys.path.append('..')
from base.spider import Spider


class Spider(Spider):
    def getName(self):
        return "有声小说"

    def init(self, extend):
        print("============有声小说============")

    def homeContent(self, filter):
        # 只保留有声小说分类
        cateManual = {
            "有声小说": "audio"
        }
        classes = [{'type_name': k, 'type_id': v} for k, v in cateManual.items()]
        return {'class': classes}

    def homeVideoContent(self):
        return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        # 使用 per-page=100 提高每页数量
        url = f'https://www.book18.me/audio/index?page={pg}&per-page=100'

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://www.book18.me/",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            }
            rsp = self.fetch(url, headers=headers)
            text = rsp.text

            videos = []

            # 方法1: 使用正则提取列表项数据属性（更准确）
            list_pattern = r'<li class="list-group-item"[^>]*data-id="(\d+)"[^>]*data-title="([^"]*)"[^>]*data-author="([^"]*)"'
            list_matches = re.findall(list_pattern, text)
            
            for data_id, data_title, data_author in list_matches:
                # 在同一个列表项中查找播放量
                play_pattern = rf'<li[^>]*data-id="{data_id}"[^>]*>.*?<i class="fa fa-headphones"></i>\s*(\d+(?:\.\d+)?)\s*万'
                play_match = re.search(play_pattern, text, re.DOTALL)
                play_count = play_match.group(1) if play_match else "0"
                
                videos.append({
                    "vod_id": data_id,
                    "vod_name": data_title,
                    "vod_pic": "",
                    "vod_remarks": f"声优: {data_author} 人气: {play_count}万"
                })

            # 方法2: 如果方法1没找到，使用原来的正则提取
            if not videos:
                # 新的正则模式匹配标题、声优和播放量
                pattern = r'<a href="/audio/\d+"[^>]*>([^<]+)</a>.*?声优:\s*<a[^>]*>([^<]+)</a>.*?<i class="fa fa-headphones"></i>\s*(\d+(?:\.\d+)?)\s*万'
                matches = re.findall(pattern, text, re.DOTALL)

                for title, actor, play_count in matches:
                    title = title.strip()
                    actor = actor.strip() if actor else "未知"
                    play_count = play_count.strip()

                    # 提取 aid（从链接中）
                    href_match = re.search(rf'href="(/audio/(\d+))"[^>]*>{re.escape(title)}', text)
                    aid = href_match.group(2) if href_match else str(abs(hash(title)) % 100000)

                    videos.append({
                        "vod_id": aid,
                        "vod_name": title,
                        "vod_pic": "",
                        "vod_remarks": f"声优: {actor} 人气: {play_count}万"
                    })

            result['list'] = videos
            result['page'] = int(pg)
            result['pagecount'] = 9999
            result['limit'] = 100
            result['total'] = 999999

        except Exception as e:
            print(f"【有声小说】分类内容获取失败: {e}")
            result = {
                'list': [],
                'page': int(pg),
                'pagecount': 1,
                'limit': 100,
                'total': 0
            }

        return result

    def detailContent(self, array):
        aid = array[0]
        url = f'https://www.book18.me/audio/{aid}'

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://www.book18.me/"
            }
            rsp = self.fetch(url, headers=headers)
            html = rsp.text

            vod = {
                "vod_id": aid,
                "vod_name": "未知标题",
                "vod_pic": "",
                "type_name": "有声小说",
                "vod_year": "",
                "vod_area": "",
                "vod_remarks": "",
                "vod_actor": "",
                "vod_director": "",
                "vod_content": "",
                "vod_play_from": "书生玩剣ⁱ·*₁＇",
                "vod_play_url": ""
            }

            # 方法1: 从页面中的标题元素提取
            title_match = re.search(r'<h[1-6][^>]*>(.*?)</h[1-6]>', html)
            if title_match:
                vod['vod_name'] = self.clean_html(title_match.group(1))
            
            # 方法2: 从页面标题中提取（去除网站后缀）
            if vod['vod_name'] == "未知标题":
                title_match = re.search(r'<title>(.*?)</title>', html)
                if title_match:
                    raw_title = title_match.group(1)
                    # 去除各种可能的网站后缀
                    clean_title = re.sub(r'\s*-?\s*(有声小说|色情小说|成人小说|情色小说|book18\.me).*$', '', raw_title).strip()
                    vod['vod_name'] = clean_title if clean_title else raw_title

            # 方法3: 从面包屑导航或列表项中提取
            if vod['vod_name'] == "未知标题":
                # 尝试从列表项的数据属性中提取
                data_title_match = re.search(r'data-title="([^"]+)"', html)
                if data_title_match:
                    vod['vod_name'] = data_title_match.group(1)

            # 方法4: 最后兜底，使用 aid 作为标题
            if vod['vod_name'] == "未知标题":
                vod['vod_name'] = f"有声小说 {aid}"

            # 提取声优信息
            actors = []
            # 从页面中提取声优信息
            actor_matches = re.findall(r'声优[：:\s]*([^<>\n]+)', html)
            if actor_matches:
                actors.extend(actor_matches)
            
            # 从列表项的数据属性中提取
            data_author_match = re.search(r'data-author="([^"]+)"', html)
            if data_author_match:
                actors.append(data_author_match.group(1))
                
            vod['vod_actor'] = ', '.join(set(actors)) if actors else "未知声优"

            # 提取播放量
            play_match = re.search(r'(\d+(?:\.\d+)?)\s*万\s*播放', html) or \
                        re.search(r'播放[：:\s]*(\d+(?:\.\d+)?)\s*万', html) or \
                        re.search(r'<i class="fa fa-headphones"></i>\s*(\d+(?:\.\d+)?)\s*万', html)
            if play_match:
                vod['vod_remarks'] = f"人气: {play_match.group(1)}万"
            else:
                vod['vod_remarks'] = "有声小说"

            # 提取描述内容
            desc_match = re.search(r'<meta name="description" content="([^"]*)"', html)
            if desc_match:
                vod['vod_content'] = desc_match.group(1)

            # 播放列表提取逻辑
            vod['vod_play_url'] = self.extractPlaylist(html, url)

            return {'list': [vod]}

        except Exception as e:
            print(f"【有声小说】详情页获取失败: {e}")
            return {
                'list': [{
                    "vod_id": aid,
                    "vod_name": f"小说 {aid}",
                    "vod_pic": "",
                    "type_name": "有声小说",
                    "vod_year": "",
                    "vod_area": "",
                    "vod_remarks": "加载失败",
                    "vod_actor": "",
                    "vod_director": "",
                    "vod_content": "",
                    "vod_play_from": "有声小说",
                    "vod_play_url": f"第1集${url}"
                }]
            }

    def extractPlaylist(self, html, fallback_url):
        """提取播放列表的核心逻辑"""
        play_list = []
        
        # 方法1: 查找playlist数据 (第一种正则模式)
        pattern1 = r"playlist\s*=\s*ref\s*\(\s*JSON\.parse\s*\(\s*'(\[.*?\])\s*'\)\s*\)"
        match1 = re.search(pattern1, html)
        if match1:
            try:
                json_str = match1.group(1)
                json_str = json_str.replace('\\"', '"').replace("\\'", "'")
                playlist = json.loads(json_str)
                for item in playlist:
                    if isinstance(item, dict) and 'title' in item and 'src' in item:
                        play_list.append(f"{item['title']}${item['src']}")
            except Exception as e:
                print(f"解析播放列表失败（模式1）: {e}")
        
        # 方法2: 如果没找到播放列表，尝试第二种正则模式
        if not play_list:
            pattern2 = r'playlist\s*=\s*ref\s*\$\$\s*JSON\.parse\s*\$\$\s*[\'"](\$.*?\$)[\'"]\s*\$\$\s*\$\$'
            match2 = re.search(pattern2, html, re.DOTALL)
            if match2:
                try:
                    json_str = match2.group(1)
                    json_str = json_str.replace('\\"', '"').replace("\\'", "'").replace('\\\\', '\\')
                    playlist = json.loads(json_str)
                    for item in playlist:
                        if isinstance(item, dict) and 'title' in item and 'src' in item:
                            play_list.append(f"{item['title']}${item['src']}")
                except Exception as e:
                    print(f"解析播放列表失败（模式2）: {e}")
        
        # 方法3: 尝试直接查找webm文件
        if not play_list:
            webm_matches = re.findall(r'https://www\.book18\.me/images/webm/[\d/]+\.webm\?t=\d+', html)
            for i, webm_url in enumerate(webm_matches):
                play_list.append(f"第{i+1}集${webm_url}")
        
        # 最终兜底方案
        if not play_list:
            play_list.append(f"第1集${fallback_url}")
        
        return '#'.join(play_list)

    def searchContent(self, key, quick, page='1'):
        result = {'list': []}
        try:
            # 构造搜索 URL
            search_url = f'https://www.book18.me/audio/index?q={quote(key)}'
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://www.book18.me/"
            }
            rsp = self.fetch(search_url, headers=headers)
            text = rsp.text

            videos = []

            # 方法1: 使用正则提取列表项数据属性（更准确）
            list_pattern = r'<li class="list-group-item"[^>]*data-id="(\d+)"[^>]*data-title="([^"]*)"[^>]*data-author="([^"]*)"'
            list_matches = re.findall(list_pattern, text)
            
            for data_id, data_title, data_author in list_matches:
                # 在同一个列表项中查找播放量
                play_pattern = rf'<li[^>]*data-id="{data_id}"[^>]*>.*?<i class="fa fa-headphones"></i>\s*(\d+(?:\.\d+)?)\s*万'
                play_match = re.search(play_pattern, text, re.DOTALL)
                play_count = play_match.group(1) if play_match else "0"
                
                videos.append({
                    "vod_id": data_id,
                    "vod_name": data_title,
                    "vod_pic": "",
                    "vod_remarks": f"声优: {data_author} 人气: {play_count}万"
                })

            # 方法2: 如果方法1没找到，使用原来的正则提取
            if not videos:
                # 新的正则模式匹配标题、声优和播放量
                pattern = r'<a href="/audio/\d+"[^>]*>([^<]+)</a>.*?声优:\s*<a[^>]*>([^<]+)</a>.*?<i class="fa fa-headphones"></i>\s*(\d+(?:\.\d+)?)\s*万'
                matches = re.findall(pattern, text, re.DOTALL)

                for title, actor, play_count in matches:
                    title = title.strip()
                    actor = actor.strip() if actor else "未知"
                    play_count = play_count.strip()

                    # 提取 aid
                    href_match = re.search(rf'href="(/audio/(\d+))"[^>]*>{re.escape(title)}', text)
                    aid = href_match.group(2) if href_match else str(abs(hash(title)) % 100000)

                    videos.append({
                        "vod_id": aid,
                        "vod_name": title,
                        "vod_pic": "",
                        "vod_remarks": f"声优: {actor} 人气: {play_count}万"
                    })

            result['list'] = videos

        except Exception as e:
            print(f"【有声小说】搜索失败: {e}")

        return result

    def playerContent(self, flag, id, vipFlags):
        # 直接播放 .webm 音频
        if id.startswith('http') and ('.webm' in id or '.m3u8' in id):
            return {
                "parse": 0,
                "playUrl": "",
                "url": id,
                "header": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": "https://www.book18.me/"
                }
            }
        else:
            # 可能是页面链接，交给 detail 处理
            return {
                "parse": 0,
                "playUrl": "",
                "url": id,
                "header": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": "https://www.book18.me/"
                }
            }

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return {}

    def clean_html(self, text):
        """清除HTML标签"""
        if not text:
            return text
        return re.sub(r'<[^>]+>', '', text).strip()
