# -*- coding: utf-8 -*-
import sys
import re
import json
import base64
from urllib.parse import urljoin, quote, unquote

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

HOST = "https://www.qlys.cc"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

CATEGORIES = {
    "1": "电影", "2": "电视剧", "3": "短剧", "4": "动漫", "5": "综艺",
}

class Spider(Spider):
    def init(self, extend=""):
        global HOST
        try:
            resp = self.fetch(HOST, headers={"User-Agent": UA}, timeout=15000)
            if hasattr(resp, 'url') and resp.url and resp.url != HOST.rstrip("/"):
                HOST = resp.url.rstrip("/")
        except:
            pass

    def homeContent(self, filter=False):
        r = {"class": [], "list": [], "filter": {}}
        for k, v in CATEGORIES.items():
            r["class"].append({"type_id": k, "type_name": v})
        try:
            resp = self.fetch(HOST, headers={"User-Agent": UA}, timeout=30000)
            html = resp.text if hasattr(resp, 'text') else str(resp)
            items = self._items(html)
            r["list"] = [it for it in items if it["vod_pic"]][:30]
        except:
            pass
        return r

    def homeVideoContent(self):
        return {"list": []}

    def categoryContent(self, tid, pg=1, filter=False, extend=""):
        pn = 1
        try: pn = max(int(str(pg)), 1)
        except: pass
        cid = str(tid)
        try:
            if pn > 1:
                url = f"{HOST}/index.php/vod/type/id/{cid}/page/{pn}.html"
            else:
                url = f"{HOST}/index.php/vod/type/id/{cid}.html"
            resp = self.fetch(url, headers={"User-Agent": UA}, timeout=30000)
            html = resp.text if hasattr(resp, 'text') else str(resp)
            items = self._items(html)
            pagecount = self._pagecount(html)
            return {"page": pn, "pagecount": pagecount, "limit": 50, "total": len(items), "list": items}
        except:
            return {"page": pn, "pagecount": 1, "limit": 50, "total": 0, "list": []}

    def detailContent(self, ids):
        if isinstance(ids, list):
            vid = ids[0] if ids else ""
        else:
            vid = str(ids) if ids else ""
        m = re.search(r'(\d+)', str(vid))
        vid = m.group(1) if m else ""
        if not vid: return {"list": []}
        try:
            resp = self.fetch(f"{HOST}/index.php/vod/detail/id/{vid}.html", headers={"User-Agent": UA}, timeout=30000)
            h = resp.text if hasattr(resp, 'text') else str(resp)
        except:
            return {"list": []}
        d = {"vod_id": vid, "vod_name": "", "vod_pic": "", "vod_year": "",
             "vod_area": "", "vod_class": "", "vod_director": "", "vod_actor": "",
             "vod_content": "", "vod_remarks": "", "vod_play_from": "", "vod_play_url": ""}
        t1 = re.search(r'<h1[^>]*>(.*?)</h1>', h, re.S)
        if t1:
            clean = re.sub(r'<[^>]+>', ' ', t1.group(1)).strip()
            parts = re.split(r'\s{2,}|\n', clean)
            for part in parts:
                p = part.strip()
                if p and len(p) > 1:
                    d["vod_name"] = p
                    break
        if not d["vod_name"]:
            t2 = re.search(r'<title>(.*?)</title>', h)
            if t2: d["vod_name"] = t2.group(1).split("-")[0].strip()
        p = re.search(r'data-original="([^"]+)"', h)
        if not p:
            p = re.search(r'data-background="([^"]+)"', h)
        if not p:
            p = re.search(r'<img[^>]*src="([^"]+\.(?:jpg|jpeg|png|webp))"', h, re.I)
        if p: d["vod_pic"] = p.group(1)
        for t in re.findall(r'<a[^>]*title="(\d{4})"', h):
            d["vod_year"] = t
        desc = re.search(r'<div\s+id="content"[^>]*>(.*?)</div>\s*</div>', h, re.S)
        if desc: d["vod_content"] = re.sub(r'<[^>]+>', '', desc.group(1)).strip()[:500]
        if not d["vod_content"]:
            desc2 = re.search(r'class="vod_content[^"]*"[^>]*>(.*?)</div>', h, re.S)
            if desc2: d["vod_content"] = re.sub(r'<[^>]+>', '', desc2.group(1)).strip()[:500]
        for mi in re.finditer(r'class="slide_info[^"]*"[^>]*>(.*?)</div>', h, re.S):
            t = re.sub(r'<[^>]+>', '', mi.group(1)).strip()
            if "导演" in t: d["vod_director"] = t.split("：")[-1].split(":")[-1].strip()
            elif "主演" in t: d["vod_actor"] = t.split("：")[-1].split(":")[-1].strip()
            elif "备注" in t or "更新" in t or "集数" in t: d["vod_remarks"] = t
        try:
            default_block = re.search(r'id="tab_con_playlist_(\d+)"[^>]*(?:style="display:block"|style="[^"]*"[^>]*>)(.*?)(?=<div\s+class="tab-content"|<div\s+id="tab_con_playlist_)', h, re.S)
            if not default_block:
                default_block = re.search(r'id="tab_con_playlist_(\d+)"[^>]*>(.*?)(?=<div\s+class="tab-content"|<div\s+id="tab_con_playlist_)', h, re.S)
            default_pid = default_block.group(1) if default_block else "1"
            default_content = default_block.group(2) if default_block else ""
            tab_names = re.findall(r'<li[^>]*class="tab-switch[^"]*"[^>]*switch="tab_con_playlist_(\d+)"[^>]*>.*?<a[^>]*>\s*(.*?)\s*</a>', h, re.S)
            default_name = "默认"
            for pid, name in tab_names:
                if pid == default_pid:
                    default_name = name.strip()
                    break
            eps = re.findall(r'href="(/index\.php/vod/play/id/[^"]+/sid/\d+/nid/\d+\.html)"[^>]*>([^<]*)<', default_content)
            el = []
            for u, n in eps:
                n = n.strip()
                if n and "报错" not in n:
                    el.append(f"{n}${urljoin(HOST, u)}")
            if not el:
                play_eps = re.findall(r'href="(/index\.php/vod/play/id/\d+/sid/(\d+)/nid/\d+\.html)"[^>]*>([^<]*)<', h)
                sources = {}
                for href, sid, name in play_eps:
                    name = name.strip()
                    if not name or "报错" in name: continue
                    if sid not in sources:
                        sources[sid] = []
                    sources[sid].append(f"{name}${urljoin(HOST, href)}")
                if default_pid in sources:
                    el = sources[default_pid]
            if el:
                d["vod_play_from"] = default_name
                d["vod_play_url"] = "#".join(el)
        except:
            pass
        return {"list": [d]}

    def searchContent(self, key, quick=False, pg="1"):
        try:
            resp = self.fetch(f"{HOST}/index.php/vod/search.html", params={"wd": str(key)}, headers={"User-Agent": UA}, timeout=15000)
            html = resp.text if hasattr(resp, 'text') else str(resp)
            if len(html) > 200:
                return {"list": self._items(html)[:30]}
        except:
            pass
        return {"list": []}

    def playerContent(self, flag, id, vipFlags=None):
        a, b = str(flag), str(id) if id else ""
        if a.startswith("http") or "/vod/play/" in a or "/index.php/vod/play/" in a:
            url = a
        elif b.startswith("http") or "/vod/play/" in b or "/index.php/vod/play/" in b:
            url = b
        elif a.startswith("/"):
            url = urljoin(HOST, a)
        elif b.startswith("/"):
            url = urljoin(HOST, b)
        else:
            url = a
        try:
            resp = self.fetch(url, headers={"User-Agent": UA}, timeout=30000)
            h = resp.text if hasattr(resp, 'text') else str(resp)
        except:
            return {"url": ""}
        data = None
        for tag in ['player_aaaa', 'player_data']:
            idx = h.find(tag)
            if idx < 0: continue
            brace = h.find('{', idx)
            if brace < 0: continue
            depth, end = 0, brace
            for i in range(brace, min(brace + 10000, len(h))):
                if h[i] == '{': depth += 1
                elif h[i] == '}':
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            try:
                data = json.loads(h[brace:end])
            except:
                data = None
            if data:
                break
        if data:
            u = data.get("url", "")
            if u:
                if data.get("encrypt", 0) == 1:
                    try: u = unquote(base64.b64decode(u).decode("utf-8"))
                    except: pass
                if u.startswith("http"):
                    return {"url": u}
        return {"url": ""}

    def localProxy(self, param):
        pass

    def _pagecount(self, html):
        pc = 1
        last = re.search(r'<a[^>]*href="[^"]*page/(\d+)\.html"[^>]*>尾页', html)
        if last:
            pc = max(pc, int(last.group(1)))
        pages = re.findall(r'href="[^"]*page/(\d+)\.html"', html)
        for p in pages:
            try: pc = max(pc, int(p))
            except: pass
        return pc

    def _items(self, html):
        items, seen = [], set()
        for m in re.finditer(r'<a[^>]*href="(/index\.php/vod/detail/id/(\d+)\.html)"[^>]*title="([^"]*)"', html):
            vid, title = m.group(2), m.group(3)
            if vid in seen: continue
            seen.add(vid)
            a_end = html.find('</a>', m.start())
            if a_end < 0: continue
            a_block = html[m.start():min(a_end + 4, m.start() + 2000)]
            pic = re.search(r'data-original="(https?://[^"]+\.(?:jpg|jpeg|png|webp))"', a_block, re.I)
            if not pic:
                pic = re.search(r'data-background="(https?://[^"]+\.(?:jpg|jpeg|png|webp))"', a_block, re.I)
            if not pic:
                pic = re.search(r'<img[^>]*src="(https?://[^"]+\.(?:jpg|jpeg|png|webp))"', a_block, re.I)
            items.append({
                "vod_id": vid, "vod_name": title,
                "vod_pic": pic.group(1) if pic else "",
                "vod_remarks": "",
                "vod_url": urljoin(HOST, m.group(1)),
            })
        return items
