#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
七猫小说(qimao.com) 爬虫 - 完全重构版
专注小说内容的爬取
"""
import json
import re
import sys
from urllib.parse import urljoin, quote, urlencode
import requests
import base64
import hashlib
import zlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

sys.path.append('..')
from base.spider import Spider


class Spider(Spider):
    """七猫小说爬虫类"""

    def __init__(self):
        self.host = 'https://www.qimao.com'
        self.api_host = 'https://api-bc.wtzw.com'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': f'{self.host}/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
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
        self.debug_mode = True
        self.config = {
            "filter": "H4sIAAAAAAAAAO1W3U4aQRR+l72GZF1EGh+iL9AYs1GaEBUbKzSNIaEgLFDKlqJujURLCohpEaTErrtFXmZ+lrfoALszO3BRbrig2ZtN9vvOzPmZ+c6ZE0EUNl+dCHvh98KmAAZVWPkAc1n8YAo+ISofhOfRuLwfC08WRQlJM61RujWGyY8sJHw2XMpCtWfDwQ2GZ6+A8dHGN0SK49syfDIdfJ3iSNdRTrXxUJDZl06JPWwobJUkSpQepQdQTwHDwGc3lA6wKBrKSDPhnxSLRRJdTttN8PwNmJfkS2nmGwwqVqpHCZbcS/SzBjNpyoSExNaY44rb1tB5d664DrpQcQMi0BVgNoDuRL/Gc/7g+OvEQbkJ6l8TXSSryRT2S26WlWQKT3wWnFPlskNXfXTRRdrjSOuz7GbQxbKD9TuYzcxlFuJwyZUxRwT4sL624OcmvC9is+IKi0cXu9G/e2wBF5g1vLYGA6C3bUbkIyh9gYbq8u38815RMY9TT1AxR4pz3Xf2Izt77FIW8yhpsotCoHeHR7tvt6OxA2ZUTVrD8rTqtlHsza58HN4+jhDv7r3OHi1NZXu9luOHRxFiGIuPw9/ykQSX0RhwqQvM71YridLzRwzV+izJzpkoHaV/ceRsn8A/rlEhSfXH2otV+0Q6Ab9xyJOnJ8/Vlae0FHmiCwW2m1beQNWOc5TrTEdkohILXH8m85rSrNTYVPF9DRYe4FCjtOSmYUafuqC0ayorBs7nYFe1On2HDoYY3S3D0yE6v3QN3+ALT8OehldWw/IqjdhlP+n/McJX5cW/uo3Ueyt5ffZ/7LOJv/U9eHXlEAAA",
        }

    def init(self, extend='{}'):
        """初始化配置"""
        try:
            config = json.loads(extend)
            self.proxies = config.get('proxy', {})
            self.log(f"✅ 初始化配置成功")
        except:
            self.proxies = {}
            self.log("✅ 使用默认配置")

    def getName(self):
        """返回爬虫名称"""
        return "七猫小说"

    # ==================== 核心功能方法 ====================

    def homeContent(self, filter):
        """获取首页分类和筛选配置"""
        try:
            result = {}
            
            # 分类配置
            categories = {
                "全部": "a",
                "女生原创": "1",
                "男生原创": "0",
                "出版图书": "2"
            }
            
            classes = []
            for name, tid in categories.items():
                classes.append({
                    'type_id': tid,
                    'type_name': name
                })
            
            result['class'] = classes
            result['type'] = '小说'
            
            # 加载筛选器
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
        """获取首页推荐（小说首页无推荐内容）"""
        return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        """获取分类内容"""
        try:
            pg = int(pg)
            self.log(f"📍 分类请求: tid={tid}, pg={pg}")
            
            # 构建URL
            url = f'{self.host}/shuku/{tid}/'
            if pg > 1:
                url = f'{url}page/{pg}/'
            
            self.log(f"📍 分类URL: {url}")
            
            response = self.fetch(url)
            if not response:
                return self._empty_result(pg)
            
            html = response.text
            
            # 使用正则提取书籍信息
            books = []
            
            # 模式1：书籍块
            book_pattern = r'<li[^>]*class="[^"]*qm-cover-text[^"]*"[^>]*>.*?<a[^>]*href="([^"]+)"[^>]*>.*?<img[^>]*src="([^"]+)"[^>]*alt="([^"]+)"[^>]*>.*?<p[^>]*class="[^"]*s-author[^"]*"[^>]*>([^<]+)</p>'
            book_matches = re.findall(book_pattern, html, re.DOTALL)
            
            for match in book_matches:
                try:
                    book_url, book_img, book_name, book_author = match
                    
                    # 清理数据
                    book_name = book_name.strip()
                    book_author = book_author.strip()
                    
                    # 确保是完整URL
                    if book_url and not book_url.startswith('http'):
                        book_url = urljoin(self.host, book_url)
                    
                    if book_img and not book_img.startswith('http'):
                        book_img = urljoin(self.host, book_img)
                    
                    if book_name and book_url:
                        books.append({
                            'vod_id': book_url,
                            'vod_name': book_name,
                            'vod_pic': book_img,
                            'vod_remarks': book_author,
                            'vod_content': ''
                        })
                        
                except Exception as e:
                    self.log(f"解析书籍项失败: {e}")
                    continue
            
            self.log(f"✅ 分类页找到 {len(books)} 本书")
            
            # 如果正则没找到，尝试备用方法
            if len(books) == 0:
                books = self._extract_books_from_html(html)
            
            return {
                'list': books,
                'page': pg,
                'pagecount': 999,
                'limit': 15,
                'total': 999999
            }
            
        except Exception as e:
            self.log(f"❌ categoryContent错误: {e}")
            return self._empty_result(pg)

    def detailContent(self, ids):
        """获取小说详情"""
        try:
            book_url = ids[0]
            self.log(f"📍 详情请求: {book_url}")
            
            response = self.fetch(book_url)
            if not response:
                return {'list': []}
            
            html = response.text
            
            # 提取书籍ID
            book_id = None
            match = re.search(r'shuku/(\d+)', book_url)
            if match:
                book_id = match.group(1)
            
            # 提取基本信息
            vod = {
                'vod_id': book_url,
                'vod_name': self._extract_by_regex(html, r'<span[^>]*class="[^"]*txt[^"]*"[^>]*>([^<]+)</span>'),
                'vod_content': self._extract_by_regex(html, r'<div[^>]*class="[^"]*book-introduction-item[^"]*"[^>]*>.*?<div[^>]*class="[^"]*qm-with-title-tb[^"]*"[^>]*>([^<]+)</div>', re.DOTALL),
                'vod_pic': self._extract_by_regex(html, r'<img[^>]*src="([^"]+)"[^>]*class="[^"]*wrap-pic[^"]*"[^>]*>'),
                'vod_remarks': self._extract_by_regex(html, r'<div[^>]*class="[^"]*qm-tag[^"]*"[^>]*>([^<]+)</div>'),
                'type_name': '小说',
                'vod_year': '',
                'vod_area': '',
                'vod_actor': self._extract_by_regex(html, r'<div[^>]*class="[^"]*sub-title[^"]*"[^>]*>.*?<span[^>]*>作者[^:]*:</span>.*?<span[^>]*>([^<]+)</span>', re.DOTALL),
                'vod_director': '',
                'vod_play_from': '七猫小说'
            }
            
            # 如果图片没找到，查找其他图片
            if not vod['vod_pic']:
                img_match = re.search(r'<img[^>]*src="([^"]+)"[^>]*alt="[^"]*{}[^"]*"[^>]*>'.format(re.escape(vod['vod_name'])), html)
                if img_match:
                    vod['vod_pic'] = img_match.group(1)
            
            # 获取章节列表
            if book_id:
                chapters = self._get_chapter_list(book_id)
                if chapters:
                    play_url = []
                    for chapter in chapters:
                        chapter_id = chapter.get('id', '')
                        chapter_title = chapter.get('title', '')
                        if chapter_id and chapter_title:
                            play_url.append(f"{chapter_title}${book_id}@@{chapter_id}@@{chapter_title}")
                    
                    if play_url:
                        vod['vod_play_url'] = '#'.join(play_url)
                        self.log(f"✅ 提取到 {len(play_url)} 章")
            
            return {'list': [vod]}
            
        except Exception as e:
            self.log(f"❌ detailContent错误: {e}")
            import traceback
            self.log(traceback.format_exc())
            return {'list': []}

    def searchContent(self, key, quick, pg='1'):
        """搜索功能"""
        try:
            pg = int(pg)
            self.log(f"🔍 搜索请求: key={key}, pg={pg}")
            
            # 使用搜索API
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
            params['sign'] = self._generate_sign(params)
            
            # 设置API头
            headers = self.headers.copy()
            headers.update(self.sign_headers)
            
            response = self.fetch(url, params=params, headers=headers)
            if not response:
                self.log("❌ 搜索API请求失败")
                return {'list': [], 'page': pg}
            
            data = response.json()
            books_data = data.get('data', {}).get('books', [])
            
            books = []
            for book in books_data:
                if book.get('show_type') == '0':  # 正常书籍
                    books.append({
                        'vod_id': f'https://www.qimao.com/shuku/{book.get("id", "")}/',
                        'vod_name': book.get('original_title', '未知'),
                        'vod_pic': book.get('image_link', ''),
                        'vod_remarks': book.get('author', '未知作者'),
                        'vod_content': book.get('introduction', '')
                    })
            
            self.log(f"✅ 搜索到 {len(books)} 本书")
            
            return {
                'list': books,
                'page': pg,
                'pagecount': 999,
                'limit': 15,
                'total': 999999
            }
            
        except Exception as e:
            self.log(f"❌ searchContent错误: {e}")
            return {'list': [], 'page': pg}

    def playerContent(self, flag, id, vipFlags):
        """获取播放链接（章节内容）"""
        try:
            self.log(f"📖 获取章节内容: {id}")
            
            # 解析参数
            parts = id.split('@@')
            if len(parts) < 3:
                return self._create_novel_result('参数错误', '章节参数格式不正确')
            
            book_id = parts[0]
            chapter_id = parts[1]
            chapter_title = parts[2]
            
            # 请求章节内容
            url = 'https://api-ks.wtzw.com/api/v1/chapter/content'
            params = {
                'id': book_id,
                'chapterId': chapter_id,
            }
            params['sign'] = self._generate_sign(params)
            
            headers = self.headers.copy()
            headers.update(self.sign_headers)
            
            response = self.fetch(url, params=params, headers=headers)
            if not response:
                return self._create_novel_result(chapter_title, '获取内容失败')
            
            data = response.json()
            encrypted_content = data.get('data', {}).get('content', '')
            
            if encrypted_content:
                # 解密内容
                content = self._decrypt_content(encrypted_content)
            else:
                content = "本章节内容为空"
            
            return self._create_novel_result(chapter_title, content)
            
        except Exception as e:
            self.log(f"❌ playerContent错误: {e}")
            return self._create_novel_result('错误', f'获取内容失败: {str(e)}')

    # ==================== 辅助方法 ====================

    def fetch(self, url, params=None, headers=None, timeout=15):
        """统一的HTTP请求方法"""
        if headers is None:
            headers = self.headers
        
        try:
            response = requests.get(
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
        except Exception as e:
            self.log(f"❌ 请求失败 {url}: {e}")
            return None

    def _extract_by_regex(self, html, pattern, flags=0):
        """使用正则表达式提取内容"""
        match = re.search(pattern, html, flags)
        if match:
            return match.group(1).strip()
        return ''

    def _extract_books_from_html(self, html):
        """从HTML中提取书籍列表（备用方法）"""
        books = []
        
        # 查找所有书籍链接
        book_links = re.findall(r'<a[^>]*href="([^"]*/shuku/\d+/)[^"]*"[^>]*>', html)
        
        for link in book_links:
            try:
                # 提取书籍ID
                match = re.search(r'shuku/(\d+)', link)
                if match:
                    book_id = match.group(1)
                    
                    # 查找书籍标题
                    title_pattern = rf'href="{re.escape(link)}"[^>]*>.*?<img[^>]*alt="([^"]+)"'
                    title_match = re.search(title_pattern, html, re.DOTALL)
                    
                    book_name = title_match.group(1) if title_match else f'书籍_{book_id}'
                    
                    books.append({
                        'vod_id': urljoin(self.host, link),
                        'vod_name': book_name,
                        'vod_pic': '',
                        'vod_remarks': '',
                        'vod_content': ''
                    })
                    
            except Exception as e:
                continue
        
        return books

    def _get_chapter_list(self, book_id):
        """获取章节列表"""
        try:
            url = 'https://www.qimao.com/api/book/chapter-list'
            params = {'book_id': book_id}
            
            response = self.fetch(url, params=params)
            if response:
                data = response.json()
                return data.get('data', {}).get('chapters', [])
        except Exception as e:
            self.log(f"获取章节列表失败: {e}")
        
        return []

    def _generate_sign(self, params):
        """生成签名"""
        sign_key = "d3dGiJc651gSQ8w1"
        keys = sorted(params.keys())
        sign_str = ""
        for key in keys:
            sign_str += f"{key}={params[key]}"
        sign_str += sign_key
        md5_hash = hashlib.md5(sign_str.encode('utf-8')).hexdigest()
        return md5_hash

    def _decrypt_content(self, encrypted_content):
        """解密章节内容"""
        try:
            # 解码 Base64
            decoded_bytes = base64.b64decode(encrypted_content)
            hex_str = decoded_bytes.hex()
            
            # 提取 IV 和内容
            iv = hex_str[:32]
            content_hex = hex_str[32:]
            
            # AES解密
            key_hex = "32343263636238323330643730396531"
            key = bytes.fromhex(key_hex)
            iv_bytes = bytes.fromhex(iv)
            data_bytes = bytes.fromhex(content_hex)
            
            cipher = AES.new(key, AES.MODE_CBC, iv_bytes)
            decrypted = cipher.decrypt(data_bytes)
            
            try:
                unpadded = unpad(decrypted, AES.block_size)
            except ValueError:
                unpadded = decrypted
            
            return unpadded.decode('utf-8').strip()
            
        except Exception as e:
            self.log(f"❌ 解密失败: {e}")
            return "解密失败，请稍后再试"

    def ungzip(self, b64_data):
        """解码 base64 字符串，进行 gzip 解压缩"""
        try:
            compressed_data = base64.b64decode(b64_data)
            decompressed_data = zlib.decompress(compressed_data, zlib.MAX_WBITS | 32)
            return decompressed_data.decode('utf-8')
        except Exception as e:
            self.log(f"解压缩失败: {e}")
            return "{}"

    def _create_novel_result(self, title, content):
        """创建小说播放结果"""
        result_data = {
            'title': title,
            'content': content,
        }
        
        return {
            "parse": 0,
            "playUrl": '',
            "url": 'novel://' + json.dumps(result_data, ensure_ascii=False),
            "header": '',
            "jx": 0
        }

    def _empty_result(self, pg):
        """返回空结果"""
        return {
            'list': [],
            'page': pg,
            'pagecount': 1,
            'limit': 15,
            'total': 0
        }

    def log(self, message):
        """日志输出"""
        if self.debug_mode:
            print(f"[七猫小说] {message}")

    # ==================== 框架必需方法 ====================

    def isVideoFormat(self, url):
        """判断URL是否为视频格式"""
        return False

    def manualVideoCheck(self):
        """是否需要手动检查视频"""
        return False

    def localProxy(self, param):
        """本地代理功能"""
        pass

    def destroy(self):
        """清理资源"""
        pass
