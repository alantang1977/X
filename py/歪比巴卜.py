# -*- coding: utf-8 -*-
"""
==========================================================
  歪比巴卜 (v.wbbb1.com) TVBox Python Spider
  适用: TVBox OK版 / FongMi版 (type=3, Chaquopy引擎)
  框架: 苹果CMS V10 (maccms) - mxpro模板
  更新: 2026-08-10

  URL规则:
    分类/筛选页: /show/{tid}-{area}-{sort}-{class}-{lang}----{page}---{year}.html
    详情页: /detail/{vid}.html
    播放页: /vplay/{vid}-{sid}-{nid}.html
    搜索页: /search/{keyword}-------------.html

  播放解密:
    1. 播放页直接包含 player_aaaa (无需 iframe 二次请求)
    2. 从 player_aaaa 提取 url(加密token), encrypt, from, link_next
    3. 根据 encrypt 解密 url 得到 PlayUrl
    4. 构建 urlValueurl = PlayUrl + "&next=//" + domain + link_next
    5. 用 RC4 + MD5 生成 key/vkey/ckey 请求参数
    6. POST 到 哈喽.850088.xyz/player/api.php 获取加密的视频URL
    7. 用 RC4 解密 aes_key/aes_iv, 再用 AES-CBC 解密得到直链
    8. 提取不到直链时走嗅探 + click 自动点击 #start

  AES-CBC 解密支持三级回退:
    1. pycryptodome (Crypto.Cipher.AES)
    2. ctypes OpenSSL (libcrypto)
    3. 纯 Python AES-128 实现 (FIPS 197 标准逆序)

  注意: 站点搜索页有验证码保护, 搜索可能返回空结果
==========================================================
"""

import sys
sys.path.append('..')

# 本地调试时模拟 base.spider.Spider 基类
try:
    from base.spider import Spider
except ImportError:
    import types
    base_mod = types.ModuleType('base')
    spider_mod = types.ModuleType('base.spider')
    class Spider:
        pass
    spider_mod.Spider = Spider
    base_mod.spider = spider_mod
    sys.modules['base'] = base_mod
    sys.modules['base.spider'] = spider_mod

import re
import json
import base64
import ssl
import hashlib
import time
import urllib.request
import urllib.error
import urllib.parse
from urllib.parse import quote, unquote, urljoin
from html import unescape as html_unescape
from json.decoder import JSONDecoder


