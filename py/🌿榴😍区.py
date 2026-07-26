# -*- coding: utf-8 -*-
# 🌿尼🐴出品，严禁传播仅供参考学习
import sys
import re
import json
import base64
import threading
import requests
import urllib3
import os
import time
import random
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import unquote, quote, urljoin

urllib3.disable_warnings()
sys.path.append('..')
from base.spider import Spider as BaseSpider

# ===== 纯 Python AES-128 工具（保留，以防加密）=====
_sbox = bytes([
    0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,
    0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,
    0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,
    0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,
    0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,
    0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,
    0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,
    0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,
    0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,
    0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,
    0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,
    0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,
    0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,
    0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,
    0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,
    0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16])
_inv_sbox = bytes([
    0x52,0x09,0x6a,0xd5,0x30,0x36,0xa5,0x38,0xbf,0x40,0xa3,0x9e,0x81,0xf3,0xd7,0xfb,
    0x7c,0xe3,0x39,0x82,0x9b,0x2f,0xff,0x87,0x34,0x8e,0x43,0x44,0xc4,0xde,0xe9,0xcb,
    0x54,0x7b,0x94,0x32,0xa6,0xc2,0x23,0x3d,0xee,0x4c,0x95,0x0b,0x42,0xfa,0xc3,0x4e,
    0x08,0x2e,0xa1,0x66,0x28,0xd9,0x24,0xb2,0x76,0x5b,0xa2,0x49,0x6d,0x8b,0xd1,0x25,
    0x72,0xf8,0xf6,0x64,0x86,0x68,0x98,0x16,0xd4,0xa4,0x5c,0xcc,0x5d,0x65,0xb6,0x92,
    0x6c,0x70,0x48,0x50,0xfd,0xed,0xb9,0xda,0x5e,0x15,0x46,0x57,0xa7,0x8d,0x9d,0x84,
    0x90,0xd8,0xab,0x00,0x8c,0xbc,0xd3,0x0a,0xf7,0xe4,0x58,0x05,0xb8,0xb3,0x45,0x06,
    0xd0,0x2c,0x1e,0x8f,0xca,0x3f,0x0f,0x02,0xc1,0xaf,0xbd,0x03,0x01,0x13,0x8a,0x6b,
    0x3a,0x91,0x11,0x41,0x4f,0x67,0xdc,0xea,0x97,0xf2,0xcf,0xce,0xf0,0xb4,0xe6,0x73,
    0x96,0xac,0x74,0x22,0xe7,0xad,0x35,0x85,0xe2,0xf9,0x37,0xe8,0x1c,0x75,0xdf,0x6e,
    0x47,0xf1,0x1a,0x71,0x1d,0x29,0xc5,0x89,0x6f,0xb7,0x62,0x0e,0xaa,0x18,0xbe,0x1b,
    0xfc,0x56,0x3e,0x4b,0xc6,0xd2,0x79,0x20,0x9a,0xdb,0xc0,0xfe,0x78,0xcd,0x5a,0xf4,
    0x1f,0xdd,0xa8,0x33,0x88,0x07,0xc7,0x31,0xb1,0x12,0x10,0x59,0x27,0x80,0xec,0x5f,
    0x60,0x51,0x7f,0xa9,0x19,0xb5,0x4a,0x0d,0x2d,0xe5,0x7a,0x9f,0x93,0xc9,0x9c,0xef,
    0xa0,0xe0,0x3b,0x4d,0xae,0x2a,0xf5,0xb0,0xc8,0xeb,0xbb,0x3c,0x83,0x53,0x99,0x61,
    0x17,0x2b,0x04,0x7e,0xba,0x77,0xd6,0x26,0xe1,0x69,0x14,0x63,0x55,0x21,0x0c,0x7d])
_rcon = [0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x80,0x1b,0x36]
def _xtime(a): return ((a << 1) ^ 0x1b) & 0xff if a & 0x80 else (a << 1) & 0xff
def _gf_mul(a, b):
    r = 0
    for _ in range(8):
        if b & 1: r ^= a
        a = _xtime(a)
        b >>= 1
    return r
