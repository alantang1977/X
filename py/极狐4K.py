# -*- coding: utf-8 -*-
import sys
import time
import requests
from pyquery import PyQuery as pq
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def init(self, extend=""):
        pass

    def getName(self):
        return "4kfox爬虫"

    def isVideoFormat(self, url):
        return any([url.endswith(ext) for ext in ['.mp4', '.m3u8', '.flv', '.avi']])

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    # 网站基础配置
    host = 'https://4kfox.com'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Referer': host
    }

    def homeContent(self, filter):
        """获取首页分类信息"""
        result = {"class": [], "filters": {}}
        try:
            resp = requests.get(self.host, headers=self.headers, timeout=10)
            doc = pq(resp.text)
            
            # 解析分类（导航栏中的主要分类）
            categories = doc('nav#main-nav ul li a').items()
            for item in categories:
                href = item.attr('href')
                if not href or 'javascript' in href:
                    continue
                # 提取分类ID（从URL中截取，如/category/movies -> movies）
                tid = href.strip('/').split('/')[-1]
                type_name = item.text().strip()
                if tid and type_name and type_name not in ['Home', 'TV Shows', 'Movies']:  # 过滤不需要的分类
                    result["class"].append({
                        "type_id": tid,
                        "type_name": type_name
                    })
            
            # 过滤条件（示例：按年份/地区，实际可根据网站筛选器扩展）
            result["filters"] = {}
            return result
        except Exception as e:
            print(f"首页分类解析错误: {e}")
            return result

    def homeVideoContent(self):
        """获取首页推荐视频"""
        try:
            resp = requests.get(self.host, headers=self.headers, timeout=10)
            doc = pq(resp.text)
            
            # 解析首页推荐视频（如Featured、Latest Updates区域）
            video_items = doc('div.post-listing div.item').items()
            video_list = []
            for item in video_items:
                video = self.parse_video_item(item)
                if video:
                    video_list.append(video)
            return {"list": video_list}
        except Exception as e:
            print(f"首页推荐视频解析错误: {e}")
            return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        """获取分类下的视频列表（分页）"""
        result = {"list": [], "page": pg, "pagecount": 1, "limit": 20, "total": 0}
        try:
            # 构造分类页URL（如https://4kfox.com/category/movies/page/2）
            url = f"{self.host}/category/{tid}/page/{pg}" if pg != "1" else f"{self.host}/category/{tid}"
            resp = requests.get(url, headers=self.headers, timeout=10)
            doc = pq(resp.text)
            
            # 解析视频列表
            video_items = doc('div.post-listing div.item').items()
            for item in video_items:
                video = self.parse_video_item(item)
                if video:
                    result["list"].append(video)
            
            # 解析分页（获取总页数）
            pagination = doc('div.pagination span.page-numbers').text()
            if pagination and 'Page' in pagination:
                total_pages = pagination.split('of')[-1].strip()
                result["pagecount"] = int(total_pages) if total_pages.isdigit() else 1
            
            result["total"] = result["pagecount"] * result["limit"]
            return result
        except Exception as e:
            print(f"分类视频解析错误: {e}")
            return result

    def detailContent(self, ids):
        """获取视频详情（根据视频ID，即详情页URL中的标识）"""
        result = {"list": []}
        try:
            # 视频详情页URL（ids为视频标识，如/post-name）
            url = f"{self.host}/{ids}"
            resp = requests.get(url, headers=self.headers, timeout=10)
            doc = pq(resp.text)
            
            # 解析视频详情
            vod_name = doc('h1.entry-title').text().strip()
            if not vod_name:
                return result
            
            # 解析封面图
            vod_pic = doc('div.post-thumbnail img').attr('src') or doc('div.single-post-thumbnail img').attr('src')
            
            # 解析描述
            vod_content = doc('div.entry-content p').text().strip()
            
            # 解析演员/导演（从元数据中提取）
            vod_actor = ", ".join([item.text() for item in doc('div.metadata span:contains("Stars") a').items()])
            vod_director = ", ".join([item.text() for item in doc('div.metadata span:contains("Director") a').items()])
            
            # 解析播放链接（假设在iframe中）
            play_url = doc('div.video-container iframe').attr('src')
            if not play_url:
                # 尝试从按钮中提取播放链接
                play_btn = doc('a:contains("Watch Now")').attr('href')
                play_url = play_btn if play_btn else ""
            
            # 构造播放列表（单线路单集）
            vod_play_from = "Default Line"
            vod_play_url = f"Watch Now${play_url}"
            
            result["list"].append({
                "vod_id": ids,
                "vod_name": vod_name,
                "vod_pic": vod_pic,
                "vod_actor": vod_actor,
                "vod_director": vod_director,
                "vod_content": vod_content,
                "vod_play_from": vod_play_from,
                "vod_play_url": vod_play_url,
                "vod_remarks": "HD"  # 示例：清晰度
            })
            return result
        except Exception as e:
            print(f"视频详情解析错误: {e}")
            return result

    def searchContent(self, key, quick, pg="1"):
        """搜索视频"""
        result = {"list": [], "page": pg}
        try:
            # 构造搜索URL（如https://4kfox.com/?s=keyword&page=1）
            url = f"{self.host}/?s={key}&page={pg}"
            resp = requests.get(url, headers=self.headers, timeout=10)
            doc = pq(resp.text)
            
            # 解析搜索结果中的视频
            video_items = doc('div.post-listing div.item').items()
            for item in video_items:
                video = self.parse_video_item(item)
                if video:
                    result["list"].append(video)
            return result
        except Exception as e:
            print(f"搜索解析错误: {e}")
            return result

    def playerContent(self, flag, id, vipFlags):
        """处理播放链接"""
        # id为播放链接（如https://example.com/stream）
        return {
            "parse": 0,  # 不使用解析器，直接返回链接
            "url": id,
            "header": self.headers
        }

    def parse_video_item(self, item):
        """解析单个视频项（通用方法，用于列表页）"""
        try:
            # 提取视频ID（从URL中获取，如/posts/movie-name -> movie-name）
            link = item.find('a').attr('href')
            if not link:
                return None
            ids = link.strip('/').split('/')[-1]
            
            # 提取标题
            title = item.find('h3.entry-title a').text().strip()
            if not title:
                return None
            
            # 提取封面图
            img = item.find('img').attr('src') or item.find('img').attr('data-src')
            
            # 提取备注（如年份/评分）
            vod_remarks = item.find('span.year').text().strip() or "HD"
            
            return {
                "vod_id": ids,
                "vod_name": title,
                "vod_pic": img,
                "vod_remarks": vod_remarks
            }
        except Exception as e:
            print(f"视频项解析错误: {e}")
            return None

    # 以下方法为兼容原框架，无需修改
    def liveContent(self, url):
        pass

    def isVideoFormat(self, url):
        return any([url.endswith(ext) for ext in ['.mp4', '.m3u8', '.flv', '.avi', '.mov']])

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass
