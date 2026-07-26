# -*- coding: utf-8 -*-
"""
合并插件：仅用于解析外部直播源（M3U/TXT），支持多个来源合并
- 从 ext.lives 或 ext.lives_url 读取源配置（格式与 zbhb.json 的 lives 一致）
- 每个源可独立设置 headers、proxy 等
- 生成的频道列表按来源分组，并添加占位频道，格式与完整版 zb.py 一致
- 日志、缓存、代理机制保留
"""

import re
import sys
import os
import time
import json
import base64
import hashlib
import threading
from urllib.parse import urljoin, urlparse
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
        def liveContent(self, url): return ""
        def localProxy(self, params): return []
        def destroy(self): return ""


# ========================= 外部频道管理器 =========================
class ExternalChannelManager:
    """管理所有从外部源解析出的频道"""
    def __init__(self):
        self.channels = []          # 所有频道列表
        self.id_map = {}            # id -> channel dict
        self.next_id = 1
        self.source_groups = {}     # source -> [group1, group2, ...]
        self.source_order = []      # 来源出现顺序
        self.group_number_map = {}  # (source, group) -> number

    def add_channel(self, name, group, url, headers=None, proxy=False, source='external'):
        headers = headers or {}
        ch = {
            'name': name,
            'group': group,
            'url': url,
            'headers': headers,
            'proxy': proxy,
            'source': source,
            'id': f"ext_{self.next_id}"
        }
        self.next_id += 1
        self.channels.append(ch)
        self.id_map[ch['id']] = ch

        if source not in self.source_groups:
            self.source_groups[source] = []
            self.source_order.append(source)
        if group not in self.source_groups[source]:
            self.source_groups[source].append(group)
        return ch

    def assign_group_numbers(self):
        number = 1
        for source in self.source_order:
            for group in self.source_groups[source]:
                self.group_number_map[(source, group)] = number
                number += 1

    def get_group_number(self, source, group):
        return self.group_number_map.get((source, group), 0)

    def get_channel_by_id(self, ch_id):
        return self.id_map.get(ch_id)


