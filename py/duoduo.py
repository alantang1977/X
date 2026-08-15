# -*- coding: utf-8 -*-
# 多多视频 - duoduosdf12223234334.top
# by TRAE
# Vue SPA + 苹果CMS API + 解析播放
import re
import sys
import json
import time
import os
import hashlib
import urllib.request
import urllib.parse
import ssl
from urllib.parse import quote

sys.path.append('..')
from base.spider import Spider


class Spider(Spider):

    def getName(self):
        return "多多视频"

    def init(self, extend=""):
        self.host = "https://duoduosdf12223234334.top"
        self.api = f"{self.host}/api.php/web"
        self.ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        self.web_sign = "ddtvf65f3a83d6d9ad6f"
        self.x_client = "8f3d2a1c7b6e5d4c9a0b1f2e3d4c5b6a"
        # type_id -> type_name 映射 (API的type_id参数无效, 必须用type_name)
        self._type_map = {"1": "电影", "2": "剧集", "3": "动漫", "4": "综艺"}
        self._ssl_ctx = ssl.create_default_context()
        self._ssl_ctx.check_hostname = False
        self._ssl_ctx.verify_mode = ssl.CERT_NONE

    def getDependence(self):
        return []

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def action(self, action):
        pass

    def destroy(self):
        pass

    # ---- decode/url 签名 (逆向自 web_app_wasm) ----
    DEV = "com.web.player"
    ID = "WF-2c064bc5b3400788f31b848849bc3a60f835423ba2dfe69d7ea93974c216e4f2"
    SK = "WEB-50a8e9c84a1dc05669a692ded99a2dac46527229e607a7be15db88dbc59059d1"

    def _proto_varint(self, n):
        out = bytearray()
        while True:
            x = n & 0x7f
            n >>= 7
            if n:
                out.append(x | 0x80)
            else:
                out.append(x)
                break
        return bytes(out)

    def _proto_bytes(self, field, data):
        return self._proto_varint((field << 3) | 2) + self._proto_varint(len(data)) + data

    def _proto_varint_field(self, field, value):
        return self._proto_varint(field << 3) + self._proto_varint(value)

    def _build_decode_request(self, token, play_from, ts_ms, nonce_hex):
        sign = hashlib.sha256(
            ("finger=%s&id=%s&nonce=%s&sk=%s&time=%d&v=1" % (self.ID, self.DEV, nonce_hex, self.SK, ts_ms)).encode()
        ).hexdigest().upper()
        req = b""
        req += self._proto_bytes(1, token.encode())
        req += self._proto_bytes(2, play_from.encode())
        req += self._proto_varint_field(3, ts_ms)
        req += self._proto_bytes(4, nonce_hex.encode())
        req += self._proto_bytes(5, sign.encode())
        req += self._proto_bytes(6, self.DEV.encode())
        req += self._proto_varint_field(7, 1)
        return req

    def _parse_decode_response(self, data):
        result = {}
        i = 0
        n = len(data)
        while i < n:
            key = 0
            shift = 0
            while True:
                b = data[i]; i += 1
                key |= (b & 0x7f) << shift
                shift += 7
                if not (b & 0x80):
                    break
            field = key >> 3
            wire = key & 7
            if wire == 0:
                val = 0
                shift = 0
                while True:
                    b = data[i]; i += 1
                    val |= (b & 0x7f) << shift
                    shift += 7
                    if not (b & 0x80):
                        break
                result[field] = val
            elif wire == 2:
                ln = 0
                shift = 0
                while True:
                    b = data[i]; i += 1
                    ln |= (b & 0x7f) << shift
                    shift += 7
                    if not (b & 0x80):
                        break
                result[field] = data[i:i+ln]
                i += ln
            elif wire == 1:
                result[field] = data[i:i+8]; i += 8
            elif wire == 5:
                result[field] = data[i:i+4]; i += 4
            else:
                break
        return result

    def _decode_url(self, token, play_from):
        """调用 decode/url 接口, 返回真实可播放地址; 失败返回空串"""
        for attempt in range(3):
            try:
                ts_ms = int(time.time() * 1000)
                nonce_hex = os.urandom(16).hex()
                body = self._build_decode_request(token, play_from, ts_ms, nonce_hex)
                req = urllib.request.Request(f"{self.api}/decode/url", data=body, method='POST')
                req.add_header("Content-Type", "application/x-protobuf")
                req.add_header("Accept", "application/x-protobuf")
                req.add_header("User-Agent", self.ua)
                req.add_header("X-Client", self.x_client)
                req.add_header("web-sign", self.web_sign)
                resp = urllib.request.urlopen(req, timeout=20, context=self._ssl_ctx)
                fields = self._parse_decode_response(resp.read())
                url = fields.get(3)
                if url and url.startswith(b"http"):
                    return url.decode('utf-8', errors='replace')
                time.sleep(0.5)
            except Exception as e:
                print(f'decode_url error: {e}')
                time.sleep(0.5)
        return ""

    def fetch_html(self, url):
        """发送带签名头的HTTP请求"""
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", self.ua)
            req.add_header("Accept", "application/json")
            req.add_header("X-Client", self.x_client)
            req.add_header("web-sign", self.web_sign)
            resp = urllib.request.urlopen(req, timeout=15, context=self._ssl_ctx)
            return resp.read().decode('utf-8', errors='replace')
        except Exception as e:
            print(f'fetch_html error: {e}')
            return ""

    def homeContent(self, filter):
        result = {"class": [], "filters": {}, "list": []}
        try:
            html = self.fetch_html(self.api + "/index/home")
            if html:
                data = json.loads(html)
                if data.get("code") == 200 and data.get("data"):
                    home = data["data"]
                    categories = home.get("categories", [])
                    for cat in categories:
                        type_name = cat.get("type_name", "")
                        type_id = str(cat.get("type_id", ""))
                        result["class"].append({
                            "type_name": type_name,
                            "type_id": type_id,
                        })
                    result["filters"] = self._build_filters()
                    seen = set()
                    for cat in categories:
                        videos = cat.get("videos", [])
                        for v in videos:
                            vid = str(v.get("vod_id", ""))
                            if vid and vid not in seen:
                                seen.add(vid)
                                result["list"].append({
                                    "vod_id": vid,
                                    "vod_name": v.get("vod_name", ""),
                                    "vod_pic": v.get("vod_pic", ""),
                                    "vod_remarks": v.get("vod_remarks", ""),
                                })
                    for rec in home.get("recommend", []):
                        vid = str(rec.get("vod_id", ""))
                        if vid and vid not in seen:
                            seen.add(vid)
                            result["list"].append({
                                "vod_id": vid,
                                "vod_name": rec.get("vod_name", ""),
                                "vod_pic": rec.get("vod_pic", ""),
                                "vod_remarks": rec.get("vod_remarks", ""),
                            })
        except Exception as e:
            print(f'homeContent error: {e}')
        return result

    def homeVideoContent(self):
        return self.homeContent(False)

    def _build_filters(self):
        years = [{"n": "全部", "v": ""}]
        for y in range(2026, 2015, -1):
            years.append({"n": str(y), "v": str(y)})

        areas = [
            {"n": "全部", "v": ""},
            {"n": "大陆", "v": "大陆"}, {"n": "港台", "v": "港台"},
            {"n": "美国", "v": "美国"}, {"n": "日本", "v": "日本"},
            {"n": "韩国", "v": "韩国"}, {"n": "泰国", "v": "泰国"},
            {"n": "其他", "v": "其他"},
        ]

        sorts = [
            {"n": "时间", "v": "time"},
            {"n": "人气", "v": "hits"},
            {"n": "评分", "v": "score"},
        ]

        movie_class = [
            {"n": "全部", "v": ""},
            {"n": "动作", "v": "动作"}, {"n": "喜剧", "v": "喜剧"},
            {"n": "爱情", "v": "爱情"}, {"n": "科幻", "v": "科幻"},
            {"n": "恐怖", "v": "恐怖"}, {"n": "剧情", "v": "剧情"},
            {"n": "战争", "v": "战争"}, {"n": "犯罪", "v": "犯罪"},
            {"n": "奇幻", "v": "奇幻"}, {"n": "冒险", "v": "冒险"},
            {"n": "悬疑", "v": "悬疑"}, {"n": "动画", "v": "动画"},
        ]

        tv_class = [
            {"n": "全部", "v": ""},
            {"n": "剧情", "v": "剧情"}, {"n": "喜剧", "v": "喜剧"},
            {"n": "爱情", "v": "爱情"}, {"n": "科幻", "v": "科幻"},
            {"n": "悬疑", "v": "悬疑"}, {"n": "恐怖", "v": "恐怖"},
            {"n": "古装", "v": "古装"}, {"n": "都市", "v": "都市"},
            {"n": "家庭", "v": "家庭"}, {"n": "战争", "v": "战争"},
            {"n": "犯罪", "v": "犯罪"}, {"n": "历史", "v": "历史"},
        ]

        anime_class = [
            {"n": "全部", "v": ""},
            {"n": "国产动漫", "v": "国产动漫"}, {"n": "日本动漫", "v": "日本动漫"},
            {"n": "欧美动漫", "v": "欧美动漫"}, {"n": "海外动漫", "v": "海外动漫"},
        ]

        variety_filters = [
            {"key": "area", "name": "地区", "value": areas},
            {"key": "sort", "name": "排序", "value": sorts},
            {"key": "year", "name": "年份", "value": years},
        ]

        return {
            "1": [
                {"key": "class", "name": "类型", "value": movie_class},
                {"key": "area", "name": "地区", "value": areas},
                {"key": "sort", "name": "排序", "value": sorts},
                {"key": "year", "name": "年份", "value": years},
            ],
            "2": [
                {"key": "class", "name": "类型", "value": tv_class},
                {"key": "area", "name": "地区", "value": areas},
                {"key": "sort", "name": "排序", "value": sorts},
                {"key": "year", "name": "年份", "value": years},
            ],
            "3": [
                {"key": "class", "name": "类型", "value": anime_class},
                {"key": "sort", "name": "排序", "value": sorts},
                {"key": "year", "name": "年份", "value": years},
            ],
            "4": variety_filters,
        }

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg else 1
        result = {"list": [], "page": page, "pagecount": 1, "limit": 24, "total": 0}
        try:
            # API的type_id参数无效, 必须用type_name
            type_name = self._type_map.get(str(tid), str(tid))
            url = f"{self.api}/filter/vod?type_name={quote(type_name)}&page={page}&sort=hits"
            extend = extend or {}
            area = extend.get("area", "")
            if area and area != "全部":
                url += f"&area={quote(area)}"
            cls = extend.get("class", "")
            if cls and cls != "全部":
                url += f"&class={quote(cls)}"
            year = extend.get("year", "")
            if year and year != "全部":
                url += f"&year={year}"
            sort = extend.get("sort", "") or "hits"
            url += f"&sort={quote(sort)}"

            html = self.fetch_html(url)
            if html:
                data = json.loads(html)
                if data.get("code") == 200 and isinstance(data.get("data"), list):
                    items = data["data"]
                    for v in items:
                        result["list"].append({
                            "vod_id": str(v.get("vod_id", "")),
                            "vod_name": v.get("vod_name", ""),
                            "vod_pic": v.get("vod_pic", ""),
                            "vod_remarks": v.get("vod_remarks", ""),
                        })
                    # 该API不返回真实total/pageCount, 按页满估算翻页
                    limit = data.get("limit", 24) or 24
                    result["limit"] = limit
                    result["total"] = len(items)
                    if items and len(items) >= limit:
                        result["pagecount"] = page + 1
                    else:
                        result["pagecount"] = page
        except Exception as e:
            print(f'categoryContent error: {e}')
        return result

    def detailContent(self, ids):
        result = {"list": []}
        try:
            vod_id = ids[0]
            html = self.fetch_html(f"{self.api}/vod/get_detail?vod_id={vod_id}")
            if html:
                data = json.loads(html)
                if data.get("code") == 200 and data.get("data"):
                    vod_list = data["data"]
                    vod = vod_list[0] if isinstance(vod_list, list) else vod_list

                    vod_play_from = vod.get("vod_play_from", "")
                    vod_play_url = vod.get("vod_play_url", "")

                    # 按 from 代码匹配显示名 (vodplayer与播放线路不一定对齐)
                    show_map = {}
                    for p in (data.get("vodplayer") or []):
                        src = p.get("from", "")
                        if src:
                            show_map[src] = p.get("show", "") or src

                    from_list = vod_play_from.split("$$$") if vod_play_from else []
                    url_list = vod_play_url.split("$$$") if vod_play_url else []

                    play_from = []
                    play_url = []
                    vod_id_str = str(vod.get("vod_id", ""))

                    for i, line_name in enumerate(from_list):
                        display_name = show_map.get(line_name, line_name)
                        if i < len(url_list) and url_list[i]:
                            eps = url_list[i].split("#")
                            urls = []
                            for idx, ep in enumerate(eps, start=1):
                                parts = ep.split("$")
                                if len(parts) == 2:
                                    pid_value = f"{vod_id_str}_{i}_{idx}"
                                    urls.append(f"{parts[0]}${pid_value}")
                            if urls:
                                play_from.append(display_name)
                                play_url.append("#".join(urls))

                    content = vod.get("vod_content", "")
                    vod_content = re.sub(r'<[^>]+>', '', content).strip()

                    result["list"] = [{
                        "vod_id": str(vod.get("vod_id", "")),
                        "vod_name": vod.get("vod_name", ""),
                        "vod_pic": vod.get("vod_pic", ""),
                        "vod_director": vod.get("vod_director", ""),
                        "vod_actor": vod.get("vod_actor", ""),
                        "vod_year": str(vod.get("vod_year", "")),
                        "vod_area": vod.get("vod_area", ""),
                        "vod_content": vod_content,
                        "vod_remarks": vod.get("vod_remarks", ""),
                        "vod_play_from": "$$$".join(play_from),
                        "vod_play_url": "$$$".join(play_url),
                    }]
        except Exception as e:
            print(f'detailContent error: {e}')
        return result

    def searchContent(self, key, quick, pg="1"):
        result = {"list": [], "page": int(pg) if pg else 1}
        try:
            wd = quote(key)
            url = f"{self.api}/search/index?wd={wd}&page={pg}"
            html = self.fetch_html(url)
            if html:
                data = json.loads(html)
                if data.get("code") == 200 and isinstance(data.get("data"), list):
                    for v in data["data"]:
                        result["list"].append({
                            "vod_id": str(v.get("vod_id", "")),
                            "vod_name": v.get("vod_name", ""),
                            "vod_pic": v.get("vod_pic", ""),
                            "vod_remarks": v.get("vod_remarks", ""),
                        })
        except Exception as e:
            print(f'searchContent error: {e}')
        return result

    def _ref_host(self, url):
        """从播放链接中提取 scheme://host 作为 Referer"""
        try:
            pr = urllib.parse.urlparse(url)
            if pr.scheme and pr.netloc:
                return f"{pr.scheme}://{pr.netloc}"
        except Exception:
            pass
        return self.host

    def playerContent(self, flag, pid, vipFlags):
        result = {}
        try:
            # pid格式: vod_id_线路序号_集数序号
            parts = pid.split("_")
            vod_id = parts[0]
            src_idx = int(parts[1]) if len(parts) > 1 else 0
            ep_idx = int(parts[2]) if len(parts) > 2 else 1
            src_code = ""

            html = self.fetch_html(f"{self.api}/vod/get_detail?vod_id={vod_id}")
            if html:
                data = json.loads(html)
                if data.get("code") == 200 and data.get("data"):
                    vod_list = data["data"]
                    vod = vod_list[0] if isinstance(vod_list, list) else vod_list
                    froms = (vod.get("vod_play_from") or "").split("$$$")
                    urls = (vod.get("vod_play_url") or "").split("$$$")
                    if src_idx < len(froms):
                        src_code = froms[src_idx]
                    if src_idx < len(urls):
                        eps = urls[src_idx].split("#")
                        if ep_idx <= len(eps):
                            ep_parts = eps[ep_idx - 1].split("$")
                            if len(ep_parts) == 2:
                                token = ep_parts[1]
                                real = self._decode_url(token, src_code)
                                if real:
                                    result["parse"] = 0
                                    result["url"] = real
                                    result["header"] = {
                                        "User-Agent": self.ua,
                                        "Referer": self._ref_host(real),
                                    }
                                    return result

            # 回退: 用网站播放页
            result["parse"] = 1
            url = f"{self.host}/play/{vod_id}?ep={ep_idx}"
            if src_code:
                url += f"&source={quote(src_code)}"
            result["url"] = url
            result["header"] = {"User-Agent": self.ua, "Referer": self.host}
        except Exception as e:
            print(f'playerContent error: {e}')
            result["parse"] = 0
            result["url"] = ""
        return result

    def localProxy(self, params):
        return None
