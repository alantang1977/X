# coding=utf-8
# !/usr/bin/python
import sys
import datetime
from copy import deepcopy
from urllib.parse import quote_plus, unquote, quote
from lxml import etree

sys.path.append('..')
from base.spider import Spider
import json
import re
import base64


class Spider(Spider):
    def getName(self):
        return "飞快"

    def init(self, extend=""):
        self.log("feikuai", "Spider initialized")
        pass
    
    def log(self, tag, message):
        """Log with tag for logcat filtering"""
        print(f"[{tag}] {message}")
        sys.stdout.flush()

    def homeContent(self, filter):
        self.log("feikuai", "homeContent called")
        result = {}
        cateManual = {
            "推荐": "0",
            "电影": "1",
            "欧美剧": "16",
            "日韩剧": "15",
            "日韩动漫": "27",
            "欧美动漫": "28",
            "短剧": "32"
        }
        classes = []
        for k in cateManual:
            classes.append({'type_name': k, 'type_id': cateManual[k]})
        result['class'] = classes
        if filter:
            result['filters'] = self.get_filters()
        self.log("feikuai", f"homeContent returned {len(classes)} categories")
        return result

    def get_filters(self):
        filt = deepcopy(self.config.get('filter', {}))
        current_year = datetime.datetime.now().year
        years = [{"n": "全部", "v": ""}] + [{"n": str(y), "v": str(y)} for y in range(current_year, 2009, -1)]
        for tid, arr in filt.items():
            for item in arr:
                key = item.get('key') or item.get('k')
                if key in ('year', '11'):
                    item['value'] = years
        return filt

    def homeVideoContent(self):
        self.log("feikuai", "homeVideoContent called - fetching recommendations")
        recommend_list = []
        try:
            url = "https://feikuai.tv/"
            self.log("feikuai", f"Fetching homepage: {url}")
            rsp = self.fetch(url, headers=self.header)
            if not rsp or not rsp.text:
                self.log("feikuai", "Failed to fetch homepage")
                return {'list': recommend_list}

            root = self._parse_html(rsp)
            if not root:
                self.log("feikuai", "Failed to parse homepage HTML")
                return {'list': recommend_list}

            recommend_links = root.xpath(
                '//div[contains(@class, "module-focus")]//a[contains(@href, "/voddetail/")] | '
                '//div[contains(@class, "module-hot")]//a[contains(@href, "/voddetail/")] | '
                '//div[contains(@class, "module-recommend")]//a[contains(@href, "/voddetail/")] | '
                '//div[contains(@class, "module-items") and contains(@class, "module-poster-items")]//a[contains(@href, "/voddetail/")]'
            )
            self.log("feikuai", f"Found {len(recommend_links)} recommendation links")

            seen = set()
            for a in recommend_links:
                video_item = self._parse_video_item(a)
                if video_item and video_item["vod_id"] not in seen:
                    seen.add(video_item["vod_id"])
                    recommend_list.append(video_item)

            recommend_list = recommend_list[:30]
            self.log("feikuai", f"Returning {len(recommend_list)} recommendations")
        except Exception as e:
            self.log("feikuai", f"Error in homeVideoContent: {str(e)}")
        return {'list': recommend_list}
    
    def _parse_video_item(self, a_element):
        """Parse single video item from element"""
        try:
            href = a_element.xpath('./@href')[0] if a_element.xpath('./@href') else ''
            m = re.search(r'/voddetail/(\d+)\.html', href)
            if not m:
                return None
            sid = m.group(1)

            title_nodes = (a_element.xpath('.//div[contains(@class, "module-poster-item-title")]//text()') or
                          a_element.xpath('.//div[contains(@class, "module-card-item-title")]/a//text()') or
                          a_element.xpath('./@title') or a_element.xpath('.//img/@alt'))
            name = title_nodes[0].strip() if title_nodes else f"视频_{sid}"
            
            img = self._parse_image_url(a_element)
            
            remark_nodes = a_element.xpath('.//div[contains(@class, "module-item-note")]//text()')
            remark = ''.join([x.strip() for x in remark_nodes if x.strip()]) if remark_nodes else ""

            return {
                "vod_id": sid,
                "vod_name": name,
                "vod_pic": img,
                "vod_remarks": remark
            }
        except Exception:
            return None

    def _parse_image_url(self, element):
        """Parse image URL from element"""
        img_nodes = (element.xpath('.//img[contains(@class, "lazy")]/@data-original[contains(., ".webp") or contains(., ".jpg") or contains(., ".png")]') or
                    element.xpath('.//img[contains(@class, "lazy")]/@src[contains(., ".webp") or contains(., ".jpg") or contains(., ".png")]') or
                    element.xpath('.//img/@data-original[contains(., ".webp") or contains(., ".jpg") or contains(., ".png")]') or
                    element.xpath('.//img/@src[contains(., ".webp") or contains(., ".jpg") or contains(., ".png")]'))
        
        if img_nodes:
            img = img_nodes[0]
            if img.startswith('/'):
                img = 'https://feikuai.tv' + img
            return img
        return ''

    def _parse_html(self, rsp):
        try:
            if hasattr(rsp, 'content'):
                parser = etree.HTMLParser(encoding='utf-8', recover=True, remove_blank_text=True)
                return etree.HTML(rsp.content, parser=parser)
            else:
                parser = etree.HTMLParser(encoding='utf-8', recover=True, remove_blank_text=True)
                return etree.HTML(rsp.text.encode('utf-8', errors='ignore'), parser=parser)
        except Exception:
            return self.html(rsp.text)

    def _build_vodshow_url(self, tid, pg, ext):
        area = (ext.get('area') or ext.get('1') or '').strip()
        cate = (ext.get('class') or ext.get('3') or '').strip()
        year = (ext.get('year') or ext.get('11') or '').strip()
        by = (ext.get('by') or ext.get('2') or '').strip()
        by_map = {'最新': 'time', '最热': 'hits', '评分': 'score'}
        by_val = by_map.get(by, '')
        enc_area = quote_plus(area) if area else ''
        enc_cate = quote_plus(cate) if cate else ''
        pg_str = '' if str(pg) in ('', '1') else str(pg)
        url = f'https://feikuai.tv/vodshow/{tid}-{enc_area}-{by_val}-{enc_cate}-----{pg_str}---{year}.html'
        return url

    def categoryContent(self, tid, pg, filter, extend):
        # Handle 推荐 page
        if str(tid) == '0':
            self.log("feikuai", "categoryContent: tid=0, returning homeVideoContent")
            return self.homeVideoContent()
        
        self.log("feikuai", f"categoryContent called: tid={tid}, pg={pg}")
        result = {'list': [], 'page': pg, 'pagecount': 9999, 'limit': 90, 'total': 999999}
        try:
            ext = extend or {}
            url = self._build_vodshow_url(tid, pg, ext)
            self.log("feikuai", f"Built URL: {url}")
        except Exception as e:
            self.log("feikuai", f"Error building URL: {str(e)}")
            url = f'https://feikuai.tv/vodshow/{tid}-----------.html'
        headers = self.header.copy()
        tid_str = str(tid)
        if tid_str == '1':
            headers['Referer'] = 'https://feikuai.tv/vodtype/1.html'
        elif tid_str in ('15', '16', '32'):
            headers['Referer'] = 'https://feikuai.tv/vodtype/2.html'
        elif tid_str in ('27', '28'):
            headers['Referer'] = 'https://feikuai.tv/vodtype/4.html'
        else:
            headers['Referer'] = 'https://feikuai.tv/'
        self.log("feikuai", f"Fetching category page with referer: {headers['Referer']}")
        rsp = self.fetch(url, headers=headers)
        if not rsp or not rsp.text:
            self.log("feikuai", "Failed to fetch category page")
            return result
        root = self._parse_html(rsp)
        videos = []
        seen = set()
        try:
            links = root.xpath('//div[contains(@class, "module-items") and contains(@class, "module-poster-items")]//a[contains(@href, "/voddetail/")]')
            if not links:
                links = root.xpath('//a[contains(@class, "module-poster-item") and contains(@href, "/voddetail/")]')
            if not links:
                links = root.xpath('//div[contains(@class, "module-card-items")]//a[contains(@href, "/voddetail/")]')
            self.log("feikuai", f"Found {len(links)} video links")
            for a in links:
                video_item = self._parse_video_item(a)
                if video_item and video_item["vod_id"] not in seen:
                    seen.add(video_item["vod_id"])
                    videos.append(video_item)
        except Exception as e:
            self.log("feikuai", f"Error parsing category videos: {str(e)}")
        result['list'] = videos
        self.log("feikuai", f"categoryContent returning {len(videos)} videos")
        return result

    def _decode_url_field(self, raw, encrypt):
        try:
            if not raw:
                return ''
            enc = str(encrypt or '0').strip()
            if enc == '1':
                txt = unquote(raw)
            elif enc == '2':
                try:
                    b = base64.b64decode(raw + '===')
                    txt = unquote(b.decode('utf-8', errors='ignore'))
                except Exception:
                    txt = unquote(raw)
            else:
                txt = raw
            txt = re.sub(r'%u([0-9a-fA-F]{4})',
                         lambda m: chr(int(m.group(1), 16)), txt)
            return txt
        except Exception:
            return raw

    def _convert_to_push_url(self, raw_url, source_name, is_single_tab):
        """Convert pan/magnet URL to push format for TVBox/Fongmi"""
        try:
            # Aliyun/Alipan
            if raw_url.startswith('https://www.aliyundrive.com/s/') or raw_url.startswith('https://www.alipan.com/s/'):
                self.log("feikuai", f"Converting Aliyun URL: {raw_url[:50]}...")
                if is_single_tab:
                    return f"http://127.0.0.1:9978/proxy?do=ali&type=push&confirm=0&url={quote(raw_url)}"
                else:
                    return f"http://127.0.0.1:9978/proxy?do=ali&type=push&url={quote(raw_url)}"
            
            # Quark
            elif raw_url.startswith('https://pan.quark.cn/s/'):
                self.log("feikuai", f"Converting Quark URL: {raw_url[:50]}...")
                if is_single_tab:
                    return f"http://127.0.0.1:9978/proxy?do=quark&type=push&confirm=0&url={quote(raw_url)}"
                else:
                    return f"http://127.0.0.1:9978/proxy?do=quark&type=push&url={quote(raw_url)}"
            
            # Baidu Pan
            elif raw_url.startswith('https://pan.baidu.com/s/'):
                self.log("feikuai", f"Converting Baidu Pan URL: {raw_url[:50]}...")
                if is_single_tab:
                    return f"http://127.0.0.1:9978/proxy?do=push&confirm=0&url={quote(raw_url)}"
                else:
                    return f"http://127.0.0.1:9978/proxy?do=push&url={quote(raw_url)}"
            
            # Magnet or ed2k - return as is
            elif raw_url.startswith('magnet:') or raw_url.startswith('ed2k:'):
                self.log("feikuai", f"Returning magnet/ed2k URL as-is")
                return raw_url
            
            # Other URLs - return as is
            else:
                self.log("feikuai", f"Unknown URL type, returning as-is: {raw_url[:50]}...")
                return raw_url
        except Exception as e:
            self.log("feikuai", f"Error converting URL: {str(e)}")
            return raw_url

    def detailContent(self, ids):
        if not ids:
            self.log("feikuai", "detailContent: no ids provided")
            return {'list': []}
        tid = str(ids[0]).strip()
        self.log("feikuai", f"detailContent called for id: {tid}")
        url = f'https://feikuai.tv/voddetail/{tid}.html'
        try:
            self.log("feikuai", f"Fetching detail page: {url}")
            rsp = self.fetch(url, headers=self.header)
            if not rsp or not rsp.text:
                self.log("feikuai", "Failed to fetch detail page")
                return self._create_fallback_vod(tid, '获取页面失败')
            root = self._parse_html(rsp)
            if root is None:
                self.log("feikuai", "Failed to parse detail HTML")
                return self._create_fallback_vod(tid, '解析HTML失败')
        except Exception as e:
            self.log("feikuai", f"Error in detailContent: {str(e)}")
            return self._create_fallback_vod(tid, f'异常: {str(e)}')
        
        title = ''
        try:
            tnodes = root.xpath('//h1/text() | //div[contains(@class, "module-info-heading")]//h1/text()')
            title = tnodes[0].strip() if tnodes else ''
        except Exception:
            title = ''
        
        pic = ''
        try:
            pnodes = root.xpath('//div[contains(@class, "module-info-poster")]//img/@data-original | //div[contains(@class, "module-info-poster")]//img/@src | //img[contains(@class, "lazy")]/@data-original | //img[contains(@class, "lazy")]/@src')
            if pnodes:
                pic = pnodes[0]
                if pic.startswith('/'):
                    pic = 'https://feikuai.tv' + pic
        except Exception:
            pic = ''
        
        detail = ''
        try:
            dnodes = root.xpath('//div[contains(@class, "module-info-introduction-content")]//text()')
            if dnodes:
                detail = '\n'.join([x.strip() for x in dnodes if x.strip()])
        except Exception:
            detail = ''
        
        vod = {
            "vod_id": tid,
            "vod_name": title,
            "vod_pic": pic,
            "type_name": "",
            "vod_year": "",
            "vod_area": "",
            "vod_remarks": "",
            "vod_actor": "",
            "vod_director": "",
            "vod_content": detail
        }
        
        playFrom = []
        playList = []
        
        # Extract regular video sources
        try:
            ep_links = root.xpath('//div[contains(@class, "module-play-list")]//a[contains(@href, "/vodplay/")] | //ul[contains(@class, "module-play-list")]//a[contains(@href, "/vodplay/")]')
            self.log("feikuai", f"Found {len(ep_links)} episode links")
            groups = {}
            for a in ep_links:
                try:
                    hrefs = a.xpath('./@href')
                    if not hrefs:
                        continue
                    href = hrefs[0]
                    m = re.search(r'/vodplay/(\d+)-(\d+)-(\d+)\.html', href)
                    if not m:
                        continue
                    vid, sid, epid = m.group(1), m.group(2), m.group(3)
                    if vid != tid:
                        continue
                    name = ''.join(a.xpath('string(.)')).strip()
                    if not name or name in ('立即播放', '收藏', '追更', '分享', '报错', '下载'):
                        continue
                    if sid not in groups:
                        groups[sid] = []
                    groups[sid].append(f"{name}${vid}-{sid}-{epid}")
                except Exception:
                    continue
            
            ordered_sids = []
            for blk in root.xpath('//div[contains(@class, "his-tab-list")]'):
                try:
                    first = blk.xpath('.//a[contains(@href, "/vodplay/")][1]/@href')
                    if not first:
                        continue
                    mm = re.search(r'/vodplay/(\d+)-(\d+)-(\d+)\.html', first[0])
                    if not mm:
                        continue
                    sid = mm.group(2)
                    if sid not in ordered_sids:
                        ordered_sids.append(sid)
                except Exception:
                    continue
            
            labels = []
            try:
                labels = [x.strip() for x in root.xpath('//div[contains(@class, "module-tab-items-box")]//div[contains(@class, "module-tab-item")]//span/text()') if x.strip()]
            except Exception:
                labels = []
            
            for idx, sid in enumerate(ordered_sids):
                sname = labels[idx] if idx < len(labels) else f"线路{sid}"
                playFrom.append(sname)
                playList.append('#'.join(groups.get(sid, [])))
        except Exception:
            pass
        
        # Extract pan/magnet download links
        pan_sources = []
        try:
            download_section = root.xpath('//div[@id="download-list"]')
            if download_section:
                self.log("feikuai", "Found download section")
                tab_items = root.xpath('//div[@id="y-downList"]//div[contains(@class, "module-tab-item")]')
                self.log("feikuai", f"Found {len(tab_items)} download tabs")
                
                for tab in tab_items:
                    try:
                        source_name = ''.join(tab.xpath('.//span/text()')).strip()
                        if not source_name or source_name == '天翼云盘':
                            continue
                        
                        tab_index = tab.xpath('./@data-index')
                        if not tab_index:
                            continue
                        tab_index = tab_index[0]
                        
                        content_divs = root.xpath(f'//div[@id="tab-content-{tab_index}"]//div[@class="module-row-info"]//a')
                        
                        episodes = []
                        for idx, link_elem in enumerate(content_divs, 1):
                            try:
                                raw_url = link_elem.xpath('./@href')
                                if not raw_url:
                                    continue
                                raw_url = raw_url[0].strip()
                                
                                title_elem = link_elem.xpath('.//h4/text()')
                                if title_elem:
                                    ep_title = title_elem[0].strip()
                                    ep_title = re.sub(r'@一键搜片-\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}$', '', ep_title).strip()
                                else:
                                    ep_title = f"资源{idx}"
                                
                                # Convert to push URL format
                                push_url = self._convert_to_push_url(raw_url, source_name, len(content_divs) == 1)
                                episodes.append(f"{ep_title}${push_url}")
                            except Exception:
                                continue
                        
                        if episodes:
                            self.log("feikuai", f"Added {len(episodes)} episodes for source: {source_name}")
                            pan_sources.append((source_name, episodes))
                    except Exception as e:
                        self.log("feikuai", f"Error parsing download tab: {str(e)}")
                        continue
        except Exception as e:
            self.log("feikuai", f"Error extracting pan sources: {str(e)}")
        
        # Add pan sources to playFrom/playList
        for source_name, episodes in pan_sources:
            playFrom.append(source_name)
            playList.append('#'.join(episodes))
        
        self.log("feikuai", f"Total sources: {len(playFrom)}, Pan sources: {len(pan_sources)}")
        
        if not playFrom or not playList:
            playFrom = ['飞快']
            playList = [f'暂无播放源$https://feikuai.tv/voddetail/{tid}.html']
        
        vod['vod_play_from'] = '$$$'.join(playFrom) if playFrom else ""
        vod['vod_play_url'] = '$$$'.join(playList)
        return {'list': [vod]}

    def _create_fallback_vod(self, tid, error_msg):
        return {
            'list': [{
                'vod_id': tid,
                'vod_name': f'加载失败: {error_msg}',
                'vod_pic': '',
                'vod_content': f'无法加载视频详情。错误: {error_msg}',
                'vod_play_from': '飞快',
                'vod_play_url': f'错误$https://feikuai.tv/voddetail/{tid}.html'
            }]
        }

    def searchContent(self, key, quick, pg='1'):
        self.log("feikuai", f"searchContent called: key={key}, pg={pg}")
        videos = []
        try:
            if str(pg) in ('', '1'):
                url = f'https://feikuai.tv/vodsearch/-------------.html?wd={quote_plus(key)}'
                headers = self.header.copy()
                headers['Referer'] = f'https://feikuai.tv/vodsearch/-------------.html?wd={quote_plus(key)}'
            else:
                url = f'https://feikuai.tv/label/search_ajax.html?wd={quote_plus(key)}&by=time&order=desc&page={pg}'
                headers = self.header.copy()
                headers['X-Requested-With'] = 'XMLHttpRequest'
                headers['Accept'] = '*/*'
                headers['Referer'] = f'https://feikuai.tv/vodsearch/-------------.html?wd={quote_plus(key)}'
            
            self.log("feikuai", f"Search URL: {url}")
            rsp = self.fetch(url, headers=headers)
            if not rsp or not rsp.text:
                self.log("feikuai", "Failed to fetch search results")
                return {'list': []}
            
            root = self._parse_html(rsp)
            items = root.xpath('//div[@id="resultList"]//a[contains(@href, "/voddetail/")]')
            if not items:
                items = root.xpath('//div[contains(@class, "module-card-items")]//a[contains(@href, "/voddetail/")]')
            if not items:
                items = root.xpath('//div[contains(@class, "module-items") and contains(@class, "module-poster-items")]//a[contains(@href, "/voddetail/")]')
            if not items:
                items = root.xpath('//a[contains(@href, "/voddetail/")]')
            
            self.log("feikuai", f"Found {len(items)} search result items")
            seen = set()
            for a in items:
                video_item = self._parse_video_item(a)
                if video_item and video_item["vod_id"] not in seen:
                    seen.add(video_item["vod_id"])
                    videos.append(video_item)
            
            self.log("feikuai", f"searchContent returning {len(videos)} videos")
            return {'list': videos}
        except Exception as e:
            self.log("feikuai", f"Error in searchContent: {str(e)}")
            return {'list': []}

    def playerContent(self, flag, id, vipFlags):
        self.log("feikuai", f"playerContent called: flag={flag}, id={id}")
        # For push URLs, return directly with parse=1
        if isinstance(id, str) and ('127.0.0.1:9978/proxy' in id or id.startswith('magnet:') or id.startswith('ed2k:')):
            self.log("feikuai", f"Returning push/magnet URL directly: {id[:50]}...")
            return {"parse": 1, "url": id, "header": self.header}
        
        # Original video playback logic
        play_url = f'https://feikuai.tv/vodplay/{id}.html'
        vurl = play_url
        self.log("feikuai", f"Fetching player page: {play_url}")
        rsp = self.fetch(play_url, headers=self.header, timeout=45)
        text = rsp.text
        m = re.search(r'(?:var\s+)?player_[a-zA-Z0-9_]+\s*=\s*(\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\})(?=\s*</script>)', text, re.S)
        if m:
            data = json.loads(m.group(1))
            vurl = data.get('url') or ''
            vurl = self._decode_url_field(vurl, str(data.get('encrypt', '0')))
            if vurl.startswith('//'):
                vurl = 'https:' + vurl
            self.log("feikuai", f"Extracted video URL: {vurl[:50]}...")
        else:
            self.log("feikuai", "Failed to extract player data")
        return {"parse": 0, "url": vurl, "header": self.header}
    
    def localProxy(self, params):
        pass
    
    def isVideoFormat(self, url):
        return url

    def manualVideoCheck(self):
        return []

    def destroy(self):
        pass

    def getProxyUrl(self, local=True):
        return 'http://127.0.0.1:9978/proxy?do=py'

    config = {
        "filter": {
            "1": [
                {"key": "class", "name": "类型", "value": [{"n": "全部", "v": ""}, {"n": "恐怖", "v": "恐怖"}, {"n": "惊悚", "v": "惊悚"}, {"n": "爱情", "v": "爱情"}, {"n": "同性", "v": "同性"}, {"n": "喜剧", "v": "喜剧"}, {"n": "动画", "v": "动画"}, {"n": "纪录片", "v": "纪录片"}]},
                {"key": "area", "name": "地区", "value": [{"n": "全部", "v": ""}, {"n": "日本", "v": "日本"}, {"n": "韩国", "v": "韩国"}, {"n": "美国", "v": "美国"}, {"n": "英国", "v": "英国"}, {"n": "法国", "v": "法国"}, {"n": "德国", "v": "德国"}, {"n": "意大利", "v": "意大利"}, {"n": "巴西", "v": "巴西"}, {"n": "瑞典", "v": "瑞典"}]},
                {"key": "year", "name": "年份", "value": []},
                {"key": "by", "name": "排序", "value": [{"n": "最新", "v": "最新"}, {"n": "最热", "v": "最热"}, {"n": "评分", "v": "评分"}]}
            ],
            "16": [
                {"key": "class", "name": "类型", "value": [{"n": "全部", "v": ""}, {"n": "恐怖", "v": "恐怖"}, {"n": "惊悚", "v": "惊悚"}, {"n": "爱情", "v": "爱情"}, {"n": "同性", "v": "同性"}, {"n": "喜剧", "v": "喜剧"}, {"n": "动画", "v": "动画"}, {"n": "纪录片", "v": "纪录片"}]},
                {"key": "area", "name": "地区", "value": [{"n": "全部", "v": ""}, {"n": "美国", "v": "美国"}, {"n": "英国", "v": "英国"}, {"n": "法国", "v": "法国"}, {"n": "德国", "v": "德国"}, {"n": "意大利", "v": "意大利"}, {"n": "巴西", "v": "巴西"}, {"n": "瑞典", "v": "瑞典"}]},
                {"key": "year", "name": "年份", "value": []},
                {"key": "by", "name": "排序", "value": [{"n": "最新", "v": "最新"}, {"n": "评分", "v": "评分"}]}
            ],
            "15": [
                {"key": "class", "name": "类型", "value": [{"n": "全部", "v": ""}, {"n": "恐怖", "v": "恐怖"}, {"n": "惊悚", "v": "惊悚"}, {"n": "爱情", "v": "爱情"}, {"n": "同性", "v": "同性"}, {"n": "喜剧", "v": "喜剧"}, {"n": "动画", "v": "动画"}, {"n": "纪录片", "v": "纪录片"}]},
                {"key": "area", "name": "地区", "value": [{"n": "全部", "v": ""}, {"n": "日本", "v": "日本"}, {"n": "韩国", "v": "韩国"}]},
                {"key": "year", "name": "年份", "value": []},
                {"key": "by", "name": "排序", "value": [{"n": "最新", "v": "最新"}, {"n": "评分", "v": "评分"}]}
            ],
            "27": [
                {"key": "area", "name": "地区", "value": [{"n": "全部", "v": ""}, {"n": "日本", "v": "日本"}, {"n": "韩国", "v": "韩国"}]},
                {"key": "class", "name": "类型", "value": [{"n": "全部", "v": ""}, {"n": "同性", "v": "同性"}, {"n": "恐怖", "v": "恐怖"}, {"n": "情色", "v": "情色"}, {"n": "搞笑", "v": "搞笑"}]},
                {"key": "year", "name": "年份", "value": []},
                {"key": "by", "name": "排序", "value": [{"n": "最新", "v": "最新"}, {"n": "评分", "v": "评分"}]}
            ],
            "28": [
                {"key": "area", "name": "地区", "value": [{"n": "全部", "v": ""}, {"n": "美国", "v": "美国"}, {"n": "其他", "v": "其他"}]},
                {"key": "class", "name": "类型", "value": [{"n": "全部", "v": ""}, {"n": "同性", "v": "同性"}, {"n": "恐怖", "v": "恐怖"}, {"n": "搞笑", "v": "搞笑"}]},
                {"key": "year", "name": "年份", "value": []},
                {"key": "by", "name": "排序", "value": [{"n": "最新", "v": "最新"}, {"n": "评分", "v": "评分"}]}
            ],
            "32": [
                {"key": "year", "name": "年份", "value": []},
                {"key": "by", "name": "排序", "value": [{"n": "最新", "v": "最新"}, {"n": "评分", "v": "评分"}]}
            ]
        }
    }

    header = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive"
    }
