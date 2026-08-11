# -*- coding: utf-8 -*-
# @Author  : 陆小凤
# @Time    : 2026/8/11
"""
全能直播聚合插件 - 点播版 v15_final（纯配置驱动）增强版
- 兼容 JS 版输入格式（JSON 或 URL 字符串）
- 统一 playerContent 返回结构
- 默认 UA = okhttp/3.15
- 支持分类显示顺序与别名 (分类显示/分类别名)
- 【v15.1】增强子模块健康检查与自动重建
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
from urllib.parse import urljoin, urlparse, urlencode, parse_qs, urlunparse, quote
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
# [MOD] 统一默认 User-Agent
DEFAULT_USER_AGENT = 'okhttp/3.15'
DEFAULT_EXTERNAL_API_URL = "https://xn--v4q818bf34b.cc/helper/api.php"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else os.getcwd()
CACHE_DIR = os.path.join(SCRIPT_DIR, 'cache')
MODULE_CACHE_DIR = os.path.join(CACHE_DIR, 'modules')

def _ensure_cache_dirs():
    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(MODULE_CACHE_DIR, exist_ok=True)

_ensure_cache_dirs()

EPG_LOGO_URL = "https://cdn.jsdmirror.com/gh/fanmingming/live@master/tv/{name}.png"
EPG_API_URL = "http://epg.51zmt.top:8000/api/diyp/?ch={name}&date={date}"
DEFAULT_IMAGE = "https://000.hfr1107.top/lives.jpg"

BOOL_MAP = {'是': True, '否': False, '下载': True, '不下载': False,
            'true': True, 'false': False, '1': True, '0': False, True: True, False: False}

DEFAULT_LOG_DIR = '/storage/emulated/0/download/logs/'
LOG_LEVELS = {'debug': 0, 'info': 1, '警告': 1, 'warn': 1, '错误': 2, 'error': 2}

# ========================= 日志 =========================
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
        if not self.enabled and self._buf:
            self._flush()  # 清空缓存

    def set_level(self, v):
        if isinstance(v, str):
            self.level = LOG_LEVELS.get(v.lower(), 1)
        elif isinstance(v, int):
            self.level = max(0, min(2, v))

    def log(self, msg, data=None):
        if self.level > 1:  # 仅 error 及以上不输出
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

# ========================= 缓存 =========================
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

# ========================= 解密模块（完整，与 v6 一致） =========================
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

# ========================= 名称规范化模块（纯配置驱动） =========================
class ChannelNormalizer:
    def __init__(self, ext_config=None):
        self.config = ext_config or {}
        self.enabled = self.config.get('启用', True)

        # 1. 繁简映射表（直接使用配置中的 t2s_map）
        t2s_map = self.config.get('t2s_map', {})
        if not isinstance(t2s_map, dict):
            t2s_map = {}
        self.t2s_table = str.maketrans(t2s_map)

        # 2. 中文数字映射
        self.cn_num_map = self.config.get('cn_num_map', {})
        if not isinstance(self.cn_num_map, dict):
            self.cn_num_map = {}

        # 3. 内置规范名映射
        self.builtin_map = self.config.get('builtin_map', {})
        if not isinstance(self.builtin_map, dict):
            self.builtin_map = {}

        # 4. 构建质量/运营商正则（必须在 _build_map 之前，因为 normalize_key 会用到）
        quality_words = self.config.get('quality_words', [])
        operator_words = self.config.get('operator_words', [])
        self.quality_pattern = self._build_pattern(quality_words)
        self.operator_pattern = self._build_pattern(operator_words)

        # 5. 构建规范映射（别名合并）
        self._canonical_map = {}
        self._build_map()

    def _build_pattern(self, word_list):
        """根据单词列表构建正则表达式（大小写不敏感）"""
        if not word_list:
            return re.compile(r'(?!)')  # 永不匹配
        if isinstance(word_list, str):
            word_list = [word_list.strip()] if word_list.strip() else []
        escaped = [re.escape(w) for w in word_list if w.strip()]
        if not escaped:
            return re.compile(r'(?!)')
        return re.compile('|'.join(escaped), re.IGNORECASE)

    def _build_map(self):
        self._canonical_map = {}
        # 从 builtin_map 填充（规范名 → 规范名）
        for canonical in self.builtin_map.values():
            k = self.normalize_key(canonical)
            if k and k not in self._canonical_map:
                self._canonical_map[k] = canonical

        # 获取别名：优先从 config 中读取 builtin_aliases
        aliases = self.config.get('builtin_aliases', {})
        if not aliases:
            # 若 config 中没有，则尝试从文件读取（兼容旧方式）
            alias_path = self.config.get('aliases_path') or os.path.join(SCRIPT_DIR, 'channel_db.json')
            if os.path.exists(alias_path):
                try:
                    with open(alias_path, 'r', encoding='utf-8') as f:
                        db = json.load(f)
                    aliases = db.get('builtin_aliases', {})
                except Exception:
                    pass

        # 合并别名到映射
        for canonical, alias_list in aliases.items():
            k = self.normalize_key(canonical)
            if k and k not in self._canonical_map:
                self._canonical_map[k] = canonical
            for alias in (alias_list if isinstance(alias_list, list) else []):
                k2 = self.normalize_key(alias)
                if k2:
                    self._canonical_map[k2] = canonical

    # ---------- 转换方法 ----------
    def to_half_width(self, s):
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

    def to_simplified(self, s):
        return s.translate(self.t2s_table)

    def yangshi_to_cctv(self, s):
        pattern = re.compile(
            r'央视\s*([0-9]{1,2}|[一二三四五六七八九十]{1,3})\s*(?:套|台|频道|综合|高清)?'
        )
        def replacer(m):
            num = m.group(1)
            if num.isdigit():
                n = int(num)
            else:
                n = self.cn_num_map.get(num)
            return f'CCTV{n}' if n else m.group(0)
        return pattern.sub(replacer, s)

    def normalize_key(self, name):
        if not name:
            return ''
        s = self.yangshi_to_cctv(
            self.to_simplified(self.to_half_width(str(name).strip()))
        ).upper()
        # 处理 CCTV 系列
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
        # 移除质量/运营商标记
        s = self.quality_pattern.sub('', s)
        s = self.operator_pattern.sub('', s)
        # 移除所有符号和空白
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
        s = self.quality_pattern.sub('', raw)
        s = self.operator_pattern.sub('', s)
        s = re.sub(r'[（(\[【]\s*[)）\]【】]', '', s)
        s = re.sub(r'^[\s\-_·.|]+|[\s\-_·.|]+$', '', s).strip()
        return s if s else raw

# ========================= 主类 Spider =========================
class Spider(BaseSpider):
    MODULE_CACHE_TTL = 600
    URL_CACHE_TTL = 3600
    EPG_CACHE_TTL = 300
    RETRY_COUNT = 2

    def __init__(self):
        super().__init__()
        self.logger = Logger()
        self.session = None
        self._proxy_sessions = LRUCache(maxsize=32, ttl=3600)
        self._header_cache = LRUCache(maxsize=4096, ttl=1800)
        self._disk_cache = DiskCache(os.path.join(CACHE_DIR, 'data'), ttl=3600)
        self._epg_cache = DiskCache(os.path.join(CACHE_DIR, 'epg'), ttl=self.EPG_CACHE_TTL)
        self._source_cache = DiskCache(os.path.join(CACHE_DIR, 'source'), ttl=self.URL_CACHE_TTL)
        self._channels = []
        self._channels_lock = threading.Lock()
        self._module_m3u = {}
        self._module_spiders = {}
        self._module_lock = threading.Lock()
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
        self._category_map = {}
        self._category_order = []
        self._category_type = {}
        self._interface_groups = {}
        self._agg_lock = threading.Lock()
        self._last_refresh_ts = 0
        self._refreshing = False
        self.epg_logo_url = EPG_LOGO_URL
        self.epg_api_url = EPG_API_URL
        self.epg_timeout = (3, 8)
        self.epg_name_map = {}

        self.cache_ttl = 86400
        self._cache_data = {}
        self._cache_ready = False
        self._cache_lock = threading.Lock()
        self._cache_file = os.path.join(CACHE_DIR, 'full_cache.json')
        self._cache_building = False
        self.enable_refresh = True

        self.default_vod_pic = DEFAULT_IMAGE
        self.epg_logo_url_cfg = EPG_LOGO_URL
        self.epg_api_url_cfg = EPG_API_URL

        self._source_loaded = {}
        self._global_ready = False
        self._first_source_name = None
        self._focus_count = {}

        # 新增分类别名与显示配置存储
        self.category_aliases = {}
        self._display_config = None
        self._interface_ids = []
        self._static_ids = []

        # 【新增】子模块健康统计
        self._spider_health = {}
        self._health_lock = threading.Lock()

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

    def _setup_session(self, sess, proxy_url=None):
        retry = Retry(total=2, backoff_factor=0.3, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=20)
        sess.mount('http://', adapter)
        sess.mount('https://', adapter)
        sess.headers.update({'User-Agent': DEFAULT_USER_AGENT, 'Accept-Language': 'zh-CN,zh;q=0.9'})
        if proxy_url:
            sess.proxies = {'http': proxy_url, 'https': proxy_url}
        sess.verify = False
        return sess

    def _init_session(self):
        self.session = requests.Session()
        self._setup_session(self.session)

    def _get_playback_session(self, proxy_url=None):
        if not proxy_url:
            return self.session
        cached = self._proxy_sessions.get(proxy_url)
        if cached is not None:
            return cached
        new_sess = requests.Session()
        self._setup_session(new_sess, proxy_url)
        self._proxy_sessions.put(proxy_url, new_sess)
        return new_sess

    def _ensure_headers_with_default(self, headers):
        if not headers:
            headers = {}
        if 'User-Agent' not in headers:
            headers['User-Agent'] = DEFAULT_USER_AGENT
        return headers

    def _parse_url_string(self, input_data):
        base_url = ''
        pic_url = ''
        lives = []

        if '$$$' in input_data:
            parts = input_data.split('$$$', 1)
            base_url = parts[0].strip()
            rest = parts[1].strip()
        else:
            rest = input_data

        if '&&&' in rest:
            parts = rest.split('&&&', 1)
            rest = parts[0].strip()
            pic_url = parts[1].strip()
            if pic_url and not pic_url.startswith(('http://', 'https://')):
                pic_url = base_url + pic_url

        segments = rest.split('#')
        for seg in segments:
            seg = seg.strip()
            if not seg:
                continue
            if '$' in seg:
                name, url = seg.split('$', 1)
                if not url.startswith(('http://', 'https://')):
                    url = base_url + url
                lives.append({
                    'name': name.replace('!!', ''),
                    'url': url,
                    'img': pic_url
                })
            else:
                url = seg
                if not url.startswith(('http://', 'https://')):
                    url = base_url + url
                try:
                    req_headers = self._ensure_headers_with_default({})
                    resp = self.session.get(url, timeout=(self.connect_timeout, self.read_timeout_url),
                                            headers=req_headers)
                    if resp.status_code == 200:
                        data = json.loads(resp.text)
                        path_prefix = url[:url.rfind('/')+1]
                        for item in data:
                            if not isinstance(item, dict):
                                continue
                            name = item.get('name', '').replace('!!', '')
                            item_url = item.get('url', '')
                            if not name or not item_url:
                                continue
                            if not item_url.startswith(('http://', 'https://')):
                                item_url = path_prefix + item_url
                            lives.append({
                                'name': name,
                                'url': item_url,
                                'img': pic_url,
                                'headers': self._extract_source_headers(item)
                            })
                except Exception as e:
                    self.logger.log(f"URL字符串子分类请求失败: {url} - {e}")
        return lives, base_url, pic_url

    # ========================= 初始化 =========================
    def init(self, extend):
        self._init_session()

        ext = {}
        if extend:
            extend_str = str(extend).strip()
            if extend_str.startswith('{') or extend_str.startswith('['):
                try:
                    ext = json.loads(extend_str)
                except Exception:
                    ext = {}
            elif extend_str.startswith(('http://', 'https://', 'ftp://')) or os.path.exists(extend_str):
                loaded = self._load_ext_from_path(extend_str)
                if loaded and isinstance(loaded, dict):
                    ext = loaded
                    self.logger.log(f"已从路径加载配置: {extend_str}")
                else:
                    self.logger.log(f"无法从路径加载配置: {extend_str}")
            else:
                self.logger.log("检测到传统 URL 字符串格式，尝试解析...")
                lives, base_url, pic_url = self._parse_url_string(extend_str)
                if lives:
                    ext = {'lives': lives, 'vod_pic': pic_url}
                    if pic_url:
                        self.default_vod_pic = pic_url
                else:
                    self.logger.log("URL字符串解析失败，使用空配置")

        self._last_extend = ext
        self.logger.set_enabled(self._p_bool(ext, '启用日志'))
        self.logger.log("=" * 50 + " 启动 VOD（兼容JS版） " + "=" * 50)

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
            else:
                self.logger.log(f"外部配置加载失败: {config_file}")

        self._parse_config(ext)
        self.logger.set_log_dir(self.log_dir)

        normalizer_config = {
            '启用': self._p_bool(ext, '启用', default=True),
            'quality_words': self._p(ext, 'quality_words', default=[]),
            'operator_words': self._p(ext, 'operator_words', default=[]),
            't2s_map': self._p(ext, 't2s_map', default={}),
            'cn_num_map': self._p(ext, 'cn_num_map', default={}),
            'builtin_map': self._p(ext, 'builtin_map', default={}),
            'builtin_aliases': self._p(ext, 'builtin_aliases', default={}),
            'aliases_path': self._p(ext, 'aliases_path', default=''),
            'clean_rules': self._p(ext, 'clean_rules', default={}),
        }
        self.normalizer = ChannelNormalizer(normalizer_config)

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

        raw_lives = self._p(ext, 'lives', default=[])
        lives = []
        name_counter = {}
        for item in raw_lives:
            if not isinstance(item, dict):
                continue
            new_item = item.copy()
            raw_name = new_item.get('name', '未命名')
            if raw_name in name_counter:
                name_counter[raw_name] += 1
                new_name = f"{raw_name}_{name_counter[raw_name]}"
            else:
                name_counter[raw_name] = 1
                new_name = raw_name
            new_item['name'] = new_name
            lives.append(new_item)

        self._source_configs = []
        for idx, item in enumerate(lives):
            if not isinstance(item, dict):
                continue
            name = item.get('name', '未命名')
            url = item.get('url')
            api = item.get('api')
            if not url and not api:
                continue
            proxy = item.get('proxy')
            headers = item.get('header', item.get('headers', {}))
            ua = item.get('ua', '')
            if ua:
                headers['User-Agent'] = ua
            ext_cfg = item.get('ext', {})
            cfg = {
                'name': name,
                'url': url,
                'api': api,
                'proxy': proxy,
                'headers': headers,
                'ext': ext_cfg,
            }
            self._source_configs.append(cfg)
            if idx == 0:
                self._first_source_name = name

        # 保存接口和静态分类ID列表
        self._interface_ids = [cfg['name'] for cfg in self._source_configs]
        self._static_ids = list(self._category_map.keys())

        # 构建分类顺序和类型（先默认所有接口+静态）
        self._category_order = []
        self._category_type = {}
        for name in self._interface_ids:
            self._category_order.append(name)
            self._category_type[name] = 'interface'
        for cat in self._static_ids:
            self._category_order.append(cat)
            self._category_type[cat] = 'static'

        # 解析分类别名
        alias_cfg = ext.get('分类别名', {})
        if alias_cfg and isinstance(alias_cfg, dict):
            self.category_aliases = alias_cfg
        else:
            self.category_aliases = {}

        # 解析分类显示配置
        self._display_config = ext.get('分类显示', None)

        # 应用分类显示配置（先初始化，后加载缓存再应用）
        self._apply_display_config()

        for cfg in self._source_configs:
            self._source_loaded[cfg['name']] = (cfg['name'] == self._first_source_name)

        first_cfg = None
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
            self._load_one_source(first_cfg, is_first=True)

        if len(self._source_configs) > 1:
            threading.Thread(target=self._load_remaining_sources, daemon=True).start()

        self._load_cache_from_disk()
        # 加载缓存后，再次应用配置（覆盖缓存中的顺序）
        self._apply_display_config()

        if self._cache_ready:
            self.logger.log("全量缓存加载成功，数据已就绪")
            if self.refresh_interval > 0 and self.enable_refresh:
                self._start_refresh()
        else:
            threading.Thread(target=self._build_cache_bg, daemon=True).start()
        self.logger.flush()

    def _apply_display_config(self):
        """根据分类显示配置重新设置 _category_order 和 _category_type"""
        if not self._display_config:
            return
        top = self._display_config.get('置顶', [])
        middle = self._display_config.get('静态', [])
        bottom = self._display_config.get('后置', [])

        # 过滤有效ID
        valid_top = [x for x in top if x in self._interface_ids]
        valid_middle = [x for x in middle if x in self._static_ids]
        valid_bottom = [x for x in bottom if x in self._interface_ids]

        # 构建新顺序
        new_order = valid_top + valid_middle + valid_bottom

        # 设置类型
        for cat in new_order:
            if cat in self._interface_ids:
                self._category_type[cat] = 'interface'
            elif cat in self._static_ids:
                self._category_type[cat] = 'static'
            else:
                # 若都不在，则可能是旧缓存遗留，忽略
                pass

        self._category_order = new_order
        self.logger.debug(f"应用分类显示配置，顺序: {new_order}")

    def _load_remaining_sources(self):
        for cfg in self._source_configs[1:]:
            if self._shutdown_flag.is_set():
                break
            name = cfg['name']
            with self._channels_lock:
                if name in self._source_groups:
                    continue
            self._load_one_source(cfg, is_first=False)
            time.sleep(0.2)
        self.logger.debug("后台源加载完成")

    def _load_one_source(self, cfg, is_first=False):
        name = cfg['name']
        with self._channels_lock:
            if name in self._source_groups:
                return

        self.logger.debug(f"加载源: {name}")
        channels = []
        if cfg.get('api'):
            channels = self._load_py_source(cfg['api'], cfg)
        elif cfg.get('url'):
            channels = self._load_url_source(cfg)
        else:
            self.logger.log(f"【{name}】跳过：无 url 或 api")
            self._source_loaded[name] = True
            self._check_global_ready()
            return

        if channels:
            with self._channels_lock:
                if name in self._source_groups:
                    return
                self._channels.extend(channels)
                groups = {}
                for ch in channels:
                    group = ch.get('group', '默认分类')
                    groups.setdefault(group, []).append(ch)
                self._source_groups[name] = groups
                self._interface_groups[name] = {'groups': list(groups.keys()), 'group_channels': groups}
            self.logger.log(f"【{name}】加载 {len(channels)} 个频道, {len(groups)} 个分组")
        else:
            with self._channels_lock:
                self._source_groups[name] = {}
                self._interface_groups[name] = {'groups': [], 'group_channels': {}}
            self.logger.log(f"【{name}】加载完成，但无频道数据")

        self._source_loaded[name] = True
        if not is_first:
            self._check_global_ready()
        self._build_channel_index()
        return channels

    def _check_global_ready(self):
        all_loaded = all(self._source_loaded.get(cfg['name'], False) for cfg in self._source_configs)
        if all_loaded and not self._global_ready:
            self._global_ready = True
            self.logger.log("所有接口源加载完成，开始构建全量缓存")
            self._build_caches()
            self._save_cache_to_disk()

    def _load_py_source(self, api, cfg):
        name = cfg['name']
        try:
            ext_str = json.dumps(cfg.get('ext', {}), ensure_ascii=False)
            module = self._import_py_module(api)
            if not module or not hasattr(module, 'Spider'):
                self.logger.log(f"【{name}】模块加载失败")
                return []
            spider = module.Spider()
            spider.init(ext_str)
            with self._module_lock:
                # 【优化】先销毁旧实例，释放资源
                old_spider = self._module_spiders.get(name)
                if old_spider and hasattr(old_spider, 'destroy'):
                    try:
                        old_spider.destroy()
                    except Exception as e:
                        self.logger.log(f"销毁旧实例 {name} 异常: {e}")
                self._module_spiders[name] = spider
                # 【新增】重置健康统计
                with self._health_lock:
                    self._spider_health[name] = {'fails': 0, 'last_fail': 0, 'calls': 0}
            content = spider.liveContent('')
            if not content:
                self.logger.log(f"【{name}】liveContent 为空")
                return []
            proxy_url = cfg.get('proxy')
            headers = cfg.get('headers', {})
            channels = self._parse_content(content, name, proxy_url=proxy_url, source_headers=headers)
            return channels
        except Exception as e:
            self.logger.log(f"【{name}】加载异常: {e}")
            return []

    def _load_url_source(self, cfg):
        name = cfg.get('name', '未知源')
        url = cfg.get('url', '')
        proxy_url = cfg.get('proxy')
        source_headers = cfg.get('headers', {}) or self._extract_source_headers(cfg)

        if not url:
            return []

        if not url.startswith(('http://', 'https://', 'ftp://')):
            if os.path.exists(url):
                try:
                    with open(url, 'r', encoding='utf-8') as f:
                        content = f.read()
                    self.logger.debug(f"从本地文件加载 {name}: {url}")
                    return self._parse_content(content, name, proxy_url=proxy_url, source_url=url, source_headers=source_headers)
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
                return self._parse_content(cached, name, proxy_url=proxy_url, source_headers=source_headers)

            session = self._get_playback_session(proxy_url)
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
            return self._parse_content(content, name, proxy_url=proxy_url, source_url=url, source_headers=source_headers)
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
        log_level = self._p(ext, '日志级别', 'log_level', default='info')
        self.logger.set_level(log_level)
        self.max_workers = min(16, max(1, int(self._p(ext, '最大并发', 'max_workers', default=4))))
        self.connect_timeout = max(3, int(self._p(ext, '连接超时', 'connect_timeout', default=5)))
        self.read_timeout_url = max(5, int(self._p(ext, 'URL读取超时', 'url_read_timeout', default=8)))
        self.read_timeout_api = max(5, int(self._p(ext, 'API读取超时', 'api_read_timeout', default=10)))
        self.sources_load_timeout = max(30, int(self._p(ext, '源加载超时', 'sources_load_timeout', default=90)))

        self.default_vod_pic = self._p(ext, 'vod_pic', default=DEFAULT_IMAGE)
        self.epg_logo_url_cfg = self._p(ext, 'epg_logo_url', default=EPG_LOGO_URL)
        self.epg_api_url_cfg = self._p(ext, 'epg_api_url', default=EPG_API_URL)
        self.epg_timeout = self._parse_timeout(
            self._p(ext, 'epg_timeout', default=[3, 8])
        )
        ext_epg_map = self._p(ext, 'epg_name_map', default={})
        if ext_epg_map and isinstance(ext_epg_map, dict):
            self.epg_name_map = dict(ext_epg_map)
        else:
            self.epg_name_map = {}

        self.cache_ttl = max(60, int(self._p(ext, '缓存有效期', 'cache_ttl', default=86400)))
        self.enable_refresh = self._p_bool(ext, '启用定时刷新', default=True)

    def _parse_timeout(self, val, default=(3, 8)):
        if isinstance(val, (list, tuple)) and len(val) >= 2:
            return (int(val[0]), int(val[1]))
        if isinstance(val, (int, float)):
            return (int(val), int(val))
        if isinstance(val, str):
            parts = [x.strip() for x in val.split(',') if x.strip().isdigit()]
            if len(parts) >= 2:
                return (int(parts[0]), int(parts[1]))
        return default

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
            with ThreadPoolExecutor(max_workers=min(self.max_workers, len(urls))) as ex:
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
        ext_str = json.dumps(item.get('ext', {}), ensure_ascii=False)
        proxy_url = item.get('proxy')
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
                content = self._load_py_module(local_path, name, ext_str)
            else:
                if not os.path.exists(api_path):
                    self.logger.log(f"模块文件不存在: {api_path}")
                    return []
                content = self._load_py_module(api_path, name, ext_str)
            if content:
                self._module_m3u[name] = content
                return self._parse_content(content, name, proxy_url=proxy_url)
        except Exception as e:
            self.logger.log(f"加载模块失败 {name}: {e}")
        return []

    def _load_py_module(self, api_path, name, ext_str='{}'):
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
                spider.init(ext_str)

            # 【优化】在替换前销毁旧实例
            old_spider = self._module_spiders.get(name)
            if old_spider and hasattr(old_spider, 'destroy'):
                try:
                    old_spider.destroy()
                except Exception as e:
                    self.logger.log(f"销毁旧实例 {name} 异常: {e}")

            with self._module_lock:
                self._module_spiders[name] = spider
                # 【新增】重置健康统计
                with self._health_lock:
                    self._spider_health[name] = {'fails': 0, 'last_fail': 0, 'calls': 0}

            if hasattr(spider, 'liveContent'):
                return spider.liveContent('')
            return None
        except Exception as e:
            self.logger.log(f"模块执行失败 {name}: {e}")
            return None

    # ========================= 内容解析 =========================
    def _parse_content(self, content, source_name, proxy_url=None, source_url='', source_headers=None):
        if not content:
            return []
        source_headers = source_headers or {}
        if isinstance(content, str):
            content = content.strip()
            if content.startswith('#EXTM3U') or content.startswith('#EXTINF'):
                return self._parse_m3u(content, source_name, proxy_url, source_url, source_headers)
            elif content.startswith('{') or content.startswith('['):
                try:
                    data = json.loads(content)
                    return self._parse_json(data, source_name, proxy_url, source_url, source_headers)
                except Exception:
                    pass
            elif '#genre#' in content:
                return self._parse_txt(content, source_name, proxy_url, source_url, source_headers)
        elif isinstance(content, (dict, list)):
            return self._parse_json(content, source_name, proxy_url, source_url, source_headers)
        return []

    def _parse_m3u(self, content, source_name, proxy_url, source_url='', source_headers=None):
        channels = []
        source_headers = source_headers or {}
        lines = content.split('\n')
        current = None
        group_title = source_name
        for line in lines:
            line = line.strip()
            if line.startswith('#EXTINF'):
                current = {'name': '', 'group': group_title, 'source': source_name,
                           'proxy_url': proxy_url, 'headers': dict(source_headers)}
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

    def _parse_txt(self, content, source_name, proxy_url, source_url='', source_headers=None):
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
                        'source': source_name, 'proxy_url': proxy_url,
                        'headers': dict(source_headers)
                    })
        return channels

    def _parse_json(self, data, source_name, proxy_url, source_url='', source_headers=None):
        channels = []
        source_headers = source_headers or {}
        if isinstance(data, list):
            for item in data:
                ch = self._extract_channel(item, source_name, proxy_url, source_headers)
                if ch:
                    channels.append(ch)
        elif isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, list):
                    for item in v:
                        ch = self._extract_channel(item, source_name, proxy_url, source_headers, group=k)
                        if ch:
                            channels.append(ch)
                elif isinstance(v, dict):
                    ch = self._extract_channel(v, source_name, proxy_url, source_headers, group=k)
                    if ch:
                        channels.append(ch)
        return channels

    def _extract_channel(self, item, source_name, proxy_url, source_headers, group=None):
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
            'proxy_url': proxy_url,
            'headers': headers
        }

    def export_database(self, path=None):
        if not self.download_playlist:
            return
        path = path or os.path.join(self.log_dir, 'channel_database.json')
        try:
            with self._cache_lock:
                db = {
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'total_channels': len(self._channels),
                    'category_order': self._category_order,
                    'category_type': self._category_type,
                    'interface_groups': {},
                    'static_categories': {}
                }
                for src_name, src_data in self._interface_groups.items():
                    db['interface_groups'][src_name] = {
                        'groups': src_data.get('groups', []),
                        'channels': {}
                    }
                    for g, ch_list in src_data.get('group_channels', {}).items():
                        db['interface_groups'][src_name]['channels'][g] = [
                            {
                                'name': ch.get('name'),
                                'url': ch.get('url'),
                                'logo': ch.get('logo'),
                                'group': ch.get('group'),
                                'headers': ch.get('headers', {}),
                                'proxy_url': ch.get('proxy_url')
                            } for ch in ch_list
                        ]
                for cat, ch_dict in self._cache_data.items():
                    db['static_categories'][cat] = {
                        'channels': {
                            norm: {
                                'display': info['display'],
                                'logo': info['logo'],
                                'sources': info['sources']
                            } for norm, info in ch_dict.items()
                        }
                    }

            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(db, f, ensure_ascii=False, indent=2)
            self.logger.log(f"完整数据库已导出: {path}（共 {len(self._channels)} 个频道）")
        except Exception as e:
            self.logger.log(f"导出数据库失败: {e}")

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

    # ========================= 修改后的 _build_caches =========================
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

                    # ---------- 按 url 去重，保留首次出现的条目 ----------
                    unique_sources = {}
                    for s in sources:
                        url = s.get('url', '')
                        if not url:
                            continue
                        if url not in unique_sources:
                            unique_sources[url] = s
                    deduped_sources = list(unique_sources.values())
                    # ----------------------------------------------------

                    line_infos = []
                    used_names = set()
                    for s in deduped_sources:
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
                            'proxy_url': s.get('proxy_url')
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

            # ========== interface_groups 构建（不变） ==========
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
            self.export_database()

    # ========================= 辅助函数 =========================
    def _get_logo(self, norm_name):
        if norm_name in self._channel_logos:
            return self._channel_logos[norm_name]
        epg_name = self.epg_name_map.get(norm_name, norm_name)
        return self.epg_logo_url_cfg.format(name=quote(str(epg_name), safe=''))

    def _get_epg(self, norm_name):
        epg_name = self.epg_name_map.get(norm_name, norm_name)
        cache_key = f"epg_{epg_name}_{time.strftime('%Y%m%d')}"
        cached = self._epg_cache.get(cache_key)
        if cached:
            return cached
        try:
            url = self.epg_api_url_cfg.format(
                name=quote(str(epg_name), safe=''),
                date=time.strftime('%Y%m%d')
            )
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

    def _auto_clean_cache(self):
        now = time.time()
        ttl = getattr(self, 'cache_ttl', 86400)
        cleaned = 0
        for root, _, files in os.walk(CACHE_DIR):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    if os.path.isfile(fp) and now - os.path.getmtime(fp) > ttl:
                        os.remove(fp)
                        cleaned += 1
                except Exception:
                    pass
        if cleaned:
            self.logger.log(f"自动清理缓存: 删除 {cleaned} 个过期文件")

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
            self._auto_clean_cache()
            self.logger.log(f"全量缓存构建完成，耗时 {time.time()-t0:.1f}s")
            if self.refresh_interval > 0 and self.enable_refresh:
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
        if not self.enable_refresh or self.refresh_interval <= 0:
            return
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
                # 使用别名
                display_name = self.category_aliases.get(cat, cat)
                classes.append({"type_id": cat, "type_name": display_name})
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
                                "vod_pic": self.default_vod_pic,
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
                                "vod_pic": info['logo'] or self.default_vod_pic,
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
                    "vod_pic": self.default_vod_pic,
                    "vod_remarks": f"{len(groups[g])}个频道"
                })
            if videos:
                return {"list": videos}
        return {"list": []}

    def _interface_category_content(self, tid, pg):
        groups = self._interface_groups.get(tid, {}).get('groups', [])
        if not groups and tid in self._source_groups:
            groups = list(self._source_groups[tid].keys())

        if not groups:
            if self._source_loaded.get(tid, False):
                return {
                    "list": [{
                        "vod_id": "__empty__",
                        "vod_name": "⚠️ 该源无有效数据",
                        "vod_pic": self.default_vod_pic,
                        "vod_remarks": "接口可能已失效或配置错误"
                    }],
                    "page": 1,
                    "pagecount": 1,
                    "limit": 30,
                    "total": 1
                }
            else:
                return {"list": [], "page": 1, "pagecount": 1, "limit": 30, "total": 0}

        videos = []
        for group in groups:
            videos.append({
                "vod_id": f"{tid}###{group}",
                "vod_name": group,
                "vod_pic": self.default_vod_pic,
                "vod_remarks": ""
            })
        total = len(videos)
        page_size = 30
        page = max(1, int(pg) if str(pg).isdigit() else 1)
        start = (page - 1) * page_size
        end = start + page_size
        page_videos = videos[start:end]
        return {
            "list": page_videos,
            "page": page,
            "pagecount": max(1, (total + page_size - 1) // page_size),
            "limit": page_size,
            "total": total
        }

    def _dynamic_static_category_content(self, tid, pg):
        channel_names = self._category_map.get(tid, [])
        if not channel_names:
            return {"list": [], "page": 1, "pagecount": 1, "limit": 30, "total": 0}
        with self._channels_lock:
            matched_channels = []
            for ch in self._channels:
                norm = self.normalizer.normalize(ch.get('name', ''))
                if norm in channel_names:
                    matched_channels.append(ch)
        if not matched_channels:
            return {"list": [], "page": 1, "pagecount": 1, "limit": 30, "total": 0}
        merged = {}
        for ch in matched_channels:
            norm = self.normalizer.normalize(ch.get('name', ''))
            if not norm:
                continue
            if norm not in merged:
                merged[norm] = {
                    'display': self._display_names.get(norm, norm),
                    'logo': self._get_logo(norm),
                    'sources': []
                }
            # 此处也要按 url 去重（动态构建时也需要）
            url = ch.get('url', '')
            if not url:
                continue
            # 检查是否已存在相同 url
            if any(s['url'] == url for s in merged[norm]['sources']):
                continue
            line_info = {
                'name': ch.get('source', '未知源'),
                'url': url,
                'headers': ch.get('headers', {}),
                'proxy_url': ch.get('proxy_url')
            }
            merged[norm]['sources'].append(line_info)
        videos = []
        for norm, info in merged.items():
            videos.append({
                "vod_id": f"{tid}###{norm}",
                "vod_name": info['display'],
                "vod_pic": info['logo'] or self.default_vod_pic,
                "vod_remarks": f"{len(info['sources'])}个源"
            })
        total = len(videos)
        page_size = 30
        page = max(1, int(pg) if str(pg).isdigit() else 1)
        start = (page - 1) * page_size
        end = start + page_size
        page_videos = videos[start:end]
        return {
            "list": page_videos,
            "page": page,
            "pagecount": max(1, (total + page_size - 1) // page_size),
            "limit": page_size,
            "total": total
        }

    def _static_category_content(self, tid, pg):
        with self._cache_lock:
            if tid not in self._cache_data:
                return {"list": [], "page": 1, "pagecount": 1, "limit": 30, "total": 0}
            channels = list(self._cache_data[tid].keys())
            total = len(channels)
            page_size = 30
            page = max(1, int(pg) if str(pg).isdigit() else 1)
            start = (page - 1) * page_size
            end = start + page_size
            videos = []
            for norm in channels[start:end]:
                info = self._cache_data[tid][norm]
                videos.append({
                    "vod_id": f"{tid}###{norm}",
                    "vod_name": info['display'],
                    "vod_pic": info['logo'] or self.default_vod_pic,
                    "vod_remarks": f"{len(info['sources'])}个源"
                })
            return {
                "list": videos,
                "page": page,
                "pagecount": max(1, (total + page_size - 1) // page_size),
                "limit": page_size,
                "total": total
            }

    def categoryContent(self, tid, pg, filter, extend):
        cat_type = self._category_type.get(tid, 'static')
        if cat_type == 'interface':
            if tid == self._first_source_name:
                return self._interface_category_content(tid, pg)
            if self._source_loaded.get(tid, False):
                return self._interface_category_content(tid, pg)
            timeout = self.sources_load_timeout
            start_time = time.time()
            while time.time() - start_time < timeout:
                time.sleep(0.5)
                if self._source_loaded.get(tid, False):
                    break
            if self._source_loaded.get(tid, False):
                return self._interface_category_content(tid, pg)
            else:
                return {
                    "list": [{
                        "vod_id": "__timeout__",
                        "vod_name": "⏱️ 加载超时",
                        "vod_pic": self.default_vod_pic,
                        "vod_remarks": "请检查网络或稍后重试"
                    }],
                    "page": 1,
                    "pagecount": 1,
                    "limit": 30,
                    "total": 1
                }
        elif cat_type == 'static':
            if self._global_ready:
                return self._static_category_content(tid, pg)
            else:
                return self._dynamic_static_category_content(tid, pg)
        return {"list": [], "page": 1, "pagecount": 1, "limit": 30, "total": 0}

    # ========================= 详情页 =========================
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
                item_clean = item.strip().lower()
                for g, ch_list in groups_dict.items():
                    if g.strip().lower() == item_clean:
                        group_channels = ch_list
                        break
                if not group_channels and cat_or_interface in self._source_groups:
                    groups = self._source_groups[cat_or_interface]
                    for g, ch_list in groups.items():
                        if g.strip().lower() == item_clean:
                            group_channels = ch_list
                            break
                if not group_channels:
                    with self._channels_lock:
                        matched = [ch for ch in self._channels
                                   if ch.get('source') == cat_or_interface and
                                   ch.get('group', '').strip().lower() == item_clean]
                    if matched:
                        group_channels = matched
                if not group_channels:
                    return {"list": []}

                name_counter = {}
                play_from_list = []
                play_url_list = []
                seen = set()
                for ch in group_channels:
                    name = ch.get('name', '未知频道')
                    url = ch.get('url', '')
                    if not url or (name, url) in seen:
                        continue
                    seen.add((name, url))
                    name_counter[name] = name_counter.get(name, 0) + 1
                    if name_counter[name] == 1:
                        display_name = name
                    else:
                        display_name = f"{name}-{name_counter[name]}"
                    play_from_list.append(display_name)
                    play_url = url
                    headers = ch.get('headers', {})
                    proxy_url = ch.get('proxy_url')
                    if headers or proxy_url:
                        cache_key = f"{display_name}||{url}"
                        self._header_cache.put(cache_key, {
                            'headers': headers,
                            'proxy_url': proxy_url
                        })
                    play_url_list.append(f"{display_name}${play_url}")

                original_director = " | ".join(play_from_list)
                original_actor = f"共{len(play_from_list)}个频道"
                vod = {
                    "vod_id": vid,
                    "vod_name": item,
                    "vod_pic": self.default_vod_pic,
                    "vod_director": cat_or_interface,
                    "vod_actor": original_director,
                    "vod_play_from": "$$$".join(play_from_list),
                    "vod_play_url": "$$$".join(play_url_list),
                }
                epg_content = self._format_epg(item) if item else "暂无节目预告"
                vod["vod_content"] = f"{original_actor}\n{epg_content}"
                return {"list": [vod]}

            else:  # static
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
                    play_url = url
                    headers = s.get('headers', {})
                    proxy_url = s.get('proxy_url')
                    if headers or proxy_url:
                        cache_key = f"{s['name']}||{url}"
                        self._header_cache.put(cache_key, {
                            'headers': headers,
                            'proxy_url': proxy_url
                        })
                    play_url_list.append(f"{display}${play_url}")
                original_director = " | ".join(play_from_list)
                original_actor = f"共{len(sources)}条线路"
                vod = {
                    "vod_id": vid,
                    "vod_name": display,
                    "vod_pic": info['logo'] or self.default_vod_pic,
                    "vod_director": cat_or_interface,
                    "vod_actor": original_director,
                    "vod_play_from": "$$$".join(play_from_list),
                    "vod_play_url": "$$$".join(play_url_list)
                }
                epg_content = self._format_epg(item)
                vod["vod_content"] = f"{original_actor}\n{epg_content}"
                return {"list": [vod]}

    # ========================= 播放接口 =========================
    def playerContent(self, flag, id, vipFlags):
        cache_key = f"{flag}||{id}"
        cached = self._header_cache.get(cache_key)
        if cached:
            headers = cached.get('headers', {})
            proxy = cached.get('proxy_url')
        else:
            headers = {}
            proxy = None
        # 强制确保 headers 包含 User-Agent
        headers = self._ensure_headers_with_default(headers)
        result = {
            "parse": 0,
            "url": id,
            "playUrl": "",
            "flag": flag,
            "header": headers,          # 直接返回字典对象,
            "js": "",
            "extra": {}
        }
        if proxy:
            result['proxy'] = proxy
        return result

    # ========================= 搜索 =========================
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
                            "vod_pic": info['logo'] or self.default_vod_pic,
                            "vod_remarks": f"{len(info['sources'])}个源"
                        })
                    if len(results) >= 20:
                        break
                if len(results) >= 20:
                    break
        return {"list": results}

    # ========================= 本地代理 =========================
    def localProxy(self, params):
        # 辅助函数：严格判断是否 HTTP 成功（2xx 或 206 部分内容）
        def is_success(result):
            return (result and isinstance(result, list) and len(result) >= 2 and
                    200 <= result[0] < 300)  # 只认 2xx 状态码
    
        src = params.get('__src')
        if src and src in self._module_spiders:
            try:
                clean = {k: v for k, v in params.items() if k != '__src'}
                spider = self._module_spiders[src]
    
                # 健康统计更新
                with self._health_lock:
                    if src not in self._spider_health:
                        self._spider_health[src] = {'fails': 0, 'last_fail': 0, 'calls': 0}
                    self._spider_health[src]['calls'] += 1
    
                result = spider.localProxy(clean)
    
                # ----- 核心修改：严格判断成功 -----
                if is_success(result):
                    # 请求成功，重置失败计数
                    with self._health_lock:
                        if src in self._spider_health:
                            self._spider_health[src]['fails'] = 0
                    return result
                else:
                    # 返回了 4xx、5xx 或格式错误，均视为失败
                    with self._health_lock:
                        self._spider_health[src]['fails'] += 1
                        self._spider_health[src]['last_fail'] = time.time()
    
                    # 连续失败 >= 3 次，触发后台重建
                    if self._spider_health[src]['fails'] >= 3:
                        self.logger.log(f"【{src}】连续失败 {self._spider_health[src]['fails']} 次 (含4xx/5xx)，触发后台重建")
                        self._clear_source_header_cache(src)
                        threading.Thread(target=self._rebuild_spider, args=(src,), daemon=True).start()
                        with self._health_lock:
                            self._spider_health[src]['fails'] = 0  # 重置，避免重复触发
                    
                    # 注意：这里不直接返回 result，而是继续尝试其他模块（fallback）
                    # 如果只有一个模块，且返回了 404，最终会走到最后的 _err
            except Exception as e:
                self.logger.log(f"【{src}】localProxy 异常: {e}")
                # 异常处理逻辑保持不变（计为失败并尝试重建）...
    
        # ----- 回退逻辑：严格判断（只取 2xx）-----
        for sp in self._module_spiders.values():
            try:
                result = sp.localProxy(params)
                if is_success(result):  # 只有 2xx 才作为有效回退
                    return result
            except Exception:
                continue
    
        # 所有模块都返回非 2xx，返回最终错误
        return self._err("无法处理该请求（所有模块均返回 4xx/5xx）")

    def _clear_source_header_cache(self, src_name):
        """清除指定源相关的 header 缓存"""
        keys_to_delete = []
        with self._header_cache._lock:
            for key in list(self._header_cache._d.keys()):
                if key.startswith(f"{src_name}||"):
                    keys_to_delete.append(key)
        for key in keys_to_delete:
            self._header_cache.put(key, None)  # 相当于删除

    def _rebuild_spider(self, src_name):
        """后台重建子模块实例"""
        try:
            self.logger.log(f"开始重建子模块: {src_name}")
            # 查找原始配置
            cfg = None
            for c in self._source_configs:
                if c['name'] == src_name and c.get('api'):
                    cfg = c
                    break
            if not cfg:
                self.logger.log(f"未找到 {src_name} 的配置，无法重建")
                return

            # 重新加载
            channels = self._load_py_source(cfg['api'], cfg)
            if channels:
                # 更新频道数据
                with self._channels_lock:
                    # 移除旧频道数据
                    self._channels = [ch for ch in self._channels if ch.get('source') != src_name]
                    # 添加新频道
                    self._channels.extend(channels)
                    # 更新分组
                    groups = {}
                    for ch in channels:
                        group = ch.get('group', '默认分类')
                        groups.setdefault(group, []).append(ch)
                    self._source_groups[src_name] = groups
                    self._interface_groups[src_name] = {'groups': list(groups.keys()), 'group_channels': groups}
                self._build_channel_index()
                self.logger.log(f"子模块 {src_name} 重建成功，加载 {len(channels)} 个频道")
            else:
                self.logger.log(f"子模块 {src_name} 重建失败，无频道数据")
        except Exception as e:
            self.logger.log(f"重建子模块 {src_name} 异常: {e}")

    def _err(self, msg):
        return [500, "application/vnd.apple.mpegurl", f"#EXTM3U\n#EXT-X-ENDLIST\n# {msg}"]

    def destroy(self):
        self._stop_refresh = True
        self._shutdown_flag.set()

        # 【优化】销毁所有子模块实例
        for name, spider in list(self._module_spiders.items()):
            if spider and hasattr(spider, 'destroy'):
                try:
                    spider.destroy()
                except Exception:
                    pass
        self._module_spiders.clear()

        if hasattr(self, 'session') and self.session:
            try:
                self.session.close()
            except Exception:
                pass
        if hasattr(self, '_proxy_sessions'):
            for _, (sess, _) in list(self._proxy_sessions._d.items()):
                try:
                    sess.close()
                except Exception:
                    pass
            self._proxy_sessions.clear()
        for ex in self._executors[:]:
            try:
                ex.shutdown(wait=False)
            except Exception:
                pass
        self._executors.clear()
        if hasattr(self, '_header_cache'):
            self._header_cache.clear()
        if hasattr(self, 'logger'):
            self.logger.flush()
        return ""