# -*- coding: utf-8 -*-
import sys,json,time,base64,random,string,hashlib
from urllib.parse import urlencode,quote
from base.spider import Spider
from Crypto.Cipher import AES,PKCS1_v1_5
from Crypto.PublicKey import RSA
from Crypto.Util.Padding import pad,unpad

class Spider(Spider):
    def __init__(self):
        super().__init__()
        self.base_url = 'https://api-h5.uvod.tv'; self.web_url = 'https://www.uvod.tv'; self.token = ''; self._iv = b"abcdefghijklmnop"
        self._client_private = """-----BEGIN PRIVATE KEY-----
MIICdwIBADANBgkqhkiG9w0BAQEFAASCAmEwggJdAgEAAoGBAJ4FBai1Y6my4+fc
8AD5tyYzxgN8Q7M/PuFv+8i1Xje8ElXYVwzvYd1y/cNxwgW4RX0tDy9ya562V33x
6SyNr29DU6XytOeOlOkxt3gd5169K4iFaJ0l0wA4koMTcCAYVxC9B4+zzS5djYmF
MuRGfYgKYNH99vfY7BZjdAY68ty5AgMBAAECgYB1rbvHJj5wVF7Rf4Hk2BMDCi9+
zP4F8SW88Y6KrDbcPt1QvOonIea56jb9ZCxf4hkt3W6foRBwg86oZo2FtoZcpCJ+
rFqUM2/wyV4CuzlL0+rNNSq7bga7d7UVld4hQYOCffSMifyF5rCFNH1py/4Dvswm
pi5qljf+dPLSlxXl2QJBAMzPJ/QPAwcf5K5nngQtbZCD3nqDFpRixXH4aUAIZcDz
S1RNsHrT61mEwZ/thQC2BUJTQNpGOfgh5Ecd1MnURwsCQQDFhAFfmvK7svkygoKX
t55ARNZy9nmme0StMOfdb4Q2UdJjfw8+zQNtKFOM7VhB7ijHcfFuGsE7UeXBe20n
g/XLAkEAv9SoT2hgJaQxxUk4MCF8pgddstJlq8Z3uTA7JMa4x+kZfXTm/6TOo6I8
2VbXZLsYYe8op0lvsoHMFvBSBljV0QJBAKhxyoYRa98dZB5qZRskciaXTlge0WJk
kA4vvh3/o757izRlQMgrKTfng1GVfIZFqKtnBiIDWTXQw2N9cnqXtH8CQAx+CD5t
l1iT0cMdjvlMg2two3SnpOjpo7gALgumIDHAmsVWhocLtcrnJI032VQSUkNnLq9z
EIfmHDz0TPTNHBQ=
-----END PRIVATE KEY-----
"""
        self._client_public = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCeBQWotWOpsuPn3PAA+bcmM8YD
