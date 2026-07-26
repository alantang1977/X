import re
import json
import base64
import requests
from urllib.parse import quote, unquote
from base.spider import Spider as BaseSpider

class Spider(BaseSpider):
    def getName(self):
        return "聚影网盘"

    def init(self, extend=""):
        self.ext=self._json(extend); self.host=str(self.ext.get("host") or "https://www.jying.top").rstrip("/"); self.username=str(self.ext.get("username") or ""); self.password=str(self.ext.get("password") or ""); self.token=str(self.ext.get("token") or ""); self.cookie=str(self.ext.get("cookie") or ""); self.timeout=int(self.ext.get("timeout") or 15); self.limit=int(self.ext.get("limit") or 24); self.cache={}; self.session=requests.Session(); self.session.verify=False; self.session.headers.update({"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36","Accept":"application/json, text/plain, */*","Content-Type":"application/json","X-Requested-With":"XMLHttpRequest","Referer":self.host+"/login"})
        if self.cookie: self.session.headers.update({"Cookie":self.cookie})
        if self.token: self.session.headers.update({"X-App-User-Token":self.token})
        self._login(); return {}

    def homeContent(self, filter):
        d=self._overview(); cls=[{"type_id":"all","type_name":"影视库"},{"type_id":"movie","type_name":"电影"},{"type_id":"tv","type_name":"电视剧"},{"type_id":"anime","type_name":"动漫"},{"type_id":"documentary","type_name":"纪录片"},{"type_id":"other","type_name":"其他"}]
        return {"class":cls,"filters":self._filters(d) if filter else {}}

    def homeVideoContent(self):
        d=self._api("/api/app/home-initial-data/",{"page_size":12}); arr=[]
        for k in ["default_movies","hero_candidates"]: arr+=d.get(k) or []
        for v in (d.get("featured_sections") or {}).values(): arr+=v or []
        return {"list":[self._vod(x) for x in self._dedupe(arr)[:24]]}

    def categoryContent(self, tid, pg, filter, extend):
        page=self._page(pg); tid=str(tid or "all"); ext=self._json(extend); typ,data=self._pid(tid)
        if typ=="group": return self._group_page(data,page)
        if typ=="movie": return self._movie_res_page(data,page)
        p={"page":page,"page_size":self.limit,"count":1,"ordering":ext.get("ordering") or ext.get("sort") or "-created_at"}
        if tid not in ["all",""]: p["type"]=tid
        for k in ["category","region","tag","year","resource_type"]:
            if ext.get(k): p[k]=ext.get(k)
        d=self._api("/api/app/movies/",p); arr=d.get("results") or []
        return {"list":[self._vod(x) for x in arr],"page":page,"pagecount":int(d.get("total_pages") or page+(1 if arr else 0)),"limit":self.limit,"total":int(d.get("total_count") or d.get("count") or len(arr))}

    def detailContent(self, ids):
        vid=ids[0] if isinstance(ids,list) and ids else ids; typ,data=self._pid(str(vid or ""))
        if typ=="res": return self._detail_res(data)
        mid=data.get("id") if typ in ["movie","group"] else vid
        d=self._detail(mid); m=d.get("data") or d.get("movie") or d
        res=self._resources(mid); groups={}
        for x in res: groups.setdefault(self._rtype(x),[]).append(x)
        froms=[]; urls=[]
        for k in self._order(groups):
            arr=groups.get(k) or []
            if arr: froms.append(self._rname(k,arr[0])); urls.append("#".join([self._clean(x.get("title") or x.get("resource_description") or self._rname(k,x))+"$"+self._eid("res",x) for x in arr]))
        if not froms:
            froms=["提示"]; urls=["暂无资源$__EMPTY__"]
        vod={"vod_id":str(mid),"vod_name":m.get("title") or "资源","vod_pic":m.get("cover") or m.get("cover_url") or "","vod_remarks":self._remarks(m),"type_name":m.get("movie_type_display") or m.get("category_name") or "","vod_year":str(m.get("release_year") or m.get("year") or ""),"vod_area":m.get("region") or "","vod_actor":m.get("actors") or "","vod_director":m.get("director") or "","vod_content":m.get("description") or "","vod_play_from":"$$$".join(froms),"vod_play_url":"$$$".join(urls)}
        return {"list":[vod]}

    def searchContent(self, key, quick=False, pg="1"):
        return self.searchContentPage(key,quick,pg)

    def searchContentPage(self, key, quick=False, pg="1"):
        page=self._page(pg); kw=str(key or "").strip()
        if not kw: return {"list":[],"page":page,"pagecount":1,"limit":self.limit,"total":0}
        d=self._api("/api/app/movies/",{"q":kw,"page":page,"page_size":self.limit,"count":1,"exact":1}); arr=d.get("results") or []
        return {"list":[self._vod(x) for x in arr],"page":page,"pagecount":int(d.get("total_pages") or 1),"limit":self.limit,"total":int(d.get("total_count") or d.get("count") or len(arr))}

    def playerContent(self, flag, id, vipFlags):
        if str(id or "") in ["__EMPTY__",""]: return {"parse":0,"playUrl":"","url":"","header":self._h()}
        typ,data=self._pid(id)
        if typ=="res":
            url=self._access(data); url=unquote(str(url or "")).replace("&amp;","&").strip()
            if url.lower().startswith("magnet:?") or url.lower().startswith("ed2k://"): return {"parse":0,"playUrl":"","url":url,"header":self._h()}
            if re.search(r"\.(m3u8|mp4|flv|mkv|ts)(\?|$)",url,re.I): return {"parse":0,"playUrl":"","url":url,"header":self._h()}
            return {"parse":0,"playUrl":"","url":"push://"+url if url.startswith("http") else url,"header":self._h()}
        return {"parse":0,"playUrl":"","url":id,"header":self._h()}

    def localProxy(self, params):
        return None

    def isVideoFormat(self, url):
        return bool(re.search(r"\.(m3u8|mp4|flv|mkv|ts)(\?|$)",str(url or ""),re.I))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        return ""

    def _login(self):
        if self.token: return True
        if not self.username or not self.password: return False
        try:
            self.session.get(self.host+"/api/csrf/",timeout=self.timeout); csrf=self.session.cookies.get("csrftoken") or ""; h=self._h(); h.update({"X-CSRFToken":csrf,"Origin":self.host,"Referer":self.host+"/login"}); r=self.session.post(self.host+"/api/app/login/",headers=h,json={"username":self.username,"password":self.password},timeout=self.timeout).json(); self.token=r.get("token") or ""; self.session.headers.update({"X-App-User-Token":self.token}) if self.token else None; return bool(self.token)
        except Exception: return False

    def _api(self,path,params=None,post=None):
        key=("p" if post is not None else "g")+path+json.dumps(params or {},ensure_ascii=False,sort_keys=True)+json.dumps(post or {},ensure_ascii=False,sort_keys=True)
        if key in self.cache: return self.cache[key]
        try:
            url=self.host+path; h=self._h(); h.update({"Referer":self.host+"/categories"}); r=self.session.post(url,headers=h,json=post or {},timeout=self.timeout) if post is not None else self.session.get(url,headers=h,params=params or {},timeout=self.timeout); d=r.json() if r.text else {}
        except Exception: d={}
        self.cache[key]=d if isinstance(d,dict) else {}; return self.cache[key]

    def _overview(self):
        return self._api("/api/app/categories/")

    def _detail(self,mid):
        return self._api("/api/app/movie/%s/detail/"%quote(str(mid)))

    def _resources(self,mid):
        key="res|"+str(mid)
        if key in self.cache: return self.cache[key]
        arr=[]; page=1
        while page<=10:
            d=self._api("/api/app/movie/%s/resources/"%quote(str(mid)),{"page":page,"page_size":120}); a=d.get("resources") or []
            if not a: break
            arr+=a
            if not d.get("has_more"): break
            page+=1
        self.cache[key]=self._dedupe(arr); return self.cache[key]

    def _access(self,x):
        if x.get("target"): return x.get("target")
        u=x.get("share_link") or x.get("raw_share_link") or x.get("share_link_with_code") or ""
        if u: return u
        rid=x.get("id"); ticket=x.get("access_ticket") or ""
        if not rid or not ticket: return ""
        d=self._api("/api/app/resource/%s/access/"%quote(str(rid)),post={"access_ticket":str(ticket)})
        target=d.get("target") or d.get("share_link") or ""; code=d.get("access_code") or d.get("extraction_code") or ""
        return (target+(" 提取码:"+code if code and code not in target else "")).strip()

    def _group_page(self,data,page):
        arr=[x for x in self._resources(data.get("id")) if self._rtype(x)==data.get("group")]; total=len(arr); pc=max(1,(total+self.limit-1)//self.limit); page=max(1,min(page,pc)); s=(page-1)*self.limit
        return {"list":[{"vod_id":self._eid("res",x),"vod_name":self._clean(x.get("title") or x.get("resource_description") or self._rname(self._rtype(x),x)),"vod_pic":data.get("pic") or "","vod_remarks":self._rname(self._rtype(x),x),"vod_tag":"file","vod_content":x.get("description") or x.get("resource_description") or ""} for x in arr[s:s+self.limit]],"page":page,"pagecount":pc,"limit":self.limit,"total":total}

    def _movie_res_page(self,data,page):
        groups={}
        for x in self._resources(data.get("id")): groups.setdefault(self._rtype(x),[]).append(x)
        lst=[{"vod_id":self._eid("group",{"id":data.get("id"),"group":k,"pic":data.get("pic") or ""}),"vod_name":self._rname(k,(groups.get(k) or [{}])[0]),"vod_pic":data.get("pic") or "","vod_remarks":"%s条资源"%len(groups.get(k) or []),"vod_tag":"folder"} for k in self._order(groups)]
        return {"list":lst,"page":1,"pagecount":1,"limit":len(lst),"total":len(lst)}

    def _detail_res(self,x):
        name=self._clean(x.get("title") or x.get("resource_description") or self._rname(self._rtype(x),x)); pic=x.get("pic") or ""; return {"list":[{"vod_id":str(x.get("id") or "res"),"vod_name":name,"vod_pic":pic,"vod_remarks":self._rname(self._rtype(x),x),"vod_content":x.get("description") or x.get("resource_description") or "","vod_play_from":self._rname(self._rtype(x),x),"vod_play_url":name+"$"+self._eid("res",x)}]}

    def _filters(self,d):
        years=[{"n":"全部","v":""}]+[{"n":str(y),"v":str(y)} for y in range(2028,1989,-1)]
        types=[{"n":"全部","v":""},{"n":"电影","v":"movie"},{"n":"电视剧","v":"tv"},{"n":"动漫","v":"anime"},{"n":"纪录片","v":"documentary"},{"n":"其他","v":"other"}]
        regions=[{"n":"全部","v":""}]+self._vals(d.get("region_stats") or [],"name","key")
        tags=[{"n":"全部","v":""}]+self._vals(d.get("tags") or [],"name","name")
        cats=[{"n":"全部","v":""}]+self._vals(d.get("categories") or [],"name","slug")
        disks=[{"n":"全部","v":""}]+self._vals(d.get("resource_type_stats") or [],"name","key")
        if len(disks)==1: disks+=[{"n":"百度网盘","v":"baidu"},{"n":"115网盘","v":"115"},{"n":"123云盘","v":"123"},{"n":"迅雷云盘","v":"xunlei"},{"n":"夸克网盘","v":"quark"},{"n":"阿里云盘","v":"aliyun"},{"n":"磁力","v":"magnet"}]
        sort=[{"n":"最新","v":"-created_at"},{"n":"最多资源","v":"-resource_count"},{"n":"年份新","v":"-release_year"},{"n":"热度","v":"-views"}]
        f=[{"key":"type","name":"类型","value":types},{"key":"region","name":"国家","value":regions[:80]},{"key":"year","name":"年份","value":years},{"key":"tag","name":"标签","value":tags[:120]},{"key":"category","name":"分类","value":cats[:120]},{"key":"resource_type","name":"网盘","value":disks[:80]},{"key":"ordering","name":"排序","value":sort}]
        return {k:f for k in ["all","movie","tv","anime","documentary","other"]}

    def _vals(self,arr,nk,vk):
        out=[]; seen=set()
        for x in arr:
            n=str(x.get(nk) or x.get("display_name") or x.get("label") or x.get("resource_type_display") or x.get(vk) or "").strip(); v=str(x.get(vk) or x.get("slug") or x.get("key") or x.get("resource_type") or n).strip()
            if n and v and v not in seen: seen.add(v); out.append({"n":n,"v":v})
        return out

    def _vod(self,x):
        return {"vod_id":self._eid("movie",{"id":x.get("id"),"pic":x.get("cover") or x.get("cover_url") or ""}),"vod_name":x.get("title") or "资源","vod_pic":x.get("cover") or x.get("cover_url") or "","vod_remarks":self._remarks(x),"vod_content":x.get("description") or "","vod_tag":"folder"}

    def _remarks(self,x):
        a=[]
        for k in ["movie_type_display","release_year","year","category_name","region"]:
            if x.get(k) and str(x.get(k)) not in a: a.append(str(x.get(k)))
        if x.get("resource_count") is not None: a.append("%s源"%x.get("resource_count"))
        return " / ".join(a[:4])

    def _rtype(self,x):
        t=str(x.get("resource_type") or "other").lower()
        if t=="magnetlink": return "magnet"
        if "123" in t: return "123"
        if "baidu" in t: return "baidu"
        if "xunlei" in t: return "xunlei"
        if "quark" in t: return "quark"
        if "aliyun" in t or "alipan" in t: return "aliyun"
        if "115" in t: return "115"
        if "uc"==t: return "uc"
        if "ed2k" in t: return "ed2k"
        return t or "other"

    def _rname(self,k,x=None):
        return (x or {}).get("resource_type_display") or {"123":"123云盘","baidu":"百度网盘","xunlei":"迅雷云盘","quark":"夸克网盘","aliyun":"阿里云盘","115":"115网盘","uc":"UC网盘","magnet":"磁力","ed2k":"电驴","other":"其他"}.get(k,k)

    def _order(self,groups):
        keys=["baidu","115","123","xunlei","quark","aliyun","uc","magnet","ed2k","other"]
        return [x for x in keys if groups.get(x)]+[x for x in groups.keys() if x not in keys]

    def _h(self):
        h={"User-Agent":self.session.headers.get("User-Agent","Mozilla/5.0"),"Accept":"application/json, text/plain, */*","Content-Type":"application/json","X-Requested-With":"XMLHttpRequest"}
        if self.token: h["X-App-User-Token"]=self.token
        csrf=self.session.cookies.get("csrftoken")
        if csrf: h["X-CSRFToken"]=csrf
        return h

    def _eid(self,typ,data):
        return "jy|%s|%s"%(typ,base64.urlsafe_b64encode(json.dumps(data or {},ensure_ascii=False,separators=(",",":")).encode()).decode().rstrip("="))

    def _pid(self,s):
        a=str(s or "").split("|",2)
        if len(a)>=3 and a[0]=="jy":
            try: return a[1],json.loads(base64.urlsafe_b64decode((a[2]+"="*(-len(a[2])%4)).encode()).decode())
            except Exception: return "",{}
        return "",{}

    def _json(self,s):
        if isinstance(s,dict): return s
        for x in [str(s or "")]:
            try: return json.loads(x) if x.strip().startswith("{") else {}
            except Exception: pass
            try: y=unquote(x); return json.loads(y) if y.strip().startswith("{") else {}
            except Exception: pass
            try: y=base64.b64decode(x+"="*(-len(x)%4)).decode(); return json.loads(y) if y.strip().startswith("{") else {}
            except Exception: pass
        return {}

    def _page(self,pg):
        return int(pg) if str(pg).isdigit() and int(pg)>0 else 1

    def _clean(self,s):
        return re.sub(r"\s+"," ",str(s or "资源")).replace("$","＄").replace("#","＃").strip()[:120]

    def _dedupe(self,arr):
        out=[]; seen=set()
        for x in arr or []:
            k=str(x.get("id") or x.get("share_link") or x.get("title") or x)
            if k and k not in seen: seen.add(k); out.append(x)
        return out
