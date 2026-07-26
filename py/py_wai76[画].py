#coding=utf-8
#!/usr/bin/python
import sys
import json
import re
from urllib.parse import urljoin, quote
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
	def getName(self):
		return "心动美图"

	def init(self, extend):
		self.baseUrl = "https://www.wai76.com"
		self.header = {
			"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
		}

	def isVideoFormat(self, url):
		return False

	def manualVideoCheck(self):
		pass

	def homeContent(self, filter):
		result = {}
		try:
			r = self.fetch(self.baseUrl, headers=self.header, timeout=10)
			if r.status_code != 200:
				return {'class': []}
			
			html_content = r.text
			
			# 从导航菜单中提取分类
			category_pattern = r'<li class="menu-item.*?"><a href="(.*?)">(.*?)</a></li>'
			categories = re.findall(category_pattern, html_content)
			
			classList = []
			seen_names = set()
			
			for url, name in categories:
				if ('/tag/' in url or '/category/' in url) and name and name not in seen_names:
					# 确保URL是完整的
					if not url.startswith('http'):
						url = urljoin(self.baseUrl, url)
					seen_names.add(name)
					classList.append({
						"type_name": name,
						"type_id": url
					})
			
			# 如果没有从导航菜单获取到分类，使用默认分类
			if not classList:
				default_categories = [
					('https://www.wai76.com/tag/秀人网/', '秀人网'),
					('https://www.wai76.com/tag/语画界/', '语画界'),
					('https://www.wai76.com/tag/爱蜜社/', '爱蜜社'),
					('https://www.wai76.com/tag/美媛馆/', '美媛馆'),
					('https://www.wai76.com/tag/尤果圈/', '尤果圈'),
					('https://www.wai76.com/tag/丝袜/', '丝袜'),
					('https://www.wai76.com/tag/制服/', '制服'),
					('https://www.wai76.com/tag/内衣/', '内衣'),
				]
				for url, name in default_categories:
					if name not in seen_names:
						seen_names.add(name)
						classList.append({
							"type_name": name,
							"type_id": url
						})
			
			classList.sort(key=lambda x: x['type_name'])
			result['class'] = classList[:100]
			
		except Exception as e:
			print(f"Error in homeContent: {e}")
			return {'class': []}
		
		return result

	def homeVideoContent(self):
		return {}

	def categoryContent(self, tid, page, filter, extend):
		result = {}
		try:
			page = int(page)
			category_url = tid
			
			# 添加分页参数
			if page > 1:
				if '?' in category_url:
					category_url += f'&paged={page}'
				else:
					category_url += f'?paged={page}'
			
			r = self.fetch(category_url, headers=self.header, timeout=10)
			
			if r.status_code != 200:
				return {'list': [], 'page': page, 'pagecount': page, 'limit': 0, 'total': 0}
			
			html_content = r.text
			
			videos = []
			
			# 提取文章信息，包括标题、链接和图片
			post_pattern = r'<div id="post-\d+" class="clear.*?">.*?<a class="thumbnail-link" href="([^"]+)">.*?<img[^>]*src="([^"]+)"[^>]*>.*?<h2 class="entry-title"><a[^>]*href="[^"]+"[^>]*>(.*?)</a></h2>.*?</div>'
			posts = re.findall(post_pattern, html_content, re.DOTALL)
			
			for url, img, title in posts:
				title = self.cleanText(title)
				img = img.strip()
				
				if not img.startswith('http'):
					img = urljoin(self.baseUrl, img)
				
				videos.append({
					"vod_id": url,
					"vod_name": title,
					"vod_pic": img,
					"vod_remarks": ""
				})
			
			# 检查是否有下一页
			has_next_page = 'class="next page-numbers"' in html_content
			pagecount = page + 1 if has_next_page else page
			
			result['list'] = videos
			result['page'] = page
			result['pagecount'] = pagecount
			result['limit'] = len(videos)
			result['total'] = len(videos) * pagecount
			
		except Exception as e:
			print(f"Error in categoryContent: {e}")
			return {'list': [], 'page': page, 'pagecount': page, 'limit': 0, 'total': 0}
		
		return result

	def detailContent(self, ids):
		result = {}
		try:
			detail_url = ids[0]
			r = self.fetch(detail_url, headers=self.header, timeout=10)
			
			if r.status_code != 200:
				return {'list': []}
			
			html_content = r.text
			
			title_match = re.search(r'<h1 class="entry-title">(.*?)</h1>', html_content, re.DOTALL)
			if title_match:
				title = self.cleanText(title_match.group(1))
			else:
				title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html_content, re.DOTALL)
				if title_match:
					title = self.cleanText(title_match.group(1))
				else:
					url_title = detail_url.split('/')[-2]
					title = url_title.replace('_', ' ').replace('-', ' ')
			
			# 提取封面图
			cover_img = ""
			img_match = re.search(r'<img[^>]*src=["\']([^"\']+)"\'', html_content)
			if img_match:
				cover_img = img_match.group(1)
				if not cover_img.startswith('http'):
					cover_img = urljoin(self.baseUrl, cover_img)
			
			vod = {
				"vod_id": ids[0],
				"vod_name": title,
				"vod_pic": cover_img,
				"type_name": "图片",
				"vod_year": "",
				"vod_content": "点击查看完整图片",
				"vod_play_from": "图片播放",
				"vod_play_url": f"完整图片${detail_url}",
				"vod_player": "pics"
			}
			
			result['list'] = [vod]
			
		except Exception as e:
			print(f"Error in detailContent: {e}")
			return {'list': []}
		
		return result

	def searchContent(self, key, quick, pg='1'):
		return self.searchContentPage(key, quick, pg)

	def searchContentPage(self, key, quick, page):
		result = {}
		try:
			page = int(page)
			search_url = f"{self.baseUrl}/?s={quote(key)}&paged={page}"
			
			r = self.fetch(search_url, headers=self.header, timeout=10)
			
			if r.status_code != 200:
				return {'list': []}
			
			html_content = r.text
			
			videos = []
			
			# 提取文章信息，使用与categoryContent相同的模式
			post_pattern = r'<div id="post-\d+" class="clear.*?">.*?<a class="thumbnail-link" href="([^"]+)">.*?<img[^>]*src="([^"]+)"[^>]*>.*?<h2 class="entry-title"><a[^>]*href="[^"]+"[^>]*>(.*?)</a></h2>.*?</div>'
			posts = re.findall(post_pattern, html_content, re.DOTALL)
			
			for url, img, title in posts:
				title = self.cleanText(title)
				img = img.strip()
				
				if not img.startswith('http'):
					img = urljoin(self.baseUrl, img)
				
				videos.append({
					"vod_id": url,
					"vod_name": title,
					"vod_pic": img,
					"vod_remarks": ""
				})
			
			# 检查是否有下一页
			has_next_page = 'class="next page-numbers"' in html_content
			pagecount = page + 1 if has_next_page else page
			
			result['list'] = videos
			result['page'] = page
			result['pagecount'] = pagecount
			result['limit'] = len(videos)
			result['total'] = len(videos) * pagecount
			
		except Exception as e:
			print(f"Error in searchContentPage: {e}")
			return {'list': []}
		
		return result

	def playerContent(self, flag, id, vipFlags):
		# id 是 detailContent 传入的文章链接
		images = self._scrape_images_with_pages(id)
		
		# 确保至少有一张图片
		if not images:
			# 使用默认图库路径
			gallery_path = 'mjixnji/mzk4njq'
			print(f"使用默认图库路径: {gallery_path}")
			
			# 构建图片URL
			for i in range(1, 17):
				img_url = f"https://www.wai76.com/gallery/{gallery_path}/{i:03d}.webp"
				images.append(img_url)
		
		novel_data = "&&".join(images)
		
		return {
			"parse": 0,
			"playUrl": "",
			"url": f'pics://{novel_data}',
			"header": ""
		}
	
	def _scrape_images_with_pages(self, url):
		images = []
		max_pages = 10  # 限制最大页数，避免卡顿
		max_images = 500  # 增加最大图片数量限制，确保能爬取所有分页
		max_workers = 3  # 最大并发线程数
		
		# 首先处理第一页
		base_url = url.rstrip('/')
		
		# 构建所有要爬取的页面URL
		page_urls = []
		for page in range(1, max_pages + 1):
			if page == 1:
				current_url = base_url + '/'
			else:
				current_url = f"{base_url}/{page}/"
			page_urls.append((page, current_url))
		
		# 使用线程池并发爬取
		all_page_images = {}
		lock = threading.Lock()
		
		def scrape_page(page_info):
			page_num, page_url = page_info
			print(f"爬取页面: {page_url}")
			
			try:
				r = self.fetch(page_url, headers=self.header, timeout=10)
				if not r or r.status_code != 200:
					print(f"页面 {page_url} 不存在")
					return page_num, []
				
				html_content = r.text
				
				# 提取图片URL - 改进的正则表达式
				# 尝试多种图片URL格式
				img_patterns = [
					r'https://www\.wai76\.com/gallery/[^"\s\)]+\.(?:jpg|jpeg|png|gif|webp)',  # 完整URL
					r'gallery/[^"\s\)]+\.(?:jpg|jpeg|png|gif|webp)',  # 相对路径
					r'<img[^>]+src=["\']([^"\']+)"\'',  # img标签src
					r'<img[^>]+data-src=["\']([^"\']+)"\''  # img标签data-src
				]
				
				# 遍历所有图片模式
				page_images = []
				for pattern in img_patterns:
					imgs = re.findall(pattern, html_content, re.IGNORECASE)
					for img in imgs:
						img = img.strip()
						# 处理相对路径
						if not img.startswith('http'):
							if img.startswith('/'):
								img = self.baseUrl + img
							else:
								img = self.baseUrl + '/' + img
						# 过滤掉封面图和重复图片
						if '/cover/' not in img and img not in page_images:
							page_images.append(img)
				
				print(f"页面 {page_url} 提取到 {len(page_images)} 张图片")
				return page_num, page_images
				
			except Exception as e:
				print(f"爬取页面 {page_url} 时出错: {e}")
				return page_num, []
		
		# 使用线程池并发执行
		with ThreadPoolExecutor(max_workers=max_workers) as executor:
			future_to_page = {executor.submit(scrape_page, page_info): page_info for page_info in page_urls}
			
			for future in as_completed(future_to_page):
				page_num, page_images = future.result()
				all_page_images[page_num] = page_images
		
		# 按页面顺序合并图片
		for page_num in sorted(all_page_images.keys()):
			for img in all_page_images[page_num]:
				if img not in images:
					images.append(img)
			
			print(f"第 {page_num} 页合并后总共 {len(images)} 张图片")
			
			# 如果已经获取了足够的图片，停止合并
			if len(images) >= max_images:
				print(f"已获取足够图片（{max_images}张），停止合并")
				break
		
		# 如果没有从页面提取到图片，尝试从gallery路径构建
		if not images:
			r = self.fetch(url, headers=self.header, timeout=10)
			if r and r.status_code == 200:
				html_content = r.text
				gallery_pattern = r'gallery/([^/]+/[^/]+)'
				gallery_matches = re.findall(gallery_pattern, html_content)
				
				if gallery_matches:
					gallery_path = gallery_matches[0]
					print(f"找到图库路径: {gallery_path}")
					
					# 构建图片URL
					for i in range(1, 17):
						img_url = f"https://www.wai76.com/gallery/{gallery_path}/{i:03d}.webp"
						if img_url not in images:
							images.append(img_url)
		
		return images

	def localProxy(self, param):
		pass

	def destroy(self):
		pass