# coding=utf-8
# !/usr/bin/python

"""

作者 丢丢喵 🚓 内容均从互联网收集而来 仅供交流学习使用 版权归原创者所有 如侵犯了您的权益 请通知作者 将及时删除侵权内容
                    ====================Diudiumiao====================

"""

from Crypto.Util.Padding import unpad
from Crypto.Util.Padding import pad
from urllib.parse import unquote
from Crypto.Cipher import ARC4
from urllib.parse import quote
from base.spider import Spider
from Crypto.Cipher import AES
from datetime import datetime
from bs4 import BeautifulSoup
from base64 import b64decode
import urllib.request
import urllib.parse
import datetime
import binascii
import requests
import base64
import json
import time
import sys
import re
import os

sys.path.append('..')

xurl = "https://nnyy.la"

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

    def split_id_by_at(self, id):
        return id.split("@")

    def split_first_part_by_comma(self, first_part):
        return first_part.split(",")

    def parse_url_dictionary(self, response_text):
        pattern = r'urlDictionary\[(\d+)\]\[(\d+)\]\s*=\s*"([^"]+)"'
        matches = re.findall(pattern, response_text)
        url_dictionary = {}
        for key1, key2, value in matches:
            key1_int = int(key1)
            key2_int = int(key2)
            if key1_int not in url_dictionary:
                url_dictionary[key1_int] = {}
            url_dictionary[key1_int][key2_int] = value
        return url_dictionary

    def get_url_from_dictionary(self, url_dictionary, indices):
        primary_index = int(indices[0].strip())
        secondary_index = int(indices[1].strip())
        return url_dictionary[primary_index][secondary_index]

    def decrypt_url(self, encrypted_hex, key="i_love_you"):
        encrypted_bytes = bytes.fromhex(encrypted_hex)
        s = list(range(256))
        j = 0
        key_bytes = key.encode('utf-8')
        key_length = len(key_bytes)
        for i in range(256):
            j = (j + s[i] + key_bytes[i % key_length]) % 256
            s[i], s[j] = s[j], s[i]
        i = 0
        j = 0
        decrypted_bytes = bytearray(len(encrypted_bytes))
        for k in range(len(encrypted_bytes)):
            i = (i + 1) % 256
            j = (j + s[i]) % 256
            s[i], s[j] = s[j], s[i]
            keystream_byte = s[(s[i] + s[j]) % 256]
            decrypted_bytes[k] = encrypted_bytes[k] ^ keystream_byte
        return decrypted_bytes.decode('utf-8')

    def _extract_play_sources(self, soups):
        xianlu = ''
        for item in soups:
            vods = item.find_all('dt')
            for sou in vods:
                name = sou.text.strip()
                xianlu = xianlu + name + '$$$'
            xianlu = xianlu[:-3]
        return xianlu

    def _extract_play_urls(self, soups1, did):
        bofang = ''
        for item in soups1:
            vods1 = item.find_all('a')
            for sou1 in vods1:
                id1 = sou1['onclick']
                numbers = re.findall(r'\((.*?)\)', id1)[0] if re.findall(r'\((.*?)\)', id1) else ""
                id = f"{numbers}@{did}"
                name = sou1.text.strip()
                bofang = bofang + name + '$' + id + '#'
            bofang = bofang[:-1] + '$$$'
        bofang = bofang[:-3]
        return bofang

    def _extract_content(self, res):
        content_raw = self.extract_middle_text(res, '剧情简介：<span>', '<', 0).replace('\n', '')
        return '😸丢丢为您介绍剧情📢' + (content_raw if content_raw is not None else "暂无剧情介绍")

    def _extract_director(self, res):
        director_raw = self.extract_middle_text(res, '导演：', '</div>', 1, 'href=".*?">(.*?)</a>')
        return director_raw if director_raw is not None and director_raw.strip() != "" else "暂无导演介绍"

    def _extract_actor(self, res):
        actor_raw = self.extract_middle_text(res, '主演：', '</div>', 1, 'href=".*?">(.*?)</a>')
        return actor_raw if actor_raw is not None and actor_raw.strip() != "" else "暂无主演介绍"

    def _extract_remarks(self, res):
        remarks_raw = self.extract_middle_text(res, '类型：', '</div>', 1, 'href=".*?">(.*?)</a>')
        return remarks_raw if remarks_raw is not None and remarks_raw.strip() != "" else "暂无类型介绍"

    def _extract_area(self, res):
        area_raw = self.extract_middle_text(res, '制片国家/地区：', '</div>', 1, 'href=".*?">(.*?)</a>')
        return area_raw if area_raw is not None and area_raw.strip() != "" else "暂无国家/地区介绍"

    def _extract_year(self, doc):
        years = doc.find('h1', class_="product-title")
        year = years.text.strip() if years else '暂无年份介绍'
        return year.replace('\n', '打分：')

    def _extract_video_items(self, vods):
        videos = []
        for vod in vods:
            name = vod.find('img')['alt']
            ids = vod.find('a', class_="thumbnail")
            id = ids['href']
            pic = vod.find('img')['data-src']
            remarks = vod.find('div', class_="note")
            remark = remarks.text.strip()
            video = {
                "vod_id": id,
                "vod_name": name,
                "vod_pic": pic,
                "vod_remarks": remark
                    }
            videos.append(video)
        return videos

    def extract_middle_text(self, text, start_str, end_str, pl, start_index1: str = '', end_index2: str = ''):
        if pl == 3:
            plx = []
            while True:
                start_index = text.find(start_str)
                if start_index == -1:
                    break
                end_index = text.find(end_str, start_index + len(start_str))
                if end_index == -1:
                    break
                middle_text = text[start_index + len(start_str):end_index]
                plx.append(middle_text)
                text = text.replace(start_str + middle_text + end_str, '')
            if len(plx) > 0:
                purl = ''
                for i in range(len(plx)):
                    matches = re.findall(start_index1, plx[i])
                    output = ""
                    for match in matches:
                        match3 = re.search(r'(?:^|[^0-9])(\d+)(?:[^0-9]|$)', match[1])
                        if match3:
                            number = match3.group(1)
                        else:
                            number = 0
                        if 'http' not in match[0]:
                            output += f"#{match[1]}${number}{xurl}{match[0]}"
                        else:
                            output += f"#{match[1]}${number}{match[0]}"
                    output = output[1:]
                    purl = purl + output + "$$$"
                purl = purl[:-3]
                return purl
            else:
                return ""
        else:
            start_index = text.find(start_str)
            if start_index == -1:
                return ""
            end_index = text.find(end_str, start_index + len(start_str))
            if end_index == -1:
                return ""

        if pl == 0:
            middle_text = text[start_index + len(start_str):end_index]
            return middle_text.replace("\\", "")

        if pl == 1:
            middle_text = text[start_index + len(start_str):end_index]
            matches = re.findall(start_index1, middle_text)
            if matches:
                jg = ' '.join(matches)
                return jg

        if pl == 2:
            middle_text = text[start_index + len(start_str):end_index]
            matches = re.findall(start_index1, middle_text)
            if matches:
                new_list = [f'{item}' for item in matches]
                jg = '$$$'.join(new_list)
                return jg

    def homeContent(self, filter):
        result = {"class": []}

        detail = requests.get(url=xurl, headers=headerx)
        detail.encoding = "utf-8"
        res = detail.text
        doc = BeautifulSoup(res, "lxml")
        
        soups = doc.find_all('div', class_="nav")

        for soup in soups:
            vods = soup.find_all('a')

            for vod in vods:

                name = vod.text.strip()

                skip_names = ["首页"]
                if name in skip_names:
                    continue

                id = vod['href'].replace('/', '')

                result["class"].append({"type_id": id, "type_name": name})

        result["class"].append({"type_id": "duanju", "type_name": "短剧"})

        return result

    def homeVideoContent(self):
        videos = []

        detail = requests.get(url=xurl, headers=headerx)
        detail.encoding = "utf-8"
        res = detail.text
        doc = BeautifulSoup(res, "lxml")

        soups = doc.find('div', class_="bd")

        vods = soups.find_all('li')

        videos = self._extract_video_items(vods)

        result = {'list': videos}
        return result

    def categoryContent(self, cid, pg, filter, ext):
        result = {}
        videos = []

        if pg:
            page = int(pg)
        else:
            page = 1

        url = f'{xurl}/{cid}/?page={str(page)}'
        detail = requests.get(url=url, headers=headerx)
        detail.encoding = "utf-8"
        res = detail.text
        doc = BeautifulSoup(res, "lxml")

        soups = doc.find_all('div', class_="lists-content")

        for soup in soups:
            vods = soup.find_all('li')

            videos = self._extract_video_items(vods)

        result = {'list': videos}
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        return result

    def detailContent(self, ids):
        did = ids[0]
        result = {}
        videos = []

        if 'http' not in did:
            did = xurl + did

        detail = requests.get(url=did, headers=headerx)
        detail.encoding = "utf-8"
        res = detail.text
        doc = BeautifulSoup(res, "lxml")

        content = self._extract_content(res)

        director = self._extract_director(res)

        actor = self._extract_actor(res)

        remarks = self._extract_remarks(res)

        area = self._extract_area(res)

        year = self._extract_year(doc)

        soups = doc.find_all('div', class_="playlists")
        xianlu = self._extract_play_sources(soups)

        soups1 = doc.find_all('ul', class_="sort-list")
        bofang = self._extract_play_urls(soups1, did)

        videos.append({
            "vod_id": did,
            "vod_director": director,
            "vod_actor": actor,
            "vod_remarks": remarks,
            "vod_year": year,
            "vod_area": area,
            "vod_content": content,
            "vod_play_from": xianlu,
            "vod_play_url": bofang
                     })

        result['list'] = videos
        return result

    def playerContent(self, flag, id, vipFlags):

        fenge = self.split_id_by_at(id)

        fenge1 = self.split_first_part_by_comma(fenge[0])

        detail = requests.get(url=fenge[1], headers=headerx)
        detail.encoding = "utf-8"
        res = detail.text

        url_dictionary = self.parse_url_dictionary(res)

        result = self.get_url_from_dictionary(url_dictionary, fenge1)

        url = self.decrypt_url(result)

        result = {}
        result["parse"] = 0
        result["playUrl"] = ''
        result["url"] = url
        result["header"] = headerx
        return result

    def searchContentPage(self, key, quick, pg):
        result = {}
        videos = []

        url = f'{xurl}/search?wd={key}'
        detail = requests.get(url=url, headers=headerx)
        detail.encoding = "utf-8"
        res = detail.text
        doc = BeautifulSoup(res, "lxml")

        soups = doc.find_all('div', class_="lists-content")

        for item in soups:
            vods = item.find_all('li')

            videos = self._extract_video_items(vods)

        result['list'] = videos
        result['page'] = pg
        result['pagecount'] = 1
        result['limit'] = 90
        result['total'] = 999999
        return result

    def searchContent(self, key, quick, pg="1"):
        return self.searchContentPage(key, quick, '1')

    def localProxy(self, params):
        if params['type'] == "m3u8":
            return self.proxyM3u8(params)
        elif params['type'] == "media":
            return self.proxyMedia(params)
        elif params['type'] == "ts":
            return self.proxyTs(params)
        return None