_mul_e = bytes(_gf_mul(0x0e, i) for i in range(256))
_mul_b = bytes(_gf_mul(0x0b, i) for i in range(256))
_mul_d = bytes(_gf_mul(0x0d, i) for i in range(256))
_mul_9 = bytes(_gf_mul(0x09, i) for i in range(256))
_key_schedules = {}
def _key_schedule(key):
    k = bytes(key)
    if k in _key_schedules: return _key_schedules[k]
    w = []
    for i in range(4): w.append([key[4*i], key[4*i+1], key[4*i+2], key[4*i+3]])
    for i in range(4, 44):
        temp = w[i-1][:]
        if i % 4 == 0:
            temp = temp[1:] + temp[:1]
            temp = [_sbox[b] for b in temp]
            temp[0] ^= _rcon[i//4 - 1]
        w.append([w[i-4][j] ^ temp[j] for j in range(4)])
    _key_schedules[k] = w
    return w
def _dec_block(block, w):
    s0,s1,s2,s3,s4,s5,s6,s7,s8,s9,s10,s11,s12,s13,s14,s15 = block
    s0 ^= w[40][0]; s1 ^= w[40][1]; s2 ^= w[40][2]; s3 ^= w[40][3]
    s4 ^= w[41][0]; s5 ^= w[41][1]; s6 ^= w[41][2]; s7 ^= w[41][3]
    s8 ^= w[42][0]; s9 ^= w[42][1]; s10^= w[42][2]; s11^= w[42][3]
    s12^= w[43][0]; s13^= w[43][1]; s14^= w[43][2]; s15^= w[43][3]
    box = _inv_sbox
    for rnd in range(9, 0, -1):
        t0=box[s0]; t1=box[s13]; t2=box[s10]; t3=box[s7]
        t4=box[s4]; t5=box[s1]; t6=box[s14]; t7=box[s11]
        t8=box[s8]; t9=box[s5]; t10=box[s2]; t11=box[s15]
        t12=box[s12]; t13=box[s9]; t14=box[s6]; t15=box[s3]
        rk=w[rnd*4]; t0^=rk[0]; t1^=rk[1]; t2^=rk[2]; t3^=rk[3]
        rk=w[rnd*4+1]; t4^=rk[0]; t5^=rk[1]; t6^=rk[2]; t7^=rk[3]
        rk=w[rnd*4+2]; t8^=rk[0]; t9^=rk[1]; t10^=rk[2]; t11^=rk[3]
        rk=w[rnd*4+3]; t12^=rk[0]; t13^=rk[1]; t14^=rk[2]; t15^=rk[3]
        s0 =_mul_e[t0]^_mul_b[t1]^_mul_d[t2]^_mul_9[t3]
        s1 =_mul_9[t0]^_mul_e[t1]^_mul_b[t2]^_mul_d[t3]
        s2 =_mul_d[t0]^_mul_9[t1]^_mul_e[t2]^_mul_b[t3]
        s3 =_mul_b[t0]^_mul_d[t1]^_mul_9[t2]^_mul_e[t3]
        s4 =_mul_e[t4]^_mul_b[t5]^_mul_d[t6]^_mul_9[t7]
        s5 =_mul_9[t4]^_mul_e[t5]^_mul_b[t6]^_mul_d[t7]
        s6 =_mul_d[t4]^_mul_9[t5]^_mul_e[t6]^_mul_b[t7]
        s7 =_mul_b[t4]^_mul_d[t5]^_mul_9[t6]^_mul_e[t7]
        s8 =_mul_e[t8]^_mul_b[t9]^_mul_d[t10]^_mul_9[t11]
        s9 =_mul_9[t8]^_mul_e[t9]^_mul_b[t10]^_mul_d[t11]
        s10=_mul_d[t8]^_mul_9[t9]^_mul_e[t10]^_mul_b[t11]
        s11=_mul_b[t8]^_mul_d[t9]^_mul_9[t10]^_mul_e[t11]
        s12=_mul_e[t12]^_mul_b[t13]^_mul_d[t14]^_mul_9[t15]
        s13=_mul_9[t12]^_mul_e[t13]^_mul_b[t14]^_mul_d[t15]
        s14=_mul_d[t12]^_mul_9[t13]^_mul_e[t14]^_mul_b[t15]
        s15=_mul_b[t12]^_mul_d[t13]^_mul_9[t14]^_mul_e[t15]
    t0=box[s0]; t1=box[s13]; t2=box[s10]; t3=box[s7]
    t4=box[s4]; t5=box[s1]; t6=box[s14]; t7=box[s11]
    t8=box[s8]; t9=box[s5]; t10=box[s2]; t11=box[s15]
    t12=box[s12]; t13=box[s9]; t14=box[s6]; t15=box[s3]
    rk=w[0]; t0^=rk[0]; t1^=rk[1]; t2^=rk[2]; t3^=rk[3]
    rk=w[1]; t4^=rk[0]; t5^=rk[1]; t6^=rk[2]; t7^=rk[3]
    rk=w[2]; t8^=rk[0]; t9^=rk[1]; t10^=rk[2]; t11^=rk[3]
    rk=w[3]; t12^=rk[0]; t13^=rk[1]; t14^=rk[2]; t15^=rk[3]
    return bytes([t0,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12,t13,t14,t15])
def _aes_cbc_decrypt(data, key, iv):
    if not data or len(data) % 16: return data
    n = len(data) // 16
    w = _key_schedule(key)
    out = bytearray(len(data))
    prev = iv
    for i in range(n):
        block = data[i*16:(i+1)*16]
        dec = _dec_block(block, w)
        for j in range(16): out[i*16+j] = dec[j] ^ prev[j]
        prev = block
    pad = out[-1]
    if 1 <= pad <= 16: return bytes(out[:-pad])
    return bytes(out)

# ===== 全局代理 =====
_proxy_port = 0
_proxy_started = False
_proxy_session = requests.Session()
_proxy_session.verify = False
_proxy_headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://t66yy.cc/',
}
class _ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
class _ProxyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            real_url = unquote(self.path[1:])
            if not real_url or not real_url.startswith('http'):
                self.send_response(404); self.end_headers(); return
            r = _proxy_session.get(real_url, headers=_proxy_headers, timeout=20, verify=False)
            ct = r.headers.get('Content-Type', 'image/jpeg')
            self.send_response(200)
            self.send_header('Content-Type', ct)
            self.send_header('Content-Length', len(r.content))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(r.content)
        except BrokenPipeError: pass
        except Exception:
            self.send_response(404); self.end_headers()
    def log_message(self, format, *args): pass
