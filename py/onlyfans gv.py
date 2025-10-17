# -*- coding: utf-8 -*-
#author:嗷呜群fans&claude4⚡
import json
import sys
import re
import time
from base64 import b64encode
from urllib.parse import urljoin, urlencode
import requests
from pyquery import PyQuery as pq
from requests import Session
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def init(self, extend=""):
        try:
            self.proxies = json.loads(extend) if extend else {}
        except:
            self.proxies = {}
            
        if isinstance(self.proxies, dict) and 'proxy' in self.proxies and isinstance(self.proxies['proxy'], dict):
            self.proxies = self.proxies['proxy']
            
        fixed = {}
        for k, v in (self.proxies or {}).items():
            if isinstance(v, str) and not v.startswith('http'):
                fixed[k] = f'http://{v}'
            else:
                fixed[k] = v
        self.proxies = fixed
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:142.0) Gecko/20100101 Firefox/142.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.3,en;q=0.2',
            'Referer': 'https://gayvidsclub.com/',
            'Origin': 'https://gayvidsclub.com',
        }
        
        self.host = "https://gayvidsclub.com"
        self.session = Session()
        self.session.proxies.update(self.proxies)
        self.session.headers.update(self.headers)
        
    def getName(self):
        return "GayVidsClub"

    def isVideoFormat(self, url):
        return '.m3u8' in url or '.mp4' in url

    def manualVideoCheck(self):
        return True

    def destroy(self):
        pass

    def homeContent(self, filter):
        result = {}
        cateManual = {
            "最新": "/all-gay-porn/",
            "COAT": "/all-gay-porn/coat/",
            "MEN'S RUSH.TV": "/all-gay-porn/mens-rush-tv/",
            "HUNK CHANNEL": "/all-gay-porn/hunk-channel/",
            "KO": "/all-gay-porn/ko/",
            "EXFEED": "/all-gay-porn/exfeed/",
            "BRAVO!": "/all-gay-porn/bravo/",
            "STR8BOYS": "/all-gay-porn/str8boys/",
            "G-BOT": "/all-gay-porn/g-bot/"
        }
        classes = []
        filters = {}
        for k in cateManual:
            classes.append({
                'type_name': k,
                'type_id': cateManual[k]
            })
        result['class'] = classes
        result['filters'] = filters
        return result

    def homeVideoContent(self):
        data = self.fetchPage("/")
        vlist = self.getlist(data("article"))
        if not vlist:
            data = self.fetchPage('/all-gay-porn/')
            vlist = self.getlist(data("article"))
        return {'list': vlist}

    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        
        if pg == 1:
            url = tid
        else:
            url = f"{tid}page/{pg}/"
        
        data = self.fetchPage(url)
        vdata = self.getlist(data("article"))
        
        result['list'] = vdata
        return result

    def detailContent(self, ids):
        data = self.fetchPage(ids[0])
        
        title = data('h1').text().strip()
        
        iframe_src = None
        iframe_elem = data('iframe')
        if iframe_elem:
            iframe_src = iframe_elem.attr('src')
        
        if not iframe_src:
            scripts = data('script')
            for script in scripts.items():
                script_text = script.text()
                if 'iframe' in script_text and 'src' in script_text:
                    matches = re.findall(r'iframe.*?src=[\'"](https?://[^\'"]+)[\'"]', script_text)
                    if matches:
                        iframe_src = matches[0]
                        break
        
        # 获取海报图片 - 确保使用横版图片
        vod_pic = ""
        img_elem = data('img')
        if img_elem:
            vod_pic = img_elem.attr('src')
            # 确保使用横版海报图
            if vod_pic and ('poster' in vod_pic or 'cover' in vod_pic):
                # 已经是横版图片，不做处理
                pass
            elif vod_pic:
                # 尝试转换为横版图片
                vod_pic = self.ensure_horizontal_poster(vod_pic)
        
        vod = {
            'vod_name': title,
            'vod_content': 'GayVidsClub视频',
            'vod_tag': 'GayVidsClub',
            'vod_pic': vod_pic,  # 添加海报图片
            'vod_play_from': 'GayVidsClub',
            'vod_play_url': ''
        }
        
        play_lines = []
        
        if iframe_src:
            if not iframe_src.startswith('http'):
                iframe_src = urljoin(self.host, iframe_src)
            play_lines.append(f"直连${self.e64(iframe_src)}")
        
        play_lines.append(f"嗅探${self.e64(ids[0])}")
        
        if iframe_src:
            play_lines.append(f"阿里云盘解析${self.e64(iframe_src)}")
            
            play_lines.append(f"夸克网盘解析${self.e64(iframe_src)}")
            
            play_lines.append(f"115网盘解析${self.e64(iframe_src)}")
            
            play_lines.append(f"迅雷解析${self.e64(iframe_src)}")
            
            play_lines.append(f"PikPak解析${self.e64(iframe_src)}")
            
            play_lines.append(f"手机推送${iframe_src}")
        else:
            fallback_url = ids[0]
            play_lines.append(f"阿里云盘解析${self.e64(fallback_url)}")
            play_lines.append(f"夸克网盘解析${self.e64(fallback_url)}")
            play_lines.append(f"115网盘解析${self.e64(fallback_url)}")
            play_lines.append(f"迅雷解析${self.e64(fallback_url)}")
            play_lines.append(f"PikPak解析${self.e64(fallback_url)}")
            play_lines.append(f"手机推送${fallback_url}")
        
        vod['vod_play_url'] = '#'.join(play_lines)
        
        return {'list': [vod]}

    def searchContent(self, key, quick, pg="1"):
        if pg == 1:
            url = f"/?s={key}"
        else:
            url = f"/page/{pg}/?s={key}"
        
        data = self.fetchPage(url)
        return {'list': self.getlist(data("article")), 'page': pg}

    def playerContent(self, flag, id, vipFlags):
        url = self.d64(id)
        
        if "直连" in flag:
            return {'parse': 0, 'url': url, 'header': self.headers}
        elif "嗅探" in flag:
            return {'parse': 1, 'url': url, 'header': self.headers}
        elif "阿里云盘解析" in flag:
            return self.parse_with_aliyun(url)
        elif "夸克网盘解析" in flag:
            return self.parse_with_quark(url)
        elif "115网盘解析" in flag:
            return self.parse_with_115(url)
        elif "迅雷解析" in flag:
            return self.parse_with_thunder(url)
        elif "PikPak解析" in flag:
            return self.parse_with_pikpak(url)
        elif "手机推送" in flag:
            return {'parse': 1, 'url': url, 'header': self.headers}
        else:
            return {'parse': 1, 'url': url, 'header': self.headers}
    
    def fetchPage(self, url):
        if not url.startswith('http'):
            url = urljoin(self.host, url)
        response = self.session.get(url)
        return pq(response.text)
    
    def getlist(self, items):
        vlist = []
        for item in items.items():
            vid = item.find('a').attr('href')
            img = item.find('img').attr('src')
            name = item.find('h2').text()
            if not name:
                name = item.find('h3').text()
            
            # 确保使用横版海报图
            if img:
                if '?' in img:
                    img = img.split('?')[0]
                # 确保使用横版图片
                img = self.ensure_horizontal_poster(img)
            
            vlist.append({
                'vod_id': vid,
                'vod_name': name,
                'vod_pic': img,
                'vod_remarks': '',
                'style': {'type': 'rect', 'ratio': 1.33}  # 添加横版样式
            })
        return vlist
    
    def ensure_horizontal_poster(self, img_url):
        """
        确保使用横版海报图片
        """
        if not img_url:
            return img_url
            
        # 如果已经是横版图片，直接返回
        if 'poster' in img_url or 'cover' in img_url:
            return img_url
            
        # 尝试转换为横版图片
        # 常见的竖版图片标识
        vertical_indicators = ['thumb', 'vertical', 'portrait', 'square']
        
        # 常见的横版图片标识
        horizontal_indicators = ['poster', 'cover', 'horizontal', 'landscape']
        
        # 检查是否是竖版图片
        is_vertical = any(indicator in img_url for indicator in vertical_indicators)
        
        if is_vertical:
            # 尝试转换为横版图片
            for v_indicator in vertical_indicators:
                for h_indicator in horizontal_indicators:
                    if v_indicator in img_url:
                        # 替换竖版标识为横版标识
                        new_url = img_url.replace(v_indicator, h_indicator)
                        # 检查新URL是否有效
                        try:
                            response = self.session.head(new_url, timeout=3)
                            if response.status_code == 200:
                                return new_url
                        except:
                            continue
            
            # 如果无法转换，尝试添加横版参数
            if '?' in img_url:
                new_url = img_url + '&type=horizontal'
            else:
                new_url = img_url + '?type=horizontal'
                
            return new_url
        
        return img_url
    
    def e64(self, data):
        return b64encode(data.encode()).decode()
    
    def d64(self, data):
        from base64 import b64decode
        return b64decode(data).decode()
    
    def parse_with_aliyun(self, url):
        try:
            parse_result = {
                'parse': 1,
                'url': url,
                'header': self.headers,
                'parse_type': 'aliyun',
                'message': '使用阿里云盘解析服务'
            }
            return parse_result
        except Exception as e:
            return {'parse': 1, 'url': url, 'header': self.headers}
    
    def parse_with_quark(self, url):
        try:
            parse_result = {
                'parse': 1,
                'url': url,
                'header': self.headers,
                'parse_type': 'quark',
                'message': '使用夸克网盘解析服务'
            }
            return parse_result
        except Exception as e:
            return {'parse': 1, 'url': url, 'header': self.headers}
    
    def parse_with_115(self, url):
        try:
            parse_result = {
                'parse': 1,
                'url': url,
                'header': self.headers,
                'parse_type': '115',
                'message': '使用115网盘解析服务'
            }
            return parse_result
        except Exception as e:
            return {'parse': 1, 'url': url, 'header': self.headers}
    
    def parse_with_thunder(self, url):
        try:
            parse_result = {
                'parse': 1,
                'url': url,
                'header': self.headers,
                'parse_type': 'thunder',
                'message': '使用迅雷解析服务'
            }
            return parse_result
        except Exception as e:
            return {'parse': 1, 'url': url, 'header': self.headers}
    
    def parse_with_pikpak(self, url):
        try:
            parse_result = {
                'parse': 1,
                'url': url,
                'header': self.headers,
                'parse_type': 'pikpak',
                'message': '使用PikPak解析服务'
            }
            return parse_result
        except Exception as e:
            return {'parse': 1, 'url': url, 'header': self.headers}