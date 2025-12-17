import re
import sys
import urllib.parse
import json
from pyquery import PyQuery as pq

sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def getName(self):
        return "韩剧看看"
    
    def init(self, extend):
        self.siteUrl = "https://www.hanjukankan.com"
        self.header = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': self.siteUrl,
            'Origin': self.siteUrl
        }
    
    def getHeader(self):
        return self.header

    def homeContent(self, filter):
        result = {}
        classes = []
        try:
            rsp = self.fetch(self.siteUrl, headers=self.getHeader())
            if rsp and rsp.text:
                doc = pq(rsp.text)
                
                # 策略1：抓取顶部导航 (最常见的位置)
                # 针对韩剧、韩影、韩综等分类
                items = doc('.stui-header__menu li a')
                
                # 策略2：如果是移动端模板，尝试抓取滑动菜单
                if not items:
                    items = doc('.type-slide li a')
                
                seen_ids = set()
                
                for item in items.items():
                    name = item.text().strip()
                    href = item.attr('href')
                    
                    # 过滤无效分类
                    if not name or not href or name == "首页" or name == "全站":
                        continue
                        
                    # 提取分类ID
                    # 匹配格式: /vodtype/1.html 或 /list/1.html
                    match = re.search(r'/(?:vodtype|list)/(\d+)', href)
                    if match:
                        tid = match.group(1)
                        if tid not in seen_ids:
                            seen_ids.add(tid)
                            classes.append({
                                'type_name': name,
                                'type_id': tid
                            })
            
            # 排序优化：尽量让韩剧、电影排在前面（如果抓取顺序乱的话）
            # 这里保持原站顺序通常是最好的

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
            rsp = self.fetch(self.siteUrl, headers=self.getHeader())
            if rsp and rsp.text:
                doc = pq(rsp.text)
                
                # 首页推荐内容选择器
                # 兼容 stui-vodlist 和 common-list
                items = doc('.stui-vodlist li, .index-list li')
                
                for item in items.items():
                    videos.append(self._parse_vod_item(item))
            
            # 过滤掉空的条目
            result['list'] = [v for v in videos if v['vod_id']]
            
        except Exception as e:
            print(f"homeVideoContent error: {e}")
            
        return result

    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        videos = []
        try:
            # 拼接分类链接：/vodtype/{tid}-{pg}.html
            url = f"{self.siteUrl}/vodtype/{tid}-{pg}.html"
            
            rsp = self.fetch(url, headers=self.getHeader())
            if rsp and rsp.text:
                doc = pq(rsp.text)
                
                # 分类页列表选择器
                items = doc('.stui-vodlist li, .vod-list li')
                for item in items.items():
                    videos.append(self._parse_vod_item(item))
                    
        except Exception as e:
            print(f"categoryContent error: {e}")
            
        result['list'] = [v for v in videos if v['vod_id']]
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
            # 补全链接
            if aid.startswith('http'):
                url = aid
            else:
                url = urllib.parse.urljoin(self.siteUrl, aid)
                
            rsp = self.fetch(url, headers=self.getHeader())
            if not rsp or not rsp.text:
                return result
                
            html = rsp.text
            doc = pq(html)
            
            vod = {
                'vod_id': aid,
                'vod_name': doc('h1.title').text() or doc('.stui-content__detail .title').text(),
                'vod_pic': '',
                'vod_remarks': '',
                'vod_content': '',
                'vod_play_from': '',
                'vod_play_url': ''
            }
            
            # 1. 解析图片
            img = doc('.stui-vodlist__thumb').attr('data-original') or \
                  doc('.stui-vodlist__thumb').attr('src') or \
                  doc('.picture img').attr('src')
            vod['vod_pic'] = self._fix_url(img)
            
            # 2. 解析简介
            content = doc('.stui-content__detail .desc').text() or \
                      doc('.stui-pannel_bd .col-pd').text() or \
                      doc('meta[name="description"]').attr('content')
            vod['vod_content'] = content.strip() if content else ""
            
            # 3. 解析备注（年份、地区等）
            info = doc('.stui-content__detail .data').text()
            if info:
                vod['vod_remarks'] = info
            
            # 4. 解析播放列表 (核心部分)
            playFrom = []
            playList = []
            
            # 获取播放源标题 (例如: 专线线路, 极速云)
            tabs = doc('.stui-pannel__head h3, .stui-vodlist__head h3')
            if not tabs:
                tabs = doc('.nav-tabs li')
                
            for tab in tabs.items():
                name = tab.text().replace("播放", "").strip()
                if name:
                    playFrom.append(name)
            
            # 如果没找到标题，但有列表，给个默认名
            playlists = doc('.stui-content__playlist, .playlist')
            if len(playlists) > len(playFrom):
                for i in range(len(playlists) - len(playFrom)):
                    playFrom.append(f"线路{len(playFrom)+1}")
            
            # 获取每一集的链接
            for pl in playlists.items():
                urls = []
                links = pl.find('a')
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
            
            # 搜索URL构造
            # 韩剧看看通常使用 /vodsearch/-------------.html?wd=关键字
            # 或者 /index.php/ajax/suggest?mid=1&wd=关键字 (JSON)
            # 这里使用HTML搜索页
            
            search_url = f"{self.siteUrl}/vodsearch/-------------.html?wd={urllib.parse.quote(key)}"
            
            rsp = self.fetch(search_url, headers=self.getHeader())
            if rsp and rsp.text:
                doc = pq(rsp.text)
                items = doc('.stui-vodlist li, .search-list li')
                for item in items.items():
                    videos.append(self._parse_vod_item(item))
                    
        except Exception as e:
            print(f"searchContent error: {e}")
            
        result['list'] = [v for v in videos if v['vod_id']]
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
            
            # 嗅探模式：parse=1
            # 大多数CMS站点使用iframe嵌入或者m3u8，直接开启嗅探最稳
            result["parse"] = 1
            result["playUrl"] = ''
            result["url"] = url
            result["header"] = self.getHeader()
            
        except Exception as e:
            print(f"playerContent error: {e}")
            
        return result

    # --- 辅助函数 ---
    
    def _parse_vod_item(self, item):
        """解析单个视频条目的通用函数"""
        res = {'vod_id': '', 'vod_name': '', 'vod_pic': '', 'vod_remarks': ''}
        try:
            a = item.find('a.stui-vodlist__thumb')
            if not a:
                a = item.find('a') # 兜底
                
            if not a: return res

            # 获取标题
            title = a.attr('title') or item.find('.title a').text() or item.find('h4 a').text()
            
            # 获取链接
            href = a.attr('href')
            
            # 获取图片 (处理懒加载和背景图)
            img = a.attr('data-original') or a.attr('style') or a.find('img').attr('src')
            
            # 处理背景图样式 url('...')
            if img and 'background-image' in img:
                match = re.search(r'url\([\'"]?(.*?)[\'"]?\)', img)
                if match:
                    img = match.group(1)
            
            # 获取备注 (集数/评分)
            remarks = item.find('.pic-text').text() or \
                      item.find('.pic-tag').text() or \
                      item.find('.remarks').text()
            
            res['vod_id'] = href
            res['vod_name'] = title
            res['vod_pic'] = self._fix_url(img)
            res['vod_remarks'] = remarks
            
        except Exception as e:
            pass
        return res

    def _fix_url(self, url):
        """修复相对路径"""
        if not url: return ""
        if url.startswith('//'):
            return "https:" + url
        if not url.startswith('http'):
            return urllib.parse.urljoin(self.siteUrl, url)
        return url

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return {}
