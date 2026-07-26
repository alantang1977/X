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

HOST = "https://www.moxy.top"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

class Spider(Spider):
    def init(self, extend=""):
        global HOST
        try:
            r = self.fetch(HOST, headers={"User-Agent": UA}, timeout=15000)
            if hasattr(r, 'url') and r.url and "moxy" not in r.url:
                HOST = r.url.rstrip("/")
        except:
            pass

    def homeContent(self, filter=False):
        r = {"class": [], "list": [], "filter": {}}
        for k, v in {"1":"电影","2":"连续剧","3":"综艺","4":"动漫","5":"短剧"}.items():
            r["class"].append({"type_id": k, "type_name": v})
        try:
            resp = self.fetch(HOST, headers={"User-Agent": UA}, timeout=30000)
            html = resp.text if hasattr(resp, 'text') else str(resp)
            r["list"] = self._items(html)[:60]
        except:
            pass
        return r

    def homeVideoContent(self):
        return {"list": []}

    def categoryContent(self, tid, pg=1, filter=False, extend=""):
        pn = 1
        try: pn = max(int(str(pg)), 1)
        except: pass
        cid = str(tid) if str(tid) in "12345" else "1"
        try:
            if pn > 1:
                url = f"{HOST}/vodshow/{cid}--------{pn}---.html"
            else:
                url = f"{HOST}/vodshow/{cid}-----------.html"
            resp = self.fetch(url, headers={"User-Agent": UA}, timeout=30000)
            html = resp.text if hasattr(resp, 'text') else str(resp)
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
        if not vid: return {"list": []}
        try:
            resp = self.fetch(f"{HOST}/voddetail{vid}.html", headers={"User-Agent": UA}, timeout=30000)
            h = resp.text if hasattr(resp, 'text') else str(resp)
        except:
            return {"list": []}
        d = {"vod_id": vid, "vod_name": "", "vod_pic": "", "vod_year": "",
             "vod_area": "", "vod_class": "", "vod_director": "", "vod_actor": "",
             "vod_content": "", "vod_remarks": "", "vod_play_from": "", "vod_play_url": ""}
        t1 = re.search(r'<h1[^>]*>(.*?)</h1>', h, re.S)
        if t1: d["vod_name"] = t1.group(1).strip()
        if not d["vod_name"]:
            t2 = re.search(r'<title>(.*?)</title>', h)
            if t2: d["vod_name"] = t2.group(1).split("-")[0].strip()
        p = re.search(r'data-original="([^"]+)"', h)
        if p: d["vod_pic"] = p.group(1)
        for t in re.findall(r'<a[^>]*title="(\d{4})"', h):
            d["vod_year"] = t
        for t in re.findall(r'<a[^>]*title="([^"]*)"', h):
            if t in ("中国大陆","中国","香港","台湾","美国","日本","韩国","英国","法国","泰国","印度"):
                d["vod_area"] = t
        desc = re.search(r'<div[^>]*class="[^"]*module-info-introduction-content[^"]*"[^>]*>\s*<p>(.*?)</p>', h, re.S)
        if desc: d["vod_content"] = re.sub(r'<[^>]+>', '', desc.group(1)).strip()[:500]
        for m in re.finditer(r'<div[^>]*class="[^"]*module-info-item[^"]*"[^>]*>(.*?)</div>', h, re.S):
            t = re.sub(r'<[^>]+>', '', m.group(1)).strip()
            if "导演" in t: d["vod_director"] = t.replace("导演：","").replace("导演:","").strip()
            elif "主演" in t: d["vod_actor"] = t.replace("主演：","").replace("主演:","").strip()
            elif "备注" in t: d["vod_remarks"] = t.replace("备注：","").replace("备注:","").strip()
        try:
            sources = re.findall(r'data-dropdown-value="([^"]+)"', h) or ["默认"]
            blocks = re.findall(r'<div[^>]*class="[^"]*module-play-list[^"]*"[^>]*>(.*?)</div>\s*</div>\s*</div>', h, re.S)
            if not blocks:
                blocks = re.findall(r'<div[^>]*class="[^"]*module-play-list-content[^"]*"[^>]*>(.*?)</div>', h, re.S)
            pf, pu = [], []
            for i, blk in enumerate(blocks):
                eps = re.findall(r'<a[^>]*href="(/vodplay/[^"]+)"[^>]*>(?:<[^>]+>)*([^<]{1,20})(?:</[^>]+>)*</a>', blk, re.S)
                if not eps:
                    eps = re.findall(r'<a[^>]*href="(/vodplay/[^"]+)"[^>]*>.*?<span>(.*?)</span>', blk, re.S)
                if eps:
                    src = sources[i] if i < len(sources) else f"源{i+1}"
                    el = [f"{n.strip()}${urljoin(HOST, u)}" for u, n in eps if n.strip()]
                    if el:
                        pf.append(src)
                        pu.append("#".join(el))
            if pf:
                d["vod_play_from"] = "$$$".join(pf)
                d["vod_play_url"] = "$$$".join(pu)
        except:
            pass
        return {"list": [d]}

    def searchContent(self, key, quick=False, pg="1"):
        try:
            url = f"{HOST}/vodsearch/{quote(str(key))}-------------.html"
            resp = self.fetch(url, headers={"User-Agent": UA}, timeout=15000)
            html = resp.text if hasattr(resp, 'text') else str(resp)
            if len(html) > 200:
                return {"list": self._items(html)[:30]}
        except:
            pass
        return {"list": []}

    def playerContent(self, flag, id, vipFlags=None):
        a, b = str(flag), str(id) if id else ""
        if a.startswith("http") or "/vodplay/" in a:
            url = a
        elif b.startswith("http") or "/vodplay/" in b:
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
        pd = re.search(r'player_data\s*=\s*(\{.*?\})', h, re.S)
        if pd:
            try:
                data = json.loads(pd.group(1))
                u = data.get("url", "")
                if u:
                    try:
                        real_url = unquote(base64.b64decode(u).decode("utf-8"))
                    except:
                        real_url = u
                    if real_url.startswith("http"):
                        return {"url": real_url}
            except:
                pass
        return {"url": ""}

    def localProxy(self, param):
        pass

    def _pagecount(self, html):
        pc = 1
        last = re.search(r'<a[^>]*href="[^"]*vodshow/\d+[^"]*(\d+)---\.html"[^>]*>尾页', html, re.S)
        if last:
            pc = max(pc, int(last.group(1)))
        page_links = re.findall(r'<a[^>]*href="[^"]*vodshow/\d+-(\d+)', html)
        for p in page_links:
            try:
                n = int(p)
                if n <= 100:
                    pc = max(pc, n)
            except:
                pass
        all_nums = re.findall(r'class="[^"]*page-number[^"]*"[^>]*>\s*(\d+)\s*<', html)
        for n in all_nums:
            try: pc = max(pc, int(n))
            except: pass
        return pc

    def _items(self, html):
        items, seen = [], set()
        def ext(href, block):
            v = re.search(r'/voddetail(\d+)\.html', href)
            if not v or v.group(1) in seen: return None
            seen.add(v.group(1))
            t = (re.search(r'title="([^"]*)"', block) or re.search(r'alt="([^"]*)"', block))
            if not t: return None
            p = re.search(r'data-original="([^"]+)"', block)
            n = re.search(r'<div[^>]*class="[^"]*module-item-note[^"]*"[^>]*>([^<]+)</div>', block)
            return {"vod_id": v.group(1), "vod_name": t.group(1),
                    "vod_pic": p.group(1) if p else "",
                    "vod_remarks": n.group(1).strip() if n else "",
                    "vod_url": urljoin(HOST, href)}
        for m in re.finditer(
            r'<a[^>]*href="(/voddetail\d+\.html)"[^>]*title="([^"]*)"[^>]*class="[^"]*module-poster-item[^"]*"[\s\S]*?</a>',
            html
        ):
            item = ext(m.group(1), m.group(0))
            if item: items.append(item)
        for m in re.finditer(
            r'<a[^>]*href="(/voddetail\d+\.html)"[^>]*class="[^"]*module-card-item-poster[^"]*"[\s\S]*?</a>',
            html
        ):
            item = ext(m.group(1), m.group(0))
            if item: items.append(item)
        return items
