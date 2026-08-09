# -*- coding: utf-8 -*-
# @Author  : 陆小凤
# @Time    : 2026/8/6
"""
全能直播聚合插件 - 点播版 v5.6（修复缩进 + 启动即加载）
"""
import re
import sys
import os
import time
import json
import base64
import struct
import hashlib
import threading
import importlib.util
from concurrent.futures import ThreadPoolExecutor, wait, as_completed
from urllib.parse import urljoin, urlparse, urlencode, parse_qs, urlunparse
from collections import OrderedDict, defaultdict, Counter
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        def getProxyUrl(self): return "http://127.0.0.1:9978/proxy?do=py&"
        def init(self, extend): pass
        def getName(self): return "Live"
        def homeContent(self, filter): return {"class": [], "filters": {}}
        def homeVod(self): return {"list": []}
        def categoryContent(self, tid, pg, filter, extend): return {"list": [], "page": 1, "pagecount": 1}
        def detailContent(self, ids): return {"list": []}
        def playerContent(self, flag, id, vipFlags): return {"parse": 0, "playUrl": "", "url": ""}
        def searchContent(self, key, quick): return {"list": []}
        def localProxy(self, params): return []
        def destroy(self): return ""

# ========================= 常量 =========================
DEFAULT_EXTERNAL_API_URL = "https://xn--v4q818bf34b.cc/helper/api.php"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else os.getcwd()
CACHE_DIR = os.path.join(SCRIPT_DIR, 'cache')
os.makedirs(CACHE_DIR, exist_ok=True)
MODULE_CACHE_DIR = os.path.join(CACHE_DIR, 'modules')
os.makedirs(MODULE_CACHE_DIR, exist_ok=True)

EPG_LOGO_URL = "https://epg.112114.xyz/logo/{name}.png"
EPG_API_URL = "http://epg.112114.xyz/?ch={name}&date={date}"
DEFAULT_IMAGE = "https://cdn.jsdelivr.net/gh/your-repo/loading.png"  # 请替换为有效占位图

PROXY_OFF = '关闭代理'
PROXY_VIDEO = '视频代理'
PROXY_ALL = '全局代理'
PROXY_LIST = '列表代理'

PROXY_ALIASES = {
    '关闭代理': PROXY_OFF, 'noproxy': PROXY_OFF, 'no': PROXY_OFF, 'off': PROXY_OFF,
    'false': PROXY_OFF, '0': PROXY_OFF, '': PROXY_OFF, False: PROXY_OFF, None: PROXY_OFF,
    '视频代理': PROXY_VIDEO, 'proxy': PROXY_VIDEO, 'video': PROXY_VIDEO,
    'true': PROXY_VIDEO, '1': PROXY_VIDEO, True: PROXY_VIDEO,
    '全局代理': PROXY_ALL, 'allproxy': PROXY_ALL, 'all': PROXY_ALL, 'global': PROXY_ALL,
    '列表代理': PROXY_LIST, 'listproxy': PROXY_LIST, 'list': PROXY_LIST,
}

BOOL_MAP = {'是': True, '否': False, '下载': True, '不下载': False,
            'true': True, 'false': False, '1': True, '0': False, True: True, False: False}

DEFAULT_LOG_DIR = '/storage/emulated/0/download/logs/'
LOG_LEVELS = {'debug': 0, 'info': 1, '警告': 1, 'warn': 1, '错误': 2, 'error': 2}


# ========================= 日志、缓存 =========================
class Logger:
    def __init__(self):
        self.enabled = False
        self.log_dir = DEFAULT_LOG_DIR
        self.level = 1
        self._buf = []
        self._lock = threading.Lock()
    def set_log_dir(self, path):
        if path and isinstance(path, str):
            self.log_dir = path.rstrip('/') + '/'
    def set_enabled(self, v):
        self.enabled = BOOL_MAP.get(v, bool(v))
        if self.enabled:
            self._buf.clear()
    def set_level(self, v):
        if isinstance(v, str):
            self.level = LOG_LEVELS.get(v.lower(), 1)
        elif isinstance(v, int):
            self.level = max(0, min(2, v))
    def log(self, msg, data=None):
        if self.level > 1:
            return
        line = f"[{time.strftime('%H:%M:%S')}] {msg}"
        if data is not None:
            line += ' ' + json.dumps(data, ensure_ascii=False, default=str)[:500]
        with self._lock:
            self._buf.append(line)
            if len(self._buf) >= 50:
                self._flush()
    def debug(self, msg, data=None):
        if not self.enabled or self.level > 0:
            return
        self.log(f"[D] {msg}", data)
    def _flush(self):
        if not self._buf:
            return
        try:
            os.makedirs(self.log_dir, exist_ok=True)
            log_file = os.path.join(self.log_dir, 'vod_plugin.log')
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write('\n'.join(self._buf) + '\n')
            self._buf.clear()
        except Exception:
            pass
    def flush(self):
        with self._lock:
            self._flush()


class DiskCache:
    def __init__(self, cache_dir, ttl=3600):
        self.cache_dir = cache_dir
        self.ttl = ttl
        os.makedirs(cache_dir, exist_ok=True)
        self._lock = threading.Lock()

    def _get_path(self, key):
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{key_hash}.json")

    def get(self, key):
        path = self._get_path(key)
        try:
            if not os.path.exists(path):
                return None
            mtime = os.path.getmtime(path)
            if time.time() - mtime > self.ttl:
                os.remove(path)
                return None
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None

    def put(self, key, value):
        path = self._get_path(key)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(value, f, ensure_ascii=False, default=str)
        except Exception:
            pass

    def clear(self):
        try:
            for fname in os.listdir(self.cache_dir):
                if fname.endswith('.json'):
                    os.remove(os.path.join(self.cache_dir, fname))
        except Exception:
            pass


class LRUCache:
    def __init__(self, maxsize=2048, ttl=300):
        self._d = OrderedDict()
        self._ttl = ttl
        self._max = maxsize
        self._lock = threading.Lock()
    def get(self, key):
        with self._lock:
            e = self._d.get(key)
            if e and time.time() - e[1] < self._ttl:
                self._d.move_to_end(key)
                return e[0]
            if e:
                del self._d[key]
        return None
    def put(self, key, val):
        with self._lock:
            if key in self._d:
                del self._d[key]
            elif len(self._d) >= self._max:
                self._d.popitem(last=False)
            self._d[key] = (val, time.time())
    def clear(self):
        with self._lock:
            self._d.clear()


# ========================= 解密模块（保留完整） =========================
_HAS_AES = False
_AES_MODE = None
try:
    from Crypto.Cipher import AES as _AES_IMPL
    _AES_MODE = 'pycryptodome'
    _HAS_AES = True
except ImportError:
    try:
        import pyaes as _AES_IMPL
        _AES_MODE = 'pyaes'
        _HAS_AES = True
    except ImportError:
        pass

def _pad_key(k):
    return k + "0000000000000000"[:16 - len(k)]

def _aes_decrypt(cipher_bytes, key, iv):
    kb = _pad_key(key).encode('latin-1')
    ib = _pad_key(iv).encode('latin-1')
    if _AES_MODE == 'pycryptodome':
        return _AES_IMPL.new(kb, _AES_IMPL.MODE_CBC, ib).decrypt(cipher_bytes)
    elif _AES_MODE == 'pyaes':
        aes = _AES_IMPL.AESModeOfOperationCBC(kb, iv=ib)
        d = _AES_IMPL.Decrypter(aes)
        r = d.feed(cipher_bytes)
        r += d.feed()
        return r
    return b''

def _strip_pkcs7(d):
    if d:
        p = d[-1]
        if 0 < p <= 16 and d[-p:] == bytes([p]) * p:
            return d[:-p]
    return d

def _parse_aes_container(raw_hex_or_b64):
    try:
        if not re.match(r'^[A-Fa-f0-9]+$', raw_hex_or_b64):
            raw = base64.b64decode(raw_hex_or_b64).decode('ascii', errors='ignore')
            if not raw.startswith('24'):
                return None
            hex_data = raw
        else:
            hex_data = raw_hex_or_b64
        hex_data = re.sub(r'\s+', '', hex_data)
        if len(hex_data) % 2:
            hex_data = hex_data[:-1]
        raw_str = bytes.fromhex(hex_data).decode('latin-1').lower()
        ks = raw_str.find('$#')
        if ks < 0:
            return None
        ke = raw_str.find('#$', ks + 2)
        if ke < 0:
            return None
        key = raw_str[ks+2:ke]
        iv = raw_str[-13:]
        hdr = hex_data.find('2324')
        if hdr < 0:
            return None
        cipher_hex = hex_data[hdr+4:-26]
        if len(cipher_hex) < 32:
            return None
        cipher = bytes.fromhex(cipher_hex)
        return key, iv, cipher
    except Exception:
        return None

def decrypt_cbc(hex_data):
    params = _parse_aes_container(hex_data)
    if not params:
        return None
    key, iv, cipher = params
    decrypted = _strip_pkcs7(_aes_decrypt(cipher, key, iv))
    result = decrypted.decode('utf-8', errors='replace').strip()
    if result.startswith('{') or result.startswith('['):
        return result
    return None

def decode_png_encrypted(content):
    if not content or len(content) < 50:
        return None
    try:
        c = content.strip()
        r = len(c) % 4
        if r:
            c += '=' * (4 - r)
        raw = base64.b64decode(c).decode('ascii', errors='ignore')
        if not raw.startswith('24'):
            return None
        params = _parse_aes_container(raw)
        if not params:
            return None
        key, iv, cipher = params
        decrypted = _strip_pkcs7(_aes_decrypt(cipher, key, iv))
        result = decrypted.decode('utf-8', errors='replace')
        json.loads(result)
        return result
    except Exception:
        return None

def decode_bmp(content):
    if len(content) < 100 or content[:2] != b'BM':
        return None
    try:
        off = struct.unpack('<I', content[10:14])[0]
        px = content[off:]
        for k in [0x9B, 0xAF, 0x5A, 0x66, 0x88, 0x77]:
            txt = bytes([b ^ k for b in px]).decode('utf-8', errors='replace')
            if '#genre' in txt:
                return txt
            s = txt.find('{')
            if s < 0:
                s = txt.find('[')
            if s >= 0:
                d, end = 0, 0
                for i, ch in enumerate(txt[s:]):
                    if ch == '{':
                        d += 1
                    elif ch == '}':
                        d -= 1
                        if d == 0:
                            end = i + 1
                            break
                if end > 0:
                    try:
                        json.loads(txt[s:s+end])
                        return txt[s:s+end]
                    except Exception:
                        pass
    except Exception:
        pass
    return None

