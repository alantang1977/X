# -*- coding: utf-8 -*-
# 专属全网聚合 Python版
# 适配常见 Cat/TVBox Python Spider
#本地py适配  😂  

import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from base.spider import Spider


class Spider(Spider):
    sources = {
        's1': {'name': '杏吧资源', 'api': 'https://xingba111.com/api.php/provide/vod/'},
        's2': {'name': '极品资源', 'api': 'https://jipinvip1.com/api.php/provide/vod/'},
        's3': {'name': '香蕉资源网', 'api': 'https://www.xiangjiaozyw.com/api.php/provide/vod/'},
        's4': {'name': '番茄资源', 'api': 'https://fqzy.me//api.php/provide/vod/'},
        's5': {'name': '黑料资源', 'api': 'https://heiliaozyapi.com/api.php/seaxml/vod/'},
        's6': {'name': '黄色仓库', 'api': 'https://hsckzy.vip/api.php/provide/vod/'},
        's7': {'name': '奶香香资源', 'api': 'https://naixxzy.com/api.php/provide/vod/'},
        's8': {'name': '桃花资源', 'api': 'https://thzy1.me/api.php/provide/vod/'},
        's9': {'name': 'CK伦理资源', 'api': 'https://ckzy.me/api.php/provide/vod/'},
        's10': {'name': '大奶子资源', 'api': 'https://apidanaizi.com/api.php/provide/vod/'},
        's11': {'name': '搜av资源', 'api': 'https://api.souavzyw.net/api.php/provide/vod/'},
        's12': {'name': '奥斯卡资源', 'api': 'https://aosikazy1.com/api.php/provide/vod/'},
        's13': {'name': '滴滴资源', 'api': 'https://api.ddapi.cc/api.php/provide/vod/at/json/'},
        's14': {'name': '豆豆资源', 'api': 'https://api.douapi.cc/api.php/provide/vod/'},
        's15': {'name': '鲨鱼资源', 'api': 'https://shayuapi.com/api.php/provide/vod/'},
        's16': {'name': '辣椒资源', 'api': 'http://apilj.com/api.php/provide/vod/at/json/'},
        's17': {'name': '森林资源', 'api': 'https://slapibf.com/api.php/provide/vod/'},
        's18': {'name': '155资源', 'api': 'https://155api.com/api.php/provide/vod/'},
        's19': {'name': '乐播资源', 'api': 'https://lbapi9.com/api.php/provide/vod/'},
        's20': {'name': '玉兔资源', 'api': 'https://apiyutu.com/api.php/provide/vod/'},
        's21': {'name': '番号资源', 'api': 'http://fhapi9.com/api.php/provide/vod/'},
        's22': {'name': '精品X资源', 'api': 'https://www.jingpinx.com/api.php/provide/vod/'},
        's23': {'name': 'jkun资源', 'api': 'https://jkunzyapi.com/api.php/provide/vod/'},
    }

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    def getName(self):
        return "影视+专属全网聚合"

    def init(self, extend=""):
        pass

    def fetch(self, url, timeout=8):
        try:
            r = requests.get(
                url,
                headers=self.headers,
                timeout=timeout,
                verify=False
            )
            return r.text
        except Exception:
            return ""

    def clean_item(self, item, source_key, source_name, is_detail=False):
        item = dict(item)

        if not is_detail:
            item["vod_id"] = f"{source_key}@@{item.get('vod_id', '')}"

        remarks = item.get("vod_remarks", "")
        item["vod_remarks"] = f"{source_name} | {remarks}"

        if item.get("vod_play_from"):
            froms = item["vod_play_from"].split("$$$")
            froms = [f"{source_name}-{x}" for x in froms]
            item["vod_play_from"] = "$$$".join(froms)

        item.pop("vod_down_from", None)
        item.pop("vod_down_url", None)

        return item

    def homeContent(self, filter):
        classes = []
        filters = {}

        def load_class(key, source):
            url = f"{source['api']}?ac=list"
            html = self.fetch(url, 4)

            try:
                data = json.loads(html)
            except:
                data = {}

            vals = [{"n": "全部(最新)", "v": ""}]

            for c in data.get("class", []):
                vals.append({
                    "n": c.get("type_name", ""),
                    "v": c.get("type_id", "")
                })

            return key, vals

        with ThreadPoolExecutor(max_workers=16) as executor:
            futures = []

            for key, source in self.sources.items():
                classes.append({
                    "type_id": key,
                    "type_name": source["name"]
                })

                futures.append(executor.submit(load_class, key, source))

            for future in as_completed(futures):
                try:
                    key, vals = future.result()

                    filters[key] = [{
                        "key": "cateId",
                        "name": "分类",
                        "value": vals
                    }]
                except:
                    pass

        return {
            "class": classes,
            "filters": filters,
            "list": []
        }

    def categoryContent(self, tid, pg, filter, extend):
        if tid not in self.sources:
            return {"list": []}

        source = self.sources[tid]

        cate_id = ""
        if isinstance(extend, dict):
            cate_id = extend.get("cateId", "")

        url = f"{source['api']}?ac=detail&pg={pg}"

        if cate_id:
            url += f"&t={cate_id}"

        html = self.fetch(url)

        try:
            data = json.loads(html)
        except:
            data = {}

        result = []

        for item in data.get("list", []):
            result.append(
                self.clean_item(
                    item,
                    tid,
                    source["name"],
                    False
                )
            )

        return {
            "list": result,
            "page": data.get("page", pg),
            "pagecount": data.get("pagecount", 1),
            "limit": data.get("limit", 20),
            "total": data.get("total", len(result))
        }

    def detailContent(self, ids):
        if isinstance(ids, list):
            ids = ids[0]

        if "@@" not in ids:
            return {"list": []}

        source_key, real_id = ids.split("@@", 1)

        if source_key not in self.sources:
            return {"list": []}

        source = self.sources[source_key]

        url = f"{source['api']}?ac=detail&ids={real_id}"

        html = self.fetch(url)

        try:
            data = json.loads(html)
        except:
            data = {}

        result = []

        for item in data.get("list", []):
            cleaned = self.clean_item(
                item,
                source_key,
                source["name"],
                True
            )

            cleaned["vod_id"] = ids

            result.append(cleaned)

        return {"list": result}

    def search_one(self, source_key, source, keyword, pg):
        url = f"{source['api']}?ac=detail&wd={keyword}&pg={pg}"

        html = self.fetch(url, 6)

        try:
            data = json.loads(html)
        except:
            data = {}

        result = []

        for item in data.get("list", []):
            result.append(
                self.clean_item(
                    item,
                    source_key,
                    source["name"],
                    False
                )
            )

        return {
            "list": result,
            "pagecount": data.get("pagecount", 1)
        }

    def searchContent(self, key, quick=False, pg=1):
        result = []
        max_page = 1

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = []

            for source_key, source in self.sources.items():
                futures.append(
                    executor.submit(
                        self.search_one,
                        source_key,
                        source,
                        key,
                        pg
                    )
                )

            for future in as_completed(futures):
                try:
                    data = future.result()

                    result.extend(data["list"])

                    if data["pagecount"] > max_page:
                        max_page = data["pagecount"]

                except:
                    pass

        return {
            "list": result,
            "page": pg,
            "pagecount": max_page,
            "limit": 40,
            "total": 9999
        }

    def playerContent(self, flag, id, vipFlags):
        return {
            "parse": 0,
            "playUrl": "",
            "url": id,
            "header": self.headers
        }

    def localProxy(self, param):
        return [200, "text/plain", "ok"]


if __name__ == "__main__":
    Spider().run()
