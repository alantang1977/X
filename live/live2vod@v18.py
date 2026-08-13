# -*- coding: utf-8 -*-
# @Author  : 陆小凤 (Optimized by AI)
# @Time    : 2026/8/13
"""
全能直播聚合插件 - 点播版 v18[稳定版]
优化重点：
1. 消除 init() 三重加载竞态 → 统一加载调度器
2. 忙等待 90s → threading.Event 通知 + 5s 快速失败
3. _channels 读取无锁 → 全程 RLock 保护
4. _cache_ready 异常时保持 False，确保状态一致
5. 保留全部原始功能：解密、EPG、过滤、分类显示、本地代理等
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
DEFAULT_USER_AGENT = 'okhttp/4.12.0'
DEFAULT_EXTERNAL_API_URL = "https://xn--v4q818bf34b.cc/helper/api.php"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else os.getcwd()
CACHE_DIR = os.path.join(SCRIPT_DIR, 'cache')
MODULE_CACHE_DIR = os.path.join(CACHE_DIR, 'modules')

def _ensure_cache_dirs():
    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(MODULE_CACHE_DIR, exist_ok=True)

_ensure_cache_dirs()

EPG_LOGO_URL = "https://cdn.jsdelivr.net/gh/mursor1985/epg/logo/{name}.png"
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
            self._flush()

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

# ========================= 解密模块 =========================
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

def _strip_pkcs7(d):
    if d:
        p = d[-1]
        if 0 < p <= 16 and d[-p:] == bytes([p]) * p:
            return d[:-p]
    return d

def _contains_special_strings(response):
    """参照 get.php containsSpecialStrings"""
    if not isinstance(response, str):
        return False
    return bool(re.search(r'sites|genre|EXTINF', response))

def _extract_text(response_no_spaces):
    """
    参照 get.php extractText：
    1) rtrim 掉末尾所有 '*'（PHP rtrim($s, '**') 的字符掩码实际等价于 rtrim($s, '*')）
    2) 取最后一组 '**' 之后的内容
    """
    trimmed = response_no_spaces.rstrip('*')
    pos = trimmed.rfind('**')
    if pos != -1:
        return trimmed[pos + 2:]
    return trimmed

def _extract_encryption_params(s):
    """参照 get.php extract_encryption_params"""
    prefix = "2423"
    suffix = "2324"
    suffix_pos = s.find(suffix)
    if suffix_pos == -1:
        return None
    pwd_mix = s[:suffix_pos + len(suffix)]
    if len(s) < 26:
        return None
    roundtime_in_hax = s[-26:]
    encrypted_text = s[len(pwd_mix):-26]
    pwd_in_hax = pwd_mix[len(prefix):-len(suffix)]
    return {
        'pwdInHax': pwd_in_hax,
        'roundtimeInHax': roundtime_in_hax,
        'encryptedText': encrypted_text
    }

def _decrypt_aes(encrypted_text_hex, pwd_in_hax, roundtime_in_hax):
    """
    参照 get.php decrypt_aes: AES-128-CBC
    PHP 使用 str_pad($bin, 16, "0", STR_PAD_RIGHT)，即右侧补字符 '0'（ASCII 48），不是 \x00
    """
    if not _HAS_AES:
        return None
    try:
        round_time = bytes.fromhex(roundtime_in_hax)
        pwd = bytes.fromhex(pwd_in_hax)
    except Exception:
        return None

    # PHP: str_pad($roundTime, 16, "0", STR_PAD_RIGHT)
    iv = round_time.ljust(16, b'0')
    key = pwd.ljust(16, b'0')

    try:
        cipher_bytes = bytes.fromhex(encrypted_text_hex)
    except Exception:
        return None

    decrypted = None
    if _AES_MODE == 'pycryptodome':
        try:
            decrypted = _AES_IMPL.new(key, _AES_IMPL.MODE_CBC, iv).decrypt(cipher_bytes)
        except Exception:
            return None
    elif _AES_MODE == 'pyaes':
        try:
            aes = _AES_IMPL.AESModeOfOperationCBC(key, iv=iv)
            d = _AES_IMPL.Decrypter(aes)
            decrypted = d.feed(cipher_bytes)
            decrypted += d.feed()
        except Exception:
            return None

    if decrypted:
        return _strip_pkcs7(decrypted)
    return None

def _extract_content(response):
    """
    参照 get.php extractContent 的解密逻辑。
    支持 ** Base64 多层解码 和 2423 前缀 AES 多层解码。
    返回解密后的字符串，若无法解密返回 None。
    注意：不包含 PHP 源码中的任何注释前缀。
    """
    if not response:
        return None

    MAX_ITER = 10
    current = response.strip()

    for _ in range(MAX_ITER):
        has_double_star = '**' in current
        starts_with_2423 = current.startswith('2423')

        if not has_double_star and not starts_with_2423:
            break

        if has_double_star:
            response_no_spaces = re.sub(r'\s+', '', current)
            cleaned_text = _extract_text(response_no_spaces)
            try:
                decoded = base64.b64decode(cleaned_text).decode('utf-8', errors='replace')
                current = decoded
                continue
            except Exception:
                return None

        if starts_with_2423:
            params = _extract_encryption_params(current)
            if not params:
                return None
            decrypted = _decrypt_aes(params['encryptedText'], params['pwdInHax'], params['roundtimeInHax'])
            if not decrypted:
                return None
            current = decrypted.decode('utf-8', errors='replace')
            continue

    return current if current else None

def _is_plaintext(content):
    """判断内容是否已经是明文（无需解密）"""
    if not isinstance(content, str):
        return False
    content = content.strip()
    if content.startswith('{') or content.startswith('['):
        try:
            json.loads(content)
            return True
        except Exception:
            pass
    if _contains_special_strings(content):
        return True
    return False

def try_decrypt_content(content, url='', external_api_url=DEFAULT_EXTERNAL_API_URL, session=None):
    if not content:
        return None

    # 已经是明文，直接返回
    if _is_plaintext(content):
        return content

    # 参照 get.php 解密逻辑
    result = _extract_content(content)
    if result:
        return result

    # 外部 API 兜底（保留原始能力）
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
    def __init__(self, ext_config=None):
        self.config = ext_config or {}
        self.enabled = self.config.get('启用', True)

        t2s_map = self.config.get('t2s_map', {})
        if not isinstance(t2s_map, dict):
            t2s_map = {}
        self.t2s_table = str.maketrans(t2s_map)

        self.cn_num_map = self.config.get('cn_num_map', {})
        if not isinstance(self.cn_num_map, dict):
            self.cn_num_map = {}

        self.builtin_map = self.config.get('builtin_map', {})
        if not isinstance(self.builtin_map, dict):
            self.builtin_map = {}

        quality_words = self.config.get('quality_words', [])
        operator_words = self.config.get('operator_words', [])
        self.quality_pattern = self._build_pattern(quality_words)
        self.operator_pattern = self._build_pattern(operator_words)

        self._canonical_map = {}
        self._build_map()

    def _build_pattern(self, word_list):
        if not word_list:
            return re.compile(r'(?!)')
        if isinstance(word_list, str):
            word_list = [word_list.strip()] if word_list.strip() else []
        escaped = [re.escape(w) for w in word_list if w.strip()]
        if not escaped:
            return re.compile(r'(?!)')
        return re.compile('|'.join(escaped), re.IGNORECASE)

    def _build_map(self):
        self._canonical_map = {}
        for canonical in self.builtin_map.values():
            k = self.normalize_key(canonical)
            if k and k not in self._canonical_map:
                self._canonical_map[k] = canonical

        aliases = self.config.get('builtin_aliases', {})
        if not aliases:
            alias_path = self.config.get('aliases_path') or os.path.join(SCRIPT_DIR, 'channel_db.json')
            if os.path.exists(alias_path):
                try:
                    with open(alias_path, 'r', encoding='utf-8') as f:
                        db = json.load(f)
                    aliases = db.get('builtin_aliases', {})
                except Exception:
                    pass

        for canonical, alias_list in aliases.items():
            k = self.normalize_key(canonical)
            if k and k not in self._canonical_map:
                self._canonical_map[k] = canonical
            for alias in (alias_list if isinstance(alias_list, list) else []):
                k2 = self.normalize_key(alias)
                if k2:
                    self._canonical_map[k2] = canonical

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
        s = self.quality_pattern.sub('', s)
        s = self.operator_pattern.sub('', s)
        s = re.sub(r'[\s\-_·.|"\'\'\u2019，,、（）()\[\]【】]', '', s)
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
    CATEGORY_TIMEOUT = 5.0  # 影视TV前端容忍的超时时间（秒）

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
        # OPTIMIZED: 使用 RLock 支持同线程重入，避免死锁
        self._channels_lock = threading.RLock()
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
        self._agg_lock = threading.RLock()
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
        # OPTIMIZED: 用 Event 替代忙等待，每个源独立通知
        self._source_ready_events = {}
        self._global_ready_event = threading.Event()
        self._first_source_name = None
        self._focus_count = {}

        self.category_aliases = {}
        self._display_config = None
        self._interface_ids = []
        self._static_ids = []

        self._spider_health = {}
        self._health_lock = threading.Lock()

        self.filter_enabled = False
        self.filter_ignore = []
        self.filter_keep = []
        self.filter_global_filter = []
        self.filter_global_keep = []

        self.display_enabled = False
        self.display_order = []
        self.display_aliases = {}

    # ========================= 辅助方法 =========================
    def _resolve_resource_path(self, source):
        if not source:
            return None, None
        source = source.strip()
        is_local = False
        if source.startswith(('./', '.\\', '/')):
            is_local = True
        elif not source.lower().startswith(('http://', 'https://', 'ftp://')):
            is_local = True

        if is_local:
            if source.startswith('./') or source.startswith('.\\'):
                file_path = os.path.join(SCRIPT_DIR, source[2:])
            elif source.startswith('/'):
                file_path = source
            elif not os.path.isabs(source):
                file_path = os.path.join(SCRIPT_DIR, source)
            else:
                file_path = source
            return 'local', file_path
        else:
            return 'remote', source

    def _load_json_resource(self, source, allow_decrypt=False):
        if not source:
            return None
        res_type, res_path = self._resolve_resource_path(source)
        if not res_type:
            return None

        if res_type == 'local':
            if not os.path.exists(res_path):
                self.logger.log(f"本地文件不存在: {res_path}")
                return None
            try:
                with open(res_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                self.logger.log(f"本地文件JSON解析失败 {res_path}: {e}")
                return None
            except Exception as e:
                self.logger.log(f"读取本地文件失败 {res_path}: {e}")
                return None
        else:
            try:
                resp = self.session.get(
                    res_path,
                    timeout=(self.connect_timeout, self.read_timeout_url),
                    verify=False
                )
                if resp.status_code != 200:
                    self.logger.log(f"远程资源返回非200: {res_path} [{resp.status_code}]")
                    return None
                text = resp.text
                try:
                    return json.loads(text)
                except Exception:
                    if allow_decrypt:
                        dec = try_decrypt_content(text, res_path, self.external_api_url, self.session)
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
                    return None
            except Exception as e:
                self.logger.log(f"远程加载失败 {res_path}: {e}")
                return None

    def _load_config_file(self, path):
        if not path:
            return None
        return self._load_json_resource(path, allow_decrypt=False)

    def _load_ext_from_path(self, path):
        if not path:
            return None
        result = self._load_json_resource(path, allow_decrypt=False)
        if result is not None:
            return result
        if path.startswith(('http://', 'https://', 'ftp://')):
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

    # ========================= 初始化（核心优化区域）=========================
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
        self.logger.log("=" * 50 + " 启动 VOD（Optimized v18） " + "=" * 50)

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

        # 获取并合并 lives
        raw_lives = self._fetch_and_merge_lives(ext)
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

        self._interface_ids = [cfg['name'] for cfg in self._source_configs]
        self._static_ids = list(self._category_map.keys())

        self._category_order = []
        self._category_type = {}
        for name in self._interface_ids:
            self._category_order.append(name)
            self._category_type[name] = 'interface'
        for cat in self._static_ids:
            self._category_order.append(cat)
            self._category_type[cat] = 'static'

        self._parse_display_config(ext)

        for cfg in self._source_configs:
            self._source_loaded[cfg['name']] = False
            # OPTIMIZED: 每个源预创建 Event
            self._source_ready_events[cfg['name']] = threading.Event()

        # ==================== 核心优化：统一加载调度 ====================
        if self.filter_enabled:
            # 过滤模式：必须全量加载后才能过滤，统一同步加载
            self.logger.log("过滤模式：同步加载所有源并构建缓存")
            self._load_all_sources_sync()
            self._build_caches()
            with self._cache_lock:
                self._cache_ready = True
            self.logger.log("过滤后数据已就绪")
        else:
            # 快速模式：首源同步（快速首屏响应），其余后台加载
            if self._source_configs:
                self.logger.log(f"快速模式：同步加载首源 {self._first_source_name}")
                self._load_one_source_safe(self._source_configs[0])

            if len(self._source_configs) > 1:
                t = threading.Thread(target=self._load_remaining_bg, daemon=True)
                t.start()
            else:
                self._global_ready = True
                self._global_ready_event.set()

            # 尝试加载磁盘缓存
            self._load_cache_from_disk()
            if self._cache_ready:
                self.logger.log("全量缓存加载成功，数据已就绪")
                if self.refresh_interval > 0 and self.enable_refresh:
                    self._start_refresh()
            else:
                threading.Thread(target=self._build_cache_bg, daemon=True).start()

        self.logger.flush()

    # ========================= 统一加载调度器（新增）=========================
    def _load_one_source_safe(self, cfg):
        """线程安全的单源加载，带双重检查锁定"""
        name = cfg['name']
        # 快速路径检查
        if self._source_loaded.get(name):
            return

        with self._channels_lock:
            # 再次检查（双重检查锁定）
            if self._source_loaded.get(name):
                return

            channels = []
            if cfg.get('api'):
                channels = self._load_py_source(cfg['api'], cfg)
            elif cfg.get('url'):
                channels = self._load_url_source(cfg)

            if channels:
                self._channels.extend(channels)
                groups = {}
                for ch in channels:
                    group = ch.get('group', '默认分类')
                    groups.setdefault(group, []).append(ch)
                self._source_groups[name] = groups
                self._interface_groups[name] = {
                    'groups': list(groups.keys()),
                    'group_channels': groups
                }
                self.logger.log(f"【{name}】加载 {len(channels)} 个频道, {len(groups)} 个分组")
            else:
                self._source_groups[name] = {}
                self._interface_groups[name] = {'groups': [], 'group_channels': {}}
                self.logger.log(f"【{name}】加载完成，但无频道数据")

            self._source_loaded[name] = True
            # 通知所有等待该源的线程
            event = self._source_ready_events.get(name)
            if event:
                event.set()

    def _load_all_sources_sync(self):
        """同步加载所有源（过滤模式专用）"""
        self.logger.log("开始同步加载所有源...")
        for cfg in self._source_configs:
            if self._shutdown_flag.is_set():
                break
            self._load_one_source_safe(cfg)
        self._global_ready = True
        self._global_ready_event.set()
        self.logger.log("所有源加载完成")

    def _load_remaining_bg(self):
        """后台加载剩余源（快速模式专用）"""
        for cfg in self._source_configs[1:]:
            if self._shutdown_flag.is_set():
                break
            self._load_one_source_safe(cfg)
            time.sleep(0.1)

        # 检查是否全部完成
        all_done = all(self._source_loaded.get(c['name'], False) 
                      for c in self._source_configs)
        if all_done:
            self._global_ready = True
            self._global_ready_event.set()
            self.logger.log("后台加载全部完成，开始构建全量缓存")
            self._build_caches()
            self._save_cache_to_disk()
            if self.refresh_interval > 0 and self.enable_refresh:
                self._start_refresh()
        self.logger.debug("后台源加载完成")

    # ========================= 显示配置解析 =========================
    def _parse_display_config(self, ext):
        self.display_enabled = False
        self.display_order = []
        self.display_aliases = {}

        display_key = None
        for key in ext.keys():
            if key.startswith('分类显示|'):
                display_key = key
                break

        if not display_key:
            if '分类显示' in ext:
                display_key = '分类显示'
                self.display_enabled = True
                self.logger.log("检测到旧版 '分类显示' 配置，自动启用")
            else:
                return

        status = display_key.split('|')[1] if '|' in display_key else '开启'
        if status == '关闭':
            self.logger.debug("分类显示配置已关闭")
            return

        self.display_enabled = True
        display_config = ext.get(display_key, {})
        if not isinstance(display_config, dict):
            self.logger.log(f"分类显示配置格式错误，应为字典: {display_config}")
            return

        top = display_config.get('置顶', [])
        middle = display_config.get('静态', [])
        bottom = display_config.get('后置', [])

        all_entries = []

        def process_entries(entries, group_name):
            if not isinstance(entries, list):
                return
            for entry in entries:
                if not entry:
                    continue
                if isinstance(entry, str):
                    sub_entries = entry.split('|')
                    for sub in sub_entries:
                        sub = sub.strip()
                        if not sub:
                            continue
                        if '<别名>' in sub:
                            parts = sub.split('<别名>', 1)
                            id_val = parts[0].strip()
                            alias_val = parts[1].strip() if len(parts) > 1 else id_val
                        else:
                            id_val = sub.strip()
                            alias_val = id_val
                        if id_val:
                            all_entries.append((group_name, id_val, alias_val))
                elif isinstance(entry, dict):
                    id_val = entry.get('id', '')
                    alias_val = entry.get('name', id_val)
                    if id_val:
                        all_entries.append((group_name, id_val, alias_val))

        process_entries(top, '置顶')
        process_entries(middle, '静态')
        process_entries(bottom, '后置')

        order = []
        aliases = {}
        for group_name, id_val, alias_val in all_entries:
            if id_val not in order:
                order.append(id_val)
                aliases[id_val] = alias_val if alias_val else id_val

        valid_order = [x for x in order if x in self._interface_ids or x in self._static_ids]
        if valid_order:
            self.display_order = valid_order
            self.display_aliases = aliases
            self._category_order = valid_order
            self.logger.debug(f"分类显示配置已应用，顺序: {valid_order}")
        else:
            self.logger.log("分类显示配置中所有ID均无效，保持原有顺序")

    # ========================= 配置解析 =========================
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

        # 解析过滤规则
        filter_key = None
        for key in ext.keys():
            if key.startswith('过滤规则|'):
                filter_key = key
                break

        self.filter_enabled = False
        self.filter_ignore = []
        self.filter_keep = []
        self.filter_global_filter = []
        self.filter_global_keep = []

        if filter_key:
            status = filter_key.split('|')[1] if '|' in filter_key else '开启'
            if status == '开启':
                self.filter_enabled = True
                filter_config = ext.get(filter_key, {})
                if isinstance(filter_config, dict):
                    self.filter_ignore = self._normalize_rule_list(filter_config.get('忽略', []))
                    self.filter_keep = self._normalize_rule_list(filter_config.get('保留', []))
                    self.filter_global_filter = self._normalize_string_list(filter_config.get('全局_过滤词', []))
                    self.filter_global_keep = self._normalize_string_list(filter_config.get('全局_保留词', []))
                    self.logger.debug(f"过滤规则已启用: 忽略{len(self.filter_ignore)}条, 保留{len(self.filter_keep)}条")
            else:
                self.logger.debug("过滤规则已关闭")

    def _normalize_rule_list(self, rules):
        if not isinstance(rules, list):
            return []
        result = []
        for rule in rules:
            if not isinstance(rule, dict):
                continue
            interfaces = rule.get('接口', None)
            categories = rule.get('分类', None)
            if not isinstance(interfaces, list):
                interfaces = [interfaces] if interfaces is not None else []
            if not isinstance(categories, list):
                categories = [categories] if categories is not None else []
            if not interfaces and not categories:
                continue
            if not interfaces:
                interfaces = ['.*']
            if not categories:
                categories = ['.*']
            for iface in interfaces:
                for cat in categories:
                    final_iface = iface if iface else '.*'
                    final_cat = cat if cat else '.*'
                    result.append({'接口': final_iface, '分类': final_cat})
        return result

    def _normalize_string_list(self, items):
        if isinstance(items, str):
            items = [items]
        elif not isinstance(items, list):
            return []
        result = []
        for item in items:
            item = str(item).strip()
            if not item:
                continue
            if '|' in item:
                for sub in item.split('|'):
                    sub = sub.strip()
                    if sub:
                        result.append(sub)
            else:
                result.append(item)
        return result

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

    # ========================= 统一资源加载 =========================
    def _fetch_and_merge_lives(self, ext):
        all_lives = []

        raw_lives = self._p(ext, 'lives', default=[])
        if isinstance(raw_lives, list):
            for item in raw_lives:
                if isinstance(item, str):
                    item = item.strip()
                    if not item:
                        continue
                    data = self._load_json_resource(item, allow_decrypt=True)
                    if data:
                        if isinstance(data, list):
                            all_lives.extend(data)
                            self.logger.debug(f"从资源加载 {len(data)} 个源: {item}")
                        elif isinstance(data, dict) and 'lives' in data and isinstance(data['lives'], list):
                            all_lives.extend(data['lives'])
                            self.logger.debug(f"从资源加载 {len(data['lives'])} 个源: {item}")
                        else:
                            self.logger.log(f"资源数据格式无效: {item}")
                else:
                    all_lives.append(item)

        urls = self._p(ext, '接口_单仓', 'lives_urls', default=[])
        if isinstance(urls, str):
            urls = [urls] if urls else []
        elif not isinstance(urls, list):
            urls = []

        if urls:
            self.logger.log(f"加载配置源: {len(urls)} 个")
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
                            self.logger.log(f"加载配置源异常: {e}")
                finally:
                    if ex in self._executors:
                        self._executors.remove(ex)

        simple_urls = self._p(ext, '接口_直播', 'lives_url', default=[])
        if isinstance(simple_urls, str):
            simple_urls = [simple_urls] if simple_urls else []
        elif not isinstance(simple_urls, list):
            simple_urls = []

        for u in simple_urls:
            if isinstance(u, str) and u.strip():
                u = u.strip()
                data = self._fetch_one_remote(u)
                if data:
                    if isinstance(data, list):
                        all_lives.extend(data)
                    elif isinstance(data, dict):
                        lv = self._p(data, 'lives')
                        if isinstance(lv, list):
                            all_lives.extend(lv)

        return self._dedup_lives(all_lives)

    def _fetch_one_remote(self, url):
        if not url:
            return None
        return self._load_json_resource(url, allow_decrypt=True)

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

    # ========================= 源加载（保留原始能力）=========================
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
                old_spider = self._module_spiders.get(name)
                if old_spider and hasattr(old_spider, 'destroy'):
                    try:
                        old_spider.destroy()
                    except Exception as e:
                        self.logger.log(f"销毁旧实例 {name} 异常: {e}")
                self._module_spiders[name] = spider
                with self._health_lock:
                    self._spider_health[name] = {'fails': 0, 'last_fail': 0, 'calls': 0, 'last_rebuild': 0}
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

    # ========================= 匹配工具方法 =========================
    def _is_regex_pattern(self, pattern):
        return bool(re.search(r'[\\^$.|?*+(){}\[\]]', pattern))

    def _match_pattern(self, pattern, text):
        if not text or not pattern:
            return False
        if self._is_regex_pattern(pattern):
            try:
                return re.search(pattern, text, re.IGNORECASE) is not None
            except re.error:
                return pattern.lower() in text.lower()
        else:
            return pattern.lower() in text.lower()

    def _match_any_pattern(self, patterns, text):
        if not patterns or not text:
            return False
        for p in patterns:
            if self._match_pattern(p, text):
                return True
        return False

    def _match_category_rule(self, rule, source, group):
        if not rule or not isinstance(rule, dict):
            return False
        interface_pattern = rule.get('接口', '.*')
        category_pattern = rule.get('分类', '.*')

        if interface_pattern != '.*':
            if interface_pattern.lower() not in source.lower():
                return False

        if category_pattern == '.*':
            return True
        if self._is_regex_pattern(category_pattern):
            try:
                return re.search(category_pattern, group, re.IGNORECASE) is not None
            except re.error:
                return category_pattern.lower() in group.lower()
        else:
            return category_pattern.lower() in group.lower()

    # ========================= 过滤主方法（核心优化）=========================
    def _apply_filters(self):
        """
        应用过滤规则（全程RLock保护，消除竞态）：
        1. 忽略规则绝对优先：被忽略的频道彻底丢弃
        2. 保留规则保护频道不被全局过滤误伤
        3. 全局过滤/保留仅对未被忽略且未被保留的频道生效
        """
        if not self.filter_enabled:
            self.logger.debug("过滤功能已关闭，跳过")
            return

        # OPTIMIZED: 全程在 _channels_lock 保护下执行，避免与后台加载竞态
        with self._channels_lock:
            if not self._channels:
                return

            total_before = len(self._channels)
            step_counts = {
                'category_ignore': 0,
                'category_keep': 0,
                'global_filter': 0,
                'global_keep': 0
            }

            for ch in self._channels:
                ch.pop('_drop', None)
                ch.pop('_keep', None)
                ch.pop('_ignored', None)

            # 步骤1：分类忽略（绝对优先，不可救回）
            if self.filter_ignore:
                for ch in self._channels:
                    if ch.get('_drop'):
                        continue
                    source = ch.get('source', '')
                    group = ch.get('group', '')
                    for rule in self.filter_ignore:
                        if self._match_category_rule(rule, source, group):
                            ch['_drop'] = True
                            ch['_ignored'] = True
                            step_counts['category_ignore'] += 1
                            self.logger.debug(f"【分类忽略】{source} → {group} 命中规则，彻底丢弃 {ch.get('name')}")
                            break

            # 步骤2：分类保留（仅对未被忽略的频道保护）
            if self.filter_keep:
                for ch in self._channels:
                    if ch.get('_drop') or ch.get('_keep'):
                        continue
                    source = ch.get('source', '')
                    group = ch.get('group', '')
                    for rule in self.filter_keep:
                        if self._match_category_rule(rule, source, group):
                            ch['_keep'] = True
                            step_counts['category_keep'] += 1
                            self.logger.debug(f"【分类保留】{source} → {group} 保护频道 {ch.get('name')}")
                            break

            # 步骤3：全局过滤（仅对未被忽略且未被保留的频道）
            if self.filter_global_filter:
                for ch in self._channels:
                    if ch.get('_drop') or ch.get('_keep'):
                        continue
                    combined = f"{ch.get('name', '')} {ch.get('url', '')}"
                    if self._match_any_pattern(self.filter_global_filter, combined):
                        ch['_drop'] = True
                        step_counts['global_filter'] += 1
                        self.logger.debug(f"【全局过滤】{ch.get('name')} 命中过滤词，丢弃")

            # 步骤4：全局保留（仅救回被全局过滤的，不可救回被忽略的）
            if self.filter_global_keep:
                for ch in self._channels:
                    if ch.get('_ignored'):
                        continue
                    if not ch.get('_drop') or ch.get('_keep'):
                        continue
                    combined = f"{ch.get('name', '')} {ch.get('url', '')}"
                    if self._match_any_pattern(self.filter_global_keep, combined):
                        ch['_drop'] = False
                        ch['_keep'] = True
                        step_counts['global_keep'] += 1
                        self.logger.debug(f"【全局保留】{ch.get('name')} 命中保留词，救回")

            # 最终过滤
            filtered = [ch for ch in self._channels if not ch.get('_drop')]
            dropped = total_before - len(filtered)
            self._channels = filtered

            self.logger.log(
                f"过滤完成：总频道 {total_before}，保留 {len(filtered)}，丢弃 {dropped} "
                f"(分类忽略 {step_counts['category_ignore']}，"
                f"分类保留 {step_counts['category_keep']}，"
                f"全局过滤 {step_counts['global_filter']}，"
                f"全局保留救回 {step_counts['global_keep']})"
            )

            # 清理标记
            for ch in self._channels:
                ch.pop('_drop', None)
                ch.pop('_keep', None)
                ch.pop('_ignored', None)

    # ========================= 构建缓存（状态一致性优化）=========================
    def _build_caches(self):
        self._apply_filters()
        self._build_channel_index()

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

                    unique_sources = {}
                    for s in sources:
                        url = s.get('url', '')
                        if not url:
                            continue
                        if url not in unique_sources:
                            unique_sources[url] = s
                    deduped_sources = list(unique_sources.values())

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
                # OPTIMIZED: 只有真正构建出非空数据才标记ready
                self._cache_ready = bool(cache_cats)
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
        if not data:
            return "暂无节目预告"

        if isinstance(data, dict) and 'epg_data' in data:
            epg_list = data.get('epg_data', [])
        elif isinstance(data, list):
            epg_list = data
        else:
            return "节目数据格式异常"

        if not epg_list:
            return "暂无节目预告"

        now = time.strftime('%H:%M')
        lines = []
        for prog in epg_list[:8]:
            if not isinstance(prog, dict):
                continue
            start = prog.get('start', '').strip()
            end = prog.get('end', '').strip()
            title = prog.get('title', '未知节目').strip()
            title = re.sub(r'\s*--.*$', '', title)
            if not start:
                continue
            is_current = False
            if start <= now and (not end or end >= now):
                is_current = True
            mark = ' ▶' if is_current else ''
            lines.append(f"{start} {title}{mark}")

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
            # OPTIMIZED: 不复用init已加载的数据，而是复用 _source_configs 统一调度
            if not self._global_ready:
                for cfg in self._source_configs:
                    if not self._source_loaded.get(cfg['name']):
                        self._load_one_source_safe(cfg)
                self._global_ready = True
                self._global_ready_event.set()

            self._build_channel_index()
            self._build_caches()
            self._save_cache_to_disk()
            self._auto_clean_cache()
            self.logger.log(f"全量缓存构建完成，耗时 {time.time()-t0:.1f}s")
            if self.refresh_interval > 0 and self.enable_refresh:
                self._start_refresh()
        except Exception as e:
            self.logger.log(f"缓存构建异常: {e}")
            # OPTIMIZED: 异常时确保 cache_ready 为 False
            with self._cache_lock:
                self._cache_ready = False
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
                display_name = self.display_aliases.get(cat) if self.display_enabled else None
                if not display_name:
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
            url = ch.get('url', '')
            if not url:
                continue
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
        """
        OPTIMIZED: 用 threading.Event.wait(timeout) 替代忙等待 90 秒
        影视TV规范：5 秒内必须响应，超时返回空列表（前端不卡死）
        """
        cat_type = self._category_type.get(tid, 'static')
        if cat_type == 'interface':
            # 首源直接返回（已同步加载）
            if tid == self._first_source_name:
                return self._interface_category_content(tid, pg)

            # 已加载的直接返回
            if self._source_loaded.get(tid, False):
                return self._interface_category_content(tid, pg)

            # OPTIMIZED: Event 等待替代 while sleep 轮询
            event = self._source_ready_events.get(tid)
            if event:
                ready = event.wait(timeout=self.CATEGORY_TIMEOUT)
                if ready:
                    return self._interface_category_content(tid, pg)

            # 超时或没有Event：快速返回空，不阻塞影视TV前端
            return {"list": [], "page": 1, "pagecount": 1, "limit": 30, "total": 0}

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

            else:
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
        headers = self._ensure_headers_with_default(headers)
        result = {
            "parse": 0,
            "url": id,
            "playUrl": "",
            "flag": flag,
            "header": headers,
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
        def is_success(result):
            return (result and isinstance(result, list) and len(result) >= 2 and
                    200 <= result[0] < 300)

        src = params.get('__src')
        if src and src in self._module_spiders:
            try:
                clean = {k: v for k, v in params.items() if k != '__src'}
                spider = self._module_spiders[src]

                with self._health_lock:
                    if src not in self._spider_health:
                        self._spider_health[src] = {'fails': 0, 'last_fail': 0, 'calls': 0}
                    self._spider_health[src]['calls'] += 1

                result = spider.localProxy(clean)

                if is_success(result):
                    with self._health_lock:
                        if src in self._spider_health:
                            self._spider_health[src]['fails'] = 0
                    return result
                else:
                    with self._health_lock:
                        self._spider_health[src]['fails'] += 1
                        self._spider_health[src]['last_fail'] = time.time()

                    if self._spider_health[src]['fails'] >= 3:
                        with self._health_lock:
                            last_rebuild = self._spider_health[src].get('last_rebuild', 0)
                            # 修复2：60秒冷却期，防止宕机时无限重建
                            if time.time() - last_rebuild < 60:
                                self.logger.log(f"【{src}】重建冷却中（还剩 {60 - int(time.time() - last_rebuild)}s），跳过")
                                return self._err("模块冷却中，请稍后重试")
                            # 重置失败计数并记录重建时间
                            self._spider_health[src]['last_rebuild'] = time.time()
                            self._spider_health[src]['fails'] = 0
    
                        self.logger.log(f"【{src}】连续失败，触发后台重建")
                        self._clear_source_header_cache(src)
                        threading.Thread(target=self._rebuild_spider, args=(src,), daemon=True).start()
            except Exception as e:
                self.logger.log(f"【{src}】localProxy 异常: {e}")

        for sp in self._module_spiders.values():
            try:
                result = sp.localProxy(params)
                if is_success(result):
                    return result
            except Exception:
                continue

        return self._err("无法处理该请求（所有模块均返回 4xx/5xx）")

    def _clear_source_header_cache(self, src_name):
        keys_to_delete = []
        # OPTIMIZED: 通过公共接口操作，不直接访问内部属性
        with self._header_cache._lock:
            for key in list(self._header_cache._d.keys()):
                if key.startswith(f"{src_name}||"):
                    keys_to_delete.append(key)
        for key in keys_to_delete:
            self._header_cache.put(key, None)

    def _rebuild_spider(self, src_name):
        """重建子模块：强制刷新缓存、原子替换、统一重建索引、同步就绪状态"""
        try:
            # 查找对应配置
            cfg = None
            for c in self._source_configs:
                if c['name'] == src_name and c.get('api'):
                    cfg = c
                    break
            if not cfg:
                self.logger.log(f"【{src_name}】未找到配置，无法重建")
                self._source_loaded[src_name] = False
                self._source_ready_events.get(src_name, threading.Event()).clear()
                return

            # 修复4：强制清除远程模块缓存，确保加载最新代码
            api_url = cfg['api']
            if api_url.startswith(('http://', 'https://')):
                ck = hashlib.md5(api_url.encode()).hexdigest() + '.py'
                cf = os.path.join(MODULE_CACHE_DIR, ck)
                if os.path.exists(cf):
                    try:
                        os.remove(cf)
                        self.logger.log(f"【{src_name}】已清除模块缓存，强制重新下载")
                    except Exception as e:
                        self.logger.debug(f"清除模块缓存失败: {e}")

            # 重新加载模块与频道
            channels = self._load_py_source(api_url, cfg)

            # 修复1：在 _channels_lock 内原子替换 _channels，绝不暴露中间状态
            with self._channels_lock:
                new_channels = [ch for ch in self._channels if ch.get('source') != src_name]
                if channels:
                    new_channels.extend(channels)
                self._channels = new_channels

                # 同步更新源级分组索引（供 homeVod fallback 使用）
                if channels:
                    groups = {}
                    for ch in channels:
                        group = ch.get('group', '默认分类')
                        groups.setdefault(group, []).append(ch)
                    self._source_groups[src_name] = groups
                else:
                    self._source_groups.pop(src_name, None)

            # 修复1：统一调用 _build_caches() 重建所有派生状态（_interface_groups / _cache_data 等），
            # 避免直接 patch _interface_groups 导致的读者竞态。
            # 由于 _agg_lock 已改为 RLock，_build_caches 内部嵌套加锁不会死锁。
            if channels:
                self._build_caches()
                # 修复3：重建成功 → 标记就绪
                self._source_loaded[src_name] = True
                event = self._source_ready_events.get(src_name)
                if event:
                    event.set()
                self.logger.log(f"【{src_name}】重建成功，加载 {len(channels)} 个频道")
            else:
                # 修复3：重建失败/无数据 → 清除残留、标记未就绪
                with self._agg_lock:
                    self._interface_groups.pop(src_name, None)
                self._source_loaded[src_name] = False
                event = self._source_ready_events.get(src_name)
                if event:
                    event.clear()
                self.logger.log(f"【{src_name}】重建失败，已标记为未加载")

        except Exception as e:
            self.logger.log(f"【{src_name}】重建异常: {e}")
            # 修复3：异常时也必须回退状态，防止前端永远等待
            self._source_loaded[src_name] = False
            self._source_ready_events.get(src_name, threading.Event()).clear()


    def _err(self, msg):
        return [500, "application/vnd.apple.mpegurl", f"#EXTM3U\n#EXT-X-ENDLIST\n# {msg}"]

    def destroy(self):
        self._stop_refresh = True
        self._shutdown_flag.set()

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
