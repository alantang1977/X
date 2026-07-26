#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
作者：十一
网站：https://www.yxxq41.cc/
描述：映像星球 (OK影视/TVBox 爬虫插件) - 使用 MxPro CMS JSON API
支持分类浏览、搜索、详情获取、播放链接解析 - 全量数据
"""

import re
import json
import logging
import urllib.parse
import os
import sys
import requests

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from base.spider import Spider as BaseSpider
except ImportError:
    BaseSpider = object

logger = logging.getLogger(__name__)


class Spider(BaseSpider):
    """映像星球爬虫 - 使用 MxPro CMS API"""

    BASE_URL = "https://www.yxxq41.cc"
    API_URL = "https://www.yxxq41.cc/api.php/provide/vod/at/json/"
    
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json,text/plain,*/*",
        "Referer": "https://www.yxxq41.cc/",
    }

    CATEGORY_MAP = {
        "1": "电影",
        "2": "电视剧",
        "3": "综艺",
        "4": "动漫",
        "7": "纪录片",
        "39": "短剧",
        "53": "体育",
    }

    def __init__(self):
        try:
            super().__init__()
        except Exception:
            pass
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def init(self, extend):
        pass

    def getName(self):
        return "映像星球"

    def _fix_pic(self, pic_url):
        """处理图片URL，取有效的真实地址"""
        if not pic_url or not isinstance(pic_url, str):
            return ''
        if '#' in pic_url:
            for p in reversed(pic_url.split('#')):
                p = p.strip()
                if p and 'test.com' not in p:
                    if p.startswith('//'):
                        return 'https:' + p
                    if not p.startswith('http'):
                        return 'https://' + p
                    return p
        pic_url = pic_url.strip()
        if not pic_url or 'test.com' in pic_url:
            return ''
        if pic_url.startswith('//'):
            pic_url = 'https:' + pic_url
        elif not pic_url.startswith('http'):
            pic_url = 'https://' + pic_url
        return pic_url

    def _batch_get_pics(self, vod_list):
        """批量获取封面图 - 分批20个一组"""
        if not vod_list:
            return vod_list
        
        need_pic = [v for v in vod_list if not v.get('vod_pic')]
        if not need_pic:
            return vod_list
        
        need_ids = [v['vod_id'] for v in need_pic]
        
        # 每批最多20个ID（API限制）
        batch_size = 20
        pic_map = {}
        
        for i in range(0, len(need_ids), batch_size):
            batch = need_ids[i:i+batch_size]
            try:
                url = f"{self.API_URL}?ac=detail&ids={','.join(batch)}"
                resp = self.session.get(url, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                if data.get('code') == 1 and data.get('list'):
                    for vod in data['list']:
                        pic = self._fix_pic(vod.get('vod_pic', ''))
                        if pic:
                            pic_map[str(vod['vod_id'])] = pic
            except Exception:
                continue
        
        for v in vod_list:
            vid = v['vod_id']
            if not v.get('vod_pic') and vid in pic_map:
                v['vod_pic'] = pic_map[vid]
        
        return vod_list

    def homeContent(self, filter=False):
        try:
            classes = []
            for cate_id, cate_name in self.CATEGORY_MAP.items():
                classes.append({
                    "type_id": cate_id,
                    "type_name": cate_name,
                })
            
            # 取电影最新36条
            url = f"{self.API_URL}?ac=list&t=1&pg=1&pagesize=36"
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            
            videos = []
            if data.get('code') == 1 and data.get('list'):
                for vod in data['list']:
                    videos.append({
                        "vod_id": str(vod['vod_id']),
                        "vod_name": vod.get('vod_name', ''),
                        "vod_pic": self._fix_pic(vod.get('vod_pic', '')),
                        "vod_remarks": vod.get('vod_remarks', ''),
                    })
            
            # 批量补充封面
            videos = self._batch_get_pics(videos)
            
            return {"class": classes, "list": videos}
        except Exception as e:
            logger.error(f"首页失败: {e}")
            return {}

    def homeVideoContent(self):
        home = self.homeContent()
        return {"list": home.get("list", [])}

    def categoryContent(self, tid, pg, filter, ext):
        try:
            page = int(pg) if pg else 1
            url = f"{self.API_URL}?ac=list&t={tid}&pg={page}&pagesize=50"
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            
            vod_list = []
            if data.get('code') == 1 and data.get('list'):
                for vod in data['list']:
                    vod_list.append({
                        "vod_id": str(vod['vod_id']),
                        "vod_name": vod.get('vod_name', ''),
                        "vod_pic": self._fix_pic(vod.get('vod_pic', '')),
                        "vod_remarks": vod.get('vod_remarks', ''),
                    })
            
            # 批量补充封面
            vod_list = self._batch_get_pics(vod_list)
            
            return {
                "list": vod_list,
                "page": page,
                "pagecount": data.get('pagecount', 1),
                "limit": 50,
                "total": data.get('total', 0),
            }
        except Exception as e:
            logger.error(f"分类失败: {e}")
            return {"list": [], "page": 1, "pagecount": 1, "limit": 20, "total": 0}

    def detailContent(self, ids):
        try:
            vod_id = ids[0] if isinstance(ids, list) else str(ids)
            url = f"{self.API_URL}?ac=detail&ids={vod_id}"
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            
            if data.get('code') != 1 or not data.get('list'):
                return {"list": []}
            
            vod = data['list'][0]
            
            vod_item = {
                "vod_id": str(vod['vod_id']),
                "vod_name": vod.get('vod_name', ''),
                "vod_pic": self._fix_pic(vod.get('vod_pic', '')),
                "type_name": vod.get('vod_class', ''),
                "vod_year": vod.get('vod_year', ''),
                "vod_area": vod.get('vod_area', ''),
                "vod_remarks": vod.get('vod_remarks', ''),
                "vod_actor": vod.get('vod_actor', ''),
                "vod_director": vod.get('vod_director', ''),
                "vod_content": vod.get('vod_content', '') or vod.get('vod_blurb', ''),
                "vod_play_from": vod.get('vod_play_from', ''),
                "vod_play_url": vod.get('vod_play_url', ''),
            }
            
            return {"list": [vod_item]}
        except Exception as e:
            logger.error(f"详情失败: {e}")
            return {"list": []}

    def playerContent(self, flag, id, vipFlags):
        try:
            play_url = urllib.parse.unquote(id) if id else ''
            if not play_url:
                return {"parse": 0, "url": ""}
            return {
                "parse": 0,
                "url": play_url,
                "header": json.dumps(self.HEADERS),
            }
        except Exception as e:
            logger.error(f"播放失败: {e}")
            return {"parse": 0, "url": ""}

    def searchContent(self, key, quick, pg):
        try:
            page = int(pg) if pg else 1
            encoded_key = urllib.parse.quote(key)
            url = f"{self.API_URL}?ac=list&wd={encoded_key}&pg={page}&pagesize=50"
            
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            
            vod_list = []
            if data.get('code') == 1 and data.get('list'):
                for vod in data['list']:
                    vod_list.append({
                        "vod_id": str(vod['vod_id']),
                        "vod_name": vod.get('vod_name', ''),
                        "vod_pic": self._fix_pic(vod.get('vod_pic', '')),
                        "vod_remarks": vod.get('vod_remarks', ''),
                    })
            
            vod_list = self._batch_get_pics(vod_list)
            
            return {
                "list": vod_list,
                "page": page,
                "pagecount": data.get('pagecount', 1),
                "limit": 50,
                "total": data.get('total', len(vod_list)),
            }
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return {"list": [], "page": 1, "pagecount": 1, "limit": 20, "total": 0}

    def localProxy(self, param):
        return []


if __name__ == "__main__":
    spider = Spider()
    
    print("=" * 60)
    print("【1】首页")
    home = spider.homeContent()
    print(f"分类: {len(home.get('class', []))}, 推荐: {len(home.get('list', []))}")
    has_pic = sum(1 for v in home.get('list', []) if v.get('vod_pic'))
    print(f"有封面的: {has_pic}/{len(home.get('list', []))}")
    for v in home.get('list', [])[:3]:
        print(f"  - {v['vod_name']} | pic: {v['vod_pic'][:60] if v['vod_pic'] else '无'}...")
    
    print("\n" + "=" * 60)
    print("【2】电影 第1页")
    cat1 = spider.categoryContent("1", "1", False, {})
    print(f"总数: {cat1.get('total')}, 总页: {cat1.get('pagecount')}, 本页: {len(cat1.get('list', []))}")
    has_pic = sum(1 for v in cat1.get('list', []) if v.get('vod_pic'))
    print(f"有封面的: {has_pic}/{len(cat1.get('list', []))}")
    for v in cat1.get('list', [])[:3]:
        print(f"  - {v['vod_name']} | pic: {v['vod_pic'][:60] if v['vod_pic'] else '无'}...")
    
    print("\n【3】详情")
    detail = spider.detailContent(["23026"])
    if detail.get('list'):
        d = detail['list'][0]
        print(f"标题: {d['vod_name']}")
        print(f"封面: {d['vod_pic'][:80] if d['vod_pic'] else '无'}...")
    
    print("\n完成!")