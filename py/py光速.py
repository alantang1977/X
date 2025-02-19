# coding=utf-8
# !/usr/bin/python
# by嗷呜
import re
import sys
from urllib.parse import quote

from Crypto.Hash import MD5

sys.path.append("..")
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from base64 import b64encode, b64decode
import json
import time
from base.spider import Spider


class Spider(Spider):

    def getName(self):
        return "光速"

    def init(self, extend=""):
        self.host = self.gethost()
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def action(self, action):
        pass

    def destroy(self):
        pass

    def homeContent(self, filter):
        data = self.getdata("/api.php/getappapi.index/initV119")
        dy = {"class": "类型", "area": "地区", "lang": "语言", "year": "年份", "letter": "字母", "by": "排序",
              "sort": "排序", }
        filters = {}
        classes = []
        json_data = data["type_list"]
        homedata = data["banner_list"]
        for item in json_data:
            if item["type_name"] == "全部":
                continue
            has_non_empty_field = False
            jsontype_extend = json.loads(item["type_extend"])
            homedata.extend(item["recommend_list"])
            jsontype_extend["sort"] = "最新,最热,最赞"
            classes.append({"type_name": item["type_name"], "type_id": item["type_id"]})
            for key in dy:
                if key in jsontype_extend and jsontype_extend[key].strip() != "":
                    has_non_empty_field = True
                    break
            if has_non_empty_field:
                filters[str(item["type_id"])] = []
                for dkey in jsontype_extend:
                    if dkey in dy and jsontype_extend[dkey].strip() != "":
                        values = jsontype_extend[dkey].split(",")
                        value_array = [{"n": value.strip(), "v": value.strip()} for value in values if
                                       value.strip() != ""]
                        filters[str(item["type_id"])].append({"key": dkey, "name": dy[dkey], "value": value_array})
        result = {}
        result["class"] = classes
        result["filters"] = filters
        result["list"] = homedata
        return result

    def homeVideoContent(self):
        pass

    def categoryContent(self, tid, pg, filter, extend):
        body = {"area": extend.get('area', '全部'), "year": extend.get('year', '全部'), "type_id": tid, "page": pg,
                "sort": extend.get('sort', '最新'), "lang": extend.get('lang', '全部'),
                "class": extend.get('class', '全部')}
        result = {}
        data = self.getdata("/api.php/getappapi.index/typeFilterVodList", body)
        result["list"] = data["recommend_list"]
        result["page"] = pg
        result["pagecount"] = 9999
        result["limit"] = 90
        result["total"] = 999999
        return result

    def detailContent(self, ids):
        body = f"vod_id={ids[0]}"
        data = self.getdata("/api.php/getappapi.index/vodDetail", body)
        vod = data["vod"]

        play = []
        names = []
        for itt in data["vod_play_list"]:
            a = []
            names.append(itt["player_info"]["show"])
            parse = itt["player_info"]["parse"]
            ua = ''
            if itt["player_info"].get("user_agent", ''):
                ua = b64encode(itt["player_info"]["user_agent"].encode('utf-8')).decode('utf-8')
            for it in itt["urls"]:
                url = it["url"]
                if not re.search(r'\.m3u8|\.mp4', url):
                    url = parse + '@@' + url
                url = b64encode(url.encode('utf-8')).decode('utf-8')
                a.append(f"{it['name']}${url}|||{ua}|||{it['token']}")
            play.append("#".join(a))
        vod["vod_play_from"] = "$$$".join(names)
        vod["vod_play_url"] = "$$$".join(play)
        result = {"list": [vod]}
        return result

    def searchContent(self, key, quick, pg="1"):
        body = f"keywords={key}&type_id=0&page={pg}"
        data = self.getdata("/api.php/getappapi.index/searchList", body)
        result = {"list": data["search_list"], "page": pg}
        return result

    phend = {
        'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 11; M2012K10C Build/RP1A.200720.011)'}

    def playerContent(self, flag, id, vipFlags):
        ids = id.split("|||")
        if ids[1]: self.phend['User-Agent'] = b64decode(ids[1]).decode('utf-8')
        url = b64decode(ids[0]).decode('utf-8')
        if not re.search(r'\.m3u8|\.mp4', url):
            a = url.split("@@")
            body = f"parse_api={a[0]}&url={quote(self.aes('encrypt', a[1]))}&token={ids[-1]}"
            jd = self.getdata("/api.php/getappapi.index/vodParse", body)['json']
            url = json.loads(jd)['url']
            # if '.mp4' not in url:
            #     l=self.fetch(url, headers=self.phend,allow_redirects=False)
            #     if l.status_code == 200 and l.headers.get('Location',''):
            #         url=l.headers['Location']
        if '.jpg' in url or '.png' in url or '.jpeg' in url:
            url = self.getProxyUrl() + "&url=" + b64encode(url.encode('utf-8')).decode('utf-8') + "&type=m3u8"
        result = {}
        result["parse"] = 0
        result["url"] = url
        result["header"] = self.phend
        return result

    def localProxy(self, param):
        url = b64decode(param["url"]).decode('utf-8')
        durl = url[:url.rfind('/')]
        data = self.fetch(url, headers=self.phend).content.decode("utf-8")
        inde = None
        pd = True
        lines = data.strip().split('\n')
        for index, string in enumerate(lines):
            # if '#EXT-X-DISCONTINUITY' in string and pd:
            #     pd = False
            #     inde = index
            if '#EXT' not in string and 'http' not in string:
                lines[index] = durl + ('' if string.startswith('/') else '/') + string
        if inde:
            del lines[inde:inde + 4]
        data = '\n'.join(lines)
        return [200, "application/vnd.apple.mpegur", data]

    def gethost(self):
        host = self.fetch('https://jingyu-1312635929.cos.ap-nanjing.myqcloud.com/1.json').text.strip()
        return host

    def aes(self, operation, text):
        key = "4d83b87c4c5ea111".encode("utf-8")
        iv = key
        if operation == "encrypt":
            cipher = AES.new(key, AES.MODE_CBC, iv)
            ct_bytes = cipher.encrypt(pad(text.encode("utf-8"), AES.block_size))
            ct = b64encode(ct_bytes).decode("utf-8")
            return ct
        elif operation == "decrypt":
            cipher = AES.new(key, AES.MODE_CBC, iv)
            pt = unpad(cipher.decrypt(b64decode(text)), AES.block_size)
            return pt.decode("utf-8")

    def header(self):
        t = str(int(time.time()))
        md5_hash = MD5.new()
        md5_hash.update(t.encode('utf-8'))
        signature_md5 = md5_hash.hexdigest()
        header = {"User-Agent": "okhttp/3.14.9", "app-version-code": "300", "app-ui-mode": "light",
                  "app-user-device-id": signature_md5, "app-api-verify-time": t,
                  "app-api-verify-sign": self.aes("encrypt", t), "Content-Type": "application/x-www-form-urlencoded"}
        return header

    def getdata(self, path, data=None):
        # data = self.post(self.host + path, headers=self.header(), data=data).text
        data = self.post(self.host + path, headers=self.header(), data=data, verify=False).json()["data"]
        data1 = self.aes("decrypt", data)
        return json.loads(data1)
