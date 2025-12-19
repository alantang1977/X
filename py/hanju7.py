# -*- coding: utf-8 -*-
import json
import re
import requests
from bs4 import BeautifulSoup

class Spider(object):
    """
    新韩剧网(hanju7.com)爬虫 Python版
    源JS作者：deepseek
    转换：AI Assistant
    """
    
    def __init__(self):
        self.siteUrl = 'https://www.hanju7.com'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': self.siteUrl
        }

    def init(self, extend=""):
        pass

    def homeContent(self, filter):
        result = {}
        cateManual = {
            "韩剧": "1",
            "韩国电影": "3",
            "韩国综艺": "4",
            "排行榜": "hot",
            "最新更新": "new"
        }
        classes = []
        for k, v in cateManual.items():
            classes.append({
                'type_name': k,
                'type_id': v
            })

        # 筛选配置
        years = [
            {"n": "全部", "v": ""}, {"n": "2025", "v": "2025"}, {"n": "2024", "v": "2024"},
            {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"}, {"n": "2021", "v": "2021"},
            {"n": "2020", "v": "2020"}, {"n": "10后", "v": "2010__2019"}, {"n": "00后", "v": "2000__2009"},
            {"n": "90后", "v": "1990__1999"}, {"n": "80后", "v": "1980__1989"}, {"n": "更早", "v": "1900__1980"}
        ]
        sorts = [{"n": "最新", "v": "newstime"}, {"n": "热门", "v": "onclick"}]

        filterConfig = {}
        # 为 ID 1, 3, 4 添加筛选
        for type_id in ["1", "3", "4"]:
            filterConfig[type_id] = [
                {"key": "year", "name": "按年份", "value": years},
                {"key": "sort", "name": "按排序", "value": sorts}
            ]

        result['class'] = classes
        result['filters'] = filterConfig
        return result

    def homeVideoContent(self):
        try:
            r = requests.get(self.siteUrl + '/', headers=self.headers)
            r.encoding = 'utf-8'
            soup = BeautifulSoup(r.text, 'html.parser')
            videos = self._parse_video_list(soup)
            return {'list': videos}
        except Exception as e:
            return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        # 获取筛选参数
        year = extend.get('year', '')
        sort = extend.get('sort', '')

        try:
            url = ""
            if tid in ['hot', 'new']:
                # 排行榜或最新更新
                url = f"{self.siteUrl}/{tid}.html"
                r = requests.get(url, headers=self.headers)
                r.encoding = 'utf-8'
                soup = BeautifulSoup(r.text, 'html.parser')
                
                videos = []
                # JS 逻辑：querySelectorAll('#t ~ li')
                # 这里的逻辑需要根据HTML结构适配，通常是一个列表容器
                # 假设HTML结构中有一个 id="t" 的元素，后面紧跟 li
                # Python BS4 处理兄弟节点不如 JS 方便，通常直接找包含列表的 ul 或 div
                
                # 尝试查找主要的列表容器，通常是 .list 或 similar
                # 兼容 JS 中的逻辑，尝试找到列表项
                items = soup.select('.list li') # 假设通用类名，如果不匹配需根据实际网页调整
                if not items:
                    # 如果没有 .list，尝试直接找 #t 后的兄弟节点（模拟JS逻辑）
                    t_elem = soup.find(id='t')
                    if t_elem:
                        items = t_elem.find_next_siblings('li')

                i = 1
                for li in items:
                    a_tag = li.find('a', href=re.compile(r'/detail/'))
                    if not a_tag:
                        continue
                        
                    vid = self.siteUrl + a_tag['href']
                    name = a_tag.get_text(strip=True)
                    
                    time_elem = li.find(id='time')
                    actor_elem = li.find(id='actor')
                    
                    year_txt = time_elem.get_text(strip=True) if time_elem else ""
                    actor_txt = actor_elem.get_text(strip=True) if actor_elem else ""
                    
                    # 模拟JS中的占位图逻辑
                    pic = f'https://dummyimage.com/240x240/ffffff/ffc800.png&text={i}'
                    i += 1
                    
                    videos.append({
                        "vod_id": vid,
                        "vod_name": name,
                        "vod_year": year_txt,
                        "vod_pic": pic,
                        "vod_remarks": f"{year_txt} | {actor_txt}"
                    })
                
                result = {
                    "code": 1, 
                    "msg": "数据列表", 
                    "list": videos, 
                    "page": 1, 
                    "pagecount": 1, 
                    "limit": len(videos), 
                    "total": len(videos)
                }

            else:
                # 普通分类
                # URL格式: /list/tid-year-sort-pg.html
                url = f"{self.siteUrl}/list/{tid}-{year}-{sort}-{pg}.html"
                r = requests.get(url, headers=self.headers)
                r.encoding = 'utf-8'
                soup = BeautifulSoup(r.text, 'html.parser')
                videos = self._parse_video_list(soup)
                
                result = {
                    "code": 1, 
                    "msg": "数据列表", 
                    "list": videos, 
                    "page": int(pg), 
                    "pagecount": 10000, 
                    "limit": 24, 
                    "total": 240000
                }
                
        except Exception as e:
            print(f"Error in categoryContent: {e}")
            result = {"list": []}
            
        return result

    def detailContent(self, array):
        try:
            tid = array[0]
            if not tid.startswith('http'):
                tid = self.siteUrl + tid if tid.startswith('/') else tid
                
            r = requests.get(tid, headers=self.headers)
            r.encoding = 'utf-8'
            soup = BeautifulSoup(r.text, 'html.parser')

            # 获取文本辅助函数
            def get_dt_text(keyword):
                dt = soup.find('dt', string=lambda t: t and keyword in t)
                if dt and dt.find_next_sibling():
                    return dt.find_next_sibling().get_text(strip=True)
                return ""

            # 提取图片
            img_tag = soup.select_one('img[src*="//pics.hanju7.com/"]')
            pic = 'https:' + img_tag['src'] if img_tag else ''

            # 提取剧情
            content_div = soup.select_one('.juqing')
            content = content_div.get_text(strip=True) if content_div else ""

            # 提取播放列表 (Regex 解析 bb_a 函数)
            # JS: bb_a('链接','名称') -> 实际上原JS正则是 bb_a('name','url')
            # JS Match: match[1] = url/param, match[2] = name (Wait, let's re-read JS)
            # JS Source: match(/bb_a\('([^']+)','([^']+)'/) -> match[1] is 1st arg, match[2] is 2nd arg.
            # JS Logic: `${match[2]}$${match[1]}`
            # 这里的顺序取决于网页源码中 bb_a 的参数顺序。通常是 bb_a('集数名称', '播放地址')
            
            play_urls = []
            scripts = soup.find_all('script') # 或者直接在html文本中搜索
            # 在整个HTML中查找所有 onclick="bb_a(...)"
            pattern = re.compile(r"bb_a\('([^']+?)','([^']+?)'\)")
            # 查找所有匹配项
            matches = pattern.findall(r.text)
            
            # matches list of tuples: [(arg1, arg2), ...]
            # 假设网页是 bb_a('第01集', '/play/xxx.html')
            # 那么 arg1=名称, arg2=URL
            # JS return: match[2]$match[1] => URL$名称
            
            for m in matches:
                name = m[0]
                url_part = m[1]
                play_urls.append(f"{url_part}${name}")

            vod = {
                "vod_id": tid,
                "vod_name": get_dt_text('片名'),
                "vod_pic": pic,
                "vod_remarks": get_dt_text('状态'),
                "vod_year": get_dt_text('上映').split('-')[0],
                "vod_actor": get_dt_text('主演'),
                "vod_content": content,
                "vod_play_from": "新韩剧网",
                "vod_play_url": "#".join(play_urls)
            }

            return {
                "code": 1, 
                "msg": "数据列表", 
                "page": 1, 
                "pagecount": 1, 
                "limit": 1, 
                "total": 1, 
                "list": [vod]
            }
            
        except Exception as e:
            print(f"Error in detailContent: {e}")
            return {"list": []}

    def searchContent(self, key, quick, pg="1"):
        try:
            url = f"{self.siteUrl}/search/"
            data = {
                "show": "searchkey",
                "keyboard": key
            }
            r = requests.post(url, data=data, headers=self.headers)
            r.encoding = 'utf-8'
            soup = BeautifulSoup(r.text, 'html.parser')

            videos = []
            # 搜索结果列表解析
            # JS: querySelectorAll('#t ~ li')
            # 兼容处理，寻找列表
            items = soup.select('.list li') 
            if not items:
                # 尝试寻找搜索结果容器
                t_elem = soup.find(id='t')
                if t_elem:
                    items = t_elem.find_next_siblings('li')

            for li in items:
                a_tag = li.find('a', href=re.compile(r'/detail/'))
                if not a_tag:
                    continue
                
                vid = self.siteUrl + a_tag['href']
                name = a_tag.get('title', a_tag.get_text(strip=True))
                
                time_elem = li.find(id='time')
                actor_elem = li.find(id='actor')
                
                year_txt = time_elem.get_text(strip=True) if time_elem else ""
                
                # 提取年份正则
                year_match = re.search(r'\((\d{4})\)', a_tag.get_text())
                year_in_title = year_match.group(1) if year_match else ""
                
                actor_txt = actor_elem.get_text(strip=True) if actor_elem else ""
                remarks = f"{year_in_title} | {actor_txt}"

                videos.append({
                    "vod_id": vid,
                    "vod_name": name,
                    "vod_year": year_txt,
                    "vod_remarks": remarks,
                    # 搜索列表可能没有图片，或者需要额外解析，这里JS原版也没处理图片
                    "vod_pic": "" 
                })

            return {
                "code": 1, 
                "msg": "搜索结果", 
                "list": videos, 
                "page": 1, 
                "pagecount": 1, 
                "limit": len(videos), 
                "total": len(videos)
            }
        except Exception as e:
            print(f"Error in searchContent: {e}")
            return {"list": []}

    def playerContent(self, flag, id, vipFlags):
        # id 是 vod_play_url 中的 url 部分
        # 这里的 id 应该是 /play/xxxxx.html 这样的格式
        
        url = id
        if not url.startswith('http'):
            url = self.siteUrl + url

        # JS 版本使用了 webview sniffing (type: 'sniff')
        # 并配合了脚本点击。
        # 在 Python 爬虫标准中，我们返回 parse=1 让播放器/壳子去嗅探目标网页中的视频流
        
        return {
            "parse": 1,
            "playUrl": "",
            "url": url,
            "header": {
                "User-Agent": self.headers['User-Agent'],
                "Referer": self.siteUrl
            }
        }

    def _parse_video_list(self, soup):
        videos = []
        items = soup.select('.list li')
        for li in items:
            a_tag = li.find('a', href=re.compile(r'/detail/'))
            if not a_tag:
                continue
            
            vid = self.siteUrl + a_tag['href']
            name = a_tag.get('title', '')
            if not name:
                name = a_tag.get_text(strip=True)
                
            pic_url = a_tag.get('data-original', '')
            if pic_url and not pic_url.startswith('http'):
                pic_url = 'https:' + pic_url
                
            tip_elem = li.select_one('.tip')
            year = tip_elem.get_text(strip=True) if tip_elem else ""
            
            videos.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic_url,
                "vod_year": year
            })
        return videos
