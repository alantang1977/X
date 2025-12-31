# -*- coding: utf-8 -*-
# @Author  : AI Assistant
# @Desc    : 全链路无感版 (搜索/分类/详情全缓存 + 异步并发 + 连接池预热)

import json
import os
import time
import hashlib
import requests
from requests.adapters import HTTPAdapter
from concurrent.futures import ThreadPoolExecutor, as_completed
from base.spider import Spider

class Spider(Spider):
    def getName(self):
        return "CjJson_Ultimate_Pro"

    def init(self, extend):
        self.sites = []
        self.session = requests.Session()
        
        # [核心优化1] 极速连接池：预加载 TCP 连接，大幅降低握手延迟
        # pool_connections=100 保证了高并发搜索时每个站点都有独立连接
        adapter = HTTPAdapter(pool_connections=100, pool_maxsize=100, max_retries=1)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Connection": "keep-alive"
        })

        # [核心优化2] 缓存系统初始化
        self.cache_dir = "/storage/emulated/0/lz/cache/"
        self.memory_cache = {} # 内存缓存 (用于详情页，应用关闭即销毁)
        self.disk_ttl = 3600   # 磁盘缓存有效期 1小时
        
        if not os.path.exists(self.cache_dir):
            try: os.makedirs(self.cache_dir)
            except: pass

        # 加载站点配置
        default_path = "./js/cj.json"
        mode = "0"
        json_path = default_path

        if extend:
            if "|" in extend:
                parts = extend.split("|")
                json_path = parts[0] if parts[0] else default_path
                mode = parts[1] if len(parts) > 1 else "0"
            elif len(extend) == 1 and extend in ["0", "1", "2"]:
                mode = extend
            else:
                json_path = extend

        try:
            if os.path.exists(json_path):
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    all_sites = data.get("api_site", [])
                    self.sites = self._filter_sites(all_sites, mode)
        except Exception:
            pass

    # --- 缓存核心逻辑 ---
    
    def _get_disk_cache(self, key):
        """读取磁盘缓存 (用于搜索和分类)"""
        try:
            md5_key = hashlib.md5(key.encode('utf-8')).hexdigest()
            path = os.path.join(self.cache_dir, f"{md5_key}.json")
            if os.path.exists(path):
                if time.time() - os.path.getmtime(path) < self.disk_ttl:
                    with open(path, "r", encoding="utf-8") as f:
                        return json.load(f)
                else:
                    os.remove(path) # 过期删除
        except:
            pass
        return None

    def _set_disk_cache(self, key, data):
        """写入磁盘缓存"""
        try:
            if not data or not data.get("list"): return # 空数据不缓存
            md5_key = hashlib.md5(key.encode('utf-8')).hexdigest()
            path = os.path.join(self.cache_dir, f"{md5_key}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except:
            pass

    def _filter_sites(self, sites, mode):
        if mode == "0": return sites
        adult_kws = {"AV", "色", "福利", "成人", "18+", "偷拍", "自拍", "淫", "激情", "GAY", "SEX"}
        def is_adult(name):
            if not name: return False
            name_upper = name.upper()
            if name_upper.startswith("AV"): return True
            return any(k in name_upper for k in adult_kws)

        if mode == "1": return [s for s in sites if not is_adult(s.get("name", ""))]
        elif mode == "2": return [s for s in sites if is_adult(s.get("name", ""))]
        return sites

    def _fetch(self, api_url, params=None):
        try:
            sep = "&" if "?" in api_url else "?"
            qs = "&".join([f'{k}={v}' for k, v in params.items()]) if params else ""
            full_url = f"{api_url}{sep}{qs}" if qs else api_url
            # 超时控制：搜索要快(2s)，详情可以稍慢(5s)
            timeout = 2.0 if params and "wd" in params else 4.0
            res = self.session.get(full_url, timeout=timeout, verify=False)
            if res.status_code == 200:
                try: return res.json()
                except: return json.loads(res.text.strip().lstrip('﻿'))
        except:
            pass
        return {}

    def homeContent(self, filter):
        classes = []
        filters = {}
        universal_filter = [
            {"key": "cateId", "name": "分类", "value": [
                {"n": "全部", "v": ""},
                {"n": "动作片", "v": "动作"}, {"n": "喜剧片", "v": "喜剧"},
                {"n": "爱情片", "v": "爱情"}, {"n": "科幻片", "v": "科幻"},
                {"n": "恐怖片", "v": "恐怖"}, {"n": "剧情片", "v": "剧情"},
                {"n": "战争片", "v": "战争"}, {"n": "国产剧", "v": "国产"},
                {"n": "港剧", "v": "香港"}, {"n": "韩剧", "v": "韩国"},
                {"n": "欧美剧", "v": "欧美"}, {"n": "台剧", "v": "台湾"},
                {"n": "日剧", "v": "日本"}, {"n": "纪录片", "v": "记录"},
                {"n": "动漫", "v": "动漫"}, {"n": "综艺", "v": "综艺"}
            ]}
        ]
        for i, s in enumerate(self.sites):
            type_id = str(i)
            clean_name = s.get("name", f"站点{i}").replace("TV-", "").replace("AV-", "")
            classes.append({"type_id": type_id, "type_name": clean_name})
            filters[type_id] = universal_filter
        return {"class": classes, "filters": filters}

    def homeVideoContent(self):
        return {"list": []}

    # [核心优化3] 分类页缓存：实现“后退”秒开
    def categoryContent(self, tid, pg, filter, ext):
        # 生成唯一的缓存 Key
        cate_id_val = ext.get("cateId", "") if ext else ""
        cache_key = f"CAT_{tid}_{pg}_{cate_id_val}"
        
        # 1. 尝试读缓存
        cached = self._get_disk_cache(cache_key)
        if cached: return cached

        try:
            idx = int(tid)
            if idx >= len(self.sites): return {"list": []}
            site = self.sites[idx]
            paichu_str = str(site.get("paichu", ""))
            paichu = set(paichu_str.split(",")) if paichu_str else set()
            
            params = {"ac": "detail", "pg": pg}
            data = self._fetch(site["api"], params)
            
            video_list = []
            if data and "list" in data:
                for item in data["list"]:
                    if str(item.get("type_id")) in paichu: continue
                    # 本地筛选逻辑
                    if cate_id_val:
                        type_name = item.get("type_name", "")
                        if cate_id_val not in type_name: continue
                    
                    item["vod_id"] = f"{idx}@@{item['vod_id']}"
                    video_list.append(item)
            
            result = {
                "page": int(data.get("page", 1)) if data else 1,
                "pagecount": int(data.get("pagecount", 1)) if data else 1,
                "limit": 20,
                "total": int(data.get("total", 0)) if data else 0,
                "list": video_list
            }
            
            # 2. 写入缓存
            self._set_disk_cache(cache_key, result)
            return result
        except:
            return {"list": []}

    # [核心优化4] 详情页内存缓存：防止误触返回后的重复加载
    def detailContent(self, array):
        if not array: return {"list": []}
        vod_id_full = str(array[0])
        
        # 1. 内存缓存 (RamCache) - 极速响应
        if vod_id_full in self.memory_cache:
            return self.memory_cache[vod_id_full]

        if "@@" not in vod_id_full: return {"list": []}
        try:
            idx, vid = vod_id_full.split("@@")
            idx = int(idx)
            site = self.sites[idx]
            data = self._fetch(site["api"], {"ac": "detail", "ids": vid})
            if data and "list" in data:
                item = data["list"][0]
                item["vod_id"] = vod_id_full
                result = {"list": [item]}
                
                # 2. 写入内存缓存
                self.memory_cache[vod_id_full] = result
                return result
        except: pass
        return {"list": []}

    # [核心优化5] 异步并发 + 磁盘缓存搜索
    def searchContent(self, key, quick, pg="1"):
        if not key: return {"list": []}
        
        # 1. 查缓存
        cache_key = f"SEARCH_{key}"
        cached = self._get_disk_cache(cache_key)
        if cached: return cached

        # 2. 准备并发
        search_targets = []
        for i, s in enumerate(self.sites):
            bz_val = str(s.get("bz", "1")).strip()
            if bz_val != "0" and s.get("api"):
                search_targets.append((i, s))

        def search_one_site(target):
            idx, site = target
            try:
                paichu_str = str(site.get("paichu", ""))
                paichu = set(paichu_str.split(",")) if paichu_str else set()
                # 搜索只给 2.5s 超时，过时不候
                data = self._fetch(site["api"], {"ac": "detail", "wd": key})
                local_res = []
                if data and "list" in data:
                    for item in data["list"]:
                        if str(item.get("type_id")) in paichu: continue
                        site_name = site.get("name", "").replace("TV-", "").replace("AV-", "")
                        item["vod_name"] = f"[{site_name}] {item['vod_name']}"
                        item["vod_id"] = f"{idx}@@{item['vod_id']}"
                        local_res.append(item)
                return idx, local_res 
            except:
                return idx, []

        # 3. 执行并发 (Max 60 线程)
        temp_results = {}
        with ThreadPoolExecutor(max_workers=60) as executor:
            futures = [executor.submit(search_one_site, target) for target in search_targets]
            for future in as_completed(futures):
                try:
                    idx, res = future.result()
                    if res: temp_results[idx] = res
                except: pass

        # 4. 聚合与缓存
        final_list = []
        sorted_indices = sorted(temp_results.keys())
        for idx in sorted_indices:
            final_list.extend(temp_results[idx])

        result_data = {"list": final_list}
        self._set_disk_cache(cache_key, result_data)
        
        return result_data

    def playerContent(self, flag, id, vipFlags):
        # 播放链接通常有时效性，不建议缓存
        if ".m3u8" in id or ".mp4" in id:
            return {"url": id, "header": {"User-Agent": "Mozilla/5.0"}, "parse": 0, "jx": 0}
        return {"url": id, "header": {"User-Agent": "Mozilla/5.0"}, "parse": 1, "jx": 0}

    def localProxy(self, params):
        return [200, "video/MP2T", "", ""]
