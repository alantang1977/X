import sys
import json
import re
import requests
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def __init__(self):
        self.name = "电影云集"
        self.host = "https://dyyjpro.com"
        self.timeout = 15
        self.limit = 20
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        self.default_image = "https://picsum.photos/300/400"
        
        # 分类映射表
        self.category_map = {
            "dianying": "电影",
            "ju": "剧集", 
            "dongman": "动漫",
            "zongyi": "综艺",
            "duanju": "短剧",
            "xuexi": "学习",
            "duwu": "读物",
            "yinpin": "音频"
        }
    
    def getName(self):
        return self.name
    
    def init(self, extend=""):
        print(f"============{extend}============")
    
    def homeContent(self, filter):
        return {
            'class': [
                {"type_name": "电影", "type_id": "dianying"},
                {"type_name": "剧集", "type_id": "ju"},
                {"type_name": "动漫", "type_id": "dongman"},
                {"type_name": "综艺", "type_id": "zongyi"},
                {"type_name": "短剧", "type_id": "duanju"},
                {"type_name": "学习", "type_id": "xuexi"},
                {"type_name": "读物", "type_id": "duwu"},
                {"type_name": "音频", "type_id": "yinpin"}
            ]
        }
    
    def categoryContent(self, tid, pg, filter, extend):
        result = {'list': [], 'page': pg, 'pagecount': 9999, 'limit': self.limit, 'total': 999999}
        
        try:
            # 获取分类中文名
            if tid in self.category_map:
                category_name = self.category_map[tid]
            else:
                category_name = tid
            
            # 构建URL
            if pg == 1:
                url = f"{self.host}/category/{tid}"
            else:
                url = f"{self.host}/category/{tid}/page/{pg}"
            
            print(f"分类URL: {url}")
            
            rsp = requests.get(url, headers=self.headers, timeout=self.timeout)
            if rsp.status_code != 200:
                print(f"HTTP状态码错误: {rsp.status_code}")
                # 尝试另一种URL格式
                if pg == 1:
                    url = f"{self.host}/category/{category_name}"
                else:
                    url = f"{self.host}/category/{category_name}/page/{pg}"
                
                print(f"尝试备用URL: {url}")
                rsp = requests.get(url, headers=self.headers, timeout=self.timeout)
                if rsp.status_code != 200:
                    return result
            
            html = rsp.text
            
            # 修复：基于实际HTML结构提取
            videos = []
            
            # 方法1：直接查找所有文章块
            # 首先找到所有article标签
            article_pattern = r'<article[^>]*class="[^"]*post-item[^"]*"[^>]*>(.*?)</article>'
            articles = re.findall(article_pattern, html, re.S)
            
            print(f"找到 {len(articles)} 个文章块")
            
            for article_html in articles:
                # 提取链接
                href_match = re.search(r'href="([^"]+)"', article_html)
                if not href_match:
                    continue
                    
                href = href_match.group(1)
                
                # 提取图片 - 首先尝试data-bg属性
                img_url = ""
                img_match = re.search(r'data-bg="([^"]+)"', article_html)
                if img_match:
                    img_url = img_match.group(1)
                else:
                    # 尝试src属性
                    img_match = re.search(r'<img[^>]*src="([^"]+)"', article_html)
                    if img_match:
                        img_url = img_match.group(1)
                
                # 提取标题 - 查找h2标签内的a标签
                title = ""
                h2_match = re.search(r'<h2[^>]*class="[^"]*entry-title[^"]*"[^>]*>(.*?)</h2>', article_html, re.S)
                if h2_match:
                    h2_content = h2_match.group(1)
                    # 从h2中提取a标签的文本
                    a_match = re.search(r'<a[^>]*>(.*?)</a>', h2_content, re.S)
                    if a_match:
                        title = a_match.group(1)
                
                # 如果还没有标题，尝试其他方式
                if not title:
                    # 尝试从链接中提取
                    title_match = re.search(r'title="([^"]+)"', article_html)
                    if title_match:
                        title = title_match.group(1)
                    elif href:
                        # 从URL中提取
                        title = href.split('/')[-1].replace('.html', '').replace('-', ' ')
                        title = re.sub(r'\d+', '', title).strip()
                        if len(title) < 2:
                            title = category_name + "资源"
                
                # 清理标题
                if title:
                    title = re.sub(r'<[^>]+>', '', title).strip()
                    title = re.sub(r'\s+', ' ', title)
                
                # 确保链接完整
                if href and not href.startswith('http'):
                    href = f"{self.host}{href}" if href.startswith('/') else f"{self.host}/{href}"
                
                # 确保图片完整
                if img_url and not img_url.startswith('http'):
                    img_url = f"{self.host}{img_url}" if img_url.startswith('/') else f"{self.host}/{img_url}"
                elif not img_url:
                    img_url = self.default_image
                
                if href and title:
                    videos.append({
                        "vod_id": href,
                        "vod_name": title,
                        "vod_pic": img_url,
                        "vod_remarks": "",
                        "vod_content": title
                    })
            
            # 方法2：如果方法1没找到，使用更简单的查找方式
            if not videos:
                print("使用方法2提取")
                # 查找所有文章链接
                article_links = re.findall(r'<a[^>]*href="([^"]+/\d+\.html)"[^>]*>', html)
                article_links = list(set(article_links))[:self.limit]
                
                for link in article_links:
                    if not link.startswith('http'):
                        full_link = f"{self.host}{link}" if link.startswith('/') else f"{self.host}/{link}"
                    else:
                        full_link = link
                    
                    # 提取标题
                    title = "未知标题"
                    # 在链接附近查找
                    link_pattern = f'href="{re.escape(link)}"'
                    link_pos = html.find(link_pattern)
                    if link_pos > -1:
                        start = max(0, link_pos - 200)
                        search_area = html[start:link_pos]
                        
                        # 查找可能的标题
                        title_match = re.search(r'>([^<>{]+?)</a>', search_area)
                        if title_match:
                            title = title_match.group(1).strip()
                        
                        # 查找图片
                        img_match = re.search(r'<img[^>]*src="([^"]+)"', search_area)
                        if img_match:
                            img_url = img_match.group(1)
                            if not img_url.startswith('http'):
                                img_url = f"{self.host}{img_url}" if img_url.startswith('/') else f"{self.host}/{img_url}"
                        else:
                            img_url = self.default_image
                    else:
                        img_url = self.default_image
                    
                    videos.append({
                        "vod_id": full_link,
                        "vod_name": title,
                        "vod_pic": img_url,
                        "vod_remarks": "",
                        "vod_content": title
                    })
            
            result['list'] = videos
            
            if videos:
                print(f"成功获取 {len(videos)} 个视频")
                # 显示前几个用于调试
                for i, video in enumerate(videos[:3]):
                    print(f"  {i+1}. {video['vod_name']} - {video['vod_pic'][:50]}...")
            else:
                print(f"分类 {tid} 没有找到数据")
                # 显示部分HTML用于调试
                print("HTML预览（前2000字符）:")
                print(html[:2000])
                
        except Exception as e:
            print(f"categoryContent error: {e}")
            import traceback
            traceback.print_exc()
        
        return result
    
    def detailContent(self, array):
        result = {'list': []}
        if not array:
            return result
        
        try:
            vod_id = array[0]
            url = vod_id if vod_id.startswith('http') else f"{self.host}{vod_id}"
            
            print(f"正在访问详情页: {url}")
            
            rsp = requests.get(url, headers=self.headers, timeout=self.timeout)
            if rsp.status_code != 200:
                raise Exception(f"HTTP状态码: {rsp.status_code}")
            
            html = rsp.text
            
            # 提取标题 - 多种方法尝试
            title = "电影云集资源"
            
            # 方法1: 从h1标签提取
            h1_patterns = [
                r'<h1[^>]*class="post-title"[^>]*>(.*?)</h1>',
                r'<h1[^>]*class="entry-title"[^>]*>(.*?)</h1>',
                r'<h1[^>]*>(.*?)</h1>'
            ]
            
            for pattern in h1_patterns:
                match = re.search(pattern, html, re.S)
                if match:
                    title = match.group(1).strip()
                    title = re.sub(r'<[^>]+>', '', title)
                    if title:
                        break
            
            # 方法2: 从title标签提取
            if not title or title == "电影云集资源":
                title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.S)
                if title_match:
                    title = title_match.group(1).strip()
                    # 清理标题
                    title = re.split(r'[-|_]', title)[0].strip()
            
            # 方法3: 从meta标签提取
            if not title or title == "电影云集资源":
                meta_patterns = [
                    r'<meta[^>]*property="og:title"[^>]*content="([^"]+)"',
                    r'<meta[^>]*name="title"[^>]*content="([^"]+)"'
                ]
                
                for pattern in meta_patterns:
                    match = re.search(pattern, html, re.I)
                    if match:
                        title = match.group(1).strip()
                        break
            
            print(f"标题: {title}")
            
            # 提取图片 - 多种方法尝试
            vod_pic = self.default_image
            
            # 方法1: meta标签
            img_patterns = [
                r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"',
                r'<meta[^>]*name="og:image"[^>]*content="([^"]+)"',
                r'<meta[^>]*itemprop="image"[^>]*content="([^"]+)"'
            ]
            
            for pattern in img_patterns:
                match = re.search(pattern, html, re.I)
                if match:
                    img_url = match.group(1).strip()
                    if img_url and not img_url.startswith('data:'):
                        if not img_url.startswith('http'):
                            img_url = f"{self.host}{img_url}" if img_url.startswith('/') else f"{self.host}/{img_url}"
                        vod_pic = img_url
                        print(f"从meta提取到图片: {img_url[:50]}...")
                        break
            
            # 方法2: 文章特色图片
            if vod_pic == self.default_image:
                featured_patterns = [
                    r'<img[^>]*class="[^"]*wp-post-image[^"]*"[^>]*src="([^"]+)"',
                    r'<img[^>]*class="[^"]*featured-image[^"]*"[^>]*src="([^"]+)"',
                    r'<img[^>]*src="([^"]+)"[^>]*class="[^"]*featured[^"]*"'
                ]
                
                for pattern in featured_patterns:
                    match = re.search(pattern, html, re.I)
                    if match:
                        img_url = match.group(1).strip()
                        if img_url and not img_url.startswith('data:'):
                            if not img_url.startswith('http'):
                                img_url = f"{self.host}{img_url}" if img_url.startswith('/') else f"{self.host}/{img_url}"
                            vod_pic = img_url
                            print(f"从特色图片提取到图片: {img_url[:50]}...")
                            break
            
            # 提取内容区域
            content_html = ""
            content_patterns = [
                r'<div[^>]*class="post-content"[^>]*>(.*?)</div>',
                r'<article[^>]*class="post[^"]*"[^>]*>(.*?)</article>',
                r'<div[^>]*class="entry-content"[^>]*>(.*?)</div>'
            ]
            
            for pattern in content_patterns:
                match = re.search(pattern, html, re.S)
                if match:
                    content_html = match.group(1)
                    break
            
            # 如果没有找到内容区域，使用整个页面
            if not content_html:
                content_html = html
            
            # 提取所有网盘链接 - 夸克优先
            play_items = {}
            
            # 1. 夸克网盘 (优先)
            quark_patterns = [
                r'(pan\.quark\.cn/s/[a-zA-Z0-9]+)',
                r'(https?://pan\.quark\.cn/s/[a-zA-Z0-9]+)'
            ]
            
            quark_links = []
            for pattern in quark_patterns:
                matches = re.findall(pattern, content_html, re.I)
                for match in matches:
                    if not match.startswith('http'):
                        link = f"https://{match}"
                    else:
                        link = match
                    
                    if link not in quark_links:
                        quark_links.append(link)
            
            if quark_links:
                play_items['夸克网盘'] = quark_links
            
            # 2. 百度网盘
            baidu_patterns = [
                r'(pan\.baidu\.com/s/[a-zA-Z0-9_-]+)',
                r'(https?://pan\.baidu\.com/s/[a-zA-Z0-9_-]+)'
            ]
            
            baidu_links = []
            for pattern in baidu_patterns:
                matches = re.findall(pattern, content_html, re.I)
                for match in matches:
                    if not match.startswith('http'):
                        link = f"https://{match}"
                    else:
                        link = match
                    
                    if link not in baidu_links:
                        baidu_links.append(link)
            
            if baidu_links:
                play_items['百度网盘'] = baidu_links
            
            # 3. 其他网盘
            other_patterns = {
                '阿里云盘': [
                    r'(aliyundrive\.com/s/[a-zA-Z0-9]+)',
                    r'(https?://www\.aliyundrive\.com/s/[a-zA-Z0-9]+)'
                ],
                '迅雷云盘': [
                    r'(pan\.xunlei\.com/s/[a-zA-Z0-9]+)',
                    r'(https?://pan\.xunlei\.com/s/[a-zA-Z0-9]+)'
                ],
                '115网盘': [
                    r'(115\.com/s/[a-zA-Z0-9]+)',
                    r'(https?://115\.com/s/[a-zA-Z0-9]+)'
                ],
                '磁力链接': [
                    r'(magnet:\?xt=urn:btih:[a-zA-Z0-9]{32,})'
                ],
                '电驴链接': [
                    r'(ed2k://[^\s"\']+)'
                ]
            }
            
            for netdisk_name, patterns in other_patterns.items():
                links = []
                for pattern in patterns:
                    matches = re.findall(pattern, content_html, re.I)
                    for match in matches:
                        if not match.startswith(('http://', 'https://', 'magnet:', 'ed2k:')):
                            link = f"https://{match}"
                        else:
                            link = match
                        
                        if link not in links:
                            links.append(link)
                
                if links:
                    play_items[netdisk_name] = links
            
            # 构建播放源 - 夸克网盘在前
            if play_items:
                play_sources = []
                play_urls = []
                
                # 夸克网盘优先
                if '夸克网盘' in play_items:
                    play_sources.append('夸克网盘')
                    formatted_links = []
                    for i, link in enumerate(play_items['夸克网盘'], 1):
                        push_link = f"push://{link}"
                        formatted_links.append(f"第{i}集${push_link}")
                    play_urls.append('#'.join(formatted_links))
                
                # 百度网盘
                if '百度网盘' in play_items:
                    play_sources.append('百度网盘')
                    formatted_links = []
                    for i, link in enumerate(play_items['百度网盘'], 1):
                        # 查找提取码
                        password = ''
                        link_pos = content_html.find(link)
                        if link_pos != -1:
                            start = max(0, link_pos - 150)
                            end = min(len(content_html), link_pos + len(link) + 150)
                            nearby = content_html[start:end]
                            pwd_match = re.search(r'[提取码密码pwd][：:]\s*([a-zA-Z0-9]{4})', nearby, re.I)
                            if pwd_match:
                                password = pwd_match.group(1)
                        
                        push_link = f"push://{link}"
                        if password:
                            formatted_links.append(f"第{i}集(码:{password})${push_link}")
                        else:
                            formatted_links.append(f"第{i}集${push_link}")
                    play_urls.append('#'.join(formatted_links))
                
                # 其他网盘
                for netdisk_name, links in play_items.items():
                    if netdisk_name not in ['夸克网盘', '百度网盘']:
                        play_sources.append(netdisk_name)
                        formatted_links = []
                        for i, link in enumerate(links, 1):
                            push_link = f"push://{link}"
                            formatted_links.append(f"第{i}集${push_link}")
                        play_urls.append('#'.join(formatted_links))
                
                play_from = '$$$'.join(play_sources)
                play_url = '$$$'.join(play_urls)
                print(f"播放源: {play_from}")
            else:
                print("没有找到网盘链接")
                play_from = '电影云集'
                play_url = '暂无资源$#'
            
            # 提取简介
            vod_content = title
            if content_html:
                # 移除HTML标签
                text_content = re.sub(r'<[^>]+>', ' ', content_html)
                text_content = re.sub(r'\s+', ' ', text_content).strip()
                
                # 查找剧情简介
                desc_patterns = [
                    r'剧情简介[：:]\s*(.*?)(?:\n|$)',
                    r'简介[：:]\s*(.*?)(?:\n|$)',
                    r'内容简介[：:]\s*(.*?)(?:\n|$)',
                    r'剧情介绍[：:]\s*(.*?)(?:\n|$)'
                ]
                
                description = ""
                for pattern in desc_patterns:
                    match = re.search(pattern, text_content, re.I)
                    if match:
                        description = match.group(1).strip()
                        break
                
                if description:
                    vod_content = description[:200] + "..."
                elif len(text_content) > 50:
                    vod_content = text_content[:200] + "..."
            
            # 创建视频项
            vod_item = {
                'vod_id': url,
                'vod_name': title,
                'vod_pic': vod_pic,
                'vod_content': vod_content,
                'vod_remarks': f"共{len(play_items)}个网盘源" if play_items else "暂无网盘资源",
                'vod_play_from': play_from,
                'vod_play_url': play_url
            }
            
            result['list'].append(vod_item)
            print(f"成功创建视频项")
            
        except Exception as e:
            print(f"detailContent error: {e}")
            import traceback
            traceback.print_exc()
            result['list'].append({
                'vod_id': 'error',
                'vod_name': '电影云集资源',
                'vod_pic': self.default_image,
                'vod_content': f'访问失败: {str(e)}',
                'vod_remarks': '',
                'vod_play_from': '电影云集',
                'vod_play_url': '暂无资源$#'
            })
        
        return result
    
    def searchContent(self, key, quick, pg):
        result = {'list': []}
        
        try:
            import urllib.parse
            encoded_key = urllib.parse.quote(key)
            
            if pg == 1:
                url = f"{self.host}/?s={encoded_key}"
            else:
                url = f"{self.host}/page/{pg}/?s={encoded_key}"
            
            print(f"搜索URL: {url}")
            
            rsp = requests.get(url, headers=self.headers, timeout=self.timeout)
            if rsp.status_code == 200:
                html = rsp.text
                
                # 使用与分类页相同的方法
                videos = []
                article_pattern = r'<article[^>]*class="[^"]*post-item[^"]*"[^>]*>(.*?)</article>'
                articles = re.findall(article_pattern, html, re.S)
                
                for article_html in articles:
                    # 提取链接
                    href_match = re.search(r'href="([^"]+)"', article_html)
                    if not href_match:
                        continue
                        
                    href = href_match.group(1)
                    
                    # 提取图片
                    img_url = ""
                    img_match = re.search(r'data-bg="([^"]+)"', article_html)
                    if img_match:
                        img_url = img_match.group(1)
                    else:
                        img_match = re.search(r'<img[^>]*src="([^"]+)"', article_html)
                        if img_match:
                            img_url = img_match.group(1)
                    
                    # 提取标题
                    title = ""
                    h2_match = re.search(r'<h2[^>]*class="[^"]*entry-title[^"]*"[^>]*>(.*?)</h2>', article_html, re.S)
                    if h2_match:
                        h2_content = h2_match.group(1)
                        a_match = re.search(r'<a[^>]*>(.*?)</a>', h2_content, re.S)
                        if a_match:
                            title = a_match.group(1)
                    
                    # 清理标题
                    if title:
                        title = re.sub(r'<[^>]+>', '', title).strip()
                    
                    # 确保链接完整
                    if href and not href.startswith('http'):
                        href = f"{self.host}{href}" if href.startswith('/') else f"{self.host}/{href}"
                    
                    # 确保图片完整
                    if img_url and not img_url.startswith('http'):
                        img_url = f"{self.host}{img_url}" if img_url.startswith('/') else f"{self.host}/{img_url}"
                    elif not img_url:
                        img_url = self.default_image
                    
                    if href and title:
                        videos.append({
                            "vod_id": href,
                            "vod_name": title,
                            "vod_pic": img_url,
                            "vod_remarks": "",
                            "vod_content": title
                        })
                
                result['list'] = videos
                
        except Exception as e:
            print(f"searchContent error: {e}")
        
        return result
    
    def playerContent(self, flag, id, vipFlags):
        """
        播放器内容处理
        """
        print(f"playerContent被调用: flag={flag}")
        
        try:
            # 清理id
            id = str(id).strip()
            
            # 对于百度网盘的特殊处理
            if "pan.baidu.com" in id:
                # 确保链接有完整协议
                if not id.startswith('http'):
                    id = f"https://{id}"
                
                # 移除可能存在的重复协议
                id = id.replace('push://', '').replace('push:http://', 'http://').replace('push:https://', 'https://')
                
                # 使用push协议
                push_url = f"push://{id}"
                
                print(f"推送百度网盘: {push_url[:100]}...")
                
                # 百度网盘可能需要特殊header
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }
                
                return {
                    "parse": 0,
                    "playUrl": "",
                    "url": push_url,
                    "header": json.dumps(headers)
                }
            else:
                # 其他网盘
                if not id.startswith('push://'):
                    push_url = f"push://{id}"
                else:
                    push_url = id
                
                return {
                    "parse": 0,
                    "playUrl": "",
                    "url": push_url,
                    "header": ""
                }
            
        except Exception as e:
            print(f"playerContent error: {e}")
            return {
                "parse": 0,
                "playUrl": "",
                "url": "push://error",
                "header": ""
            }


