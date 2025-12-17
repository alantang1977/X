import re
import sys
import urllib.parse
from pyquery import PyQuery as pq

sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def getName(self):
        return "韩剧看看"
    
    def init(self, extend):
        pass
        
    def homeContent(self, filter):
        result = {}
        classes = []
        try:
            rsp = self.fetch("https://www.hanjukankan.com")
            if rsp and rsp.text:
                doc = pq(rsp.text)
                
                # Extracting categories
                items = doc('.category-menu a')
                for item in items.items():
                    name = item.text()
                    href = item.attr('href')
                    if name and href:
                        match = re.search(r'/category/(\d+)', href)
                        if match:
                            classes.append({
                                'type_name': name,
                                'type_id': match.group(1)
                            })

                if not classes:
                    items = doc('.dropdown-menu li a')
                    for item in items.items():
                        name = item.text()
                        href = item.attr('href')
                        if name and href:
                            match = re.search(r'/category/(\d+)', href)
                            if match:
                                classes.append({
                                    'type_name': name,
                                    'type_id': match.group(1)
                                })
                
                seen = set()
                unique_classes = []
                for cls in classes:
                    if cls['type_id'] not in seen:
                        seen.add(cls['type_id'])
                        unique_classes.append(cls)
                classes = unique_classes
                
        except Exception as e:
            print(f"homeContent error: {e}")
            
        result['class'] = classes
        return result

    def homeVideoContent(self):
        result = {}
        try:
            videos = []
            url = "https://www.hanjukankan.com/"
            rsp = self.fetch(url)
            if rsp and rsp.text:
                doc = pq(rsp.text)
                items = doc('.video-list li')
                for item in items.items():
                    a = item.find('.video-thumb')
                    href = a.attr('href')
                    title = a.attr('title') or item.find('.title').text()
                    img = a.attr('data-original') or a.attr('style')

                    if img and 'background-image:' in img:
                        match = re.search(r'url\(["\']?(.*?)["\']?\)', img)
                        if match:
                            img = match.group(1)
                    
                    if not title or not href:
                        continue
                    
                    play_count = item.find('.play-count').text() or '播放0次'
                    score = item.find('.score').text() or '0.0 分'
                    
                    videos.append({
                        'vod_id': href,
                        'vod_name': title,
                        'vod_pic': img,
                        'vod_remarks': f"{score} | {play_count}"
                    })
            
            result['list'] = videos
        except Exception as e:
            print(f"homeVideoContent error: {e}")
            
        return result

    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        videos = []
        try:
            url = f"https://www.hanjukankan.com/category/{tid}/page/{pg}"
            rsp = self.fetch(url)
            if rsp and rsp.text:
                doc = pq(rsp.text)
                items = doc('.video-list li')
                for item in items.items():
                    a = item.find('.video-thumb')
                    href = a.attr('href')
                    title = a.attr('title') or item.find('.title').text()
                    img = a.attr('data-original') or a.attr('style')

                    if img and 'background-image:' in img:
                        match = re.search(r'url\(["\']?(.*?)["\']?\)', img)
                        if match:
                            img = match.group(1)
                    
                    if not title or not href:
                        continue
                    
                    play_count = item.find('.play-count').text() or '播放0次'
                    score = item.find('.score').text() or '0.0 分'
                    
                    videos.append({
                        'vod_id': href,
                        'vod_name': title,
                        'vod_pic': img,
                        'vod_remarks': f"{score} | {play_count}"
                    })
        except Exception as e:
            print(f"categoryContent error: {e}")
            
        result['list'] = videos
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        return result

    def detailContent(self, array):
        result = {}
        if not array or not array[0]:
            return result
            
        try:
            aid = array[0]
            play_url = f"https://www.hanjukankan.com/{aid}"
            rsp = self.fetch(play_url)
            if not rsp or not rsp.text:
                return result
                
            html = rsp.text
            doc = pq(html)
            
            vod = {
                'vod_id': aid,
                'vod_name': doc('title').text() or '',
                'vod_pic': '',
                'vod_remarks': '',
                'vod_content': '',
                'vod_play_from': '韩剧看看',
                'vod_play_url': ''
            }
            
            img = doc('.video-thumb').attr('data-original') or doc('.video-thumb').attr('style')
            if img and 'background-image:' in img:
                match = re.search(r'url\(["\']?(.*?)["\']?\)', img)
                if match:
                    vod['vod_pic'] = match.group(1)
            
            description = doc('.video-description').text()
            if description:
                vod['vod_remarks'] = description
                
            content = doc('.content').text() or doc('.detail').text()
            if content:
                vod['vod_content'] = content
            
            vod['vod_play_url'] = f'正片${play_url}'
            
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
                
            url = f"https://www.hanjukankan.com/?s={urllib.parse.quote(key)}&page={page}"
            rsp = self.fetch(url)
            if rsp and rsp.text:
                doc = pq(rsp.text)
                items = doc('.video-list li')
                for item in items.items():
                    a = item.find('.video-thumb')
                    href = a.attr('href')
                    title = a.attr('title') or item.find('.title').text()
                    img = a.attr('data-original') or a.attr('style')

                    if img and 'background-image:' in img:
                        match = re.search(r'url\(["\']?(.*?)["\']?\)', img)
                        if match:
                            img = match.group(1)
                    
                    if not title or not href:
                        continue
                    
                    play_count = item.find('.play-count').text() or '播放0次'
                    score = item.find('.score').text() or '0.0 分'
                    
                    videos.append({
                        'vod_id': href,
                        'vod_name': title,
                        'vod_pic': img,
                        'vod_remarks': f"{score} | {play_count}"
                    })
        except Exception as e:
            print(f"searchContent error: {e}")
            
        result['list'] = videos
        return result

    def playerContent(self, flag, id, vipFlags):
        result = {}
        try:
            if not id:
                return result
            
            if id.startswith('http'):
                play_url = id
            else:
                play_url = f"https://www.hanjukankan.com/{id}"
            
            result["parse"] = 1
            result["playUrl"] = ''
            result["url"] = play_url
            result["header"] = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'https://www.hanjukankan.com/'
            }
            
        except Exception as e:
            print(f"playerContent error: {e}")
            
        return result

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return {}
