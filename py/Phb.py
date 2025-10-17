# -*- coding: utf-8 -*-
# by @嗷呜
import json
import re
import sys
from pyquery import PyQuery as pq
from base64 import b64decode, b64encode
from requests import Session
sys.path.append('..')
from base.spider import Spider


class Spider(Spider):

    def init(self, extend=""):
        self.host=self.gethost()
        self.headers['referer']=f'{self.host}/'
        self.session = Session()
        self.session.headers.update(self.headers)
        pass

    def getName(self):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'sec-ch-ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-full-version': '"133.0.6943.98"',
        'sec-ch-ua-arch': '"x86"',
        'sec-ch-ua-platform': '"Windows"',
        'sec-ch-ua-platform-version': '"19.0.0"',
        'sec-ch-ua-model': '""',
        'sec-ch-ua-full-version-list': '"Not(A:Brand";v="99.0.0.0", "Google Chrome";v="133.0.6943.98", "Chromium";v="133.0.6943.98"',
        'dnt': '1',
        'upgrade-insecure-requests': '1',
        'sec-fetch-site': 'none',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-user': '?1',
        'sec-fetch-dest': 'document',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'priority': 'u=0, i'
    }

    def homeContent(self, filter):
        result = {}
        cateManual = {
            "视频": "/video",
            "片单": "/playlists",
            "频道": "/channels",
            "分类": "/categories",
            "明星": "/pornstars"
        }
        classes = []
        filters = {}
        for k in cateManual:
            classes.append({
                'type_name': k,
                'type_id': cateManual[k]
            })
        result['class'] = classes
        result['filters'] = filters
        return result

    def homeVideoContent(self):
        data = self.getpq('/recommended')
        vhtml = data("#recommendedListings .pcVideoListItem .phimage")
        return {'list':self.getlist(vhtml)}

    def categoryContent(self, tid, pg, filter, extend):
        vdata = []
        result = {}
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        if tid=='/video' or '_this_video' in tid:
            pagestr = f'&' if '?' in tid else f'?'
            tid=tid.split('_this_video')[0]
            data=self.getpq(f'{tid}{pagestr}page={pg}')
            vdata=self.getlist(data('#videoCategory .pcVideoListItem'))
        elif tid == '/playlists':
            data=self.getpq(f'{tid}?page={pg}')
            vhtml=data('#playListSection li')
            vdata = []
            for i in vhtml.items():
                vdata.append({
                    'vod_id': 'playlists_click_' + i('.thumbnail-info-wrapper .display-block a').attr('href'),
                    'vod_name': i('.thumbnail-info-wrapper .display-block a').attr('title'),
                    'vod_pic': i('.largeThumb').attr('src'),
                    'vod_tag': 'folder',
                    'vod_remarks': i('.playlist-videos .number').text(),
                    'style': {"type": "rect", "ratio": 1.33}
                })
        elif tid=='/channels':
            data=self.getpq(f'{tid}?o=rk&page={pg}')
            vhtml=data('#filterChannelsSection li .description')
            vdata=[]
            for i in vhtml.items():
                vdata.append({
                    'vod_id': 'director_click_'+i('.avatar a').attr('href'),
                    'vod_name': i('.avatar img').attr('alt'),
                    'vod_pic': i('.avatar img').attr('src'),
                    'vod_tag':'folder',
                    'vod_remarks': i('.descriptionContainer ul li').eq(-1).text(),
                    'style':{"type": "rect", "ratio": 1.33}
                })
        elif tid=='/categories' and pg=='1':
            result['pagecount'] = 1
            data=self.getpq(f'{tid}')
            vhtml=data('.categoriesListSection li .relativeWrapper')
            vdata=[]
            for i in vhtml.items():
                vdata.append({
                    'vod_id': i('a').attr('href')+'_this_video',
                    'vod_name': i('a').attr('alt'),
                    'vod_pic': i('a img').attr('src'),
                    'vod_tag':'folder',
                    'style':{"type": "rect", "ratio": 1.33}
                })
        elif tid=='/pornstars':
            data=self.getpq(f'{tid}?o=t&page={pg}')
            vhtml=data('#popularPornstars .performerCard .wrap')
            vdata=[]
            for i in vhtml.items():
                vdata.append({
                    'vod_id': 'pornstars_click_'+i('a').attr('href'),
                    'vod_name': i('.performerCardName').text(),
                    'vod_pic': i('a img').attr('src'),
                    'vod_tag':'folder',
                    'vod_year':i('.performerVideosViewsCount span').eq(0).text(),
                    'vod_remarks': i('.performerVideosViewsCount span').eq(-1).text(),
                    'style':{"type": "rect", "ratio": 1.33}
                })
        elif 'playlists_click' in tid:
            tid=tid.split('click_')[-1]
            if pg=='1':
                hdata=self.getpq(tid)
                self.token=hdata('#searchInput').attr('data-token')
                vdata = self.getlist(hdata('#videoPlaylist .pcVideoListItem .phimage'))
            else:
                tid=tid.split('playlist/')[-1]
                data=self.getpq(f'/playlist/viewChunked?id={tid}&token={self.token}&page={pg}')
                vdata=self.getlist(data('.pcVideoListItem .phimage'))
        elif 'director_click' in tid:
            tid=tid.split('click_')[-1]
            data=self.getpq(f'{tid}/videos?page={pg}')
            vdata=self.getlist(data('#showAllChanelVideos .pcVideoListItem .phimage'))
        elif 'pornstars_click' in tid:
            tid=tid.split('click_')[-1]
            data=self.getpq(f'{tid}/videos?page={pg}')
            vdata=self.getlist(data('#mostRecentVideosSection .pcVideoListItem .phimage'))
        result['list'] = vdata
        return result

    def detailContent(self, ids):
        url = f"{self.host}{ids[0]}"
        data = self.getpq(ids[0])
        vn=data('meta[property="og:title"]').attr('content')
        dtext=data('.userInfo .usernameWrap a')
        pdtitle = '[a=cr:' + json.dumps({'id': 'director_click_'+dtext.attr('href'), 'name': dtext.text()}) + '/]' + dtext.text() + '[/a]'
        vod = {
            'vod_name': vn,
            'vod_director':pdtitle,
            'vod_remarks': (data('.userInfo').text()+' / '+data('.ratingInfo').text()).replace('\n',' / '),
            'vod_play_from': 'Pornhub',
            'vod_play_url': ''
        }
        js_content = data("#player script").eq(0).text()
        plist = [f"{vn}${self.e64(f'{1}@@@@{url}')}"]
        try:
            pattern = r'"mediaDefinitions":\s*(\[.*?\]),\s*"isVertical"'
            match = re.search(pattern, js_content, re.DOTALL)
            if match:
                json_str = match.group(1)
                udata = json.loads(json_str)
                plist = [
                    f"{media['height']}${self.e64(f'{0}@@@@{url}')}"
                    for media in udata[:-1]
                    if (url := media.get('videoUrl'))
                ]
        except Exception as e:
            print(f"提取mediaDefinitions失败: {str(e)}")
        vod['vod_play_url'] = '#'.join(plist)
        return {'list':[vod]}

    def searchContent(self, key, quick, pg="1"):
        data=self.getpq(f'/video/search?search={key}&page={pg}')
        return {'list':self.getlist(data('#videoSearchResult .pcVideoListItem .phimage'))}

    def playerContent(self, flag, id, vipFlags):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.5410.0 Safari/537.36',
            'pragma': 'no-cache',
            'cache-control': 'no-cache',
            'sec-ch-ua-platform': '"Windows"',
            'sec-ch-ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
            'dnt': '1',
            'sec-ch-ua-mobile': '?0',
            'origin': self.host,
            'sec-fetch-site': 'cross-site',
            'sec-fetch-mode': 'cors',
            'sec-fetch-dest': 'empty',
            'referer': f'{self.host}/',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'priority': 'u=1, i',
        }
        ids=self.d64(id).split('@@@@')
        return {'parse': int(ids[0]), 'url': ids[1], 'header': headers}

    def localProxy(self, param):
        pass

    def gethost(self):
        try:
            response = self.fetch('https://www.pornhub.com',headers=self.headers,allow_redirects=False)
            return response.headers['Location'][:-1]
        except Exception as e:
            print(f"获取主页失败: {str(e)}")
            return "https://www.pornhub.com"

    def e64(self, text):
        try:
            text_bytes = text.encode('utf-8')
            encoded_bytes = b64encode(text_bytes)
            return encoded_bytes.decode('utf-8')
        except Exception as e:
            print(f"Base64编码错误: {str(e)}")
            return ""

    def d64(self,encoded_text):
        try:
            encoded_bytes = encoded_text.encode('utf-8')
            decoded_bytes = b64decode(encoded_bytes)
            return decoded_bytes.decode('utf-8')
        except Exception as e:
            print(f"Base64解码错误: {str(e)}")
            return ""

    def getlist(self, data):
        vlist=[]
        for i in data.items():
            vlist.append({
                'vod_id': i('a').attr('href'),
                'vod_name': i('a').attr('title'),
                'vod_pic': i('img').attr('src'),
                'vod_remarks': i('.bgShadeEffect').text() or i('.duration').text(),
                'style': {'ratio': 1.33, 'type': 'rect'}
            })
        return vlist

    def getpq(self, path):
        try:
            response = self.session.get(f'{self.host}{path}').text
            return pq(response.encode('utf-8'))
        except Exception as e:
            print(f"请求失败: , {str(e)}")
            return None
