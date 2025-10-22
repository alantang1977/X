#Kyele
import sys
import json
import time
import re
import requests
sys.path.append('..')
from base.spider import Spider
class Spider(Spider):
    def __init__(self):
        super().__init__()
        self.base = 'https://www.pandalive.co.kr'; self.api = 'https://api.pandalive.co.kr'; self.session = requests.Session()
        self.ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'
        self.common_headers = {'User-Agent': self.ua, 'Accept': 'application/json, text/plain, */*', 'Origin': self.base, 'Referer': self.base + '/'}
        self.x_device_info = {"t": "webPc", "v": "1.0", "ui": "0", "ck": {"sessKeyAsp": ""}}; self.extra_cookie = ''
    def init(self, extend=""):
        try:
            if extend:
                cfg = extend if isinstance(extend, dict) else json.loads(extend)
                self.x_device_info = cfg.get('x_device_info', self.x_device_info); self.extra_cookie = cfg.get('cookie', '')
        except Exception: pass
        try:
            self.session.headers.update(self.common_headers)
            if self.extra_cookie: self.session.headers['Cookie'] = self.extra_cookie
            self.session.get(self.base, timeout=8); self._app_token()
        except Exception: pass
        return self
    def getName(self): return 'PandaLive'
    def isVideoFormat(self, url): return url.endswith('.m3u8') or url.endswith('.mp4')
    def manualVideoCheck(self): return False
    def destroy(self):
        try: self.session.close()
        except Exception: pass
    def _app_token(self):
        headers = self._with_x_device_info(dict(self.session.headers))
        return self.session.get(f'{self.api}/v1/member/app_token', headers=headers, timeout=8)
    def _list_live(self, page=None, page_size=None, order_by='user', only_new='N'):
        if page_size is None: page_size = 60
        limit = page_size; offset = 0 if page is None else max(0, (page - 1) * limit)
        headers = self._with_x_device_info(dict(self.session.headers))
        headers['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8'
        data = {'orderBy': order_by, 'onlyNewBj': only_new, 'limit': str(limit), 'offset': str(offset)}
        try:
            r = self.session.post(f'{self.api}/v1/live', data=data, headers=headers, timeout=8)
            j = {}
            try: j = r.json()
            except Exception: pass
            if isinstance(j, dict) and isinstance(j.get('list'), list) and len(j['list']) > 0: return j
        except Exception: pass
        try: return self.session.get(f'{self.api}/v1/live', timeout=8).json()
        except Exception: return {}
    def _list_live_page(self, page, page_size, order_by='user', only_new='N'):
        j = self._list_live(page=page, page_size=page_size, order_by=order_by, only_new=only_new)
        return j.get('list', []) if isinstance(j, dict) else []
    def _list_live_aggregate(self, max_pages=5, page_size=60, min_expect=60, order_by='user', only_new='N'):
        try:
            cache_key = f'pandalive_agg_v2_{order_by}_{only_new}'; cached = self.getCache(cache_key)
            if isinstance(cached, dict) and isinstance(cached.get('list'), list): return cached['list']
        except Exception: pass
        seen = set(); result = []
        first = self._list_live(page=None, page_size=page_size, order_by=order_by, only_new=only_new)
        items = first.get('list', []) if isinstance(first, dict) else []
        for it in items:
            code = it.get('code') or it.get('userId')
            if code and code not in seen: seen.add(code); result.append(it)
        p = 1
        while len(result) < min_expect and p <= max_pages:
            page_items = self._list_live_page(page=p, page_size=page_size, order_by=order_by, only_new=only_new)
            added = 0
            for it in page_items:
                code = it.get('code') or it.get('userId')
                if code and code not in seen: seen.add(code); result.append(it); added += 1
            if added == 0 and p > 1: break
            p += 1
        try:
            payload = {"expiresAt": int(time.time()) + 20, "list": result}
            self.setCache(f'pandalive_agg_v2_{order_by}_{only_new}', payload)
        except Exception: pass
        return result
    def _live_play(self, play_id):
        body = {'play_id': play_id, 'device': 'webPc', 'player': 'ivs'}
        headers = self._with_x_device_info(dict(self.session.headers))
        headers['Content-Type'] = 'application/json'; headers['Referer'] = f'{self.base}/play/{play_id.split("_")[0]}'
        r = self.session.post(f'{self.api}/v1/live/play', headers=headers, data=json.dumps(body), timeout=8)
        if r.status_code != 200:
            try: self._app_token()
            except Exception: pass
            r = self.session.post(f'{self.api}/v1/live/play', headers=headers, data=json.dumps(body), timeout=8)
        try: return r.json()
        except Exception: return {'result': False, 'status': r.status_code, 'text': r.text}
    def _with_x_device_info(self, headers):
        try: headers['x-device-info'] = json.dumps(self.x_device_info, separators=(',', ':'))
        except Exception: headers['x-device-info'] = '{"t":"webPc","v":"1.0","ui":"0","ck":{"sessKeyAsp":""}}'
        return headers
    def homeContent(self, filter):
        classes = [{"type_name": "LIVE", "type_id": "live"}]
        if filter:
            filters = {"live": [{"key": "sort", "value": [
                            {"n": "观看次数", "v": "user-N"}, {"n": "热门", "v": "hot-N"},
                            {"n": "最新", "v": "new-N"}, {"n": "新人", "v": "user-Y"}
                        ]}]}
        else: filters = {}
        return {"class": classes, "filters": filters}
    def homeVideoContent(self):
        items = self._list_live_aggregate(max_pages=3, page_size=60, min_expect=48, order_by='user', only_new='N')
        if not items:
            items = (self._list_live().get('list', []))
        return {"list": [self._to_vod(it) for it in items[:48]]}
    def categoryContent(self, tid, pg, filter, extend):
        page_size = 24; p = 1
        try: p = int(pg)
        except Exception: pass
        order_by, only_new = 'user', 'N'
        try:
            if isinstance(extend, str):
                try: extend = json.loads(extend) if extend.strip().startswith('{') else {}
                except Exception: extend = {}
            if isinstance(extend, dict):
                s = extend.get('sort')
                if isinstance(s, str) and '-' in s:
                    ab = s.split('-', 1)
                    if len(ab) == 2: order_by, only_new = (ab[0] or 'user'), (ab[1] or 'N')
            if (order_by, only_new) == ('user', 'N') and (tid or '').lower() != 'live':
                order_by, only_new = self._tid_to_sort(tid)
        except Exception: pass
        server_items = self._list_live_page(page=p, page_size=page_size, order_by=order_by, only_new=only_new)
        if len(server_items) >= page_size:
            return {"page": p, "pagecount": 99999, "limit": page_size, "total": 999999, "list": [self._to_vod(it) for it in server_items]}
        all_items = self._list_live_aggregate(max_pages=12, page_size=100, min_expect=120, order_by=order_by, only_new=only_new)
        total = len(all_items)
        if total <= 0:
            base_list = self._list_live().get('list', [])
            total = len(base_list)
            if total <= 0: return {"page": p, "pagecount": 1, "limit": page_size, "total": 0, "list": []}
            start = (p - 1) * page_size; end = start + page_size
            part = base_list[start:end]
            videos = [self._to_vod(it) for it in part]
            return {"page": p, "pagecount": (total + page_size - 1)//page_size, "limit": page_size, "total": total, "list": videos}
        start = ((p - 1) * page_size) % total; part = []
        for i in range(page_size): part.append(all_items[(start + i) % total])
        return {"page": p, "pagecount": 99999, "limit": page_size, "total": 999999, "list": [self._to_vod(it) for it in part]}
    def _tid_to_sort(self, tid):
        t = (tid or '').lower()
        if t == 'live_newbj': return 'user', 'Y'
        if t == 'live_hot': return 'hot', 'N'
        if t == 'live_new': return 'new', 'N'
        return 'user', 'N'
    def detailContent(self, ids):
        vid = ids[0]; parts = vid.split('|'); play_id = parts[0]
        user_id = parts[1] if len(parts) > 1 else play_id.split('_')[0]
        title = parts[2] if len(parts) > 2 else user_id
        vod = {"vod_id": vid, "vod_name": title, "vod_pic": "", "type_name": "LIVE", "vod_year": "", "vod_area": "", "vod_remarks": "PandaLive", "vod_actor": "", "vod_director": "", "vod_content": title, "vod_play_from": "IVS", "vod_play_url": f"直播${vid}"}
        return {"list": [vod]}
    def searchContent(self, key, quick, pg="1"):
        items = self._list_live().get('list', [])
        key_l = key.lower(); result = []
        for it in items:
            title = str(it.get('title', '')); user_id = str(it.get('userId', '')); user_nick = str(it.get('userNick', ''))
            if key_l in title.lower() or key_l in user_id.lower() or key_l in user_nick.lower():
                result.append(self._to_vod(it))
        return {"list": result, "page": 1}
    def playerContent(self, flag, id, vipFlags):
        try:
            vid = id; parts = vid.split('|'); play_id = parts[0]
            j = self._live_play(play_id); m3u8 = self._find_first_m3u8(j) if isinstance(j, dict) else ''
            if not m3u8: return {"parse": 1, "playUrl": "", "url": f"{self.base}/play/{play_id.split('_')[0]}", "header": self._play_headers()}
            return {"parse": 0, "playUrl": "", "url": m3u8, "header": self._play_headers()}
        except Exception: return {"parse": 1, "playUrl": "", "url": f"{self.base}", "header": self._play_headers()}
    def liveContent(self, url):
        try:
            play_id = url; j = self._live_play(play_id)
            m3u8 = self._find_first_m3u8(j)
            if m3u8: return {"parse": 0, "url": m3u8, "header": self._play_headers()}
        except Exception: pass
        return {"parse": 1, "url": f"{self.base}/play/{url}", "header": self._play_headers()}
    def localProxy(self, param):
        action = param.get('action') if isinstance(param, dict) else None
        if action == 'play':
            play_id = param.get('play_id', ''); j = self._live_play(play_id)
            m3u8 = self._find_first_m3u8(j)
            if m3u8: return self._redirect(m3u8)
        return None
    def _redirect(self, url):
        return {"code": 302, "headers": {"Location": url}}
    def _find_first_m3u8(self, obj):
        try:
            text = json.dumps(obj, ensure_ascii=False)
            m = re.search(r'https?://[^\s"\\]+\.m3u8[^\s"\\]*', text)
            if m: return m.group(0)
        except Exception: pass
        return ''
    def _play_headers(self):
        return {'User-Agent': self.ua, 'Referer': self.base + '/', 'Origin': self.base}
    def _to_vod(self, it):
        title = it.get('title') or it.get('userNick') or it.get('userId') or 'LIVE'
        pic = it.get('thumbUrl') or it.get('ivsThumbnail') or ''
        user_id = it.get('userId', ''); play_id = it.get('code', user_id); vod_id = f"{play_id}|{user_id}|{title}"
        remarks = f"观众 {it.get('user', 0)} | 点赞 {it.get('likeCnt', 0)}"
        return {'vod_id': vod_id, 'vod_name': title, 'vod_pic': pic, 'vod_remarks': remarks}