# ========================= 主 Spider 类 =========================
class Spider(BaseSpider):
    CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR, 0o755, True)

    EXTERNAL_CACHE_TTL = 300   # 远程源内容缓存时间

    def __init__(self):
        super().__init__()
        self.log_enabled = False
        self.log_file = '/sdcard/Download/live_plugin.log'
        self.session = None
        self.ext_manager = ExternalChannelManager()
        self._ext_cache = {}
        self._ext_cache_lock = threading.Lock()
        self._parse_names = []   # 记录每个来源的名称

    def _log(self, msg, data=None):
        if not self.log_enabled:
            return
        try:
            line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
            if data is not None:
                line += ' ' + json.dumps(data, ensure_ascii=False, default=str)
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(line + '\n')
        except Exception:
            pass

    def init(self, extend):
        try:
            extend_dict = json.loads(extend) if extend else {}
        except:
            extend_dict = {}

        self.log_enabled = extend_dict.get('log_enabled', False)
        self._log("Spider init", extend_dict)

        # ---- 1. 创建请求会话 ----
        self.session = requests.Session()
        retry = Retry(total=2, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry, pool_connections=5, pool_maxsize=10)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'zh-CN,zh;q=0.9'
        })

        # 如果提供了代理列表，则尝试设置
        proxy_list = extend_dict.get('proxy', [])
        if proxy_list:
            for p in proxy_list:
                test_proxies = {'http': p, 'https': p}
                try:
                    r = requests.get('https://www.google.com', proxies=test_proxies, timeout=2)
                    if r.status_code < 400:
                        self.session.proxies = test_proxies
                        self._log("代理设置成功", {"proxy": p})
                        break
                except Exception:
                    continue
            else:
                self._log("所有代理均不可用，将不使用代理")

        # ---- 2. 获取直播源列表 ----
        lives = []
        if 'lives' in extend_dict and isinstance(extend_dict['lives'], list):
            lives = extend_dict['lives']
            self._log("从 ext.lives 读取到源", {"count": len(lives)})
        elif 'lives_url' in extend_dict:
            url = extend_dict['lives_url']
            try:
                resp = self.session.get(url, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list):
                        lives = data
                    elif isinstance(data, dict) and 'lives' in data:
                        lives = data['lives']
                    self._log("从远程加载 lives", {"url": url, "count": len(lives)})
                else:
                    self._log("远程加载失败", {"url": url, "status": resp.status_code})
            except Exception as e:
                self._log("远程加载异常", {"url": url, "error": repr(e)})

        # 如果仍然没有，则使用一个空列表（用户需通过 ext 提供）
        if not lives:
            self._log("未配置任何直播源，请检查 ext.lives 或 ext.lives_url")
            lives = []

        # ---- 3. 解析每个源 ----
        for idx, item in enumerate(lives):
            self._parse_remote_interface(item, idx)

        # ---- 4. 为频道分配分组编号 ----
        self.ext_manager.assign_group_numbers()

        self._log("初始化完成", {"外部频道数": len(self.ext_manager.channels)})

    # ==================== 源解析函数 ====================
    def _parse_remote_interface(self, item, idx):
        name = item.get('name', f'源{idx+1}')
        url = item.get('url')
        if not url:
            self._log(f"源 {name} 缺少 url，跳过")
            return
        self._parse_names.append(name)

        headers = {}
        if 'header' in item and isinstance(item['header'], dict):
            headers.update(item['header'])
        if 'ua' in item:
            headers['User-Agent'] = item['ua']
        if 'Referer' in item:
            headers['Referer'] = item['Referer']
        # 额外字段全部作为 header 传递
        exclude_keys = {'name', 'url', 'type', 'proxy', 'playerType', 'epg', 'logo', 'ua', 'Referer', 'header'}
        for k, v in item.items():
            if k not in exclude_keys and v is not None:
                headers[k] = str(v)

        proxy = item.get('proxy', 'noproxy').lower() == 'proxy'

        cache_key = hashlib.md5(f"{url}{json.dumps(headers, sort_keys=True)}".encode()).hexdigest()
        content = self._get_cached_ext_content(cache_key)
        if content is None:
            try:
                resp = self._http_get_with_proxy(url, headers, proxy)
                if resp and resp.status_code == 200:
                    resp.encoding = 'utf-8'
                    content = resp.text
                    self._set_cached_ext_content(cache_key, content)
                else:
                    self._log(f"获取源失败 {name}", {"status": resp.status_code if resp else 'no response'})
                    return
            except Exception as e:
                self._log(f"请求异常 {name}", {"error": repr(e)})
                return

        parsed = self._parse_remote_content(content, name, headers, proxy)
        for ch in parsed:
            self.ext_manager.add_channel(
                name=ch['name'],
                group=ch['group'],
                url=ch['url'],
                headers=ch.get('headers', headers.copy()),
                proxy=ch.get('proxy', proxy),
                source=f"source_{idx}"  # 按源索引分组
            )
        self._log(f"源 {name} 解析完成，频道数 {len(parsed)}")

    def _http_get_with_proxy(self, url, headers, use_proxy):
        """根据 use_proxy 决定是否使用代理"""
        if use_proxy and self.session.proxies:
            return self.session.get(url, headers=headers, timeout=30, verify=False)
        else:
            # 临时移除代理
            original_proxies = self.session.proxies
            self.session.proxies = {}
            try:
                resp = self.session.get(url, headers=headers, timeout=30, verify=False)
            finally:
                self.session.proxies = original_proxies
            return resp

    def _get_cached_ext_content(self, key):
        with self._ext_cache_lock:
            entry = self._ext_cache.get(key)
            if entry and time.time() - entry['time'] < Spider.EXTERNAL_CACHE_TTL:
                return entry['content']
        return None

    def _set_cached_ext_content(self, key, content):
        with self._ext_cache_lock:
            self._ext_cache[key] = {'content': content, 'time': time.time()}

    def _parse_remote_content(self, content, source_name, default_headers, default_proxy):
        """解析 M3U 或 TXT 格式的直播列表"""
        channels = []
        if '#EXTM3U' in content:
            lines = content.splitlines()
            current_group = '默认分类'
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if line.startswith('#EXTM3U') or line.startswith('#EXT-X-'):
                    i += 1
                    continue
                if line.startswith('#EXTINF:'):
                    info = line
                    group_match = re.search(r'group-title="([^"]+)"', info)
                    if group_match:
                        current_group = group_match.group(1)
                    name_match = re.search(r',([^,]+)$', info)
                    ch_name = name_match.group(1).strip() if name_match else f"频道_{len(channels)}"
                    i += 1
                    while i < len(lines) and not lines[i].strip():
                        i += 1
                    if i < len(lines):
                        url = lines[i].strip()
                        if url and not url.startswith('#'):
                            channels.append({
                                'name': ch_name,
                                'group': current_group,
                                'url': url,
                                'headers': default_headers.copy(),
                                'proxy': default_proxy
                            })
                    i += 1
                else:
                    if ',' in line and not line.startswith('#'):
                        parts = line.split(',', 1)
                        ch_name = parts[0].strip()
                        url = parts[1].strip()
                        if ch_name and url and not url.startswith('#'):
                            channels.append({
                                'name': ch_name,
                                'group': current_group,
                                'url': url,
                                'headers': default_headers.copy(),
                                'proxy': default_proxy
                            })
                    i += 1
        else:  # TXT 格式
            lines = content.splitlines()
            current_group = '默认分类'
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '#genre#' in line:
                    parts = line.split(',')
                    grp = parts[0].strip()
                    if grp.startswith('#'):
                        grp = grp[1:].strip()
                    if grp:
                        current_group = grp
                    continue
                if ',' in line:
                    parts = line.split(',', 1)
                    ch_name = parts[0].strip()
                    url = parts[1].strip()
                    if ch_name and url and not url.startswith('#'):
                        channels.append({
                            'name': ch_name,
                            'group': current_group,
                            'url': url,
                            'headers': default_headers.copy(),
                            'proxy': default_proxy
                        })
        return channels

    # ==================== 生成播放列表 ====================
    def liveContent(self, url):
        lines = ['#EXTM3U']

        # 占位频道信息
        placeholder_name = "↓↓↓↓↓↓"
        placeholder_url = "http://127.0.0.1:9978/proxy?do=py&fun=placeholder"

        # 按来源分组显示
        source_groups = {}
        for ch in self.ext_manager.channels:
            source_groups.setdefault(ch['source'], []).append(ch)

        for src, ch_list in source_groups.items():
            # 获取来源显示名称
            display_name = self._get_source_display_name(src)
            block_name = f"=={display_name}=="
            lines.append(f'\n{block_name},#genre#')
            # 添加占位频道
            lines.append(f'#EXTINF:-1 tvg-name="{placeholder_name}" group-title="{block_name}",{placeholder_name}')
            lines.append(placeholder_url)

            # 按 group 细分
            group_dict = {}
            for ch in ch_list:
                group_dict.setdefault(ch['group'], []).append(ch)
            for group_name, items in group_dict.items():
                num = self.ext_manager.get_group_number(src, group_name)
                if num > 0:
                    group_title = f"{group_name}|{num}"
                else:
                    group_title = group_name
                lines.append(f'{group_title},#genre#')
                for ch in items:
                    name = ch['name'].replace('"', '\\"').replace(',', '\\,')
                    if ch['headers'] or ch['proxy']:
                        proxy_url = f"http://127.0.0.1:9978/proxy?do=py&fun=external&id={ch['id']}"
                    else:
                        proxy_url = ch['url']
                    lines.append(f'#EXTINF:-1 tvg-id="{ch["id"]}" tvg-name="{name}" group-title="{group_name}",{name}')
                    lines.append(proxy_url)

        return '\n'.join(lines)

    def _get_source_display_name(self, source):
        if source.startswith('source_'):
            try:
                idx = int(source.split('_')[1])
                if idx < len(self._parse_names):
                    return self._parse_names[idx]
            except:
                pass
            return f'源{idx+1}'
        return '外部频道'

    # ==================== 本地代理处理 ====================
    def localProxy(self, params):
        fun = params.get('fun')
        if fun == 'external':
            return self._handle_external(params)
        elif fun == 'ts':
            return self._handle_ts(params)
        elif fun == 'placeholder':
            # 占位频道返回错误提示（与完整版一致）
            return self._error_response("占位频道，请切换到其他频道")
        else:
            return self._error_response("未知请求")

    def _handle_external(self, params):
        ch_id = params.get('id')
        if not ch_id:
            return self._error_response("缺少频道ID")
        ch = self.ext_manager.get_channel_by_id(ch_id)
        if not ch:
            return self._error_response("无效的频道ID")

        if 'ts' in params:
            ts_url = self._b64_decode(params['ts'])
            try:
                resp = self._http_get_with_proxy(ts_url, ch['headers'], ch['proxy'])
                if resp.status_code != 200:
                    return self._error_response(f"TS 请求失败 {resp.status_code}")
                return [200, "video/MP2T", resp.content, {
                    'Content-Type': 'video/MP2T',
                    'Content-Length': str(len(resp.content)),
                    'Cache-Control': 'no-cache'
                }]
            except Exception as e:
                return self._error_response(f"TS 代理异常: {str(e)}")

        url = ch['url']
        headers = ch['headers']
        proxy = ch['proxy']

        try:
            resp = self._http_get_with_proxy(url, headers, proxy)
            if resp.status_code != 200:
                return self._error_response(f"外部频道请求失败 {resp.status_code}")

            content_type = resp.headers.get('Content-Type', '')
            if 'mpegurl' in content_type or 'application/vnd.apple.mpegurl' in content_type or '#EXTM3U' in resp.text[:1000]:
                m3u8_content = self._rewrite_external_m3u8(resp.text, ch_id, url)
                return [200, "application/vnd.apple.mpegurl", m3u8_content]
            else:
                return [200, resp.headers.get('Content-Type', 'application/octet-stream'), resp.content, {
                    'Content-Type': resp.headers.get('Content-Type', 'application/octet-stream'),
                    'Content-Length': str(len(resp.content)),
                    'Cache-Control': 'no-cache'
                }]
        except Exception as e:
            self._log("外部频道请求异常", {"id": ch_id, "error": repr(e)})
            return self._error_response(f"请求异常: {str(e)}")

    def _rewrite_external_m3u8(self, text, ch_id, base_url):
        lines = text.splitlines()
        rewritten = []
        for line in lines:
            if line.startswith('#'):
                rewritten.append(line)
            else:
                ts_url = urljoin(base_url, line.strip())
                encoded_ts = self._b64_encode(ts_url)
                proxy_ts = f"http://127.0.0.1:9978/proxy?do=py&fun=ts&url={encoded_ts}&channel={ch_id}"
                rewritten.append(proxy_ts)
        return '\n'.join(rewritten) + '\n'

    def _handle_ts(self, params):
        b64_url = params.get('url', '')
        if not b64_url:
            return self._error_response("缺少 TS URL")
        try:
            ts_url = self._b64_decode(b64_url)
        except:
            return self._error_response("TS URL 解码失败")

        try:
            # 从参数获取频道ID以使用对应 headers，若无则使用通用
            ch_id = params.get('channel')
            headers = {}
            if ch_id:
                ch = self.ext_manager.get_channel_by_id(ch_id)
                if ch:
                    headers = ch['headers']
            resp = self._http_get_with_proxy(ts_url, headers, True)  # 默认使用代理
            if resp.status_code != 200:
                return self._error_response(f"TS 请求失败 {resp.status_code}")
            return [200, "video/MP2T", resp.content, {
                'Content-Type': 'video/MP2T',
                'Content-Length': str(len(resp.content)),
                'Cache-Control': 'no-cache'
            }]
        except Exception as e:
            return self._error_response(f"TS 代理异常: {str(e)}")

    def _b64_encode(self, s):
        return base64.urlsafe_b64encode(s.encode()).decode().rstrip('=')

    def _b64_decode(self, s):
        padding = 4 - (len(s) % 4)
        if padding != 4:
            s += '=' * padding
        return base64.urlsafe_b64decode(s).decode()

    def _error_response(self, msg):
        error_m3u = (
            "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-MEDIA-SEQUENCE:0\n"
            "#EXT-X-TARGETDURATION:10\n#EXTINF:10.0,\nerror.ts\n"
            f"#EXT-X-ENDLIST\n# {msg}"
        )
        return [500, "application/vnd.apple.mpegurl", error_m3u]

    def getName(self):
        return "直播聚合 (外部源)"

    def destroy(self):
        if self.session:
            self.session.close()
        self._log("Spider destroyed")