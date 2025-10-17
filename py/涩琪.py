# -*- coding: utf-8 -*-
# by @嗷呜
import base64
import json
import re
import sys
from pprint import pprint
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from pyquery import PyQuery as pq
sys.path.append('..')
from base.spider import Spider


class Spider(Spider):

    def init(self, extend=""):
        self.chost,self.token=self.gettoken()
        self.phost='https://wsrv.nl?url=https://image.tmdb.org/t/p/w500'
        # self.chost,self.token= 'https://api.themoviedb.org/3','eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJhZDFhYmJjMmM4YjhkY2I2NzJiYzI1Y2M3ZDcxYzVhOCIsIm5iZiI6MTczNzUxMTI4MC4wOCwic3ViIjoiNjc5MDUxNzA1NTBlNmZjM2NkZGZlOThiIiwic2NvcGVzIjpbImFwaV9yZWFkIl0sInZlcnNpb24iOjF9.fmGzxmyxA-r74R_1_wo-sPHtfOn3zyGQqzPxr3NUIII'
        # print(self.chost,self.token)
        self.headers.update({'authorization': f"Bearer {self.token}"})
        pass

    def getName(self):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    headers ={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.7103.48 Safari/537.36',
        'sec-ch-ua-platform': '"Windows"',
        'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="136", "Google Chrome";v="136"',
        'origin': 'https://nunflix.org',
        'referer': 'https://nunflix.org/',
    }

    jx='https://111movies.com'

    def homeContent(self, filter):
        result = {}
        cate = {
            "电影": "movie",
            "剧集": "tv"
        }
        classes = []
        filters = {}
        for k, j in cate.items():
            classes.append({
                'type_name': k,
                'type_id': j
            })
        result['class'] = classes
        result['filters'] = filters
        return result

    def homeVideoContent(self):
        data=self.fetch(f"{self.chost}/trending/all/week",headers=self.headers).json()
        return {'list':self.getlist(data['results'])}

    def categoryContent(self, tid, pg, filter, extend):
        params = {'page':pg}
        data=self.fetch(f'{self.chost}/discover/{tid}',params=params,headers=self.headers).json()
        result = {}
        result['list'] = self.getlist(data['results'],tid)
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        return result

    def detailContent(self, ids):
        v=self.fetch(f'{self.chost}{ids[0]}',headers=self.headers).json()
        if 'movie' in ids[0]:
            p=f"{v.get('title') or v.get('name')}${ids[0]}"
        else:
            p='#'.join([f"{i.get('name')}${ids[0]}/{i.get('season_number')}/1" for i in v.get('seasons')])
        vod = {
            'vod_year': v.get('release_date') or v.get('last_air_date'),
            'vod_area': v.get('original_language'),
            'vod_remarks': v.get('tagline'),
            'vod_content': v.get('overview'),
            'vod_play_from': '默认',
            'vod_play_url': p
        }
        return {'list':[vod]}

    def searchContent(self, key, quick, pg="1"):
        data=self.fetch(f'{self.chost}/search/multi',params={'query':key,'page':pg},headers=self.headers).json()
        return {'list':self.getlist(data['results']),'page':pg}

    def playerContent(self, flag, id, vipFlags):
        data=self.fetch(f'{self.jx}{id}',headers=self.headers).text
        jstr=json.loads(pq(data)('#__NEXT_DATA__').text())
        url=self.encrypt_data(jstr['props']['pageProps'].get('data'))
        return  {'parse': 0, 'url': url, 'header': self.jxh()}

    def getlist(self,data,tid=''):
        videos = []
        for i in data:
            videos.append({
                'vod_id': f"/{tid or i.get('media_type')}/{i.get('id')}",
                'vod_name': i.get('title') or i.get('name'),
                'vod_pic': f"{self.phost}{i.get('backdrop_path')}",
                'vod_remarks': f"{i.get('popularity', 0):.2f}",
            })
        return  videos

    def encrypt_data(self,data_str):
        key = bytes(
            [1, 157, 45, 74, 228, 243, 24, 124, 194, 12, 184, 70, 3, 93, 102, 187, 254, 72, 230, 97, 57, 129, 254, 216,
             223,
             113, 82, 42, 62, 208, 244, 63])
        iv = bytes([147, 233, 144, 118, 246, 33, 110, 119, 13, 209, 140, 42, 32, 186, 47, 89])
        xkey = bytes([238, 123, 35, 56, 43, 184, 57, 233, 233, 41])
        cipher = AES.new(key, AES.MODE_CBC, iv)
        padded_data = pad(data_str.encode(), AES.block_size)
        encrypted_data = cipher.encrypt(padded_data)
        hex_data = encrypted_data.hex()
        result = ""
        for i in range(len(hex_data)):
            char_code = ord(hex_data[i])
            xor_value = xkey[i % len(xkey)]
            result += chr(char_code ^ xor_value)

        base64_result = base64.b64encode(result.encode('utf-8')).decode('ascii').replace('+', '-').replace('/',
                                                                                                           '_').replace(
            '=', '')
        source_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
        target_chars = "PpowE6rtqQ9OxFNzg_vLTJmHKi07j45fXubCVecGURsaS1ny8lBWdAD2ZkM3-YhI"
        char_map = {source_chars[i]: target_chars[i] for i in range(len(source_chars))}
        final_result = ''.join([char_map.get(c, c) for c in base64_result])
        return self.geturl(final_result)

    def geturl(self,txt):
        data=self.post(f"{self.jx}/rijevra/{txt}/sr",headers=self.jxh()).json()
        urls=[]
        for i in data:
            urls.extend([i['name'],f"{self.getProxyUrl()}&dddd={i['data']}"])
        return urls

    def localProxy(self, param):
        try:
            data=self.post(f"{self.jx}/rijevra/{param.get('dddd')}",headers=self.jxh()).json()
            return [302,'application/vnd.apple.mpegurl',None,{'Location':data['url']}]
        except Exception as e:
            self.log(e)
            return ''

    def liveContent(self, url):
        pass

    def jxh(self):
        header = self.headers.copy()
        header.update({'referer': f'{self.jx}/', 'origin': self.jx, 'content-type': 'text/plain'})
        header.pop('authorization', None)
        return header

    def gettoken(self):
        host='https://nunflix.org'
        data=self.fetch(f'{host}/explore/movie',headers=self.headers).text
        mod=pq(data)('script[type="module"]').attr('src')
        murl= mod if mod.startswith('http') else f'{host}{mod}'
        print(murl)
        mdd=self.fetch(murl,headers=self.headers).text
        ane_match = re.search(r'Ane\s*=\s*"([^"]+)"', mdd)
        ane_value = ane_match.group(1) if ane_match else ''
        xne_match = re.search(r'xne\s*=\s*"([^"]+)"', mdd)
        xne_value = xne_match.group(1) if xne_match else ''
        if ane_value and xne_value:
            return ane_value.strip(),xne_value.strip()

if __name__ == "__main__":
    sp = Spider()
    formatJo = sp.init()
    # formatJo = sp.homeContent(False)  # 主页，等于真表示启用筛选
    formatJo = sp.homeVideoContent()  # 主页视频
    # formatJo = sp.searchContent("斗罗",False,'1') # 搜索{"area":"大陆","by":"hits","class":"国产","lg":"国语"}
    # formatJo = sp.categoryContent('movie', '1', False, {})  # 分类
    # formatJo = sp.detailContent(['/tv/93405'])  # 详情
    # formatJo = sp.playerContent("","/tv/93405/1/1",{}) # 播放
    # formatJo = sp.localProxy({"dddd":""}) # 播放
    pprint(formatJo)
