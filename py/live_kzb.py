# -*- coding: utf-8 -*-
# @Author  : Doubebly
# @Time    : 2025/5/22 20:23

import sys
import requests
import json
sys.path.append('..')
from base.spider import Spider


class Spider(Spider):
    def getName(self):
        return "Kzb"

    def init(self, extend):
        self.extend = json.loads(extend)
        pass

    def getDependence(self):
        return []

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass


    def liveContent(self, url):
        keys = ['578', '579', '580', '581', '582', '583', '584', '585', '586', '587', '588', '589', '590', '591', '592', '593', '594', '595', '596', '597', '598', '599', '600', '601', '602', '603', '604', '605', '606', '607', '608', '609', '610', '611', '612', '613', '614', '615', '616', '617', '618', '619', '620', '621', '622', '623', '624']
        values = {}
        headers = {
            'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Mobile Safari/537.36 EdgA/136.0.0.0"
        }
        response = requests.get(self.extend['host'] + "/prod-api/iptv/getIptvList?liveType=0&deviceType=1", headers=headers)
        for i in response.json()['list']:
            values[str(i['id'])] = i
        tv_list = ['#EXTM3U']
        for ii in keys:
            c = values[ii]
            name = c['play_source_name']
            group_name = '卫视频道' if '卫视' in name else '央视频道'
            tv_list.append(f'#EXTINF:-1 tvg-id="" tvg-name="" tvg-logo="https://live.fanmingming.cn/tv/{name}.png" group-title="{group_name}",{name}')
            tv_list.append(c['play_source_url'])
        return '\n'.join(tv_list)

    def homeContent(self, filter):
        return {}

    def homeVideoContent(self):
        return {}

    def categoryContent(self, cid, page, filter, ext):
        return {}

    def detailContent(self, did):
        return {}

    def searchContent(self, key, quick, page='1'):
        return {}

    def searchContentPage(self, keywords, quick, page):
        return {}

    def playerContent(self, flag, pid, vipFlags):
        return {}

    def localProxy(self, params):
        return {}

    def destroy(self):
        return '正在Destroy'

if __name__ == '__main__':
    pass
