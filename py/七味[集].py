import sys
import json
import re
from urllib.parse import quote, unquote, urlparse
import requests
from lxml import etree
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def getName(self):
        return "七味"

    def init(self, extend=""):
        self.hosts = [
            'https://www.pcmp4.com',
            'https://www.qwnull.com',
            'https://www.qwmkv.com',
            'https://www.qwfilm.com',
            'https://www.qnmp4.com',
            'https://www.qnnull.com',
            'https://www.qnhot.com'
        ]
        self.currentHostIndex = 0
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        self.timeout = 5000
    
    def getCurrentHost(self):
        return self.hosts[self.currentHostIndex]
    
    def nextHost(self):
        self.currentHostIndex = (self.currentHostIndex + 1) % len(self.hosts)
        return self.getCurrentHost()
    
    def _parse_dom(self, response):
        try:
            if hasattr(response, 'content'):
                return etree.HTML(response.content)
            return etree.HTML(response.text)
        except Exception as e:
            return None
    
    def _normalize_url(self, url):
        if not url:
            return url
        if url.startswith('//'):
            return 'https:' + url
        if url.startswith('/'):
            return self.getCurrentHost() + url
        return url
    
    def fetch(self, url, headers=None, timeout=None):
        try:
            response = requests.get(url, headers=headers or self.headers, timeout=timeout or self.timeout)
            response.encoding = response.apparent_encoding
            return response
        except Exception as e:
            next_url = url.replace(self.getCurrentHost(), self.nextHost())
            try:
                response = requests.get(next_url, headers=headers or self.headers, timeout=timeout or self.timeout)
                response.encoding = response.apparent_encoding
                return response
            except Exception as e2:
                return None
    
    def homeContent(self, filter):
        result = {
            'class': [
                {'type_name': '电影', 'type_id': '1'},
                {'type_name': '剧集', 'type_id': '2'},
                {'type_name': '综艺', 'type_id': '3'},
                {'type_name': '动漫', 'type_id': '4'},
                {'type_name': '短剧', 'type_id': '30'}
            ]
        }
        return result
    
    def homeVideoContent(self):
        result = []
        try:
            response = self.fetch(self.getCurrentHost(), headers=self.headers)
            if not response or not response.text:
                return {'list': result}
            html = self._parse_dom(response)
            if html is None:
                return {'list': result}

            items = html.xpath('//ul[contains(@class, "content-list")]/li')[:30]
            for item in items:
                a_tag = item.xpath('.//div[@class="li-img"]/a')[0]
                href = a_tag.get('href', '')
                title = a_tag.get('title', '')
                img = str(a_tag.xpath('.//img/@src')[0]) if a_tag.xpath('.//img/@src') else ''
                desc = str(item.xpath('.//div[@class="tag"]/text()')[0]).strip() if item.xpath('.//div[@class="tag"]/text()') else ''
                if title and href:
                    vod_id = re.search(r'/mv/(\d+)\.html', href).group(1) if re.search(r'/mv/(\d+)\.html', href) else ''
                    result.append({
                        'vod_id': vod_id,
                        'vod_name': title,
                        'vod_pic': self._normalize_url(img),
                        'vod_remarks': desc
                    })
        except Exception as e:
            pass
        return {'list': result}
    
    def categoryContent(self, tid, pg, filter, extend):
        result = {'list': [], 'page': pg, 'pagecount': 9999, 'limit': 20, 'total': 999999}
        try:
            url = f'/vt/{tid}.html?page={pg}'
            url = self._normalize_url(url)      
            response = self.fetch(url, headers=self.headers)
            if not response or not response.text:
                return result
            html = self._parse_dom(response)
            if html is None:
                return result
            items = html.xpath('//ul[contains(@class, "content-list")]/li')
            for item in items[:30]:  # 限制每页返回30个结果
                try:
                    a_tag = item.xpath('.//div[@class="li-img"]/a')[0]
                    href = a_tag.get('href', '')
                    title = a_tag.get('title', '')
                    img = str(a_tag.xpath('.//img/@src')[0]) if a_tag.xpath('.//img/@src') else ''
                    desc = str(item.xpath('.//div[@class="tag"]/text()')[0]).strip() if item.xpath('.//div[@class="tag"]/text()') else ''
                    if title and href:
                        vod_id_match = re.search(r'/mv/(\d+)\.html', href)
                        vod_id = vod_id_match.group(1) if vod_id_match else ''
                        result['list'].append({
                            'vod_id': vod_id,
                            'vod_name': title,
                            'vod_pic': self._normalize_url(img),
                            'vod_remarks': desc
                        })
                except Exception:
                    continue
        except Exception as e:
            pass
        return result
    def detailContent(self, ids):
        if not ids:
            return {'list': []}
        try:
            input_param = str(ids[0]).strip()
            video_id_match = re.search(r'/mv/(\d+)\.html', input_param)
            video_id = video_id_match.group(1) if video_id_match else input_param
            input_url = f'{self.getCurrentHost()}/mv/{video_id}.html'
            if not video_id:
                raise Exception('无效的视频ID')
            response = self.fetch(input_url, headers=self.headers)
            if not response or not response.text:
                raise Exception('页面内容为空')
            html = response.text
            root = self._parse_dom(response)
            if root is None:
                raise Exception('页面解析失败')
            VOD = {
                'vod_name': '',
                'type_name': '',
                'vod_pic': '',
                'vod_content': '',
                'vod_remarks': '',
                'vod_year': '',
                'vod_area': '',
                'vod_actor': '',
                'vod_director': '',
                'vod_play_from': '',
                'vod_play_url': ''
            }
            h1_element = root.xpath('.//div[@class="main-ui-meta"]/h1')[0]
            h1_text = ''.join(map(str, h1_element.xpath('.//text()'))).strip()
            year_match = re.search(r'\((\d{4})\)', h1_text)
            if year_match:
                VOD['vod_year'] = year_match.group(1)
                VOD['vod_name'] = re.sub(r'\s*\(\d{4}\)', '', h1_text).strip()
            else:
                VOD['vod_name'] = h1_text
            VOD['vod_pic'] = str(root.xpath('.//div[@class="img"]/img/@src')[0]) if root.xpath('.//div[@class="img"]/img/@src') else ''
            meta_divs = root.xpath('.//div[@class="main-ui-meta"]/div')
            for div in meta_divs:
                text_content = ''.join(map(str, div.xpath('.//text()'))).strip()
                if '导演：' in text_content:
                    VOD['vod_director'] = '/'.join(map(str, div.xpath('.//a/text()')))
                elif '主演：' in text_content:
                    VOD['vod_actor'] = '/'.join(map(str, div.xpath('.//a/text()')))
                elif '类型：' in text_content:
                    VOD['type_name'] = '/'.join(map(str, div.xpath('.//a/text()')))
                elif '地区：' in text_content:
                    VOD['vod_area'] = '/'.join(map(str, div.xpath('.//a/text()')))
            otherbox = root.xpath('.//div[@class="otherbox"]')
            if otherbox:
                VOD['vod_remarks'] = ''.join(map(str, otherbox[0].xpath('.//text()'))).strip()
            content_element = root.xpath('.//div[@class="movie-introduce"]//p[@class="zkjj_a"]')
            if content_element:
                VOD['vod_content'] = ''.join(map(str, content_element[0].xpath('.//text()'))).strip()
            play_from = []
            play_url = []
            line_items = root.xpath('//div[@class="hd right"]/ul[@class="py-tabs"]/li')
            episode_containers = root.xpath('//div[@class="bd"]/ul[contains(@class, "player")]')
            for i in range(len(line_items)):
                line_item = line_items[i]
                line_text = ''.join(map(str, line_item.xpath('.//text()'))).strip()
                line_name = line_text.split('\n')[0].strip()
                line_name = re.sub(r'\d+', '', line_name).strip()
                line_name = line_name.replace(' ', '')
                if line_name and i < len(episode_containers):
                    play_from.append(line_name)
                    episode_items = episode_containers[i].xpath('.//a')
                    episode_list = []
                    for j, ep_item in enumerate(episode_items):
                        try:
                            ep_title = ''.join(map(str, ep_item.xpath('.//text()'))).strip()
                            href = ep_item.get('href', '')
                            line_num_match = re.search(r'/py/(\d+)-(\d+)-(\d+)\.html', href)
                            if line_num_match:
                                line_num = line_num_match.group(2)
                                episode_list.append(f"{ep_title}${video_id}|{line_num}|{j}")
                        except Exception:
                            continue
                    if not episode_list:
                        episode_list.append(f"正片${video_id}|{i+1}|0")
                    play_url.append('#'.join(episode_list))
            magnet_links = list(set(re.findall(r'magnet:\?[^&"\'\s]+', html) or []))
            if magnet_links:
                play_from.append('磁力下载')
                play_url.append('#'.join([f"磁力{i + 1}${link}" for i, link in enumerate(magnet_links)]))
            pan_regex = r'https?:\/\/(?:pan\.baidu\.com|pan\.quark\.cn|drive\.uc\.cn|cloud\.189\.cn|yun\.139\.com|alipan\.com|pan\.aliyun\.com|115\.com|115cdn\.com)\/[^"\'\s]+'
            pan_links = list(set(re.findall(pan_regex, html) or []))
            if pan_links:
                pan_types = {
                    'pan.baidu.com': '百度',
                    'pan.quark.cn': '夸克',
                    'drive.uc.cn': 'UC',
                    'cloud.189.cn': '天翼',
                    'yun.139.com': '移动',
                    'alipan.com': '阿里',
                    'pan.aliyun.com': '阿里',
                    '115.com': '115',
                    '115cdn.com': '115'
                }
                pan_links_by_type = {}
                for link in pan_links:
                    for domain, pan_type in pan_types.items():
                        if domain in link:
                            pan_links_by_type.setdefault(pan_type, []).append(link)
                            break
                for pan_type, links in pan_links_by_type.items():
                    play_from.append(f"{pan_type}网盘")
                    processed_links = [f"{pan_type}网盘{i + 1}$push://{link}" for i, link in enumerate(links)]
                    play_url.append('#'.join(processed_links))
            if not play_from:
                play_from = ['默认线路']
                play_url = [f"正片${video_id}|0|0"]
            VOD['vod_play_from'] = '$$$'.join(play_from)
            VOD['vod_play_url'] = '$$$'.join(play_url)
            VOD['vod_id'] = video_id
            return {'list': [VOD]}
        except Exception as e:
            return {'list': [{
                "vod_name": '加载失败',
                "type_name": '',
                "vod_pic": '',
                "vod_content": f'加载失败: {str(e)}',
                "vod_remarks": '请检查网络连接或配置是否正确',
                "vod_play_from": '默认线路',
                "vod_play_url": '正片$$0|0|0',
                "vod_id": '',
                "vod_director": '',
                "vod_actor": '',
                "vod_year": '',
                "vod_area": ''
            }]}
    
    def searchContent(self, key, quick, pg):
        results = []
        try:
            keyword = key.lower().strip()
            if not keyword:
                return {'list': results}
            home_response = self.fetch(self.getCurrentHost(), headers=self.headers)
            if not home_response or not home_response.text:
                return {'list': results}
            root = self._parse_dom(home_response)
            if root is None:
                return {'list': results}
            home_data = []
            content_list_items = root.xpath('//*[contains(@class, "content-list")]//li')
            home_data.extend(content_list_items)
            content_list_nth_items = root.xpath('//*[contains(@class, "content-list-nth")]//li')
            home_data.extend(content_list_nth_items)
            ul_items = root.xpath('//ul/li')
            home_data.extend(ul_items)
            seen_titles = set()
            for item in home_data:
                try:
                    a_tag = item.xpath('.//div[@class="li-img"]/a')[0] if item.xpath('.//div[@class="li-img"]/a') else None
                    if not a_tag:
                        continue
                    title = a_tag.get('title', '')
                    if not title:
                            h3_a = item.xpath('.//h3/a')
                            if h3_a:
                                title = h3_a[0].get('text', '') or h3_a[0].get('title', '') or str(h3_a[0].text) or ''
                    
                    if title and title not in seen_titles:
                        seen_titles.add(title)
                        if keyword in title.lower():
                            href = a_tag.get('href', '')
                            img = str(a_tag.xpath('.//img/@src')[0]) if a_tag.xpath('.//img/@src') else ''
                            desc = item.xpath('.//div[@class="tag"]/text()')[0].strip() if item.xpath('.//div[@class="tag"]/text()') else ''
                            vod_id_match = re.search(r'/mv/(\d+)\.html', href)
                            vod_id = vod_id_match.group(1) if vod_id_match else ''
                            results.append({
                                "vod_id": vod_id,
                                "vod_name": title,
                                "vod_pic": self._normalize_url(img),
                                "vod_remarks": desc
                            })
                except Exception:
                    continue
        except Exception:
            pass
        return {'list': results}
    
    def _getDefaultHeaders(self):
        return {**self.headers, "Referer": self.getCurrentHost()}
    def _isValidPanUrl(self, url):
        if not url or '</' in url or '/>' in url:
            return False
        pan_domains = ['pan.baidu.com', 'pan.baiduimg.com', 'pan.quark.cn', 'drive.uc.cn', 
                      'cloud.189.cn', 'yun.139.com', 'alipan.com', 'pan.aliyun.com', 
                      '115.com', '115cdn.com']
        return any(domain in url for domain in pan_domains)
    def playerContent(self, flag, id, vipFlags):
        try:
            if id.startswith('magnet:') or id.startswith('push://'):
                return {"parse": 0, "url": id}
            ids = id.split('|')
            if len(ids) == 3:
                videoId, lineIndex, episodeIndex = ids
                lineNumber = int(lineIndex) + 1
                episodeNumber = int(episodeIndex) + 1
                playUrl = f"{self.getCurrentHost()}/py/{videoId}-{lineNumber}-{episodeNumber}.html"
                return {"parse": 1, "url": playUrl, "header": self._getDefaultHeaders()}
            return {"parse": 1, "url": id, "header": self._getDefaultHeaders()}
        except Exception as error:
            return {"parse": 1, "url": id, "header": self._getDefaultHeaders()}

    def isVideoFormat(self, url):
        return False

    def localProxy(self, url):
        return False

    def manualVideoCheck(self, url):
        return False

