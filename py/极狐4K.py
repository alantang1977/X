import requests
from pyquery import PyQuery as pq
import json
from base64 import b64encode, b64decode

class Fox4kSpider:
    def __init__(self):
        self.base_url = "https://4kfox.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": self.base_url
        }

    def _fetch_page(self, url):
        """通用页面请求方法"""
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.encoding = "utf-8"
            if response.status_code == 200:
                return response.text
            print(f"请求失败，状态码: {response.status_code}，URL: {url}")
            return None
        except Exception as e:
            print(f"请求出错: {str(e)}，URL: {url}")
            return None

    def get_categories(self):
        """获取首页导航栏分类"""
        categories = []
        html = self._fetch_page(self.base_url)
        if not html:
            return categories
        
        doc = pq(html)
        # 定位导航栏分类（排除首页、搜索等非分类项）
        for item in doc(".main-nav .menu-item a").items():
            href = item.attr("href")
            if href and "/category/" in href:
                # 提取分类ID（从URL中解析）
                cat_id = href.strip("/").split("/")[-1]
                cat_name = item.text().strip()
                if cat_name and cat_id:
                    categories.append({
                        "id": cat_id,
                        "name": cat_name,
                        "url": href
                    })
        return categories

    def get_home_recommendations(self):
        """获取首页推荐视频"""
        recommendations = []
        html = self._fetch_page(self.base_url)
        if not html:
            return recommendations
        
        doc = pq(html)
        # 定位首页推荐视频列表
        for item in doc(".movie-grid .movie-item").items():
            # 提取视频基本信息
            link = item.find("a").attr("href")
            if not link or "/movies/" not in link:
                continue
            
            # 解析视频ID
            video_id = link.strip("/").split("/")[-1]
            title = item.find(".movie-title").text().strip()
            cover = item.find(".movie-poster img").attr("src")
            # 补全封面URL（处理相对路径）
            if cover and not cover.startswith("http"):
                cover = f"{self.base_url}{cover}"
            
            # 提取年份和质量信息
            meta = item.find(".movie-meta").text().split("|")
            year = meta[0].strip() if len(meta) > 0 else ""
            quality = meta[1].strip() if len(meta) > 1 else ""
            
            recommendations.append({
                "id": video_id,
                "title": title,
                "cover": cover,
                "year": year,
                "quality": quality,
                "url": link
            })
        return recommendations

    def get_category_videos(self, cat_id, page=1):
        """获取分类视频列表（支持分页）"""
        videos = {
            "list": [],
            "current_page": page,
            "total_pages": 0,
            "has_more": False
        }
        
        # 构造分类页URL
        url = f"{self.base_url}/category/{cat_id}/page/{page}/"
        html = self._fetch_page(url)
        if not html:
            return videos
        
        doc = pq(html)
        # 解析视频列表
        for item in doc(".movie-grid .movie-item").items():
            link = item.find("a").attr("href")
            if not link or "/movies/" not in link:
                continue
            
            video_id = link.strip("/").split("/")[-1]
            title = item.find(".movie-title").text().strip()
            cover = item.find(".movie-poster img").attr("src")
            if cover and not cover.startswith("http"):
                cover = f"{self.base_url}{cover}"
            
            meta = item.find(".movie-meta").text().split("|")
            year = meta[0].strip() if len(meta) > 0 else ""
            quality = meta[1].strip() if len(meta) > 1 else ""
            
            videos["list"].append({
                "id": video_id,
                "title": title,
                "cover": cover,
                "year": year,
                "quality": quality,
                "url": link
            })
        
        # 解析分页信息
        pagination = doc(".pagination .page-numbers")
        if pagination:
            last_page = pagination.eq(-2).text()  # 倒数第二个是最后一页
            if last_page.isdigit():
                videos["total_pages"] = int(last_page)
                videos["has_more"] = page < videos["total_pages"]
        
        return videos

    def get_video_detail(self, video_id):
        """获取视频详情（标题、封面、描述、播放链接等）"""
        detail = {}
        url = f"{self.base_url}/movies/{video_id}/"
        html = self._fetch_page(url)
        if not html:
            return detail
        
        doc = pq(html)
        
        # 基本信息
        detail["title"] = doc("h1.movie-title").text().strip()
        detail["cover"] = doc(".movie-poster img").attr("src")
        if detail["cover"] and not detail["cover"].startswith("http"):
            detail["cover"] = f"{self.base_url}{detail['cover']}"
        
        # 解析元数据（类型、年份、地区等）
        meta_info = {}
        for meta in doc(".movie-meta .meta-item").items():
            key = meta.find(".meta-label").text().strip().replace(":", "")
            value = meta.find(".meta-value").text().strip()
            meta_info[key] = value
        
        detail["genre"] = meta_info.get("类型", "")  # 类型
        detail["year"] = meta_info.get("年份", "")    # 年份
        detail["country"] = meta_info.get("国家", "") # 地区
        detail["cast"] = meta_info.get("演员", "")    # 演员
        detail["director"] = meta_info.get("导演", "")# 导演
        
        # 剧情描述
        detail["description"] = doc(".movie-description").text().strip()
        
        # 播放链接（多线路）
        play_sources = []
        for source in doc(".playlists .playlist").items():
            source_name = source.find(".playlist-title").text().strip() or f"线路{len(play_sources)+1}"
            episodes = []
            for ep in source.find(".episode").items():
                ep_name = ep.text().strip()
                ep_url = ep.attr("data-src") or ep.attr("href")
                if ep_url and not ep_url.startswith("http"):
                    ep_url = f"{self.base_url}{ep_url}"
                episodes.append({
                    "name": ep_name,
                    "url": ep_url
                })
            play_sources.append({
                "source_name": source_name,
                "episodes": episodes
            })
        
        detail["play_sources"] = play_sources
        return detail

    def search_videos(self, keyword, page=1):
        """搜索视频"""
        results = {
            "list": [],
            "current_page": page,
            "has_more": False
        }
        
        url = f"{self.base_url}/search/?q={keyword}&page={page}"
        html = self._fetch_page(url)
        if not html:
            return results
        
        doc = pq(html)
        # 解析搜索结果
        for item in doc(".movie-grid .movie-item").items():
            link = item.find("a").attr("href")
            if not link or "/movies/" not in link:
                continue
            
            video_id = link.strip("/").split("/")[-1]
            title = item.find(".movie-title").text().strip()
            cover = item.find(".movie-poster img").attr("src")
            if cover and not cover.startswith("http"):
                cover = f"{self.base_url}{cover}"
            
            meta = item.find(".movie-meta").text().split("|")
            year = meta[0].strip() if len(meta) > 0 else ""
            quality = meta[1].strip() if len(meta) > 1 else ""
            
            results["list"].append({
                "id": video_id,
                "title": title,
                "cover": cover,
                "year": year,
                "quality": quality,
                "url": link
            })
        
        # 检查是否有下一页
        next_page = doc(".pagination .next.page-numbers").attr("href")
        results["has_more"] = bool(next_page)
        return results

    @staticmethod
    def encode_data(data):
        """Base64编码数据（用于处理播放链接）"""
        return b64encode(json.dumps(data).encode()).decode()

    @staticmethod
    def decode_data(encoded_data):
        """Base64解码数据"""
        return json.loads(b64decode(encoded_data).decode())


