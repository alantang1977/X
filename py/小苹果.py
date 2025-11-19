"""
@header({
  searchable: 1,
  filterable: 1,
  quickSearch: 1,
  title: '小苹果',
  lang: 'hipy'
})
"""

# -*- coding: utf-8 -*-
# by @嗷呜
import sys
sys.path.append('..')
from base.spider import Spider
import re

class Spider(Spider):

    def init(self, extend=""):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    host = 'http://asp.xpgtv.com'

    headers = {
        "User-Agent": "okhttp/3.12.11"
    }

    def homeContent(self, filter):
        data = self.fetch(f"{self.host}/api.php/v2.vod/androidtypes", headers=self.headers).json()
        dy = {
            "classes": "类型",
            "areas": "地区",
            "years": "年份",
            "sortby": "排序",
        }
        filters = {}
        classes = []
        for item in data['data']:
            # 简化字段检查逻辑
            has_non_empty_field = any(key in item and len(item[key]) > 1 for key in dy)
            item['soryby'] = ['updatetime', 'hits', 'score']
            demos = ['时间', '人气', '评分']
            classes.append({"type_name": item["type_name"], "type_id": str(item["type_id"])})
            
            if has_non_empty_field:
                filters[str(item["type_id"])] = []
                for dkey in item:
                    if dkey in dy and len(item[dkey]) > 1:
                        values = item[dkey]
                        value_array = [
                            {"n": demos[idx] if dkey == "sortby" else value.strip(), "v": value.strip()}
                            for idx, value in enumerate(values) if value.strip()
                        ]
                        filters[str(item["type_id"])].append(
                            {"key": dkey, "name": dy[dkey], "value": value_array}
                        )
        
        return {
            "class": classes,
            "filters": filters
        }

    def homeVideoContent(self):
        rsp = self.fetch(f"{self.host}/api.php/v2.main/androidhome", headers=self.headers).json()
        videos = []
        for i in rsp['data']['list']:
            videos.extend(self.getlist(i['list']))
        return {'list': videos}

    def categoryContent(self, tid, pg, filter, extend):
        params = {
            "page": pg,
            "type": tid,
            "area": extend.get('areaes', ''),
            "year": extend.get('yeares', ''),
            "sortby": extend.get('sortby', ''),
            "class": extend.get('classes', '')
        }
        # 简化参数过滤
        params = {k: v for k, v in params.items() if v}
        rsp = self.fetch(f'{self.host}/api.php/v2.vod/androidfilter10086', headers=self.headers, params=params).json()
        
        return {
            'list': self.getlist(rsp['data']),
            'page': pg,
            'pagecount': 9999,
            'limit': 90,
            'total': 999999
        }

    def detailContent(self, ids):
        rsp = self.fetch(f'{self.host}/api.php/v3.vod/androiddetail2?vod_id={ids[0]}', headers=self.headers).json()
        v = rsp.get('data', {}) or {}
        urls = v.get('urls') or []
        play_items = []
        
        # 预编译正则表达式提高性能
        patterns = [
            (r'^\d+$', None),  # 纯数字
            (r'^\d+-\d+$', None),  # 数字范围
            (r'^第\d+[集期话节]$', None),  # 第X集/期/话/节
            (r'^第\d+季$', None),  # 第X季
            (r'^[集期话]?\d+$', None),  # 集X/期X/话X
            (r'^E[P]?\d+$', re.IGNORECASE),  # EP1/E01
            (r'^\d+[PpKk]$', None),  # 分辨率
            (r'^[Hh][Dd]$', None),  # HD
            (r'^[Ff][Hh][Dd]$', None),  # FHD
            (r'^[Uu][Hh][Dd]$', None)  # UHD
        ]
        
        allowed_chinese_keywords = {
            '蓝光', '超清', '高清', '标清', '枪版', '全清',
            '全集', '全', '完整版', '正片', '预告', '花絮'
        }
        
        for i in urls:
            key = (i.get('key') or i.get('name') or "").strip()
            url = (i.get('url') or "").strip()
            
            if key and url:
                if key in allowed_chinese_keywords:
                    play_items.append(f"{key}${url}")
                else:
                    # 使用预编译的正则表达式检查
                    matched = False
                    for pattern, flags in patterns:
                        if flags:
                            if re.match(pattern, key, flags):
                                matched = True
                                break
                        else:
                            if re.match(pattern, key):
                                matched = True
                                break
                    
                    if matched:
                        play_items.append(f"{key}${url}")

        play_url = "#".join(play_items)
        
        vod = {
            'vod_id': v.get('id'),
            'vod_name': v.get('name'),
            'vod_pic': v.get('pic'),
            'vod_year': v.get('year'),
            'vod_area': v.get('area'),
            'vod_lang': v.get('lang'),
            'type_name': v.get('className'),
            'vod_actor': v.get('actor'),
            'vod_director': v.get('director'),
            'vod_content': v.get('content'),
            'vod_play_from': '小苹果',
            'vod_play_url': play_url
        }

        return {'list': [vod]}

    def searchContent(self, key, quick, pg='1'):
        rsp = self.fetch(f'{self.host}/api.php/v2.vod/androidsearch10086?page={pg}&wd={key}', headers=self.headers).json()
        return {'list': self.getlist(rsp['data']), 'page': pg}

    def playerContent(self, flag, id, vipFlags):
        header = {
            'user_id': 'XPGBOX',
            'token2': 'SnAXiSW8vScXE0Z9aDOnK5xffbO75w1+uPom3WjnYfVEA1oWtUdi2Ihy1N8=',
            'version': 'XPGBOX com.phoenix.tv1.5.7',
            'hash': 'd78a',
            'screenx': '2345',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
            'token': 'ElEDlwCVgXcFHFhddiq2JKteHofExRBUrfNlmHrWetU3VVkxnzJAodl52N9EUFS+Dig2A/fBa/V9RuoOZRBjYvI+GW8kx3+xMlRecaZuECdb/3AdGkYpkjW3wCnpMQxf8vVeCz5zQLDr8l8bUChJiLLJLGsI+yiNskiJTZz9HiGBZhZuWh1mV1QgYah5CLTbSz8=',
            'timestamp': '1743060300',
            'screeny': '1065',
        }
        if 'http' not in id:
            id = f"http://c.xpgtv.net/m3u8/{id}.m3u8"
        return {"parse": 0, "url": id, "header": header}

    def localProxy(self, param):
        pass

    def getlist(self, data):
        videos = []
        for vod in data:
            # 简化备注生成逻辑
            remarks = f"更新至{vod.get('updateInfo')}" if vod.get('updateInfo') else vod.get('score', '')
            videos.append({
                "vod_id": vod['id'],
                "vod_name": vod['name'],
                "vod_pic": vod['pic'],
                "vod_remarks": remarks
            })
        return videos