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
import html
import json
import time
import sys
import re
import os

sys.path.append('..')

xurl = "https://music.163.com"

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
        pass

    def fetch_toplist_data(self):
        detail = requests.get(url=xurl + "/discover/toplist", headers=headerx)
        detail.encoding = "utf-8"
        return detail.text

    def parse_video_items(self, html_content):
        doc = BeautifulSoup(html_content, "lxml")
        soups = doc.find_all('ul', class_="f-cb")
        videos = []
        for soup in soups:
            vods = soup.find_all('li')
            for vod in vods:
                video = self.extract_video_info(vod)
                if video:
                    videos.append(video)
        return videos

    def extract_video_info(self, vod_item):
        names = vod_item.find('p', class_="name")
        if names is None:
            return None
        name = names.text.strip()
        id = names.find('a')['href']
        pic = vod_item.find('img')['src']
        pic = pic.replace('40y40', '150y150')
        remarks = vod_item.find('p', class_="s-fc4")
        remark = remarks.text.strip()
        return {
            "vod_id": id,
            "vod_name": name,
            "vod_pic": pic,
            "vod_remarks": remark
               }

    def homeVideoContent(self):
        html_content = self.fetch_toplist_data()
        videos = self.parse_video_items(html_content)
        result = {'list': videos}
        return result

    def categoryContent(self, cid, pg, filter, ext):
        pass

    def fetch_detail_data(self, did):
        url = f'{xurl}{did}'
        detail = requests.get(url=url, headers=headerx)
        detail.encoding = "utf-8"
        return detail.text

    def parse_song_list_data(self, html_content):
        doc = BeautifulSoup(html_content, "lxml")
        soups = doc.find_all('textarea', id="song-list-pre-data")
        json_text = soups[0].get_text()
        return json.loads(json_text)

    def format_play_url(self, json_data):
        bofang = ''
        for vod in json_data:
            remarkMV = vod['mvid']
            remarkMV = "MP3" if remarkMV in [0, "0"] else "MV"
            name = f"{vod['name']} {remarkMV}"
            id = vod['id']
            bofang = bofang + name + '$' + str(id) + '#'
        return bofang[:-1]

    def build_video_info(self, did, play_url):
        xianlu = '网易云音乐'
        videos = []
        videos.append({
            "vod_id": did,
            "vod_play_from": xianlu,
            "vod_play_url": play_url
                      })
        return videos

    def detailContent(self, ids):
        did = ids[0]
        result = {}
        html_content = self.fetch_detail_data(did)
        json_data = self.parse_song_list_data(html_content)
        bofang = self.format_play_url(json_data)
        videos = self.build_video_info(did, bofang)
        result['list'] = videos
        return result

    def fetch_player_data(self, id):
        url = f'https://api.cenguigui.cn/api/netease/music_v1.php?id={id}&type=json&level=standard'
        detail = requests.get(url=url, headers=headerx)
        detail.encoding = "utf-8"
        return detail.json()

    def extract_mv_url(self, data):
        result_data = data.get('data', {})
        mv_info = result_data.get('mv_info', {})
        return mv_info.get('mv', '')

    def extract_audio_url(self, data):
        result_data = data.get('data', {})
        return result_data.get('url', '')

    def determine_play_url(self, mv_url, audio_url):
        if mv_url and mv_url != '未知mv':
            return mv_url
        else:
            return audio_url

    def build_player_result(self, url):
        result = {}
        result["parse"] = 0
        result["playUrl"] = ''
        result["url"] = url
        result["header"] = headerx
        return result

    def playerContent(self, flag, id, vipFlags):
        data = self.fetch_player_data(id)
        mv_url = self.extract_mv_url(data)
        audio_url = self.extract_audio_url(data)
        play_url = self.determine_play_url(mv_url, audio_url)
        result = self.build_player_result(play_url)
        return result

    def searchContentPage(self, key, quick, pg):
        pass

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








