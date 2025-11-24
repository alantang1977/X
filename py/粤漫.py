#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
粤漫之家(ymvid.com) 爬虫 - PyQuery版本（增强调试版）
专注粤语动漫资源的爬取
"""
import json
import re
import sys
from urllib.parse import urljoin, quote
import requests
from pyquery import PyQuery as pq

sys.path.append('..')
from base.spider import Spider


class Spider(Spider):
    """粤漫之家爬虫类"""

    def __init__(self):
        self.host = 'https://www.ymvid.com'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': f'{self.host}/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        self.debug_mode = True

    def init(self, extend='{}'):
        """初始化配置"""
        try:
            config = json.loads(extend)
            self.proxies = config.get('proxy', {})
        except:
            self.proxies = {}

    def getName(self):
        """返回爬虫名称"""
        return "粤漫之家"

    # ==================== 核心功能方法 ====================

    def homeContent(self, filter):
        """获取首页分类和筛选配置"""
        result = {}

        # 分类配置
        categories = {
            "全部动画": "1",
            "粤语动画": "1-c1",
            "国语动画": "1-c2",
            "连载中": "1-s1",
            "已完结": "1-s2"
        }

        classes = []
        for name, tid in categories.items():
            classes.append({
                'type_id': tid,
                'type_name': name
            })

        result['class'] = classes

        # 筛选器配置
        if filter:
            result['filters'] = {
                '1': [
                    {
                        'key': 'c',
                        'name': '语言',
                        'value': [
                            {'n': '全部', 'v': '0'},
                            {'n': '粤语', 'v': '1'},
                            {'n': '国语', 'v': '2'}
                        ]
                    },
                    {
                        'key': 's',
                        'name': '状态',
                        'value': [
                            {'n': '全部', 'v': '0'},
                            {'n': '连载', 'v': '1'},
                            {'n': '完结', 'v': '2'},
                            {'n': '未播放', 'v': '3'}
                        ]
                    }
                ]
            }

        return result

    def homeVideoContent(self):
        """获取首页推荐视频"""
        try:
            response = self.fetch(self.host)
            if not response:
                self.log("❌ 无法获取首页内容")
                return {'list': []}

            html = pq(response.text)

            # 查找所有视频链接
            all_links = html('a[href*="/play/"]')
            self.log(f"首页找到 {len(all_links)} 个play链接")

            videos = []
            processed_ids = set()

            for link in all_links.items():
                try:
                    video = self._parse_video_item(link, html)
                    if video.get('vod_id') and video['vod_id'] not in processed_ids:
                        processed_ids.add(video['vod_id'])
                        videos.append(video)
                        if len(videos) >= 20:  # 首页最多20个
                            break
                except Exception as e:
                    continue

            self.log(f"✅ 首页成功提取 {len(videos)} 个视频")
            return {'list': videos}

        except Exception as e:
            self.log(f"❌ homeVideoContent错误: {e}")
            return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        """获取分类内容"""
        try:
            pg = int(pg)

            # 构建URL
            url = f'{self.host}/list/{tid}/'
            if pg > 1:
                url = f'{url}page/{pg}/'

            self.log(f"📍 分类URL: {url}")

            response = self.fetch(url)
            if not response:
                return self._empty_result(pg)

            html = pq(response.text)

            # 查找所有视频链接
            all_links = html('a[href*="/play/"]')
            self.log(f"分类页找到 {len(all_links)} 个play链接")

            videos = []
            processed_ids = set()

            for link in all_links.items():
                try:
                    video = self._parse_video_item(link, html)
                    if video.get('vod_id') and video['vod_id'] not in processed_ids:
                        processed_ids.add(video['vod_id'])
                        videos.append(video)
                except:
                    continue

            self.log(f"✅ 分类页成功提取 {len(videos)} 个视频")

            return {
                'list': videos,
                'page': pg,
                'pagecount': 9999,
                'limit': 24,
                'total': 999999
            }

        except Exception as e:
            self.log(f"❌ categoryContent错误: {e}")
            return self._empty_result(int(pg) if isinstance(pg, str) else pg)

    def detailContent(self, ids):
        """获取视频详情"""
        try:
            video_id = ids[0]
            url = f'{self.host}/play/{video_id}'

            response = self.fetch(url)
            if not response:
                return {'list': []}

            html = pq(response.text)

            # 提取基本信息
            vod = {
                'vod_id': video_id,
                'vod_name': html('h1').text() or '未知',
                'vod_content': html('.vod_content').text() or html('.description').text() or '',
                'vod_pic': '',
                'type_name': '动画',
                'vod_year': '',
                'vod_area': '',
                'vod_remarks': '',
                'vod_actor': '',
                'vod_director': ''
            }

            # 提取封面图
            for img in html('img').items():
                img_src = img.attr('data-src') or img.attr('src') or ''
                if img_src and 'logo' not in img_src.lower() and img_src.startswith('http'):
                    if any(keyword in img_src for keyword in ['poster', 'cover', 'thumb']):
                        vod['vod_pic'] = img_src
                        break
                    elif not vod.get('vod_pic'):
                        vod['vod_pic'] = img_src

            # 提取播放源和剧集
            play_from, play_url = self._extract_play_info(html, video_id)

            if play_from and play_url:
                vod['vod_play_from'] = '$'.join(play_from)
                vod['vod_play_url'] = '$'.join(play_url)
                self.log(f"✅ 提取到 {len(play_from)} 个播放源")
            else:
                vod['vod_play_from'] = '默认'
                vod['vod_play_url'] = f"播放${video_id}"
                self.log("⚠️ 未找到播放列表")

            return {'list': [vod]}

        except Exception as e:
            self.log(f"❌ detailContent错误: {e}")
            import traceback
            self.log(traceback.format_exc())
            return {'list': []}

    def searchContent(self, key, quick, pg='1'):
        """搜索功能"""
        try:
            search_url = f'{self.host}/search/{quote(key)}/'
            if pg != '1':
                search_url = f'{self.host}/search/{quote(key)}/page/{pg}/'

            response = self.fetch(search_url)
            if not response:
                return {'list': [], 'page': pg}

            html = pq(response.text)

            all_links = html('a[href*="/play/"]')
            self.log(f"搜索'{key}'找到 {len(all_links)} 个链接")

            videos = []
            processed_ids = set()

            for link in all_links.items():
                try:
                    video = self._parse_video_item(link, html)
                    if video.get('vod_id') and video['vod_id'] not in processed_ids:
                        processed_ids.add(video['vod_id'])
                        videos.append(video)
                except:
                    continue

            self.log(f"✅ 搜索找到 {len(videos)} 个结果")
            return {'list': videos, 'page': pg}

        except Exception as e:
            self.log(f"❌ searchContent错误: {e}")
            return {'list': [], 'page': pg}

    def playerContent(self, flag, id, vipFlags):
        """获取播放链接"""
        try:
            if not id.startswith('http'):
                play_url = f'{self.host}/play/{id}'
            else:
                play_url = id

            response = self.fetch(play_url)
            if not response:
                return {'parse': 1, 'url': play_url, 'header': self.headers}

            # 尝试提取直链
            real_url = self._extract_video_url(response.text)

            if real_url:
                self.log(f"✅ 提取到直链: {real_url[:50]}...")
                return {'parse': 0, 'url': real_url, 'header': self.headers}
            else:
                self.log(f"⚠️ 未找到直链，使用嗅探模式")
                return {'parse': 1, 'url': play_url, 'header': self.headers}

        except Exception as e:
            self.log(f"❌ playerContent错误: {e}")
            return {'parse': 1, 'url': id, 'header': self.headers}

    # ==================== 辅助方法 ====================

    def fetch(self, url, headers=None, timeout=15):
        """统一的HTTP请求方法"""
        if headers is None:
            headers = self.headers

        try:
            response = requests.get(
                url,
                headers=headers,
                proxies=self.proxies,
                timeout=timeout,
                verify=False
            )

            if response.status_code != 200:
                self.log(f"⚠️ HTTP {response.status_code}: {url}")

            response.raise_for_status()
            return response
        except Exception as e:
            self.log(f"❌ 请求失败: {e}")
            return None

    def _parse_video_item(self, item, html=None):
        """解析视频列表项"""
        video = {}

        try:
            # 获取href
            href = item.attr('href') or ''
            if href and '/play/' in href:
                match = re.search(r'/play/(\d+)', href)
                if match:
                    video['vod_id'] = match.group(1)

                    # 提取标题
                    title = (item.text().strip() or
                            item.attr('title') or '')

                    if title and len(title) > 1:
                        video['vod_name'] = title

                    # 提取图片
                    img = item.find('img')
                    if img:
                        img_src = img.attr('data-src') or img.attr('src')
                        if img_src:
                            video['vod_pic'] = urljoin(self.host, img_src)

        except Exception as e:
            if self.debug_mode:
                self.log(f"解析视频项异常: {e}")

        return video

    def _extract_play_info(self, html, video_id):
        """提取播放源和剧集信息"""
        play_from = []
        play_url = []

        try:
            # 查找剧集列表
            all_episode_links = html('a[href*="/play/"]')
            self.log(f"详情页找到 {len(all_episode_links)} 个play链接")

            if len(all_episode_links) > 0:
                play_from.append('默认')
                episodes = []
                processed_ids = set()

                for link in all_episode_links.items():
                    href = link.attr('href')
                    if href:
                        match = re.search(r'/play/(\d+)', href)
                        if match:
                            ep_id = match.group(1)
                            if ep_id != video_id and ep_id not in processed_ids:
                                processed_ids.add(ep_id)
                                ep_name = link.text().strip()

                                # 有效的剧集名
                                if ep_name and len(ep_name) < 50:
                                    episodes.append(f"{ep_name}${ep_id}")
                                elif not ep_name:
                                    episodes.append(f"第{len(episodes)+1}集${ep_id}")

                if episodes:
                    play_url.append('#'.join(episodes))
                    self.log(f"✅ 提取到 {len(episodes)} 集")

        except Exception as e:
            self.log(f"提取播放信息失败: {e}")

        return play_from, play_url

    def _extract_video_url(self, html_content):
        """从HTML中提取视频播放链接"""
        patterns = [
            r'"url"\s*:\s*"([^"]+\.m3u8[^"]*)"',
            r'"url"\s*:\s*"([^"]+\.mp4[^"]*)"',
            r'"playUrl"\s*:\s*"([^"]+)"',
            r'var\s+url\s*=\s*["\']([^"\']+)["\']',
            r'src\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'https?://[^"\'<>\s]+\.m3u8[^"\'<>\s]*',
            r'https?://[^"\'<>\s]+\.mp4[^"\'<>\s]*'
        ]

        for pattern in patterns:
            matches = re.findall(pattern, html_content)
            if matches:
                url = matches[0].replace('\\/', '/')
                return url

        return ''

    def _empty_result(self, pg):
        """返回空结果"""
        return {
            'list': [],
            'page': pg,
            'pagecount': 1,
            'limit': 24,
            'total': 0
        }

    def log(self, message):
        """日志输出"""
        print(f"[粤漫之家] {message}")

    # ==================== 框架必需方法 ====================

    def isVideoFormat(self, url):
        """判断URL是否为视频格式"""
        video_formats = ['.m3u8', '.mp4', '.flv', '.ts']
        return any(fmt in url.lower() for fmt in video_formats)

    def manualVideoCheck(self):
        """是否需要手动检查视频"""
        return False

    def localProxy(self, param):
        """本地代理功能"""
        pass

    def destroy(self):
        """清理资源"""
        pass
