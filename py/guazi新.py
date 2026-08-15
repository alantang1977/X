# coding = utf-8
#!/usr/bin/python
import re
import sys
import os
import json
import time
import base64
import hashlib
import random
import string
import traceback
import urllib.parse
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
from base.spider import Spider

sys.path.append('..')

# ===================== 调试日志 =====================
# 写日志到 OK 影视常见可写目录，找不到就退化到 /tmp
def _log_path():
    candidates = [
        '/storage/emulated/0/ok影视/logs',
        '/storage/emulated/0/oktvbox/logs',
        '/storage/emulated/0/Python/logs',
        '/sdcard/ok影视/logs',
        '/tmp',
    ]
    for d in candidates:
        try:
            if os.path.isdir(d) or d == '/tmp':
                os.makedirs(d, exist_ok=True)
                return os.path.join(d, 'guazi.log')
        except Exception:
            continue
    return '/tmp/guazi.log'

LOG_FILE = _log_path()

def _write_log(level, msg):
    try:
        line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [{level}] {msg}\n"
        # 同时打 print 和写文件，方便在 OK 影视控制台直接看
        print(line, end='')
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(line)
    except Exception:
        pass

def log_info(msg):  _write_log('INFO', msg)
def log_warn(msg):  _write_log('WARN', msg)
def log_err(msg):   _write_log('ERROR', msg)
def log_debug(msg): _write_log('DEBUG', msg)

# 设备缓存文件路径
DEVICE_CACHE_DIRS = [
    '/storage/emulated/0/ok影视/cache',
    '/storage/emulated/0/oktvbox/cache',
    '/sdcard/ok影视/cache',
    '/tmp',
]
DEVICE_CACHE_FILE = None

def _resolve_device_cache_path():
    global DEVICE_CACHE_FILE
    for d in DEVICE_CACHE_DIRS:
        try:
            os.makedirs(d, exist_ok=True)
            DEVICE_CACHE_FILE = os.path.join(d, 'guazi_device.json')
            return DEVICE_CACHE_FILE
        except Exception:
            continue
    DEVICE_CACHE_FILE = '/tmp/guazi_device.json'
    return DEVICE_CACHE_FILE

