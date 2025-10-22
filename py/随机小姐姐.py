# coding=utf-8
# !/usr/bin/python
import sys
import requests
import datetime
from bs4 import BeautifulSoup
import re
import base64
from base.spider import Spider
import json

sys.path.append('..')
xurl = "http://xjj2.716888.xyz"
headerx = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.87 Safari/537.36',
    'Cookie':'mk_encrypt_c21f969b5f03d33d43e04f8f136e7682=390e11f0d5ae13b2787e6a72db11527f'
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

    def homeVideoContent(self):
        id = ['4k/4k.php', 'djxjj/dj1.php', 'zj/jipinyz/jipinyz.php', 'zj/xuejie/xuejie.php', 'zj/kawayi/kawayi.php',
              'zj/nennen/nennen.php', 'zj/heji1/heji1.php', 'zj/sihuawd/sihuawd.php', 'zj/wanmeisc/wanmeisc.php',
              'zj/manyao/manyao.php', 'zj/sihuadd/sihuadd.php', 'zj/qingchun/qingchun.php', 'zj/cos/cos.php',
              'zj/jingpinbz/jingpinbz.php', 'zj/jipinll/jipinll.php', 'zj/nideym/nideym.php', 'zj/tianmei/tianmei.php',
              'zj/yusi/yusi.php', 'zj/shuaige/shuaige.php', 'zj/rewu/rewu.php', 'zj/jingpinsc/jingpinsc.php']
        name = ['随机', 'DJ姐姐', '极品钰足', '学姐系列', '卡哇伊', '嫩嫩系列', '美女舞蹈', '丝滑舞蹈', '完美身材',
                '慢摇系列', '丝滑吊带', '清纯系列', 'COS系列', '精品变装', '极品罗丽', '你的裕梦', '甜妹系列',
                '御丝系列', '帅哥哥', '热舞系列', '精品收藏']
        pic = ['https://img0.baidu.com/it/u=2236794495,926227820&fm=253&fmt=auto&app=138&f=JPEG?w=1091&h=500',
               'https://pic.rmb.bdstatic.com/mvideo/e17d86ce4489a02870ace9a25a804c3e',
               'https://img1.baidu.com/it/u=4087009209,613234683&fm=253&fmt=auto&app=138&f=JPEG?w=500&h=364',
               'https://img1.baidu.com/it/u=2347706654,3055017263&fm=253&fmt=auto&app=138&f=JPEG?w=500&h=750',
               'https://img2.baidu.com/it/u=3715511725,1094436549&fm=253&fmt=auto&app=138&f=JPEG?w=500&h=1083',
               'https://img2.baidu.com/it/u=2560410906,3760952489&fm=253&fmt=auto&app=138&f=JPEG?w=500&h=750',
               'https://img0.baidu.com/it/u=4119328645,2294770712&fm=253&fmt=auto&app=138&f=JPEG?w=500&h=750',
               'https://img1.baidu.com/it/u=3167365498,4156845177&fm=253&fmt=auto&app=120&f=JPEG?w=355&h=631',
               'https://img2.baidu.com/it/u=2214691242,2295609938&fm=253&fmt=auto&app=120&f=JPEG?w=800&h=973',
               'https://img1.baidu.com/it/u=3930123826,1131807820&fm=253&fmt=auto&app=138&f=JPEG?w=889&h=500',
               'https://img2.baidu.com/it/u=3998619741,1128428746&fm=253&fmt=auto&app=138&f=JPEG?w=500&h=594',
               'https://img2.baidu.com/it/u=1507871502,2316279678&fm=253&fmt=auto&app=138&f=JPEG?w=500&h=768',
               'https://img0.baidu.com/it/u=2245878765,4037513957&fm=253&fmt=auto&app=138&f=JPEG?w=617&h=411',
               'https://img1.baidu.com/it/u=3623293272,829752126&fm=253&fmt=auto&app=138&f=JPEG?w=285&h=285',
               'https://img2.baidu.com/it/u=1922261112,3647796435&fm=253&fmt=auto&app=120&f=JPEG?w=500&h=542',
               'https://img1.baidu.com/it/u=3970043028,2042301564&fm=253&fmt=auto&app=120&f=JPEG?w=500&h=889',
               'https://img2.baidu.com/it/u=3229384329,3046902124&fm=253&fmt=auto&app=120&f=JPEG?w=800&h=800',
               'https://img1.baidu.com/it/u=3113661564,2558849413&fm=253&fmt=auto&app=138&f=JPEG?w=500&h=500',
               'https://img1.baidu.com/it/u=2361496550,3302335162&fm=253&fmt=auto&app=138&f=JPEG?w=333&h=500',
               'https://img1.baidu.com/it/u=270105183,1595166255&fm=253&fmt=auto&app=120&f=JPEG?w=800&h=500',
               'https://img1.baidu.com/it/u=4071105902,825241031&fm=253&fmt=auto&app=138&f=JPEG?w=235&h=340']
        list_length = len(id)
        videos = []
        for i in range(list_length):
            print(id[i])
            video = {
                "vod_id": id[i],
                "vod_name": name[i],
                "vod_pic": pic[i],
                "vod_remarks": '播放20个',
            }
            videos.append(video)

        result = {'list': videos}

        return result

    def categoryContent(self, cid, pg, filter, ext):
        pass

    def detailContent(self, ids):
        videos = []
        result = {}
        did = ids[0]
        for i in range(1, 21):
            playurl = ""
            for j in range(1, i + 1):
                playurl += f"{j}$/fenlei/{did}#"
        playurl = playurl[:-1]

        videos.append({
            "vod_id": '',
            "vod_name": '',
            "vod_pic": "",
            "type_name": '',
            "vod_year": "",
            "vod_area": "",
            "vod_remarks": "",
            "vod_actor": "",
            "vod_director": "",
            "vod_content": "",
            "vod_play_from": "GK推荐",
            "vod_play_url": playurl
        })

        result['list'] = videos
        return result

    def playerContent(self, flag, id, vipFlags):
        result = {}
        response = requests.get(url=xurl + id, headers=headerx, allow_redirects=False)

        location_header = response.headers.get('Location')
        if 'http' in location_header:
            purl = location_header
        else:
            purl = 'http:' + location_header
        result["parse"] = 0
        result["playUrl"] = ''
        result["url"] = purl
        result["header"] = headerx
        return result

    def searchContentPage(self, key, quick, page):
        pass

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
