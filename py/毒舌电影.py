# coding=utf-8
# !/usr/bin/python
import sys
import datetime
from copy import deepcopy
from urllib.parse import urljoin, quote_plus
from lxml import etree
import urllib3

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sys.path.append('..')
from base.spider import Spider
import json
import re


class Spider(Spider):
    def getName(self):
        return "毒舌电影"

    def init(self, extend=""):
        print("============毒舌电影 Spider Initialized============")
        print(f"[dushe] Spider loaded successfully!")
        print(f"[dushe] Extend param: {extend}")
        pass

    def homeContent(self, filter):
        result = {}
        cateManual = {
            "电影": "1",
            "电视剧": "2",
            "动漫": "3",
            "纪录片": "4"
        }

        classes = []
        for k in cateManual:
            classes.append({
                'type_name': k,
                'type_id': cateManual[k]
            })

        result['class'] = classes
        if (filter):
            result['filters'] = self.get_filters()
        return result

    def get_filters(self):
        base = self.config.get('filter', {})
        filt = deepcopy(base)
        current_year = datetime.datetime.now().year
        
        # Build years list: current year to 2013, plus decades
        years = [{"n": "全部", "v": ""}]
        for y in range(current_year, 2012, -1):
            years.append({"n": str(y), "v": str(y)})
        years.extend([
            {"n": "90年代", "v": "90年代"},
            {"n": "80年代", "v": "80年代"},
            {"n": "70年代", "v": "70年代"}
        ])
        
        for tid, arr in filt.items():
            for item in arr:
                key = item.get('key') or item.get('k')
                if key in ('year', '11'):
                    if 'value' in item:
                        item['value'] = years
                    else:
                        item['v'] = years
        return filt

    def homeVideoContent(self):
        # Not implemented for this site
        result = {'list': []}
        return result

    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        try:
            ext = extend or {}
            # Extract filter values
            cate_type = ext.get('class') or ext.get('3') or ''
            area = ext.get('area') or ext.get('1') or ''
            year = ext.get('year') or ext.get('11') or ''
            by = ext.get('by') or ext.get('2') or ''
            
            # URL encode Chinese characters
            enc_type = quote_plus(cate_type) if cate_type else ''
            enc_area = quote_plus(area) if area else ''
            enc_year = quote_plus(year) if year else ''
            
            # Map sorting values
            by_map = {
                '最新': '2',
                '最热': '3',
                '评分': '4'
            }
            by_val = by_map.get(by, '2')  # Default to 最新
            
            # Build URL: /show/{tid}-{type}-{area}--{year}-{by}-{pg}.html
            url = f'https://www.dushe06.com/show/{tid}-{enc_type}-{enc_area}--{enc_year}-{by_val}-{pg}.html'
        except Exception:
            # Fallback URL
            url = f'https://www.dushe06.com/show/{tid}-----2-{pg}.html'

        print(url)
        rsp = self.fetch(url, headers=self.header)
        if not rsp or not rsp.text:
            return result
        
        # Fix encoding - use lxml directly to avoid base class encoding problems
        try:
            if hasattr(rsp, 'content'):
                parser = etree.HTMLParser(encoding='utf-8', recover=True, remove_blank_text=True)
                root = etree.HTML(rsp.content, parser=parser)
            else:
                parser = etree.HTMLParser(encoding='utf-8', recover=True, remove_blank_text=True)
                root = etree.HTML(rsp.text.encode('utf-8', errors='ignore'), parser=parser)
        except Exception:
            root = self.html(rsp.text)
        videos = []
        
        try:
            # Extract video items: <a href="/detail/xxx.html" class="v-item">
            items = root.xpath("//a[@class='v-item']")
            for item in items:
                try:
                    # Extract href
                    hrefs = item.xpath('./@href')
                    if not hrefs:
                        continue
                    href = hrefs[0]
                    
                    # Extract ID from /detail/54125.html
                    m = re.search(r'/detail/(\d+)\.html', href)
                    if not m:
                        continue
                    sid = m.group(1)
                    
                    # Extract title from nested div.v-item-title (not display:none)
                    title_nodes = item.xpath('.//div[@class="v-item-title" and not(contains(@style,"display: none"))]/text()')
                    title = title_nodes[0].strip() if title_nodes else ''
                    
                    # Extract image - second img tag with data-original or src
                    # Skip placeholder images
                    img_nodes = item.xpath('.//img[@class="lazy lazyload"]')
                    pic = ''
                    for img in img_nodes:
                        # Try data-original first
                        src = img.xpath('./@data-original')
                        if not src:
                            src = img.xpath('./@src')
                        if src:
                            img_url = src[0]
                            # Skip placeholder
                            if 'logo_placeholder' not in img_url:
                                # Handle relative URLs
                                if img_url.startswith('/'):
                                    pic = 'https://vres.mgdnka.cn' + img_url
                                elif img_url.startswith('http'):
                                    pic = img_url
                                break
                    
                    # Extract remarks from v-item-bottom span
                    remark_nodes = item.xpath('.//div[@class="v-item-bottom"]//span/text()')
                    remark = remark_nodes[0].strip() if remark_nodes else ''
                    
                    # Extract rating from v-item-top-left span
                    rating_nodes = item.xpath('.//div[@class="v-item-top-left"]//span/text()')
                    if rating_nodes:
                        remark = rating_nodes[0].strip() + ' ' + remark if remark else rating_nodes[0].strip()
                    
                    videos.append({
                        "vod_id": sid,
                        "vod_name": title,
                        "vod_pic": pic,
                        "vod_remarks": remark.strip()
                    })
                except Exception:
                    continue
        except Exception:
            pass
        
        result['list'] = videos
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        return result

    def _create_fallback_vod(self, tid, error_msg):
        """Create a fallback VOD entry when extraction fails"""
        return {
            'list': [{
                'vod_id': tid,
                'vod_name': f'加载失败: {error_msg}',
                'vod_pic': '',
                'vod_content': f'无法加载视频详情。错误: {error_msg}',
                'vod_play_from': '毒舌电影',
                'vod_play_url': f'错误${f"https://www.dushe06.com/detail/{tid}.html"}'
            }]
        }
    
    def detailContent(self, ids):
        print(f'[dushe] ===== detailContent called =====')
        print(f'[dushe] ids parameter: {ids}')
        print(f'[dushe] ids type: {type(ids)}')
        
        try:
            if not ids:
                print(f'[dushe] ERROR: ids is empty')
                return {'list': []}
            
            tid = str(ids[0]).strip()
            
            # Check if this is a debug entry - return the stored debug info
            if tid.startswith('debug_'):
                print(f'[dushe] Debug entry clicked')
                # Return a generic debug message since we can't pass the actual debug_info through
                # The real debug info should be visible in the search results vod_content
                return {
                    'list': [{
                        'vod_id': tid,
                        'vod_name': '🔍 搜索调试信息',
                        'vod_pic': 'https://via.placeholder.com/300x400/FF0000/FFFFFF?text=DEBUG',
                        'vod_content': '⚠️ 调试信息应该已经显示在搜索结果页面\n\n如果您看到这个页面，说明:\n1. 搜索功能遇到了问题\n2. 详细的调试信息应该在上一页显示\n\n请返回搜索结果页查看完整的调试信息，包括:\n• 失败的具体步骤\n• 错误信息\n• Token状态\n• 响应长度\n• 找到的项目数\n• 提取的视频数\n\n如果需要更详细的信息，请查看FongMi应用日志。',
                        'vod_play_from': '提示',
                        'vod_play_url': '返回搜索页$https://www.dushe06.com'
                    }]
                }
            
            url = f'https://www.dushe06.com/detail/{tid}.html'
            print(f'[dushe] Fetching URL: {url}')
            
            try:
                rsp = self.fetch(url, headers=self.header)
                if not rsp or not rsp.text:
                    print(f'[dushe] ERROR: Failed to fetch detail page')
                    return self._create_fallback_vod(tid, '获取页面失败')
                
                print(f'[dushe] Fetch successful, content length: {len(rsp.text)}')
                
                # Fix encoding issues - use lxml directly to avoid base class encoding problems
                try:
                    # Get raw bytes and parse directly with lxml
                    if hasattr(rsp, 'content'):
                        # Parse bytes directly - lxml handles encoding better
                        parser = etree.HTMLParser(encoding='utf-8', recover=True, remove_blank_text=True)
                        root = etree.HTML(rsp.content, parser=parser)
                        print(f'[dushe] HTML parsed with lxml directly from bytes')
                    else:
                        # Fallback to text if content not available
                        html_text = rsp.text.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
                        parser = etree.HTMLParser(encoding='utf-8', recover=True, remove_blank_text=True)
                        root = etree.HTML(html_text, parser=parser)
                        print(f'[dushe] HTML parsed with lxml from text')
                except Exception as decode_err:
                    print(f'[dushe] lxml parsing error: {str(decode_err)}')
                    # Last resort: try base class method
                    try:
                        root = self.html(rsp.text)
                        print(f'[dushe] Fallback to self.html() succeeded')
                    except Exception as fallback_err:
                        print(f'[dushe] Fallback also failed: {str(fallback_err)}')
                        root = None
                
                if root is None:
                    print(f'[dushe] ERROR: Failed to parse HTML')
                    return self._create_fallback_vod(tid, '解析HTML失败')
                
                print(f'[dushe] HTML parsed successfully')
            except Exception as e:
                print(f'[dushe] ERROR in fetch/parse: {str(e)}')
                import traceback
                traceback.print_exc()
                return self._create_fallback_vod(tid, f'异常: {str(e)}')
        except Exception as e:
            print(f'[dushe] FATAL ERROR in detailContent: {str(e)}')
            import traceback
            traceback.print_exc()
            return {'list': []}
        
        # Title - from div.detail-title strong (not display:none)
        try:
            title_nodes = root.xpath('//div[@class="detail-title"]/strong[not(contains(text(),"kekys") or contains(text(),"𝕜𝕜𝕪𝕤"))]/text()')
            title = title_nodes[0].strip() if title_nodes else ""
        except Exception:
            title = ""
        
        # Picture
        pic = ""
        try:
            pics = root.xpath('//div[@class="detail-pic"]//img/@src')
            if not pics:
                pics = root.xpath('//div[@class="detail-pic"]//img/@data-original')
            if pics:
                pic = pics[0]
                if pic.startswith('/'):
                    pic = 'https://vres.mgdnka.cn' + pic
        except Exception:
            pic = ""
        
        # Description
        detail = ""
        try:
            detail_nodes = root.xpath('//div[@class="detail-desc"]//p/text()')
            if detail_nodes:
                detail = '\n'.join([d.strip() for d in detail_nodes if d.strip()])
        except Exception:
            detail = ""
        
        # Score - from豆瓣 tag
        douban = ""
        try:
            score_nodes = root.xpath('//div[@class="detail-tags"]//a[contains(@href,"show")]/text()')
            for s in score_nodes:
                if '分' not in s:
                    continue
                # Extract number from text like "9.4分" or just year
                if re.match(r'^\d{4}$', s.strip()):
                    continue
                douban = s.strip()
                break
        except Exception:
            pass
        
        # Remarks
        remarks = ""
        try:
            remark_nodes = root.xpath('//div[@class="detail-info-row"][contains(.//div,"备注")]//div[@class="detail-info-row-main"]/text()')
            if remark_nodes:
                remarks = remark_nodes[0].strip()
        except Exception:
            pass
        
        # Director
        director = ""
        try:
            dir_nodes = root.xpath('//div[@class="detail-info-row"][contains(.//div,"导演")]//div[@class="detail-info-row-main"]//a/text()')
            if dir_nodes:
                director = '/'.join([d.strip() for d in dir_nodes])
        except Exception:
            pass
        
        # Actor
        actor = ""
        try:
            actor_nodes = root.xpath('//div[@class="detail-info-row"][contains(.//div,"演员")]//div[@class="detail-info-row-main"]//a/text()')
            if actor_nodes:
                actor = '/'.join([a.strip() for a in actor_nodes])
        except Exception:
            pass
        
        # Year
        year = ""
        try:
            year_nodes = root.xpath('//div[@class="detail-info-row"][contains(.//div,"首映")]//div[@class="detail-info-row-main"]/text()')
            if year_nodes:
                year = year_nodes[0].strip()
        except Exception:
            pass
        
        # Type/Genre from tags
        type_name = ""
        try:
            tag_nodes = root.xpath('//div[@class="detail-tags"]//a[@class="detail-tags-item"]/text()')
            if tag_nodes:
                # Filter out year
                tags = [t.strip() for t in tag_nodes if not re.match(r'^\d{4}$', t.strip())]
                type_name = '/'.join(tags)
        except Exception:
            pass
        
        vod = {
            "vod_id": tid,
            "vod_name": title,
            "vod_pic": pic,
            "type_name": type_name,
            "vod_year": year,
            "vod_area": "",
            "vod_remarks": remarks,
            "vod_actor": actor,
            "vod_director": director,
            "vod_douban_score": douban,
            "vod_content": detail
        }
        
        # Extract play sources and episodes
        playFrom = []
        playList = []
        
        try:
            # Find all source tabs: div.swiper-slide.source-swiper-slide
            source_tabs = root.xpath('//div[contains(@class,"source-swiper-slide")]//a[@class="source-item"]')
            # Find all episode lists: div.episode-list
            episode_lists = root.xpath('//div[@class="episode-list"]')
            
            print(f'[dushe] Found {len(source_tabs)} source tabs, {len(episode_lists)} episode lists')
            
            # Match sources with episode lists
            for idx, source_tab in enumerate(source_tabs):
                try:
                    # Extract source name from span.source-item-label
                    source_name_nodes = source_tab.xpath('.//span[@class="source-item-label"]/text()')
                    source_name = source_name_nodes[0].strip() if source_name_nodes else f"线路{idx+1}"
                    
                    # Get corresponding episode list
                    if idx < len(episode_lists):
                        episode_list = episode_lists[idx]
                        # Extract all episode links
                        episode_links = episode_list.xpath('.//a[@class="episode-item"]')
                        vodItems = []
                        
                        for ep_link in episode_links:
                            try:
                                ep_href = ep_link.xpath('./@href')
                                ep_name = ep_link.xpath('./text()')
                                
                                if ep_href and ep_name:
                                    href = ep_href[0]
                                    name = ep_name[0].strip()
                                    
                                    # Extract play ID from /play/54125-32-25552.html
                                    m = re.search(r'/play/([^.]+)\.html', href)
                                    if m:
                                        play_id = m.group(1)
                                        vodItems.append(f"{name}${play_id}")
                            except Exception as e:
                                print(f'[dushe] Error extracting episode: {str(e)}')
                                continue
                        
                        if vodItems:
                            playFrom.append(source_name)
                            playList.append('#'.join(vodItems))
                            print(f'[dushe] Source {idx+1} "{source_name}": {len(vodItems)} episodes')
                except Exception as e:
                    print(f'[dushe] Error processing source {idx}: {str(e)}')
                    continue
        except Exception as e:
            print(f'[dushe] Error in play extraction: {str(e)}')
        
        # Ensure we have play data
        if not playFrom or not playList:
            print(f'[dushe] WARNING: No play data extracted, using fallback')
            playFrom = ['毒舌电影']
            playList = [f'暂无播放源$https://www.dushe06.com/detail/{tid}.html']
        
        vod['vod_play_from'] = '$$$'.join(playFrom)
        vod['vod_play_url'] = '$$$'.join(playList)
        
        print(f'[dushe] detailContent result:')
        print(f'  - Title: {vod["vod_name"]}')
        print(f'  - Sources: {len(playFrom)}')
        print(f'  - vod_play_from: {vod["vod_play_from"][:100]}')
        print(f'  - vod_play_url length: {len(vod["vod_play_url"])}')
        
        result = {
            'list': [vod]
        }
        return result

    def searchContent(self, key, quick, pg='1'):
        # Call the actual search implementation
        print(f'[dushe] searchContent called: key={key}, quick={quick}, pg={pg}')
        return self.searchContentPage(key, quick, pg)
    
    def searchContentPage(self, key, quick, pg='1'):
        # Search requires a token from the homepage
        print(f'[dushe] ===== searchContentPage called =====')
        print(f'[dushe] key: {key}, pg: {pg}')
        
        debug_info = {
            'step': 'init',
            'error': None,
            'token': None,
            'url': None,
            'response_length': 0,
            'items_found': 0,
            'videos_extracted': 0
        }
        
        try:
            # Use requests directly instead of self.fetch() to avoid base class interference
            import requests
            import time
            
            # Get homepage to extract search token
            debug_info['step'] = 'fetching_homepage'
            print(f'[dushe] Fetching homepage for token...')
            
            # Add delay before homepage fetch
            time.sleep(0.5)
            
            try:
                home_rsp = requests.get('https://www.dushe06.com', headers=self.header, timeout=15, verify=False)
            except Exception as fetch_err:
                debug_info['error'] = f'Homepage fetch error: {type(fetch_err).__name__}'
                print(f'[dushe] HOMEPAGE FETCH ERROR: {str(fetch_err)}')
                return self._create_debug_result(key, debug_info)
            
            if not home_rsp or not home_rsp.text:
                debug_info['error'] = 'Empty homepage response'
                print(f'[dushe] ERROR: {debug_info["error"]}')
                return self._create_debug_result(key, debug_info)
            
            # Extract token from search form
            debug_info['step'] = 'extracting_token'
            token = ''
            m = re.search(r'name="t"\s+value="([^"]+)"', home_rsp.text)
            if m:
                token = m.group(1)
                debug_info['token'] = token[:20] + '...' if len(token) > 20 else token
                print(f'[dushe] Token found: {token}')
            else:
                debug_info['error'] = 'Token not found in homepage'
                print(f'[dushe] WARNING: Token not found, proceeding without token')
            
            # Build search URL with token
            debug_info['step'] = 'building_url'
            url = f'https://www.dushe06.com/search?t={token}&k={quote_plus(key)}'
            if pg and pg != '1':
                url += f'&page={pg}'
            
            debug_info['url'] = url
            print(f'[dushe] Search URL: {url}')
            
            debug_info['step'] = 'fetching_search'
            
            # Add delay between requests
            time.sleep(0.8)
            
            # Update Referer to homepage for search request
            search_headers = self.header.copy()
            search_headers['Referer'] = 'https://www.dushe06.com/'
            
            try:
                rsp = requests.get(url, headers=search_headers, timeout=15, verify=False)
            except Exception as fetch_err:
                debug_info['error'] = f'Search fetch error: {type(fetch_err).__name__}'
                print(f'[dushe] SEARCH FETCH ERROR: {str(fetch_err)}')
                return self._create_debug_result(key, debug_info)
            
            if not rsp or not rsp.text:
                debug_info['error'] = 'Empty search response'
                print(f'[dushe] ERROR: {debug_info["error"]}')
                return self._create_debug_result(key, debug_info)
            
            debug_info['response_length'] = len(rsp.text)
            print(f'[dushe] Search response length: {len(rsp.text)}')
            
            # Fix encoding - use lxml directly to avoid base class encoding problems
            debug_info['step'] = 'parsing_html'
            try:
                if hasattr(rsp, 'content'):
                    parser = etree.HTMLParser(encoding='utf-8', recover=True, remove_blank_text=True)
                    root = etree.HTML(rsp.content, parser=parser)
                else:
                    parser = etree.HTMLParser(encoding='utf-8', recover=True, remove_blank_text=True)
                    root = etree.HTML(rsp.text.encode('utf-8', errors='ignore'), parser=parser)
            except Exception as e:
                debug_info['error'] = f'HTML parsing error: {str(e)}'
                print(f'[dushe] lxml parsing error: {str(e)}, trying fallback')
                root = self.html(rsp.text)
            
            videos = []
            
            # Search uses different structure: a.search-result-item
            # Note: class attribute may have whitespace/newlines, so use contains()
            debug_info['step'] = 'extracting_items'
            items = root.xpath("//a[contains(@class, 'search-result-item')]")
            debug_info['items_found'] = len(items)
            print(f'[dushe] Found {len(items)} search result items')
            
            for idx, item in enumerate(items):
                try:
                    print(f'[dushe] Processing item {idx+1}...')
                    hrefs = item.xpath('./@href')
                    print(f'[dushe]   hrefs: {hrefs}')
                    if not hrefs:
                        print(f'[dushe]   SKIP: No href found')
                        continue
                    href = hrefs[0]
                    
                    m = re.search(r'/detail/(\d+)\.html', href)
                    if not m:
                        print(f'[dushe]   SKIP: href does not match pattern: {href}')
                        continue
                    sid = m.group(1)
                    print(f'[dushe]   ID: {sid}')
                    
                    # Title from div.title
                    title_nodes = item.xpath('.//div[@class="title"]/text()')
                    title = title_nodes[0].strip() if title_nodes else ''
                    print(f'[dushe]   Title: {title}')
                    
                    if not title:
                        print(f'[dushe]   SKIP: No title found')
                        continue
                    
                    # Image from search-result-item-pic img
                    # Note: There are 2 img tags - first has real image in data-original, second is placeholder
                    img_nodes = item.xpath('.//div[@class="search-result-item-pic"]//img[@class="lazy lazyload"]')
                    pic = ''
                    for img in img_nodes:
                        # Prioritize data-original over src (src is always placeholder)
                        data_orig = img.xpath('./@data-original')
                        if data_orig:
                            img_url = data_orig[0]
                            # Skip placeholder images
                            if 'logo_placeholder' not in img_url and not img_url.startswith('data:'):
                                if img_url.startswith('/'):
                                    pic = 'https://vres.mgdnka.cn' + img_url
                                elif img_url.startswith('http'):
                                    pic = img_url
                                break
                    
                    # Tags as remarks (year/region/genre)
                    tag_nodes = item.xpath('.//div[@class="tags"]//span/text()')
                    remark = '/'.join([t.strip() for t in tag_nodes if t.strip()]) if tag_nodes else ''
                    
                    video_item = {
                        "vod_id": sid,
                        "vod_name": title,
                        "vod_pic": pic,
                        "vod_remarks": remark
                    }
                    videos.append(video_item)
                    print(f'[dushe]   ✓ Added: {title}')
                    
                except Exception as e:
                    print(f'[dushe] ✗ Error extracting item {idx}: {str(e)}')
                    import traceback
                    traceback.print_exc()
                    continue
            
            debug_info['videos_extracted'] = len(videos)
            debug_info['step'] = 'completed'
            print(f'[dushe] Total extracted: {len(videos)} videos')
            
            # If no videos extracted, return debug info
            if len(videos) == 0:
                debug_info['error'] = 'No videos extracted from items'
                return self._create_debug_result(key, debug_info)
            
            return {'list': videos}
        except Exception as e:
            debug_info['step'] = 'exception'
            debug_info['error'] = str(e)
            print(f'[dushe] FATAL ERROR in searchContentPage: {str(e)}')
            import traceback
            traceback.print_exc()
            return self._create_debug_result(key, debug_info)
    
    def _create_debug_result(self, key, debug_info):
        """Create a debug result entry that shows what went wrong"""
        error_msg = debug_info.get('error', 'Unknown error')
        step = debug_info.get('step', 'unknown')
        
        # Build detailed debug content for vod_content
        debug_content = f"🔍 搜索调试信息\n\n"
        debug_content += f"搜索关键词: {key}\n"
        debug_content += f"失败步骤: {step}\n"
        debug_content += f"错误信息: {error_msg}\n\n"
        debug_content += f"=== 详细信息 ===\n"
        if debug_info.get('token'):
            debug_content += f"Token: {debug_info['token']}\n"
        if debug_info.get('url'):
            debug_content += f"URL: {debug_info['url']}\n"
        debug_content += f"响应长度: {debug_info.get('response_length', 0)} bytes\n"
        debug_content += f"找到项目数: {debug_info.get('items_found', 0)}\n"
        debug_content += f"提取视频数: {debug_info.get('videos_extracted', 0)}\n\n"
        debug_content += f"=== 可能原因 ===\n"
        if step == 'fetching_homepage':
            debug_content += "• 无法连接到网站首页\n"
            debug_content += "• 网络连接问题\n"
            debug_content += "• SSL证书验证失败\n"
        elif step == 'extracting_token':
            debug_content += "• 网站HTML结构已改变\n"
            debug_content += "• Token字段名称已更新\n"
        elif step == 'fetching_search':
            debug_content += "• 搜索请求失败\n"
            debug_content += "• Token可能已过期\n"
        elif step == 'parsing_html':
            debug_content += "• HTML解析失败\n"
            debug_content += "• 编码问题\n"
        elif step == 'extracting_items':
            debug_content += "• XPath选择器不匹配\n"
            debug_content += "• 网站HTML结构已改变\n"
        elif step == 'completed':
            debug_content += "• 找到了项目但无法提取数据\n"
            debug_content += "• 标题或ID字段为空\n"
            debug_content += "• 检查日志查看跳过原因\n"
        
        debug_content += f"\n请查看FongMi日志获取更多详细信息"
        
        # Create a compact remarks string with key info
        remarks = f"步骤:{step} | "
        remarks += f"项目:{debug_info.get('items_found', 0)} | "
        remarks += f"提取:{debug_info.get('videos_extracted', 0)}"
        
        print(f'[dushe] Creating debug result for step: {step}')
        print(f'[dushe] Debug info: {debug_info}')
        
        return {
            'list': [{
                'vod_id': 'debug_0',
                'vod_name': f'❌ 搜索失败: {key}',
                'vod_pic': 'https://via.placeholder.com/300x400/FF0000/FFFFFF?text=DEBUG',
                'vod_remarks': remarks,
                'vod_content': debug_content,
                'vod_play_from': '调试信息',
                'vod_play_url': '查看上方详情$https://www.dushe06.com'
            }]
        }

    def playerContent(self, flag, id, vipFlags):
        """
        Return play page URL with parse=1 to let TVBox resolve the playable URL
        """
        url = f'https://www.dushe06.com/play/{id}.html'
        result = {
            "parse": 1,
            "playUrl": "",
            "url": url,
            "header": self.header
        }
        return result

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def localProxy(self, param):
        action = {
            'url': '',
            'header': '',
            'param': '',
            'type': 'string',
            'after': ''
        }
        return [200, "video/MP2T", action, ""]

    config = {
        "filter": {
            "1": [  # 电影
                {
                    "key": "class",
                    "name": "类型",
                    "value": [
                        {"n": "全部", "v": ""},
                        {"n": "恐怖", "v": "恐怖"},
                        {"n": "惊悚", "v": "惊悚"},
                        {"n": "爱情", "v": "爱情"},
                        {"n": "同性", "v": "同性"},
                        {"n": "喜剧", "v": "喜剧"},
                        {"n": "动画", "v": "动画"},
                        {"n": "短片", "v": "短片"}
                    ]
                },
                {
                    "key": "area",
                    "name": "地区",
                    "value": [
                        {"n": "全部", "v": ""},
                        {"n": "日本", "v": "日本"},
                        {"n": "韩国", "v": "韩国"},
                        {"n": "美国", "v": "美国"},
                        {"n": "英国", "v": "英国"},
                        {"n": "法国", "v": "法国"},
                        {"n": "德国", "v": "德国"},
                        {"n": "意大利", "v": "意大利"},
                        {"n": "巴西", "v": "巴西"},
                        {"n": "瑞典", "v": "瑞典"}
                    ]
                },
                {"key": "year", "name": "年份", "value": []},
                {
                    "key": "by",
                    "name": "排序",
                    "value": [
                        {"n": "最新", "v": "最新"},
                        {"n": "最热", "v": "最热"},
                        {"n": "评分", "v": "评分"}
                    ]
                }
            ],
            "2": [  # 电视剧
                {
                    "key": "class",
                    "name": "类型",
                    "value": [
                        {"n": "全部", "v": ""},
                        {"n": "恐怖", "v": "恐怖"},
                        {"n": "惊悚", "v": "惊悚"},
                        {"n": "爱情", "v": "爱情"},
                        {"n": "同性", "v": "同性"},
                        {"n": "喜剧", "v": "喜剧"},
                        {"n": "动画", "v": "动画"}
                    ]
                },
                {
                    "key": "area",
                    "name": "地区",
                    "value": [
                        {"n": "全部", "v": ""},
                        {"n": "日本", "v": "日本"},
                        {"n": "韩国", "v": "韩国"},
                        {"n": "美国", "v": "美国"},
                        {"n": "英国", "v": "英国"},
                        {"n": "法国", "v": "法国"},
                        {"n": "德国", "v": "德国"},
                        {"n": "意大利", "v": "意大利"},
                        {"n": "巴西", "v": "巴西"},
                        {"n": "瑞典", "v": "瑞典"}
                    ]
                },
                {"key": "year", "name": "年份", "value": []},
                {
                    "key": "by",
                    "name": "排序",
                    "value": [
                        {"n": "最新", "v": "最新"},
                        {"n": "最热", "v": "最热"},
                        {"n": "评分", "v": "评分"}
                    ]
                }
            ],
            "3": [  # 动漫
                {
                    "key": "class",
                    "name": "类型",
                    "value": [
                        {"n": "全部", "v": ""},
                        {"n": "同性", "v": "同性"},
                        {"n": "恐怖", "v": "恐怖"},
                        {"n": "搞笑", "v": "搞笑"}
                    ]
                },
                {
                    "key": "area",
                    "name": "地区",
                    "value": [
                        {"n": "全部", "v": ""},
                        {"n": "日本", "v": "日本"},
                        {"n": "韩国", "v": "韩国"},
                        {"n": "美国", "v": "美国"},
                        {"n": "其他", "v": "其他"}
                    ]
                },
                {"key": "year", "name": "年份", "value": []},
                {
                    "key": "by",
                    "name": "排序",
                    "value": [
                        {"n": "最新", "v": "最新"},
                        {"n": "最热", "v": "最热"},
                        {"n": "评分", "v": "评分"}
                    ]
                }
            ],
            "4": [  # 纪录片
                {
                    "key": "class",
                    "name": "类型",
                    "value": [
                        {"n": "全部", "v": ""},
                        {"n": "同性", "v": "同性"},
                        {"n": "记录", "v": "记录"},
                        {"n": "冒险", "v": "冒险"}
                    ]
                },
                {
                    "key": "area",
                    "name": "地区",
                    "value": [
                        {"n": "全部", "v": ""},
                        {"n": "美国", "v": "美国"},
                        {"n": "英国", "v": "英国"},
                        {"n": "日本", "v": "日本"},
                        {"n": "韩国", "v": "韩国"},
                        {"n": "法国", "v": "法国"}
                    ]
                },
                {"key": "year", "name": "年份", "value": []},
                {
                    "key": "by",
                    "name": "排序",
                    "value": [
                        {"n": "最新", "v": "最新"},
                        {"n": "最热", "v": "最热"},
                        {"n": "评分", "v": "评分"}
                    ]
                }
            ]
        }
    }

    header = {
        "Referer": "https://www.dushe06.com",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "sec-ch-ua": '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Connection": "keep-alive"
    }
