"""
@header({
  searchable: 1,
  filterable: 1,
  quickSearch: 1,
  title: '七猫小说',
  类型: '小说',
  logo: 'https://cdn-front.qimao.com/global/static/images/favicon2022.ico',
  lang: 'hipy'
})
"""

import sys
import json
import re
import base64
import hashlib
import zlib
from urllib.parse import urlencode
from typing import List, Dict, Any, Optional

sys.path.append('..')

from base.spider import Spider as BaseSpider
from base.htmlParser import jsoup
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad


class Spider(BaseSpider):
    """七猫小说爬虫类"""
    
    def __init__(self):
        self.name = "七猫小说"
        self.host = 'https://www.qimao.com'
        self.api_host = 'https://api-bc.wtzw.com'
        self.debug_mode = True
        
        # 通用请求头
        self.headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
            "accept-encoding": "gzip, deflate, br",
            "connection": "keep-alive"
        }
        
        # API请求头（用于加密接口）
        self.sign_headers = {
            "app-version": "51110",
            "platform": "android",
            "reg": "0",
            "AUTHORIZATION": "",
            "application-id": "com.****.reader",
            "net-env": "1",
            "channel": "unknown",
            "qm-params": "",
            "sign": "fc697243ab534ebaf51d2fa80f251cb4"
        }
        
        self.proxies = {}
        self.timeout = 15
        
        # 配置信息
        self.config = {
            "player": {},
            "filter": "H4sIAAAAAAAAAO1W3U4aQRR+l72GZF1EGh+iL9AYs1GaEBUbKzSNIaEgLFDKlqJujURLCohpEaTErrtFXmZ+lrfoALszO3BRbrig2ZtN9vvOzPmZ+c6ZE0EUNl+dCHvh98KmAAZVWPkAc1n8YAo+ISofhOfRuLwfC08WRQlJM61RujWGyY8sJHw2XMpCtWfDwQ2GZ6+A8dHGN0SK49syfDIdfJ3iSNdRTrXxUJDZl06JPWwobJUkSpQepQdQTwHDwGc3lA6wKBrKSDPhnxSLRRJdTttN8PwNmJfkS2nmGwwqVqpHCZbcS/SzBjNpyoSExNaY44rb1tB5d664DrpQcQMi0BVgNoDuRL/Gc/7g+OvEQbkJ6l8TXSSryRT2S26WlWQKT3wWnFPlskNXfXTRRdrjSOuz7GbQxbKD9TuYzcxlFuJwyZUxRwT4sL524OcmvC9is+IKi0cXu9G/e2wBF5g1vLYGA6C3bUbkIyh9gYbq8u38815RMY9TT1AxR4pz3Xf2Izt77FIW8yhpsotCoHeHR7tvt6OxA2ZUTVrD8rTqtlHsza58HN4+jhDv7r3OHi1NZXu9luOHRxFiGIuPw9/ykQSX0RhwqQvM71YridLzRwzV+izJzpkoHaV/ceRsn8A/rlEhSfXH2otV+0Q6Ab9xyJOnJ8/Vlae0FHmiCwW2m1beQNWOc5TrTEdkohILXH8m85rSrNTYVPF9DRYe4FCjtOSmYUafuqC0ayorBs7nYFe1On2HDoYY3S3D0yE6v3QN3+ALT8OehldWw/IqjdhlP+n/McJX5cW/uo3Ueyt5ffZ/7LOJv/U9eHXlEAAA",
        }

    def init(self, extend='{}'):
        """初始化配置"""
        try:
            config = json.loads(extend)
            self.proxies = config.get('proxy', {})
            self.log(f"✅ 初始化配置: {config}")
        except Exception as e:
            self.log(f"❌ 初始化配置失败: {e}")
            self.proxies = {}

    def getName(self):
        """返回爬虫名称"""
        return self.name

    # ==================== 核心功能方法 ====================

    def homeContent(self, filter):
        """获取首页分类和筛选配置"""
        try:
            result = {}
            
            # 分类配置
            class_names = '全部&女生原创&男生原创&出版图书'.split('&')
            class_urls = 'a&1&0&2'.split('&')
            classes = []
            
            for i in range(len(class_names)):
                classes.append({
                    'type_name': class_names[i],
                    'type_id': class_urls[i]
                })
            
            result['class'] = classes
            result['type'] = '小说'
            
            # 加载筛选器配置
            if self.config.get('filter'):
                try:
                    filter_config = self.ungzip(self.config['filter'])
                    result['filters'] = json.loads(filter_config)
                    self.log("✅ 筛选器配置加载成功")
                except Exception as e:
                    self.log(f"❌ 筛选器配置加载失败: {e}")
                    result['filters'] = {}
            
            return result
            
        except Exception as e:
            self.log(f"❌ homeContent错误: {e}")
            return {'class': [], 'filters': {}}

    def homeVideoContent(self):
        """获取首页推荐视频（小说无需此功能）"""
        return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        """获取分类内容"""
        try:
            pg = int(pg)
            self.log(f"📍 分类请求: tid={tid}, pg={pg}, extend={extend}")
            
            # 构建筛选URL
            filter_url = "{{fl.作品分类 or 'a'}}-a-{{fl.作品字数 or 'a'}}-{{fl.更新时间 or 'a'}}-a-{{fl.是否完结 or 'a'}}-{{fl.排序 or 'click'}}"
            api_url = f'{self.host}/shuku/fyclass-fyfilter-fypage/'
            url = api_url.replace('fyclass', str(tid)).replace('fyfilter', filter_url).replace('fypage', str(pg))
            
            # 使用jinja2渲染（简化版）
            if isinstance(extend, dict):
                for key, value in extend.items():
                    placeholder = f"{{{{fl.{key}}}}}"
                    if placeholder in url:
                        url = url.replace(placeholder, str(value) if value else 'a')
            
            self.log(f"📍 分类URL: {url}")
            
            # 请求分类页面
            response = self.fetch(url)
            if not response:
                return self._empty_result(pg)
            
            html = response.text
            
            # 解析HTML
            jsp = jsoup(url)
            data = jsp.pdfa(html, 'ul.qm-cover-text&&li')
            self.log(f"✅ 找到 {len(data)} 本小说")
            
            books = []
            for it in data:
                try:
                    book = {
                        "vod_name": jsp.pdfh(it, '.s-tit&&Text'),
                        "vod_id": jsp.pd(it, 'a&&href'),
                        "vod_remarks": jsp.pdfh(it, '.s-author&&Text'),
                        "vod_pic": jsp.pd(it, 'img&&src'),
                        "vod_content": jsp.pdfh(it, '.s-desc&&Text'),
                    }
                    
                    # 过滤空数据
                    if book.get('vod_name') and book.get('vod_id'):
                        books.append(book)
                        
                except Exception as e:
                    self.log(f"❌ 解析小说项失败: {e}")
                    continue
            
            # 尝试通过API获取更多信息
            try:
                api_url = f"{self.host}/qimaoapi/api/classify/book-list"
                params = {
                    'channel': tid,
                    'category1': extend.get('作品分类', 'a'),
                    'category2': 'a',
                    'words': extend.get('作品字数', 'a'),
                    'update_time': extend.get('更新时间', 'a'),
                    'is_vip': 'a',
                    'is_over': extend.get('是否完结', 'a'),
                    'order': extend.get('排序', 'click'),
                    'page': pg
                }
                
                api_response = self.fetch(api_url, params=params)
                if api_response:
                    api_data = api_response.json()
                    book_list = api_data.get('data', {}).get('book_list', [])
                    
                    # 更新书籍信息
                    for book in books:
                        book_extra = [x for x in book_list if x.get('read_url') == book['vod_id']]
                        if book_extra:
                            book['vod_pic'] = book_extra[0].get('image_link') or book['vod_pic']
            except Exception as e:
                self.log(f"⚠️ API请求失败（不影响主要功能）: {e}")
            
            return {
                'list': books,
                'page': pg,
                'pagecount': 999,
                'limit': 15,
                'total': 999999
            }
            
        except Exception as e:
            self.log(f"❌ categoryContent错误: {e}")
            import traceback
            self.log(traceback.format_exc())
            return self._empty_result(pg)

    def detailContent(self, ids):
        """获取小说详情"""
        try:
            url = ids[0]
            self.log(f"📍 详情请求: {url}")
            
            response = self.fetch(url)
            if not response:
                return {'list': []}
            
            html = response.text
            jsp = jsoup(url)
            
            # 提取基本信息
            vod = {
                'vod_name': jsp.pdfh(html, 'span.txt&&Text'),
                'type_name': jsp.pdfh(html, '.qm-tag:eq(-1)&&Text'),
                'vod_pic': jsp.pd(html, '.wrap-pic&&img&&src'),
                'vod_content': jsp.pdfh(html, '.book-introduction-item&&.qm-with-title-tb&&Text'),
                'vod_remarks': jsp.pdfh(html, '.qm-tag&&Text'),
                'vod_year': '',
                'vod_area': '',
                'vod_actor': jsp.pdfh(html, '.sub-title&&span:eq(1)&&Text'),
                'vod_director': jsp.pdfh(html, '.sub-title&&span&&a&&Text'),
                'vod_play_from': jsp.pdfh(html, '.qm-sheader&&img&&alt'),
                'vod_id': url
            }
            
            # 提取书籍ID
            book_id = None
            match = re.search(r'shuku/(\d+)', url)
            if match:
                book_id = match.group(1)
            
            if book_id:
                # 获取章节列表
                chapter_url = 'https://www.qimao.com/api/book/chapter-list'
                params = {'book_id': book_id}
                
                chapter_response = self.fetch(chapter_url, params=params)
                if chapter_response:
                    chapter_data = chapter_response.json()
                    chapters = jsp.pjfa(chapter_data, 'data.chapters')
                    
                    if chapters:
                        # 构建章节列表
                        chapter_list = []
                        for idx, chapter in enumerate(chapters):
                            chapter_title = chapter.get('title', f'第{idx+1}章')
                            chapter_id = chapter.get('id', '')
                            
                            if chapter_id:
                                chapter_list.append(
                                    f'{chapter_title}${book_id}@@{chapter_id}@@{chapter_title}'
                                )
                        
                        if chapter_list:
                            vod['vod_play_url'] = '#'.join(chapter_list)
                            vod['vod_play_from'] = '七猫小说'
                            self.log(f"✅ 提取到 {len(chapter_list)} 章")
            
            return {'list': [vod]}
            
        except Exception as e:
            self.log(f"❌ detailContent错误: {e}")
            import traceback
            self.log(traceback.format_exc())
            return {'list': []}

    def searchContent(self, key, quick, pg=1):
        """搜索小说"""
        try:
            pg = int(pg)
            self.log(f"🔍 搜索请求: key={key}, pg={pg}")
            
            url = 'https://api-bc.wtzw.com/search/v1/words'
            params = {
                'extend': '',
                'tab': '0',
                'gender': '0',
                'refresh_state': '8',
                'page': pg,
                'wd': key,
                'is_short_story_user': '0'
            }
            
            # 生成签名
            params['sign'] = self.get_sign_str(params)
            
            # 设置API请求头
            api_headers = self.headers.copy()
            api_headers.update(self.sign_headers)
            
            response = self.fetch(url, params=params, headers=api_headers)
            if not response:
                return {'list': [], 'page': pg}
            
            data = response.json()
            books = data.get('data', {}).get('books', [])
            
            result_books = []
            for book in books:
                # 只显示正常书籍（show_type为0）
                if book.get('show_type') == '0':
                    result_books.append({
                        'vod_name': book.get('original_title', '未知'),
                        'vod_remarks': book.get('author', '未知作者'),
                        'vod_pic': book.get('image_link', ''),
                        'vod_id': f'https://www.qimao.com/shuku/{book.get("id", "")}/',
                        'vod_content': book.get('introduction', '')
                    })
            
            self.log(f"✅ 搜索到 {len(result_books)} 本小说")
            
            return {
                'list': result_books,
                'page': pg,
                'pagecount': 999,
                'limit': 15,
                'total': 999999
            }
            
        except Exception as e:
            self.log(f"❌ searchContent错误: {e}")
            return {'list': [], 'page': pg}

    def playerContent(self, flag, id, vipFlags):
        """获取章节内容"""
        try:
            self.log(f"📖 获取章节内容: {id}")
            
            # 解析参数
            parts = id.split('@@')
            if len(parts) < 3:
                return self._create_player_result('参数错误', '章节参数格式不正确')
            
            book_id = parts[0]
            chapter_id = parts[1]
            chapter_title = parts[2]
            
            # 构建请求参数
            params = {
                'id': book_id,
                'chapterId': chapter_id,
            }
            params['sign'] = self.get_sign_str(params)
            
            # 请求章节内容
            url = 'https://api-ks.wtzw.com/api/v1/chapter/content'
            
            # 设置API请求头
            api_headers = self.headers.copy()
            api_headers.update(self.sign_headers)
            
            response = self.fetch(url, params=params, headers=api_headers)
            if not response:
                return self._create_player_result(chapter_title, '获取内容失败')
            
            data = response.json()
            encrypted_content = data.get('data', {}).get('content', '')
            
            if not encrypted_content:
                return self._create_player_result(chapter_title, '内容为空')
            
            # 解密内容
            content = self.decode_content(encrypted_content)
            
            return self._create_player_result(chapter_title, content)
            
        except Exception as e:
            self.log(f"❌ playerContent错误: {e}")
            import traceback
            self.log(traceback.format_exc())
            return self._create_player_result('错误', '获取章节内容失败')

    # ==================== 辅助方法 ====================

    def fetch(self, url, params=None, headers=None, method='GET', timeout=None):
        """统一的HTTP请求方法"""
        if headers is None:
            headers = self.headers
        
        if timeout is None:
            timeout = self.timeout
        
        try:
            if method.upper() == 'GET':
                response = requests.get(
                    url,
                    params=params,
                    headers=headers,
                    proxies=self.proxies,
                    timeout=timeout,
                    verify=False
                )
            else:
                response = requests.post(
                    url,
                    params=params,
                    headers=headers,
                    proxies=self.proxies,
                    timeout=timeout,
                    verify=False
                )
            
            if response.status_code != 200:
                self.log(f"⚠️ HTTP {response.status_code}: {url}")
            
            response.raise_for_status()
            return response
            
        except requests.exceptions.Timeout:
            self.log(f"⏰ 请求超时: {url}")
            return None
        except requests.exceptions.RequestException as e:
            self.log(f"❌ 请求失败: {e}")
            return None
        except Exception as e:
            self.log(f"❌ 请求异常: {e}")
            return None

    def buildUrl(self, url, params):
        """构建带参数的URL"""
        if params:
            return f"{url}?{urlencode(params)}"
        return url

    def _empty_result(self, pg):
        """返回空结果"""
        return {
            'list': [],
            'page': pg,
            'pagecount': 1,
            'limit': 15,
            'total': 0
        }

    def _create_player_result(self, title, content):
        """创建播放器结果"""
        ret = json.dumps({
            'title': title,
            'content': content,
        }, ensure_ascii=False)
        
        return {
            "parse": 0,  # 0=直接播放、1=嗅探
            "playUrl": '',
            "url": 'novel://' + ret,
            "header": '',
            "jx": 0  # VIP解析,0=不解析、1=解析
        }

    def log(self, message):
        """日志输出"""
        if self.debug_mode:
            print(f"[七猫小说] {message}")

    # ==================== 加解密相关方法 ====================

    @staticmethod
    def ungzip(b64_data: str) -> str:
        """解码 base64 字符串，进行 gzip 解压缩"""
        try:
            compressed_data = base64.b64decode(b64_data)
            decompressed_data = zlib.decompress(compressed_data, zlib.MAX_WBITS | 32)
            return decompressed_data.decode('utf-8')
        except Exception as e:
            raise ValueError(f"解压缩过程中出错: {str(e)}")

    @staticmethod
    def get_sign_str(params):
        """生成签名"""
        sign_key = "d3dGiJc651gSQ8w1"
        keys = sorted(params.keys())
        sign_str = ""
        for key in keys:
            sign_str += f"{key}={params[key]}"
        sign_str += sign_key
        md5_hash = hashlib.md5(sign_str.encode('utf-8')).hexdigest()
        return md5_hash

    def decode_content(self, response):
        """解密章节内容"""
        try:
            # 解码 Base64
            decoded_bytes = base64.b64decode(response)
            hex_str = decoded_bytes.hex()
            
            # 提取 IV 和内容
            iv = hex_str[:32]
            content_hex = hex_str[32:]
            
            # 解密
            decrypted_content = self.novel_content_decrypt(content_hex, iv)
            return decrypted_content
            
        except Exception as e:
            self.log(f"❌ 解密内容失败: {e}")
            return "解密失败，请稍后再试"

    @staticmethod
    def novel_content_decrypt(data, iv):
        """AES解密小说内容"""
        try:
            key_hex = "32343263636238323330643730396531"
            key = bytes.fromhex(key_hex)
            iv_bytes = bytes.fromhex(iv)
            data_bytes = bytes.fromhex(data)
            
            cipher = AES.new(key, AES.MODE_CBC, iv_bytes)
            decrypted = cipher.decrypt(data_bytes)
            
            try:
                unpadded = unpad(decrypted, AES.block_size)
            except ValueError:
                unpadded = decrypted
            
            return unpadded.decode('utf-8').strip()
            
        except Exception as e:
            raise ValueError(f"解密失败: {str(e)}")

    # ==================== 框架必需方法 ====================

    def isVideoFormat(self, url):
        """判断URL是否为视频格式（小说无需此功能）"""
        return False

    def manualVideoCheck(self):
        """是否需要手动检查视频（小说无需此功能）"""
        return False

    def localProxy(self, param):
        """本地代理功能"""
        pass

    def destroy(self):
        """清理资源"""
        pass

    def getDependence(self):
        """获取依赖"""
        return []
