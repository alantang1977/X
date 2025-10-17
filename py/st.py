import re
import sys
import requests
from pyquery import PyQuery as pq

# 添加到系统路径以便导入基础爬虫类
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def __init__(self):
        # 基础配置
        self.name = "🔞┃stgay┃🏳️‍🌈"
        self.host = "https://25f.jlrlpjbz.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1"
        }
        self.timeout = 10
        
        # 分类映射
        self.class_map = {
            "首页": {"type_id": "all/play"},
            "最新": {"type_id": "all/new"},
            "热门": {"type_id": "all/hot"},
            "动漫": {"type_id": "category/tongxing-Gman"}
        }

    def getName(self):
        return self.name

    def init(self, extend=""):
        # 初始化方法，可以留空或添加初始化逻辑
        pass

    def homeContent(self, filter):
        result = {}
        # 构造分类列表
        classes = []
        for name, info in self.class_map.items():
            classes.append({
                'type_name': name,
                'type_id': info['type_id']
            })
        result['class'] = classes
        
        # 获取首页视频内容
        try:
            home_data = self.get_videos("all/play", 1)
            result['list'] = home_data['list']
        except:
            result['list'] = []
            
        return result

    def homeVideoContent(self):
        # 首页推荐视频，根据配置可能不需要
        return []

    def categoryContent(self, tid, pg, filter, extend):
        # 获取分类内容
        return self.get_videos(tid, pg)

    def get_videos(self, tid, pg):
        result = {}
        try:
            # 构建分类URL
            url = f"{self.host}/videos/{tid}/{pg}"
            html = self.fetch(url).text
            
            # 使用PyQuery解析HTML
            data = pq(html)
            
            vlist = []
            # 数组规则: <li>&&</li>[不包含:checkNum]
            items = data('li:not(:has(.checkNum))')
            for item in items.items():
                try:
                    # 标题规则: alt="&&"
                    title = item('img').attr('alt') or ''
                    if not title:
                        continue
                    
                    # 链接规则: <a class="flex aspect-w-16*href="&&""
                    href_selector = item('a[class*="flex"][class*="aspect-w-16"]')
                    href = href_selector.attr('href') or ''
                    if not href:
                        continue
                    
                    # 提取视频ID
                    vod_id = href.split('/')[-1]
                    
                    # 副标题规则: text-white\">&&</div>
                    subtitle = item('.text-white').text() or ''
                    
                    # 图片规则: data-poster="&&"
                    pic = item('img').attr('data-poster') or item('img').attr('src') or ''
                    if pic and not pic.startswith('http'):
                        pic = f"{self.host}{pic}" if pic.startswith('/') else pic
                    
                    vlist.append({
                        'vod_id': vod_id,
                        'vod_name': title,
                        'vod_pic': pic,
                        'vod_remarks': subtitle
                    })
                except Exception as e:
                    print(f"解析视频项失败: {e}")
                    continue
            
            result['list'] = vlist
            result['page'] = pg
            result['pagecount'] = 9999  # 假设有大量页面
            result['limit'] = len(vlist)
            result['total'] = 999999
        except Exception as e:
            print(f"获取分类内容失败: {e}")
            result['list'] = []
            result['page'] = pg
            result['pagecount'] = 1
            result['limit'] = 0
            result['total'] = 0
            
        return result

    def detailContent(self, ids):
        try:
            if not ids or not ids[0]:
                return {'list': []}
                
            vod_id = ids[0]
            url = f"{self.host}/video/{vod_id}"
            html = self.fetch(url).text
            
            # 简介规则: class="dx-title leading-22 mb-3">&&</h1>
            title_match = re.search(r'class="dx-title leading-22 mb-3">(.*?)</h1>', html)
            title = title_match.group(1) if title_match else "未知标题"
            
            # 播放数组规则: <div id="mse"&&</div>
            player_div_match = re.search(r'<div id="mse"(.*?)</div>', html, re.S)
            player_div = player_div_match.group(1) if player_div_match else ""
            
            # 播放链接规则: data-url="&&"
            play_url_match = re.search(r'data-url="(.*?)"', player_div) if player_div else None
            play_url = play_url_match.group(1) if play_url_match else ""
            
            # 如果没有找到播放链接，尝试其他可能的位置
            if not play_url:
                # 尝试从JavaScript变量中提取
                js_matches = re.findall(r'(https?://[^\s"\']+\.(?:m3u8|mp4))', html)
                if js_matches:
                    play_url = js_matches[0]
            
            vod = {
                'vod_id': vod_id,
                'vod_name': title,
                'vod_pic': '',
                'vod_play_from': 'stgay',
                'vod_play_url': f'正片${play_url}' if play_url else '正片$暂无播放地址'
            }
            return {'list': [vod]}
        except Exception as e:
            print(f"获取详情内容失败: {e}")
            return {'list': []}

    def searchContent(self, key, quick, pg=1):
        # 根据配置，搜索功能不可用
        return {'list': []}

    def playerContent(self, flag, id, vipFlags):
        # 直接播放模式
        return {
            'parse': 0,  # 直接播放
            'url': id,
            'header': self.headers
        }

    def fetch(self, url, headers=None, timeout=None):
        if headers is None:
            headers = self.headers
        if timeout is None:
            timeout = self.timeout
            
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.encoding = 'utf-8'  # 确保正确编码
            return response
        except Exception as e:
            print(f"请求失败: {url}, 错误: {e}")
            # 返回一个模拟的响应对象，避免后续代码崩溃
            return type('obj', (object,), {
                'text': '',
                'status_code': 500,
                'headers': {}
            })