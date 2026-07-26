# -*- coding: utf-8 -*-
import sys
import re
import json
from urllib.parse import urljoin, quote

sys.path.append('..')
try:
    from base.spider import Spider
except ImportError:
    class Spider:
        def fetch(self, url, headers=None, **kw):
            import requests as rq
            kw.pop('timeout', None)
            r = rq.get(url, headers=headers, timeout=15, **kw)
            r.encoding = 'utf-8'
            return r

HOST = "https://gqc.ink"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

CATEGORIES = {
    "dianying": "电影", "lianxuju": "连续剧", "zongyi": "综艺",
    "dongman": "动漫", "duanju": "短剧",
}

class Spider(Spider):
    def init(self, extend=""):
        global HOST
        try:
            r = self.fetch(HOST, headers={"User-Agent": UA}, timeout=15000)
            if hasattr(r, 'url') and r.url and r.url != HOST.rstrip("/"):
                HOST = r.url.rstrip("/")
        except:
            pass

    def homeContent(self, filter=False):
        r = {"class": [], "list": []}
        for k, v in CATEGORIES.items():
            r["class"].append({"type_id": k, "type_name": v})
        return r

    def homeVideoContent(self):
        return {"list": []}

    def categoryContent(self, tid, pg=1, filter=False, extend=""):
        pn = 1
        try: pn = max(int(str(pg)), 1)
        except: pass
        cat = str(tid)
        if cat not in CATEGORIES:
            cat = "dianying"
        slug = cat
        try:
            if pn > 1:
                url = f"{HOST}/vodshow/{slug}--------{pn}---.html"
            else:
                url = f"{HOST}/vodshow/{slug}--------1---.html"
            r = self.fetch(url, headers={"User-Agent": UA}, timeout=30000)
            html = r.text if hasattr(r, 'text') else str(r)
            items = self._items(html)
            return {"page": pn, "pagecount": self._pagecount(html), "limit": 50, "total": len(items), "list": items}
        except:
            return {"page": pn, "pagecount": 1, "limit": 50, "total": 0, "list": []}

    def detailContent(self, ids):
        if isinstance(ids, list):
            vid = ids[0] if ids else ""
        else:
            vid = str(ids) if ids else ""
        m = re.search(r'(\d+)', str(vid))
        vid = m.group(1) if m else ""
        if not vid:
            return {"list": []}
        try:
            r = self.fetch(f"{HOST}/neirong/{vid}.html", headers={"User-Agent": UA}, timeout=30000)
            h = r.text if hasattr(r, 'text') else str(r)
        except:
            return {"list": []}
        d = {"vod_id": vid, "vod_name": "", "vod_pic": "", "vod_year": "",
             "vod_area": "", "vod_class": "", "vod_director": "", "vod_actor": "",
             "vod_content": "", "vod_remarks": "", "vod_play_from": "", "vod_play_url": ""}
        t1 = re.search(r'<h1[^>]*>(.*?)</h1>', h, re.S)
        if t1:
            clean = re.sub(r'<[^>]+>', ' ', t1.group(1)).strip()
            d["vod_name"] = clean.split('\n')[0].strip()
        if not d["vod_name"]:
            t2 = re.search(r'<title>(.*?)</title>', h)
            if t2: d["vod_name"] = t2.group(1).split("-")[0].strip()
        p = re.search(r'data-original="(https?://[^"]+\.(?:jpg|jpeg|png|webp))"', h, re.I)
        if not p:
            p = re.search(r'data-background="(https?://[^"]+\.(?:jpg|jpeg|png|webp))"', h, re.I)
        if not p:
            p = re.search(r'<img[^>]*src="(https?://[^"]+\.(?:jpg|jpeg|png|webp))"', h, re.I)
        if p: d["vod_pic"] = p.group(1)
        desc_m = re.search(r'class="fed-part-esan[^"]*"[\s\S]*?<span[^>]*>简介[：:]?</span>\s*&nbsp;.*?(?:<a[^>]*>[\s\S]*?</a>)\s*([^<]+)', h)
        if not desc_m:
            desc_m = re.search(r'class="fed-part-esan[^"]*"[\s\S]*?<span[^>]*>简介[：:]?</span>\s*&nbsp;\s*([^<]+)', h)
        if desc_m:
            desc = re.sub(r'\s+', ' ', desc_m.group(1)).strip()[:500]
            d["vod_content"] = desc
        for mi in re.finditer(r'class="fed-deta-info[^"]*"[\s\S]*?>(.*?)</li>', h, re.S):
            t = re.sub(r'<[^>]+>', '', mi.group(1)).strip()
            if "导演" in t: d["vod_director"] = t.split("：")[-1].split(":")[-1].strip()
            elif "主演" in t: d["vod_actor"] = t.split("：")[-1].split(":")[-1].strip()
            elif "年份" in t or "上映" in t:
                ym = re.search(r'(\d{4})', t)
                if ym: d["vod_year"] = ym.group(1)
            elif "备注" in t or "更新" in t: d["vod_remarks"] = t
        try:
            pf, pu = [], []
            tops = re.search(r'fed-drop-tops(.*?)fed-drop-btms', h, re.S)
            route_buttons = []
            if tops:
                for bm in re.finditer(r'href="/bofang/\d+-(\d+)-1\.html"[\s\S]*?>(.*?)<span[^>]*>(\d+)<', tops.group(1), re.S):
                    route = bm.group(1)
                    name = re.sub(r'<[^>]+>', '', bm.group(2)).strip()
                    count = int(bm.group(3))
                    if name and count > 0:
                        route_buttons.append((route, name, count))
            vis = re.search(r'fed-play-item fed-drop-item fed-visible(.*?)</ul>\s*</div>', h, re.S)
            default_eps = []
            default_route = None
            if vis:
                for em in re.finditer(r'href="/bofang/\d+-(\d+)-(\d+)\.html"[\s\S]*?>([^<]+)<', vis.group(1)):
                    r2, nid, name = em.group(1), em.group(2), em.group(3).strip()
                    if not default_route:
                        default_route = r2
                    default_eps.append((int(nid), name))
            if not route_buttons:
                items = re.findall(r'href="(/bofang/\d+-\d+-\d+\.html)"[\s\S]*?>([^<]+)<', h)
                routes = {}
                for href, name in items:
                    name = name.strip()
                    if not name or "报错" in name or "剧情" in name or "简介" in name or "立即播放" in name:
                        continue
                    rm = re.search(r'/bofang/\d+-(\d+)-(\d+)\.html', href)
                    if rm:
                        rt, nid = rm.group(1), rm.group(2)
                        if rt not in routes:
                            routes[rt] = []
                        routes[rt].append(f"{name}${urljoin(HOST, href)}")
                for rt in sorted(routes):
                    pf.append(f"源{len(pf)+1}")
                    pu.append("#".join(routes[rt]))
            else:
                for route, name, count in route_buttons:
                    eps_list = []
                    if default_route == route and default_eps:
                        for nid, ename in default_eps:
                            eps_list.append(f"{ename}${urljoin(HOST, f'/bofang/{vid}-{route}-{nid}.html')}")
                    else:
                        if default_eps:
                            for nid, ename in default_eps:
                                if nid <= count:
                                    eps_list.append(f"{ename}${urljoin(HOST, f'/bofang/{vid}-{route}-{nid}.html')}")
                        else:
                            for nid in range(1, count + 1):
                                eps_list.append(f"第{nid}集${urljoin(HOST, f'/bofang/{vid}-{route}-{nid}.html')}")
                    if eps_list:
                        pf.append(name)
                        pu.append("#".join(eps_list))
            if pf:
                d["vod_play_from"] = "$$$".join(pf)
                d["vod_play_url"] = "$$$".join(pu)
        except:
            pass
        return {"list": [d]}

    def searchContent(self, key, quick=False, pg="1"):
        return {"list": []}

    def playerContent(self, flag, id, vipFlags=None):
        a, b = str(flag), str(id) if id else ""
        if a.startswith("http") or "/bofang/" in a:
            url = a
        elif b.startswith("http") or "/bofang/" in b:
            url = b
        elif a.startswith("/"):
            url = urljoin(HOST, a)
        elif b.startswith("/"):
            url = urljoin(HOST, b)
        else:
            url = a
        try:
            r = self.fetch(url, headers={"User-Agent": UA}, timeout=30000)
            h = r.text if hasattr(r, 'text') else str(r)
        except:
            return {"url": ""}
        dm = re.search(r'"dmId"\s*:\s*"([^"]+)"', h)
        if dm:
            u = dm.group(1)
            if u.startswith("http"):
                if ".m3u8" in u:
                    return {"url": u}
                return {"url": u}
        m3u8 = re.search(r'(https?://[^\s"\'<>]+\.m3u8)', h)
        if m3u8:
            return {"url": m3u8.group(1)}
        return {"url": ""}

    def localProxy(self, param):
        pass

    def _pagecount(self, html):
        pc = 1
        # 优先用 data-total 属性 (fed模板分页跳转按钮)
        dt = re.findall(r'data-total="(\d+)"', html)
        for t in dt:
            try: pc = max(pc, int(t))
            except: pass
        # /vodshow/ 格式分页: href="/vodshow/dianying--------2---.html"
        pages_vod = re.findall(r'href="/vodshow/[^"]*-(\d+)-*--*\.html"', html)
        for p in pages_vod:
            try:
                n = int(p)
                if n > 1 and n < 10000:
                    pc = max(pc, n)
            except: pass
        # /fenlei/ 格式分页 (兼容旧格式)
        pages_fen = re.findall(r'href="/fenlei/[^"]*-?(\d+)\.html"', html)
        for p in pages_fen:
            try:
                n = int(p)
                if n > 1 and n < 10000:
                    pc = max(pc, n)
            except: pass
        return pc

    def _items(self, html):
        items, seen = [], set()
        # 只取 data-original 的列表项，不取 data-background 的轮播项
        # 轮播项标题和封面不在同一个结构里，混入会导致错位
        cover_map = {}
        for m in re.finditer(r'data-original="(https?://[^"]+)"', html, re.I):
            # 找到 data-original 前面最近的 href (取最后一个，不是第一个)
            before = html[max(0, m.start()-500):m.start()]
            hms = re.findall(r'href="(/neirong/(\d+)\.html)"', before)
            if hms:
                hm = hms[-1]
                vid = hm[1]
                if vid not in cover_map:
                    cover_map[vid] = (hm[0], m.group(1))
        # 标题: fed-list-title
        titles = {}
        for tm in re.finditer(r'class="[^"]*fed-list-title[^"]*"[\s\S]*?href="/neirong/(\d+)\.html"[\s\S]*?>\s*(.*?)\s*</a>', html, re.S):
            name = re.sub(r'<[^>]+>', '', tm.group(2)).strip()
            if name:
                titles[tm.group(1)] = name[:50]
        # 合并: 只用列表项的封面
        for vid, (href, pic) in cover_map.items():
            if vid in seen:
                continue
            seen.add(vid)
            items.append({
                "vod_id": vid, "vod_name": titles.get(vid, ""),
                "vod_pic": pic, "vod_remarks": "", "vod_url": urljoin(HOST, href),
            })
        return items
