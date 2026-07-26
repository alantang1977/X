# -*- coding: utf-8 -*-
"""
太二追剧 — 兼容 FongMi/TV (T3) 与 WebHomeTV/PeekPro (T4) 双壳子
站点: https://v.tai2.lol/
版本: 1.1.0
"""
import sys
import json
import re
import time
import base64
from urllib.parse import urljoin, quote

sys.path.append('..')

# ===== 兼容导入：FM 有基类，PeekPro 没有就自己定义 =====
try:
    from base.spider import Spider
except ImportError:
    import requests as rq
    class Spider:
        def fetch(self, url, headers=None, **kw):
            kw.pop('timeout', None)
            r = rq.get(url, headers=headers, timeout=15, **kw)
            r.encoding = 'utf-8'
            return r


class Spider(Spider):
    """太二追剧 Spider — 综艺/电视剧/电影聚合站"""

    def getName(self):
        return "太二追剧"

    def init(self, extend=""):
        """初始化：extend 对应站点配置中的 ext 字段"""
        if isinstance(extend, list):
            self.extend = ''
        else:
            self.extend = extend or ''

        self.host = "https://v.tai2.lol"
        self.header = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
            'Referer': self.host + '/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
        }
        self._home_cache = []
        self._home_cache_time = 0

    # ========== 网络请求封装（带异常兜底）==========
    def _txt(self, url, referer=None, timeout=30):
        """获取页面文本，带异常兜底"""
        headers = dict(self.header)
        if referer:
            headers["Referer"] = referer
        try:
            rsp = self.fetch(url, headers=headers, timeout=timeout)
            try:
                rsp.encoding = "utf-8"
            except Exception:
                pass
            return rsp.text
        except Exception:
            return ""

    def _match(self, pattern, text, flags=0):
        """正则匹配，失败返回空字符串"""
        m = re.search(pattern, text, flags)
        return m.group(1) if m else ""

    def _url(self, path):
        """拼接完整 URL"""
        if not path:
            return ""
        if path.startswith("http"):
            return path
        return urljoin(self.host, path)

    # ========== 首页 ==========
    def homeContent(self, filter):
        """返回首页分类和筛选器"""
        result = {
            "class": [
                {"type_id": "1", "type_name": "电影"},
                {"type_id": "2", "type_name": "电视剧"},
                {"type_id": "3", "type_name": "综艺"},
                {"type_id": "4", "type_name": "动漫"},
            ]
        }
        if filter:
            result["filters"] = {
                "1": [
                    {
                        "key": "cate",
                        "name": "分类",
                        "value": [
                            {"n": "全部", "v": ""},
                            {"n": "动作片", "v": "6"},
                            {"n": "喜剧片", "v": "7"},
                            {"n": "爱情片", "v": "8"},
                            {"n": "科幻片", "v": "9"},
                            {"n": "恐怖片", "v": "10"},
                            {"n": "剧情片", "v": "11"},
                            {"n": "战争片", "v": "12"},
                            {"n": "纪录片", "v": "20"},
                        ]
                    },
                    {
                        "key": "year",
                        "name": "年份",
                        "value": [
                            {"n": "全部", "v": ""},
                            {"n": "2026", "v": "2026"},
                            {"n": "2025", "v": "2025"},
                            {"n": "2024", "v": "2024"},
                            {"n": "2023", "v": "2023"},
                            {"n": "2022", "v": "2022"},
                            {"n": "2021", "v": "2021"},
                            {"n": "2020", "v": "2020"},
                        ]
                    },
                    {
                        "key": "area",
                        "name": "地区",
                        "value": [
                            {"n": "全部", "v": ""},
                            {"n": "大陆", "v": "大陆"},
                            {"n": "香港", "v": "香港"},
                            {"n": "台湾", "v": "台湾"},
                            {"n": "美国", "v": "美国"},
                            {"n": "韩国", "v": "韩国"},
                            {"n": "日本", "v": "日本"},
                            {"n": "泰国", "v": "泰国"},
                            {"n": "英国", "v": "英国"},
                        ]
                    },
                ],
                "2": [
                    {
                        "key": "cate",
                        "name": "分类",
                        "value": [
                            {"n": "全部", "v": ""},
                            {"n": "国产剧", "v": "13"},
                            {"n": "港台剧", "v": "14"},
                            {"n": "日韩剧", "v": "15"},
                            {"n": "欧美剧", "v": "16"},
                            {"n": "海外剧", "v": "21"},
                        ]
                    },
                    {
                        "key": "year",
                        "name": "年份",
                        "value": [
                            {"n": "全部", "v": ""},
                            {"n": "2026", "v": "2026"},
                            {"n": "2025", "v": "2025"},
                            {"n": "2024", "v": "2024"},
                            {"n": "2023", "v": "2023"},
                            {"n": "2022", "v": "2022"},
                            {"n": "2021", "v": "2021"},
                        ]
                    },
                ],
                "3": [
                    {
                        "key": "cate",
                        "name": "分类",
                        "value": [
                            {"n": "全部", "v": ""},
                            {"n": "大陆综艺", "v": "22"},
                            {"n": "港台综艺", "v": "23"},
                            {"n": "日韩综艺", "v": "24"},
                            {"n": "欧美综艺", "v": "25"},
                        ]
                    },
                    {
                        "key": "year",
                        "name": "年份",
                        "value": [
                            {"n": "全部", "v": ""},
                            {"n": "2026", "v": "2026"},
                            {"n": "2025", "v": "2025"},
                            {"n": "2024", "v": "2024"},
                            {"n": "2023", "v": "2023"},
                        ]
                    },
                ],
                "4": [
                    {
                        "key": "cate",
                        "name": "分类",
                        "value": [
                            {"n": "全部", "v": ""},
                            {"n": "国产动漫", "v": "26"},
                            {"n": "日本动漫", "v": "27"},
                            {"n": "欧美动漫", "v": "28"},
                            {"n": "海外动漫", "v": "29"},
                        ]
                    },
                    {
                        "key": "year",
                        "name": "年份",
                        "value": [
                            {"n": "全部", "v": ""},
                            {"n": "2026", "v": "2026"},
                            {"n": "2025", "v": "2025"},
                            {"n": "2024", "v": "2024"},
                            {"n": "2023", "v": "2023"},
                        ]
                    },
                ],
            }
        return result

    def homeVideoContent(self):
        """首页精选内容"""
        now = int(time.time())
        if self._home_cache and now - self._home_cache_time < 300:
            return {"list": self._home_cache[:72]}

        try:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            tids = ["1", "2", "3", "4"]
            videos = []
            seen = set()

            def load(tid):
                # 尝试多种 URL 格式
                urls = [
                    self.host + "/vodshow/" + tid + "-----------.html",
                    self.host + "/type/" + tid + ".html",
                    self.host + "/vodtype/" + tid + ".html",
                ]
                for u in urls:
                    html = self._txt(u, timeout=12)
                    if html and len(html) > 1000 and "520" not in html[:500]:
                        return self._parse_list(html)
                return []

            pool = ThreadPoolExecutor(max_workers=4)
            futures = [pool.submit(load, t) for t in tids]
            try:
                for fu in as_completed(futures, timeout=18):
                    for v in fu.result() or []:
                        vid = v.get("vod_id")
                        if vid and vid not in seen:
                            seen.add(vid)
                            videos.append(v)
                        if len(videos) >= 72:
                            break
            finally:
                pool.shutdown(wait=False)

            self._home_cache = videos[:72]
            self._home_cache_time = now
            return {"list": self._home_cache}
        except Exception:
            return {"list": []}

    # ========== 分类列表 ==========
    def categoryContent(self, tid, pg, filter, extend):
        """分类列表页 — 支持多种 URL 格式"""
        cate = extend.get("cate", "") if extend else ""
        year = extend.get("year", "") if extend else ""
        area = extend.get("area", "") if extend else ""

        # 尝试多种 URL 格式
        urls_to_try = []

        # 格式1: 苹果 CMS 标准 /vodshow/tid-cate-by-class-area-year-letter-order-pg.html
        if cate or year or area:
            urls_to_try.append(self.host + "/vodshow/" + tid + "-" + cate + "--" + year + "--" + area + "---" + pg + ".html")
            urls_to_try.append(self.host + "/vodshow/" + tid + "-" + cate + "--------" + pg + ".html")
        urls_to_try.append(self.host + "/vodshow/" + tid + "-----------" + pg + ".html")

        # 格式2: 简化 /type/tid-pg.html
        urls_to_try.append(self.host + "/type/" + tid + "-" + pg + ".html")
        urls_to_try.append(self.host + "/type/" + tid + ".html")

        # 格式3: /vodtype/tid-pg.html
        urls_to_try.append(self.host + "/vodtype/" + tid + "-" + pg + ".html")
        urls_to_try.append(self.host + "/vodtype/" + tid + ".html")

        rsp = ""
        videos = []
        for url in urls_to_try:
            rsp = self._txt(url, timeout=30)
            if rsp and len(rsp) > 1000 and "520" not in rsp[:500]:
                videos = self._parse_list(rsp)
                if videos:
                    break

        # 估算总页数
        total_match = self._match(r'共\s*(\d+)\s*条', rsp) or self._match(r'total\s*[:=]\s*(\d+)', rsp)
        total = int(total_match) if total_match and total_match.isdigit() else max(len(videos) * 10, 20)
        limit = 20
        pagecount = (total + limit - 1) // limit if total > 0 else 10

        result = {
            "list": videos,
            "page": pg,
            "pagecount": pagecount,
            "limit": limit,
            "total": total,
        }
        return result

    # ========== 详情页（关键：ids 兼容 list 和 str）==========
    def detailContent(self, ids):
        """影片详情页"""
        if isinstance(ids, str):
            ids = [ids]
        vod_id = ids[0]

        # 尝试多种详情页 URL 格式
        urls_to_try = [
            self.host + "/detail/" + vod_id + ".html",
            self.host + "/voddetail/" + vod_id + ".html",
            self.host + "/vod/" + vod_id + ".html",
        ]

        rsp = ""
        for url in urls_to_try:
            rsp = self._txt(url, timeout=30)
            if rsp and len(rsp) > 1000 and "520" not in rsp[:500]:
                break

        if not rsp:
            return {"list": []}

        # 解析详情 — 多种模式尝试
        vod_name = self._extract_title(rsp)
        vod_pic = self._extract_pic(rsp)
        type_name = self._extract_field(rsp, [r'类型[：:]\s*([^<\n]+)', r'class=["\']type["\'][^>]*>([^<]+)'])
        vod_year = self._extract_field(rsp, [r'年份[：:]\s*([^<\n]+)', r'class=["\']year["\'][^>]*>([^<]+)'])
        vod_area = self._extract_field(rsp, [r'地区[：:]\s*([^<\n]+)', r'class=["\']area["\'][^>]*>([^<]+)'])
        vod_remarks = self._extract_field(rsp, [r'状态[：:]\s*([^<\n]+)', r'class=["\']remarks?["\'][^>]*>([^<]+)', r'class=["\']note["\'][^>]*>([^<]+)'])
        vod_actor = self._extract_field(rsp, [r'主演[：:]\s*([^<\n]+)', r'class=["\']actor["\'][^>]*>([^<]+)'])
        vod_director = self._extract_field(rsp, [r'导演[：:]\s*([^<\n]+)', r'class=["\']director["\'][^>]*>([^<]+)'])
        vod_content = self._extract_content(rsp)

        # 解析播放列表
        play_from_list, play_url_list = self._extract_playlist(rsp, url)

        vod = {
            "vod_id": vod_id,
            "vod_name": vod_name or "未知影片",
            "vod_pic": vod_pic,
            "type_name": type_name or "",
            "vod_year": vod_year or "",
            "vod_area": vod_area or "",
            "vod_remarks": vod_remarks or "",
            "vod_actor": vod_actor or "",
            "vod_director": vod_director or "",
            "vod_content": vod_content or "暂无简介",
            "vod_play_from": "$$$".join(play_from_list) if play_from_list else "默认线路",
            "vod_play_url": "$$$".join(play_url_list) if play_url_list else "正片$" + url,
        }
        return {"list": [vod]}

    # ========== 搜索 ==========
    def searchContent(self, key, quick, pg="1"):
        """搜索功能"""
        urls_to_try = [
            self.host + "/vodsearch/" + quote(key) + "----------" + pg + ".html",
            self.host + "/search.html?wd=" + quote(key) + "&page=" + pg,
            self.host + "/search?wd=" + quote(key) + "&page=" + pg,
        ]

        videos = []
        for url in urls_to_try:
            rsp = self._txt(url, timeout=30)
            if rsp and len(rsp) > 1000 and "520" not in rsp[:500]:
                videos = self._parse_list(rsp)
                if videos:
                    break

        return {"list": videos}

    # ========== 播放解析 ==========
    def playerContent(self, flag, id, vipFlags):
        """
        flag: 播放来源名
        id: 集数 URL/ID
        """
        url = id if str(id).startswith("http") else self._url(id)
        html = self._txt(url, referer=self.host + "/", timeout=30)

        if not html:
            return {"parse": 1, "playUrl": "", "url": url}

        real = ""

        # 1. player_aaaa JSON
        m = re.search(
            r'var\s+player_[a-zA-Z0-9_]+\s*=\s*(\{.*?\})\s*</script>',
            html, re.S
        )
        if m:
            try:
                data = json.loads(m.group(1))
                real = data.get("url", "") or ""
                encrypt = data.get("encrypt", 0)
                if encrypt in [1, 2] and real:
                    try:
                        real = base64.b64decode(real).decode("utf-8")
                    except Exception:
                        pass
            except Exception:
                real = self._match(r'"url"\s*:\s*"([^"]+)"', m.group(1))

        # 2. iframe 嵌套
        if not real:
            iframe = re.search(
                r'<iframe[^>]+src=["\']([^"\']+)["\']',
                html, re.S
            )
            if iframe:
                iframe_url = self._url(iframe.group(1))
                iframe_html = self._txt(iframe_url, referer=url, timeout=30)
                real = self._match(r'"url"\s*:\s*"([^"]+)"', iframe_html)
                if not real:
                    real = self._match(
                        r'["\'](https?://[^"\']+\.(?:m3u8|mp4)[^"\']*)["\']',
                        iframe_html, re.I
                    )

        # 3. 全局匹配 m3u8/mp4
        if not real:
            m2 = re.search(
                r'["\'](https?://[^"\']+\.(?:m3u8|mp4)[^"\']*)["\']',
                html, re.I
            )
            if m2:
                real = m2.group(1)

        # 4. 解析到子 m3u8
        if real and real.endswith(".m3u8"):
            real = self._resolve_m3u8_child(real, referer=url)

        if real:
            real = real.replace("\\/", "/")
            return {
                "parse": 0,
                "playUrl": "",
                "url": real,
                "header": {
                    "User-Agent": self.header["User-Agent"],
                    "Referer": url,
                },
                "format": "application/x-mpegURL",
                "contentType": "application/x-mpegURL",
            }

        return {
            "parse": 1,
            "playUrl": "",
            "url": url,
            "header": {
                "User-Agent": self.header["User-Agent"],
                "Referer": url,
            },
        }

    # ========== 列表解析 — 超宽松匹配 ==========
    def _parse_list(self, html):
        """从 HTML 中解析影片列表 — 支持多种常见结构"""
        videos = []
        if not html or len(html) < 500:
            return videos

        # 模式1: 标准苹果 CMS 卡片结构 (li > a > img + title)
        items = re.findall(
            r'<li[^>]*>.*?<a[^>]+href=["\']([^"\']*(?:detail|vod|play)[^"\']*)["\'][^>]*>.*?'
            r'<img[^>]+(?:data-original|src)=["\']([^"\']+)["\'][^>]*>.*?'
            r'<[^>]*class=["\'][^"\']*(?:title|name)[^"\']*["\'][^>]*>(.*?)</[^>]*>.*?'
            r'(?:<[^>]*class=["\'][^"\']*(?:remarks?|note|status)[^"\']*["\'][^>]*>(.*?)</[^>]*>)?'
            r'.*?</li>',
            html, re.S
        )

        if items:
            for href, pic, title, remarks in items:
                title = re.sub(r'<[^>]+>', '', title).strip()
                remarks = re.sub(r'<[^>]+>', '', remarks).strip() if remarks else ""
                vid = self._extract_id(href)
                if vid:
                    videos.append({
                        "vod_id": str(vid),
                        "vod_name": title,
                        "vod_pic": self._url(pic),
                        "vod_remarks": remarks,
                    })

        # 模式2: div 卡片结构
        if not videos:
            cards = re.findall(
                r'<div[^>]*class=["\'][^"\']*(?:item|card|vod|video|pic)[^"\']*["\'][^>]*>.*?'
                r'<a[^>]+href=["\']([^"\']*(?:detail|vod|play)[^"\']*)["\'][^>]*>.*?'
                r'<img[^>]+(?:data-original|src)=["\']([^"\']+)["\'][^>]*>.*?'
                r'<[^>]*class=["\'][^"\']*(?:title|name)[^"\']*["\'][^>]*>(.*?)</[^>]*>.*?'
                r'(?:<[^>]*class=["\'][^"\']*(?:remarks?|note|status|text)[^"\']*["\'][^>]*>(.*?)</[^>]*>)?'
                r'.*?</div>',
                html, re.S
            )
            for href, pic, title, remarks in cards:
                title = re.sub(r'<[^>]+>', '', title).strip()
                remarks = re.sub(r'<[^>]+>', '', remarks).strip() if remarks else ""
                vid = self._extract_id(href)
                if vid:
                    videos.append({
                        "vod_id": str(vid),
                        "vod_name": title,
                        "vod_pic": self._url(pic),
                        "vod_remarks": remarks,
                    })

        # 模式3: 最宽松的 a + img 匹配
        if not videos:
            links = re.findall(
                r'<a[^>]+href=["\']([^"\']*(?:detail|vod|play)[^"\']*)["\'][^>]*>.*?'
                r'<img[^>]+(?:data-original|src)=["\']([^"\']+)["\'][^>]*>.*?'
                r'</a>',
                html, re.S
            )
            for href, pic in links:
                vid = self._extract_id(href)
                if vid:
                    videos.append({
                        "vod_id": str(vid),
                        "vod_name": "",
                        "vod_pic": self._url(pic),
                        "vod_remarks": "",
                    })

        return videos

    def _extract_id(self, href):
        """从 URL 中提取影片 ID"""
        if not href:
            return None
        # 尝试多种 ID 格式
        patterns = [
            r'/(\d+)\.html',
            r'id=(\d+)',
            r'/(\d+)/?$',
            r'/(\d+)\.htm',
        ]
        for p in patterns:
            m = re.search(p, href)
            if m:
                return m.group(1)
        # 如果都没匹配到，返回 URL 本身
        return href

    def _extract_title(self, html):
        """提取影片标题"""
        # 尝试多种模式
        patterns = [
            r'<h1[^>]*>(.*?)</h1>',
            r'<h2[^>]*>(.*?)</h2>',
            r'class=["\']title["\'][^>]*>(.*?)</[^>]*>',
            r'class=["\']name["\'][^>]*>(.*?)</[^>]*>',
            r'<title>(.*?)</title>',
        ]
        for p in patterns:
            title = self._match(p, html)
            if title:
                title = re.sub(r'<[^>]+>', '', title).strip()
                if title and title != "太二追剧":
                    return title
        return ""

    def _extract_pic(self, html):
        """提取封面图"""
        patterns = [
            r'<img[^>]+class=["\'][^"\']*(?:poster|pic|thumb)[^"\']*["\'][^>]+src=["\']([^"\']+)["\']',
            r'<img[^>]+src=["\']([^"\']+)["\'][^>]+class=["\'][^"\']*(?:poster|pic|thumb)[^"\']*["\']',
            r'poster["\']?\s*[:=]\s*["\']([^"\']+)',
            r'<img[^>]+src=["\']([^"\']+)["\'][^>]*class=["\'][^"\']*vod[^"\']*["\']',
        ]
        for p in patterns:
            pic = self._match(p, html)
            if pic:
                return self._url(pic)
        return ""

    def _extract_field(self, html, patterns):
        """通用字段提取"""
        for p in patterns:
            val = self._match(p, html)
            if val:
                val = re.sub(r'<[^>]+>', '', val).strip()
                if val:
                    return val
        return ""

    def _extract_content(self, html):
        """提取剧情简介"""
        patterns = [
            r'简介[：:]\s*</h[\d][^>]*>\s*<p[^>]*>(.*?)</p>',
            r'class=["\']desc["\'][^>]*>(.*?)</[^>]*>',
            r'class=["\']content["\'][^>]*>(.*?)</[^>]*>',
            r'class=["\']summary["\'][^>]*>(.*?)</[^>]*>',
            r'剧情[：:]\s*<[^>]*>(.*?)</[^>]*>',
        ]
        for p in patterns:
            content = self._match(p, html)
            if content:
                content = re.sub(r'<[^>]+>', '', content).strip()
                if content:
                    return content
        return ""

    def _extract_playlist(self, html, referer_url):
        """提取播放列表"""
        play_from_list = []
        play_url_list = []

        # 模式1: 标准播放器列表 (div.player_list)
        player_blocks = re.findall(
            r'<div[^>]*class=["\'][^"\']*player_list[^"\']*["\'][^>]*>(.*?)</div>',
            html, re.S
        )
        if player_blocks:
            for block in player_blocks:
                source_name = self._match(r'<h3[^>]*>(.*?)</h3>', block) or \
                              self._match(r'<span[^>]*>(.*?)</span>', block) or \
                              "默认线路"
                source_name = re.sub(r'<[^>]+>', '', source_name).strip()
                play_from_list.append(source_name)

                episodes = re.findall(
                    r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
                    block, re.S
                )
                ep_strs = []
                for ep_url, ep_name in episodes:
                    ep_name = re.sub(r'<[^>]+>', '', ep_name).strip()
                    ep_url = self._url(ep_url)
                    ep_strs.append(ep_name + "$" + ep_url)
                play_url_list.append("#".join(ep_strs))

        # 模式2: 通用播放列表 (ul/li 结构)
        if not play_from_list:
            lists = re.findall(
                r'<ul[^>]*class=["\'][^"\']*(?:play|episode|list)[^"\']*["\'][^>]*>(.*?)</ul>',
                html, re.S
            )
            if lists:
                for lst in lists:
                    play_from_list.append("默认线路")
                    episodes = re.findall(
                        r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
                        lst, re.S
                    )
                    ep_strs = []
                    for ep_url, ep_name in episodes:
                        ep_name = re.sub(r'<[^>]+>', '', ep_name).strip()
                        ep_url = self._url(ep_url)
                        ep_strs.append(ep_name + "$" + ep_url)
                    play_url_list.append("#".join(ep_strs))

        # 模式3: 最宽松的 a 标签
        if not play_from_list:
            ep_pattern = re.findall(
                r'<a[^>]+href=["\']([^"\']*(?:play|vodplay)[^"\']*)["\'][^>]*>(.*?)</a>',
                html, re.S
            )
            if ep_pattern:
                play_from_list.append("默认线路")
                ep_strs = []
                for ep_url, ep_name in ep_pattern:
                    ep_name = re.sub(r'<[^>]+>', '', ep_name).strip()
                    ep_url = self._url(ep_url)
                    ep_strs.append(ep_name + "$" + ep_url)
                play_url_list.append("#".join(ep_strs))

        # 兜底
        if not play_from_list:
            play_from_list.append("默认线路")
            play_url_list.append("正片$" + referer_url)

        return play_from_list, play_url_list

    # ========== m3u8 子解析（Exo 兼容）==========
    def _resolve_m3u8_child(self, m3u8_url, referer=""):
        """Exo 对部分主 m3u8 的相对跳转兼容差，优先解析到子 m3u8。"""
        text = self._txt(m3u8_url, referer=referer or self.host + "/", timeout=20)
        if not text or "#EXTM3U" not in text:
            return m3u8_url
        lines = [x.strip() for x in text.splitlines() if x.strip()]
        for i, line in enumerate(lines):
            if line.startswith("#EXT-X-STREAM-INF"):
                for nxt in lines[i + 1:]:
                    if nxt and not nxt.startswith("#"):
                        return urljoin(m3u8_url, nxt)
        return m3u8_url

    # ========== 本地代理（可选）==========
    def localProxy(self, param):
        """本地 HTTP 代理"""
        return [200, "video/MP2T", b"", ""]

    # ========== 清理 ==========
    def destroy(self):
        """T3 清理方法"""
        pass

    def close(self):
        """T4 daemon 关闭时调用"""
        self.destroy()