class Spider(Spider):

    HOST = "https://v.wbbb1.com"
    UA = "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"

    # 播放器域名 (punycode: 哈喽.850088.xyz)
    PLAYER_HOST = "https://xn--qvr2v.850088.xyz"
    PLAYER_HOSTNAME = "xn--qvr2v.850088.xyz"
    PLAYER_API = "https://xn--qvr2v.850088.xyz/player/api.php"

    # 分类配置
    CATEGORIES = [
        {"type_name": "电影", "type_id": "1"},
        {"type_name": "剧集", "type_id": "2"},
        {"type_name": "动漫", "type_id": "3"},
        {"type_name": "综艺", "type_id": "4"},
    ]

    # 各分类的地区选项
    AREA_MAP = {
        "1": ["大陆", "香港", "美国", "韩国", "日本", "法国", "英国", "德国", "泰国", "台湾", "印度", "其他"],
        "2": ["大陆", "香港", "台湾", "美国", "韩国", "日本", "泰国", "英国", "其他"],
        "3": ["大陆", "日本", "欧美", "其他"],
        "4": ["大陆", "港台", "日韩", "欧美", "其他"],
    }

    # 语言选项 (通用)
    LANG_VALUES = [
        {"n": "全部", "v": ""},
        {"n": "国语", "v": "国语"}, {"n": "英语", "v": "英语"},
        {"n": "粤语", "v": "粤语"}, {"n": "韩语", "v": "韩语"},
        {"n": "日语", "v": "日语"}, {"n": "其它", "v": "其它"},
    ]

    # 排序选项
    SORT_VALUES = [
        {"n": "按最新", "v": "time"},
        {"n": "按人气", "v": "hits"},
        {"n": "按评分", "v": "score"},
    ]

    def getName(self):
        return "歪比巴卜"

    def init(self, extend=""):
        self.headers = {
            "User-Agent": self.UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": self.HOST + "/",
        }
        self._ssl_ctx = ssl.create_default_context()
        self._ssl_ctx.check_hostname = False
        self._ssl_ctx.verify_mode = ssl.CERT_NONE

    def getDependence(self):
        return []

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def action(self, action):
        pass

    def destroy(self):
        pass

    # ==================== 筛选配置 ====================
    def _build_filters(self):
        filters = {}
        year_values = [{"n": "全部", "v": ""}]
        for y in range(2026, 2014, -1):
            year_values.append({"n": str(y), "v": str(y)})

        for cat in self.CATEGORIES:
            cat_id = cat["type_id"]
            area_values = [{"n": "全部", "v": ""}]
            for a in self.AREA_MAP.get(cat_id, []):
                area_values.append({"n": a, "v": a})

            filters[cat_id] = [
                {"key": "area", "name": "地区", "value": area_values},
                {"key": "year", "name": "年份", "value": year_values},
                {"key": "lang", "name": "语言", "value": self.LANG_VALUES},
                {"key": "sort", "name": "排序", "value": self.SORT_VALUES},
            ]
        return filters

    # ==================== HTTP ====================
    def _fetch(self, url, headers=None, timeout=15, data=None):
        """GET/POST请求, 返回HTML文本
        data 不为 None 时使用 POST
        优先使用 TVBox 基类的 self.fetch()/self.post(), 回退到 urllib
        """
        hdr = headers or self.headers

        if data is not None:
            # POST 请求
            try:
                rsp = self.post(url, data=data, headers=hdr)
                if isinstance(rsp, str):
                    return rsp
                if rsp and hasattr(rsp, 'text'):
                    return rsp.text
                if rsp and hasattr(rsp, 'content'):
                    return rsp.content.decode("utf-8", errors="ignore")
            except:
                pass
            # urllib 回退
            req_url = url
            try:
                post_data = data.encode("utf-8") if isinstance(data, str) else urllib.parse.urlencode(data).encode("utf-8")
                req = urllib.request.Request(req_url, data=post_data, headers=hdr)
                opener = urllib.request.build_opener(
                    urllib.request.HTTPSHandler(context=self._ssl_ctx)
                )
                with opener.open(req, timeout=timeout) as r:
                    d = r.read()
                    return d.decode("utf-8", errors="ignore") if d else ""
            except urllib.error.HTTPError as e:
                try:
                    return e.read().decode("utf-8", errors="ignore")
                except:
                    return ""
            except Exception:
                return ""
        else:
            # GET 请求
            try:
                rsp = self.fetch(url, headers=hdr)
                if isinstance(rsp, str):
                    return rsp
                if rsp and hasattr(rsp, 'text'):
                    return rsp.text
                if rsp and hasattr(rsp, 'content'):
                    return rsp.content.decode("utf-8", errors="ignore")
            except:
                pass
            req_url = url
            if not req_url.isascii():
                req_url = quote(req_url, safe=":/?&=%-._~")
            try:
                req = urllib.request.Request(req_url, headers=hdr)
                opener = urllib.request.build_opener(
                    urllib.request.HTTPSHandler(context=self._ssl_ctx)
                )
                with opener.open(req, timeout=timeout) as r:
                    d = r.read()
                    return d.decode("utf-8", errors="ignore") if d else ""
            except urllib.error.HTTPError as e:
                try:
                    return e.read().decode("utf-8", errors="ignore")
                except:
                    return ""
            except Exception:
                return ""

    # ==================== 加解密工具 ====================
    @staticmethod
    def _rc4(key, data):
        """RC4 加解密 (对称)"""
        S = list(range(256))
        j = 0
        key_bytes = key.encode('latin-1') if isinstance(key, str) else key
        for i in range(256):
            j = (j + S[i] + key_bytes[i % len(key_bytes)]) % 256
            S[i], S[j] = S[j], S[i]
        result = bytearray()
        i2 = j = 0
        data_bytes = data.encode('latin-1') if isinstance(data, str) else data
        for byte in data_bytes:
            i2 = (i2 + 1) % 256
            j = (j + S[i2]) % 256
            S[i2], S[j] = S[j], S[i2]
            result.append(byte ^ S[(S[i2] + S[j]) % 256])
        return result.decode('latin-1')

    @staticmethod
    def _calculate(x):
        """(MD5(x) + ' P')[-22:]"""
        return (hashlib.md5(x.encode('utf-8')).hexdigest() + ' P')[-22:]

    @staticmethod
    def _calculatee(x):
        """MD5(x).hexdigest()"""
        return hashlib.md5(x.encode('utf-8')).hexdigest()

    def _enplay(self, urlValueurl, x):
        """btoa(RC4(calculate(urlValueurl), x))"""
        return base64.b64encode(
            self._rc4(self._calculate(urlValueurl), x).encode('latin-1')
        ).decode('ascii')

    def _deplay(self, urlValueurl, x):
        """RC4(calculate(urlValueurl), atob(x))"""
        return self._rc4(
            self._calculate(urlValueurl),
            base64.b64decode(x).decode('latin-1')
        )

    @staticmethod
    def _aes_cbc_decrypt(key_str, iv_str, ciphertext_b64):
        """AES-CBC 解密 (PKCS7 padding)
        优先使用 pycryptodome, 回退到 ctypes(OpenSSL), 再回退到纯Python实现
        """
        key = key_str.encode('utf-8')
        iv = iv_str.encode('utf-8')
        ciphertext = base64.b64decode(ciphertext_b64)

        # 方式1: pycryptodome
        try:
            from Crypto.Cipher import AES as _AES
            cipher = _AES.new(key, _AES.MODE_CBC, iv)
            decrypted = cipher.decrypt(ciphertext)
            pad = decrypted[-1]
            if pad <= 16:
                decrypted = decrypted[:-pad]
            return decrypted.decode('utf-8')
        except Exception:
            pass

        # 方式2: ctypes (OpenSSL libcrypto)
        try:
            import ctypes
            import ctypes.util
            lib_name = ctypes.util.find_library('crypto') or 'libcrypto.so'
            libcrypto = ctypes.CDLL(lib_name)
            # AES_set_decrypt_key(key, 128, &aes_key) -> 0 on success
            aes_key = (ctypes.c_ubyte * 244)()  # AES_KEY struct size
            ret = libcrypto.AES_set_decrypt_key(key, ctypes.c_int(128), ctypes.byref(aes_key))
            if ret == 0:
                out_buf = ctypes.create_string_buffer(len(ciphertext))
                tmp_iv = (ctypes.c_ubyte * 16)(*iv)
                # AES_cbc_encrypt(in, out, len, &key, iv, AES_DECRYPT)
                libcrypto.AES_cbc_encrypt(
                    ctypes.c_char_p(ciphertext), out_buf,
                    ctypes.c_size_t(len(ciphertext)),
                    ctypes.byref(aes_key), tmp_iv, 0  # 0 = AES_DECRYPT
                )
                decrypted = bytearray(out_buf.raw[:len(ciphertext)])
                pad = decrypted[-1]
                if pad <= 16:
                    decrypted = decrypted[:-pad]
                return decrypted.decode('utf-8')
        except Exception:
            pass

        # 方式3: 纯 Python AES-128-CBC 解密
        return Spider._pure_aes_cbc_decrypt(key, iv, ciphertext)

    # ==================== 纯 Python AES-128 ====================
    _S_BOX = [
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
        0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16,
    ]
    _R_CON = [0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x80,0x1b,0x36]

    @classmethod
    def _init_aes_tables(cls):
        if hasattr(cls, '_INV_S_BOX'):
            return
        cls._INV_S_BOX = [0] * 256
        for i in range(256):
            cls._INV_S_BOX[cls._S_BOX[i]] = i

    @staticmethod
    def _xtime(a):
        return (((a << 1) ^ 0x1B) & 0xFF) if (a & 0x80) else (a << 1)

    @staticmethod
    def _gmul(a, b):
        p = 0
        for _ in range(8):
            if b & 1:
                p ^= a
            hi = a & 0x80
            a = (a << 1) & 0xFF
            if hi:
                a ^= 0x1B
            b >>= 1
        return p

    @classmethod
    def _key_expansion(cls, key):
        Nk = len(key) // 4
        Nr = Nk + 6
        w = []
        for i in range(Nk):
            w.append(list(key[4*i:4*i+4]))
        for i in range(Nk, 4 * (Nr + 1)):
            temp = list(w[i-1])
            if i % Nk == 0:
                temp = [cls._S_BOX[temp[1]], cls._S_BOX[temp[2]], cls._S_BOX[temp[3]], cls._S_BOX[temp[0]]]
                temp[0] ^= cls._R_CON[i//Nk - 1]
            w.append([w[i-Nk][j] ^ temp[j] for j in range(4)])
        return w

    @classmethod
    def _pure_aes_cbc_decrypt(cls, key, iv, ciphertext):
        """纯 Python AES-128-CBC 解密 (FIPS 197 标准逆序)"""
        cls._init_aes_tables()
        w = cls._key_expansion(key)
        Nr = len(key) // 4 + 6

        plaintext = bytearray()
        prev = iv
        for offset in range(0, len(ciphertext), 16):
            block = ciphertext[offset:offset+16]
            state = list(block)
            # 初始 AddRoundKey: 使用最后一轮密钥 (逆序)
            for c in range(4):
                for r in range(4):
                    state[4*c+r] ^= w[Nr*4+c][r]
            # 主轮: Nr-1 downto 1 (逆序)
            for rnd in range(Nr - 1, 0, -1):
                # InvShiftRows
                state[1], state[5], state[9], state[13] = state[13], state[1], state[5], state[9]
                state[2], state[6], state[10], state[14] = state[10], state[14], state[2], state[6]
                state[3], state[7], state[11], state[15] = state[7], state[11], state[15], state[3]
                # InvSubBytes
                for i in range(16):
                    state[i] = cls._INV_S_BOX[state[i]]
                # AddRoundKey
                for c in range(4):
                    for r in range(4):
                        state[4*c+r] ^= w[rnd*4+c][r]
                # InvMixColumns
                for c in range(4):
                    s0, s1, s2, s3 = state[4*c], state[4*c+1], state[4*c+2], state[4*c+3]
                    state[4*c]   = cls._gmul(s0,14) ^ cls._gmul(s1,11) ^ cls._gmul(s2,13) ^ cls._gmul(s3,9)
                    state[4*c+1] = cls._gmul(s0,9) ^ cls._gmul(s1,14) ^ cls._gmul(s2,11) ^ cls._gmul(s3,13)
                    state[4*c+2] = cls._gmul(s0,13) ^ cls._gmul(s1,9) ^ cls._gmul(s2,14) ^ cls._gmul(s3,11)
                    state[4*c+3] = cls._gmul(s0,11) ^ cls._gmul(s1,13) ^ cls._gmul(s2,9) ^ cls._gmul(s3,14)
            # 最终轮: 使用第一轮密钥 (无 InvMixColumns)
            state[1], state[5], state[9], state[13] = state[13], state[1], state[5], state[9]
            state[2], state[6], state[10], state[14] = state[10], state[14], state[2], state[6]
            state[3], state[7], state[11], state[15] = state[7], state[11], state[15], state[3]
            for i in range(16):
                state[i] = cls._INV_S_BOX[state[i]]
            for c in range(4):
                for r in range(4):
                    state[4*c+r] ^= w[c][r]
            # XOR with prev block (CBC)
            for i in range(16):
                plaintext.append(state[i] ^ prev[i])
            prev = block

        pad = plaintext[-1]
        if 0 < pad <= 16 and all(b == pad for b in plaintext[-pad:]):
            plaintext = plaintext[:-pad]
        return plaintext.decode('utf-8')

    # ==================== 工具 ====================
    def _fix_pic(self, pic):
        if not pic:
            return ""
        pic = html_unescape(pic)
        if pic.startswith("http"):
            return pic
        if pic.startswith("//"):
            return "https:" + pic
        if not pic.startswith("/"):
            pic = "/" + pic
        return self.HOST + pic

    def _fix_url(self, url, base=None):
        if not url:
            return ""
        url = html_unescape(url).strip()
        if url.startswith("http"):
            return url
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return self.HOST + url
        if base:
            return urljoin(base, url)
        return self.HOST + "/" + url

    def _build_show_url(self, tid, extend, page):
        area = ""
        sort = ""
        cls = ""
        lang = ""
        year = ""
        if extend:
            if isinstance(extend, str):
                try:
                    extend = json.loads(extend)
                except:
                    extend = {}
            area = extend.get("area", "") or ""
            sort = extend.get("sort", "") or ""
            cls = extend.get("class", "") or ""
            lang = extend.get("lang", "") or ""
            year = extend.get("year", "") or ""

        fields = [
            str(tid), quote(area, safe=""), sort, quote(cls, safe=""),
            quote(lang, safe=""), "", "", "", str(page), "", "", year
        ]
        return "/show/" + "-".join(fields) + ".html"

    # ==================== 列表解析 ====================
    def _parse_list(self, html):
        items = []
        seen = set()
        pattern = re.compile(
            r'<a[^>]*href="(/detail/(\d+)\.html)"[^>]*>(.*?)</a>',
            re.S
        )
        for m in pattern.finditer(html):
            vid = m.group(2)
            if vid in seen:
                continue
            full_tag = m.group(0)
            content = m.group(3)

            title = ""
            tm = re.search(r'title="([^"]+)"', full_tag)
            if tm:
                title = tm.group(1).strip()
            if not title:
                tm = re.search(r'<strong>([^<]+)</strong>', content)
                if tm:
                    title = tm.group(1).strip()
            if not title:
                tm = re.search(r'alt="([^"]+)"', content)
                if tm:
                    title = tm.group(1).strip()
            if not title:
                continue

            seen.add(vid)

            pic = ""
            pm = re.search(r'data-original="([^"]+)"', content)
            if not pm:
                pm = re.search(r'data-src="([^"]+)"', content)
            if not pm:
                pm = re.search(r'<img[^>]+src="([^"]+)"', content)
            if pm:
                pic_url = pm.group(1)
                if not pic_url.startswith("data:"):
                    pic = self._fix_pic(pic_url)

            remark = ""
            rm = re.search(r'module-item-note[^>]*>([^<]+)<', content)
            if rm:
                remark = rm.group(1).strip()

            items.append({
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": remark,
            })
        return items

    # ==================== 首页 ====================
    def homeContent(self, filter):
        result = {}
        classes = []
        for c in self.CATEGORIES:
            classes.append({"type_name": c["type_name"], "type_id": c["type_id"]})
        result["class"] = classes
        result["filters"] = self._build_filters()
        html = self._fetch(self.HOST + "/")
        if html:
            result["list"] = self._parse_list(html)
        return result

    def homeVideoContent(self):
        result = {"list": []}
        html = self._fetch(self.HOST + "/")
        if html:
            result["list"] = self._parse_list(html)[:24]
        return result

    # ==================== 分类 ====================
    def categoryContent(self, tid, pg, filter, extend):
        result = {"list": [], "page": 1, "pagecount": 1, "limit": 30, "total": 0}
        try:
            page = int(pg) if pg else 1
        except:
            page = 1
        if page < 1:
            page = 1
        result["page"] = page

        path = self._build_show_url(tid, extend, page)
        html = self._fetch(self.HOST + path)
        if not html:
            return result

        items = self._parse_list(html)
        result["list"] = items
        result["limit"] = len(items)

        next_m = re.search(
            r'href="(/show/' + re.escape(tid) + r'[^"]*-' + str(page + 1) + r'---[^"]*\.html)"',
            html
        )
        result["pagecount"] = 9999 if next_m else page
        result["total"] = 9999 if next_m else len(items)
        return result

    # ==================== 详情 ====================
    def detailContent(self, ids):
        result = {"list": []}
        if not ids:
            return result
        vid = ids[0]
        url = self.HOST + "/detail/" + vid + ".html"
        html = self._fetch(url)
        if not html:
            return result

        vod = {
            "vod_id": vid,
            "vod_name": "",
            "vod_pic": "",
            "vod_year": "",
            "vod_area": "",
            "vod_actor": "",
            "vod_director": "",
            "vod_content": "",
            "vod_remarks": "",
            "vod_play_from": "",
            "vod_play_url": "",
        }

        m = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
        if m:
            vod["vod_name"] = m.group(1).strip()
        if not vod["vod_name"]:
            m = re.search(r'<title>([^<]+)</title>', html)
            if m:
                title = m.group(1).strip().split("-")[0].strip()
                vod["vod_name"] = title

        pm = re.search(r'data-original="([^"]+)"', html)
        if not pm:
            pm = re.search(r'data-src="([^"]+)"', html)
        if pm:
            vod["vod_pic"] = self._fix_pic(pm.group(1))

        dm = re.search(
            r'module-info-introduction-content[^>]*>(.*?)</div>',
            html, re.S
        )
        if dm:
            vod["vod_content"] = re.sub(r'<[^>]+>', '', dm.group(1)).strip()
        if not vod["vod_content"]:
            mdm = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]+)"', html)
            if mdm:
                raw = mdm.group(1)
                cm = re.search(r'剧情[：:]\s*(.*)', raw)
                vod["vod_content"] = cm.group(1).strip() if cm else raw.strip()

        tm = re.search(r'module-info-tag[^>]*>(.*?)</div>', html, re.S)
        if tm:
            tag_links = re.findall(r'<a[^>]*>([^<]+)</a>', tm.group(1))
            for t in tag_links:
                t = t.strip()
                if re.match(r'\d{4}', t):
                    vod["vod_year"] = t
                elif not vod["vod_area"]:
                    vod["vod_area"] = t

        for m in re.finditer(r'module-info-item-title[^>]*>([^<]+)<', html):
            label = m.group(1).strip().rstrip('：').rstrip(':').strip()
            segment = html[m.end():m.end() + 3000]
            cm = re.search(r'module-info-item-content[^>]*>(.*?)</div>', segment, re.S)
            if not cm:
                continue
            content_html = cm.group(1)
            names = re.findall(r'<a[^>]*>([^<]+)</a>', content_html)
            pure = re.sub(r'<[^>]+>', '', content_html).strip()

            if "导演" in label and names:
                vod["vod_director"] = ", ".join(n.strip() for n in names)
            elif ("主演" in label or "演员" in label) and names:
                vod["vod_actor"] = ", ".join(n.strip() for n in names)
            elif ("备注" in label or "更新" in label) and pure:
                vod["vod_remarks"] = pure

        play_from, play_url = self._parse_play_info(html)
        vod["vod_play_from"] = play_from
        vod["vod_play_url"] = play_url

        result["list"] = [vod]
        return result

    def _parse_play_info(self, html):
        play_from_list = []
        play_url_list = []

        source_names = {}
        source_tabs = re.findall(
            r'data-dropdown-value="([^"]+)"[^>]*>\s*<span>([^<]+)</span>',
            html
        )
        if source_tabs:
            for i, (val, name) in enumerate(source_tabs):
                source_names[i + 1] = name
        if not source_names:
            tab_items = re.findall(
                r'module-tab-item[^>]*>\s*<span>([^<]+)</span>',
                html
            )
            if not tab_items:
                tab_items = re.findall(
                    r'module-tab-item[^>]*>([^<]+)</',
                    html
                )
            for i, name in enumerate(tab_items):
                source_names[i + 1] = name.strip()

        all_ep_links = re.findall(
            r'href="(/vplay/(\d+-\d+-\d+)\.html)"[^>]*>(.*?)</a>',
            html, re.S
        )

        source_eps = {}
        for href, href_id, inner in all_ep_links:
            text = re.sub(r'<[^>]+>', '', inner).strip()
            if not text:
                tm = re.search(r'title="([^"]+)"', href)
                text = tm.group(1) if tm else ""
            text = text.replace("播放", "").strip() if text else ""
            if not text:
                text = "第{0}集".format(href_id.split("-")[-1])
            parts = href_id.split("-")
            if len(parts) >= 2:
                src_idx = parts[-2]
                if src_idx not in source_eps:
                    source_eps[src_idx] = []
                source_eps[src_idx].append((text, href))

        for src_idx in sorted(source_eps.keys(), key=lambda x: int(x)):
            episodes = source_eps[src_idx]
            src_idx_int = int(src_idx)
            src_name = source_names.get(src_idx_int, "线路{0}".format(src_idx))

            parts = []
            for ep_text, ep_href in episodes:
                parts.append("{0}${1}".format(ep_text, ep_href))
            if parts:
                play_from_list.append(src_name)
                play_url_list.append("#".join(parts))

        return "$$$".join(play_from_list), "$$$".join(play_url_list)

    # ==================== 搜索 ====================
    def searchContent(self, key, quick):
        """搜索: 站点对搜索页有验证码保护, 返回空列表时属正常"""
        keyword = quote(key)
        url = self.HOST + "/search/" + keyword + "-------------.html"
        html = self._fetch(url)
        if not html:
            return {"list": []}
        # 检测验证码页面 (站点对搜索启用了安全验证)
        if "系统安全验证" in html or "verify_check" in html:
            return {"list": []}
        return {"list": self._parse_list(html)}

    # ==================== 播放 ====================
    def _extract_player_aaaa(self, html):
        """从HTML提取player_aaaa JSON"""
        m = re.search(r'var\s+player_aaaa\s*=\s*', html)
        if m:
            start = m.end()
            try:
                data, _ = JSONDecoder().raw_decode(html, start)
                return data
            except:
                pass
        m = re.search(r'player_aaaa\s*=\s*(\{.*?\})\s*</script>', html, re.S)
        if m:
            try:
                return json.loads(m.group(1))
            except:
                pass
        m = re.search(r'player_aaaa\s*=\s*(\{.*?\})', html, re.S)
        if m:
            try:
                return json.loads(m.group(1))
            except:
                pass
        return None

    def _decrypt_maccms_url(self, raw_url, encrypt):
        """maccms标准解密 player_aaaa.url
        encrypt=0: 明文
        encrypt=1: URL编码
        encrypt=2: base64 + URL编码
        """
        url = raw_url
        if str(encrypt) == '2':
            try:
                url = base64.b64decode(url).decode('utf-8')
            except:
                pass
        for _ in range(3):
            try:
                decoded = unquote(url)
                if decoded == url:
                    break
                url = decoded
            except:
                break
        url = html_unescape(url)
        return url

    def playerContent(self, flag, id, vipFlags):
        """播放解密流程:
        1. 请求主播放页 /vplay/{vid}-{sid}-{nid}.html
        2. 从页面提取 player_aaaa (直接在主页面中, 无需 iframe)
        3. 解密 player_aaaa.url 得到 PlayUrl (encrypt 0/1/2)
        4. 构建 urlValueurl = PlayUrl + "&next=//" + domain + link_next
        5. 用 RC4+MD5 生成 key/vkey/ckey, POST 到 播放器API
        6. 用 RC4 解密 aes_key/aes_iv, 再用 AES-CBC 解密得到直链
        7. 提取不到直链时走嗅探模式
        """
        headers = {
            "User-Agent": self.UA,
            "Referer": self.HOST + "/",
        }

        # 构建播放页URL
        play_path = id
        if "$" in play_path:
            play_path = play_path.split("$")[-1]
        play_path = play_path.strip()
        if not play_path.startswith("http"):
            if not play_path.startswith("/"):
                play_path = "/" + play_path
            play_page_url = self.HOST + play_path
        else:
            play_page_url = play_path

        result_url = ""

        # ========== 第1步: 请求主播放页, 提取 player_aaaa ==========
        html = self._fetch(play_page_url, headers=headers)

        if html:
            player = self._extract_player_aaaa(html)
            if player:
                raw_url = player.get("url", "")
                encrypt = player.get("encrypt", 0)
                link_next = player.get("link_next", "")
                play_from = player.get("from", "")

                # 解密 PlayUrl
                play_url_value = self._decrypt_maccms_url(raw_url, encrypt)

                if play_url_value:
                    # ========== 第2步: 构建 urlValueurl ==========
                    domain = "v.wbbb1.com"
                    if link_next:
                        url_value_url = play_url_value + "&next=//" + domain + link_next
                    else:
                        url_value_url = play_url_value + "&next=//"

                    # ========== 第3步: 生成请求参数, POST 到 API ==========
                    try:
                        timestamp = int(time.time())
                        key_val = self._enplay(url_value_url, self._calculatee(url_value_url + "stray"))
                        vkey_val = self._enplay(url_value_url, str(timestamp) + self._calculatee(self._calculate(url_value_url) + "stray"))
                        ckey_val = self._enplay(url_value_url, self._calculatee(self.PLAYER_HOSTNAME + "stray"))

                        api_headers = {
                            "User-Agent": self.UA,
                            "Content-Type": "application/x-www-form-urlencoded",
                            "Referer": self.PLAYER_HOST + "/player/?url=" + quote(play_url_value, safe=""),
                            "Origin": self.PLAYER_HOST,
                        }
                        api_data = "url=" + quote(url_value_url, safe="") + \
                                   "&key=" + quote(key_val, safe="") + \
                                   "&vkey=" + quote(vkey_val, safe="") + \
                                   "&ckey=" + quote(ckey_val, safe="")

                        api_response = self._fetch(self.PLAYER_API, headers=api_headers, data=api_data)

                        if api_response:
                            resp = json.loads(api_response)
                            if resp.get("code") == 200:
                                enc_url = resp.get("url", "")
                                aes_key_enc = resp.get("aes_key", "")
                                aes_iv_enc = resp.get("aes_iv", "")

                                if enc_url and aes_key_enc and aes_iv_enc:
                                    # ========== 第4步: 解密 AES key/iv ==========
                                    aes_key = self._deplay(url_value_url, aes_key_enc)
                                    aes_iv = self._deplay(url_value_url, aes_iv_enc)

                                    # ========== 第5步: AES-CBC 解密视频URL ==========
                                    try:
                                        result_url = self._aes_cbc_decrypt(aes_key, aes_iv, enc_url)
                                    except Exception:
                                        result_url = ""
                    except Exception:
                        result_url = ""

        # ========== 返回结果 ==========
        if result_url and (".m3u8" in result_url or ".mp4" in result_url or "://" in result_url):
            return {
                "parse": 0,
                "playUrl": "",
                "jx": 0,
                "url": result_url,
                "header": headers,
            }

        # 直链提取失败, 走嗅探模式
        # 构建嗅探URL: 播放器iframe页面
        if play_url_value:
            sniff_url = self.PLAYER_HOST + "/player/?url=" + quote(play_url_value, safe="")
            if link_next:
                sniff_url += "&next=//" + domain + link_next
            else:
                sniff_url += "&next=//"
            sniff_url += "&title=play"
        else:
            sniff_url = play_page_url

        click_js = 'document.querySelector("#start").click();'

        return {
            "parse": 1,
            "playUrl": "",
            "jx": 1,
            "url": sniff_url,
            "header": headers,
            "click": click_js,
        }

    def localProxy(self, param):
        action = {
            'url': '',
            'header': '',
            'param': '',
            'type': 'string',
            'after': ''
        }
        return [200, "video/MP2T", action, ""]
