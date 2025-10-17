# coding=utf-8
# !/usr/bin/python
import sys
import requests
from bs4 import BeautifulSoup
import re
from base.spider import Spider
import json
sys.path.append('..')
xurl = "https://ee55ff.com/video.html"
headerx = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.87 Safari/537.36'
}
class Spider(Spider):
    global xurl
    global headerx

    def getName(self):
        return "首页"

    def init(self, extend):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def homeContent(self, filter):
        # https://yaselulu.autos/?page_id=9

        data = {"name": "John", "age": 31, "city": "New York"}
        res = requests.post('https://spiderscloudcn2.51111666.com/getDataInit', headers=headerx, json=data)
        res.encoding = "utf-8"
        json_dict = json.loads(res.text)
        menu0ListMap = json_dict["data"]["menu0ListMap"]
        result = {}
        result['class'] = []
        for item in menu0ListMap:
            if item['typeName'] == "传媒" or item['typeName'] == "视频" or item['typeName'] == "电影":
                for item1 in item['menu2List']:
                    result['class'].append({'type_id': item1['typeId2'], 'type_name': item1['typeName2']})

        return result

    def homeVideoContent(self):
        videos = []
        try:
            data = {
                "command": "WEB_GET_INFO",
                "pageNumber": 1,
                "RecordsPage": 20,
                "typeId": "24",
                "typeMid": "1",
                "languageType": "CN",
                "content": ""
            }
            res = requests.post('https://spiderscloudcn2.51111666.com/forward', headers=headerx, json=data)
            res.encoding = "utf-8"
            json_dict = json.loads(res.text)
            menu0ListMap = json_dict["data"]["resultList"]
            for item in menu0ListMap:
                name1 = item['vod_name'].replace("yy8ycom", "")
                pattern = r'(.*?)-(.*?)-\d+\s+'
                name = re.sub(pattern, '', name1)
                id = item['id']
                pic = item['vod_pic']
                id2 = item['vod_server_id']

                video = {
                    "vod_id": str(id) + '#' + str(id2),
                    "vod_name": name,
                    "vod_pic": pic,
                    "vod_remarks": ''
                }
                videos.append(video)
            result = {'list': videos}
            return result
        except:
            pass

    def categoryContent(self, cid, pg, filter, ext):
        result = {}
        videos = []
        if not pg:
            pg = 1

        # https://yaselulu.autos/?cat=3754&paged=1

        videos = []
        try:
            data = {
                "command": "WEB_GET_INFO",
                "pageNumber": pg,
                "RecordsPage": 20,
                "typeId": cid,
                "typeMid": "1",
                "languageType": "CN",
                "content": ""
            }
            res = requests.post('https://spiderscloudcn2.51111666.com/forward', headers=headerx, json=data)
            res.encoding = "utf-8"
            json_dict = json.loads(res.text)
            menu0ListMap = json_dict["data"]["resultList"]
            for item in menu0ListMap:
                name1 = item['vod_name'].replace("yy8ycom", "")
                pattern = r'(.*?)-(.*?)-\d+\s+'
                name = re.sub(pattern, '', name1)
                id = item['id']
                pic = item['vod_pic']
                id2 = item['vod_server_id']

                video = {
                    "vod_id": str(id) + '#' + str(id2),
                    "vod_name": name,
                    "vod_pic": pic,
                    "vod_remarks": ''
                }
                videos.append(video)
        except:
            pass

        result['list'] = videos
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        return result

    def detailContent(self, ids):
        l10 = "https://server10.vuljers.com"
        l11 = 'https://server11.vuljers.com'
        l12 = 'https://server12.xylhwdu.com'
        l13 = 'https://server13.benpsbp.com'
        l14 = 'https://server14.connectr.cn'
        did = ids[0]
        cid, svid = did.split("#")
        videos = []
        result = {}
        data = {
            "command": "WEB_GET_INFO_DETAIL",
            "type_Mid": "1",
            "id": cid,
            "languageType": "CN"
        }
        res = requests.post('https://spiderscloudcn2.51111666.com/forward', headers=headerx, json=data)
        res.encoding = "utf-8"
        json_dict = json.loads(res.text)
        if svid == "10":
            purl = l10 + json_dict['data']["result"]["vod_url"]
        elif svid == "11":
            purl = l11 + json_dict['data']["result"]["vod_url"]
        elif svid == "12":
            purl = l12 + json_dict['data']["result"]["vod_url"]
        elif svid == "13":
            purl = l13 + json_dict['data']["result"]["vod_url"]
        elif svid == "14":
            purl = l14 + json_dict['data']["result"]["vod_url"]
        else:
            purl = json_dict['data']["result"]["vod_url"]

        videos.append({
            "vod_id": '',
            "vod_name": '',
            "vod_pic": "",
            "type_name": "ぃぅおか🍬 คิดถึง",
            "vod_year": "",
            "vod_area": "",
            "vod_remarks": "",
            "vod_actor": "",
            "vod_director": "",
            "vod_content": "",
            "vod_play_from": "直链播放",
            "vod_play_url": purl
        })

        result['list'] = videos
        return result

    def playerContent(self, flag, id, vipFlags):
        result = {}
        result["parse"] = 0
        result["playUrl"] = ''
        result["url"] = id
        result["header"] = headerx
        return result

    def searchContentPage(self, key, quick, page):
        # https://yaselulu.autos/?s=%E6%88%91%E7%9A%84&paged=2

        result = {}
        videos = []
        if not page:
            page = 1

        data = {
            "command": "WEB_GET_INFO",
            "pageNumber": page,
            "RecordsPage": 20,
            "typeId": "0",
            "typeMid": "1",
            "languageType": "CN",
            "content": key,
            "type": "1"
        }
        res = requests.post('https://spiderscloudcn2.51111666.com/forward', headers=headerx, json=data)
        res.encoding = "utf-8"
        json_dict = json.loads(res.text)
        menu0ListMap = json_dict["data"]["resultList"]
        for item in menu0ListMap:
            name = item['vod_name'].replace("yy8ycom", "")
            id = item['id']
            pic = item['vod_pic']
            id2 = item['vod_server_id']

            video = {
                "vod_id": str(id) + '#' + str(id2),
                "vod_name": name,
                "vod_pic": pic,
                "vod_remarks": ''
            }
            videos.append(video)

        result['list'] = videos
        result['page'] = page
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        return result
    def searchContent(self, key, quick):
        return self.searchContentPage(key, quick, '1')



    def localProxy(self, params):
        if params['type'] == "m3u8":
            return self.proxyM3u8(params)
        elif params['type'] == "media":
            return self.proxyMedia(params)
        elif params['type'] == "ts":
            return self.proxyTs(params)
        return None
