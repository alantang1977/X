#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ztzssz.com 爬虫 - TVBox/影视仓 Spider 插件
支持分类浏览、筛选（类型/地区/语言/年份/字母）、搜索、详情获取、播放链接解析
选集正序排列，海报封面补充
"""

import re
import json
import logging
import urllib.parse
import os
import sys
import requests
from bs4 import BeautifulSoup

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from base.spider import Spider as BaseSpider
except ImportError:
    BaseSpider = object

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class Spider(BaseSpider):
    """ztzssz.com 爬虫"""

    BASE_URL = "https://www.ztzssz.com"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 12; SM-S908U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://www.ztzssz.com/",
    }

    # 分类：键为网站分类ID，与 /vodtype/{id}.html 对应
    CATEGORY_MAP = {
        "1": {"name": "电影", "url": "/vodtype/1.html"},
        "2": {"name": "电视剧", "url": "/vodtype/2.html"},
        "3": {"name": "综艺", "url": "/vodtype/3.html"},
        "4": {"name": "动漫", "url": "/vodtype/4.html"},
        "20": {"name": "短剧", "url": "/vodtype/20.html"},
        "35": {"name": "动画片", "url": "/vodtype/35.html"},
        "36": {"name": "4K电影", "url": "/vodtype/36.html"},
        "37": {"name": "Netflix作品", "url": "/vodtype/37.html"},
    }

    def __init__(self):
        try:
            super().__init__()
        except Exception:
            pass
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update(self.HEADERS)

    def init(self, extend):
        pass

    def getName(self):
        return "ztzssz影视"

    def _parse_ext(self, ext):
        """解析ext参数，兼容dict和JSON字符串"""
        if not ext:
            return {}
        if isinstance(ext, dict):
            return ext
        if isinstance(ext, str):
            try:
                return json.loads(ext)
            except Exception:
                return {}
        return {}

    def _get(self, url):
        try:
            resp = self.session.get(url, timeout=30)
            resp.encoding = "utf-8"
            return resp
        except Exception as e:
            logger.error(f"请求失败 {url}: {e}")
            return None

    # ==================== 首页 ====================
    def homeContent(self, filter=False):
        try:
            url = f"{self.BASE_URL}/"
            resp = self._get(url)
            if not resp:
                return {}

            classes = [{"type_id": cid, "type_name": info["name"]}
                       for cid, info in self.CATEGORY_MAP.items()]

            home_list = self._parse_video_list(resp.text)

            return {
                "class": classes,
                "filters": self._get_filters(),
                "list": home_list,
            }
        except Exception as e:
            logger.error(f"获取首页失败: {e}")
            return {}

    def homeVideoContent(self):
        home = self.homeContent()
        return {"list": home.get("list", [])}

    # ==================== 筛选 ====================
    def _get_filters(self):
        """筛选配置：类型/地区/语言/年份/字母
        网站筛选URL为中文值（如 喜剧/大陆/国语），故筛选value直接用中文。
        """
        filters = {}
        # 类型：按分类区分（电影/电视剧/动漫等类型不同），这里取较通用的集合
        type_values_common = [
            {"n": "全部", "v": ""},
            {"n": "动作", "v": "动作"}, {"n": "喜剧", "v": "喜剧"},
            {"n": "爱情", "v": "爱情"}, {"n": "科幻", "v": "科幻"},
            {"n": "恐怖", "v": "恐怖"}, {"n": "剧情", "v": "剧情"},
            {"n": "战争", "v": "战争"}, {"n": "警匪", "v": "警匪"},
            {"n": "犯罪", "v": "犯罪"}, {"n": "动画", "v": "动画"},
            {"n": "奇幻", "v": "奇幻"}, {"n": "武侠", "v": "武侠"},
            {"n": "冒险", "v": "冒险"}, {"n": "枪战", "v": "枪战"},
            {"n": "悬疑", "v": "悬疑"}, {"n": "惊悚", "v": "惊悚"},
            {"n": "经典", "v": "经典"}, {"n": "青春", "v": "青春"},
            {"n": "文艺", "v": "文艺"}, {"n": "古装", "v": "古装"},
            {"n": "历史", "v": "历史"}, {"n": "运动", "v": "运动"},
            {"n": "农村", "v": "农村"}, {"n": "儿童", "v": "儿童"},
            {"n": "网络电影", "v": "网络电影"},
        ]
        # 电视剧/综艺/动漫常用类型
        type_values_series = [
            {"n": "全部", "v": ""},
            {"n": "古装", "v": "古装"}, {"n": "战争", "v": "战争"},
            {"n": "青春偶像", "v": "青春偶像"}, {"n": "喜剧", "v": "喜剧"},
            {"n": "家庭", "v": "家庭"}, {"n": "犯罪", "v": "犯罪"},
            {"n": "动作", "v": "动作"}, {"n": "奇幻", "v": "奇幻"},
            {"n": "剧情", "v": "剧情"}, {"n": "历史", "v": "历史"},
            {"n": "经典", "v": "经典"}, {"n": "乡村", "v": "乡村"},
            {"n": "情景", "v": "情景"}, {"n": "商战", "v": "商战"},
            {"n": "网剧", "v": "网剧"}, {"n": "其他", "v": "其他"},
        ]

        area_values = [
            {"n": "全部", "v": ""},
            {"n": "大陆", "v": "大陆"}, {"n": "香港", "v": "香港"},
            {"n": "台湾", "v": "台湾"}, {"n": "美国", "v": "美国"},
            {"n": "法国", "v": "法国"}, {"n": "英国", "v": "英国"},
            {"n": "日本", "v": "日本"}, {"n": "韩国", "v": "韩国"},
            {"n": "德国", "v": "德国"}, {"n": "泰国", "v": "泰国"},
            {"n": "印度", "v": "印度"}, {"n": "意大利", "v": "意大利"},
            {"n": "西班牙", "v": "西班牙"}, {"n": "加拿大", "v": "加拿大"},
            {"n": "其他", "v": "其他"},
        ]
        lang_values = [
            {"n": "全部", "v": ""},
            {"n": "国语", "v": "国语"}, {"n": "英语", "v": "英语"},
            {"n": "粤语", "v": "粤语"}, {"n": "闽南语", "v": "闽南语"},
            {"n": "韩语", "v": "韩语"}, {"n": "日语", "v": "日语"},
            {"n": "法语", "v": "法语"}, {"n": "德语", "v": "德语"},
            {"n": "其它", "v": "其它"},
        ]
        year_values = [{"n": "全部", "v": ""}]
        for y in range(2026, 1999, -1):
            year_values.append({"n": str(y), "v": str(y)})

        letter_values = [{"n": "全部", "v": ""}]
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            letter_values.append({"n": letter, "v": letter})
        letter_values.append({"n": "其他", "v": "0"})

        for cate_id in self.CATEGORY_MAP:
            if cate_id in ("2", "3", "4", "20"):
                tv = type_values_series
            else:
                tv = type_values_common
            filters[cate_id] = [
                {"key": "type", "name": "类型", "value": tv},
                {"key": "area", "name": "地区", "value": area_values},
                {"key": "lang", "name": "语言", "value": lang_values},
                {"key": "year", "name": "年份", "value": year_values},
                {"key": "letter", "name": "字母", "value": letter_values},
            ]
        return filters

    # ==================== 分类 ====================
    def categoryContent(self, tid, pg, filter, ext):
        try:
            page = int(pg) if pg else 1
            type_id = str(tid)

            cate_info = self.CATEGORY_MAP.get(type_id)
            if not cate_info:
                return {"list": [], "page": page, "pagecount": 1, "limit": 20, "total": 0}

            ext_dict = self._parse_ext(ext)
            type_filter = ext_dict.get('type', '')
            lang_filter = ext_dict.get('lang', '')
            year_filter = ext_dict.get('year', '')
            letter_filter = ext_dict.get('letter', '')
            area_filter = ext_dict.get('area', '')

            has_filter = any([type_filter, lang_filter, year_filter, letter_filter, area_filter])

            if has_filter:
                # 筛选URL: /vodshow/{cate_id}-{area}--{type}-{lang}-{letter}---{page}---{year}.html
                # 共12段: [cate_id, area, '', type, lang, letter, '', '', page, '', '', year]
                seg_page = str(page) if page > 1 else ''
                segs = [
                    type_id, area_filter, '', type_filter, lang_filter,
                    letter_filter, '', '', seg_page, '', '', year_filter
                ]
                url = f"{self.BASE_URL}/vodshow/{'-'.join(segs)}.html"
            else:
                # 无筛选: /vodtype/{id}.html，分页 /vodtype/{id}-{page}.html
                url = self.BASE_URL + cate_info["url"]
                if page > 1:
                    url = url.replace('.html', f'-{page}.html')

            resp = self._get(url)
            if not resp:
                return {"list": [], "page": page, "pagecount": 1, "limit": 20, "total": 0}

            videos = self._parse_video_list(resp.text)
            pagecount = self._parse_total_pages(resp.text)

            return {
                "list": videos,
                "page": page,
                "pagecount": pagecount,
                "limit": 20,
                "total": len(videos) * pagecount if pagecount else len(videos),
            }
        except Exception as e:
            logger.error(f"获取分类内容失败: {e}")
            return {"list": [], "page": 1, "pagecount": 1, "limit": 20, "total": 0}

    def _parse_total_pages(self, html):
        """解析总页数，格式: <span class="num">1/1213</span>"""
        patterns = [
            r'class="num"[^>]*>\s*(\d+)\s*/\s*(\d+)',
            r'(\d+)\s*/\s*(\d+)\s*</span>',
            r'/vodtype/\d+-(\d+)\.html["\'][^>]*>尾页',
            r'/vodshow/[^"\'-]+-(\d+)---\.html["\'][^>]*>尾页',
        ]
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                return int(match.group(2) if match.lastindex and match.lastindex >= 2 else match.group(1))
        return 1

    def _parse_video_list(self, html):
        """解析视频列表（首页/分类/筛选/搜索通用）
        卡片: a.ewave-vodlist__thumb (含 data-original, title, href) 或 div.ewave-vodlist__thumb > a.thumb-link
        """
        videos = []
        soup = BeautifulSoup(html, 'html.parser')

        # 兼容两种结构：a.vodlist__thumb 自带链接，或 div.vodlist__thumb 内含 a.thumb-link
        items = soup.find_all('a', class_=re.compile(r'vodlist__thumb'))
        if not items:
            items = soup.find_all('div', class_=re.compile(r'vodlist__thumb'))

        seen_ids = set()
        for item in items:
            href = item.get('href', '')
            if not href:
                a_inner = item.find('a', href=True)
                href = a_inner.get('href', '') if a_inner else ''
            vid_match = re.search(r'/voddetail/(\d+)\.html', href)
            if not vid_match:
                continue
            vid_id = vid_match.group(1)
            if vid_id in seen_ids:
                continue
            seen_ids.add(vid_id)

            title = item.get('title', '')
            poster = item.get('data-original', '')
            if not poster:
                img = item.find('img')
                if img:
                    poster = img.get('data-original', '') or img.get('src', '')
            if not title:
                img = item.find('img')
                if img:
                    title = img.get('alt', '') or item.get('title', '')

            remark_tag = item.find(class_=re.compile(r'pic-text|pic_tag'))
            remarks = remark_tag.get_text(strip=True) if remark_tag else ''

            if title:
                videos.append({
                    "vod_id": vid_id,
                    "vod_name": title,
                    "vod_pic": poster,
                    "vod_remarks": remarks,
                })
        return videos

    # ==================== 详情 ====================
    def detailContent(self, ids):
        try:
            vod_id = ids[0] if isinstance(ids, list) else str(ids)
            url = f"{self.BASE_URL}/voddetail/{vod_id}.html"
            resp = self._get(url)
            if not resp:
                return {"list": []}

            html = resp.text
            soup = BeautifulSoup(html, 'html.parser')

            # 标题: h1.title 内第一个 span（去除评分）
            title = ''
            h1 = soup.find('h1', class_=re.compile(r'title'))
            if h1:
                span = h1.find('span')
                title = span.get_text(strip=True) if span else h1.get_text(strip=True)
            if not title:
                h1 = soup.find('h1')
                if h1:
                    title = h1.get_text(strip=True)

            # 海报: div.ewave-content__thumb 内 img[data-original]
            poster = ''
            thumb_box = soup.find(class_=re.compile(r'content__thumb|vodlist__thumb'))
            if thumb_box:
                img = thumb_box.find('img')
                if img:
                    poster = img.get('data-original', '') or img.get('src', '')

            # 信息: p.data 列表，一个p内可能含多个 label(类型/地区/年份用 span.text-muted 分隔)
            year = area = type_name = actor = director = content = remarks = ''
            data_ps = soup.find_all('p', class_=re.compile(r'data'))
            for p in data_ps:
                # 收集该p下所有 label span 及其后续文本，按 label 分组
                labels = p.find_all('span', class_=re.compile(r'text-muted|left'))
                for idx, label_tag in enumerate(labels):
                    label = label_tag.get_text(strip=True)
                    # 该label之后、下一个label之前的所有文本
                    nxt = labels[idx + 1] if idx + 1 < len(labels) else None
                    val = ''
                    for sib in label_tag.next_siblings:
                        if sib is nxt:
                            break
                        if hasattr(sib, 'get_text'):
                            t = sib.get_text(strip=True)
                        else:
                            t = str(sib).strip()
                        if t:
                            val += t
                    val = val.strip()
                    if label.startswith('类型'):
                        type_name = val
                    elif label.startswith('地区'):
                        area = val
                    elif label.startswith('年份'):
                        year_match = re.search(r'(\d{4})', val)
                        year = year_match.group(1) if year_match else val
                    elif label.startswith('主演'):
                        actor = val
                    elif label.startswith('导演'):
                        director = val
                    elif label.startswith('更新'):
                        remarks = val

            # 简介: p.desc
            desc_tag = soup.find('p', class_=re.compile(r'desc|content__desc'))
            if desc_tag:
                content = desc_tag.get_text(strip=True)
                content = re.sub(r'详情\s*$', '', content).strip()

            # 播放源和集数（正序）
            play_from_list, play_url_list = self._parse_play_sources(html, vod_id)

            vod_item = {
                "vod_id": vod_id,
                "vod_name": title,
                "vod_pic": poster,
                "type_name": type_name,
                "vod_year": year,
                "vod_area": area,
                "vod_remarks": remarks,
                "vod_actor": actor,
                "vod_director": director,
                "vod_content": content,
                "vod_play_from": '$$$'.join(play_from_list),
                "vod_play_url": '$$$'.join(play_url_list),
            }
            return {"list": [vod_item]}
        except Exception as e:
            logger.error(f"获取详情失败: {e}")
            return {"list": []}

    def _parse_play_sources(self, html, vod_id):
        """解析播放源和集数 - 正序排列
        结构: ul.nav-tabs > li > a[href="#playlist{sid}"] (源名)
              div.tab-pane#playlist{sid} > ul > a[href="/vodplay/{vid}-{sid}-{nid}.html"] (集数)
        """
        play_from_list = []
        play_url_list = []

        soup = BeautifulSoup(html, 'html.parser')

        # 源名映射: {sid: 源名}
        source_names = {}
        nav = soup.find('ul', class_=re.compile(r'nav-tabs'))
        if nav:
            for a in nav.find_all('a', href=True):
                m = re.search(r'#playlist(\w+)', a.get('href', ''))
                if m:
                    source_names[m.group(1)] = a.get_text(strip=True)

        # 每个 tab-pane 为一个源
        panes = soup.find_all('div', class_=re.compile(r'tab-pane'))
        if not panes:
            # 兜底：直接按 play 链接分组
            return self._parse_play_sources_fallback(html, vod_id)

        for pane in panes:
            pane_id = pane.get('id', '')
            sid_match = re.search(r'playlist(\w+)', pane_id)
            if not sid_match:
                continue
            sid = sid_match.group(1)
            from_name = source_names.get(sid, f"线路{sid}")

            ul = pane.find('ul')
            if not ul:
                continue
            episodes = []
            seen_nid = set()
            for a in ul.find_all('a', href=re.compile(r'/vodplay/')):
                href = a.get('href', '')
                m = re.search(r'/vodplay/(\d+)-(\w+)-(\d+)\.html', href)
                if not m:
                    continue
                nid = int(m.group(3))
                if nid in seen_nid:
                    continue
                seen_nid.add(nid)
                ep_name = a.get_text(strip=True) or f"第{nid}集"
                full_url = self.BASE_URL + href
                episodes.append((nid, ep_name, full_url))

            if not episodes:
                continue
            # 正序排列
            episodes = sorted(episodes, key=lambda x: x[0])

            play_from_list.append(from_name)
            urls = [f"{name}${u}" for _, name, u in episodes]
            play_url_list.append('#'.join(urls))

        if not play_from_list:
            return self._parse_play_sources_fallback(html, vod_id)
        return play_from_list, play_url_list

    def _parse_play_sources_fallback(self, html, vod_id):
        """兜底：从所有 play 链接按 sid 分组"""
        play_from_list = []
        play_url_list = []
        links = re.findall(r'/vodplay/\d+-\w+-\d+\.html', html)
        sources = {}
        for link in links:
            m = re.match(r'/vodplay/(\d+)-(\w+)-(\d+)\.html', link)
            if not m:
                continue
            sid = m.group(2)
            nid = int(m.group(3))
            sources.setdefault(sid, {})[nid] = link

        for sid in sorted(sources.keys()):
            eps = sources[sid]
            episodes = sorted(eps.items())
            play_from_list.append(f"线路{sid}")
            urls = [f"第{nid}集${self.BASE_URL}{link}" for nid, link in episodes]
            play_url_list.append('#'.join(urls))
        return play_from_list, play_url_list

    # ==================== 播放 ====================
    def playerContent(self, flag, id, vipFlags):
        """解析播放页 m3u8 链接"""
        try:
            url = id
            # 兼容相对路径
            if url.startswith('/'):
                url = self.BASE_URL + url
            elif not url.startswith('http'):
                url = self.BASE_URL + '/vodplay/' + url

            resp = self._get(url)
            if not resp:
                return {}

            m3u8_url = self._extract_m3u8(resp.text)
            if not m3u8_url:
                return {}

            return {
                "parse": 0,
                "playUrl": "",
                "url": m3u8_url,
                "header": "",
            }
        except Exception as e:
            logger.error(f"解析播放失败: {e}")
            return {}

    def _extract_m3u8(self, html):
        """从播放页提取 m3u8 链接"""
        match = re.search(r'player_aaaa\s*=\s*({[^<]+})', html)
        if match:
            try:
                data = json.loads(match.group(1))
                m3u8_url = data.get('url', '')
                if m3u8_url:
                    return m3u8_url
            except Exception:
                pass
        # 兜底：直接匹配 m3u8
        m = re.search(r'(https?://[^"\'\\s]+\.m3u8[^"\'\\s]*)', html)
        return m.group(1) if m else ''

    # ==================== 搜索 ====================
    def searchContent(self, key, quick, pg="1"):
        """搜索内容 - TVBox标准接口(key, quick, pg)
        优先使用AJAX接口（JSON格式，速度快），失败则回退到HTML搜索页
        """
        try:
            page = int(pg) if pg else 1
            encoded_key = urllib.parse.quote(key)

            # 优先尝试 AJAX 建议接口（返回JSON，数据干净）
            ajax_url = f"{self.BASE_URL}/index.php/ajax/suggest?mid=1&wd={encoded_key}"
            resp = self._get(ajax_url)
            if resp and resp.headers.get('content-type', '').find('json') >= 0:
                try:
                    data = resp.json()
                    if data.get('code') == 1 and data.get('list'):
                        videos = []
                        for item in data['list']:
                            videos.append({
                                "vod_id": str(item.get('id', '')),
                                "vod_name": item.get('name', ''),
                                "vod_pic": item.get('pic', ''),
                                "vod_remarks": item.get('note', ''),
                            })
                        return {
                            "list": videos,
                            "page": data.get('page', page),
                            "pagecount": data.get('pagecount', 1),
                            "limit": data.get('limit', 20),
                            "total": data.get('total', len(videos)),
                        }
                except Exception:
                    pass

            # 回退到HTML搜索页
            url = f"{self.BASE_URL}/vodsearch/-------------.html?wd={encoded_key}"
            if page > 1:
                url += f"&page={page}"

            resp = self._get(url)
            if not resp:
                return {"list": [], "page": page, "pagecount": 1, "limit": 20, "total": 0}

            if any(k in resp.text for k in ['验证码', '人机验证', '安全验证', 'just_a_test']):
                logger.warning("搜索被安全验证拦截")
                return {"list": [], "page": page, "pagecount": 1, "limit": 20, "total": 0}

            videos = self._parse_video_list(resp.text)
            pagecount = self._parse_total_pages(resp.text)

            return {
                "list": videos,
                "page": page,
                "pagecount": pagecount if pagecount > 1 else 1,
                "limit": 20,
                "total": len(videos) * pagecount if pagecount > 1 else len(videos),
            }
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return {"list": [], "page": 1, "pagecount": 1, "limit": 20, "total": 0}
