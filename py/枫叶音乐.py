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

xurl = "https://fy-musicbox-api.mu-jie.cc"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.87 Safari/537.36'
          }

headerx = {
    "Host": "fy-musicbox-api.mu-jie.cc",
    "Connection": "keep-alive",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
    "sec-ch-ua-platform": '"Windows"',
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0",
    "sec-ch-ua": '"Microsoft Edge";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
    "sec-ch-ua-mobile": "?0",
    "Accept": "*/*",
    "Origin": "https://mu-jie.cc",
    "Sec-Fetch-Site": "same-site",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
    "Referer": "https://mu-jie.cc/",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "Accept-Encoding": "gzip, deflate"
          }

class Spider(Spider):
    global xurl
    global headerx
    global headers

    def getName(self):
        return "首页"

    def init(self, extend):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

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

    def fetch_category_data(self):
        url = f'{xurl}/getPlaylistCategory'
        detail = requests.get(url=url, headers=headerx)
        detail.encoding = "utf-8"
        data = detail.json()
        return data[0]['category']

    def process_category_item(self, vods):
        name = vods['name']
        return {"type_id": name, "type_name": name}

    def process_sub_categories(self, data1):
        sub_result = []
        for vods in data1:
            sub_result.append(self.process_category_item(vods))
        return sub_result

    def process_categories(self, data):
        result_classes = []
        for vod in data:
            data1 = vod['sub']
            result_classes.extend(self.process_sub_categories(data1))
        return result_classes

    def homeContent(self, filter):
        result = {"class": []}
        category_data = self.fetch_category_data()
        result["class"] = self.process_categories(category_data)
        return result

    def homeVideoContent(self):
        pass

    def fetch_playlist_tracks_data(self, playlist_id):
        url = f'{xurl}/meting/?server=netease&type=playlist&id={playlist_id}'
        detail = requests.get(url=url, headers=headerx)
        detail.encoding = "utf-8"
        return detail.json()

    def process_track_item(self, vod):
        name = vod['name']
        id = vod['url']
        pic = vod['pic']
        remark = vod['artist']
        return {
            "vod_id": id,
            "vod_name": name,
            "vod_pic": pic,
            "vod_remarks": remark
                }

    def process_playlist_tracks(self, data):
        videos = []
        for vod in data['tracks']:
            video = self.process_track_item(vod)
            videos.append(video)
        return videos

    def fetch_category_playlists_data(self, cid):
        url = f'{xurl}/netease/playlist/category?type={cid}&limit=60'
        detail = requests.get(url=url, headers=headerx)
        detail.encoding = "utf-8"
        return detail.json()

    def process_category_playlist_item(self, vod):
        name = vod['name']
        id = vod['id']
        pic = vod['coverImgUrl']
        remark = vod['playCount']
        return {
            "vod_id": f"{id}@",
            "vod_name": name,
            "vod_pic": pic,
            "vod_tag": "folder",
            "vod_remarks": f"{remark} 播放量"
               }

    def process_category_playlists(self, data):
        videos = []
        for vod in data:
            video = self.process_category_playlist_item(vod)
            videos.append(video)
        return videos

    def build_category_result(self, videos, pg):
        result = {'list': videos}
        result['page'] = pg
        result['pagecount'] = 1
        result['limit'] = 90
        result['total'] = 999999
        return result

    def split_cid(self, cid):
        return cid.split("@")

    def categoryContent(self, cid, pg, filter, ext):
        videos = []
        if '@' in cid:
            fenge = self.split_cid(cid)
            data = self.fetch_playlist_tracks_data(fenge[0])
            videos = self.process_playlist_tracks(data)
        else:
            data = self.fetch_category_playlists_data(cid)
            videos = self.process_category_playlists(data)
        result = self.build_category_result(videos, pg)
        return result

    def create_video_detail_item(self, did):
        return {
            "vod_id": did,
            "vod_play_from": '音乐专线',
            "vod_play_url": did
               }

    def create_videos_detail_list(self, did):
        videos = []
        video_item = self.create_video_detail_item(did)
        videos.append(video_item)
        return videos

    def build_detail_result(self, videos):
        result = {}
        result['list'] = videos
        return result

    def detailContent(self, ids):
        did = ids[0]
        videos = self.create_videos_detail_list(did)
        result = self.build_detail_result(videos)
        return result

    def get_redirect_location(self, id):
        response = requests.get(url=id, headers=headerx, allow_redirects=False)
        return response.headers.get('Location')

    def build_player_result(self, url):
        result = {}
        result["parse"] = 0
        result["playUrl"] = ''
        result["url"] = url
        result["header"] = headers
        return result

    def playerContent(self, flag, id, vipFlags):
        url = self.get_redirect_location(id)
        result = self.build_player_result(url)
        return result

    def parse_search_page(self, pg):
        if pg:
            return int(pg)
        else:
            return 1

    def fetch_search_data(self, key, page):
        url = f'{xurl}/netease/search/song/?keywords={key}&pn={str(page)}&limit=20'
        detail = requests.get(url=url, headers=headerx)
        detail.encoding = "utf-8"
        return detail.json()

    def process_search_result_item(self, vod):
        name = vod['name']
        id = vod['url']
        pic = vod['pic']
        remark = vod['artist']
        return {
            "vod_id": id,
            "vod_name": name,
            "vod_pic": pic,
            "vod_remarks": remark
               }

    def process_search_results_list(self, data):
        videos = []
        for vod in data:
            video = self.process_search_result_item(vod)
            videos.append(video)
        return videos

    def build_search_result(self, videos, pg):
        result = {}
        result['list'] = videos
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        return result

    def searchContentPage(self, key, quick, pg):
        page = self.parse_search_page(pg)
        data = self.fetch_search_data(key, page)
        videos = self.process_search_results_list(data)
        result = self.build_search_result(videos, pg)
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








