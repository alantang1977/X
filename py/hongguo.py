# -*- coding: utf-8 -*-
"""红果短剧 TVBox Python 源"""
import json, re, sys, time, traceback
from urllib.parse import quote, urlencode
import requests

sys.path.append("../../")
try:
    from base.spider import Spider
except ImportError:
    class Spider:
        pass


class Spider(Spider):
    site = "https://hongguoduanju.com"
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 12; TV) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": "https://hongguoduanju.com/",
    }
    cat_qs = [
        "sort_type=1", "sort_type=2",
        "background=cate_1", "background=cate_757", "background=cate_758",
        "background=cate_11", "background=cate_127", "background=cate_4",
        "topic=cate_165", "topic=cate_303",
        "setting=cate_36", "setting=cate_37",
    ]

    def __init__(self):
        self.bridge = "http://127.0.0.1:9979"
        self._cache = {}

    def init(self, extend=""):
        if isinstance(extend, dict):
            self.bridge = str(extend.get("bridge") or self.bridge).rstrip("/")
        elif extend:
            text = str(extend).strip()
            try:
                data = json.loads(text)
                self.bridge = str(data.get("bridge") or self.bridge).rstrip("/")
            except Exception:
                if text.startswith("http"):
                    self.bridge = text.rstrip("/")

    def _get(self, url):
        r = requests.get(url, headers=self.headers, timeout=25)
        r.raise_for_status()
        r.encoding = "utf-8"
        return r.text

    def _extract_json(self, html):
        """Extract _ROUTER_DATA JSON using {} counting balance"""
        # 站点改版后标记无 window. 前缀：_ROUTER_DATA = {...}
        marker = "_ROUTER_DATA = "
        pos = html.find(marker)
        if pos == -1:
            # 兼容旧版 window._ROUTER_DATA = {...}
            marker = "window._ROUTER_DATA = "
            pos = html.find(marker)
        if pos == -1:
            raise RuntimeError("_ROUTER_DATA not found")
        pos += len(marker)
        while pos < len(html) and html[pos] in (" ", chr(9), chr(10), chr(13)):
            pos += 1
        if pos >= len(html) or html[pos] != "{":
            raise RuntimeError("_ROUTER_DATA not JSON object")
        depth = 1
        i = pos + 1
        in_str = False
        esc = False
        while i < len(html) and depth > 0:
            ch = html[i]
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = not in_str
            elif not in_str:
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
            i += 1
        return json.loads(html[pos:i])

    def _router_data(self, url):
        now = time.time()
        cached = self._cache.get(url)
        if cached and now - cached[0] < 300:
            return cached[1]
        html = self._get(url)
        data = self._extract_json(html)
        self._cache[url] = (now, data)
        return data

    @staticmethod
    def _vod(item):
        tags = " ".join(str(x) for x in (item.get("tags") or [])[:3])
        cnt = item.get("episode_cnt") or len(item.get("vid_list") or [])
        remark = ("全%s集" % cnt) if cnt else tags
        return {
            "vod_id": str(item.get("series_id") or ""),
            "vod_name": str(item.get("series_name") or ""),
            "vod_pic": str(item.get("series_cover") or ""),
            "vod_remarks": remark,
        }

    def _cat_items(self, qs):
        data = self._router_data(self.site + "/category?" + qs)
        page = data.get("loaderData", {}).get("category_page", {})
        items = page.get("recommendList") or page.get("categoryData", {}).get("recommendList") or []
        seen, out = set(), []
        for it in items:
            sid = str(it.get("series_id") or "")
            if sid and sid not in seen:
                seen.add(sid)
                out.append(it)
        return out

    def homeContent(self, filter_):
        names = ["热门", "最新", "都市", "现代",
                 "古代", "乡村", "职场", "校园",
                 "悬疑", "喜剧", "重生", "穿越"]
        return {
            "class": [{"type_name": n, "type_id": q} for n, q in zip(names, self.cat_qs)],
            "list": self.homeVideoContent().get("list", []),
        }

    def homeVideoContent(self):
        try:
            return {"list": [self._vod(x) for x in self._cat_items("sort_type=1")[:30]]}
        except Exception:
            traceback.print_exc()
            return {"list": []}

    def categoryContent(self, tid, pg, *a):
        page = max(1, int(pg or 1))
        try:
            items = self._cat_items(str(tid))
            n = len(items)
            start = (page - 1) * 30
            return {"list": [self._vod(x) for x in items[start:start + 30]],
                    "page": page, "pagecount": max(1, (n + 29) // 30), "limit": 30, "total": n}
        except Exception:
            traceback.print_exc()
            return {"list": [], "page": page, "pagecount": page}

    def detailContent(self, ids):
        sid = str(ids[0])
        try:
            data = self._router_data(self.site + "/detail?series_id=" + quote(sid))
            s = data.get("loaderData", {}).get("detail_page", {}).get("seriesDetail") or {}
            vids = [v for v in (s.get("vid_list") or []) if str(v)]
            eps = ["第%d集$%s" % (i + 1, v) for i, v in enumerate(vids)]
            return {"list": [{
                "vod_id": sid,
                "vod_name": str(s.get("series_name") or ""),
                "vod_pic": str(s.get("series_cover") or ""),
                "type_name": ",".join(str(x) for x in (s.get("tags") or [])),
                "vod_remarks": "全%s集" % (s.get("episode_cnt") or len(vids)),
                "vod_content": str(s.get("series_intro") or ""),
                "vod_play_from": "红果",
                "vod_play_url": "#".join(eps),
            }]}
        except Exception:
            traceback.print_exc()
            return {"list": []}

    def searchContent(self, key, *a):
        try:
            all_items, seen = [], set()
            for qs in self.cat_qs:
                for it in self._cat_items(qs):
                    sid = str(it.get("series_id") or "")
                    if sid and sid not in seen:
                        seen.add(sid)
                        all_items.append(it)
            kw = str(key).strip().lower()
            hits = [x for x in all_items
                    if kw in str(x.get("series_name") or "").lower()
                    or kw in str(x.get("series_intro") or "").lower()]
            return {"list": [self._vod(x) for x in hits[:30]], "page": 1}
        except Exception:
            traceback.print_exc()
            return {"list": [], "page": 1}

    def searchContentPage(self, key, quick, pg=1):
        return self.searchContent(key, quick, pg)

    def playerContent(self, flag, pid, *a):
        return {"parse": 0, "playUrl": "",
                "url": self.bridge + "/play?" + urlencode({"vid": str(pid)}),
                "header": {"User-Agent": self.headers["User-Agent"], "Referer": self.site + "/"}}

    def localProxy(self, params):
        return None

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def destroy(self):
        return

    def getName(self):
        return "红果短剧"