def _find_free_port():
    import socket
    sk = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sk.bind(('127.0.0.1', 0))
    port = sk.getsockname()[1]
    sk.close()
    return port
def _start_proxy():
    global _proxy_port, _proxy_started
    if _proxy_started: return
    _proxy_port = _find_free_port()
    server = _ThreadedHTTPServer(('127.0.0.1', _proxy_port), _ProxyHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    _proxy_started = True

# ===== Spider =====
class Spider(BaseSpider):
    session = requests.Session()
    host = 'https://t66yy.cc'

    def __init__(self):
        super().__init__()
        self._categories_cache = None
        self._debug = True

    def _log(self, msg):
        if self._debug: print(f'[t66yy] {msg}')

    def getName(self): return 't66yy'
    def isVideoFormat(self, url):
        if not url: return False
        return '.m3u8' in url or '.mp4' in url or '.ts' in url
    def manualVideoCheck(self): return False
    def destroy(self): pass

    def localProxy(self, param): return [404, 'text/plain', '']

    def init(self, extend=''):
        self.session.verify = False
        self.session.headers.update(self._get_headers())
        _start_proxy()
        text = self._fetch(self.host)
        if text:
            self._load_categories(text)

    def _get_headers(self, referer=None):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': referer or self.host + '/',
        }
        return headers

    def _proxy_url(self, url):
        if not url: return ''
        if url.startswith('http://127.0.0.1'): return url
        return f'http://127.0.0.1:{_proxy_port}/{quote(url, safe="")}'

    def _fetch(self, url, referer=None, retries=3):
        for i in range(retries):
            try:
                if referer is None: referer = self.host + '/'
                headers = self._get_headers(referer)
                if i > 0: time.sleep(random.uniform(0.5, 1.5))
                r = self.session.get(url, headers=headers, timeout=30, verify=False)
                r.encoding = 'utf-8'
                if r.status_code == 200: return r.text
                elif r.status_code in [403, 429, 503]:
                    self._log(f'请求被拦截 [{r.status_code}]，重试 {i+1}/{retries}')
                else:
                    return ''
            except Exception as e:
                self._log(f'请求异常 [{e}]，重试 {i+1}/{retries}')
        return ''

    @staticmethod
    def _decode_b64(encoded_str):
        """模拟网站的 d() 函数：base64解码 -> URL解码"""
        try:
            raw = base64.b64decode(encoded_str)
            return unquote(raw.decode('utf-8'))
        except:
            return encoded_str

    # ----- 分类加载（仅视频，跳过磁力）-----
    def _load_categories(self, text):
        if not text: return
        cats = []
        seen = set()
        # 匹配 .area 区块中的 <dd> 链接
        # 每个分类链接格式：<a href="/list/数字-1.html"><script>document.write(d('...'))</script></a>
        # 我们直接在整个页面中匹配所有这样的链接，但需要跳过磁力区（通过上级 .area 的 dt 文本判断）
        # 更好的方法：先按 .area 分割，判断其 dt 是否包含“磁力”
        area_pattern = r'<div class="area">\s*<dl class="first">\s*<dt><a[^>]*>([^<]+)</a></dt>\s*<dd>(.*?)</dd>\s*</dl>\s*</div>'
        for dt_text, dd_html in re.findall(area_pattern, text, re.S):
            if '磁力' in dt_text:
                continue
            # 提取 dd 中所有链接
            for href, b64_name in re.findall(r'<a href="(/list/\d+-\d+\.html)">\s*<script[^>]*>document\.write\(d\(\'([A-Za-z0-9+/=]+)\'\)\);</script>', dd_html):
                name = self._decode_b64(b64_name)
                name = re.sub(r'<[^>]+>', '', name).strip()
                if not name or name in seen: continue
                seen.add(name)
                tid = href.split('/')[-1].split('-')[0]
                cats.append({'type_id': tid, 'type_name': name})
        self._categories_cache = cats
        self._log(f'加载分类: {len(cats)} 个')

    # ----- 列表解析（仅视频）-----
    def _parse_list(self, html):
        items = []
        # 匹配视频项：<li> <a class="thumbnail" href="/video/数字.html"> <img data-original="..."> </a> <div class="video-info"> <h5><a href="..."><script>document.write(d('...'))</script></a></h5> </div>
        # 注意标题也可能通过 script 解码
        pattern = r'<li>\s*<a class="thumbnail" href="(/video/\d+\.html)"[^>]*>.*?<img[^>]+data-original="([^"]+)"[^>]*>.*?</a>\s*<div class="video-info">\s*<h5><a[^>]*><script[^>]*>document\.write\(d\(\'([A-Za-z0-9+/=]+)\'\)\);</script></a></h5>'
        for href, pic, b64_title in re.findall(pattern, html, re.S):
            title = self._decode_b64(b64_title)
            vid = href.split('/')[-1].replace('.html', '')
            items.append({
                'vod_id': vid,
                'vod_name': title,
                'vod_pic': self._proxy_url(pic),
                'vod_remarks': '',
            })
        return items

    def _get_list(self, tid, page):
        url = f'{self.host}/list/{tid}-{page}.html'
        html = self._fetch(url, referer=f'{self.host}/list/{tid}-1.html')
        if not html: return []
        return self._parse_list(html)

    # ----- 首页（返回分类列表）-----
    def homeContent(self, filter):
        try:
            text = self._fetch(self.host)
            if text and self._categories_cache is None:
                self._load_categories(text)
            cats = self._categories_cache or []
            return {
                'class': cats,
                'filters': {},
                'type': '影视',
                'list': [],
                'page': 1, 'pagecount': 1, 'limit': 0, 'total': 0
            }
        except Exception as e:
            self._log(f'homeContent 异常: {e}')
            return {'class':[],'filters':{},'type':'影视','list':[],'page':1,'pagecount':1,'limit':0,'total':0}

    def homeVideoContent(self):
        return {'list': []}

    # ----- 分类内容 -----
    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg) if pg else 1
            items = self._get_list(tid, page)
            total_page = page + 1
            if page == 1:
                html = self._fetch(f'{self.host}/list/{tid}-1.html')
                if html:
                    pages = re.findall(r'/list/\d+-(\d+)\.html', html)
                    if pages: total_page = max(int(p) for p in pages)
            return {'list': items, 'page': page, 'pagecount': total_page, 'limit': len(items), 'total': total_page * len(items)}
        except Exception as e:
            self._log(f'categoryContent 异常: {e}')
            return {'list': [], 'page': 1, 'pagecount': 1, 'limit': 0, 'total': 0}

    # ----- 详情解析（复用原逻辑）-----
    def _fetch_detail(self, vid):
        urls = [
            f'{self.host}/video/{vid}.html',
            f'{self.host}/v/{vid}.html',
            f'{self.host}/movie/{vid}.html',
            f'{self.host}/detail/{vid}.html',
        ]
        for url in urls:
            self._log(f'获取详情: {url}')
            html = self._fetch(url, referer=self.host)
            if html and ('video' in html or 'play' in html or 'm3u8' in html or 'mp4' in html or 'iframe' in html or 'source_id' in html):
                detail = self._parse_detail(html, vid, url)
                if detail and detail.get('vod_play_url'):
                    return detail
        # 尝试直接 play.php
        try_urls = [
            f'{self.host}/play.php?vid={vid}',
            f'{self.host}/play.php?source_id={vid}',
        ]
        for try_url in try_urls:
            self._log(f'尝试直接 play.php: {try_url}')
            r = self.session.get(try_url, headers=self._get_headers(self.host), timeout=10)
            if r.status_code == 200 and r.text:
                try:
                    data = json.loads(r.text)
                    if 'url' in data:
                        return {'vod_play_url': f'直链${data["url"]}'}
                except:
                    pass
                if '.m3u8' in r.text or '.mp4' in r.text:
                    return {'vod_play_url': f'直链${r.text.strip()}'}
        return None

    def _parse_detail(self, html, vid, base_url):
        title = ''
        m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
        if m: title = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        if not title:
            m = re.search(r'<title>([^<]+)</title>', html)
            if m: title = m.group(1).strip()
        cover = ''
        m = re.search(r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"', html)
        if m: cover = m.group(1)
        if not cover:
            m = re.search(r'<img[^>]+class="[^"]*cover[^"]*"[^>]+src="([^"]+)"', html, re.S)
            if m: cover = m.group(1)
        if not cover:
            m = re.search(r'data-original="([^"]+)"', html)
            if m: cover = m.group(1)
        play_urls = []
        seen = set()
        def add(label, url):
            if url in seen: return
            seen.add(url)
            play_urls.append(f'{label}${url}')

        # 播放链接提取（不含磁力）
        for link in set(re.findall(r'href=["\']?(/[^"\'<>\s]*play\.php[^"\'<>\s]*)', html)):
            full = urljoin(base_url, link)
            if 'site_id=' in full and 'source_id=' in full:
                add('主线路', full)
            else:
                add('备用播放', full)
        for link in set(re.findall(r'href=["\']?(https?://[^"\'<>\s]*play\.php[^"\'<>\s]*)', html)):
            if 'site_id=' in link and 'source_id=' in link:
                add('主线路', link)
            else:
                add('备用播放', link)
        for media in set(re.findall(r'https?://[^\s"\'<>]+\.(?:m3u8|mp4|flv|mkv|ts)(?:\?[^\s"\'<>]*)?', html)):
            add('直链', media)
        for src in set(re.findall(r'<iframe[^>]+(?:src|data-src)=["\']([^"\']+)["\']', html)):
            if any(k in src for k in ['play.php','m3u8','mp4','embed','player']):
                add('外链', src if src.startswith('http') else urljoin(base_url, src))
        scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.S)
        for script in scripts:
            for b64 in re.findall(r'["\']([A-Za-z0-9+/]{20,}={0,2})["\']', script):
                try:
                    dec = base64.b64decode(b64).decode('utf-8')
                    if dec.startswith('http') and any(x in dec for x in ['.m3u8','.mp4','play.php']):
                        add('Base64', dec)
                except: pass
        if not play_urls:
            site_id = ''
            source_id = ''
            m_sid = re.search(r'site_id[=:](\d+)', html)
            if m_sid: site_id = m_sid.group(1)
            m_src = re.search(r'source_id[=:](\d+)', html)
            if m_src: source_id = m_src.group(1)
            if site_id and source_id:
                add('默认线路', f'https://m.892539.xyz/play.php?site_id={site_id}&source_id={source_id}')
            else:
                add('默认线路', f'{self.host}/play.php?vid={vid}')
        sources = []
        urls = []
        for i, pu in enumerate(play_urls):
            sn, url = pu.split('$', 1)
            sources.append(sn)
            urls.append(f'{sn}${url}')
        return {
            'vod_id': vid,
            'vod_name': title or vid,
            'vod_pic': self._proxy_url(cover) if cover else '',
            'vod_play_from': '$$$'.join(sources),
            'vod_play_url': '#'.join(urls),
            'vod_content': title or '',
        }

    def detailContent(self, ids):
        try:
            vid = str(ids[0] if isinstance(ids, list) else ids)
            detail = self._fetch_detail(vid)
            if not detail: return {'list': []}
            return {'list': [detail]}
        except Exception as e:
            self._log(f'detailContent 异常: {e}')
            return {'list': []}

    def playerContent(self, flag, id, vipFlags=None):
        try:
            if id and not id.startswith('http'):
                detail = self._fetch_detail(id)
                if detail and detail.get('vod_play_url'):
                    first = detail['vod_play_url'].split('#')[0]
                    if '$' in first:
                        id = first.split('$', 1)[1]
                    else:
                        id = first
            referer = self.host
            if id and id.startswith('http'):
                from urllib.parse import urlparse
                parsed = urlparse(id)
                if parsed.netloc:
                    referer = f'{parsed.scheme}://{parsed.netloc}/'
            return {
                'parse': 0,
                'url': id,
                'header': {
                    'Referer': referer,
                    'User-Agent': 'Mozilla/5.0',
                }
            }
        except Exception as e:
            self._log(f'playerContent 异常: {e}')
            return {'parse': 0, 'url': '', 'header': {}}

    def searchContent(self, key, quick, pg='1'):
        try:
            page = int(pg) if pg else 1
            # 仅搜索视频（type=1）
            url = f'{self.host}/search.php?content={quote(key)}&type=1&page={page}'
            html = self._fetch(url, referer=self.host)
            items = self._parse_list(html) if html else []
            return {'list': items, 'page': page, 'pagecount': page+1, 'limit': len(items), 'total': page*len(items)}
        except Exception as e:
            self._log(f'searchContent 异常: {e}')
            return {'list': [], 'page': 1, 'pagecount': 1, 'limit': 0, 'total': 0}