def _load_device_cache():
    """加载持久化的 deviceId/deviceKey，避免每次重新注册"""
    p = _resolve_device_cache_path()
    try:
        if os.path.isfile(p):
            with open(p, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data.get('deviceId') and data.get('deviceKey'):
                    return data
    except Exception as e:
        log_warn(f"加载设备缓存失败: {e}")
    return None

def _save_device_cache(device_id, device_key, token=''):
    p = DEVICE_CACHE_FILE or _resolve_device_cache_path()
    try:
        with open(p, 'w', encoding='utf-8') as f:
            json.dump({
                'deviceId': device_id,
                'deviceKey': device_key,
                'token': token,
                'ts': int(time.time()),
            }, f)
        log_info(f"设备缓存已保存 -> {p}")
    except Exception as e:
        log_warn(f"保存设备缓存失败: {e}")

# ===================== 爬虫主体 =====================
class Spider(Spider):
    def __init__(self):
        self.api_ua = 'okhttp/3.12.0'
        self.media_ua = 'Lavf/57.83.100'
        self.media_referer = 'http://WJiZxLXA2.com/'
        self.name = "瓜子"
        # 兜底 API 域名
        self.hosts = [
            'https://api.anctjd.com',
            'https://apinew.uozvr.com',
            'https://api.w32z7vtd.com',
            'https://api.6a7nnf7.com',
            'https://api.umygrx3.com',
            'https://api.rmedphk.com',
        ]
        self.init_control_urls = ['https://api.rqqakqyn.com']

        self.host_index = 0
        self.host = self.hosts[self.host_index]

        self.AES_KEY = 'OITxa5OqAYjhswxx'
        self.AES_IV = 'rCMNwZASNBKZ8mXV'

        self.RSA_PUBLIC_KEY = "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDUM5+/y8sPsWkd1/RQS64X259EUwxFXFE5HlA65MqrxnPs0JqoSRojSDy5QhwvROlaD6TwRQHKMY2OAZ6SnQeUJsChTEFIR9qUkwrs3/MVUMxjsv6JS6Oe/juclyJGTgVmDhB55EafXsD0SQYVj/QXXsxR6ewR5E2kL52yAAD4yQIDAQAB"
        self.RSA_PRIVATE_KEY = """-----BEGIN RSA PRIVATE KEY-----
MIICdgIBADANBgkqhkiG9w0BAQEFAASCAmAwggJcAgEAAoGAe6hKrWLi1zQmjTT1
ozbE4QdFeJGNxubxld6GrFGximxfMsMB6BpJhpcTouAqywAFppiKetUBBbXwYsYU
1wNr648XVmPmCMCy4rY8vdliFnbMUj086DU6Z+/oXBdWU3/b1G0DN3E9wULRSwcK
ZT3wj/cCI1vsCm3gj2R5SqkA9Y0CAwEAAQKBgAJH+4CxV0/zBVcLiBCHvSANm0l7
HetybTh/j2p0Y1sTXro4ALwAaCTUeqdBjWiLSo9lNwDHFyq8zX90+gNxa7c5EqcW
V9FmlVXr8VhfBzcZo1nXeNdXFT7tQ2yah/odtdcx+vRMSGJd1t/5k5bDd9wAvYdI
DblMAg+wiKKZ5KcdAkEA1cCakEN4NexkF5tHPRrR6XOY/XHfkqXxEhMqmNbB9U34
saTJnLWIHC8IXys6Qmzz30TtzCjuOqKRRy+FMM4TdwJBAJQZFPjsGC+RqcG5UvVM
iMPhnwe/bXEehShK86yJK/g/UiKrO87h3aEu5gcJqBygTq3BBBoH2md3pr/W+hUM
WBsCQQChfhTIrdDinKi6lRxrdBnn0Ohjg2cwuqK5zzU9p/N+S9x7Ck8wUI53DKm8
jUJE8WAG7WLj/oCOWEh+ic6NIwTdAkEAj0X8nhx6AXsgCYRql1klbqtVmL8+95KZ
K7PnLWG/IfjQUy3pPGoSaZ7fdquG8bq8oyf5+dzjE/oTXcByS+6XRQJAP/5ciy1b
L3NhUhsaOVy55MHXnPjdcTX0FaLi+ybXZIfIQ2P4rb19mVq1feMbCXhz+L1rG8oa
t5lYKfpe8k83ZA==
-----END RSA PRIVATE KEY-----"""

        self.DEVICE_OLD_KEY = "aLFBMWpxBrIDAD1Si/KVvm41"

        # ===== 设备信息：先尝试读缓存，否则重新生成并保存 =====
        cached = _load_device_cache()
        if cached:
            self.deviceId = cached['deviceId']
            self.deviceKey = cached['deviceKey']
            self.token = cached.get('token', '')
            self.registered = bool(self.token)
            log_info(f"使用缓存设备 deviceId={self.deviceId}")
        else:
            # 15 位纯数字 deviceId（更像 Android 真实设备）
            self.deviceId = ''.join(random.choices('0123456789', k=15))
            # deviceKey 40 位 hex 大写（20 字节）
            self.deviceKey = ''.join(random.choices('0123456789ABCDEF', k=40))
            self.token = ""
            self.registered = False
            log_info(f"生成新设备 deviceId={self.deviceId}")

        self.token_id = ""

        self.header = {
            'User-Agent': self.api_ua,
            'code': 'GZ0055',
            'deviceId': self.deviceId,
            'lang': 'zh_cn',
            'Cache-Control': 'no-cache',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Version': '2608011',
            'PackageName': 'com.xf4a1daee2.g3520dce0d.f8a8ed889d20260813',
            'Ver': '3.0.5.2',
            'api-ver': '3.0.5.2',
            'Referer': self.host,
        }

        self.cache = {}
        self.cache_timeout = 300

        # ===================== 启动：域名 + token =====================
        log_info("===== 瓜子爬虫启动 =====")
        log_info(f"日志文件: {LOG_FILE}")
        log_info(f"初始 deviceId: {self.deviceId}")
        self.fetch_latest_hosts()
        self.init_token()

    def getName(self):
        return self.name

    def init(self, extend=''):
        pass

    # ===================== 域名拉取 =====================
    def fetch_latest_hosts(self):
        log_info("===== 正在检测并拉取最新 API 域名 =====")
        old_hosts = list(self.hosts)
        for control_url in self.init_control_urls:
            try:
                url = f"{control_url}/gz/initialize/getApiUrlList?parameter=key"
                resp = self._safe_post(url, timeout=6)
                if not resp:
                    continue
                if resp.status_code != 200:
                    log_warn(f"控制节点 {control_url} 返回 HTTP {resp.status_code}")
                    continue
                try:
                    resp_json = resp.json()
                except Exception:
                    log_warn(f"控制节点 {control_url} 返回非 JSON")
                    continue

                if resp_json.get('code') != 200 or 'data' not in resp_json:
                    log_warn(f"控制节点 {control_url} 业务码异常: {resp_json}")
                    continue

                decrypted_str = self._try_decrypt_init_data(resp_json['data'])
                if not decrypted_str:
                    continue
                try:
                    hosts_data = json.loads(decrypted_str)
                except Exception as e:
                    log_warn(f"解析域名 JSON 失败: {e}, raw={decrypted_str[:200]}")
                    continue

                candidate = None
                if isinstance(hosts_data, list) and hosts_data:
                    candidate = hosts_data
                elif isinstance(hosts_data, dict):
                    for k in ('list', 'urls', 'data', 'hosts'):
                        v = hosts_data.get(k)
                        if isinstance(v, list) and v:
                            candidate = v
                            break

                if candidate:
                    self.hosts = [str(x).strip() for x in candidate if str(x).strip()]
                    self.host_index = 0
                    self.host = self.hosts[0]
                    self.header['Referer'] = self.host
                    log_info(f"成功更新动态 API 域名: {self.hosts}")
                    return
            except Exception as e:
                log_warn(f"控制节点 {control_url} 异常: {e}")

        # 兜底：失败时保留原列表
        self.hosts = old_hosts
        self.host = self.hosts[self.host_index]
        self.header['Referer'] = self.host
        log_warn("动态获取域名失败，保留兜底域名列表。")

    def _try_decrypt_init_data(self, encrypted_text):
        if not encrypted_text:
            return ""
        try:
            decoded = base64.b64decode(encrypted_text)
            return decoded.decode('utf-8', errors='ignore')
        except Exception:
            return str(encrypted_text)

    # ===================== 鉴权 =====================
    def init_token(self):
        log_info("===== 初始化设备认证 =====")
        try:
            if not self.registered or not self.token:
                self.sign_up()
                if not self.token:
                    # signUp 失败尝试 signIn（如果服务端允许）
                    log_warn("signUp 未拿到 token，尝试 signIn")
                    self.sign_in()
            else:
                # 已有 token，先尝试刷一次
                try:
                    self.refresh_token()
                except Exception as e:
                    log_warn(f"refresh 失败，重新 signIn: {e}")
                    self.sign_in()
        except Exception as e:
            log_err(f"初始化 token 失败: {e}")
            self.token = ''

    def sign_up(self):
        log_info("注册新设备...")
        params = {
            "new_key": self.deviceKey,
            "old_key": self.DEVICE_OLD_KEY,
            "phone_type": 1,
            "code": "",
        }
        result = self._auth_request('/App/Authentication/Device/signUp', params)
        if not result:
            raise Exception("signUp 无返回")
        self._apply_auth(result)
        self.registered = True
        _save_device_cache(self.deviceId, self.deviceKey, self.token)

    def sign_in(self):
        log_info("设备登录...")
        params = {
            "new_key": self.deviceKey,
            "old_key": self.DEVICE_OLD_KEY,
        }
        result = self._auth_request('/App/Authentication/Device/signIn', params)
        if not result:
            raise Exception("signIn 无返回")
        self._apply_auth(result)
        _save_device_cache(self.deviceId, self.deviceKey, self.token)

    def _apply_auth(self, result):
        if not result:
            raise Exception("认证响应为空")
        new_token = result.get('token', '')
        if not new_token:
            log_err(f"认证无 token, 响应: {json.dumps(result)[:300]}")
            raise Exception("认证失败，无 token 返回")
        self.token = new_token
        new_token_id = result.get('app_user_id', '')
        if new_token_id:
            self.token_id = new_token_id
        log_info(f"获取 token 成功, 前缀: {self.token[:30]}...")

    def refresh_token(self):
        log_info("刷新 token...")
        result = self._auth_request('/App/Authentication/Authenticator/refresh', {})
        if not result:
            raise Exception("refresh 无返回")
        self._apply_auth(result)
        _save_device_cache(self.deviceId, self.deviceKey, self.token)

    def _auth_request(self, path, params):
        return self._send_encrypted_request(params, path, is_auth=True)

    # ===================== 请求核心 =====================
    def ensure_token(self):
        if not self.token:
            if self.registered:
                self.sign_in()
            else:
                self.sign_up()

    def _safe_post(self, url, headers=None, data=None, timeout=6):
        """兼容老版本 OK 影视：老版本 self.post 不支持 timeout kw"""
        try:
            # 优先尝试带 timeout（新版）
            return self.post(url, headers=headers or {}, data=data or {}, timeout=timeout)
        except TypeError as e:
            # 老版本：去掉 timeout
            if 'timeout' in str(e):
                log_warn("self.post 不支持 timeout 关键字，已降级")
                return self.post(url, headers=headers or {}, data=data or {})
            raise

    def _send_encrypted_request(self, data, path, is_auth=False):
        try:
            if not is_auth:
                self.ensure_token()

            json_params = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
            encrypted = self.aes_encrypt(json_params, self.AES_KEY, self.AES_IV)
            if not encrypted:
                log_err(f"AES 加密失败: {path}, data={json_params[:200]}")
                return None
            request_key = encrypted.upper()

            key_json = json.dumps({"iv": self.AES_IV, "key": self.AES_KEY}, ensure_ascii=False, separators=(',', ':'))
            keys = self.rsa_encrypt(key_json, self.RSA_PUBLIC_KEY)
            if not keys:
                log_err(f"RSA 加密失败: {path}")
                return None

            t = str(int(time.time()))

            # 修复后的签名串：token_id 留空独立成段
            # 常见 TV 爬虫格式：token_id=xxx,token=yyy,phone_type=1,...
            sign_str = (
                f"token_id={self.token_id},token={self.token},"
                f"phone_type=1,request_key={request_key},app_id=1,"
                f"time={t},keys={keys}*&zvdvdvddbfikkkumtmdwqppp?|4Y!s!2br"
            )
            signature = self.get_md5(sign_str)

            body = {
                'token': self.token,
                'token_id': self.token_id,
                'phone_type': '1',
                'time': t,
                'phone_model': 'xiaomi-25031',
                'keys': keys,
                'request_key': request_key,
                'signature': signature,
                'app_id': '1',
                'ad_version': '1',
            }

            url = f"{self.host}{path}"
            log_debug(f"POST {url} path={path} body_keys={list(body.keys())}")

            response = self._safe_post(url, headers=self.header, data=body, timeout=6)
            if not response:
                log_err(f"POST 无响应: {url}")
                return None
            if response.status_code != 200:
                log_err(f"HTTP {response.status_code}: {url}")
                return None

            try:
                resp_json = response.json()
            except Exception as e:
                log_err(f"响应非 JSON: {e}, text={response.text[:200]}")
                return None

            if 'code' in resp_json and resp_json['code'] not in (200, '200'):
                log_warn(f"业务码 {resp_json.get('code')}: msg={resp_json.get('msg', '')}, path={path}")

            data_section = resp_json.get('data')
            if not data_section:
                log_warn(f"响应缺 data: {json.dumps(resp_json)[:300]}")
                return None

            encrypted_response = data_section.get('response_key', '')
            encrypted_keys = data_section.get('keys', '')

            if not encrypted_response:
                # 部分接口可能直接返回明文 data
                if isinstance(data_section, dict) and ('list' in data_section or 'vodInfo' in data_section):
                    return data_section
                log_warn(f"响应缺 response_key: {json.dumps(data_section)[:200]}")
                return None

            # ===== 解密响应 =====
            resp_key = self.AES_KEY
            resp_iv = self.AES_IV
            if encrypted_keys:
                try:
                    decrypted_keys_json = self.rsa_decrypt(encrypted_keys, self.RSA_PRIVATE_KEY)
                    if decrypted_keys_json:
                        key_info = json.loads(decrypted_keys_json)
                        resp_key = key_info.get('key', resp_key)
                        resp_iv = key_info.get('iv', resp_iv)
                except Exception as e:
                    log_warn(f"RSA 解密 keys 失败，尝试用默认 key: {e}")

            try:
                decrypted_data = self.aes_decrypt(encrypted_response, resp_key, resp_iv)
            except Exception as e:
                log_err(f"AES 解密响应失败: {e}")
                return None

            try:
                return json.loads(decrypted_data)
            except Exception as e:
                log_err(f"响应 JSON 解析失败: {e}, raw={decrypted_data[:200]}")
                return None

        except Exception as e:
            log_err(f"_send_encrypted_request 异常 [{path}]: {e}\n{traceback.format_exc()}")
            return None

    def get_data(self, data, path, use_cache=True):
        try:
            cache_key = f"{path}_{hash(json.dumps(data, sort_keys=True, ensure_ascii=False))}" if use_cache else None
            if use_cache and cache_key and cache_key in self.cache:
                cached_data, ts = self.cache[cache_key]
                if time.time() - ts < self.cache_timeout:
                    return cached_data

            for attempt in range(2):
                tried = 0
                while tried < len(self.hosts):
                    self.host = self.hosts[self.host_index]
                    self.header['Referer'] = self.host
                    result = self._send_encrypted_request(data, path)
                    if result is not None:
                        if use_cache and cache_key:
                            self.cache[cache_key] = (result, time.time())
                        return result
                    # 切换下一个域名
                    self.host_index = (self.host_index + 1) % len(self.hosts)
                    tried += 1
                    time.sleep(0.2)

                if attempt == 0:
                    log_warn("所有域名失败，尝试重认证")
                    try:
                        self.ensure_token()
                    except Exception as ex:
                        log_err(f"重认证异常: {ex}")
                    self.host_index = 0
            return None
        except Exception as e:
            log_err(f"get_data 异常: {e}")
            return None

    # ===================== 加解密 =====================
    def aes_encrypt(self, text, key, iv):
        try:
            cipher = AES.new(key.encode('utf-8'), AES.MODE_CBC, iv.encode('utf-8'))
            return cipher.encrypt(pad(text.encode('utf-8'), AES.block_size)).hex().upper()
        except Exception as e:
            log_err(f"AES 加密失败: {e}")
            return ""

    def aes_decrypt(self, text, key, iv):
        try:
            cipher = AES.new(key.encode('utf-8'), AES.MODE_CBC, iv.encode('utf-8'))
            return unpad(cipher.decrypt(bytes.fromhex(text)), AES.block_size).decode('utf-8')
        except Exception as e:
            log_err(f"AES 解密失败: {e}")
            raise

    def rsa_encrypt(self, text, public_key_str):
        try:
            key = RSA.import_key("-----BEGIN PUBLIC KEY-----\n" + public_key_str + "\n-----END PUBLIC KEY-----")
            return base64.b64encode(PKCS1_v1_5.new(key).encrypt(text.encode('utf-8'))).decode('utf-8')
        except Exception as e:
            log_err(f"RSA 加密失败: {e}")
            return ""

    def rsa_decrypt(self, encrypted_data, private_key_str):
        try:
            rsa_key = RSA.import_key(private_key_str)
            decrypted = PKCS1_v1_5.new(rsa_key).decrypt(base64.b64decode(encrypted_data), None)
            return decrypted.decode('utf-8') if decrypted else ""
        except Exception as e:
            log_err(f"RSA 解密失败: {e}")
            return ""

    def get_md5(self, text):
        return hashlib.md5(text.encode('utf-8')).hexdigest().upper()

    # ===================== 业务 =====================
    def homeContent(self, filter):
        result = {}
        classes = [
            {"type_name": "热门", "type_id": "hot"},
            {"type_name": "电影", "type_id": "1"},
            {"type_name": "电视剧", "type_id": "2"},
            {"type_name": "动漫", "type_id": "4"},
            {"type_name": "综艺", "type_id": "3"},
            {"type_name": "短剧", "type_id": "64"},
            {"type_name": "漫剧", "type_id": "74"},
            {"type_name": "儿童", "type_id": "33"},
        ]
        result['class'] = classes
        filters = {}
        for cate in classes:
            tid = cate['type_id']
            filters[tid] = [
                {"key": "area", "name": "地区", "value": [
                    {"n": "全部", "v": "0"}, {"n": "大陆", "v": "大陆"}, {"n": "香港", "v": "香港"},
                    {"n": "台湾", "v": "台湾"}, {"n": "美国", "v": "美国"}, {"n": "韩国", "v": "韩国"},
                    {"n": "日本", "v": "日本"}, {"n": "英国", "v": "英国"}, {"n": "法国", "v": "法国"},
                    {"n": "泰国", "v": "泰国"}, {"n": "印度", "v": "印度"}, {"n": "其他", "v": "其他"}
                ]},
                {"key": "year", "name": "年份", "value": [
                    {"n": "全部", "v": "0"}, {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"},
                    {"n": "2024", "v": "2024"}, {"n": "2023", "v": "2023"}, {"n": "2022", "v": "2022"},
                    {"n": "2021", "v": "2021"}, {"n": "2020", "v": "2020"}, {"n": "2019", "v": "2019"},
                    {"n": "2018", "v": "2018"}, {"n": "2017", "v": "2017"}, {"n": "2016", "v": "2016"},
                    {"n": "2015", "v": "2015"}, {"n": "2014", "v": "2014"}, {"n": "2013", "v": "2013"},
                    {"n": "2012", "v": "2012"}, {"n": "2011", "v": "2011"}, {"n": "2010", "v": "2010"},
                    {"n": "2009", "v": "2009"}, {"n": "2008", "v": "2008"}, {"n": "2007", "v": "2007"},
                    {"n": "2006", "v": "2006"}, {"n": "2005", "v": "2005"}, {"n": "更早", "v": "2004"}
                ]},
                {"key": "sort", "name": "排序", "value": [
                    {"n": "最新", "v": "d_id"}, {"n": "最热", "v": "d_hits"}, {"n": "推荐", "v": "d_score"}
                ]}
            ]
        result['filters'] = filters
        return result

    def homeVideoContent(self):
        videos = []
        body = {
            "area": "0",
            "year": "0",
            "pageSize": "30",
            "sort": "d_hits",
            "page": "1",
            "tid": "0",
        }
        data = self.get_cached_data("home_video", body, '/App/IndexList/indexList')
        if data and 'list' in data:
            for item in data['list']:
                vod_continu = item.get('vod_continu', 0) or 0
                remarks = '电影' if vod_continu == 0 else f'更新至{vod_continu}集'
                videos.append({
                    "vod_id": f"{item.get('vod_id', '')}/{vod_continu}",
                    "vod_name": item.get('vod_name', ''),
                    "vod_pic": item.get('vod_pic', ''),
                    "vod_remarks": remarks,
                })
        return {'list': videos}

    def categoryContent(self, tid, pg, filter, extend):
        videos = []
        try:
            request_tid = '0' if tid == 'hot' else str(tid)
            request_sort = 'd_hits' if tid == 'hot' else extend.get('sort', 'd_id')
            body = {
                "area": extend.get('area', '0'),
                "year": extend.get('year', '0'),
                "pageSize": "30",
                "sort": request_sort,
                "page": str(pg),
                "tid": request_tid,
            }
            cache_key = f"category_{tid}_{pg}_{hash(json.dumps(body, sort_keys=True, ensure_ascii=False))}"
            data = self.get_cached_data(cache_key, body, '/App/IndexList/indexList')
            if data and 'list' in data:
                for item in data['list']:
                    vod_continu = item.get('vod_continu', 0) or 0
                    remarks = '电影' if vod_continu == 0 else f'更新至{vod_continu}集'
                    videos.append({
                        "vod_id": f"{item.get('vod_id', '')}/{vod_continu}",
                        "vod_name": item.get('vod_name', ''),
                        "vod_pic": item.get('vod_pic', ''),
                        "vod_remarks": remarks,
                    })
        except Exception as e:
            log_err(f"categoryContent 异常: {e}")
        return {'list': videos, 'page': int(pg), 'pagecount': 9999, 'limit': 30, 'total': 999999}

    def detailContent(self, ids):
        try:
            vod_id = ids[0].split('/')[0]
            t = str(int(time.time()))
            body1 = {"token_id": self.token_id, "vod_id": vod_id, "mobile_time": t, "token": self.token}
            qdata = self.get_data(body1, '/App/IndexPlay/playInfo')
            body2 = {"vurl_cloud_id": "2", "vod_d_id": vod_id}
            jdata = self.get_data(body2, '/App/Resource/Vurl/show')
            if not qdata or 'vodInfo' not in qdata:
                log_warn(f"detailContent 无 vodInfo: vod_id={vod_id}")
                return {'list': []}
            vod = qdata['vodInfo']
            video_detail = {
                "vod_id": vod_id,
                "vod_name": vod.get('vod_name', ''),
                "vod_pic": vod.get('vod_pic', ''),
                "vod_year": vod.get('vod_year', ''),
                "vod_area": vod.get('vod_area', ''),
                "vod_actor": vod.get('vod_actor', ''),
                "vod_director": vod.get('vod_director', ''),
                "vod_content": (vod.get('vod_use_content') or '').strip(),
                "vod_play_from": "天龙瓜子",
            }
            play_list = []
            if jdata and 'list' in jdata:
                for index, item in enumerate(jdata['list']):
                    if 'play' in item:
                        n, p = [], []
                        for key, value in item['play'].items():
                            if 'param' in value and value['param']:
                                n.append(key)
                                p.append(value['param'])
                        if p:
                            play_name = str(index + 1) if len(jdata['list']) != 1 else vod.get('vod_name', '')
                            play_url = f"{p[-1]}||{n[-1]}"
                            play_list.append(f"{play_name}${play_url}")
            video_detail["vod_play_url"] = "#".join(play_list)
            return {'list': [video_detail]}
        except Exception as e:
            log_err(f"detailContent 异常: {e}")
            return {'list': []}

    def searchContent(self, key, quick, pg=1):
        videos = []
        try:
            body = {"keywords": key, "order_val": "1", "page": str(pg)}
            data = self.get_data(body, '/App/Index/findMoreVod', use_cache=False)
            if data and 'list' in data:
                for item in data['list']:
                    vod_continu = item.get('vod_continu', 0) or 0
                    remarks = '电影' if vod_continu == 0 else f'更新至{vod_continu}集'
                    videos.append({
                        "vod_id": f"{item.get('vod_id', '')}/{vod_continu}",
                        "vod_name": item.get('vod_name', ''),
                        "vod_pic": item.get('vod_pic', ''),
                        "vod_remarks": remarks,
                    })
        except Exception as e:
            log_err(f"searchContent 异常: {e}")
        return {'list': videos, 'page': int(pg), 'pagecount': 9999, 'limit': 30, 'total': 999999}

    def playerContent(self, flag, id, vipFlags):
        try:
            parts = id.split('||')
            if len(parts) < 2:
                return {"parse": 0, "playUrl": "", "url": ""}
            param_str = parts[0]
            resolutions = parts[1].split('@') if len(parts) > 1 else []
            params = {}
            for pair in param_str.split('&'):
                if '=' in pair:
                    k, v = pair.split('=', 1)
                    params[k] = v
            if resolutions:
                params['resolution'] = resolutions[0]
                data = self.get_data(params, '/App/Resource/VurlDetail/showOne', use_cache=False)
                if data and 'url' in data:
                    return {
                        "parse": 0,
                        "playUrl": "",
                        "url": data['url'],
                        "header": json.dumps({
                            "User-Agent": self.media_ua,
                            "Referer": self.media_referer,
                        }),
                        'danmaku': 'http://127.0.0.1:9978/proxy?do=diydanmu',
                    }
            return {"parse": 0, "playUrl": "", "url": ""}
        except Exception as e:
            log_err(f"playerContent 异常: {e}")
            return {"parse": 0, "playUrl": "", "url": ""}

    def isVideoFormat(self, url):
        fmts = ['.m3u8', '.mp4', '.avi', '.mkv', '.flv', '.ts']
        return any(url.lower().endswith(f) for f in fmts)

    def manualVideoCheck(self):
        pass

    def localProxy(self, params):
        return None

    def get_cached_data(self, cache_key, data, path):
        current_time = time.time()
        if cache_key in self.cache:
            cached_data, ts = self.cache[cache_key]
            if current_time - ts < self.cache_timeout:
                return cached_data
        result = self.get_data(data, path)
        if result:
            self.cache[cache_key] = (result, current_time)
        return result

if __name__ == '__main__':
    pass
