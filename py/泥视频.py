# -*- coding: utf-8 -*-
# 泥视频 - https://www.nivod.vip/
import re
import sys
import json
import time
from urllib.parse import quote, unquote
from pyquery import PyQuery as pq
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def init(self, extend=""):
        pass

    def getName(self):
        return "泥视频"

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    host = 'https://www.nivod.vip'

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

    def homeContent(self, filter):
        """获取首页内容和分类"""
        try:
            response = self.fetch_with_encoding(self.host, headers=self.headers)
            doc = self.getpq(response.text)
            
            result = {}
            classes = []
            
            # 获取分类导航
            nav_items = doc('.navbar a')
            for item in nav_items.items():
                text = item.text().strip()
                href = item.attr('href')
                if text and href and href != '/' and '/t/' in href:
                    # 提取分类ID
                    type_id = href.split('/t/')[-1].rstrip('/')
                    if type_id.isdigit():
                        classes.append({
                            'type_name': text,
                            'type_id': type_id
                        })
            
            # 获取首页视频列表
            videos = []
            video_items = doc('.module-item')
            for item in video_items.items():
                try:
                    title = item.attr('title') or ''
                    href = item.attr('href') or ''
                    
                    if title and href:
                        # 提取视频ID
                        vod_id = href.split('/nivod/')[-1].rstrip('/')
                        
                        # 获取图片 - 优先获取data-original（真实图片），避免懒加载占位图
                        img_elem = item.find('img')
                        pic = ''
                        if img_elem:
                            # 优先获取data-original（真实图片URL），然后是data-src，最后是src
                            pic = img_elem.attr('data-original') or img_elem.attr('data-src') or img_elem.attr('src') or ''
                            if pic and not pic.startswith('http'):
                                pic = self.host + pic if pic.startswith('/') else ''
                        
                        # 获取备注信息
                        note_elem = item.find('.module-item-note')
                        remarks = note_elem.text() if note_elem else ''
                        
                        videos.append({
                            'vod_id': vod_id,
                            'vod_name': title,
                            'vod_pic': pic,
                            'vod_year': '',
                            'vod_remarks': remarks
                        })
                except Exception as e:
                    self.log(f"解析视频项时出错: {e}")
                    continue
            
            result['class'] = classes
            result['list'] = videos
            return result
            
        except Exception as e:
            self.log(f"获取首页内容时出错: {e}")
            return {'class': [], 'list': []}

    def homeVideoContent(self):
        """获取推荐视频"""
        return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        """获取分类内容"""
        try:
            # 构建分类URL
            url = f"{self.host}/t/{tid}/"
            if int(pg) > 1:
                url = f"{self.host}/t/{tid}/page/{pg}/"
            
            response = self.fetch_with_encoding(url, headers=self.headers)
            doc = self.getpq(response.text)
            
            # 获取视频列表
            videos = []
            video_items = doc('.module-item')
            for item in video_items.items():
                try:
                    title = item.attr('title') or ''
                    href = item.attr('href') or ''
                    
                    if title and href:
                        # 提取视频ID
                        vod_id = href.split('/nivod/')[-1].rstrip('/')
                        
                        # 获取图片 - 优先获取data-original（真实图片），避免懒加载占位图
                        img_elem = item.find('img')
                        pic = ''
                        if img_elem:
                            # 优先获取data-original（真实图片URL），然后是data-src，最后是src
                            pic = img_elem.attr('data-original') or img_elem.attr('data-src') or img_elem.attr('src') or ''
                            if pic and not pic.startswith('http'):
                                pic = self.host + pic if pic.startswith('/') else ''
                        
                        # 获取备注信息
                        note_elem = item.find('.module-item-note')
                        remarks = note_elem.text() if note_elem else ''
                        
                        videos.append({
                            'vod_id': vod_id,
                            'vod_name': title,
                            'vod_pic': pic,
                            'vod_year': '',
                            'vod_remarks': remarks
                        })
                except Exception as e:
                    self.log(f"解析分类视频项时出错: {e}")
                    continue
            
            result = {
                'list': videos,
                'page': pg,
                'pagecount': 9999,  # 设置一个较大的值
                'limit': 80,
                'total': 999999
            }
            return result
            
        except Exception as e:
            self.log(f"获取分类内容时出错: {e}")
            return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 80, 'total': 0}

    def detailContent(self, ids):
        """获取视频详情"""
        try:
            vod_id = ids[0]
            url = f"{self.host}/nivod/{vod_id}/"
            
            response = self.fetch_with_encoding(url, headers=self.headers)
            doc = self.getpq(response.text)
            
            # 获取标题
            title_elem = doc('h1')
            title = self.fix_encoding(title_elem.text()) if title_elem else ''

            # 获取视频信息
            info_elem = doc('.module-info')
            content = self.fix_encoding(info_elem.text()) if info_elem else ''
            
            # 获取播放源和播放列表
            play_from = []
            play_url = []
            
            # 获取播放源标签
            tab_items = doc('.module-tab-item')
            play_lists = doc('.module-play-list')
            
            for i, tab in enumerate(tab_items.items()):
                # 分别提取播放源名称和集数
                span_elem = tab.find('span')
                small_elem = tab.find('small')

                source_name = ''
                if span_elem:
                    source_name = self.fix_encoding(span_elem.text().strip())
                    # 如果有集数信息，添加到播放源名称后
                    if small_elem:
                        episode_count = self.fix_encoding(small_elem.text().strip())
                        source_name = f"{source_name}{episode_count}"
                else:
                    # 如果没有span元素，使用整个文本
                    source_name = self.fix_encoding(tab.text().strip())

                if source_name:
                    play_from.append(source_name)
                    
                    # 获取对应的播放列表
                    episodes = []
                    if i < len(play_lists):
                        episode_items = play_lists.eq(i).find('a')
                        for ep in episode_items.items():
                            ep_title = self.fix_encoding(ep.text().strip())
                            ep_href = ep.attr('href')
                            if ep_title and ep_href:
                                episodes.append(f"{ep_title}${ep_href}")
                    
                    play_url.append('#'.join(episodes))
            
            vod = {
                'vod_id': vod_id,
                'vod_name': title,
                'vod_pic': '',
                'vod_year': '',
                'vod_remarks': '',
                'vod_actor': '',
                'vod_director': '',
                'vod_content': content,
                'vod_play_from': '$$$'.join(play_from),
                'vod_play_url': '$$$'.join(play_url)
            }
            
            return {'list': [vod]}
            
        except Exception as e:
            self.log(f"获取视频详情时出错: {e}")
            return {'list': []}

    def searchContent(self, key, quick, pg="1"):
        """搜索内容"""
        try:
            # 使用正确的搜索URL格式
            search_url = f"{self.host}/s/-------------/"
            params = {'wd': key}

            response = self.fetch_with_encoding(search_url, params=params, headers=self.headers)
            doc = self.getpq(response.text)
            
            # 获取搜索结果
            videos = []
            video_items = doc('.module-item')
            for item in video_items.items():
                try:
                    # 搜索页面的结构不同，需要从内部链接获取信息
                    # 查找详情链接（通常是第一个或标题链接）
                    detail_links = item.find('a[href*="/nivod/"]')
                    if not detail_links:
                        continue

                    # 获取第一个详情链接
                    detail_link = detail_links.eq(0)
                    href = detail_link.attr('href')

                    if not href:
                        continue

                    # 提取视频ID
                    vod_id = href.split('/nivod/')[-1].rstrip('/')

                    # 获取标题 - 尝试多种方式
                    title = ''
                    # 方法1: 从链接的strong标签获取
                    strong_elem = detail_link.find('strong')
                    if strong_elem:
                        title = self.fix_encoding(strong_elem.text().strip())

                    # 方法2: 从图片的alt属性获取
                    if not title:
                        img_elem = item.find('img')
                        if img_elem:
                            title = self.fix_encoding(img_elem.attr('alt') or '')

                    # 方法3: 从链接文本获取
                    if not title:
                        title = self.fix_encoding(detail_link.text().strip())

                    if not title:
                        continue

                    # 获取图片 - 优先获取data-original（真实图片），避免懒加载占位图
                    img_elem = item.find('img')
                    pic = ''
                    if img_elem:
                        # 优先获取data-original（真实图片URL），然后是data-src，最后是src
                        pic = img_elem.attr('data-original') or img_elem.attr('data-src') or img_elem.attr('src') or ''
                        if pic and not pic.startswith('http'):
                            pic = self.host + pic if pic.startswith('/') else ''

                    # 获取备注信息
                    note_elem = item.find('.module-item-note')
                    remarks = self.fix_encoding(note_elem.text()) if note_elem else ''

                    videos.append({
                        'vod_id': vod_id,
                        'vod_name': title,
                        'vod_pic': pic,
                        'vod_year': '',
                        'vod_remarks': remarks
                    })
                except Exception as e:
                    self.log(f"解析搜索结果时出错: {e}")
                    continue
            
            return {'list': videos, 'page': pg}
            
        except Exception as e:
            self.log(f"搜索时出错: {e}")
            return {'list': [], 'page': pg}

    def playerContent(self, flag, id, vipFlags):
        """获取播放地址"""
        try:
            # 播放页面URL
            play_url = f"{self.host}{id}"
            
            response = self.fetch_with_encoding(play_url, headers=self.headers)
            doc = self.getpq(response.text)
            
            # 查找播放器配置
            scripts = doc('script')
            for script in scripts.items():
                script_text = script.text()
                if 'player' in script_text and ('url' in script_text):
                    # 尝试提取播放地址
                    url_match = re.search(r'"url"\s*:\s*"([^"]+)"', script_text)
                    if url_match:
                        video_url = url_match.group(1)
                        return {
                            'parse': 0,
                            'url': video_url,
                            'header': self.headers
                        }
            
            # 如果没有找到直接播放地址，返回播放页面让系统解析
            return {
                'parse': 1,
                'url': play_url,
                'header': self.headers
            }
            
        except Exception as e:
            self.log(f"获取播放地址时出错: {e}")
            return {
                'parse': 1,
                'url': f"{self.host}{id}",
                'header': self.headers
            }

    def localProxy(self, param):
        pass

    def fix_encoding(self, text):
        """修复UTF-8编码问题"""
        if not text:
            return text

        try:
            # 检查是否包含乱码特征（常见的UTF-8乱码模式）
            garbled_patterns = [
                '\u00e4\u00b8', '\u00e5', '\u00e6', '\u00e7', '\u00e8', '\u00e9',  # 常见乱码前缀
                '\u00c3\u00a4', '\u00c3\u00a5', '\u00c3\u00a6',  # UTF-8被误解为Latin1
                '\u00ef\u00bc', '\u00e2\u0080'  # 标点符号乱码
            ]

            has_garbled = any(pattern in text for pattern in garbled_patterns)

            if has_garbled:
                self.log("检测到编码问题，尝试修复...")

                # 方法1: 尝试Latin1->UTF-8转换
                try:
                    fixed = text.encode('latin1').decode('utf-8')
                    # 检查是否修复成功（包含中文字符）
                    if re.search(r'[\u4e00-\u9fff]', fixed):
                        self.log("使用Latin1->UTF-8修复成功")
                        return fixed
                except Exception as e:
                    self.log(f"Latin1->UTF-8修复失败: {e}")

                # 方法2: 尝试其他编码转换
                encodings = ['cp1252', 'iso-8859-1']
                for encoding in encodings:
                    try:
                        fixed = text.encode(encoding).decode('utf-8')
                        if re.search(r'[\u4e00-\u9fff]', fixed):
                            self.log(f"使用{encoding}->UTF-8修复成功")
                            return fixed
                    except:
                        continue

                self.log("编码修复失败，返回原文本")

            return text

        except Exception as e:
            self.log(f"编码修复异常: {e}")
            return text

    def fetch_with_encoding(self, url, **kwargs):
        """带编码处理的请求方法"""
        try:
            response = self.fetch(url, **kwargs)
            # 确保使用UTF-8编码
            response.encoding = 'utf-8'
            return response
        except Exception as e:
            self.log(f"请求失败: {e}")
            raise

    def getpq(self, text):
        """安全的pyquery解析"""
        try:
            return pq(text)
        except Exception as e:
            self.log(f"pyquery解析出错: {e}")
            try:
                return pq(text.encode('utf-8'))
            except:
                return pq('')