# 使用示例
if __name__ == "__main__":
    spider = Fox4kSpider()
    
    # 1. 获取分类
    print("=== 网站分类 ===")
    categories = spider.get_categories()
    for cat in categories[:3]:  # 打印前3个分类
        print(f"{cat['name']} ({cat['id']}): {cat['url']}")
    
    # 2. 获取首页推荐
    print("\n=== 首页推荐视频 ===")
    recommendations = spider.get_home_recommendations()
    for video in recommendations[:3]:  # 打印前3个推荐
        print(f"{video['title']} ({video['year']} {video['quality']}): {video['id']}")
    
    # 3. 获取分类视频（以第一个分类为例）
    if categories:
        print("\n=== 分类视频列表 ===")
        cat_id = categories[0]["id"]
        category_videos = spider.get_category_videos(cat_id, page=1)
        print(f"分类 {cat_id} 第1页: {len(category_videos['list'])} 个视频")
        for video in category_videos["list"][:2]:
            print(f"{video['title']}: {video['url']}")
    
    # 4. 获取视频详情（以第一个推荐视频为例）
    if recommendations:
        print("\n=== 视频详情 ===")
        video_id = recommendations[0]["id"]
        detail = spider.get_video_detail(video_id)
        print(f"标题: {detail.get('title')}")
        print(f"类型: {detail.get('genre')}")
        print(f"简介: {detail.get('description')[:100]}...")  # 打印前100字
        print(f"播放线路数: {len(detail.get('play_sources', []))}")
    
    # 5. 搜索视频
    print("\n=== 搜索结果 ===")
    search_results = spider.search_videos("avengers", page=1)
    print(f"搜索 'avengers' 第1页: {len(search_results['list'])} 个结果")
    for video in search_results["list"][:2]:
        print(f"{video['title']}: {video['url']}")