# 测试函数
def test_all_categories():
    """测试所有分类"""
    spider = Spider()
    
    print("测试电影云集所有分类")
    print("=" * 60)
    
    # 测试所有分类
    categories = ['dianying', 'ju', 'dongman', 'zongyi', 'duanju', 'xuexi', 'duwu', 'yinpin']
    
    for category in categories:
        print(f"\n测试分类: {category}")
        result = spider.categoryContent(category, 1, {}, {})
        
        if result['list']:
            print(f"✓ 找到 {len(result['list'])} 个视频")
            
            # 显示前几个视频的信息
            for i, vod in enumerate(result['list'][:3], 1):
                print(f"  {i}. {vod['vod_name']}")
                print(f"     图片: {vod['vod_pic'][:50]}...")
        else:
            print(f"✗ 没有数据")
    
    # 测试详情页
    print("\n" + "=" * 60)
    print("测试详情页:")
    
    test_url = "https://dyyjpro.com/83556.html"
    detail_result = spider.detailContent([test_url])
    
    if detail_result['list']:
        vod = detail_result['list'][0]
        print(f"✓ 成功获取详情页")
        print(f"标题: {vod['vod_name']}")
        print(f"图片: {vod['vod_pic'][:50]}...")
        print(f"播放源: {vod['vod_play_from']}")
        
        # 检查夸克网盘是否在前面
        if '$$$' in vod['vod_play_from']:
            sources = vod['vod_play_from'].split('$$$')
            print(f"播放源顺序: {sources}")
    else:
        print("✗ 详情页没有数据")


if __name__ == '__main__':
    test_all_categories()