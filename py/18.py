# coding=utf-8
#!/usr/bin/python
import sys
sys.path.append('..')
from base.spider import Spider
import json
import urllib.parse
import re

class Spider(Spider):
    
    def getName(self):
        return "快递🔞"
    
    def init(self, extend=""):
        self.host = "https://www.xjjkdfw.sbs"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 11; M2007J3SC Build/RKQ1.200826.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/77.0.3865.120 MQQBrowser/6.2 TBS/045713 Mobile Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q.0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Referer': self.host
        }
        self.log(f"快递🔞爬虫初始化完成，主站: {self.host}")

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return True

    def homeContent(self, filter):
        """获取首页内容和分类"""
        result = {}
        classes = self._getCategories()
        result['class'] = classes
        try:
            rsp = self.fetch(self.host, headers=self.headers)
            html = rsp.text
            videos = self._getVideos(html)
            result['list'] = videos
        except Exception as e:
            self.log(f"首页获取出错: {str(e)}")
            result['list'] = []
        return result

    def homeVideoContent(self):
        """首页视频内容（可留空）"""
        return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        """分类内容"""
        try:
            pg_int = int(pg)
            if pg_int == 1:
                url = f"{self.host}/vodtype/{tid}.html"
            else:
                url = f"{self.host}/vodtype/{tid}/page/{pg_int}.html"
            
            self.log(f"访问分类URL: {url}")
            rsp = self.fetch(url, headers=self.headers)
            html = rsp.text
            
            videos = self._getVideos(html)
            
            pagecount = 999
            page_links = re.findall(r'<a href="/vodtype/{}/page/(\d+)\.html"'.format(tid), html)
            if page_links:
                pagecount = max([int(p) for p in page_links if p.isdigit()])
            
            if not videos:
                self.log(f"警告: 分类ID {tid}, 页码 {pg} 未找到任何视频。URL: {url}")

            return {
                'list': videos,
                'page': pg_int,
                'pagecount': pagecount,
                'limit': 20,
                'total': 999999
            }
        except Exception as e:
            self.log(f"分类内容获取出错 (tid={tid}, pg={pg}): {str(e)}")
            return {'list': []}

    def searchContent(self, key, quick, pg="1"):
        """搜索功能（使用官方 AJAX 接口）"""
        try:
            search_url = f"{self.host}/index.php/ajax/suggest?mid=1&wd={urllib.parse.quote(key)}"
            self.log(f"搜索URL: {search_url}")
            
            rsp = self.fetch(search_url, headers=self.headers)
            data = json.loads(rsp.text)
            
            videos = []
            for item in data:
                video = {
                    'vod_id': item.get('id', ''),
                    'vod_name': item.get('name', ''),
                    'vod_pic': item.get('pic', ''),
                    'vod_remarks': item.get('actor', '')
                }
                videos.append(video)
            return {'list': videos}
        except Exception as e:
            self.log(f"搜索出错: {str(e)}")
            return {'list': []}

    def detailContent(self, ids):
        """详情页面"""
        try:
            vid = ids[0]
            detail_url = f"{self.host}/voddetail/{vid}.html"
            self.log(f"详情URL: {detail_url}")
            rsp = self.fetch(detail_url, headers=self.headers)
            html = rsp.text
            video_info = self._getDetail(html, vid)
            return {'list': [video_info]} if video_info else {'list': []}
        except Exception as e:
            self.log(f"详情获取出错 (vid: {ids[0]}): {str(e)}")
            return {'list': []}

    def playerContent(self, flag, id, vipFlags):
        """播放链接解析"""
        try:
            play_page_url = f"{self.host}/vodplay/{id}.html"
            self.log(f"播放页面URL: {play_page_url}")
            
            rsp = self.fetch(play_page_url, headers=self.headers)
            if rsp.status_code != 200:
                self.log(f"播放页请求失败，状态码: {rsp.status_code}")
                return {'parse': 1, 'playUrl': '', 'url': play_page_url}
            
            html = rsp.text
            
            # 1. 优先解析 JS 中的 player_aaaa 变量
            player_pattern = r'var player_aaaa=({.*?});'
            player_match = re.search(player_pattern, html, re.DOTALL)
            
            if player_match:
                try:
                    player_data = json.loads(player_match.group(1).replace("'", '"'))
                    video_url = player_data.get('url', '').strip()
                    
                    if video_url:
                        if video_url.startswith('//'):
                            video_url = 'https:' + video_url
                        elif video_url.startswith('/') and not video_url.startswith('http'):
                            video_url = self.host.rstrip('/') + video_url
                        
                        self.log(f"✅ 找到视频直链: {video_url}")
                        return {
                            'parse': 0,
                            'playUrl': '',
                            'url': video_url,
                            'header': json.dumps(self.headers)
                        }
                except Exception as e:
                    self.log(f"解析player_aaaa失败: {str(e)}")
            
            # 2. 解析 iframe 播放器
            iframe_match = re.search(r'<iframe[^>]*src=["\']([^"\']+)["\']', html)
            if iframe_match:
                iframe_url = iframe_match.group(1).strip()
                if iframe_url.startswith('//'):
                    iframe_url = 'https:' + iframe_url
                elif iframe_url.startswith('/') and not iframe_url.startswith('http'):
                    iframe_url = self.host.rstrip('/') + iframe_url
                
                self.log(f"📹 找到iframe播放源: {iframe_url}")
                return {'parse': 1, 'playUrl': '', 'url': iframe_url}
            
            # 3. 最后手段：返回播放页本身，让播放器自己嗅探
            self.log(f"⚠️ 未找到播放源，返回原始播放页")
            return {'parse': 1, 'playUrl': '', 'url': play_page_url}
            
        except Exception as e:
            self.log(f"播放链接获取出错 (id: {id}): {str(e)}")
            return {'parse': 1, 'playUrl': '', 'url': f"{self.host}/vodplay/{id}.html"}

    # ========== 辅助方法 ==========
    
    def _getCategories(self):
        """从首页提取分类"""
        try:
            rsp = self.fetch(self.host, headers=self.headers)
            html = rsp.text
            categories = []
            pattern = r'<a href="/vodtype/(\d+)\.html"[^>]*>([^<]+)</a>'
            matches = re.findall(pattern, html)
            
            seen = set()
            for tid, name in matches:
                if name.strip() and tid not in seen:
                    seen.add(tid)
                    categories.append({'type_id': tid, 'type_name': name.strip()})
            return categories
        except Exception as e:
            self.log(f"获取分类出错: {str(e)}")
            return []

    def _getVideos(self, html):
        """从HTML中提取视频列表"""
        videos = []
        
        # 匹配结构：
        # <a class="thumbnail" href="/vodplay/123-1-1.html">
        #   <img data-original="https://xxx.jpg" ...>
        # </a>
        # <a href="/voddetail/123.html">标题</a>
        # <p class="vodtitle">分类 - <span class="title">日期</span></p>
        
        pattern = r'<a\s+class="thumbnail"[^>]*href="(/vodplay/(\d+)-\d+-\d+\.html)"[^>]*>.*?data-original="([^"]+)".*?</a>.*?<a\s+href="/voddetail/\d+\.html"[^>]*>([^<]+)</a>.*?<p\s+class="vodtitle">([^<]+?)\s*-\s*<span\s+class="title">([^<]+)</span>'
        
        matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
        
        for full_play_link, vid, pic, title, category, date in matches:
            if not pic.startswith('http'):
                pic = self.host + pic if pic.startswith('/') else 'https:' + pic if pic.startswith('//') else pic
            
            video = {
                'vod_id': vid,
                'vod_name': title.strip(),
                'vod_pic': pic,
                'vod_remarks': f"{category.strip()} | {date.strip()}"
            }
            videos.append(video)
        
        return videos

    def _getDetail(self, html, vid):
        """获取详情信息"""
        try:
            # 标题
            title = self.regStr(r'<h2\s+class="title">([^<]+)</h2>', html)
            
            # 封面
            pic = self.regStr(r'data-original="([^"]+)"', html)
            if pic and not pic.startswith('http'):
                pic = self.host + pic if pic.startswith('/') else 'https:' + pic if pic.startswith('//') else pic
            
            # 简介
            desc = self.regStr(r'<div\s+class="content">([\s\S]*?)</div>', html)
            if desc:
                desc = desc.strip().replace('<br>', '\n').replace('</br>', '')
            else:
                desc = title
            
            # 演员 (从标题中提取)
            actor = ""
            actor_match = re.search(r'([\u4e00-\u9fa5]{2,4})[-\s]+[A-Z0-9-]+', title)
            if actor_match:
                actor = actor_match.group(1).strip()

            # 导演信息，网站未提供，留空
            director = ""

            # 播放源
            play_from = []
            play_url_list = []
            
            playlist_matches = re.findall(r'<ul\s+class="playlist">([\s\S]*?)</ul>', html)
            if playlist_matches:
                for i, pl_html in enumerate(playlist_matches):
                    source_name = f"线路{i+1}"
                    episodes = []
                    ep_matches = re.findall(r'<a\s+href="(/vodplay/(\d+-\d+-\d+)\.html)"[^>]*>([^<]+)</a>', pl_html)
                    for full_url, ep_id, ep_name in ep_matches:
                        episodes.append(f"{ep_name.strip()}${ep_id}")
                    if episodes:
                        play_from.append(source_name)
                        play_url_list.append('#'.join(episodes))
            
            # 如果没有播放列表，则创建一个默认的
            if not play_url_list:
                play_from = ["默认源"]
                play_url_list = [f"第1集${vid}-1-1"]

            # 其他字段
            type_name = self.regStr(r'<a\s+href="/vodtype/\d+\.html"[^>]*>([^<]+)</a>', html)
            
            return {
                'vod_id': vid,
                'vod_name': title,
                'vod_pic': pic,
                'type_name': type_name.strip() if type_name else "未知",
                'vod_year': "2025",
                'vod_area': "网络",
                'vod_remarks': "高清",
                'vod_actor': actor,
                'vod_director': director,
                'vod_content': desc,
                'vod_play_from': '$$$'.join(play_from),
                'vod_play_url': '$$$'.join(play_url_list)
            }
        except Exception as e:
            self.log(f"获取详情失败 (vid={vid}): {str(e)}")
            return {
                'vod_id': vid,
                'vod_name': "加载失败",
                'vod_pic': "",
                'type_name': "",
                'vod_year': "",
                'vod_area': "",
                'vod_remarks': "",
                'vod_actor': "",
                'vod_director': "",
                'vod_content': "详情加载失败",
                'vod_play_from': "默认源",
                'vod_play_url': f"第1集${vid}-1-1"
            }

    def regStr(self, pattern, string):
        """正则提取第一个匹配组"""
        try:
            match = re.search(pattern, string)
            return match.group(1) if match else ""
        except:
            return ""