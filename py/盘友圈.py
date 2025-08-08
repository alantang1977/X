# -*- coding: utf-8 -*-
# by @嗷呜
import json
import re
import sys
sys.path.append('..')
from base.spider import Spider


class Spider(Spider):

    def init(self, extend=""):
        pass

    def getName(self):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    host='https://panyq.com'

    def homeContent(self, filter):
        pass

    def homeVideoContent(self):
        pass

    def categoryContent(self, tid, pg, filter, extend):
        pass

    def detailContent(self, ids):
        try:
            data=json.loads(bytes.fromhex(ids[0]).decode())
            verify=self.post(
                f'{self.host}/search/{data["hash"]}',
                headers=self.getheader(-1),
                data=json.dumps(data['data'],separators=(",", ":")).encode(),
            )
            if verify.status_code == 200:
                eid = data['data'][0]['eid']
                rdata = json.dumps([{"eid": eid}],separators=(",", ":")).encode()
                res = self.post(f'{self.host}/go/{eid}', headers=self.getheader(1),data=rdata)
                purl=json.loads(res.text.strip().split('\n')[-1].split(":",1)[-1])['data']['link']
                if not re.search(r'pwd=|码',purl) and data['password']:
                    purl=f"{purl}{'&' if '?' in purl else '?'}pwd={data['password']}"
                print("获取盘链接为：",purl)
            else:
                raise Exception('验证失败')
            vod = {
                'vod_id': '',
                'vod_name': '',
                'vod_pic': '',
                'type_name': '',
                'vod_year': '',
                'vod_area': '',
                'vod_remarks': '',
                'vod_actor': '',
                'vod_director': '',
                'vod_content': '',
                'vod_play_from': '',
                'vod_play_url': ''
            }
            return {'list':[vod]}
        except Exception as e:
            print(e)
            return {'list': []}

    def searchContent(self, key, quick, pg="1"):
        sign,sha,hash=self.getsign(key,pg)
        res = self.fetch(f'{self.host}/api/search', params={'sign':sign}, headers=self.getheader()).json()
        videos=[]
        for i in res['data']['hits']:
            ccc=[{"eid":i.get("eid"),"sha":sha,"page_num":pg}]
            ddd=(json.dumps({'sign':sign,'hash':hash,'data':ccc,'password':i.get('password')})).encode().hex()
            videos.append({
                'vod_id': ddd,
                'vod_name': self.removeHtmlTags(i.get('desc')),
                'vod_pic': f"https://minio.talkno.de/panyq3/{i.get('image')}",
                'vod_remarks': i.get('group'),
            })
        return {'list':videos,'page':pg}

    def playerContent(self, flag, id, vipFlags):
        pass

    def localProxy(self, param):
        pass

    def liveContent(self, url):
        pass

    def getsign(self,key,pg):
        data=json.dumps([{"cat":"all","query":key,"pageNum":int(pg),"enableSearchMusic":False,"enableSearchGame":False,"enableSearchEbook":False}],separators=(",", ":"),ensure_ascii= False).encode()
        res = self.post(self.host, headers=self.getheader(), data=data).text
        hash=re.search(r'"hash",\s*"([^"]+)"', res).group(1)
        sign = re.search(r'"sign":\s*"([^"]+)"', res).group(1)
        sha= re.search(r'"sha":\s*"([^"]+)"', res).group(1)
        return sign,sha,hash

    def getheader(self,k=0):
        kes=['ecce0904d756da58b9ea5dd03da3cacea9fa29c6','4c5c1ef8a225004ce229e9afa4cc7189eed3e6fe','c4ed62e2b5a8e3212b334619f0cdbaa77fa842ff']
        headers = {
            'origin': self.host,
            'referer': f'{self.host}/',
            'next-action': kes[k],
            'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="136", "Google Chrome";v="136"',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.7103.48 Safari/537.36',
        }
        return headers
