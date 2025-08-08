# -*- coding: utf-8 -*-
# cnotv.com (明月影院) 爬虫插件
# 开发者: Augment Agent
# 网站: https://cnotv.com/

import re
import sys
import json
import urllib.parse
from pyquery import PyQuery as pq
sys.path.append("..")
from base.spider import Spider

class Spider(Spider):
    
    def init(self, extend=""):
        self.extend = extend
        pass

    def getName(self):
        return "明月影院"

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def action(self, action):
        pass

    def destroy(self):
        pass

    # 网站基本配置
    host = 'https://cnotv.com'
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'identity',  # 禁用压缩
        'Referer': 'https://cnotv.com/',
    }

    def homeContent(self, filter):
        """获取首页内容和分类列表"""
        try:
            # 获取首页内容
            response = self.fetch(self.host, headers=self.headers)
            doc = pq(response.text)

            result = {}

            # 提取分类列表 - 基于实际HTML结构
            classes = []
            # 查找导航链接
            nav_links = doc('ul li a')
            for item in nav_links.items():
                href = item.attr('href')
                text = item.text().strip()
                if href and '/vodtype/' in href and text:
                    type_id = re.search(r'/vodtype/(\d+)/', href)
                    if type_id:
                        classes.append({
                            'type_name': text,
                            'type_id': type_id.group(1)
                        })

            result['class'] = classes

            # 提取首页推荐视频列表 - 使用.module-item容器
            videos = []
            video_containers = doc('.module-item')

            for container in video_containers.items():
                video_info = self.extract_video_info_from_container(container)
                if video_info:
                    videos.append(video_info)

            result['list'] = videos
            return result

        except Exception as e:
            self.log(f"homeContent error: {str(e)}")
            return {'class': [], 'list': []}

    def homeVideoContent(self):
        pass

    def categoryContent(self, tid, pg, filter, extend):
        """获取分类页面内容"""
        try:
            # 构建分类页面URL
            if pg == '1' or pg == 1:
                url = f"{self.host}/vodtype/{tid}/"
            else:
                url = f"{self.host}/vodtype/{tid}/page/{pg}/"

            response = self.fetch(url, headers=self.headers)
            doc = pq(response.text)

            result = {}
            videos = []

            # 提取视频列表 - 使用.module-item容器
            video_containers = doc('.module-item')
            if len(video_containers):
                # 分类页面使用容器结构
                for container in video_containers.items():
                    video_info = self.extract_video_info_from_container(container)
                    if video_info:
                        videos.append(video_info)
            else:
                # 备用方案：直接查找链接
                video_links = doc('a[href*="/voddetail/"]')
                for link in video_links.items():
                    video_info = self.extract_video_info_from_link(link)
                    if video_info:
                        videos.append(video_info)

            result['list'] = videos
            result['page'] = int(pg)
            result['pagecount'] = 9999  # 设置较大值，实际翻页时会自动调整
            result['limit'] = 20
            result['total'] = 999999

            return result

        except Exception as e:
            self.log(f"categoryContent error: {str(e)}")
            return {'list': [], 'page': int(pg), 'pagecount': 1, 'limit': 20, 'total': 0}

    def detailContent(self, ids):
        """获取视频详情"""
        try:
            video_id = ids[0]
            url = f"{self.host}/voddetail/{video_id}/"
            
            response = self.fetch(url, headers=self.headers)
            doc = pq(response.text)
            
            # 提取视频详细信息
            vod = {}
            
            # 基本信息
            vod['vod_id'] = video_id
            vod['vod_name'] = doc('h1').text().strip() or doc('.detail-title').text().strip()
            
            # 图片
            pic_elem = doc('.detail-pic img, .module-item-pic img').eq(0)
            vod['vod_pic'] = pic_elem.attr('src') or pic_elem.attr('data-src') or ''
            if vod['vod_pic'] and not vod['vod_pic'].startswith('http'):
                vod['vod_pic'] = self.host + vod['vod_pic']
            
            # 提取详情信息
            info_items = doc('.detail-info p, .module-info-item')
            for item in info_items.items():
                text = item.text().strip()
                if '导演' in text:
                    vod['vod_director'] = text.replace('导演：', '').replace('导演', '').strip()
                elif '主演' in text:
                    vod['vod_actor'] = text.replace('主演：', '').replace('主演', '').strip()
                elif '年份' in text or '上映' in text:
                    year_match = re.search(r'(\d{4})', text)
                    if year_match:
                        vod['vod_year'] = year_match.group(1)
                elif '地区' in text:
                    vod['vod_area'] = text.replace('地区：', '').replace('地区', '').strip()
                elif '类型' in text:
                    vod['vod_type'] = text.replace('类型：', '').replace('类型', '').strip()
            
            # 剧情简介
            content_elem = doc('.detail-content, .module-info-introduction')
            vod['vod_content'] = content_elem.text().strip()
            
            # 备注信息
            remarks_elem = doc('.detail-remarks, .module-item-note')
            vod['vod_remarks'] = remarks_elem.text().strip()
            
            # 提取播放源和播放列表
            play_sources = []
            play_urls = []

            # 查找播放源标签
            source_tabs = doc('.play-source-tab a, .module-tab-item')
            if not len(source_tabs):
                # 如果没有找到播放源标签，设置默认播放源
                play_sources.append('1080P8')
            else:
                for tab in source_tabs.items():
                    source_name = tab.text().strip()
                    if source_name:
                        play_sources.append(source_name)

            # 查找播放链接 - 使用实际找到的选择器
            play_links = doc('a[href*="/vodplay/"]')
            episodes = []

            for link in play_links.items():
                ep_name = link.text().strip()
                ep_url = link.attr('href')

                # 跳过空的或重复的"立即播放"链接
                if ep_url and ep_name and ep_name != '立即播放':
                    episodes.append(f"{ep_name}${ep_url}")

            # 如果没有找到有效的剧集，但有播放链接，使用第一个
            if not episodes and len(play_links):
                first_link = play_links.eq(0)
                ep_url = first_link.attr('href')
                if ep_url:
                    episodes.append(f"播放${ep_url}")

            if episodes:
                play_urls.append('#'.join(episodes))

            vod['vod_play_from'] = '$$$'.join(play_sources) if play_sources else '默认播放源'
            vod['vod_play_url'] = '$$$'.join(play_urls) if play_urls else ''
            
            result = {"list": [vod]}
            return result
            
        except Exception as e:
            self.log(f"detailContent error: {str(e)}")
            return {"list": []}

    def searchContent(self, key, quick, pg="1"):
        """搜索功能"""
        try:
            # URL编码关键词
            encoded_key = urllib.parse.quote(key)
            url = f"{self.host}/vodsearch/{encoded_key}-------------/"

            response = self.fetch(url, headers=self.headers)
            doc = pq(response.text)

            videos = []
            seen_ids = set()  # 用于去重

            # 基于实际HTML结构查找搜索结果
            # 优先查找.module-search-item容器
            search_containers = doc('.module-search-item')
            if len(search_containers):
                for container in search_containers.items():
                    video_info = self.extract_video_info_from_search_container(container)
                    if video_info and video_info['vod_id'] not in seen_ids:
                        videos.append(video_info)
                        seen_ids.add(video_info['vod_id'])
            else:
                # 备用方案：直接查找链接并去重
                video_links = doc('a[href*="/voddetail/"]')
                for link in video_links.items():
                    video_info = self.extract_video_info_from_link(link)
                    if video_info and video_info['vod_id'] not in seen_ids:
                        videos.append(video_info)
                        seen_ids.add(video_info['vod_id'])

            return {'list': videos, 'page': int(pg)}

        except Exception as e:
            self.log(f"searchContent error: {str(e)}")
            return {'list': [], 'page': int(pg)}

    def playerContent(self, flag, id, vipFlags):
        """获取播放地址"""
        try:
            url = f"{self.host}{id}" if id.startswith('/') else f"{self.host}/vodplay/{id}/"
            
            response = self.fetch(url, headers=self.headers)
            doc = pq(response.text)
            
            # 查找播放器配置
            script_texts = doc('script').text()
            
            # 尝试提取播放地址
            play_url = ""
            
            # 方法1: 查找直接的视频URL
            url_patterns = [
                r'"url"\s*:\s*"([^"]+\.m3u8[^"]*)"',
                r'"url"\s*:\s*"([^"]+\.mp4[^"]*)"',
                r'player_aaaa\s*=\s*{[^}]*"url"\s*:\s*"([^"]+)"',
                r'var\s+player\s*=\s*{[^}]*"url"\s*:\s*"([^"]+)"'
            ]
            
            for pattern in url_patterns:
                match = re.search(pattern, script_texts)
                if match:
                    play_url = match.group(1)
                    break
            
            # 如果没有找到直接URL，尝试查找iframe
            if not play_url:
                iframe = doc('iframe').attr('src')
                if iframe:
                    play_url = iframe
            
            result = {
                "parse": 1 if not play_url.endswith(('.m3u8', '.mp4')) else 0,
                "url": play_url,
                "header": self.headers
            }
            
            return result
            
        except Exception as e:
            self.log(f"playerContent error: {str(e)}")
            return {"parse": 1, "url": "", "header": {}}

    def localProxy(self, param):
        pass

    def extract_video_info_from_link(self, link):
        """从链接元素提取视频信息"""
        try:
            href = link.attr('href')
            if not href or '/voddetail/' not in href:
                return None

            # 提取视频ID
            id_match = re.search(r'/voddetail/(\d+)/', href)
            if not id_match:
                return None

            video_id = id_match.group(1)

            # 提取标题 - 优化处理
            title = link.attr('title') or ''
            if not title:
                # 从链接文本中提取，去除多余信息
                link_text = link.text().strip()
                # 尝试提取视频标题（通常在第二行或包含中文的部分）
                lines = [line.strip() for line in link_text.split('\n') if line.strip()]
                for line in lines:
                    # 跳过分类信息（如"国产剧"、"爱情片"等）
                    if line not in ['国产剧', '爱情片', '动作片', '喜剧片', '剧情片', '科幻片', '恐怖片', '战争片', '国产综艺', '日本动漫', '欧美动漫']:
                        # 如果包含演员信息，只取标题部分
                        if ',' in line and len(line) > 20:
                            # 可能是"标题 演员1, 演员2"的格式
                            parts = line.split(',')
                            if len(parts) > 1:
                                title = parts[0].strip()
                                break
                        else:
                            title = line
                            break

            # 查找相关的图片
            pic = ''
            # 尝试在同一父元素中查找图片
            parent = link.parent()
            img_elem = parent.find('img').eq(0)
            if img_elem.length:
                # 优先使用data-src（真实图片），fallback到src（占位图片）
                pic = img_elem.attr('data-src') or img_elem.attr('src') or ''

            # 如果没找到图片，尝试在链接内部查找
            if not pic:
                img_elem = link.find('img').eq(0)
                if img_elem.length:
                    # 优先使用data-src（真实图片），fallback到src（占位图片）
                    pic = img_elem.attr('data-src') or img_elem.attr('src') or ''

            if pic and not pic.startswith('http'):
                pic = self.host + pic

            # 提取备注信息 - 查找相关文本
            remarks = ''
            # 尝试从父元素中查找备注
            parent_text = parent.text()
            if '更新至' in parent_text:
                remarks_match = re.search(r'更新至【([^】]+)】', parent_text)
                if remarks_match:
                    remarks = f"更新至{remarks_match.group(1)}"
                else:
                    # 尝试其他格式
                    remarks_match = re.search(r'更新至(\d+)', parent_text)
                    if remarks_match:
                        remarks = f"更新至{remarks_match.group(1)}"
            elif '第' in parent_text and '集' in parent_text:
                remarks_match = re.search(r'第(\d+)集', parent_text)
                if remarks_match:
                    remarks = f"第{remarks_match.group(1)}集"

            if not title:
                return None

            return {
                'vod_id': video_id,
                'vod_name': title,
                'vod_pic': pic,
                'vod_remarks': remarks
            }

        except Exception as e:
            self.log(f"extract_video_info_from_link error: {str(e)}")
            return None

    def extract_video_info_from_container(self, container):
        """从.module-item容器提取视频信息"""
        try:
            # 查找容器内的视频链接
            video_links = container.find('a[href*="/voddetail/"]')
            if not len(video_links):
                return None

            # 获取第一个视频链接（通常是主链接）
            main_link = video_links.eq(0)
            href = main_link.attr('href')
            if not href:
                return None

            # 提取视频ID
            id_match = re.search(r'/voddetail/(\d+)/', href)
            if not id_match:
                return None

            video_id = id_match.group(1)

            # 查找容器内的图片
            img_elem = container.find('img').eq(0)
            pic = ''
            title_from_img = ''

            if img_elem.length:
                # 优先使用data-src（真实图片），fallback到src（占位图片）
                pic = img_elem.attr('data-src') or img_elem.attr('src') or ''
                title_from_img = img_elem.attr('alt') or ''

                # 确保图片URL是完整的HTTP链接
                if pic and not pic.startswith('http'):
                    pic = self.host + pic

            # 提取标题 - 优先使用图片alt，然后是链接文本
            title = title_from_img
            if not title:
                # 查找标题链接（通常是h3或.title内的链接）
                title_links = container.find('h3 a, .title a, .module-item-titlebox a')
                if len(title_links):
                    title = title_links.eq(0).text().strip()

                if not title:
                    # 使用主链接的文本，但需要清理
                    link_text = main_link.text().strip()
                    lines = [line.strip() for line in link_text.split('\n') if line.strip()]
                    for line in lines:
                        if line not in ['国产剧', '爱情片', '动作片', '喜剧片', '剧情片', '科幻片', '恐怖片', '战争片', '国产综艺', '日本动漫', '欧美动漫']:
                            if ',' in line and len(line) > 20:
                                title = line.split(',')[0].strip()
                                break
                            else:
                                title = line
                                break

            # 提取备注信息
            remarks = ''
            remarks_elem = container.find('.module-item-note, .note, .remarks')
            if len(remarks_elem):
                remarks = remarks_elem.eq(0).text().strip()

            if not title:
                return None

            return {
                'vod_id': video_id,
                'vod_name': title,
                'vod_pic': pic,
                'vod_remarks': remarks
            }

        except Exception as e:
            self.log(f"extract_video_info_from_container error: {str(e)}")
            return None

    def extract_video_info_from_search_container(self, container):
        """从搜索结果容器提取视频信息"""
        try:
            # 在搜索容器中查找标题链接（避免剧集链接）
            title_links = container.find('h3 a[href*="/voddetail/"]')
            if not len(title_links):
                # 备用：查找所有视频链接，选择文本最长的（通常是标题）
                all_links = container.find('a[href*="/voddetail/"]')
                if not len(all_links):
                    return None

                # 选择文本最长的链接作为标题链接
                best_link = None
                max_length = 0
                for link in all_links.items():
                    text = link.text().strip()
                    if len(text) > max_length and '第' not in text and '集' not in text:
                        max_length = len(text)
                        best_link = link

                if not best_link:
                    best_link = all_links.eq(0)

                title_links = best_link
            else:
                title_links = title_links.eq(0)

            href = title_links.attr('href')
            if not href:
                return None

            # 提取视频ID
            id_match = re.search(r'/voddetail/(\d+)/', href)
            if not id_match:
                return None

            video_id = id_match.group(1)

            # 提取标题
            title = title_links.text().strip()

            # 查找图片
            img_elem = container.find('img').eq(0)
            pic = ''
            if img_elem.length:
                # 优先使用data-src（真实图片），fallback到src（占位图片）
                pic = img_elem.attr('data-src') or img_elem.attr('src') or ''
                if pic and not pic.startswith('http'):
                    pic = self.host + pic

            # 提取备注
            remarks = ''
            remarks_elem = container.find('.note, .remarks, .video-serial')
            if len(remarks_elem):
                remarks = remarks_elem.eq(0).text().strip()

            if not title:
                return None

            return {
                'vod_id': video_id,
                'vod_name': title,
                'vod_pic': pic,
                'vod_remarks': remarks
            }

        except Exception as e:
            self.log(f"extract_video_info_from_search_container error: {str(e)}")
            return None

    def extract_video_info(self, item):
        """提取视频信息的通用方法（保持兼容性）"""
        try:
            # 查找链接
            link_elem = item.find('a[href*="/voddetail/"]').eq(0)
            if link_elem.length:
                return self.extract_video_info_from_link(link_elem)
            return None

        except Exception as e:
            self.log(f"extract_video_info error: {str(e)}")
            return None
