# coding=utf-8
import re
import json
import base64
import hashlib
import urllib.parse
from base.spider import Spider as BaseSpider

class Spider(BaseSpider):
    def getName(self):
        return "农民影视"

    def init(self, extend=""):
        self.host = "https://www.nmdvd.top"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Referer": self.host,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

    def homeContent(self, filter):
        return {
            "class": [
                {"type_id": "dianying", "type_name": "电影"}, {"type_id": "juji", "type_name": "剧集"},
                {"type_id": "dongman", "type_name": "动漫"}, {"type_id": "zongyi", "type_name": "综艺"},
                {"type_id": "duanju", "type_name": "短剧"}
            ]
        }

    def homeVideoContent(self):
        try:
            return {"list": self._parse_list(self.fetch(self.host, headers=self.headers).text)[:24]}
        except:
            return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            url = f"{self.host}/type/{tid}.html" if str(pg) == "1" else f"{self.host}/type/{tid}/page/{pg}.html"
            return {"page": int(pg), "pagecount": 999, "limit": 90, "total": 9999, "list": self._parse_list(self.fetch(url, headers=self.headers).text)}
        except:
            return {"list": []}

    def detailContent(self, array):
        try:
            url = self._fix_url(array[0])
            html = self.fetch(url, headers=self.headers).text

            vod = {
                "vod_id": url,
                "vod_name": self._match_text(html, [r'<h[13][^>]*class="[^"]*title[^"]*"[^>]*>(.*?)</h[13]>', r'<title>(.*?)</title>']).replace("_农民影视", "").replace("-农民影视", "").strip(),
                "vod_pic": self._fix_url(self._match_text(html, [r'<img[^>]+(?:data-original|src)="([^"]+)"'])),
                "vod_content": self.cleanText(self._match_text(html, [r'<span[^>]*class="[^"]*detail-sketch[^"]*"[^>]*>([\s\S]*?)</span>', r'<div[^>]*class="[^"]*detail-content[^"]*"[^>]*>([\s\S]*?)</div>']))
            }

            play_from, play_url = [], []
            for tab_id, tab_name in re.findall(r'<a[^>]+href=["\']#playlist(\d+)["\'][^>]*>(.*?)</a>', html, re.I | re.S):
                block = self._match_text(html, [rf'<div[^>]+id=["\']playlist{tab_id}["\'][^>]*>([\s\S]*?)</(?:ul|div)>'])
                if block:
                    arr = [f"{self.cleanText(name)}${self._fix_url(link)}" for link, name in re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', block, re.I | re.S) if link]
                    if arr:
                        play_from.append(self.cleanText(tab_name))
                        play_url.append("#".join(arr))

            vod["vod_play_from"] = "$$$".join(play_from)
            vod["vod_play_url"] = "$$$".join(play_url)
            return {"list": [vod]}
        except:
            return {"list": []}

    # ========================== 核心修复：搜索模块 ==========================
    def searchContent(self, key, quick, pg="1"):
        try:
            import requests
            
            # 第一页必须用 POST 激活缓存，否则直接返回 404；后续翻页再使用网站提供的 GET 链接
            if str(pg) == "1":
                url = f"{self.host}/vodsearch.html"
                rsp = requests.post(url, data={"wd": key, "submit": ""}, headers=self.headers, timeout=8, verify=False)
            else:
                url = f"{self.host}/vodsearch{urllib.parse.quote(key)}/page/{pg}.html"
                rsp = requests.get(url, headers=self.headers, timeout=8, verify=False)
                
            rsp.encoding = "utf-8"
            html = rsp.text
            items = []
            
            # 兼容 HTML 属性乱序，认准 v-thumb 过滤掉侧边栏 m-thumb 热播推荐
            for match in re.findall(r'<a([^>]*)>([\s\S]*?)</a>', html, re.I):
                a_attrs, inner = match
                if 'v-thumb' not in a_attrs:
                    continue
                    
                link = self._match_text(a_attrs, [r'href="([^"]+)"'])
                title = self._match_text(a_attrs, [r'title="([^"]+)"'])
                pic = self._match_text(a_attrs, [r'(?:data-original|src)="([^"]+)"'])
                
                if link and title:
                    remark = self.cleanText(self._match_text(inner, [r'<span[^>]*pic-text[^>]*>([\s\S]*?)</span>']))
                    items.append({
                        "vod_id": self._fix_url(link),
                        "vod_name": self.cleanText(title),
                        "vod_pic": self._fix_url(pic),
                        "vod_remarks": remark
                    })
            return {"list": items}
        except Exception as e:
            # 【电视端调试神器】如果报错，直接在电视搜索结果里弹射显示具体报错信息
            return {"list": [{"vod_id": "", "vod_name": f"搜索遭遇异常: {str(e)}", "vod_pic": "", "vod_remarks": "请联系维护"}]}
    # ====================================================================

    def playerContent(self, flag, id, vipFlags):
        try:
            page_url = self._fix_url(id)
            rsp = self.fetch(page_url, headers=self.headers)
            html, cookie = rsp.text, self._build_cookie(rsp)

            original_vid, encrypt = self._extract_player_data(html)

            # 1. 页面直接带流
            for u in self._extract_urls(html):
                if self.is_valid_video(u): return self._play(u)

            if not original_vid:
                return {"parse": 1, "playUrl": "", "url": page_url, "header": self.headers}

            # 2. 前端直连解密 (非自建解析线路)
            if not any(k in str(flag).lower() for k in ['zl', 'yd', '1080zyk', 'yynb', 'ace', '自建', 'yz']):
                for u in self._get_candidates(original_vid, encrypt):
                    if self.is_valid_video(u): return self._play(u)

            # 3. 后端解析核心处理
            jx_url = f"{self.host}/jx/player.php?vid={urllib.parse.quote(original_vid, safe='')}"

            # 3.1 尝试后端 api.php
            api_headers = {**self.headers, "Referer": page_url, "X-Requested-With": "XMLHttpRequest", "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "Cookie": cookie}
            for _ in range(2):
                data = self._post_api(f"{self.host}/jx/api.php", original_vid, api_headers)
                if data and str(data.get("code")) == "200":
                    info = data.get("data", {})
                    cipher = info.get("url") or info.get("vid") or ""
                    for u in self._get_candidates(cipher, int(str(info.get("urlmode", "0")) or 0)):
                        if self.is_valid_video(u): return self._play(u)

            # 3.2 jx/player.php 页面爬取嗅探
            for _ in range(2):
                u = self._sniff_jx(jx_url, page_url, cookie)
                if self.is_valid_video(u): return self._play(u)

            # 4. WebView 嗅探兜底
            return {"parse": 1, "playUrl": "", "url": jx_url, "header": {"User-Agent": self.headers["User-Agent"], "Referer": page_url}}

        except:
            return {"parse": 1, "playUrl": "", "url": id, "header": self.headers}

    # ========================== 核心辅助解密逻辑 ==========================
    
    def _get_candidates(self, cipher, mode):
        c = []
        if mode in (1, 0): c.append(self.decode1(cipher))
        if mode in (2, 0): c.append(self.decode2(cipher))
        c.extend([cipher, urllib.parse.unquote(cipher)])
        return [self._fix_url(u) for u in c if u and isinstance(u, str)]

    def fix_b64(self, s):
        s = re.sub(r"[^A-Za-z0-9+/=]", "", str(s).strip())
        return s + "=" * (-len(s) % 4)

    def decode1(self, cipher):
        try:
            raw = base64.b64decode(self.fix_b64(cipher))
            key = hashlib.md5(b"#tips").hexdigest().encode("utf-8")
            s2 = bytearray(raw[i] ^ key[i % len(key)] for i in range(len(raw)))
            s2_str = self.fix_b64(s2.decode("utf-8", errors="ignore"))
            return urllib.parse.unquote(base64.b64decode(s2_str).decode("utf-8", errors="ignore"))
        except: 
            return ""

    def decode2(self, cipher):
        try:
            raw = base64.b64decode(self.fix_b64(cipher)).decode("utf-8", errors="ignore")
            m_map = "PXhw7UT1B0a9kQDKZsjIASmOezxYG4CHo5Jyfg2b8FLpEvRr3WtVnlqMidu6cN"
            return urllib.parse.unquote("".join(m_map[(m_map.find(c) + 59) % 62] if m_map.find(c) != -1 else c for c in raw[1::3]).strip())
        except: 
            return ""

    # ========================== 嗅探及抓取模块 ==========================

    def _post_api(self, api_url, vid, headers):
        try:
            import requests
            return requests.post(api_url, data={"vid": vid}, headers=headers, timeout=8, verify=False).json()
        except: return None

    def _sniff_jx(self, jx_url, referer, cookie=""):
        try:
            headers = {**self.headers, "Referer": referer, "Cookie": cookie}
            html = self.fetch(jx_url, headers=headers).text
            for u in self._extract_urls(html):
                if self.is_valid_video(u): return u

            if iframe := self._match_text(html, [r'<iframe[^>]+src=[\'"]([^\'"]+)[\'"]']):
                html2 = self.fetch(self._fix_url(iframe), headers={**self.headers, "Referer": jx_url, "Cookie": cookie}).text
                for u in self._extract_urls(html2):
                    if self.is_valid_video(u): return u
        except: pass
        return ""

    def _extract_urls(self, text):
        return [self._fix_url(u) for u in re.findall(
            r'(https?://[^\s\'"]+?\.(?:m3u8|mp4|flv)(?:\?[^\'"<> ]*)?|https?://[^\s\'"]*get[mM]3u8[^\s\'"]*|[\'"]url[\'"]\s*:\s*[\'"]([^\'"]+)[\'"]|<source[^>]+src=[\'"]([^\'"]+)[\'"])', 
            text, re.I | re.S
        ) if u and isinstance(u, str)]

    def _extract_player_data(self, html):
        block = self._match_text(html, [r'player_aaaa\s*=\s*(\{[\s\S]*?\})\s*[;<]'])
        url, enc = "", 0
        try:
            data = json.loads(block)
            url, enc = str(data.get("url", "")), int(data.get("encrypt", 0) or 0)
        except:
            url = self._match_text(block, [r'[\'"]url[\'"]\s*:\s*[\'"]([^\'"]+)[\'"]'])
            enc = int(self._match_text(block, [r'[\'"]encrypt[\'"]\s*:\s*(\d+)']) or 0)
        
        return url.replace('\\/', '/').strip(), enc

    def _parse_list(self, html):
        items = []
        for block in re.findall(r'<div[^>]*class="[^"]*stui-vodlist__box[^"]*"[^>]*>([\s\S]*?)</div>\s*</div>', html, re.I):
            a = re.search(r'<a[^>]*href="([^"]+)"[^>]*title="([^"]+)"', block, re.I | re.S)
            if a:
                items.append({
                    "vod_id": self._fix_url(a.group(1)),
                    "vod_name": self.cleanText(a.group(2)),
                    "vod_pic": self._fix_url(self._match_text(block, [r'(?:data-original|src)="([^"]+)"'])),
                    "vod_remarks": self.cleanText(self._match_text(block, [r'<span[^>]*class="[^"]*pic-text[^"]*"[^>]*>(.*?)</span>']))
                })
        return items

    # ========================== 工具方法 ==========================

    def is_valid_video(self, url):
        if not url: return False
        u = str(url).strip().lower()
        if not u.startswith("http"): return False
        valid_keys = [".m3u8", ".mp4", ".flv", "getm3u8", "playm3u8", "mime=video", "type=m3u8", "byteimg.com", ".image"]
        return any(k in u for k in valid_keys)

    def _build_cookie(self, rsp):
        arr = ["tips=true"]
        if hasattr(rsp, "cookies"): arr.extend(f"{k}={v}" for k, v in rsp.cookies.items())
        return "; ".join(arr)

    def _play(self, url):
        url = str(url).strip()
        header = {"User-Agent": self.headers["User-Agent"]}
        
        if "byteimg.com" in url or ".image" in url:
            if "?" in url:
                base, query = url.split("?", 1)
                new_params = []
                for p in query.split("&"):
                    if "=" in p:
                        k, v = p.split("=", 1)
                        v = v.replace('+', '%2B').replace('=', '%3D')
                        new_params.append(f"{k}={v}")
                    else:
                        new_params.append(p)
                url = base + "?" + "&".join(new_params)
            
            header["User-Agent"] = "Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1"
            
            if "#" not in url:
                url += "#.mp4"
        else:
            header["Referer"] = self.host
            
        return {"parse": 0, "playUrl": "", "url": url, "header": header}

    def _match_text(self, text, patterns):
        for p in patterns:
            if m := re.search(p, text, re.I | re.S):
                return (m.group(1) if len(m.groups()) > 0 else m.group(0)).strip()
        return ""

    def _fix_url(self, url):
        if isinstance(url, tuple): url = next((x for x in url if x), "") 
        url = str(url).strip()
        if not url: return ""
        if url.startswith("//"): return "https:" + url
        return url if url.startswith("http") else f"{self.host}{url if url.startswith('/') else '/' + url}"

    def cleanText(self, text):
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", re.sub(r"<br\s*/?>|</p>|</div>|</li>", " ", str(text or ""), flags=re.I))).replace("&nbsp;", " ").replace("\u3000", " ").strip()