fEOzPz7hb/vItV43vBJV2FcM72Hdcv3DccIFuEV9LQ8vcmuetld98eksja9vQ1Ol
8rTnjpTpMbd4HedevSuIhWidJdMAOJKDE3AgGFcQvQePs80uXY2JhTLkRn2ICmDR
/fb32OwWY3QGOvLcuQIDAQAB
-----END PUBLIC KEY-----
"""
        self._server_public = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCeBQWotWOpsuPn3PAA+bcmM8YD
fEOzPz7hb/vItV43vBJV2FcM72Hdcv3DccIFuEV9LQ8vcmuetld98eksja9vQ1Ol
8rTnjpTpMbd4HedevSuIhWidJdMAOJKDE3AgGFcQvQePs80uXY2JhTLkRn2ICmDR
/fb32OwWY3QGOvLcuQIDAQAB
-----END PUBLIC KEY-----
"""

    def getName(self): return "UVOD"

    def init(self, extend=""):
        try: cfg = json.loads(extend) if isinstance(extend, str) and extend.strip().startswith('{') else extend if isinstance(extend, dict) else {}
        except Exception: cfg = {}
        self.base_url = cfg.get('base_url', self.base_url); self.token = cfg.get('token', self.token)
        return self.homeContent(False)

    def isVideoFormat(self, url): return any(x in url.lower() for x in ['.m3u8', '.mp4']) if url else False
    def manualVideoCheck(self): return False
    def destroy(self): pass

    def _random_key(self, n=32):
        chars = string.ascii_letters + string.digits
        return ''.join(random.choice(chars) for _ in range(n))

    def _encrypt(self, plain_text: str) -> str:
        aes_key = self._random_key(32).encode('utf-8')
        cipher = AES.new(aes_key, AES.MODE_CBC, iv=self._iv)
        ct_b64 = base64.b64encode(cipher.encrypt(pad(plain_text.encode('utf-8'), AES.block_size))).decode('utf-8')
        rsa_pub = RSA.import_key(self._server_public); rsa_cipher = PKCS1_v1_5.new(rsa_pub)
        rsa_b64 = base64.b64encode(rsa_cipher.encrypt(aes_key)).decode('utf-8')
        return f"{ct_b64}.{rsa_b64}"

    def _decrypt(self, enc_text: str) -> str:
        try:
            parts = enc_text.split('.'); ct_b64, rsa_b64 = parts
            rsa_priv = RSA.import_key(self._client_private)
            aes_key = PKCS1_v1_5.new(rsa_priv).decrypt(base64.b64decode(rsa_b64), None)
            cipher = AES.new(aes_key, AES.MODE_CBC, iv=self._iv)
            pt = unpad(cipher.decrypt(base64.b64decode(ct_b64)), AES.block_size)
            return pt.decode('utf-8', 'ignore')
        except Exception: return enc_text

    def _build_headers(self, path: str, payload: dict):
        ts = str(int(time.time() * 1000)); token = self.token or ''
        if path == '/video/latest':
            parent_id = payload.get('parent_category_id', 101); text = f"-parent_category_id={parent_id}-{ts}"
        elif path == '/video/list':
            keyword = payload.get('keyword')
            if keyword: keyword = quote(str(keyword), safe='').lower(); text = f"-keyword={keyword}&need_fragment=1&page=1&pagesize=42&sort_type=asc-{ts}"
            else: page = payload.get('page', 1); pagesize = payload.get('pagesize', 42); parent_id = payload.get('parent_category_id', ''); text = f"-page={page}&pagesize={pagesize}&parent_category_id={parent_id}&sort_type=asc-{ts}"
        elif path == '/video/info': text = f"-id={payload.get('id', '')}-{ts}"
        elif path == '/video/source': quality = payload.get('quality', ''); fragment_id = payload.get('video_fragment_id', ''); video_id = payload.get('video_id', ''); text = f"-quality={quality}&video_fragment_id={fragment_id}&video_id={video_id}-{ts}"
        else: filtered = {k: v for k, v in (payload or {}).items() if v not in (0, '0', '', False, None)}; query = urlencode(sorted(filtered.items()), doseq=True).lower(); text = f"{token}-{query}-{ts}"
        sig = hashlib.md5(text.encode('utf-8')).hexdigest()
        return {'Content-Type': 'application/json', 'X-TOKEN': token, 'X-TIMESTAMP': ts, 'X-SIGNATURE': sig, 'Origin': self.web_url, 'Referer': self.web_url + '/', 'Accept': '*/*', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'}

    def _post_api(self, path: str, payload: dict):
        url = self.base_url.rstrip('/') + path
        try:
            body = self._encrypt(json.dumps(payload, ensure_ascii=False)); headers = self._build_headers(path, payload)
            rsp = self.post(url, data=body, headers=headers, timeout=15)
            if rsp.status_code != 200 or not rsp.text: return None
            txt = rsp.text.strip(); obj = None
            try: dec = self._decrypt(txt); obj = json.loads(dec)
            except: 
                try: obj = json.loads(txt)
                except: pass
            if isinstance(obj, dict) and obj.get('error') == 0: return obj.get('data')
            return None
        except Exception: return None

    def homeContent(self, filter):
        data = self._post_api('/video/category', {}); lst = (data.get('list') or data.get('category') or []) if isinstance(data, dict) else (data or []); classes = []
        for it in lst:
            cid = it.get('id') or it.get('category_id') or it.get('value'); name = it.get('name') or it.get('label') or it.get('title')
            if cid and name: classes.append({'type_name': str(name), 'type_id': str(cid)})
        if not classes: classes = [{'type_name': '电影', 'type_id': '100'}, {'type_name': '电视剧', 'type_id': '101'}, {'type_name': '综艺', 'type_id': '102'}, {'type_name': '动漫', 'type_id': '103'}, {'type_name': '体育', 'type_id': '104'}, {'type_name': '纪录片', 'type_id': '105'}, {'type_name': '粤台专区', 'type_id': '106'}]
        return {'class': classes}

    def homeVideoContent(self):
        data = self._post_api('/video/latest', {'parent_category_id': 101})
        if isinstance(data, dict): lst = data.get('video_latest_list') or data.get('list') or data.get('rows') or data.get('items') or []
        elif isinstance(data, list): lst = data
        else: lst = []
        videos = []
        for k in lst:
            vid = k.get('id') or k.get('video_id') or k.get('videoId')
            if vid: videos.append({'vod_id': str(vid), 'vod_name': k.get('title') or k.get('name') or '', 'vod_pic': k.get('poster') or k.get('cover') or k.get('pic') or '', 'vod_remarks': k.get('score') or k.get('remarks') or ''})
        return {'list': videos}

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if str(pg).isdigit() else 1
        payload = {'parent_category_id': str(tid), 'category_id': None, 'language': None, 'year': None, 'region': None, 'state': None, 'keyword': '', 'paid': None, 'page': page, 'pagesize': 42, 'sort_field': '', 'sort_type': 'asc'}
        if isinstance(extend, dict):
            for k in ['category_id', 'year', 'region', 'state', 'keyword']:
                if extend.get(k): payload[k] = extend[k]
        data = self._post_api('/video/list', payload)
        if isinstance(data, dict): lst = data.get('video_list') or data.get('list') or data.get('rows') or data.get('items') or []; total = data.get('total', 999999)
        elif isinstance(data, list): lst = data; total = 999999
        else: lst, total = [], 0
        videos = []
        for k in lst:
            vid = k.get('id') or k.get('video_id') or k.get('videoId')
            if vid: videos.append({'vod_id': str(vid), 'vod_name': k.get('title') or k.get('name') or '', 'vod_pic': k.get('poster') or k.get('cover') or k.get('pic') or '', 'vod_remarks': k.get('score') or ''})
        return {'list': videos, 'page': page, 'pagecount': 9999, 'limit': 24, 'total': total}

    def detailContent(self, ids):
        vid = ids[0]; data = self._post_api('/video/info', {'id': vid}) or {}; video_info = data.get('video', {}) if isinstance(data, dict) else {}; fragments = data.get('video_fragment_list', []) if isinstance(data, dict) else []; play_urls = []
        if fragments:
            for fragment in fragments:
                name = fragment.get('symbol', '播放'); fragment_id = fragment.get('id', ''); qualities = fragment.get('qualities', [])
                if fragment_id and qualities: 
                    
                    max_quality = max(qualities) if qualities else 4
                    play_urls.append(f"{name}${vid}|{fragment_id}|[{max_quality}]")
        if not play_urls: play_urls.append(f"播放${vid}")
        vod = {'vod_id': str(vid), 'vod_name': video_info.get('title') or video_info.get('name') or '', 'vod_pic': video_info.get('poster') or video_info.get('cover') or video_info.get('pic') or '', 'vod_year': video_info.get('year') or '', 'vod_remarks': video_info.get('duration') or '', 'vod_content': video_info.get('description') or video_info.get('desc') or '', 'vod_play_from': '优汁🍑源', 'vod_play_url': '#'.join(play_urls) + '$$$'}
        return {'list': [vod]}

    def searchContent(self, key, quick, pg="1"):
        page = int(pg) if str(pg).isdigit() else 1
        payload = {'parent_category_id': None, 'category_id': None, 'language': None, 'year': None, 'region': None, 'state': None, 'keyword': key, 'paid': None, 'page': page, 'pagesize': 42, 'sort_field': '', 'sort_type': 'asc', 'need_fragment': 1}
        data = self._post_api('/video/list', payload)
        if isinstance(data, dict): lst = data.get('video_list') or data.get('list') or data.get('rows') or data.get('items') or []
        elif isinstance(data, list): lst = data
        else: lst = []
        videos = []
        for k in lst:
            vid = k.get('id') or k.get('video_id') or k.get('videoId')
            if vid: videos.append({'vod_id': str(vid), 'vod_name': k.get('title') or k.get('name') or '', 'vod_pic': k.get('poster') or k.get('cover') or k.get('pic') or '', 'vod_remarks': k.get('score') or ''})
        return {'list': videos}

    def _extract_first_media(self, obj):
        if not obj: return None
        if isinstance(obj, str): s = obj.strip(); return s if self.isVideoFormat(s) else None
        if isinstance(obj, (dict, list)):
            for v in (obj.values() if isinstance(obj, dict) else obj):
                r = self._extract_first_media(v)
                if r: return r
        return None

    def playerContent(self, flag, id, vipFlags):
        parts = id.split('|'); video_id = parts[0]
        if len(parts) >= 3:
            fragment_id = parts[1]; qualities_str = parts[2].strip('[]').replace(' ', ''); qualities = [q.strip() for q in qualities_str.split(',') if q.strip()]; quality = qualities[0] if qualities else '4'
            payload = {'video_id': video_id, 'video_fragment_id': int(fragment_id) if str(fragment_id).isdigit() else fragment_id, 'quality': int(quality) if str(quality).isdigit() else quality, 'seek': None}
        else: payload = {'video_id': video_id, 'video_fragment_id': 1, 'quality': 4, 'seek': None}
        data = self._post_api('/video/source', payload) or {}
        url = (data.get('video', {}).get('url', '') or data.get('url') or data.get('playUrl') or data.get('play_url') or self._extract_first_media(data) or '')
        if not url: return {'parse': 1, 'url': id}
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36', 'Referer': self.web_url + '/', 'Origin': self.web_url}
        return {'parse': 0, 'url': url, 'header': headers}

    def localProxy(self, param): return None