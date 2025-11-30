# coding=utf-8
#!/usr/bin/python
import sys
sys.path.append('..')
from base.spider import Spider
import json
import re
try:
    import ujson
except ImportError:
    ujson = json
try:
    from pyquery import PyQuery as pq
except ImportError:
    pq = None
try:
    from cachetools import TTLCache
except ImportError:
    class TTLCache:
        def __init__(self, maxsize=100, ttl=600):
            self.cache = {}
            self.maxsize = maxsize
        def __contains__(self, key):
            return key in self.cache
        def __getitem__(self, key):
            return self.cache[key]
        def __setitem__(self, key, value):
            if len(self.cache) >= self.maxsize:
                first_key = next(iter(self.cache))
                del self.cache[first_key]
            self.cache[key] = value
        def __len__(self):
            return len(self.cache)

class Spider(Spider):
    def __init__(self):
        self.cache = TTLCache(maxsize=100, ttl=600)
        self.cloud_drive_map = {
            'kuake': '夸克网盘',
            'uc': 'UC网盘',
            'xunlei1': '百度网盘'
        }
        
    def getName(self):
        return "Libvio"
        
    def init(self, extend=""):
        print("============{0}============".format(extend))
        if not hasattr(self, 'cache'):
            self.cache = TTLCache(maxsize=100, ttl=600)
        pass
        
    def _fetch_with_cache(self, url, headers=None):
        cache_key = f"{url}_{hash(str(headers))}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        try:
            response = self.fetch(url, headers=headers or self.header)
        except Exception as e:
            print(f"Fetch failed for {url}: {e}")
            response = None  # Fallback to None on error
        if response:
            self.cache[cache_key] = response
        return response
        
    def _parse_html_fast(self, html_text):
        if not html_text:
            return None
        if pq is not None:
            try:
                return pq(html_text)
            except:
                pass
        return self.html(self.cleanText(html_text))
        
    def homeContent(self, filter):
        result = {}
        cateManual = {"电影": "1", "电视剧": "2", "动漫": "4", "日韩剧": "15", "欧美剧": "16"}
        classes = []
        for k in cateManual:
            classes.append({'type_name': k, 'type_id': cateManual[k]})
        result['class'] = classes
        return result
        
    def homeVideoContent(self):
        rsp = self._fetch_with_cache("https://www.libvio.site")
        if not rsp:
            return {'list': []}
        doc = self._parse_html_fast(rsp.text)
        videos = []
        if pq is not None and hasattr(doc, '__call__'):
            try:
                thumb_links = doc('a.stui-vodlist__thumb.lazyload')
                for i in range(thumb_links.length):
                    try:
                        thumb = thumb_links.eq(i)
                        href = thumb.attr('href')
                        if not href: continue
                        sid_match = re.search(r'/detail/(\d+)\.html', href)
                        if not sid_match: continue
                        sid = sid_match.group(1)
                        name = thumb.attr('title')
                        if not name: continue
                        pic = thumb.attr('data-original') or ""
                        mark = thumb.text().strip()
                        videos.append({"vod_id": sid, "vod_name": name.strip(), "vod_pic": pic, "vod_remarks": mark})
                    except Exception as e: continue
            except: pass
        if not videos:
            try:
                thumb_links = doc.xpath("//a[@class='stui-vodlist__thumb lazyload']")
                for thumb in thumb_links:
                    try:
                        href = thumb.xpath("./@href")[0]
                        sid_match = re.search(r'/detail/(\d+)\.html', href)
                        if not sid_match: continue
                        sid = sid_match.group(1)
                        name = thumb.xpath("./@title")[0].strip()
                        if not name: continue
                        pic_list = thumb.xpath("./@data-original")
                        pic = pic_list[0] if pic_list else ""
                        mark_list = thumb.xpath("./text()")
                        mark = mark_list[0].strip() if mark_list else ""
                        videos.append({"vod_id": sid, "vod_name": name, "vod_pic": pic, "vod_remarks": mark})
                    except Exception as e: continue
            except Exception as e: print(f"Homepage parse failed: {e}")
        result = {'list': videos}
        return result
        
    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        url = 'https://www.libvio.site/type/{0}-{1}.html'.format(tid, pg)
        print(url)
        rsp = self._fetch_with_cache(url)
        if not rsp:
            return result
        doc = self._parse_html_fast(rsp.text)
        videos = []
        if pq is not None and hasattr(doc, '__call__'):
            try:
                thumb_links = doc('a.stui-vodlist__thumb.lazyload')
                for i in range(thumb_links.length):
                    try:
                        thumb = thumb_links.eq(i)
                        href = thumb.attr('href')
                        if not href: continue
                        sid_match = re.search(r'/detail/(\d+)\.html', href)
                        if not sid_match: continue
                        sid = sid_match.group(1)
                        name = thumb.attr('title')
                        if not name: continue
                        pic = thumb.attr('data-original') or ""
                        mark = thumb.text().strip()
                        videos.append({"vod_id": sid, "vod_name": name.strip(), "vod_pic": pic, "vod_remarks": mark})
                    except Exception as e: continue
            except: pass
        if not videos:
            try:
                thumb_links = doc.xpath("//a[@class='stui-vodlist__thumb lazyload']")
                for thumb in thumb_links:
                    try:
                        href = thumb.xpath("./@href")[0]
                        sid_match = re.search(r'/detail/(\d+)\.html', href)
                        if not sid_match: continue
                        sid = sid_match.group(1)
                        name = thumb.xpath("./@title")[0].strip()
                        if not name: continue
                        pic_list = thumb.xpath("./@data-original")
                        pic = pic_list[0] if pic_list else ""
                        mark_list = thumb.xpath("./text()")
                        mark = mark_list[0].strip() if mark_list else ""
                        videos.append({"vod_id": sid, "vod_name": name, "vod_pic": pic, "vod_remarks": mark})
                    except Exception as e: continue
            except Exception as e: print(f"Category parse failed: {e}")
        result['list'] = videos
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        return result
        
    def detailContent(self, array):
        tid = array[0]
        url = 'https://www.libvio.site/detail/{0}.html'.format(tid)
        rsp = self._fetch_with_cache(url)
        if not rsp:
            return {'list': []}
        doc = self._parse_html_fast(rsp.text)
        title = doc('h1').text().strip() or ""
        pic = doc('img').attr('data-original') or doc('img').attr('src') or ""
        detail = ""
        try:
            detail_content = doc('.detail-content').text().strip()
            if detail_content: detail = detail_content
            else:
                detail_text = doc('*:contains("简介：")').text()
                if detail_text and '简介：' in detail_text:
                    detail_part = detail_text.split('简介：')[1]
                    if '详情' in detail_part: detail_part = detail_part.replace('详情', '')
                    detail = detail_part.strip()
        except: pass
        douban = "0.0"
        
        score_text = doc('.detail-info *:contains("分")').text() or ""
        score_match = re.search(r'(\d+\.?\d*)\s*分', score_text)
        if score_match: douban = score_match.group(1)
        vod = {"vod_id": tid, "vod_name": title, "vod_pic": pic, "type_name": "", "vod_year": "", "vod_area": "", "vod_remarks": "", "vod_actor": "", "vod_director": "", "vod_douban_score": douban, "vod_content": detail}
        info_text = doc('p').text()
        if '类型：' in info_text:
            type_match = re.search(r'类型：([^/]+)', info_text)
            if type_match: vod['type_name'] = type_match.group(1).strip()
        if '主演：' in info_text:
            actor_match = re.search(r'主演：([^/]+)', info_text)
            if actor_match: vod['vod_actor'] = actor_match.group(1).strip()
        if '导演：' in info_text:
            director_match = re.search(r'导演：([^/]+)', info_text)
            if director_match: vod['vod_director'] = director_match.group(1).strip()
        
        playFrom = []
        playList = []
        
        vodlist_heads = doc('.stui-vodlist__head')
        for i in range(vodlist_heads.length):
            head = vodlist_heads.eq(i)
            h3_elem = head.find('h3')
            if h3_elem.length == 0:
                continue
                
            header_text = h3_elem.text().strip()
            if not any(keyword in header_text for keyword in ['播放', '下载', 'BD5'] + list(self.cloud_drive_map.values())):
                continue
                
            playFrom.append(header_text)
            vodItems = []
            
            play_links = head.find('a[href*="/play/"]')
            for j in range(play_links.length):
                try:
                    link = play_links.eq(j)
                    href = link.attr('href')
                    name = link.text().strip()
                    if not href or not name:
                        continue
                    
                    tId_match = re.search(r'/play/([^.]+)\.html', href)
                    if not tId_match:
                        continue
                        
                    tId = tId_match.group(1)
                    vodItems.append(name + "$" + tId)
                except:
                    continue
            
            playList.append('#'.join(vodItems) if vodItems else "")
        
        vod['vod_play_from'] = '$$$'.join(playFrom) if playFrom else ""
        vod['vod_play_url'] = '$$$'.join(playList) if playList else ""
        result = {'list': [vod]}
        return result

    def searchContent(self, key, quick):
        url = 'https://www.libvio.site/index.php/ajax/suggest?mid=1&wd={0}'.format(key)
        rsp = self._fetch_with_cache(url, headers=self.header)
        if not rsp:
            return {'list': []}
        try: jo = ujson.loads(rsp.text)
        except: jo = json.loads(rsp.text)
        result = {}
        jArray = []
        if jo.get('total', 0) > 0:
            for j in jo.get('list', []):
                jArray.append({"vod_id": j.get('id', ''), "vod_name": j.get('name', ''), "vod_pic": j.get('pic', ''), "vod_remarks": ""})
        result = {'list': jArray}
        return result
        
    header = {"Referer": "https://www.libvio.site", "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"}
    
    def playerContent(self, flag, id, vipFlags):
        if id.startswith('push://'):
            return {"parse": 0, "playUrl": "", "url": id, "header": ""}
            
        result = {}
        url = 'https://www.libvio.site/play/{0}.html'.format(id)
        try:
            rsp = self._fetch_with_cache(url, headers=self.header)
            if not rsp:
                return {"parse": 1, "playUrl": "", "url": url, "header": ujson.dumps(self.header)}
            return self._handle_cloud_drive(url, rsp, id)
        except Exception as e:
            print(f"Player parse error: {e}")
            return {"parse": 1, "playUrl": "", "url": url, "header": ujson.dumps(self.header)}
    
    def _handle_cloud_drive(self, url, rsp, id):
        try:
            page_text = rsp.text
            script_pattern = r'var player_[^=]*=\s*({[^}]+})'
            matches = re.findall(script_pattern, page_text)
            for match in matches:
                try:
                    player_data = ujson.loads(match)
                    from_value = player_data.get('from', '')
                    url_value = player_data.get('url', '')
                    if from_value in self.cloud_drive_map and url_value:
                        drive_url = url_value.replace('\\/', '/')
                        print(f"检测到{self.cloud_drive_map[from_value]}链接: {drive_url}")
                        return {"parse": 0, "playUrl": "", "url": f"push://{drive_url}", "header": ""}
                except:
                    continue
        except Exception as e:
            print(f"Cloud drive parse error: {e}")
        return self._handle_bd5_player(url, rsp, id)
    
    def _handle_bd5_player(self, url, rsp, id):
        try:
            doc = self._parse_html_fast(rsp.text)
            page_text = rsp.text
            api_match = re.search(r'https://www\.libvio\.site/vid/plyr/vr2\.php\?url=([^&"\s]+)', page_text)
            if api_match:
                return {"parse": 0, "playUrl": "", "url": api_match.group(1), "header": ujson.dumps({"User-Agent": self.header["User-Agent"], "Referer": "https://www.libvio.site/"})}
            iframe_src = doc('iframe').attr('src')
            if iframe_src:
                try:
                    iframe_content = self._fetch_with_cache(iframe_src, headers=self.header)
                    if not iframe_content: raise Exception("Iframe fetch failed")
                    video_match = re.search(r'https://[^"\s]+\.mp4', iframe_content.text)
                    if video_match: return {"parse": 0, "playUrl": "", "url": video_match.group(0), "header": ujson.dumps({"User-Agent": self.header["User-Agent"], "Referer": "https://www.libvio.site/"})}
                except Exception as e: print(f"iframe视频解析失败: {e}")
            script_match = re.search(r'var player_[^=]*=\s*({[^}]+})', page_text)
            if script_match:
                try:
                    jo = ujson.loads(script_match.group(1))
                    if jo:
                        nid = str(jo.get('nid', ''))
                        player_from = jo.get('from', '')
                        if player_from:
                            scriptUrl = f'https://www.libvio.site/static/player/{player_from}.js'
                            scriptRsp = self._fetch_with_cache(scriptUrl)
                            if not scriptRsp: raise Exception("Script fetch failed")
                            parse_match = re.search(r'src="([^"]+url=)', scriptRsp.text)
                            if parse_match:
                                parseUrl = parse_match.group(1)
                                path = f"{jo.get('url', '')}&next={jo.get('link_next', '')}&id={jo.get('id', '')}&nid={nid}"
                                parseRsp = self._fetch_with_cache(parseUrl + path, headers=self.header)
                                if not parseRsp: raise Exception("Parse fetch failed")
                                url_match = re.search(r"urls\s*=\s*'([^']+)'", parseRsp.text)
                                if url_match: return {"parse": 0, "playUrl": "", "url": url_match.group(1), "header": ""}
                except Exception as e: print(f"JavaScript播放器解析失败: {e}")
        except Exception as e: print(f"BD5播放源解析错误: {e}")
        return {"parse": 1, "playUrl": "", "url": url, "header": ujson.dumps(self.header)}
        
    def isVideoFormat(self, url):
        return False
        
    def manualVideoCheck(self):
        pass
        
    def localProxy(self, param):
        action = b''
        try:
            header_dict = json.loads(param.get('header', '{}')) if param.get('header') else {}
            resp = self.fetch(param['url'], headers=header_dict)
            action = resp.content
        except Exception as e:
            print(f"Local proxy error: {e}")
        return [200, "video/MP2T", action, param.get('header', '')]
