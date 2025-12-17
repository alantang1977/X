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
        self.siteUrl = "https://www.hanjukankan.com"
        pass
        
    def homeContent(self, filter):
        result = {}
        classes = []
        try:
            rsp = self.fetch(self.siteUrl)
            if rsp and rsp.text:
                doc = pq(rsp.text)
                
                # Handling categories: Try standard navigation selectors
                # Scenario A: Top Menu
                items = doc('.stui-header__menu li a')
                
                # Scenario B: Fallback to common nav if A fails
                if not items:
                     items = doc('.nav-menu li a')

                for item in items.items():
                    name = item.text()
                    href = item.attr('href')
                    if name and href and name != "首页":
                        # Match standard category pattern: /vodtype/id.html or similar
                        # Trying to extract ID from patterns like /vodtype/20.html or /list/20.html
                        match = re.search(r'/vodtype/(\d+)\.html', href)
                        if not match:
                             match = re.search(r'/list/(\d+)\.html', href)
                             
                        if match:
                            classes.append({
                                'type_name': name,
                                'type_id': match.group(1)
                            })
                
                # Remove duplicates
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
        if classes:
            result['filters'] = {}
        return result

    def homeVideoContent(self):
        result = {}
        try:
            videos = []
            rsp = self.fetch(self.siteUrl)
            if rsp and rsp.text:
                doc = pq(rsp.text)
                # Select standard video list items (common in STUI templates)
                items = doc('.stui-vodlist li, .stui-vodlist__box')
                
                for item in items.items():
                    a = item.find('a.stui-vodlist__thumb')
                    if not a:
                         a = item.find('a.module-item-cover') # Fallback selector
                         
                    href = a.attr('href')
                    title = a.attr('title') 
                    
                    # Image handling
                    img = a.attr('data-original') or a.attr('style')
                    if img and 'background-image:' in img:
                        match = re.search(r'url\(["\']?(.*?)["\']?\)', img)
                        if match:
                            img = match.group(1)
                    if img and not img.startswith('http'):
                        img = urllib.parse.urljoin(self.siteUrl, img)
                    
                    if not title or not href:
                        continue
                    
                    # Remarks (Score/Status)
                    play_count = item.find('.pic-text').text() or item.find('.text-right').text() 
                    if not play_count:
                         play_count = item.find('.module-item-text').text()
                         
                    score = item.find('.score').text()
                    remarks = score if score else play_count

                    videos.append({
                        'vod_id': href,
                        'vod_name': title,
                        'vod_pic': img,
                        'vod_remarks': remarks or ''
                    })
            
            result['list'] = videos
        except Exception as e:
            print(f"homeVideoContent error: {e}")
            
        return result

    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        videos = []
        try:
            # Construct Category URL: https://www.hanjukankan.com/vodtype/{tid}-{pg}.html
            url = f"{self.siteUrl}/vodtype/{tid}-{pg}.html"
            
            rsp = self.fetch(url)
            if rsp and rsp.text:
                doc = pq(rsp.text)
                items = doc('.stui-vodlist li, .module-item')
                for item in items.items():
                    a = item.find('a.stui-vodlist__thumb')
                    if not a:
                        a = item.find('a.module-item-cover')

                    href = a.attr('href')
                    title = a.attr('title')
                    
                    img = a.attr('data-original') or a.attr('style') or a.attr('src')
                    if img and 'background-image:' in img:
                        match = re.search(r'url\(["\']?(.*?)["\']?\)', img)
                        if match:
                            img = match.group(1)
                    if img and not img.startswith('http'):
                        img = urllib.parse.urljoin(self.siteUrl, img)
                    
                    if not title or not href:
                        continue
                    
                    play_count = item.find('.pic-text').text() or item.find('.text-right').text()
                    if not play_count:
                        play_count = item.find('.module-item-text').text()

                    videos.append({
                        'vod_id': href,
                        'vod_name': title,
                        'vod_pic': img,
                        'vod_remarks': play_count or ''
                    })
        except Exception as e:
            print(f"categoryContent error: {e}")
            
        result['list'] = videos
        result['page'] = int(pg)
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
            if aid.startswith('http'):
                url = aid
            else:
                url = urllib.parse.urljoin(self.siteUrl, aid)
                
            rsp = self.fetch(url)
            if not rsp or not rsp.text:
                return result
                
            html = rsp.text
            doc = pq(html)
            
            vod = {
                'vod_id': aid,
                'vod_name': doc('h1.title').text() or doc('title').text(),
                'vod_pic': '',
                'vod_remarks': '',
                'vod_content': '',
                'vod_play_from': '',
                'vod_play_url': ''
            }
            
            # Extract Image
            img = doc('.stui-vodlist__thumb').attr('data-original') or doc('.stui-vodlist__thumb').attr('src')
            if not img:
                 img = doc('.module-item-cover .module-item-pic img').attr('data-src')

            if img and not img.startswith('http'):
                img = urllib.parse.urljoin(self.siteUrl, img)
            vod['vod_pic'] = img
            
            # Extract Description
            desc = doc('.stui-content__detail').text() or doc('.vod_content').text() or doc('meta[name="description"]').attr('content')
            vod['vod_content'] = desc
            
            # Extract Playlist
            # Finds tabs (Sources)
            playFrom = []
            playList = []
            
            # Selector for Tabs
            tabs = doc('.stui-pannel__head h3, .module-tab-item')
            for tab in tabs.items():
                name = tab.text()
                if name:
                    playFrom.append(name.replace("线路", "Source").strip())
            
            # If no tabs found, default to 'Generic'
            if not playFrom:
                playFrom = ['韩剧看看']

            # Selector for Lists
            # Supports standard stui-content__playlist and module-play-list
            lists = doc('.stui-content__playlist, .module-play-list')
            
            for i, ul in enumerate(lists.items()):
                urls = []
                links = ul.find('a')
                for link in links.items():
                    name = link.text()
                    href = link.attr('href')
                    if name and href:
                        urls.append(f"{name}${href}")
                playList.append("#".join(urls))
            
            vod['vod_play_from'] = "$$$".join(playFrom)
            vod['vod_play_url'] = "$$$".join(playList)
            
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
            
            # Search URL format: /vodsearch/-------------.html?wd=key
            # Encoding the key
            # some sites use /index.php/ajax/suggest?mid=1&wd=... but let's use the HTML search page
            search_url = f"{self.siteUrl}/vodsearch/-------------.html?wd={urllib.parse.quote(key)}"
            
            rsp = self.fetch(search_url)
            if rsp and rsp.text:
                doc = pq(rsp.text)
                items = doc('.stui-vodlist__media li, .module-search-item')
                
                for item in items.items():
                    a = item.find('a.stui-vodlist__thumb') or item.find('a.video-cover')
                    if not a: continue

                    href = a.attr('href')
                    title = a.attr('title') or item.find('.title a').text()
                    
                    img = a.attr('data-original') or a.attr('style')
                    if img and 'background-image:' in img:
                        match = re.search(r'url\(["\']?(.*?)["\']?\)', img)
                        if match:
                            img = match.group(1)
                    if img and not img.startswith('http'):
                        img = urllib.parse.urljoin(self.siteUrl, img)

                    if not title or not href:
                        continue
                    
                    remarks = item.find('.pic-text').text() or item.find('.text-right').text()
                    
                    videos.append({
                        'vod_id': href,
                        'vod_name': title,
                        'vod_pic': img,
                        'vod_remarks': remarks or ''
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
                url = id
            else:
                url = urllib.parse.urljoin(self.siteUrl, id)
            
            # Use webview parsing (sniffing)
            result["parse"] = 1 
            result["playUrl"] = ''
            result["url"] = url
            result["header"] = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': self.siteUrl
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