def decode_image(content):
    if not content:
        return None
    if content[:4] == b'RIFF' and b'WEBP' in content[:12]:
        for b64 in re.findall(r'[A-Za-z0-9+/=]{200,}', content.decode('latin-1')):
            try:
                p = 4 - len(b64) % 4
                if p != 4:
                    b64 += '=' * p
                d = base64.b64decode(b64)
                try:
                    return json.dumps(json.loads(d))
                except Exception:
                    pass
            except Exception:
                continue
    if content[:4] == b'\x89PNG':
        iend = content.rfind(b'IEND')
        if iend > 0:
            after = content[iend+8:]
            if len(after) > 50:
                for b64 in re.findall(rb'[A-Za-z0-9+/]{100,}=*', after):
                    try:
                        p = 4 - len(b64) % 4
                        if p != 4:
                            b64 += b'=' * p
                        d = base64.b64decode(b64)
                        try:
                            return json.dumps(json.loads(d))
                        except Exception:
                            pass
                    except Exception:
                        continue
            try:
                bs = after.find(b'MjQ')
                if bs >= 0:
                    bc = bytes([b for b in after[bs:] if b in b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/='])
                    if bc:
                        r = decode_png_encrypted(bc.decode('ascii'))
                        if r:
                            return r
            except Exception:
                pass
    pos = content.rfind(b'\xff\xd9')
    if pos >= 0 and pos + 2 < len(content):
        ex = content[pos+2:]
        if ex.strip():
            try:
                return json.dumps(json.loads(ex))
            except Exception:
                pass
            try:
                d = base64.b64decode(ex).decode('utf-8', errors='ignore')
                s = d.find('{')
                if s < 0:
                    s = d.find('[')
                if s >= 0:
                    return d[s:]
            except Exception:
                pass
    try:
        txt = content.decode('utf-8', errors='ignore').strip()
        if txt:
            try:
                return json.dumps(json.loads(txt))
            except Exception:
                pass
            for b64 in re.findall(r'[A-Za-z0-9+/=]{100,}', txt):
                try:
                    p = 4 - len(b64) % 4
                    if p != 4:
                        b64 += '=' * p
                    d = base64.b64decode(b64).decode('utf-8', errors='ignore')
                    s = d.find('{')
                    if s < 0:
                        s = d.find('[')
                    if s >= 0:
                        json.loads(d[s:])
                        return d[s:]
                except Exception:
                    continue
    except Exception:
        pass
    return None

def try_decrypt_content(content, url='', external_api_url=DEFAULT_EXTERNAL_API_URL, session=None):
    if not content:
        return None
    try:
        json.loads(content)
        return content
    except Exception:
        pass
    if isinstance(content, str) and len(content) > 100:
        c = re.sub(r'\s+', '', content)
        if re.match(r'^[A-Fa-f0-9]+$', c) and len(c) > 100:
            r = decrypt_cbc(c)
            if r:
                return r
    if isinstance(content, str) and '**' in content:
        try:
            m = re.search(r'[A-Za-z0-9]{8}\*\*(.+)', content, re.DOTALL)
            if m:
                d = base64.b64decode(m.group(1).strip()).decode('utf-8', errors='replace')
                json.loads(d.lstrip('\ufeff').strip(), strict=False)
                return d
        except Exception:
            pass
    if isinstance(content, str) and content[:2] == 'BM':
        r = decode_bmp(content.encode('latin-1'))
        if r:
            return r
    if isinstance(content, str):
        try:
            r = decode_image(content.encode('latin-1'))
            if r and (r.startswith('{') or r.startswith('[')):
                return r
        except Exception:
            pass
    m = re.search(r'\{[\s\S]*\}', content)
    if m:
        try:
            return m.group()
        except Exception:
            pass
    if external_api_url and session:
        try:
            if '?url=' in external_api_url:
                resp = session.get(external_api_url + url, timeout=(5, 10))
            else:
                resp = session.post(external_api_url,
                    json={"action": "fetch_content", "params": {"url": url}, "ts": int(time.time())},
                    timeout=(5, 10))
            if resp.status_code == 200:
                data = resp.json()
                if data.get('status') == 'success':
                    r = data.get('formattedContent') or data.get('data', '')
                    if r:
                        return r
        except Exception:
            pass
    return None


# ========================= 智能匹配器 =========================
class SmartMatcher:
    _REGEX_META = re.compile(r'[\\^$.|?*+(){}\[\]]')
    _cache = {}

    @classmethod
    def compile(cls, items):
        if isinstance(items, str):
            items = [v.strip() for v in items.split(',') if v.strip()]
        elif not isinstance(items, list):
            items = []
        result = []
        for item in items:
            s = str(item).strip()
            if not s:
                continue
            if s in cls._cache:
                result.append(cls._cache[s])
                continue
            if cls._REGEX_META.search(s):
                try:
                    m = ('re', re.compile(s, re.IGNORECASE))
                except re.error:
                    m = ('sub', s.lower())
            else:
                m = ('sub', s.lower())
            cls._cache[s] = m
            result.append(m)
        return result

    @staticmethod
    def match_any(ch, patterns, fields):
        for mode, pat in patterns:
            for fld in fields:
                val = ch.get(fld, '') if fld != 'id' else ch.get('id', '')
                if mode == 'sub':
                    if pat in val.lower():
                        return True
                else:
                    if pat.search(val):
                        return True
        return False


# ========================= 名称规范化模块 =========================
class ChannelNormalizer:
    QUALITY_PATTERN = re.compile(
        r"超高清|超清|高清|标清|蓝光|HD|UHD|FHD|SD|4K|8K|HEVC|H\.?265|IPV6|IPV4|50FPS",
        re.IGNORECASE,
    )
    OPERATOR_PATTERN = re.compile(
        r"电信|联通|移动|广电|歌华|华数|鹏博士|IPTV|备用|备\d|线路\s*\d*|高码|低码|测试",
        re.IGNORECASE,
    )
    T2S_MAP = str.maketrans({
        '衛': '卫', '視': '视', '體': '体', '綜': '综', '電': '电', '劇': '剧',
        '場': '场', '鳳': '凤', '際': '际', '國': '国', '頻': '频', '聞': '闻',
        '財': '财', '經': '经', '軍': '军', '農': '农', '紀': '纪', '錄': '录',
        '藝': '艺', '臺': '台', '華': '华', '廣': '广', '東': '东', '語': '语',
        '樂': '乐', '戲': '戏', '龍': '龙', '兒': '儿', '風': '风', '雲': '云',
        '緯': '纬', '來': '来', '傳': '传', '統': '统', '醫': '医', '療': '疗',
        '釣': '钓', '魚': '鱼', '灣': '湾', '慶': '庆', '寧': '宁', '號': '号',
        '線': '线', '聲': '声', '點': '点', '響': '响', '業': '业', '產': '产',
        '護': '护', '後': '后', '將': '将', '馬': '马', '鳥': '鸟', '寶': '宝',
        '萬': '万', '與': '与', '開': '开', '關': '关', '觀': '观', '區': '区',
        '縣': '县', '麗': '丽', '陸': '陆', '葉': '叶', '雙': '双', '豐': '丰',
        '頭': '头', '陽': '阳', '義': '义', '術': '术', '畫': '画', '學': '学',
        '時': '时', '間': '间', '實': '实', '現': '现', '當': '当', '發': '发',
        '愛': '爱', '歡': '欢', '兩': '两', '個': '个', '靈': '灵', '嶺': '岭',
        '輪': '轮', '轉': '转', '遊': '游', '橋': '桥',
    })
    CN_NUM = {
        '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8,
        '九': 9, '十': 10, '十一': 11, '十二': 12, '十三': 13, '十四': 14,
        '十五': 15, '十六': 16, '十七': 17,
    }

    BUILTIN_MAP = {
        'CCTV1': 'CCTV1综合', 'CCTV2': 'CCTV2财经', 'CCTV3': 'CCTV3综艺',
        'CCTV4': 'CCTV4中文国际', 'CCTV5': 'CCTV5体育', 'CCTV5+': 'CCTV5+体育赛事',
        'CCTV6': 'CCTV6电影', 'CCTV7': 'CCTV7国防军事', 'CCTV8': 'CCTV8电视剧',
        'CCTV9': 'CCTV9纪录', 'CCTV10': 'CCTV10科教', 'CCTV11': 'CCTV11戏曲',
        'CCTV12': 'CCTV12社会与法', 'CCTV13': 'CCTV13新闻', 'CCTV14': 'CCTV14少儿',
        'CCTV15': 'CCTV15音乐', 'CCTV16': 'CCTV16奥林匹克', 'CCTV17': 'CCTV17农业农村',
        'CCTV4K': 'CCTV4K超高清', 'CCTV8K': 'CCTV8K超高清',
        'CCTV4欧洲': 'CCTV4欧洲', 'CCTV4美洲': 'CCTV4美洲',
        'CGTN': 'CGTN', 'CGTN英语': 'CGTN英语', 'CGTN纪录': 'CGTN纪录',
        'CGTN俄语': 'CGTN俄语', 'CGTN法语': 'CGTN法语', 'CGTN西语': 'CGTN西语', 'CGTN阿语': 'CGTN阿语',
        '湖南卫视': '湖南卫视', '浙江卫视': '浙江卫视', '东方卫视': '东方卫视',
        '江苏卫视': '江苏卫视', '北京卫视': '北京卫视', '广东卫视': '广东卫视',
        '深圳卫视': '深圳卫视', '山东卫视': '山东卫视', '天津卫视': '天津卫视',
        '安徽卫视': '安徽卫视', '湖北卫视': '湖北卫视', '四川卫视': '四川卫视',
        '重庆卫视': '重庆卫视', '河南卫视': '河南卫视', '河北卫视': '河北卫视',
        '江西卫视': '江西卫视', '辽宁卫视': '辽宁卫视', '黑龙江卫视': '黑龙江卫视',
        '吉林卫视': '吉林卫视', '广西卫视': '广西卫视', '贵州卫视': '贵州卫视',
        '云南卫视': '云南卫视', '陕西卫视': '陕西卫视', '山西卫视': '山西卫视',
        '甘肃卫视': '甘肃卫视', '青海卫视': '青海卫视', '宁夏卫视': '宁夏卫视',
        '西藏卫视': '西藏卫视', '新疆卫视': '新疆卫视', '内蒙古卫视': '内蒙古卫视',
        '海南卫视': '海南卫视', '东南卫视': '东南卫视', '厦门卫视': '厦门卫视',
        '大湾区卫视': '大湾区卫视', '卡酷少儿': '卡酷少儿', '金鹰卡通': '金鹰卡通',
        '炫动卡通': '炫动卡通', '优漫卡通': '优漫卡通',
        '凤凰卫视中文台': '凤凰卫视中文台', '凤凰卫视资讯台': '凤凰卫视资讯台',
        '凤凰卫视香港台': '凤凰卫视香港台', '凤凰卫视电影台': '凤凰卫视电影台',
        'TVB翡翠台': 'TVB翡翠台', 'TVB明珠台': 'TVB明珠台', 'TVB J2': 'TVB J2',
        '无线新闻台': '无线新闻台', 'ViuTV': 'ViuTV',
        '中天综合台': '中天综合台', '中天新闻台': '中天新闻台',
        '东森新闻台': '东森新闻台', '东森电影台': '东森电影台',
        '三立台湾台': '三立台湾台', '三立都会台': '三立都会台',
        '民视无线台': '民视无线台', '台视': '台视', '中视': '中视', '华视': '华视',
        '公视': '公视', 'TVBS': 'TVBS', 'TVBS新闻台': 'TVBS新闻台',
    }

    def __init__(self, ext_config=None):
        self.config = ext_config or {}
        self.enabled = self.config.get('启用', True)
        self._canonical_map = {}
        self._build_map()

    def _build_map(self):
        self._canonical_map = {}
        def seed(canonical):
            k = self.normalize_key(canonical)
            if k and k not in self._canonical_map:
                self._canonical_map[k] = canonical
        for name in self.BUILTIN_MAP.values():
            seed(name)
        alias_path = self.config.get('aliases_path') or os.path.join(
            SCRIPT_DIR, 'channel_db.json'
        )
        if os.path.exists(alias_path):
            try:
                with open(alias_path, 'r', encoding='utf-8') as f:
                    db = json.load(f)
                aliases = db.get('builtin_aliases', {})
                for canonical, alias_list in aliases.items():
                    seed(canonical)
                    for alias in (alias_list if isinstance(alias_list, list) else []):
                        k = self.normalize_key(alias)
                        if k:
                            self._canonical_map[k] = canonical
            except Exception:
                pass

    @staticmethod
    def to_half_width(s):
        result = []
        for ch in s:
            code = ord(ch)
            if 0xFF01 <= code <= 0xFF5E:
                result.append(chr(code - 0xFEE0))
            elif ch == '　':
                result.append(' ')
            else:
                result.append(ch)
        return ''.join(result)

    @staticmethod
    def to_simplified(s):
        return s.translate(ChannelNormalizer.T2S_MAP)

    @classmethod
    def yangshi_to_cctv(cls, s):
        pattern = re.compile(
            r'央视\s*([0-9]{1,2}|[一二三四五六七八九十]{1,3})\s*(?:套|台|频道|综合|高清)?'
        )
        def replacer(m):
            num = m.group(1)
            if num.isdigit():
                n = int(num)
            else:
                n = cls.CN_NUM.get(num)
            return f'CCTV{n}' if n else m.group(0)
        return pattern.sub(replacer, s)

    @classmethod
    def normalize_key(cls, name):
        if not name:
            return ''
        s = cls.yangshi_to_cctv(cls.to_simplified(cls.to_half_width(str(name).strip()))).upper()
        cctv_match = re.search(
            r'CCTV[-\s]*(\d{1,2})(K)?\s*(\+|PLUS|加)?', s, re.IGNORECASE
        )
        if cctv_match:
            num = cctv_match.group(1)
            is_k = cctv_match.group(2)
            is_plus = cctv_match.group(3)
            if is_k:
                return f'CCTV{num}K'
            key = f'CCTV{num}'
            if is_plus:
                key += '+'
            if num == '4':
                if re.search(r'欧洲|欧', s):
                    key += '欧'
                elif re.search(r'美洲|美', s):
                    key += '美'
            return key
        s = cls.QUALITY_PATTERN.sub('', s)
        s = cls.OPERATOR_PATTERN.sub('', s)
        s = re.sub(r'[\s\-_·.|"\'’，,、（）()\[\]【】]', '', s)
        return s

    def normalize(self, name):
        if not name or not self.enabled:
            return name
        key = self.normalize_key(name)
        return self._canonical_map.get(key, name.strip())

    def logo_match_name(self, name):
        if not name:
            return ''
        raw = self.yangshi_to_cctv(self.to_simplified(self.to_half_width(str(name).strip())))
        cc = re.search(r'CCTV[-\s]*(\d{1,2})(K)?\s*(\+|PLUS|加)?', raw, re.IGNORECASE)
        if cc:
            num = cc.group(1)
            is_k = cc.group(2)
            is_plus = cc.group(3)
            if is_k:
                return f'CCTV{num}K'
            if num == '4':
                if re.search(r'欧', raw):
                    return 'CCTV4欧洲'
                if re.search(r'美', raw):
                    return 'CCTV4美洲'
            return f'CCTV{num}{"+" if is_plus else ""}'
        s = self.QUALITY_PATTERN.sub('', raw)
        s = self.OPERATOR_PATTERN.sub('', s)
        s = re.sub(r'[（(\[【]\s*[)）\]【】]', '', s)
        s = re.sub(r'^[\s\-_·.|]+|[\s\-_·.|]+$', '', s).strip()
        return s if s else raw


# ========================= 主类 Spider（所有方法在类内部） =========================
class Spider(BaseSpider):
    MODULE_CACHE_TTL = 600
    URL_CACHE_TTL = 3600
    EPG_CACHE_TTL = 300
    RETRY_COUNT = 2

    def __init__(self):
        super().__init__()
        self.logger = Logger()
        self.session = None
        self._proxy_session = None
        self._proxy_ready = threading.Event()
        self._proxy_url = None
        self._disk_cache = DiskCache(os.path.join(CACHE_DIR, 'data'), ttl=3600)
        self._epg_cache = DiskCache(os.path.join(CACHE_DIR, 'epg'), ttl=self.EPG_CACHE_TTL)
        self._source_cache = DiskCache(os.path.join(CACHE_DIR, 'source'), ttl=self.URL_CACHE_TTL)
        self._channels = []
        self._channels_lock = threading.Lock()
        self._module_m3u = {}
        self._module_spiders = {}
        self._module_lock = threading.Lock()
        self._ext_cache = LRUCache(maxsize=512, ttl=300)
        self._quick_cache = LRUCache(maxsize=4096, ttl=1800)
        self.group_include = []
        self.group_exclude = []
        self.name_include = []
        self.name_exclude = []
        self.group_whitelist = []
        self.group_blacklist = []
        self.dedup_count = 3
        self.refresh_interval = 0
        self.external_api_url = DEFAULT_EXTERNAL_API_URL
        self.download_playlist = False
        self.log_dir = DEFAULT_LOG_DIR
        self.proxy_timeout = 10
        self.proxy_test_timeout = 5
        self.placeholder_name = '↓↓↓↓↓↓'
        self.max_workers = 4
        self.connect_timeout = 5
        self.read_timeout_url = 8
        self.read_timeout_api = 10
        self.sources_load_timeout = 90
        self._last_extend = None
        self._refresh_thread = None
        self._stop_refresh = False
        self._executors = []
        self._shutdown_flag = threading.Event()
        self.categories = []
        self.normalizer = None
        self._channel_index = defaultdict(list)
        self._display_names = {}
        self._channel_logos = {}
        self._source_groups = {}
        self._category_map = {}          # 静态分类有序列表
        self._category_order = []        # 所有分类顺序（接口+静态）
        self._category_type = {}         # 分类类型：'interface' 或 'static'
        self._interface_groups = {}      # 接口 -> {groups: list, group_channels: {group: [channels]}}
        self._agg_lock = threading.Lock()
        self._sources_loaded = False
        self._last_refresh_ts = 0
        self._refreshing = False
        self.epg_logo_url = EPG_LOGO_URL
        self.epg_api_url = EPG_API_URL
        self.epg_timeout = (3, 8)
        self.epg_name_map = {}

        self.direct_play = True
        self.cache_ttl = 86400
        self._cache_data = {}            # 半固化分类缓存
        self._cache_ready = False
        self._cache_lock = threading.Lock()
        self._cache_file = os.path.join(CACHE_DIR, 'full_cache.json')
        self._cache_building = False

    # ========================= 辅助方法 =========================
    def _load_config_file(self, path):
        if not path:
            return None
        if path.startswith(('http://', 'https://', 'ftp://')):
            try:
                sess = self.session if self.session else requests.Session()
                r = sess.get(path, timeout=(5, 10))
                if r.status_code == 200:
                    return r.json()
            except Exception as e:
                self.logger.log(f"远程配置下载失败: {e}")
            return None
        try:
            if path.startswith('./') or path.startswith('.\\'):
                path = os.path.join(SCRIPT_DIR, path[2:])
            elif not os.path.isabs(path):
                path = os.path.join(SCRIPT_DIR, path)
            if not os.path.exists(path):
                self.logger.log(f"配置文件不存在: {path}")
                return None
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.log(f"加载配置文件失败: {e}")
            return None

    def _load_ext_from_path(self, path):
        if not path:
            return None
        if path.startswith(('http://', 'https://', 'ftp://')):
            try:
                sess = self.session if self.session else requests.Session()
                r = sess.get(path, timeout=(5, 10))
                if r.status_code == 200:
                    return r.json()
            except Exception as e:
                self.logger.log(f"远程配置下载失败: {e}")
            return None
        candidates = []
        if os.path.isabs(path):
            candidates.append(path)
        else:
            candidates.append(os.path.join(SCRIPT_DIR, path))
            candidates.append(os.path.join(SCRIPT_DIR, path.lstrip('./.\\')))
            candidates.append(os.path.join(os.getcwd(), path))
            candidates.append(os.path.join(os.getcwd(), path.lstrip('./.\\')))
            for base in ['/sdcard/Download/', '/storage/emulated/0/Download/',
                         '/storage/emulated/0/TVBox/', '/storage/emulated/0/影视TV/',
                         '/storage/emulated/0/Download/影视TV/']:
                candidates.append(os.path.join(base, path))
                candidates.append(os.path.join(base, path.lstrip('./.\\')))
                candidates.append(os.path.join(base, os.path.basename(path)))
        for p in candidates:
            if os.path.exists(p):
                try:
                    with open(p, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except Exception as e:
                    self.logger.log(f"读取配置失败 {p}: {e}")
                    continue
        return None

    def _resolve_local_path(self, path):
        if not path or path.startswith(('http://', 'https://', 'ftp://')):
            return path
        if os.path.isabs(path):
            return path
        candidates = [
            os.path.join(SCRIPT_DIR, path),
            os.path.join(SCRIPT_DIR, path.lstrip('./.\\')),
            os.path.join(os.getcwd(), path),
            os.path.join(os.getcwd(), path.lstrip('./.\\')),
        ]
        for p in candidates:
            if os.path.exists(p):
                return p
        return candidates[0]

    def _p(self, d, *keys, default=None):
        for key in keys:
            if key in d:
                return d[key]
        return default

    def _p_bool(self, d, *keys, default=False):
        v = self._p(d, *keys, default=default)
        return BOOL_MAP.get(v, bool(v)) if not isinstance(v, bool) else v

    def _resolve_proxy_mode(self, raw):
        if raw is None:
            return PROXY_OFF
        if isinstance(raw, bool):
            return PROXY_VIDEO if raw else PROXY_OFF
        if isinstance(raw, str):
            return PROXY_ALIASES.get(raw.lower().strip(), PROXY_OFF)
        if isinstance(raw, list):
            return PROXY_ALL if raw else PROXY_OFF
        return PROXY_OFF

    def _extract_source_headers(self, live_item):
        headers = {}
        if not isinstance(live_item, dict):
            return headers
        h = live_item.get('header') or live_item.get('headers')
        if isinstance(h, dict):
            headers.update(h)
        elif isinstance(h, str):
            try:
                headers.update(json.loads(h))
            except:
                pass
        ua = live_item.get('ua') or live_item.get('user-agent') or live_item.get('User-Agent')
        if ua:
            headers['User-Agent'] = ua
        ref = live_item.get('ref') or live_item.get('referer') or live_item.get('Referer')
        if ref:
            headers['Referer'] = ref
        return headers
        
    # ========================= 初始化 =========================
    def init(self, extend):
        self._init_session()

        ext = {}
        if extend:
            extend = str(extend).strip()
            if extend.startswith('{') or extend.startswith('['):
                try:
                    ext = json.loads(extend)
                except Exception:
                    ext = {}
            else:
                loaded = self._load_ext_from_path(extend)
                if loaded and isinstance(loaded, dict):
                    ext = loaded
                    self.logger.log(f"已从路径加载配置: {extend}")
                else:
                    self.logger.log(f"无法从 ext 加载配置: {extend}")
        self._last_extend = ext
        self.logger.set_enabled(self._p_bool(ext, '启用日志'))
        self.logger.log("=" * 50 + " 启动 VOD v5.6（启动即加载） " + "=" * 50)

        config_file = ext.get('config_file', '')
        if config_file:
            file_config = self._load_config_file(config_file)
            if file_config:
                loaded_keys = 0
                for k, v in file_config.items():
                    if k not in ext:
                        ext[k] = v
                        loaded_keys += 1
                self._last_extend = ext
                self.logger.log(f"已加载外部配置: {config_file} (补充 {loaded_keys} 个参数)")

        self._parse_config(ext)
        self.logger.set_log_dir(self.log_dir)

        proxy_list = self._p(ext, '代理', default=[])
        if isinstance(proxy_list, str):
            proxy_list = [proxy_list] if proxy_list else []
        if proxy_list:
            threading.Thread(target=self._init_proxy_bg, args=(proxy_list,), daemon=True).start()
            self.logger.log(f"代理测试已启动后台任务({len(proxy_list)}个)")

        norm_config = self._p(ext, 'clean_rules', default={})
        self.normalizer = ChannelNormalizer({'clean_rules': norm_config})

        # 读取静态分类（半固化）
        self.categories = self._p(ext, 'categories', default=[])
        self._category_map = {}
        for cat in self.categories:
            cat_name = cat.get('name')
            channels = cat.get('channels', [])
            if cat_name and channels:
                norm_list = []
                seen = set()
                for ch in channels:
                    norm_ch = self.normalizer.normalize(ch)
                    if norm_ch and norm_ch not in seen:
                        seen.add(norm_ch)
                        norm_list.append(norm_ch)
                        if norm_ch not in self._display_names:
                            self._display_names[norm_ch] = ch.strip()
                if norm_list:
                    self._category_map[cat_name] = norm_list

        # ----- 构建分类顺序（先接口，后半固化） -----
        lives = self._p(ext, 'lives', default=[])
        self._source_configs = []
        for item in lives:
            if not isinstance(item, dict):
                continue
            name = item.get('name', '未命名')
            url = item.get('url')
            api = item.get('api')
            if not url and not api:
                continue
            proxy_mode = self._resolve_proxy_mode(item.get('代理', PROXY_OFF))
            headers = item.get('header', item.get('headers', {}))
            ua = item.get('ua', '')
            if ua:
                headers['User-Agent'] = ua
            ext_cfg = item.get('ext', {})
            cfg = {
                'name': name,
                'url': url,
                'api': api,
                'proxy': proxy_mode,
                'headers': headers,
                'ext': ext_cfg,
            }
            self._source_configs.append(cfg)

        # 设置分类顺序：先接口名，后半固化
        self._category_order = []
        self._category_type = {}
        for cfg in self._source_configs:
            name = cfg['name']
            self._category_order.append(name)
            self._category_type[name] = 'interface'
        for cat in self._category_map:
            self._category_order.append(cat)
            self._category_type[cat] = 'static'

        # ----- 同步加载第一个源（用于首页） -----
        first_cfg = None
        # 优先选 URL 类型（非 py），其次 api
        for cfg in self._source_configs:
            if cfg.get('url') and not cfg.get('api'):
                first_cfg = cfg
                break
        if not first_cfg:
            for cfg in self._source_configs:
                if cfg.get('api'):
                    first_cfg = cfg
                    break
        if not first_cfg and self._source_configs:
            first_cfg = self._source_configs[0]

        if first_cfg:
            self.logger.log(f"同步加载第一个源: {first_cfg['name']}")
            self._load_one_source(first_cfg)

        # ----- 后台加载剩余源 -----
        if len(self._source_configs) > 1:
            threading.Thread(target=self._load_remaining_sources, daemon=True).start()

        # ----- 尝试从磁盘加载完整缓存（若存在则直接使用） -----
        self._load_cache_from_disk()
        if self._cache_ready:
            self.logger.log("全量缓存加载成功，数据已就绪")
            if self.refresh_interval > 0:
                self._start_refresh()
        else:
            # 如果缓存无效，启动后台构建完整缓存（包括半固化分类）
            threading.Thread(target=self._build_cache_bg, daemon=True).start()
        self.logger.flush()

    def _load_remaining_sources(self):
        """后台加载除第一个外的所有源"""
        for cfg in self._source_configs[1:]:
            if self._shutdown_flag.is_set():
                break
            name = cfg['name']
            with self._channels_lock:
                if name in self._source_groups:
                    continue
            self._load_one_source(cfg)
            time.sleep(0.2)
        self.logger.debug("后台源加载完成")

    # ========================= 加载单个源（同步） =========================
    def _load_one_source(self, cfg, wait=True):
        """同步加载一个源，返回频道列表"""
        name = cfg['name']
        with self._channels_lock:
            if name in self._source_groups:
                return
        self.logger.debug(f"加载源: {name}")
        channels = []
        if cfg.get('api'):
            channels = self._load_py_source(cfg['api'], cfg)
        elif cfg.get('url'):
            # 修复：传入整个 cfg，而非拆分
            channels = self._load_url_source(cfg)
        else:
            self.logger.log(f"【{name}】跳过：无 url 或 api")
        if channels:
            with self._channels_lock:
                self._channels.extend(channels)
                # 也构建 source_groups
                groups = {}
                for ch in channels:
                    group = ch.get('group', '默认分类')
                    groups.setdefault(group, []).append(ch)
                self._source_groups[name] = groups
            self.logger.log(f"【{name}】加载 {len(channels)} 个频道, {len(groups)} 个分组")
        return channels

    def _load_py_source(self, api, cfg):
        name = cfg['name']
        try:
            merged_ext = {}
            if cfg.get('ext'):
                merged_ext.update(cfg['ext'])
            proxy_mode = cfg.get('proxy', PROXY_OFF)
            if proxy_mode == PROXY_ALL:
                merged_ext['proxy'] = [self._proxy_url] if self._proxy_url else []
            elif proxy_mode == PROXY_VIDEO:
                merged_ext['proxy'] = [self._proxy_url] if self._proxy_url else []
                merged_ext['_proxy_hint'] = True
            else:
                merged_ext['proxy'] = []

            module = self._import_py_module(api)
            if not module or not hasattr(module, 'Spider'):
                self.logger.log(f"【{name}】模块加载失败")
                return []
            spider = module.Spider()
            spider.init(json.dumps(merged_ext, ensure_ascii=False))
            with self._module_lock:
                self._module_spiders[name] = spider
            content = spider.liveContent('')
            if not content:
                self.logger.log(f"【{name}】liveContent 为空")
                return []
            # 修复：正确传递 proxy_mode 和 headers
            proxy_mode = cfg.get('proxy', PROXY_OFF)
            headers = cfg.get('headers', {})
            channels = self._parse_content(content, name, proxy_mode, source_headers=headers)
            return channels
        except Exception as e:
            self.logger.log(f"【{name}】加载异常: {e}")
            return []

    def _load_url_source(self, item):
        name = item.get('name', '未知源')
        url = item.get('url', '')
        proxy_mode = self._resolve_proxy_mode(item.get('代理'))
        source_headers = item.get('_headers', {})
        if not url:
            return []

        if not url.startswith(('http://', 'https://', 'ftp://')):
            if os.path.exists(url):
                try:
                    with open(url, 'r', encoding='utf-8') as f:
                        content = f.read()
                    self.logger.debug(f"从本地文件加载 {name}: {url}")
                    return self._parse_content(content, name, proxy_mode, source_url=url, source_headers=source_headers)
                except Exception as e:
                    self.logger.log(f"【{name}】读取本地文件失败: {e}")
                    return []
            else:
                self.logger.log(f"【{name}】本地文件不存在: {url}")
                return []

        try:
            cache_key = f"src_{hashlib.md5(url.encode()).hexdigest()}"
            cached = self._source_cache.get(cache_key)
            if cached:
                self.logger.debug(f"URL缓存命中: {name}")
                return self._parse_content(cached, name, proxy_mode, source_headers=source_headers)

            session = self._get_playback_session(proxy_mode)
            req_headers = dict(session.headers)
            req_headers.update(source_headers)

            resp = session.get(url, timeout=(self.connect_timeout, self.read_timeout_url),
                               verify=False, headers=req_headers)
            if resp.status_code != 200:
                self.logger.log(f"源返回非200: {name} [{resp.status_code}]")
                return []
            content = resp.text
            if not content:
                return []
            dec = try_decrypt_content(content, url, self.external_api_url, session)
            if dec:
                content = dec
            self._source_cache.put(cache_key, content)
            return self._parse_content(content, name, proxy_mode, source_url=url, source_headers=source_headers)
        except Exception as e:
            self.logger.log(f"加载URL失败 {name}: {e}")
            return []

    def _import_py_module(self, api):
        if api.startswith(('http://', 'https://')):
            ck = hashlib.md5(api.encode()).hexdigest() + '.py'
            cf = os.path.join(MODULE_CACHE_DIR, ck)
            if os.path.exists(cf) and time.time() - os.path.getmtime(cf) < self.MODULE_CACHE_TTL:
                fp = cf
            else:
                try:
                    resp = self.session.get(api, timeout=(self.connect_timeout, self.read_timeout_url))
                    if resp.status_code == 200:
                        with open(cf, 'w', encoding='utf-8') as f:
                            f.write(resp.text)
                        fp = cf
                    else:
                        return None
                except Exception:
                    return None
        else:
            if not os.path.isfile(api):
                return None
            fp = api
        mn = f"py_mod_{hash(fp)}"
        if mn in sys.modules:
            del sys.modules[mn]
        spec = importlib.util.spec_from_file_location(mn, fp)
        if not spec:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        sys.modules[mn] = mod
        return mod

    # ========================= 解析配置 =========================
    def _parse_config(self, ext):
        self.group_include = SmartMatcher.compile(self._p(ext, '分类包含', 'group_include', default=[]))
        self.group_exclude = SmartMatcher.compile(self._p(ext, '分类排除', 'group_exclude', default=[]))
        self.name_include = SmartMatcher.compile(self._p(ext, '节目包含', 'name_include', default=[]))
        self.name_exclude = SmartMatcher.compile(self._p(ext, '节目排除', 'name_exclude', default=[]))

        def _normalize_list(lst):
            if isinstance(lst, str):
                lst = [lst]
            elif not isinstance(lst, list):
                return []
            return [str(v).strip().lower() for v in lst if v and str(v).strip()]

        self.group_whitelist = _normalize_list(self._p(ext, '分类白名单', 'group_whitelist', default=[]))
        self.group_blacklist = _normalize_list(self._p(ext, '分类黑名单', 'group_blacklist', default=[]))

        self.dedup_count = max(1, int(self._p(ext, '重复阈值', 'dedup_count', default=3)))
        self.refresh_interval = max(0, int(self._p(ext, '刷新间隔', 'refresh_interval', default=0)))
        self.external_api_url = self._p(ext, '备用解密接口', 'external_api_url', default=DEFAULT_EXTERNAL_API_URL)
        self.download_playlist = self._p_bool(ext, '播放列表')
        self.log_dir = self._p(ext, '下载目录', 'log_dir', default=DEFAULT_LOG_DIR)
        if isinstance(self.log_dir, str) and self.log_dir:
            self.log_dir = self.log_dir.rstrip('/') + '/'
        else:
            self.log_dir = DEFAULT_LOG_DIR
        self.proxy_timeout = int(self._p(ext, '代理超时', 'proxy_timeout', default=10))
        self.proxy_test_timeout = int(self._p(ext, '代理测试超时', 'proxy_test_timeout', default=max(3, self.proxy_timeout // 2)))
        self.placeholder_name = self._p(ext, '占位名称', 'placeholder', default='↓↓↓↓↓↓')
        log_level = self._p(ext, '日志级别', 'log_level', default='info')
        self.logger.set_level(log_level)
        self.max_workers = min(16, max(1, int(self._p(ext, '最大并发', 'max_workers', default=4))))
        self.connect_timeout = max(3, int(self._p(ext, '连接超时', 'connect_timeout', default=5)))
        self.read_timeout_url = max(5, int(self._p(ext, 'URL读取超时', 'url_read_timeout', default=8)))
        self.read_timeout_api = max(5, int(self._p(ext, 'API读取超时', 'api_read_timeout', default=10)))
        self.sources_load_timeout = max(30, int(self._p(ext, '源加载超时', 'sources_load_timeout', default=90)))

        self.epg_logo_url = self._p(ext, 'epg_logo_url', default=EPG_LOGO_URL)
        self.epg_api_url = self._p(ext, 'epg_api_url', default=EPG_API_URL)
        self.epg_timeout = tuple(self._p(ext, 'epg_timeout', default=[3, 8]))
        ext_epg_map = self._p(ext, 'epg_name_map', default={})
        if ext_epg_map and isinstance(ext_epg_map, dict):
            self.epg_name_map = dict(ext_epg_map)
        else:
            self.epg_name_map = {}

        self.direct_play = self._p_bool(ext, '直连播放', 'direct_play', default=True)
        self.cache_ttl = max(60, int(self._p(ext, '缓存有效期', 'cache_ttl', default=86400)))

    # ========================= Session & 代理 =========================
    def _init_session(self):
        self.session = requests.Session()
        retry = Retry(total=2, backoff_factor=0.3, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=20)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        self.session.headers.update({'User-Agent': 'okhttp/4.12.0', 'Accept-Language': 'zh-CN,zh;q=0.9'})

    def _init_proxy_bg(self, proxy_list):
        cached = self._load_proxy_cache()
        if cached:
            self.logger.log(f"测试缓存代理: {cached}")
            if self._test_single_proxy(cached):
                self._apply_proxy(cached)
                self.logger.log(f"缓存代理可用: {cached}")
                self._proxy_ready.set()
                return
            self.logger.log("缓存代理已失效")
        if not proxy_list:
            self.logger.log("无代理列表且缓存失效，降级为直连")
            self._proxy_ready.set()
            return
        self.logger.log(f"测试代理列表({len(proxy_list)}个)...")
        found = threading.Event()
        chosen = [None]

        def test_one(p):
            if found.is_set():
                return
            if self._test_single_proxy(p):
                if not found.is_set():
                    chosen[0] = p
                    found.set()

        with ThreadPoolExecutor(max_workers=len(proxy_list)) as ex:
            futures = [ex.submit(test_one, p) for p in proxy_list]
            found.wait(timeout=self.proxy_timeout)
            for f in futures:
                f.cancel()
        if chosen[0]:
            self._apply_proxy(chosen[0])
            self._save_proxy_cache(chosen[0])
            self.logger.log(f"代理就绪: {chosen[0]}")
        else:
            self.logger.log("所有代理不可用，降级为直连")
        self._proxy_ready.set()

    def _test_single_proxy(self, proxy_url):
        try:
            timeout = self.proxy_test_timeout
            r = requests.get('https://www.google.com',
                proxies={'http': proxy_url, 'https': proxy_url},
                timeout=(timeout, timeout))
            return r.status_code < 400
        except Exception:
            return False

    def _apply_proxy(self, proxy_url):
        self._proxy_url = proxy_url
        self._proxy_session = requests.Session()
        retry = Retry(total=2, backoff_factor=0.3)
        adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=20)
        self._proxy_session.mount('http://', adapter)
        self._proxy_session.mount('https://', adapter)
        self._proxy_session.headers.update({'User-Agent': 'okhttp/4.12.0'})
        self._proxy_session.proxies = {'http': proxy_url, 'https': proxy_url}

    def _save_proxy_cache(self, proxy_url):
        try:
            path = os.path.join(CACHE_DIR, 'proxy_cache.json')
            with open(path, 'w') as f:
                json.dump({'proxy': proxy_url, 'time': time.time()}, f)
        except Exception:
            pass

    def _load_proxy_cache(self):
        try:
            path = os.path.join(CACHE_DIR, 'proxy_cache.json')
            if os.path.exists(path):
                with open(path) as f:
                    data = json.load(f)
                if time.time() - data.get('time', 0) < 86400:
                    return data.get('proxy')
        except Exception:
            pass
        return None

    def _get_playback_session(self, proxy_mode):
        if proxy_mode == PROXY_LIST:
            return self.session
        if proxy_mode in (PROXY_VIDEO, PROXY_ALL):
            if self._proxy_ready.is_set() and self._proxy_session:
                return self._proxy_session
            if self._proxy_ready.wait(timeout=5) and self._proxy_session:
                return self._proxy_session
            return self.session
        return self.session

    # ========================= 获取远程源（用于缓存构建） =========================
    def _fetch_and_merge_lives(self, ext):
        all_lives = []
        raw_lives = self._p(ext, 'lives', default=[])
        if isinstance(raw_lives, list):
            all_lives.extend(raw_lives)

        urls = self._p(ext, '接口_单仓', 'lives_urls', default=[])
        if isinstance(urls, str):
            urls = [urls] if urls else []
        elif not isinstance(urls, list):
            urls = []

        simple_urls = self._p(ext, '接口_直播', 'lives_url', default=[])
        if isinstance(simple_urls, str):
            simple_urls = [simple_urls] if simple_urls else []
        elif not isinstance(simple_urls, list):
            simple_urls = []

        for u in simple_urls:
            if isinstance(u, str) and u.strip():
                u = u.strip()
                if u.endswith('.py'):
                    all_lives.append({'name': f'接口_{len(all_lives)+1}', 'api': u})
                else:
                    all_lives.append({'name': f'接口_{len(all_lives)+1}', 'url': u})

        if urls:
            self.logger.log(f"获取远程配置: {len(urls)} 个URL")
            with ThreadPoolExecutor(max_workers=min(8, len(urls))) as ex:
                self._executors.append(ex)
                try:
                    futs = {ex.submit(self._fetch_one_remote, u): u for u in urls}
                    for fut in as_completed(futs, timeout=30):
                        if self._shutdown_flag.is_set():
                            for f in futs:
                                f.cancel()
                            break
                        try:
                            data = fut.result()
                            if data:
                                data = self._resolve_paths(data, futs[fut])
                                if isinstance(data, list):
                                    all_lives.extend(data)
                                elif isinstance(data, dict):
                                    lv = self._p(data, 'lives')
                                    if isinstance(lv, list):
                                        all_lives.extend(lv)
                        except Exception as e:
                            self.logger.log(f"远程源异常: {e}")
                finally:
                    if ex in self._executors:
                        self._executors.remove(ex)
        return self._dedup_lives(all_lives)

    def _fetch_one_remote(self, url):
        try:
            resp = self.session.get(url, timeout=(self.connect_timeout, self.read_timeout_url), verify=False)
            if resp.status_code != 200:
                return None
            text = resp.text
            try:
                return json.loads(text)
            except Exception:
                pass
            dec = try_decrypt_content(text, url, self.external_api_url, self.session)
            if dec:
                try:
                    return json.loads(dec)
                except Exception:
                    m = re.search(r'\{[\s\S]*\}', dec)
                    if m:
                        try:
                            return json.loads(m.group())
                        except Exception:
                            pass
                    m2 = re.search(r'"(?:lives)"\s*:\s*(\[[\s\S]*?\])', dec)
                    if m2:
                        try:
                            return {"lives": json.loads(m2.group(1))}
                        except Exception:
                            pass
        except Exception:
            pass
        return None

    def _dedup_lives(self, lives):
        seen = set()
        out = []
        for item in lives:
            if isinstance(item, str):
                u = item.strip()
                if u.endswith('.py'):
                    item = {'name': f'接口_{len(out)+1}', 'api': u}
                else:
                    item = {'name': f'接口_{len(out)+1}', 'url': u}
            key = item.get('url') or item.get('api') or ''
            if key and key in seen:
                continue
            if key:
                seen.add(key)
            if item.get('url'):
                item['url'] = self._resolve_local_path(item['url'])
            if item.get('api'):
                item['api'] = self._resolve_local_path(item['api'])
            item['_headers'] = self._extract_source_headers(item)
            out.append(item)
        return out

    def _resolve_paths(self, data, base_url):
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, str) and v.startswith('./'):
                    data[k] = urljoin(base_url, v)
                elif isinstance(v, (dict, list)):
                    data[k] = self._resolve_paths(v, base_url)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, str) and item.startswith('./'):
                    data[i] = urljoin(base_url, item)
                elif isinstance(item, (dict, list)):
                    data[i] = self._resolve_paths(item, base_url)
        return data

    # ========================= 加载所有源（用于后台缓存构建） =========================
    def _load_all_sources(self, lives, timeout=90):
        self._channels.clear()
        with ThreadPoolExecutor(max_workers=self.max_workers) as ex:
            self._executors.append(ex)
            try:
                futures = []
                for item in lives:
                    if item.get('api', '').endswith('.py'):
                        futures.append(ex.submit(self._load_module_source, item))
                    elif item.get('url'):
                        futures.append(ex.submit(self._load_url_source, item))
                done, not_done = wait(futures, timeout=timeout)
                for f in not_done:
                    f.cancel()
                for f in done:
                    try:
                        result = f.result()
                        if result:
                            with self._channels_lock:
                                self._channels.extend(result)
                    except Exception as e:
                        self.logger.log(f"加载源异常: {e}")
            finally:
                if ex in self._executors:
                    self._executors.remove(ex)

    def _load_module_source(self, item):
        name = item.get('name', '未知模块')
        api_path = item.get('api', '')
        proxy_mode = self._resolve_proxy_mode(item.get('代理'))
        try:
            if api_path.startswith(('http://', 'https://')):
                cache_key = hashlib.md5(api_path.encode()).hexdigest()
                local_path = os.path.join(MODULE_CACHE_DIR, f"{cache_key}.py")
                if not os.path.exists(local_path):
                    self.logger.log(f"正在下载远程模块: {api_path}")
                    resp = self.session.get(api_path, timeout=(self.connect_timeout, self.read_timeout_url))
                    if resp.status_code != 200:
                        self.logger.log(f"下载远程模块失败: {api_path}")
                        return []
                    with open(local_path, 'w', encoding='utf-8') as f:
                        f.write(resp.text)
                content = self._load_py_module(local_path, name, proxy_mode)
            else:
                if not os.path.exists(api_path):
                    self.logger.log(f"模块文件不存在: {api_path}")
                    return []
                content = self._load_py_module(api_path, name, proxy_mode)
            if content:
                self._module_m3u[name] = content
                return self._parse_content(content, name, proxy_mode)
        except Exception as e:
            self.logger.log(f"加载模块失败 {name}: {e}")
        return []

    def _load_py_module(self, api_path, name, proxy_mode):
        try:
            spec = importlib.util.spec_from_file_location(name, api_path)
            if not spec or not spec.loader:
                return None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            spider_cls = getattr(module, 'Spider', None)
            if not spider_cls:
                return None
            spider = spider_cls()
            if hasattr(spider, 'init'):
                spider.init('{}')
            with self._module_lock:
                self._module_spiders[name] = spider
            if hasattr(spider, 'liveContent'):
                return spider.liveContent('')
            return None
        except Exception as e:
            self.logger.log(f"模块执行失败 {name}: {e}")
            return None

    # ========================= 内容解析 =========================
    def _parse_content(self, content, source_name, proxy_mode, source_url='', source_headers=None):
        if not content:
            return []
        source_headers = source_headers or {}
        if isinstance(content, str):
            content = content.strip()
            if content.startswith('#EXTM3U') or content.startswith('#EXTINF'):
                return self._parse_m3u(content, source_name, proxy_mode, source_url, source_headers)
            elif content.startswith('{'):
                try:
                    data = json.loads(content)
                    return self._parse_json(data, source_name, proxy_mode, source_url, source_headers)
                except Exception:
                    pass
            elif content.startswith('['):
                try:
                    data = json.loads(content)
                    return self._parse_json(data, source_name, proxy_mode, source_url, source_headers)
                except Exception:
                    pass
            elif '#genre#' in content:
                return self._parse_txt(content, source_name, proxy_mode, source_url, source_headers)
        elif isinstance(content, (dict, list)):
            return self._parse_json(content, source_name, proxy_mode, source_url, source_headers)
        return []

    def _parse_m3u(self, content, source_name, proxy_mode, source_url='', source_headers=None):
        channels = []
        source_headers = source_headers or {}
        lines = content.split('\n')
        current = None
        group_title = source_name
        for line in lines:
            line = line.strip()
            if line.startswith('#EXTINF'):
                current = {'name': '', 'group': group_title, 'source': source_name,
                           'proxy_mode': proxy_mode, 'headers': dict(source_headers)}
                m = re.search(r'tvg-name="([^"]*)"', line)
                if m:
                    current['name'] = m.group(1)
                m = re.search(r'group-title="([^"]*)"', line)
                if m:
                    current['group'] = m.group(1)
                m = re.search(r'tvg-logo="([^"]*)"', line)
                if m:
                    current['logo'] = m.group(1)
                m = re.search(r',([^,]+)$', line)
                if m and not current['name']:
                    current['name'] = m.group(1).strip()
            elif line.startswith('#EXTVLCOPT:'):
                if current is not None:
                    opt = line[len('#EXTVLCOPT:'):].strip()
                    if opt.startswith('http-user-agent='):
                        current['headers']['User-Agent'] = opt[len('http-user-agent='):].strip()
                    elif opt.startswith('http-referrer=') or opt.startswith('http-referer='):
                        current['headers']['Referer'] = opt.split('=', 1)[1].strip()
            elif line and not line.startswith('#') and current is not None:
                current['url'] = line
                if current.get('name') and current.get('url'):
                    channels.append(current)
                current = None
        return channels

    def _parse_txt(self, content, source_name, proxy_mode, source_url='', source_headers=None):
        channels = []
        source_headers = source_headers or {}
        lines = content.split('\n')
        group = source_name
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if '#genre#' in line:
                group = line.split(',')[0].strip()
                continue
            if ',' in line:
                parts = line.split(',', 1)
                name = parts[0].strip()
                url = parts[1].strip()
                if name and url:
                    channels.append({
                        'name': name, 'group': group, 'url': url,
                        'source': source_name, 'proxy_mode': proxy_mode,
                        'headers': dict(source_headers)
                    })
        return channels

    def _parse_json(self, data, source_name, proxy_mode, source_url='', source_headers=None):
        channels = []
        source_headers = source_headers or {}
        if isinstance(data, list):
            for item in data:
                ch = self._extract_channel(item, source_name, proxy_mode, source_headers)
                if ch:
                    channels.append(ch)
        elif isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, list):
                    for item in v:
                        ch = self._extract_channel(item, source_name, proxy_mode, source_headers, group=k)
                        if ch:
                            channels.append(ch)
                elif isinstance(v, dict):
                    ch = self._extract_channel(v, source_name, proxy_mode, source_headers, group=k)
                    if ch:
                        channels.append(ch)
        return channels

    def _extract_channel(self, item, source_name, proxy_mode, source_headers, group=None):
        if not isinstance(item, dict):
            return None
        name = item.get('name') or item.get('title') or item.get('channel')
        url = item.get('url') or item.get('link') or item.get('playUrl')
        if not name or not url:
            return None
        headers = dict(source_headers)
        if 'header' in item and isinstance(item['header'], dict):
            headers.update(item['header'])
        if 'headers' in item and isinstance(item['headers'], dict):
            headers.update(item['headers'])
        if 'ua' in item:
            headers['User-Agent'] = item['ua']
        if 'referer' in item or 'ref' in item:
            headers['Referer'] = item.get('referer') or item.get('ref', '')
        raw_group = group if group is not None else item.get('group', source_name)
        if raw_group is None:
            raw_group = '未分组'
        final_group = str(raw_group).strip()
        if not final_group:
            final_group = '未分组'
        return {
            'name': str(name).strip(),
            'group': final_group,
            'url': str(url).strip(),
            'logo': item.get('logo', ''),
            'source': source_name,
            'proxy_mode': proxy_mode,
            'headers': headers
        }

    # ========================= 构建索引与缓存 =========================
    def _build_channel_index(self):
        with self._agg_lock:
            self._channel_index.clear()
            self._source_groups.clear()
            for ch in self._channels:
                raw_name = ch.get('name', '')
                norm_name = self.normalizer.normalize(raw_name) if self.normalizer else raw_name
                if not norm_name:
                    continue
                if norm_name not in self._display_names:
                    self._display_names[norm_name] = raw_name
                self._channel_index[norm_name].append(ch)
                self._source_groups[norm_name] = ch.get('group', '未分类')
                if ch.get('logo') and norm_name not in self._channel_logos:
                    self._channel_logos[norm_name] = ch['logo']

    def _build_caches(self):
        with self._agg_lock:
            cache_cats = {}
            for cat in self._category_map:
                cat_channels = self._category_map[cat]
                if not cat_channels:
                    continue
                cat_dict = {}
                for norm in cat_channels:
                    sources = self._channel_index.get(norm, [])
                    if not sources:
                        continue
                    line_infos = []
                    used_names = set()
                    for s in sources:
                        src = s.get('source', '未知源')
                        group = s.get('group', '')
                        base_name = src if not group else f"{src}|{group}"
                        if base_name not in used_names:
                            line_name = base_name
                        else:
                            idx = 1
                            while f"{base_name}-{idx}" in used_names:
                                idx += 1
                            line_name = f"{base_name}-{idx}"
                        used_names.add(line_name)
                        line_infos.append({
                            'name': line_name,
                            'url': s.get('url', ''),
                            'headers': s.get('headers', {}),
                            'proxy_mode': s.get('proxy_mode', PROXY_OFF)
                        })
                    display = self._display_names.get(norm, norm)
                    logo = self._get_logo(norm)
                    cat_dict[norm] = {
                        'display': display,
                        'logo': logo,
                        'sources': line_infos
                    }
                if cat_dict:
                    cache_cats[cat] = cat_dict

            interface_groups = {}
            for ch in self._channels:
                source = ch.get('source', '未知源')
                group = ch.get('group', '未分组')
                if not source:
                    source = '未知源'
                if not group:
                    group = '未分组'
                if source not in interface_groups:
                    interface_groups[source] = {'groups': [], 'group_channels': {}}
                if group not in interface_groups[source]['groups']:
                    interface_groups[source]['groups'].append(group)
                if group not in interface_groups[source]['group_channels']:
                    interface_groups[source]['group_channels'][group] = []
                interface_groups[source]['group_channels'][group].append(ch)

            self._interface_groups = interface_groups
            with self._cache_lock:
                self._cache_data = cache_cats
                self._cache_ready = True
            self.logger.log(f"缓存构建完成，分类数: {len(self._category_order)}，接口数: {len(interface_groups)}")

    # ========================= 辅助函数 =========================
    def _get_logo(self, norm_name):
        if norm_name in self._channel_logos:
            return self._channel_logos[norm_name]
        epg_name = self.epg_name_map.get(norm_name, norm_name)
        return self.epg_logo_url.format(name=epg_name)

    def _get_epg(self, norm_name):
        epg_name = self.epg_name_map.get(norm_name, norm_name)
        cache_key = f"epg_{epg_name}_{time.strftime('%Y%m%d')}"
        cached = self._epg_cache.get(cache_key)
        if cached:
            return cached
        try:
            url = self.epg_api_url.format(name=requests.utils.quote(epg_name), date=time.strftime('%Y%m%d'))
            r = self.session.get(url, timeout=self.epg_timeout)
            if r.status_code == 200:
                data = r.json()
                self._epg_cache.put(cache_key, data)
                return data
        except Exception as e:
            self.logger.debug(f"EPG获取失败 {epg_name}: {e}")
        return None

    def _format_epg(self, norm_name):
        data = self._get_epg(norm_name)
        if not data or not isinstance(data, list):
            return "暂无节目预告"
        lines = []
        now = time.strftime('%H:%M')
        for prog in data[:8]:
            if isinstance(prog, dict):
                t = prog.get('time', prog.get('start', ''))
                t = t.split(' ')[-1] if ' ' in str(t) else str(t)
                title = prog.get('title', prog.get('name', '未知节目'))
                mark = ' ▶' if t and t <= now else ''
                lines.append(f"{t} {title}{mark}")
        return '\n'.join(lines) if lines else "暂无节目预告"

    def _load_cache_from_disk(self):
        try:
            if not os.path.exists(self._cache_file):
                return
            with open(self._cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if time.time() - data.get('timestamp', 0) > self.cache_ttl:
                self.logger.log("缓存已过期，忽略")
                return
            with self._cache_lock:
                self._cache_data = data.get('categories', {})
                self._category_order = data.get('order', list(self._cache_data.keys()))
                self._category_type = data.get('type', {})
                self._interface_groups = data.get('interface_groups', {})
                self._cache_ready = True
            self.logger.log(f"从磁盘加载缓存，分类数: {len(self._cache_data)}, 接口数: {len(self._interface_groups)}")
        except Exception as e:
            self.logger.log(f"加载缓存失败: {e}")
            self._cache_ready = False

    def _save_cache_to_disk(self):
        try:
            with self._cache_lock:
                data = {
                    'timestamp': time.time(),
                    'ttl': self.cache_ttl,
                    'categories': self._cache_data,
                    'order': self._category_order,
                    'type': self._category_type,
                    'interface_groups': self._interface_groups
                }
            with open(self._cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.logger.log("全量缓存已写入磁盘")
        except Exception as e:
            self.logger.log(f"保存缓存失败: {e}")

    # ========================= 后台缓存构建 =========================
    def _build_cache_bg(self):
        if self._cache_building:
            return
        self._cache_building = True
        try:
            t0 = time.time()
            self.logger.log("后台开始构建全量缓存...")
            merged = self._fetch_and_merge_lives(self._last_extend)
            self._load_all_sources(merged, timeout=self.sources_load_timeout)
            self._build_channel_index()
            self._build_caches()
            self._save_cache_to_disk()
            self.logger.log(f"全量缓存构建完成，耗时 {time.time()-t0:.1f}s")
            if self.refresh_interval > 0:
                self._start_refresh()
        except Exception as e:
            self.logger.log(f"缓存构建异常: {e}")
        finally:
            self._cache_building = False
            self.logger.flush()

    def _trigger_pull_refresh(self):
        now = time.time()
        if now - self._last_refresh_ts < 60:
            return
        if self._refreshing or self._cache_building:
            return
        self._last_refresh_ts = now
        self._refreshing = True
        self.logger.log("定时刷新：开始重建缓存...")
        threading.Thread(target=self._do_pull_refresh, daemon=True).start()

    def _do_pull_refresh(self):
        try:
            self._build_cache_bg()
        except Exception as e:
            self.logger.log(f"刷新异常: {e}")
        finally:
            self._refreshing = False
            self.logger.flush()

    def _start_refresh(self):
        if self._refresh_thread and self._refresh_thread.is_alive():
            return
        self._stop_refresh = False
        def refresh_loop():
            while not self._stop_refresh:
                time.sleep(self.refresh_interval)
                if self._stop_refresh:
                    break
                self._trigger_pull_refresh()
        self._refresh_thread = threading.Thread(target=refresh_loop, daemon=True)
        self._refresh_thread.start()

    # ========================= 影视TV接口 =========================
    def homeContent(self, filter):
        classes = []
        with self._cache_lock:
            for cat in self._category_order:
                classes.append({"type_id": cat, "type_name": cat})
            if not classes:
                classes = [{"type_id": "全部", "type_name": "全部"}]
        return {"class": classes, "filters": {}}

    def homeVod(self):
        videos = []
        with self._cache_lock:
            if self._cache_ready and self._cache_data:
                for cat in self._category_order[:4]:
                    cat_type = self._category_type.get(cat, 'static')
                    if cat_type == 'interface':
                        groups = self._interface_groups.get(cat, {}).get('groups', [])[:6]
                        for group in groups:
                            videos.append({
                                "vod_id": f"{cat}###{group}",
                                "vod_name": group,
                                "vod_pic": DEFAULT_IMAGE,
                                "vod_remarks": ""
                            })
                    else:
                        if cat not in self._cache_data:
                            continue
                        channels = list(self._cache_data[cat].keys())[:6]
                        for norm in channels:
                            info = self._cache_data[cat][norm]
                            videos.append({
                                "vod_id": f"{cat}###{norm}",
                                "vod_name": info['display'],
                                "vod_pic": info['logo'] or DEFAULT_IMAGE,
                                "vod_remarks": f"{len(info['sources'])}个源"
                            })
                if videos:
                    return {"list": videos}

        first_iface = None
        for cat in self._category_order:
            if self._category_type.get(cat) == 'interface':
                first_iface = cat
                break
        if first_iface and first_iface in self._source_groups:
            groups = self._source_groups[first_iface]
            group_names = list(groups.keys())[:6]
            for g in group_names:
                videos.append({
                    "vod_id": f"{first_iface}###{g}",
                    "vod_name": g,
                    "vod_pic": DEFAULT_IMAGE,
                    "vod_remarks": f"{len(groups[g])}个频道"
                })
            if videos:
                return {"list": videos}
        return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        page = max(1, int(pg) if str(pg).isdigit() else 1)
        page_size = 30
        videos = []
        total = 0
        with self._cache_lock:
            cat_type = self._category_type.get(tid, 'static')
            if cat_type == 'interface':
                groups = self._interface_groups.get(tid, {}).get('groups', [])
                if not groups and tid in self._source_groups:
                    groups = list(self._source_groups[tid].keys())
                total = len(groups)
                start = (page - 1) * page_size
                end = start + page_size
                for group in groups[start:end]:
                    videos.append({
                        "vod_id": f"{tid}###{group}",
                        "vod_name": group,
                        "vod_pic": DEFAULT_IMAGE,
                        "vod_remarks": ""
                    })
            else:
                if tid not in self._cache_data:
                    return {"list": [], "page": page, "pagecount": 1}
                channels = list(self._cache_data[tid].keys())
                total = len(channels)
                start = (page - 1) * page_size
                end = start + page_size
                for norm in channels[start:end]:
                    info = self._cache_data[tid][norm]
                    videos.append({
                        "vod_id": f"{tid}###{norm}",
                        "vod_name": info['display'],
                        "vod_pic": info['logo'] or DEFAULT_IMAGE,
                        "vod_remarks": f"{len(info['sources'])}个源"
                    })
        return {
            "list": videos,
            "page": page,
            "pagecount": max(1, (total + page_size - 1) // page_size),
            "limit": page_size,
            "total": total
        }

    # ========================= 详情页（修复版） =========================
    def detailContent(self, ids):
        if not ids:
            return {"list": []}
        vid = ids[0] if isinstance(ids, list) else ids
        parts = vid.split('###', 1)
        if len(parts) != 2:
            return {"list": []}
        cat_or_interface, item = parts
        with self._cache_lock:
            cat_type = self._category_type.get(cat_or_interface, 'static')
            if cat_type == 'interface':
                group_channels = None
                groups_dict = self._interface_groups.get(cat_or_interface, {}).get('group_channels', {})
                if item in groups_dict:
                    group_channels = groups_dict[item]
                else:
                    item_clean = item.strip().lower()
                    for g, ch_list in groups_dict.items():
                        if g.strip().lower() == item_clean:
                            group_channels = ch_list
                            self.logger.log(f"通过忽略大小写匹配到分组 '{g}'")
                            break
    
                if not group_channels and cat_or_interface in self._source_groups:
                    groups = self._source_groups[cat_or_interface]
                    if item in groups:
                        group_channels = groups[item]
                    else:
                        for g, ch_list in groups.items():
                            if g.strip().lower() == item_clean:
                                group_channels = ch_list
                                self.logger.log(f"从 _source_groups 忽略大小写匹配到分组 '{g}'")
                                break
    
                if not group_channels:
                    self.logger.log(f"缓存和源数据均未找到分组 '{item}'，从 _channels 重新筛选")
                    with self._channels_lock:
                        all_channels = self._channels[:]
                    matched = []
                    for ch in all_channels:
                        if ch.get('source') == cat_or_interface:
                            ch_group = ch.get('group', '').strip()
                            if ch_group.lower() == item_clean:
                                matched.append(ch)
                    if matched:
                        group_channels = matched
                        self.logger.log(f"从 _channels 精确匹配到 {len(group_channels)} 个频道")
                    else:
                        for ch in all_channels:
                            if ch.get('source') == cat_or_interface:
                                ch_group = ch.get('group', '').strip()
                                if item_clean in ch_group.lower() or ch_group.lower() in item_clean:
                                    matched.append(ch)
                        if matched:
                            group_channels = matched
                            self.logger.log(f"从 _channels 模糊匹配到 {len(group_channels)} 个频道")
    
                if not group_channels:
                    self.logger.log(f"未找到分组 '{item}'，接口 '{cat_or_interface}'")
                    return {"list": []}
    
                self.logger.log(f"接口 '{cat_or_interface}' 分组 '{item}' 包含 {len(group_channels)} 个频道")
                seen = set()
                play_url_list = []
                play_from_list = []   # 新增：存放所有频道名称
                for ch in group_channels:
                    name = ch.get('name', '未知频道')
                    url = ch.get('url', '')
                    if not url or (name, url) in seen:
                        continue
                    seen.add((name, url))
                    play_from_list.append(name)   # 收集名称
                    key = hashlib.md5((url + json.dumps(ch.get('headers', {}), sort_keys=True) + ch.get('proxy_mode', PROXY_OFF)).encode()).hexdigest()[:16]
                    self._quick_cache.put(key, {
                        'url': url,
                        'headers': ch.get('headers', {}),
                        'proxy_mode': ch.get('proxy_mode', PROXY_OFF)
                    })
                    play_url = f"http://127.0.0.1:9978/proxy?do=py&fun=quick&id={key}"
                    play_url_list.append(f"{name}${play_url}")
    
                vod = {
                    "vod_id": vid,
                    "vod_name": item,
                    "vod_pic": DEFAULT_IMAGE,
                    "vod_content": "",
                    "vod_director": "",
                    "vod_actor": f"共{len(play_url_list)}个频道",
                    "vod_play_from": "$$$".join(play_from_list),   # 修复：设置为名称列表
                    "vod_play_url": "$$$".join(play_url_list)
                }
                return {"list": [vod]}
            else:
                # 静态分类保持不变（已有正确的 play_from）
                if cat_or_interface not in self._cache_data or item not in self._cache_data[cat_or_interface]:
                    return {"list": []}
                info = self._cache_data[cat_or_interface][item]
                display = info['display']
                sources = info['sources']
                if not sources:
                    return {"list": []}
                play_from_list = [s['name'] for s in sources]
                play_url_list = []
                for s in sources:
                    url = s['url']
                    if not url:
                        continue
                    key = hashlib.md5((url + json.dumps(s['headers'], sort_keys=True) + s['proxy_mode']).encode()).hexdigest()[:16]
                    self._quick_cache.put(key, {
                        'url': url,
                        'headers': s['headers'],
                        'proxy_mode': s['proxy_mode']
                    })
                    play_url = f"http://127.0.0.1:9978/proxy?do=py&fun=quick&id={key}"
                    play_url_list.append(f"{display}${play_url}")
                vod = {
                    "vod_id": vid,
                    "vod_name": display,
                    "vod_pic": info['logo'] or DEFAULT_IMAGE,
                    "vod_content": self._format_epg(item),
                    "vod_director": " | ".join(play_from_list),
                    "vod_actor": f"共{len(sources)}条线路",
                    "vod_play_from": "$$$".join(play_from_list),
                    "vod_play_url": "$$$".join(play_url_list)
                }
                return {"list": [vod]}

    def playerContent(self, flag, id, vipFlags):
        if id.startswith('http://127.0.0.1:9978/proxy') and 'fun=quick' in id:
            qid = parse_qs(urlparse(id).query).get('id', [''])[0]
            if qid:
                ch = self._quick_cache.get(qid)
                if ch:
                    if self.direct_play:
                        return {
                            "parse": 0,
                            "url": ch['url'],
                            "playUrl": "",
                            "header": json.dumps(ch['headers']),
                            "flag": flag
                        }
                    else:
                        return {
                            "parse": 0,
                            "url": id,
                            "playUrl": "",
                            "header": "{}",
                            "flag": flag
                        }
        return {"parse": 0, "url": id, "playUrl": "", "header": "{}", "flag": flag}

    def searchContent(self, key, quick):
        key_norm = self.normalizer.normalize(key) if self.normalizer else key
        results = []
        with self._cache_lock:
            for cat, channels in self._cache_data.items():
                for norm, info in channels.items():
                    display = info['display']
                    if key_norm in norm or key in display:
                        results.append({
                            "vod_id": f"搜索###{norm}",
                            "vod_name": display,
                            "vod_pic": info['logo'] or DEFAULT_IMAGE,
                            "vod_remarks": f"{len(info['sources'])}个源"
                        })
                    if len(results) >= 20:
                        break
                if len(results) >= 20:
                    break
        return {"list": results}

    def localProxy(self, params):
        src = params.get('__src')
        if src and src in self._module_spiders:
            try:
                clean = {k: v for k, v in params.items() if k != '__src'}
                result = self._module_spiders[src].localProxy(clean)
                if result and isinstance(result, list) and len(result) >= 2 and result[0] != 500:
                    return result
            except Exception:
                pass

        fun = params.get('fun')
        if fun == 'quick':
            return self._handle_quick(params)

        for sp in self._module_spiders.values():
            try:
                result = sp.localProxy(params)
                if result and isinstance(result, list) and len(result) >= 2 and result[0] != 500:
                    return result
            except Exception:
                continue
        return self._err("无法处理")

    def _handle_quick(self, params):
        qid = params.get('id')
        if not qid:
            return self._err("缺少id")
        ch = self._quick_cache.get(qid)
        if not ch:
            return self._err("缓存过期")
        proxy_mode = ch.get('proxy_mode', PROXY_OFF)
        sess = self._get_playback_session(proxy_mode)
        if 'ts' in params:
            return self._proxy_ts(self._b64d(params['ts']), ch['headers'], sess)
        return self._request_with_retry(sess, ch['url'], ch['headers'], qid)

    def _request_with_retry(self, sess, url, headers, ch_id):
        for attempt in range(2):
            try:
                resp = sess.get(url, headers=headers, timeout=(5, 12), verify=False)
                if resp and resp.status_code == 200:
                    ct = resp.headers.get('Content-Type', '')
                    if 'mpegurl' in ct or '#EXTM3U' in resp.text[:1000]:
                        return [200, "application/vnd.apple.mpegurl", self._rewrite_m3u8(resp.text, ch_id, url)]
                    return [200, ct or 'application/octet-stream', resp.content,
                            {'Content-Type': ct, 'Content-Length': str(len(resp.content)), 'Cache-Control': 'no-cache'}]
                if attempt == 0:
                    continue
                return self._err(f"请求失败")
            except Exception as e:
                if attempt == 0:
                    continue
                return self._err("请求异常")
        return self._err("请求失败")

    def _proxy_ts(self, url, headers, sess):
        for attempt in range(2):
            try:
                resp = sess.get(url, headers=headers, timeout=(5, 12), verify=False)
                if resp and resp.status_code == 200:
                    return [200, "video/MP2T", resp.content,
                            {'Content-Type': 'video/MP2T', 'Content-Length': str(len(resp.content)), 'Cache-Control': 'no-cache'}]
                if attempt == 0:
                    continue
                return self._err("TS失败")
            except Exception:
                if attempt == 0:
                    continue
                return self._err("TS异常")
        return self._err("TS失败")

    def _rewrite_m3u8(self, text, ch_id, base_url):
        lines = []
        for line in text.splitlines():
            if line.startswith('#'):
                lines.append(line)
            else:
                ts = urljoin(base_url, line.strip())
                lines.append(f"http://127.0.0.1:9978/proxy?do=py&fun=quick&ts={self._b64e(ts)}&id={ch_id}")
        return '\n'.join(lines) + '\n'

    def _b64e(self, s):
        return base64.urlsafe_b64encode(s.encode()).decode().rstrip('=')

    def _b64d(self, s):
        p = 4 - len(s) % 4
        if p != 4:
            s += '=' * p
        return base64.urlsafe_b64decode(s).decode()

    def _err(self, msg):
        return [500, "application/vnd.apple.mpegurl", f"#EXTM3U\n#EXT-X-ENDLIST\n# {msg}"]

    def destroy(self):
        self._stop_refresh = True
        self._shutdown_flag.set()
        for ex in self._executors:
            try:
                ex.shutdown(wait=False)
            except Exception:
                pass
        if hasattr(self, '_quick_cache') and self._quick_cache:
            self._quick_cache.clear()
        self.logger.flush()
        return ""