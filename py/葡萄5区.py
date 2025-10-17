# coding=utf-8
#!/usr/bin/python
import sys
sys.path.append('..')
from base.spider import Spider
from urllib.parse import quote, unquote
import urllib.parse
import re
import requests
import base64
import json
import time
from lxml import etree
from urllib.parse import urljoin

class Spider(Spider):
    
    def getName(self):
        return "葡萄视频"
    
    def init(self, extend=""):
        self.host = "https://618413.xyz"
        self.api_host = "https://h5.xxoo168.org"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': self.host
        }
        # 图片解密密钥
        self.image_key = "2019ysapp7527"
        # 定义特殊分区ID列表
        self.special_categories = ['2', '12', '11', '16', '23', '14', '58', '34', '32', '61', '15', '13']
        self.log(f"葡萄视频爬虫初始化完成，主站: {self.host}")

    def decrypt_image_data(self, encrypted_data):
        """解密图片数据"""
        try:
            key_bytes = self.image_key.encode('utf-8')
            key_length = len(key_bytes)
            
            # 对前100个字节进行异或解密
            data_length = min(100, len(encrypted_data))
            decrypted_data = bytearray(encrypted_data)
            
            for i in range(data_length):
                decrypted_data[i] ^= key_bytes[i % key_length]
            
            return bytes(decrypted_data)
        except Exception as e:
            self.log(f"图片解密失败: {str(e)}")
            return encrypted_data

    def get_decrypted_image_url(self, encrypted_url):
        """获取解密后的图片URL（返回base64数据）"""
        try:
            self.log(f"开始解密图片: {encrypted_url}")
            
            # 设置图片请求的headers
            img_headers = {
                'User-Agent': self.headers['User-Agent'],
                'Referer': self.host,
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8'
            }
            
            # 下载加密的图片数据
            response = requests.get(encrypted_url, headers=img_headers, timeout=10, verify=False)
            if response.status_code != 200:
                self.log(f"图片下载失败: {response.status_code}")
                return None
            
            # 解密图片数据
            encrypted_data = response.content
            decrypted_data = self.decrypt_image_data(encrypted_data)
            
            # 将解密后的数据转换为base64
            base64_data = base64.b64encode(decrypted_data).decode('utf-8')
            
            # 检测图片格式
            if decrypted_data.startswith(b'\xff\xd8\xff'):
                mime_type = 'image/jpeg'
            elif decrypted_data.startswith(b'\x89PNG\r\n\x1a\n'):
                mime_type = 'image/png'
            elif decrypted_data.startswith(b'GIF8'):
                mime_type = 'image/gif'
            else:
                mime_type = 'image/jpeg'  # 默认JPEG
            
            return f"data:{mime_type};base64,{base64_data}"
            
        except Exception as e:
            self.log(f"图片解密处理失败: {str(e)}")
            return None

    def html(self, content):
        """将HTML内容转换为可查询的对象"""
        try:
            return etree.HTML(content)
        except:
            self.log("HTML解析失败")
            return None

    def regStr(self, pattern, string, index=1):
        """正则表达式提取字符串"""
        try:
            match = re.search(pattern, string, re.IGNORECASE)
            if match and len(match.groups()) >= index:
                return match.group(index)
        except:
            pass
        return ""

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def localProxy(self, params):
        try:
            url=unquote(params['imgu'])
            img_headers = {
                'User-Agent': self.headers['User-Agent'],
                'Referer': self.host,
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8'
            }

            # 下载加密的图片数据
            response = requests.get(url, headers=img_headers, timeout=10, verify=False)
            if response.status_code != 200:
                self.log(f"图片下载失败: {response.status_code}")
                raise Exception("图片下载失败")

            # 解密图片数据
            encrypted_data = response.content
            decrypted_data = self.decrypt_image_data(encrypted_data)
            return [200,"image/jpeg",decrypted_data]
        except Exception as e:
            self.log(f"获取图片URL出错: {str(e)}")
            return [404,"",""]

    def homeContent(self, filter):
        """获取首页内容和分类"""
        result = {}
        # 分类定义
        classes = [
            {'type_id': '618413.xyz_2', 'type_name': '全部'},
            {'type_id': '618413.xyz_12', 'type_name': '韩国'},
            {'type_id': '618413.xyz_11', 'type_name': '欧美'},
            {'type_id': '618413.xyz_16', 'type_name': '无码'},
            {'type_id': '618413.xyz_23', 'type_name': '直播'},
            {'type_id': '618413.xyz_14', 'type_name': '字幕'},
            {'type_id': '618413.xyz_58', 'type_name': '传媒'},
            {'type_id': '618413.xyz_34', 'type_name': '探花'},
            {'type_id': '618413.xyz_32', 'type_name': '网黄'},
            {'type_id': '618413.xyz_61', 'type_name': 'jk'},
            {'type_id': '618413.xyz_15', 'type_name': '国产'},
            {'type_id': '618413.xyz_13', 'type_name': '热门'}
        ]
        result['class'] = classes
        
        try:
            rsp = self.fetch(self.host, headers=self.headers)
            if not rsp or rsp.status_code != 200:
                self.log("首页请求失败")
                result['list'] = []
                return result
                
            doc = self.html(rsp.text)
            if not doc:
                self.log("首页HTML解析失败")
                result['list'] = []
                return result
                
            videos = self._get_videos(doc, limit=20)
            result['list'] = videos
        except Exception as e:
            self.log(f"首页获取出错: {str(e)}")
            result['list'] = []
        return result

    def homeVideoContent(self):
        """分类定义 - 兼容性方法"""
        return self.homeContent(False)

    def categoryContent(self, tid, pg, filter, extend):
        """分类内容 - 修复版"""
        try:
            domain, type_id = tid.split('_')
            url = f"https://{domain}/index.php/vod/type/id/{type_id}.html"
            if pg and pg != '1':
                url = url.replace('.html', f'/page/{pg}.html')
                
            self.log(f"访问分类URL: {url}")
            rsp = self.fetch(url, headers=self.headers)
            if not rsp or rsp.status_code != 200:
                self.log("分类页面请求失败")
                return {'list': []}
                
            doc = self.html(rsp.text)
            if not doc:
                self.log("分类页面HTML解析失败")
                return {'list': []}
                
            videos = self._get_videos(doc, category_id=type_id, limit=20)
            
            # 提取分页信息
            pagecount = self._extract_pagecount(doc, rsp.text)
            current_page = int(pg)
            
            return {
                'list': videos,
                'page': current_page,
                'pagecount': pagecount,
                'limit': 20,
                'total': pagecount * 20
            }
        except Exception as e:
            self.log(f"分类内容获取出错: {str(e)}")
            return {'list': []}

    def searchContent(self, key, quick, pg="1"):
        """搜索功能 - 修复版"""
        try:
            # 根据您提供的URL格式构造搜索URL
            search_url = f"{self.host}/index.php/vod/type/id/2/wd/{urllib.parse.quote(key)}/page/{pg}.html"
            
            self.log(f"搜索URL: {search_url}")
            
            # 添加随机延时避免被封
            time.sleep(0.5)
            
            rsp = self.fetch(search_url, headers=self.headers)
            if not rsp or rsp.status_code != 200:
                self.log(f"搜索请求失败，状态码: {rsp.status_code if rsp else '无响应'}")
                return {'list': []}
            
            doc = self.html(rsp.text)
            if not doc:
                self.log("搜索页面解析失败")
                return {'list': []}
            
            videos = self._get_videos(doc, category_id='2', limit=20)
            
            # 按特殊分类处理，给特殊类视频ID补特殊标记
            for video in videos:
                # 类型id固定为2，但是搜索结果中可能包含特殊类别的链接，根据链接特征标记特殊
                # 一般搜索结果都是type_id=2，为保险起见这里不做额外区分，可根据需要调整
                
                # 示例：如果视频ID中没有特殊前缀，且链接中带特殊ID，则也可做判断(可根据具体需求)
                pass
            
            # 分页信息
            pagecount = self._extract_pagecount(doc, rsp.text)
            current_page = int(pg)
            
            self.log(f"搜索成功，获取到 {len(videos)} 个视频，共 {pagecount} 页")
            
            return {
                'list': videos,
                'page': current_page,
                'pagecount': pagecount,
                'limit': 20,
                'total': pagecount * 20
            }
        except Exception as e:
            self.log(f"搜索出错: {str(e)}")
            return {'list': []}

    def detailContent(self, ids):
        """详情页面 - 修复版"""
        try:
            vid = ids[0]
            
            # 检查是否是特殊分区的链接
            if vid.startswith('special_'):
                parts = vid.split('_')
                if len(parts) >= 4:
                    category_id = parts[1]
                    video_id = parts[2]
                    encoded_url = '_'.join(parts[3:])
                    play_url = urllib.parse.unquote(encoded_url)
                    
                    self.log(f"特殊分区视频，直接使用链接: {play_url}")
                    
                    # 从播放链接中提取信息
                    parsed_url = urllib.parse.urlparse(play_url)
                    query_params = urllib.parse.parse_qs(parsed_url.query)
                    video_url = query_params.get('v', [''])[0]
                    pic_url = query_params.get('b', [''])[0]
                    title_encrypted = query_params.get('m', [''])[0]
                    
                    # 解码标题
                    title = self._decrypt_title(title_encrypted)
                    
                    return {
                        'list': [{
                            'vod_id': vid,
                            'vod_name': title,
                            'vod_pic': pic_url,
                            'vod_remarks': '',
                            'vod_year': '',
                            'vod_play_from': '直接播放',
                            'vod_play_url': f"第1集${play_url}"
                        }]
                    }
            
            # 常规处理
            if '_' in vid and len(vid.split('_')) > 2:
                domain, category_id, video_id = vid.split('_')
            else:
                domain, video_id = vid.split('_')
            
            detail_url = f"https://{domain}/index.php/vod/detail/id/{video_id}.html"
            
            self.log(f"访问详情URL: {detail_url}")
            rsp = self.fetch(detail_url, headers=self.headers)
            if not rsp or rsp.status_code != 200:
                self.log("详情页面请求失败")
                return {'list': []}
                
            doc = self.html(rsp.text)
            if not doc:
                self.log("详情页面HTML解析失败")
                return {'list': []}
                
            video_info = self._get_detail(doc, rsp.text, vid)
            return {'list': [video_info]} if video_info else {'list': []}
        except Exception as e:
            self.log(f"详情获取出错: {str(e)}")
            return {'list': []}

    def playerContent(self, flag, id, vipFlags):
        """播放链接 - 修复版"""
        try:
            self.log(f"获取播放链接: flag={flag}, id={id}")
            
            # 检查是否是特殊分区的链接
            if id.startswith('special_'):
                parts = id.split('_')
                if len(parts) >= 4:
                    category_id = parts[1]
                    video_id = parts[2]
                    encoded_url = '_'.join(parts[3:])
                    play_url = urllib.parse.unquote(encoded_url)
                    
                    self.log(f"特殊分区视频，直接使用链接: {play_url}")
                    
                    # 从播放链接中提取视频URL
                    parsed_url = urllib.parse.urlparse(play_url)
                    query_params = urllib.parse.parse_qs(parsed_url.query)
                    video_url = query_params.get('v', [''])[0]
                    
                    if video_url:
                        if video_url.startswith('//'):
                            video_url = 'https:' + video_url
                        elif not video_url.startswith('http'):
                            video_url = urljoin(self.host, video_url)
                        
                        self.log(f"从特殊链接中提取到视频地址: {video_url}")
                        return {'parse': 0, 'playUrl': '', 'url': video_url}
            
            # 检查传入的ID是否为完整URL
            if id.startswith('http'):
                self.log("ID 是一个完整URL，直接解析参数")
                parsed_url = urllib.parse.urlparse(id)
                query_params = urllib.parse.parse_qs(parsed_url.query)
                
                video_url = query_params.get('v', [''])[0]
                if not video_url:
                    for key in query_params:
                        if key in ['url', 'src', 'file']:
                            video_url = query_params[key][0]
                            break
                
                if video_url:
                    video_url = urllib.parse.unquote(video_url)
                    if video_url.startswith('//'):
                        video_url = 'https:' + video_url
                    elif not video_url.startswith('http'):
                        video_url = urljoin(self.host, video_url)
                    
                    self.log(f"从 URL 参数中提取到视频地址: {video_url}")
                    return {'parse': 0, 'playUrl': '', 'url': video_url}
                else:
                    self.log("URL 中没有找到视频参数，尝试从页面提取")
                    rsp = self.fetch(id, headers=self.headers)
                    if rsp and rsp.status_code == 200:
                        video_url = self._extract_direct_video_url(rsp.text)
                        if video_url:
                            self.log(f"从页面提取到视频地址: {video_url}")
                            return {'parse': 0, 'playUrl': '', 'url': video_url}
                    
                    self.log("无法从页面提取视频链接，返回原始URL")
                    return {'parse': 1, 'playUrl': '', 'url': id}

            # 从 id 格式中提取视频ID和分类ID
            if id.count('_') >= 2:
                parts = id.split('_')
                video_id = parts[-1]
                category_id = parts[1]
            else:
                video_id = id.split('_')[-1]
                category_id = ''
            
            self.log(f"视频ID: {video_id}, 分类ID: {category_id}")
            
            # 对于特殊分类，使用直接解析播放页面的方式
            if category_id in self.special_categories:
                self.log("特殊分类，尝试从详情页提取直接播放链接")
                play_page_url = f"{self.host}/index.php/vod/play/id/{video_id}.html"
                
                rsp = self.fetch(play_page_url, headers=self.headers)
                if rsp and rsp.status_code == 200:
                    video_url = self._extract_direct_video_url(rsp.text)
                    if video_url:
                        self.log(f"从播放页面提取到视频地址: {video_url}")
                        return {'parse': 0, 'playUrl': '', 'url': video_url}
                
                self.log("从播放页面提取失败，尝试API方式")
                return self._get_video_by_api(id, video_id)
            else:
                self.log("使用API方式获取视频地址")
                return self._get_video_by_api(id, video_id)
                
        except Exception as e:
            self.log(f"播放链接获取出错: {str(e)}")
            if '_' in id:
                domain, play_id = id.split('_')
                play_url = f"https://{domain}/html/ksdv-c.html?m={play_id}"
            else:
                play_url = f"{self.host}/html/ksdv-c.html?m={id}"
            return {'parse': 1, 'playUrl': '', 'url': play_url}

    def _get_video_by_api(self, id, video_id):
        """通过API获取视频地址"""
        try:
            api_url = f"{self.api_host}/api/v2/vod/reqplay/{video_id}"
            self.log(f"请求API获取视频地址: {api_url}")
            
            api_headers = self.headers.copy()
            api_headers.update({
                'Referer': f"{self.host}/",
                'Origin': self.host,
                'X-Requested-With': 'XMLHttpRequest'
            })
            
            api_response = self.fetch(api_url, headers=api_headers)
            if api_response and api_response.status_code == 200:
                data = api_response.json()
                self.log(f"API响应: {data}")
                
                if data.get('retcode') == 3:
                    video_url = data.get('data', {}).get('httpurl_preview', '')
                else:
                    video_url = data.get('data', {}).get('httpurl', '')
                
                if video_url:
                    video_url = video_url.replace('?300', '')
                    self.log(f"从API获取到视频地址: {video_url}")
                    return {'parse': 0, 'playUrl': '', 'url': video_url}
                else:
                    self.log("API响应中没有找到视频地址")
            else:
                self.log(f"API请求失败，状态码: {api_response.status_code if api_response else '无响应'}")
                
            if '_' in id:
                domain, play_id = id.split('_')
                play_url = f"https://{domain}/html/ksdv-c.html?m={play_id}"
            else:
                play_url = f"{self.host}/html/ksdv-c.html?m={id}"
            self.log(f"API请求失败，回退到播放页面: {play_url}")
            return {'parse': 1, 'playUrl': '', 'url': play_url}
            
        except Exception as e:
            self.log(f"API方式获取视频出错: {str(e)}")
            if '_' in id:
                domain, play_id = id.split('_')
                play_url = f"https://{domain}/html/ksdv-c.html?m={play_id}"
            else:
                play_url = f"{self.host}/html/ksdv-c.html?m={id}"
            return {'parse': 1, 'playUrl': '', 'url': play_url}

    def _extract_direct_video_url(self, html_content):
        """从HTML内容中提取直接播放链接"""
        try:
            patterns = [
                r'v=([^&]+\.(?:m3u8|mp4))',
                r'"url"\s*:\s*["\']([^"\']+\.(?:mp4|m3u8))["\']',
                r'src\s*=\s*["\']([^"\']+\.(?:mp4|m3u8))["\']',
                r'http[^\s<>"\'?]+\.(?:mp4|m3u8)'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, html_content, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0]
                    extracted_url = match.replace('\\', '')
                    extracted_url = urllib.parse.unquote(extracted_url)
                    
                    if extracted_url.startswith('//'):
                        extracted_url = 'https:' + extracted_url
                    elif extracted_url.startswith('http'):
                        return extracted_url
            
            return None
        except Exception as e:
            self.log(f"提取直接播放URL出错: {str(e)}")
            return None

    def _get_videos(self, doc, category_id=None, limit=None):
        """获取影片列表 - 修复版，支持特殊分类ID标记"""
        try:
            videos = []
            
            # 尝试多个选择器
            elements = doc.xpath('//a[contains(@class, "vodbox")]')
            if not elements:
                elements = doc.xpath('//div[contains(@class, "vodbox")]//a')
            if not elements:
                elements = doc.xpath('//div[@class="vwpp"]//a')
                
            self.log(f"找到 {len(elements)} 个视频元素")
            
            for elem in elements:
                video = self._extract_video(elem, category_id)
                if video:
                    # 判断视频是否属于特殊分类，给vod_id添加special_前缀标识
                    if category_id in self.special_categories:
                        # 避免重复添加前缀
                        if not video['vod_id'].startswith('special_'):
                            video['vod_id'] = f"special_{category_id}_{video['vod_id']}"
                    videos.append(video)
                    
            return videos[:limit] if limit and videos else videos
        except Exception as e:
            self.log(f"获取影片列表出错: {str(e)}")
            return []

    def _extract_video(self, element, category_id=None):
        """提取影片信息 - 修复版"""
        try:
            # 获取链接
            link = element.xpath('./@href')[0]
            if link.startswith('/'):
                link = self.host + link
            
            # 检查是否是特殊分区的链接
            is_special_link = '/html/ksdv-c.html' in link
            
            # 对于特殊分区，直接使用链接本身作为ID
            if is_special_link and category_id in self.special_categories:
                # 从链接中提取视频ID
                parsed_url = urllib.parse.urlparse(link)
                query_params = urllib.parse.parse_qs(parsed_url.query)
                video_url = query_params.get('id', [''])[0]
                
                if video_url:
                    video_id_match = re.search(r'/([a-f0-9-]+)/[^/]+\.m3u8', video_url)
                    if video_id_match:
                        video_id = video_id_match.group(1)
                    else:
                        video_id = str(hash(link) % 1000000)
                else:
                    video_id = str(hash(link) % 1000000)
                
                final_vod_id = f"special_{category_id}_{video_id}_{urllib.parse.quote(link)}"
            else:
                # 常规处理
                vod_id = self.regStr(r'/id/(\d+)\.html', link)
                if not vod_id:
                    vod_id = str(hash(link) % 1000000)
                
                final_vod_id = f"618413.xyz_{vod_id}"
                if category_id:
                    final_vod_id = f"618413.xyz_{category_id}_{vod_id}"
            
            # 提取标题 - 使用更通用的选择器
            title_elem = element.xpath('.//p[@class="km-script"]/text()')
            if not title_elem:
                title_elem = element.xpath('.//p[contains(@class, "km-script")]/text()')
            if not title_elem:
                title_elem = element.xpath('.//span[contains(@class, "title")]/text()')
            if not title_elem:
                title_elem = element.xpath('.//h3/text()')
            if not title_elem:
                title_elem = element.xpath('.//h4/text()')
            if not title_elem:
                self.log("未找到标题元素，跳过该视频")
                return None
            
            title_encrypted = title_elem[0].strip()
            title = self._decrypt_title(title_encrypted)
            
            # 提取图片 - 修复选择器
            pic_elem = element.xpath('.//img/@data-original')
            if not pic_elem:
                pic_elem = element.xpath('.//img/@src')
            pic = pic_elem[0] if pic_elem else ''
            
            if pic:
                if pic.startswith('//'):
                    pic = 'https:' + pic
                elif pic.startswith('/'):
                    pic = self.host + pic
                elif not pic.startswith('http'):
                    pic = self.host + '/' + pic.lstrip('/')
            
            return {
                'vod_id': final_vod_id,
                'vod_name': title,
                'vod_pic': f"{self.getProxyUrl()}&imgu={quote(pic)}",
                'vod_remarks': '',
                'vod_year': ''
            }
        except Exception as e:
            self.log(f"提取影片信息出错: {str(e)}")
            return None

    def _decrypt_title(self, encrypted_text):
        """解密标题 - 根据网页中的解密逻辑"""
        try:
            # 网页中的解密逻辑是每个字符与128进行异或
            decrypted_chars = []
            for char in encrypted_text:
                code_point = ord(char)
                decrypted_code = code_point ^ 128
                decrypted_char = chr(decrypted_code)
                decrypted_chars.append(decrypted_char)
            
            decrypted_text = ''.join(decrypted_chars)
            return decrypted_text
        except Exception as e:
            self.log(f"标题解密失败: {str(e)}")
            return encrypted_text

    def _get_detail(self, doc, html_content, vid):
        """获取详情信息 - 修复版"""
        try:
            title = self._get_text(doc, ['//h1/text()', '//title/text()'])
            pic = self._get_text(doc, ['//div[contains(@class,"dyimg")]//img/@src', '//img[contains(@class,"poster")]/@src'])
            if pic and pic.startswith('/'):
                pic = self.host + pic
            
            desc = self._get_text(doc, ['//div[contains(@class,"yp_context")]/text()', '//div[contains(@class,"introduction")]//text()'])
            actor = self._get_text(doc, ['//span[contains(text(),"主演")]/following-sibling::*/text()'])
            director = self._get_text(doc, ['//span[contains(text(),"导演")]/following-sibling::*/text()'])

            play_from = []
            play_urls = []
            
            # 修复播放链接提取逻辑
            player_link_patterns = [
                r'href="(/html/ksdv-c\.html[^"]*)"',
                r'href="(/html/kkyd\.html[^"]*)"'
            ]
            
            player_links = []
            for pattern in player_link_patterns:
                matches = re.findall(pattern, html_content)
                player_links.extend(matches)
            
            if player_links:
                episodes = []
                for link in player_links:
                    full_url = urljoin(self.host, link)
                    episodes.append(f"第1集${full_url}")

                if episodes:
                    play_from.append("默认播放源")
                    play_urls.append('#'.join(episodes))

            if not play_from:
                self.log("未找到播放源，使用默认播放方式")
                play_from.append("默认播放源")
                play_urls.append(f"第1集${vid}")

            return {
                'vod_id': vid,
                'vod_name': title,
                'vod_pic': f"{self.getProxyUrl()}&imgu={quote(pic)}",
                'type_name': '',
                'vod_year': '',
                'vod_area': '',
                'vod_remarks': '',
                'vod_actor': actor,
                'vod_director': director,
                'vod_content': desc,
                'vod_play_from': '$$$'.join(play_from),
                'vod_play_url': '$$$'.join(play_urls)
            }
        except Exception as e:
            self.log(f"获取详情出错: {str(e)}")
            return None

    def _get_text(self, doc, selectors):
        """通用文本提取"""
        for selector in selectors:
            try:
                texts = doc.xpath(selector)
                for text in texts:
                    if text and text.strip():
                        return text.strip()
            except:
                continue
        return ''

    def _extract_pagecount(self, doc, html_content):
        """提取总页数 - 从HTML中正确解析"""
        try:
            # 方法1: 从分页链接中提取
            pagination_links = doc.xpath('//div[@class="mypage"]/a[contains(@href, "/page/")]/@href')
            if pagination_links:
                # 查找尾页链接
                last_page_url = None
                for link in pagination_links:
                    link_text = doc.xpath(f'//a[@href="{link}"]/text()')
                    if link_text and '尾页' in link_text[0]:
                        last_page_url = link
                        break
                
                if not last_page_url and pagination_links:
                    # 如果没有明确的尾页链接，取最后一个链接
                    last_page_url = pagination_links[-1]
                
                if last_page_url:
                    last_page_match = re.search(r'page/(\d+)\.html', last_page_url)
                    if last_page_match:
                        return int(last_page_match.group(1))
            
            # 方法2: 从输入框placeholder中提取
            placeholder = doc.xpath('//input[@id="pageInput"]/@placeholder')
            if placeholder:
                placeholder_text = placeholder[0]
                page_match = re.search(r'(\d+)/(\d+)页', placeholder_text)
                if page_match:
                    return int(page_match.group(2))
            
            # 方法3: 从JavaScript变量中提取
            script_match = re.search(r"const totalPages='(\d+)'", html_content)
            if script_match:
                return int(script_match.group(1))
            
            # 方法4: 从分页文本中提取最大页码
            page_texts = doc.xpath('//div[@class="mypage"]//text()')
            page_numbers = []
            for text in page_texts:
                numbers = re.findall(r'\b\d+\b', text)
                page_numbers.extend([int(n) for n in numbers if n.isdigit()])
            
            if page_numbers:
                return max(page_numbers)
            
            # 默认返回1页
            return 1
            
        except Exception as e:
            self.log(f"提取页数出错: {str(e)}")
            return 1

    def log(self, message):
        """日志输出"""
        print(f"[葡萄视频] {message}")

    def fetch(self, url, headers=None, method='GET', data=None, timeout=10):
        """网络请求"""
        try:
            if headers is None:
                headers = self.headers
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout, verify=False)
            else:
                response = requests.post(url, headers=headers, data=data, timeout=timeout, verify=False)
            return response
        except Exception as e:
            self.log(f"网络请求失败: {url}, 错误: {str(e)}")
            return None

# 注册爬虫
if __name__ == '__main__':
    from base.spider import Spider as BaseSpider
    BaseSpider.register(Spider())
