# -*- coding: utf-8 -*-
# 云朵影视 - y23xxa23duo12.xyz
# by TRAE
# Vue SPA + 苹果CMS API + 解析播放 (需登录Cookie)
import re
import sys
import json
import urllib.request
import urllib.parse
import ssl
from urllib.parse import quote

sys.path.append('..')
from base.spider import Spider


class Spider(Spider):

    def getName(self):
        return "云朵影视"

    def init(self, extend=""):
        self.host = "https://y23xxa23duo12.xyz"
        self.api = f"{self.host}/api.php/web"
        self.ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        self.web_sign = "yda81x6d9ad3c4s"
        self.x_client = "8f3d2a1c7b6e5d4c9a0b1f2e3d4c5b6a"
        # 登录账号
        self.username = "lcgz"
        self.password = "xi320421"
        # Session cookie缓存
        self._session_cookie = None
        # SSL
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

    def _get_cookie(self):
        """登录获取session cookie"""
        if self._session_cookie:
            return self._session_cookie
        try:
            login_url = f"{self.api}/account/login"
            body = json.dumps({"username": self.username, "password": self.password}).encode('utf-8')
            req = urllib.request.Request(login_url, data=body, method='POST')
            req.add_header("Content-Type", "application/json")
            req.add_header("Accept", "application/json")
            req.add_header("X-Client", self.x_client)
            req.add_header("web-sign", self.web_sign)
            req.add_header("User-Agent", self.ua)
            resp = urllib.request.urlopen(req, timeout=15, context=self._ssl_ctx)
            # 提取Set-Cookie
            cookie_header = resp.headers.get("Set-Cookie", "")
            if cookie_header:
                # 解析 cookie值
                for part in cookie_header.split(';'):
                    part = part.strip()
                    if '=' in part and 'yunduo_web_session' in part:
                        self._session_cookie = part
                        break
            if not self._session_cookie:
                # 尝试从headers列表中获取
                for h in resp.headers.get_all("Set-Cookie") or []:
                    if 'yunduo_web_session' in h:
                        val = h.split(';')[0]
                        self._session_cookie = val
                        break
        except Exception as e:
            print(f'login error: {e}')
        return self._session_cookie or ""

    def fetch_html(self, url):
        """发送带认证的HTTP请求"""
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", self.ua)
            req.add_header("Accept", "application/json")
            req.add_header("X-Client", self.x_client)
            req.add_header("web-sign", self.web_sign)
            cookie = self._get_cookie()
            if cookie:
                req.add_header("Cookie", cookie)
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
                        result["class"].append({
                            "type_name": type_name,
                            "type_id": type_name,
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
        pass

    def _build_filters(self):
        years = [{"n": "全部", "v": ""}]
        for y in range(2026, 2005, -1):
            years.append({"n": str(y), "v": str(y)})

        areas = [
            {"n": "全部", "v": ""},
            {"n": "中国大陆", "v": "中国大陆"}, {"n": "中国香港", "v": "中国香港"},
            {"n": "中国台湾", "v": "中国台湾"}, {"n": "美国", "v": "美国"},
            {"n": "日本", "v": "日本"}, {"n": "韩国", "v": "韩国"},
            {"n": "泰国", "v": "泰国"}, {"n": "英国", "v": "英国"},
            {"n": "法国", "v": "法国"}, {"n": "印度", "v": "印度"},
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
            {"n": "古装", "v": "古装"}, {"n": "武侠", "v": "武侠"},
            {"n": "历史", "v": "历史"}, {"n": "家庭", "v": "家庭"},
            {"n": "惊悚", "v": "惊悚"},
        ]

        tv_class = [
            {"n": "全部", "v": ""},
            {"n": "剧情", "v": "剧情"}, {"n": "喜剧", "v": "喜剧"},
            {"n": "爱情", "v": "爱情"}, {"n": "科幻", "v": "科幻"},
            {"n": "悬疑", "v": "悬疑"}, {"n": "恐怖", "v": "恐怖"},
            {"n": "古装", "v": "古装"}, {"n": "动作", "v": "动作"},
            {"n": "家庭", "v": "家庭"}, {"n": "战争", "v": "战争"},
            {"n": "犯罪", "v": "犯罪"}, {"n": "历史", "v": "历史"},
            {"n": "冒险", "v": "冒险"}, {"n": "奇幻", "v": "奇幻"},
            {"n": "国产剧", "v": "国产剧"},
        ]

        anime_class = [
            {"n": "全部", "v": ""},
            {"n": "国产动漫", "v": "国产动漫"}, {"n": "日本动漫", "v": "日本动漫"},
            {"n": "欧美动漫", "v": "欧美动漫"}, {"n": "海外动漫", "v": "海外动漫"},
            {"n": "其他", "v": "其他"},
        ]

        variety_filters = [
            {"key": "area", "name": "地区", "value": areas},
            {"key": "sort", "name": "排序", "value": sorts},
            {"key": "year", "name": "年份", "value": years},
        ]

        return {
            "电影": [
                {"key": "class", "name": "类型", "value": movie_class},
                {"key": "area", "name": "地区", "value": areas},
                {"key": "sort", "name": "排序", "value": sorts},
                {"key": "year", "name": "年份", "value": years},
            ],
            "剧集": [
                {"key": "class", "name": "类型", "value": tv_class},
                {"key": "area", "name": "地区", "value": areas},
                {"key": "sort", "name": "排序", "value": sorts},
                {"key": "year", "name": "年份", "value": years},
            ],
            "综艺": variety_filters,
            "动漫": [
                {"key": "class", "name": "类型", "value": anime_class},
                {"key": "sort", "name": "排序", "value": sorts},
                {"key": "year", "name": "年份", "value": years},
            ],
        }

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg else 1
        result = {"list": [], "page": page, "pagecount": 1, "limit": 24, "total": 0}
        try:
            url = f"{self.api}/filter/vod?type_name={quote(tid)}&page={page}&sort=hits"
            if extend:
                area = extend.get("area", "")
                if area and area != "全部":
                    url += f"&area={quote(area)}"
                cls = extend.get("class", "")
                if cls and cls != "全部":
                    url += f"&class={quote(cls)}"
                year = extend.get("year", "")
                if year and year != "全部":
                    url += f"&year={year}"
                sort = extend.get("sort", "")
                if sort:
                    url += f"&sort={sort}"

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
                    # 使用API返回的分页数据
                    api_total = data.get("total", 0)
                    api_pagecount = data.get("pageCount", 0)
                    if api_total and api_total > 0:
                        result["total"] = api_total
                    else:
                        result["total"] = len(items)
                    if api_pagecount and api_pagecount > 0:
                        result["pagecount"] = api_pagecount
                    elif items and len(items) >= 20:
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
            # 使用 detail_v2 获取详情和播放信息
            html = self.fetch_html(f"{self.api}/vod/detail_v2?vod_id={vod_id}")
            if html:
                data = json.loads(html)
                if data.get("code") == 200 and data.get("data"):
                    d = data["data"]
                    detail = d.get("detail", {})
                    playback = d.get("playback", {})
                    sources = playback.get("sources", [])

                    play_from = []
                    play_url = []
                    vod_id_str = str(vod_id)

                    for i, source in enumerate(sources):
                        display_name = source.get("display_name", source.get("from", ""))
                        episodes = source.get("episodes", [])
                        if not episodes:
                            continue
                        urls = []
                        for idx, ep in enumerate(episodes, start=1):
                            title = ep.get("title", str(idx))
                            url = ep.get("url", "")
                            pid_value = f"{vod_id_str}_{idx}_{i}"
                            urls.append(f"{title}${pid_value}")
                        if urls:
                            play_from.append(display_name)
                            play_url.append("#".join(urls))

                    content = detail.get("vod_content", "")
                    vod_content = re.sub(r'<[^>]+>', '', content).strip()

                    result["list"] = [{
                        "vod_id": str(detail.get("vod_id", vod_id)),
                        "vod_name": detail.get("vod_name", ""),
                        "vod_pic": detail.get("vod_pic", ""),
                        "vod_director": detail.get("vod_director", ""),
                        "vod_actor": detail.get("vod_actor", ""),
                        "vod_year": str(detail.get("vod_year", "")),
                        "vod_area": detail.get("vod_area", ""),
                        "vod_content": vod_content,
                        "vod_remarks": detail.get("vod_remarks", ""),
                        "vod_play_from": "$$$".join(play_from),
                        "vod_play_url": "$$$".join(play_url),
                    }]
        except Exception as e:
            print(f'detailContent error: {e}')
        return result

    def searchContent(self, key, quick, pg="1"):
        result = {"list": []}
        try:
            wd = quote(key)
            url = f"{self.api}/search/index?wd={wd}&pg={pg}"
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

    def playerContent(self, flag, pid, vipFlags):
        result = {}
        try:
            # pid格式: vod_id_ep_index_source_index
            parts = pid.split("_")
            vod_id = parts[0]
            ep_idx = int(parts[1]) if len(parts) > 1 else 1
            src_idx = int(parts[2]) if len(parts) > 2 else 0

            # 调用 playback_v2 获取播放信息
            html = self.fetch_html(f"{self.api}/vod/playback_v2?vod_id={vod_id}")
            if html:
                data = json.loads(html)
                if data.get("code") == 200 and data.get("data"):
                    sources = data["data"].get("sources", [])
                    if src_idx < len(sources):
                        source = sources[src_idx]
                        episodes = source.get("episodes", [])
                        if ep_idx <= len(episodes):
                            ep = episodes[ep_idx - 1]
                            play_url = ep.get("url", "")

                            if play_url.startswith("http"):
                                # 直接URL (如优酷), 用parse=1让TVBox嗅探
                                result["parse"] = 1
                                result["url"] = play_url
                            else:
                                # 加密URL, 用网站播放页让TVBox解析
                                result["parse"] = 1
                                result["url"] = f"{self.host}/play/{vod_id}?ep={ep_idx}"

                            result["header"] = {
                                "User-Agent": self.ua,
                                "Referer": self.host,
                                "Cookie": self._get_cookie(),
                            }
                            return result

            # 回退: 用网站播放页
            result["parse"] = 1
            result["url"] = f"{self.host}/play/{vod_id}?ep={ep_idx}"
            result["header"] = {"User-Agent": self.ua, "Referer": self.host}
        except Exception as e:
            print(f'playerContent error: {e}')
            result["parse"] = 0
            result["url"] = ""
        return result

    def localProxy(self, params):
        return self.Mlocal(params)