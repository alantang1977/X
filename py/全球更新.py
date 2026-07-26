#!/usr/bin/python
# -*- coding: utf-8 -*-
import json, requests
from urllib.parse import quote
try:
    from base.spider import Spider as BaseSpider
except Exception:
    BaseSpider = object

class Spider(BaseSpider):
    def getName(self): return "全球追更"
    def init(self, extend=""):
        self.key = "2894d9a1baf7812b451de03c801b0281"
        self.ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        self.headers = {"User-Agent": self.ua}
        self.img = "https://images.tmdb.org/t/p/w500"
        self.apis = ["https://api.tmdb.org/3"]
        self.platforms = [{"id":"domestic","name":"国内聚合","network":"2007|1419|1330|1605|1631"},{"id":"netflix","name":"Netflix","network":"213"},{"id":"hbo","name":"HBO Max","network":"49"},{"id":"disney","name":"Disney+","network":"2739"},{"id":"appletv","name":"Apple TV+","network":"2552"},{"id":"amazon","name":"Amazon Prime","network":"1024"},{"id":"hulu","name":"Hulu","network":"453"},{"id":"paramount","name":"Paramount+","network":"4330"}]
        self.cache = {}
    def _get(self, endpoint, params=None):
        params = params or {}
        params["api_key"] = self.key
        for base in self.apis:
            try:
                r = requests.get(base + endpoint, params=params, headers=self.headers, timeout=15)
                if r.status_code == 200: return r.json()
            except Exception:
                continue
        return {}
    def _today(self):
        import datetime
        return datetime.datetime.now().strftime("%Y-%m-%d")
    def _filters(self):
        return [{"key":"sort","name":"🔥 动态追踪","value":[{"n":"📅 追更模式","v":"next_episode"},{"n":"📆 今日播出","v":"daily_airing"},{"n":"🆕 最新上线","v":"first_air_date.desc"},{"n":"⭐ 综合热度","v":"popularity.desc"}]},{"key":"type","name":"📺 内容类型","value":[{"n":"🎥 电视剧集","v":"tv"},{"n":"🎬 电影作品","v":"movie"},{"n":"🌸 动漫动画","v":"anime"},{"n":"🎤 综艺节目","v":"variety"}]}]
    def _pic(self, p): return self.img + p if p else ""
    def _vod(self, item, typ, sort="popularity.desc"):
        mid = str(item.get("id",""))
        name = item.get("name") or item.get("title") or ""
        remark = "⭐" + str(round(float(item.get("vote_average") or 0), 1))
        date = item.get("first_air_date") or item.get("release_date") or "1900-01-01"
        ck = "info_" + typ + "_" + mid + "_" + sort
        if ck in self.cache: return self.cache[ck]
        if not any("\u4e00" <= x <= "\u9fff" for x in name):
            d = self._get(("/movie/" if typ == "movie" else "/tv/") + mid, {"language":"zh-CN","append_to_response":"alternative_titles,external_ids"})
            alt = ((d.get("alternative_titles") or {}).get("titles") or (d.get("alternative_titles") or {}).get("results") or [])
            for t in alt:
                if t.get("iso_3166_1") == "CN" and t.get("title"):
                    name = t.get("title")
                    break
        if typ != "movie" and sort in ["next_episode","daily_airing","first_air_date.desc"]:
            d = self._get("/tv/" + mid, {"language":"zh-CN"})
            ep = d.get("next_episode_to_air") or d.get("last_episode_to_air")
            if ep:
                date = ep.get("air_date") or date
                remark = ("🕒" if d.get("next_episode_to_air") else "✅") + date[5:] + " S" + str(ep.get("season_number") or 0).zfill(2) + "E" + str(ep.get("episode_number") or 0).zfill(2)
        vod = {"vod_id":typ + ":" + mid, "vod_name":name, "vod_pic":self._pic(item.get("poster_path")), "vod_remarks":remark, "_date":date}
        self.cache[ck] = vod
        return vod
    def homeContent(self, filter):
        fs = self._filters()
        return {"class":[{"type_id":p["id"],"type_name":p["name"]} for p in self.platforms], "filters":{p["id"]:fs for p in self.platforms}, "list":[]}
    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg or 1)
        p = next((x for x in self.platforms if x["id"] == tid), None)
        if not p: return {"page":page,"pagecount":1,"limit":20,"total":0,"list":[]}
        sort = (extend or {}).get("sort") or "popularity.desc"
        typ = (extend or {}).get("type") or "tv"
        media = "movie" if typ == "movie" else "tv"
        endpoint = "/discover/movie" if media == "movie" else "/discover/tv"
        base = {"language":"zh-CN","page":page,"sort_by":"popularity.desc" if sort in ["daily_airing","next_episode"] else sort}
        if typ == "anime": base["with_genres"] = "16"
        if typ == "variety": base["with_genres"] = "10764|10767"
        if sort == "daily_airing":
            base["air_date.gte"] = self._today()
            base["air_date.lte"] = self._today()
        items, seen = [], set()
        for net in p["network"].split("|"):
            q = dict(base)
            q["with_networks"] = net
            data = self._get(endpoint, q)
            for i in data.get("results", []):
                mid = str(i.get("id",""))
                if mid and mid not in seen:
                    seen.add(mid)
                    items.append(i)
        if sort in ["next_episode","daily_airing","first_air_date.desc"]: items.sort(key=lambda x:x.get("first_air_date") or x.get("release_date") or "", reverse=True)
        else: items.sort(key=lambda x:float(x.get("popularity") or 0), reverse=True)
        return {"page":page,"pagecount":100,"limit":20,"total":2000,"list":[self._vod(i, media, sort) for i in items[:20]]}
    def detailContent(self, ids):
        raw = ids[0] if isinstance(ids, list) else ids
        arr = str(raw).split(":", 1)
        typ, mid = (arr[0], arr[1]) if len(arr) == 2 else ("tv", str(raw))
        data = self._get(("/movie/" if typ == "movie" else "/tv/") + mid, {"language":"zh-CN","append_to_response":"credits"})
        if not data and typ != "movie":
            typ = "movie"
            data = self._get("/movie/" + mid, {"language":"zh-CN","append_to_response":"credits"})
        if not data: return {"list":[]}
        name = data.get("name") or data.get("title") or ""
        year = (data.get("release_date") or data.get("first_air_date") or "")[:4]
        area = ", ".join([c.get("name","") for c in data.get("production_countries", [])])
        actor = ", ".join([c.get("name","") for c in (data.get("credits") or {}).get("cast", [])[:8]])
        director = ", ".join([c.get("name","") for c in (data.get("credits") or {}).get("crew", []) if c.get("job") == "Director"][:3])
        return {"list":[{"vod_id":typ + ":" + mid,"vod_name":name,"vod_pic":self._pic(data.get("poster_path")),"type_name":"电影" if typ == "movie" else "电视剧","vod_year":year,"vod_area":area,"vod_remarks":"电影" if typ == "movie" else ("已完结" if data.get("status") == "Ended" else "连载中"),"vod_actor":actor,"vod_director":director,"vod_content":data.get("overview") or "暂无剧情简介","vod_play_from":"其他源","vod_play_url":"播放$" + quote(name)}]}
    def searchContent(self, key, quick, pg="1"):
        page = int(pg or 1)
        data = self._get("/search/multi", {"query":key,"page":page,"language":"zh-CN"})
        return {"list":[{"vod_id":i.get("media_type","tv") + ":" + str(i.get("id","")),"vod_name":i.get("title") or i.get("name") or key,"vod_pic":self._pic(i.get("poster_path")),"vod_remarks":"电影" if i.get("media_type") == "movie" else "剧集","goSearch":True} for i in data.get("results", []) if i.get("media_type") in ["movie","tv"]],"page":page,"pagecount":data.get("total_pages",1),"total":data.get("total_results",0)}
    def playerContent(self, flag, id, vipFlags):
        return {"parse":1,"url":id}