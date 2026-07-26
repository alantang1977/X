# -*- coding: utf-8 -*-
"""
太乙电影 — 兼容 FongMi/TV (T3) 与 WebHomeTV/PeekPro (T4) 双壳子
修复: 分页加载 + 播放解析
站点: https://ww98.taiee.xyz/
版本: 3.1.0
"""
import sys
import json
import re
import time
import base64
from urllib.parse import urljoin, quote, unquote

sys.path.append('..')

# ===== 兼容导入 =====
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
    """太乙电影 Spider — 修复分页和播放"""

    def getName(self):
        return "太乙电影"

    def init(self, extend=""):
        if isinstance(extend, list):
            self.extend = ''
        else:
            self.extend = extend or ''

        self.host = "https://ww98.taiee.xyz"
        self.api_base = self.host + "/api.php/provide/vod/"

        # 完整请求头
        self.header = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': self.host + '/',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }

        self.api_header = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': self.host + '/',
        }

        self._home_cache = []
        self._home_cache_time = 0
        self._class_list = []
        self._use_api = None
        # 分页缓存
        self._page_cache = {}
        self._api_total_info = None

    # ========== 网络请求封装 ==========
    def _fetch_json(self, url, timeout=30):
        try:
            rsp = self.fetch(url, headers=self.api_header, timeout=timeout)
            try:
                rsp.encoding = "utf-8"
            except Exception:
                pass
            text = rsp.text
            if text.startswith('(') and text.endswith(')'):
                text = text[1:-1]
            return json.loads(text)
        except Exception:
            return None

    def _fetch_html(self, url, referer=None, timeout=30):
        headers = dict(self.header)
        if referer:
            headers["Referer"] = referer
        try:
            rsp = self.fetch(url, headers=headers, timeout=timeout)
            try:
                rsp.encoding = "utf-8"
            except Exception:
                pass
            text = rsp.text
            if '520' in text[:1000] and 'cloudflare' in text[:1000].lower():
                return ""
            return text
        except Exception:
            return ""

    def _match(self, pattern, text, flags=0):
        m = re.search(pattern, text, flags)
        return m.group(1) if m else ""

    def _url(self, path):
        if not path:
            return ""
        if path.startswith("http"):
            return path
        return urljoin(self.host, path)

    def _is_direct_media(self, url):
        url = (url or "").lower()
        return ".m3u8" in url or ".mp4" in url or ".flv" in url or ".mkv" in url

    def _is_official_source(self, url):
        url = (url or "").lower()
        keys = (
            "mgtv.com", "youku.com", "iqiyi.com", "qiyi.com",
            "v.qq.com", "qq.com", "bilibili.com", "le.com",
            "sohu.com", "pptv.com", "1905.com",
        )
        return any(k in url for k in keys) and not self._is_direct_media(url)

    def _aes_cbc_decrypt_text(self, cipher_text):
        try:
            from Crypto.Cipher import AES
            key = cipher_text[-32:-16].encode("utf-8")
            iv = cipher_text[-16:].encode("utf-8")
            data = base64.b64decode(cipher_text[:-32])
            raw = AES.new(key, AES.MODE_CBC, iv).decrypt(data)
            pad = raw[-1]
            if 0 < pad <= 16:
                raw = raw[:-pad]
            return raw.decode("utf-8", "ignore")
        except Exception:
            return ""

    def _decode_bfq_result(self, result):
        if not result:
            return {}
        text = self._aes_cbc_decrypt_text(result)
        if not text:
            return {}
        try:
            return json.loads(text)
        except Exception:
            return {}

    def _resolve_official_to_media(self, src_url):
        if not src_url or not self._is_official_source(src_url):
            return ""
        try:
            page_url = "https://bfq.txnp.cn/player?url=" + quote(src_url, safe="")
            headers = dict(self.header)
            headers["Referer"] = "https://bfq.txnp.cn/excessive?url=" + quote(src_url, safe="")
            html = self._fetch_html(page_url, referer=headers["Referer"], timeout=20)
            result = self._match(r'let\s+result\s*=\s*"([^"]+)"', html, re.S)
            data = self._decode_bfq_result(result)
            video = ((data.get("video_info") or {}).get("video") or {})
            media = (video.get("url") or "").replace("\\/", "/")
            if media and self._is_direct_media(media):
                if ".m3u8" in media:
                    media = self._resolve_m3u8_child(media, referer=page_url)
                return media
        except Exception:
            pass
        return ""

    def _resolve_m3u8_child(self, m3u8_url, referer=None):
        """
        有些解析返回的是 master m3u8，部分壳子/播放器兼容性差。
        这里优先取第一个清晰度子 m3u8；普通 m3u8 原样返回。
        """
        if not m3u8_url or ".m3u8" not in m3u8_url.lower():
            return m3u8_url
        try:
            headers = dict(self.header)
            if referer:
                headers["Referer"] = referer
            rsp = self.fetch(m3u8_url, headers=headers, timeout=15)
            try:
                rsp.encoding = "utf-8"
            except Exception:
                pass
            text = rsp.text or ""
            if "#EXT-X-STREAM-INF" not in text:
                return m3u8_url
            for line in text.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if ".m3u8" in line.lower():
                    return urljoin(m3u8_url, line)
        except Exception:
            pass
        return m3u8_url

    # ========== 探测API ==========
    def _detect_api(self):
        if self._use_api is not None:
            return self._use_api

        urls = [
            self.api_base + "?ac=list",
            self.host + "/api.php/provide/vod/?ac=list",
            self.host + "/api/provide/vod/?ac=list",
        ]
        for url in urls:
            data = self._fetch_json(url, timeout=10)
            if data and (data.get("class") or data.get("list")):
                self._use_api = True
                self.api_base = url.replace("?ac=list", "")
                return True

        self._use_api = False
        return False

    # ========== 首页 ==========
    def homeContent(self, filter):
        classes = []

        if self._detect_api():
            data = self._fetch_json(self.api_base + "?ac=list", timeout=15)
            if data and data.get("class"):
                for c in data["class"]:
                    classes.append({
                        "type_id": str(c.get("type_id", "")),
                        "type_name": c.get("type_name", "")
                    })

        if not classes:
            html = self._fetch_html(self.host + "/", timeout=15)
            if html:
                nav_items = re.findall(r'<a[^>]+href=["\']([^"\']*(?:type|vodshow|movie|tv)[^"\']*)["\'][^>]*>([^<]+)</a>', html, re.S)
                seen = set()
                for href, name in nav_items:
                    name = re.sub(r'<[^>]+>', '', name).strip()
                    tid = self._extract_tid_from_url(href)
                    if tid and tid not in seen and name:
                        seen.add(tid)
                        classes.append({"type_id": tid, "type_name": name})

        if not classes:
            classes = [
                {"type_id": "1", "type_name": "电影"},
                {"type_id": "2", "type_name": "电视剧"},
                {"type_id": "3", "type_name": "综艺"},
                {"type_id": "4", "type_name": "动漫"},
            ]

        cleaned = []
        seen_ids = set()
        for c in classes:
            tid = str(c.get("type_id", ""))
            name = str(c.get("type_name", "")).strip()
            if not tid or not name:
                continue
            if name in ("精选", "推荐", "首页"):
                continue
            if tid in seen_ids:
                continue
            seen_ids.add(tid)
            cleaned.append({"type_id": tid, "type_name": name})
        classes = cleaned

        if self._use_api:
            classes = [c for c in classes if str(c.get("type_id", "")) != "0" and c.get("type_name") != "全部"]
            classes = [{"type_id": "0", "type_name": "全部"}] + classes

        self._class_list = classes
        result = {"class": classes}

        if filter:
            result["filters"] = self._build_filters()

        return result

    def _build_filters(self):
        filters = {}
        year_values = [
            {"n": "全部", "v": ""},
            {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"},
            {"n": "2024", "v": "2024"}, {"n": "2023", "v": "2023"},
            {"n": "2022", "v": "2022"}, {"n": "2021", "v": "2021"},
            {"n": "2020", "v": "2020"}, {"n": "2019", "v": "2019"},
        ]
        by_values = [
            {"n": "时间", "v": "time"}, {"n": "人气", "v": "hits"}, {"n": "评分", "v": "score"},
        ]
        for c in self._class_list:
            tid = c.get("type_id", "")
            if tid:
                filters[tid] = [
                    {"key": "year", "name": "年份", "value": year_values},
                    {"key": "by", "name": "排序", "value": by_values},
                ]
        return filters

    def _extract_tid_from_url(self, url):
        m = re.search(r'[type|vodshow|t]=(\d+)', url)
        if m:
            return m.group(1)
        m = re.search(r'/(\d+)\.html', url)
        if m:
            return m.group(1)
        return None

    def homeVideoContent(self):
        now = int(time.time())
        if self._home_cache and now - self._home_cache_time < 300:
            return {"list": self._home_cache[:72]}

        videos = []
        seen = set()
        classes = self._class_list
        if not classes:
            classes = [
                {"type_id": "1", "type_name": "电影"},
                {"type_id": "2", "type_name": "电视剧"},
                {"type_id": "3", "type_name": "综艺"},
                {"type_id": "4", "type_name": "动漫"},
            ]

        # API获取
        if self._detect_api():
            for c in classes[:4]:
                tid = c.get("type_id", "")
                if not tid:
                    continue
                url = self.api_base + "?ac=videolist&t=" + tid + "&pg=1&pagesize=24"
                data = self._fetch_json(url, timeout=12)
                if data and data.get("list"):
                    for item in data["list"]:
                        vid = str(item.get("vod_id", ""))
                        if vid and vid not in seen:
                            seen.add(vid)
                            videos.append(self._format_api_vod(item))
                        if len(videos) >= 72:
                            break
                if len(videos) >= 72:
                    break

        # HTML获取
        if not videos:
            try:
                from concurrent.futures import ThreadPoolExecutor, as_completed
                def load(tid):
                    return self._load_html_list(tid, "1")
                pool = ThreadPoolExecutor(max_workers=4)
                futures = [pool.submit(load, c.get("type_id", "")) for c in classes[:4]]
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
            except Exception:
                pass

        self._home_cache = videos[:72]
        self._home_cache_time = now
        return {"list": self._home_cache}

    # ========== 分类列表 — 三层fallback ==========
    def categoryContent(self, tid, pg, filter, extend):
        try:
            ext_key = json.dumps(extend or {}, ensure_ascii=False, sort_keys=True)
        except Exception:
            ext_key = ""
        cache_key = str(tid) + "_" + str(pg) + "_" + ext_key
        if cache_key in self._page_cache:
            cached = self._page_cache[cache_key]
            if int(time.time()) - cached.get("_time", 0) < 60:
                return cached

        result = self._try_api_category(tid, pg, extend)
        if result is not None:
            self._page_cache[cache_key] = result
            return result

        result = self._try_html_category(tid, pg, extend)
        if result and result.get("list"):
            self._page_cache[cache_key] = result
            return result

        result = self._try_common_category(tid, pg)
        if result and result.get("list"):
            self._page_cache[cache_key] = result
            return result

        return {"list": [], "page": pg, "pagecount": 999, "limit": 20, "total": 9999}

    def _get_api_total_info(self):
        if self._api_total_info:
            return self._api_total_info
        info = {"pagecount": 999, "total": 9999, "limit": 20}
        try:
            data = self._fetch_json(self.api_base + "?ac=videolist&pg=1&pagesize=20", timeout=15)
            if data:
                info["pagecount"] = int(data.get("pagecount") or 999)
                info["total"] = int(data.get("total") or 9999)
                info["limit"] = int(data.get("limit") or 20)
        except Exception:
            pass
        self._api_total_info = info
        return info

    def _try_api_category(self, tid, pg, extend):
        if not self._detect_api():
            return None

        tid = str(tid or "")
        pg = str(pg or "1")
        is_all = tid in ("0", "all", "全部", "")
        params = "?ac=videolist&pg=" + pg + "&pagesize=20"
        if not is_all:
            params += "&t=" + tid
        if extend:
            year = extend.get("year", "")
            by = extend.get("by", "")
            if year:
                params += "&year=" + year
            if by:
                params += "&by=" + by

        data = self._fetch_json(self.api_base + params, timeout=30)
        if not data:
            return None

        videos = []
        if data.get("list"):
            for item in data["list"]:
                videos.append(self._format_api_vod(item))

        page = int(data.get("page") or pg)
        total = int(data.get("total") or 0)
        limit = int(data.get("limit") or 20)
        api_pagecount = int(data.get("pagecount") or 0)

        if total > 0 and limit > 0:
            pagecount = (total + limit - 1) // limit
        else:
            # 如果API没返回total，根据是否有内容来判断
            pagecount = 999 if len(videos) >= limit else page
        if api_pagecount > 0:
            pagecount = max(pagecount, api_pagecount)

        total_info = self._get_api_total_info()
        if is_all:
            pagecount = max(pagecount, total_info.get("pagecount", 999))
            total = max(total, total_info.get("total", 9999))

        return {
            "list": videos,
            "page": str(page),
            "pagecount": pagecount,
            "limit": limit,
            "total": total if total > 0 else 9999,
        }

    def _try_html_category(self, tid, pg, extend):
        urls = []
        cate = extend.get("cate", "") if extend else ""
        year = extend.get("year", "") if extend else ""

        if cate or year:
            urls.append(self.host + "/vodshow/" + tid + "-" + cate + "--" + year + "------" + pg + ".html")
            urls.append(self.host + "/vodshow/" + tid + "-" + cate + "--------" + pg + ".html")
        urls.append(self.host + "/vodshow/" + tid + "-----------" + pg + ".html")
        urls.append(self.host + "/type/" + tid + "-" + pg + ".html")
        urls.append(self.host + "/type/" + tid + ".html")
        urls.append(self.host + "/vodtype/" + tid + "-" + pg + ".html")

        for url in urls:
            html = self._fetch_html(url, timeout=30)
            if html:
                videos = self._parse_html_list(html)
                if videos:
                    # 关键修复: 估算总页数，让壳子可以无限翻页
                    total_match = self._match(r'共\s*(\d+)\s*条', html) or self._match(r'total\s*[:=]\s*(\d+)', html)
                    if total_match and total_match.isdigit():
                        total = int(total_match)
                        pagecount = (total + 23) // 24
                    else:
                        # 没拿到总数，给一个很大的数让壳子可以一直翻
                        total = 9999
                        pagecount = 999

                    return {
                        "list": videos,
                        "page": pg,
                        "pagecount": pagecount,
                        "limit": 24,
                        "total": total,
                    }
        return None

    def _try_common_category(self, tid, pg):
        return None

    def _load_html_list(self, tid, pg):
        urls = [
            self.host + "/vodshow/" + tid + "-----------" + pg + ".html",
            self.host + "/type/" + tid + "-" + pg + ".html",
            self.host + "/type/" + tid + ".html",
        ]
        for url in urls:
            html = self._fetch_html(url, timeout=12)
            if html:
                videos = self._parse_html_list(html)
                if videos:
                    return videos
        return []

    # ========== 详情页 ==========
    def detailContent(self, ids):
        if isinstance(ids, str):
            ids = [ids]
        vod_id = ids[0]

        vod = self._try_api_detail(vod_id)
        if vod:
            return {"list": [vod]}

        vod = self._try_html_detail(vod_id)
        if vod:
            return {"list": [vod]}

        return {"list": []}

    def _try_api_detail(self, vod_id):
        if not self._detect_api():
            return None

        data = self._fetch_json(self.api_base + "?ac=detail&ids=" + str(vod_id), timeout=30)
        if data and data.get("list") and len(data["list"]) > 0:
            return self._format_api_detail(data["list"][0])
        return None

    def _try_html_detail(self, vod_id):
        urls = [
            self.host + "/detail/" + str(vod_id) + ".html",
            self.host + "/voddetail/" + str(vod_id) + ".html",
            self.host + "/vod/" + str(vod_id) + ".html",
        ]

        for url in urls:
            html = self._fetch_html(url, timeout=30)
            if html:
                return self._parse_html_detail(html, vod_id, url)
        return None

    # ========== 搜索 ==========
    def searchContent(self, key, quick, pg="1"):
        if self._detect_api():
            url = self.api_base + "?ac=videolist&wd=" + quote(key) + "&pg=" + pg + "&pagesize=24"
            data = self._fetch_json(url, timeout=30)
            if data and data.get("list"):
                videos = []
                for item in data["list"]:
                    videos.append(self._format_api_vod(item))
                return {"list": videos}

        urls = [
            self.host + "/vodsearch/" + quote(key) + "----------" + pg + ".html",
            self.host + "/search.html?wd=" + quote(key) + "&page=" + pg,
            self.host + "/search?wd=" + quote(key) + "&page=" + pg,
        ]
        for url in urls:
            html = self._fetch_html(url, timeout=30)
            if html:
                videos = self._parse_html_list(html)
                if videos:
                    return {"list": videos}

        return {"list": []}

    # ========== 播放解析 — 关键修复 ==========
    def playerContent(self, flag, id, vipFlags):
        """
        关键修复:
        1. id 可能是完整URL，也可能是相对路径
        2. 需要处理苹果CMS的播放链接格式
        3. 需要处理加密和iframe嵌套
        """
        # 处理id
        if not id:
            return {"parse": 1, "playUrl": "", "url": ""}

        url = id if str(id).startswith("http") else self._url(id)

        # 如果已经是直链
        if ".m3u8" in url:
            return {
                "parse": 0,
                "playUrl": "",
                "url": url,
                "header": {
                    "User-Agent": self.header["User-Agent"],
                    "Referer": self.host + "/",
                },
                "format": "application/x-mpegURL",
                "contentType": "application/x-mpegURL",
            }

        if ".mp4" in url or ".mkv" in url or ".flv" in url:
            return {
                "parse": 0,
                "playUrl": "",
                "url": url,
                "header": {
                    "User-Agent": self.header["User-Agent"],
                    "Referer": self.host + "/",
                },
            }

        if self._is_official_source(url):
            resolved = self._resolve_official_to_media(url)
            if resolved:
                return {
                    "parse": 0,
                    "playUrl": "",
                    "url": resolved,
                    "header": {
                        "User-Agent": self.header["User-Agent"],
                        "Referer": "https://bfq.txnp.cn/",
                    },
                    "format": "application/x-mpegURL" if ".m3u8" in resolved else "",
                    "contentType": "application/x-mpegURL" if ".m3u8" in resolved else "",
                }

        # 获取播放页HTML
        html = self._fetch_html(url, referer=self.host + "/", timeout=30)
        if not html:
            # 如果获取失败，尝试直接返回URL让壳子嗅探
            return {
                "parse": 1,
                "playUrl": "",
                "url": url,
                "header": {
                    "User-Agent": self.header["User-Agent"],
                    "Referer": self.host + "/",
                },
            }

        real = ""

        # 1. player_aaaa JSON (苹果CMS标准)
        m = re.search(r'var\s+player_[a-zA-Z0-9_]+\s*=\s*(\{.*?\})\s*</script>', html, re.S)
        if m:
            try:
                data = json.loads(m.group(1))
                real = data.get("url", "") or ""
                encrypt = str(data.get("encrypt", "0"))
                if encrypt == "1" and real:
                    try:
                        real = unquote(real)
                    except Exception:
                        pass
                elif encrypt == "2" and real:
                    try:
                        real = unquote(base64.b64decode(real).decode("utf-8"))
                    except Exception:
                        pass
                # 处理from字段(播放来源)
                from_src = data.get("from", "")
                if from_src:
                    # 有些站点from字段表示播放器类型
                    pass
            except Exception:
                # JSON解析失败，尝试正则提取url
                real = self._match(r'"url"\s*:\s*"([^"]+)"', m.group(1))

        # 2. 其他player变量格式
        if not real:
            m2 = re.search(r'var\s+player\s*=\s*["\']([^"\']+)["\']', html, re.S)
            if m2:
                real = m2.group(1)
                if real.startswith("//"):
                    real = "https:" + real

        # 3. iframe嵌套
        if not real:
            iframe = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.S)
            if iframe:
                iframe_url = self._url(iframe.group(1))
                iframe_html = self._fetch_html(iframe_url, referer=url, timeout=30)
                if iframe_html:
                    # 在iframe内容中找播放地址
                    real = self._match(r'"url"\s*:\s*"([^"]+)"', iframe_html)
                    if not real:
                        real = self._match(r'["\'](https?://[^"\']+\.(?:m3u8|mp4)[^"\']*)["\']', iframe_html, re.I)
                    if not real:
                        real = self._match(r'src=["\']([^"\']+\.(?:m3u8|mp4))["\']', iframe_html, re.I)

        # 4. 全局匹配m3u8/mp4直链
        if not real:
            m3 = re.search(r'["\'](https?://[^"\']+\.(?:m3u8|mp4)[^"\']*)["\']', html, re.I)
            if m3:
                real = m3.group(1)

        # 5. 匹配data-url或data-src
        if not real:
            m4 = re.search(r'data-(?:url|src)=["\']([^"\']+)["\']', html, re.S)
            if m4:
                real = m4.group(1)
                if real.startswith("//"):
                    real = "https:" + real

        # 6. 匹配video标签src
        if not real:
            m5 = re.search(r'<video[^>]+src=["\']([^"\']+)["\']', html, re.S)
            if m5:
                real = m5.group(1)

        # 处理获取到的地址
        if real:
            real = real.replace("\\/", "/")
            if real.startswith("//"):
                real = "https:" + real

            if self._is_official_source(real):
                resolved = self._resolve_official_to_media(real)
                if resolved:
                    real = resolved

            # 如果是m3u8，解析子m3u8(Exo兼容)
            if ".m3u8" in real:
                real = self._resolve_m3u8_child(real, referer=url)

            return {
                "parse": 0 if self._is_direct_media(real) else 1,
                "playUrl": "",
                "url": real,
                "header": {
                    "User-Agent": self.header["User-Agent"],
                    "Referer": url,
                },
                "format": "application/x-mpegURL" if ".m3u8" in real else "",
                "contentType": "application/x-mpegURL" if ".m3u8" in real else "",
            }

        # 都没找到，返回原始URL让壳子自行嗅探
        return {
            "parse": 1,
            "playUrl": "",
            "url": url,
            "header": {
                "User-Agent": self.header["User-Agent"],
                "Referer": url,
            },
        }

    # ========== HTML解析 ==========
    def _parse_html_list(self, html):
        videos = []
        if not html or len(html) < 500:
            return videos

        # 模式1: li结构
        items = re.findall(
            r'<li[^>]*>.*?<a[^>]+href=["\']([^"\']*(?:detail|vod|play)[^"\']*)["\'][^>]*>.*?'
            r'<img[^>]+(?:data-original|src)=["\']([^"\']+)["\'][^>]*>.*?'
            r'(?:<[^>]*class=["\'][^"\']*(?:title|name)[^"\']*["\'][^>]*>(.*?)</[^>]*>)?'
            r'(?:.*?<[^>]*class=["\'][^"\']*(?:remarks?|note|status|text)[^"\']*["\'][^>]*>(.*?)</[^>]*>)?)?'
            r'.*?</li>',
            html, re.S
        )
        for item in items:
            href, pic = item[0], item[1]
            title = item[2] if len(item) > 2 else ""
            remarks = item[3] if len(item) > 3 else ""
            title = re.sub(r'<[^>]+>', '', title).strip() if title else ""
            remarks = re.sub(r'<[^>]+>', '', remarks).strip() if remarks else ""
            vid = self._extract_vid(href)
            if vid:
                videos.append({
                    "vod_id": str(vid),
                    "vod_name": title,
                    "vod_pic": self._url(pic),
                    "vod_remarks": remarks,
                })

        # 模式2: div卡片
        if not videos:
            cards = re.findall(
                r'<div[^>]*class=["\'][^"\']*(?:item|card|vod|video|pic|list)[^"\']*["\'][^>]*>.*?'
                r'<a[^>]+href=["\']([^"\']*(?:detail|vod|play)[^"\']*)["\'][^>]*>.*?'
                r'<img[^>]+(?:data-original|src)=["\']([^"\']+)["\'][^>]*>.*?'
                r'(?:<[^>]*class=["\'][^"\']*(?:title|name)[^"\']*["\'][^>]*>(.*?)</[^>]*>)?'
                r'(?:.*?<[^>]*class=["\'][^"\']*(?:remarks?|note|status|text)[^"\']*["\'][^>]*>(.*?)</[^>]*>)?)?'
                r'.*?</div>',
                html, re.S
            )
            for card in cards:
                href, pic = card[0], card[1]
                title = card[2] if len(card) > 2 else ""
                remarks = card[3] if len(card) > 3 else ""
                title = re.sub(r'<[^>]+>', '', title).strip() if title else ""
                remarks = re.sub(r'<[^>]+>', '', remarks).strip() if remarks else ""
                vid = self._extract_vid(href)
                if vid:
                    videos.append({
                        "vod_id": str(vid),
                        "vod_name": title,
                        "vod_pic": self._url(pic),
                        "vod_remarks": remarks,
                    })

        # 模式3: 宽松a+img
        if not videos:
            links = re.findall(
                r'<a[^>]+href=["\']([^"\']*(?:detail|vod|play)[^"\']*)["\'][^>]*>.*?'
                r'<img[^>]+(?:data-original|src)=["\']([^"\']+)["\'][^>]*>.*?</a>',
                html, re.S
            )
            for href, pic in links:
                vid = self._extract_vid(href)
                if vid:
                    videos.append({
                        "vod_id": str(vid),
                        "vod_name": "",
                        "vod_pic": self._url(pic),
                        "vod_remarks": "",
                    })

        return videos

    def _parse_html_detail(self, html, vod_id, url):
        vod_name = self._extract_title(html)
        vod_pic = self._extract_pic(html)
        type_name = self._extract_field(html, [r'类型[：:]\s*([^<\n]+)', r'class=["\']type["\'][^>]*>([^<]+)'])
        vod_year = self._extract_field(html, [r'年份[：:]\s*([^<\n]+)', r'class=["\']year["\'][^>]*>([^<]+)'])
        vod_area = self._extract_field(html, [r'地区[：:]\s*([^<\n]+)', r'class=["\']area["\'][^>]*>([^<]+)'])
        vod_remarks = self._extract_field(html, [r'状态[：:]\s*([^<\n]+)', r'class=["\']remarks?["\'][^>]*>([^<]+)', r'class=["\']note["\'][^>]*>([^<]+)'])
        vod_actor = self._extract_field(html, [r'主演[：:]\s*([^<\n]+)', r'class=["\']actor["\'][^>]*>([^<]+)'])
        vod_director = self._extract_field(html, [r'导演[：:]\s*([^<\n]+)', r'class=["\']director["\'][^>]*>([^<]+)'])
        vod_content = self._extract_content(html)

        play_from_list, play_url_list = self._extract_playlist(html, url)

        return {
            "vod_id": str(vod_id),
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

    def _extract_vid(self, href):
        if not href:
            return None
        patterns = [r'/(\d+)\.html', r'id=(\d+)', r'/(\d+)/?$', r'/(\d+)\.htm']
        for p in patterns:
            m = re.search(p, href)
            if m:
                return m.group(1)
        return href

    def _extract_title(self, html):
        patterns = [
            r'<h1[^>]*>(.*?)</h1>', r'<h2[^>]*>(.*?)</h2>',
            r'class=["\']title["\'][^>]*>(.*?)</[^>]*>',
            r'class=["\']name["\'][^>]*>(.*?)</[^>]*>',
            r'<title>(.*?)</title>',
        ]
        for p in patterns:
            title = self._match(p, html)
            if title:
                title = re.sub(r'<[^>]+>', '', title).strip()
                if title and title != "太乙电影":
                    return title
        return ""

    def _extract_pic(self, html):
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
        for p in patterns:
            val = self._match(p, html)
            if val:
                val = re.sub(r'<[^>]+>', '', val).strip()
                if val:
                    return val
        return ""

    def _extract_content(self, html):
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
        play_from_list = []
        play_url_list = []

        # 模式1: player_list div
        blocks = re.findall(r'<div[^>]*class=["\'][^"\']*player_list[^"\']*["\'][^>]*>(.*?)</div>', html, re.S)
        if blocks:
            for block in blocks:
                source = self._match(r'<h3[^>]*>(.*?)</h3>', block) or self._match(r'<span[^>]*>(.*?)</span>', block) or "默认线路"
                source = re.sub(r'<[^>]+>', '', source).strip()
                play_from_list.append(source)
                eps = re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', block, re.S)
                ep_strs = []
                for ep_url, ep_name in eps:
                    ep_name = re.sub(r'<[^>]+>', '', ep_name).strip()
                    ep_url = self._url(ep_url)
                    ep_strs.append(ep_name + "$" + ep_url)
                play_url_list.append("#".join(ep_strs))

        # 模式2: ul/li
        if not play_from_list:
            lists = re.findall(r'<ul[^>]*class=["\'][^"\']*(?:play|episode|list)[^"\']*["\'][^>]*>(.*?)</ul>', html, re.S)
            for lst in lists:
                play_from_list.append("默认线路")
                eps = re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', lst, re.S)
                ep_strs = []
                for ep_url, ep_name in eps:
                    ep_name = re.sub(r'<[^>]+>', '', ep_name).strip()
                    ep_url = self._url(ep_url)
                    ep_strs.append(ep_name + "$" + ep_url)
                play_url_list.append("#".join(ep_strs))

        # 模式3: 通用a标签
        if not play_from_list:
            eps = re.findall(r'<a[^>]+href=["\']([^"\']*(?:play|vodplay)[^"\']*)["\'][^>]*>(.*?)</a>', html, re.S)
            if eps:
                play_from_list.append("默认线路")
                ep_strs = []
                for ep_url, ep_name in eps:
                    ep_name = re.sub(r'<[^>]+>', '', ep_name).strip()
                    ep_url = self._url(ep_url)
                    ep_strs.append(ep_name + "$" + ep_url)
                play_url_list.append("#".join(ep_strs))

        if not play_from_list:
            play_from_list.append("默认线路")
            play_url_list.append("正片$" + referer_url)

        return play_from_list, play_url_list

    # ========== API格式化 ==========
    def _format_api_vod(self, item):
        return {
            "vod_id": str(item.get("vod_id", "")),
            "vod_name": item.get("vod_name", ""),
            "vod_pic": item.get("vod_pic", ""),
            "type_name": item.get("type_name", ""),
            "vod_year": item.get("vod_year", ""),
            "vod_area": item.get("vod_area", ""),
            "vod_remarks": item.get("vod_remarks", item.get("vod_serial", "")),
            "vod_actor": item.get("vod_actor", ""),
            "vod_director": item.get("vod_director", ""),
        }

    def _format_api_detail(self, item):
        play_from = item.get("vod_play_from", "")
        play_url = item.get("vod_play_url", "")
        if not play_from:
            play_from = "默认线路"
        if not play_url:
            play_url = ""
        return {
            "vod_id": str(item.get("vod_id", "")),
            "vod_name": item.get("vod_name", ""),
            "vod_pic": item.get("vod_pic", ""),
            "type_name": item.get("type_name", ""),
            "vod_year": item.get("vod_year", ""),
            "vod_area": item.get("vod_area", ""),
            "vod_remarks": item.get("vod_remarks", item.get("vod_serial", "")),
            "vod_actor": item.get("vod_actor", ""),
            "vod_director": item.get("vod_director", ""),
            "vod_content": item.get("vod_content", ""),
            "vod_play_from": play_from,
            "vod_play_url": play_url,
        }

    # ========== m3u8子解析 ==========
    def _resolve_m3u8_child(self, m3u8_url, referer=""):
        text = self._fetch_html(m3u8_url, referer=referer or self.host + "/", timeout=20)
        if not text or "#EXTM3U" not in text:
            return m3u8_url
        lines = [x.strip() for x in text.splitlines() if x.strip()]
        for i, line in enumerate(lines):
            if line.startswith("#EXT-X-STREAM-INF"):
                for nxt in lines[i + 1:]:
                    if nxt and not nxt.startswith("#"):
                        return urljoin(m3u8_url, nxt)
        return m3u8_url

    # ========== 本地代理 ==========
    def localProxy(self, param):
        return [200, "video/MP2T", b"", ""]

    # ========== 清理 ==========
    def destroy(self):
        pass

    def close(self):
        self.destroy()
