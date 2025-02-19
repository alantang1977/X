# coding=utf-8
# !/usr/bin/python
import sys

sys.path.append('')
from base.spider import Spider
from urllib.parse import quote

class Spider(Spider):
    def getName(self):
        return "xpg"

    def init(self, extend=""):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    def homeContent(self, filter):
        data = self.fetch(
            "{0}/api.php/v2.vod/androidtypes".format(self.host),
            headers=self.header,
        ).json()
        dy = {
            "classes": "类型",
            "areas": "地区",
            "years": "年份",
            "sortby": "排序",
        }
        filters = {}
        classes = []
        for item in data['data']:
            has_non_empty_field = False
            item['soryby'] = ['updatetime', 'hits', 'score']
            demos = ['时间', '人气', '评分']
            classes.append({"type_name": item["type_name"], "type_id": str(item["type_id"])})
            for key in dy:
                if key in item and len(item[key]) > 1:
                    has_non_empty_field = True
                    break
            if has_non_empty_field:
                filters[str(item["type_id"])] = []
                for dkey in item:
                    if dkey in dy and len(item[dkey]) > 1:
                        values = item[dkey]
                        value_array = [
                            {"n": demos[idx] if dkey == "sortby" else value.strip(), "v": value.strip()}
                            for idx, value in enumerate(values)
                            if value.strip() != ""
                        ]
                        filters[str(item["type_id"])].append(
                            {"key": dkey, "name": dy[dkey], "value": value_array}
                        )
        result = {}
        result["class"] = classes
        result["filters"] = filters
        return result

    host = "http://item.xpgtv.com"
    header = {
        'User-Agent': 'okhttp/3.12.11',
        'token': 'ElEDlwCVgXcFHFhddiq2JKteHofExRBUrfNlmHrWetU3VVkxnzJAodl52N9EUFS+Dig2A/fBa/V9RuoOZRBjYvI+GW8kx3+xMlRecaZuECdb/3AdGkYpkjW3wCnpMQxf8vVeCz5zQLDr8l8bUChJiLLJLGsI+yiNskiJTZz9HiGBZhZuWh1mV1QgYah5CLTbSz8=',
        'token2': 'a0kEsBKRgTkBZ29NZ3WcNKN/C4T00RN/hNkmmGa5JMBeEENnqydLoetm/t8=',
        'user_id': 'XPGBOX',
        'version': 'XPGBOX com.phoenix.tv1.5.3',
        'timestamp': '1732286435',
        'hash': 'd9ab',
    }

    def homeVideoContent(self):
        rsp = self.fetch("{0}/api.php/v2.main/androidhome".format(self.host), headers=self.header)
        root = rsp.json()['data']['list']
        videos = []
        for vodd in root:
            for vod in vodd['list']:
                videos.append({
                    "vod_id": vod['id'],
                    "vod_name": vod['name'],
                    "vod_pic": vod['pic'],
                    "vod_remarks": vod['score']
                })
        result = {
            'list': videos
        }
        return result

    def categoryContent(self, tid, pg, filter, extend):
        parms = []
        parms.append(f"page={pg}")
        parms.append(f"type={tid}")
        if extend.get('areas'):
            parms.append(f"area={quote(extend['areaes'])}")
        if extend.get('years'):
            parms.append(f"year={quote(extend['yeares'])}")
        if extend.get('sortby'):
            parms.append(f"sortby={extend['sortby']}")
        if extend.get('classes'):
            parms.append(f"class={quote(extend['classes'])}")
        parms = "&".join(parms)
        result = {}
        url = '{0}/api.php/v2.vod/androidfilter10086?{1}'.format(self.host, parms)
        rsp = self.fetch(url, headers=self.header)
        root = rsp.json()['data']
        videos = []
        for vod in root:
            videos.append({
                "vod_id": vod['id'],
                "vod_name": vod['name'],
                "vod_pic": vod['pic'],
                "vod_remarks": vod['score']
            })
        result['list'] = videos
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        return result

    def detailContent(self, ids):
        id = ids[0]
        url = '{0}/api.php/v3.vod/androiddetail2?vod_id={1}'.format(self.host, id)
        rsp = self.fetch(url, headers=self.header)
        root = rsp.json()['data']
        node = root['urls']
        d = [it['key'] + "$" + f"http://c.xpgtv.net/m3u8/{it['url']}.m3u8" for it in node]
        vod = {
            "vod_name": root['name'],
            'vod_play_from': '小苹果',
            'vod_play_url': '#'.join(d),
        }
        print(vod)
        result = {
            'list': [
                vod
            ]
        }
        return result

    def searchContent(self, key, quick, pg='1'):
        url = '{0}/api.php/v2.vod/androidsearch10086?page={1}&wd={2}'.format(self.host, pg, key)
        rsp = self.fetch(url, headers=self.header)
        root = rsp.json()['data']
        videos = []
        for vod in root:
            videos.append({
                "vod_id": vod['id'],
                "vod_name": vod['name'],
                "vod_pic": vod['pic'],
                "vod_remarks": vod['score']
            })
        result = {
            'list': videos
        }
        return result

    def playerContent(self, flag, id, vipFlags):
        result = {}
        result["parse"] = 0
        result["url"] = id
        result["header"] = self.header
        return result

    def localProxy(self, param):
        pass


