# -*- coding: utf-8 -*-
# 枝枝影视 zzoc.cc
# 兼容 FongMi/TV 与 WebHomeTV/PeekPro 的 Python Spider

import sys
import re
import json
import base64
import time
from html import unescape
from urllib.parse import quote, unquote, urljoin

try:
    from concurrent.futures import ThreadPoolExecutor, as_completed
except Exception:
    ThreadPoolExecutor = None
    as_completed = None

try:
    import requests as rq
except Exception:
    rq = None

sys.path.append('..')

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    import requests as rq

    class BaseSpider:
        def fetch(self, url, headers=None, **kw):
            kw.pop('timeout', None)
            r = rq.get(url, headers=headers, timeout=30, **kw)
            r.encoding = 'utf-8'
            return r


class Spider(BaseSpider):

    def getName(self):
        return '枝枝影视'

    def init(self, extend=''):
        self.host = 'https://zzoc.cc'
        if isinstance(extend, str) and extend.startswith('http'):
            self.host = extend.rstrip('/')
        self._home_cache = []
        self._home_cache_time = 0
        self.header = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36',
            'Referer': self.host + '/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }

    # ---------- 基础工具 ----------
    def _txt(self, url, referer=None, timeout=30):
        headers = dict(self.header)
        if referer:
            headers['Referer'] = referer
        try:
            rsp = self.fetch(url, headers=headers, timeout=timeout)
            try:
                rsp.encoding = 'utf-8'
            except Exception:
                pass
            return rsp.text
        except Exception:
            return ''

    def _url(self, path):
        return urljoin(self.host + '/', path)

    def _proxy_url(self, media_url, referer=''):
        if not hasattr(self, 'getProxyUrl'):
            return media_url
        try:
            base = self.getProxyUrl()
            return base + '&url=' + quote(media_url, safe='') + '&referer=' + quote(referer or self.host + '/', safe='')
        except Exception:
            return media_url

    def _clean(self, text):
        if not text:
            return ''
        text = re.sub(r'(?is)<script.*?</script>|<style.*?</style>', '', text)
        text = re.sub(r'(?is)<br\s*/?>', ' ', text)
        text = re.sub(r'(?is)<.*?>', '', text)
        text = unescape(text)
        text = text.replace('\xa0', ' ')
        return re.sub(r'\s+', ' ', text).strip()

    def _match(self, pattern, text, default='', flags=re.S):
        m = re.search(pattern, text, flags)
        return self._clean(m.group(1)) if m else default

    def _abs_pic(self, pic):
        if not pic:
            return ''
        if pic.startswith('//'):
            return 'https:' + pic
        return self._url(pic)

    def _parse_cards(self, html):
        if not html:
            return []
        videos = []
        parts = html.split('<div class="myui-vodbox-content">')
        for part in parts[1:]:
            m = re.search(r'href=["\'](/voddetail/(\d+)\.html)["\']', part)
            if not m:
                continue
            vod_id = m.group(2)
            name = self._match(r'alt=["\']([^"\']+)["\']', part)
            if not name:
                name = self._match(r'<div class=["\']title["\']>(.*?)</div>', part)
            pic = self._match(r'<img[^>]+src=["\']([^"\']+)["\']', part)
            if 'load.gif' in pic:
                pic = self._match(r'<!--\s*<img\s+src=["\']([^"\']+)["\']', part)
            remarks = self._match(r'<div class=["\']tag[^"\']*["\']>(.*?)</div>', part)
            if not remarks:
                remarks = self._match(r'<div class=["\']score["\']>(.*?)</div>', part)
            videos.append({
                'vod_id': vod_id,
                'vod_name': name,
                'vod_pic': self._abs_pic(pic),
                'vod_remarks': remarks,
            })
        return videos

    def _pagecount(self, html, current='1'):
        if not html:
            return int(current) if str(current).isdigit() else 1
        nums = re.findall(r'/vodshow/\d+-[^"\']*?(\d+)---\.html', html)
        nums += re.findall(r'/vodsearch/[^"\']*?----------(\d+)---\.html', html)
        nums = [int(x) for x in nums if str(x).isdigit()]
        if nums:
            return max(nums)
        try:
            return int(current) + 1
        except Exception:
            return 1

    def _resolve_m3u8_child(self, m3u8_url, referer=''):
        """Exo 对部分主 m3u8 的相对跳转兼容差，优先解析到子 m3u8。"""
        try:
            text = self._txt(m3u8_url, referer=referer or self.host + '/', timeout=20)
            if not text or '#EXTM3U' not in text:
                return m3u8_url
            lines = [x.strip() for x in text.splitlines() if x.strip()]
            for i, line in enumerate(lines):
                if line.startswith('#EXT-X-STREAM-INF'):
                    for nxt in lines[i + 1:]:
                        if nxt and not nxt.startswith('#'):
                            return urljoin(m3u8_url, nxt)
            return m3u8_url
        except Exception:
            return m3u8_url

    # ---------- 首页 ----------
    def homeContent(self, filter):
        classes = [
            {'type_id': '1', 'type_name': '电影'},
            {'type_id': '2', 'type_name': '电视剧'},
            {'type_id': '3', 'type_name': '综艺'},
            {'type_id': '4', 'type_name': '动漫'},
        ]
        result = {'class': classes}
        if filter:
            result['filters'] = {
                '1': self._filters(),
                '2': self._filters(),
                '3': self._filters(),
                '4': self._filters(),
            }
        return result

    def _filters(self):
        return [
            {
                'key': 'area',
                'name': '地区',
                'value': [
                    {'n': '全部', 'v': ''},
                    {'n': '大陆', 'v': '大陆'},
                    {'n': '香港', 'v': '香港'},
                    {'n': '台湾', 'v': '台湾'},
                    {'n': '美国', 'v': '美国'},
                    {'n': '日本', 'v': '日本'},
                    {'n': '韩国', 'v': '韩国'},
                ],
            },
            {
                'key': 'year',
                'name': '年份',
                'value': [
                    {'n': '全部', 'v': ''},
                    {'n': '2026', 'v': '2026'},
                    {'n': '2025', 'v': '2025'},
                    {'n': '2024', 'v': '2024'},
                    {'n': '2023', 'v': '2023'},
                    {'n': '2022', 'v': '2022'},
                    {'n': '2021', 'v': '2021'},
                    {'n': '2020', 'v': '2020'},
                ],
            },
        ]

    def homeVideoContent(self):
        # 首页原始页面很大，直接抓首页容易慢和超时。
        # 改为从多个分类第一页并发取内容，凑够 50+ 个精选，并做短缓存。
        now = int(time.time())
        if self._home_cache and now - self._home_cache_time < 300:
            return {'list': self._home_cache[:72]}

        tids = ['1', '2', '3', '4']
        urls = [f'{self.host}/vodshow/{tid}-----------.html' for tid in tids]
        videos = []
        seen = set()

        def load(url):
            html = self._txt(url, timeout=12)
            return self._parse_cards(html)

        try:
            if ThreadPoolExecutor and as_completed:
                pool = ThreadPoolExecutor(max_workers=4)
                futures = [pool.submit(load, u) for u in urls]
                try:
                    for fu in as_completed(futures, timeout=18):
                        for v in fu.result() or []:
                            vid = v.get('vod_id')
                            if vid and vid not in seen:
                                seen.add(vid)
                                videos.append(v)
                            if len(videos) >= 72:
                                break
                        if len(videos) >= 72:
                            break
                finally:
                    try:
                        pool.shutdown(wait=False)
                    except Exception:
                        pass
            else:
                for u in urls:
                    for v in load(u):
                        vid = v.get('vod_id')
                        if vid and vid not in seen:
                            seen.add(vid)
                            videos.append(v)
                        if len(videos) >= 72:
                            break
                    if len(videos) >= 72:
                        break
        except Exception:
            pass

        # 如果分类页偶发失败，再用首页兜底补一点
        if len(videos) < 50:
            html = self._txt(self.host + '/', timeout=15)
            for v in self._parse_cards(html):
                vid = v.get('vod_id')
                if vid and vid not in seen:
                    seen.add(vid)
                    videos.append(v)
                if len(videos) >= 72:
                    break

        self._home_cache = videos[:72]
        self._home_cache_time = now
        return {'list': self._home_cache}

    # ---------- 分类 ----------
    def categoryContent(self, tid, pg, filter, extend):
        pg = str(pg or '1')
        area = ''
        year = ''
        if isinstance(extend, dict):
            area = extend.get('area', '') or ''
            year = extend.get('year', '') or ''

        area_enc = quote(area)
        year_enc = quote(year)
        if area or year:
            url = f'{self.host}/vodshow/{tid}-{area_enc}-------{pg}---{year_enc}.html'
        else:
            url = f'{self.host}/vodshow/{tid}--------{pg}---.html' if pg != '1' else f'{self.host}/vodshow/{tid}-----------.html'

        html = self._txt(url)
        videos = self._parse_cards(html)
        return {
            'list': videos,
            'page': pg,
            'pagecount': self._pagecount(html, pg),
            'limit': len(videos) or 20,
            'total': 999999,
        }

    # ---------- 详情 ----------
    def detailContent(self, ids):
        if isinstance(ids, str):
            ids = [ids]
        vod_id = ids[0]
        url = f'{self.host}/voddetail/{vod_id}.html'
        html = self._txt(url)
        if not html:
            return {'list': []}

        name = self._match(r'<meta property=["\']og:title["\'] content=["\'](.*?)-高清', html)
        if not name:
            name = self._match(r'<title>(.*?)-', html)
        pic = self._match(r'<meta property=["\']og:image["\'] content=["\'](.*?)["\']', html)
        content = self._match(r'<meta property=["\']og:description["\'] content=["\'](.*?)["\']', html)
        if '剧情介绍：' in content:
            content = content.split('剧情介绍：', 1)[-1]

        actor = self._match(r'主演[:：]\s*</?[^>]*>(.*?)</div>', html)
        director = self._match(r'导演[:：]\s*</?[^>]*>(.*?)</div>', html)
        year = self._match(r'<div class=["\']right["\']>\s*(\d{4})\s*</div>', html)
        area = self._match(r'地区[:：]\s*(.*?)</', html)
        remarks = self._match(r'<div class=["\']tag[^"\']*["\']>(.*?)</div>', html)

        play_from = []
        play_url = []
        tabs = re.findall(
            r'<li[^>]*class=["\'][^"\']*player_name[^"\']*["\'][^>]*>.*?href=["\']#playlist(\d+)["\'][^>]*>(.*?)</a>',
            html,
            re.S
        )
        for pid, flag_html in tabs:
            flag = self._clean(flag_html) or f'线路{pid}'
            block = self._match_block(rf'<div id=["\']playlist{pid}["\'][^>]*>', html)
            eps = []
            for href, title in re.findall(r'<a[^>]+href=["\']([^"\']*vodplay/[^"\']+)["\'][^>]*>(.*?)</a>', block, re.S):
                ep_name = self._clean(title) or '播放'
                eps.append(f'{ep_name}${self._url(href)}')
            if eps:
                play_from.append(flag)
                play_url.append('#'.join(eps))

        vod = {
            'vod_id': vod_id,
            'vod_name': name,
            'vod_pic': self._abs_pic(pic),
            'type_name': '',
            'vod_year': year,
            'vod_area': area,
            'vod_remarks': remarks,
            'vod_actor': actor,
            'vod_director': director,
            'vod_content': content,
            'vod_play_from': '$$$'.join(play_from),
            'vod_play_url': '$$$'.join(play_url),
        }
        return {'list': [vod]}

    def _match_block(self, start_pattern, text):
        m = re.search(start_pattern, text, re.S)
        if not m:
            return ''
        start = m.start()
        next_m = re.search(r'<div id=["\']playlist\d+["\']', text[m.end():], re.S)
        if next_m:
            return text[start:m.end() + next_m.start()]
        end = text.find('</div>     </div> </div>', m.end())
        if end != -1:
            return text[start:end]
        return text[start:start + 12000]

    # ---------- 搜索 ----------
    def searchContent(self, key, quick, pg='1'):
        pg = str(pg or '1')
        wd = quote(key)
        if pg == '1':
            url = f'{self.host}/vodsearch/{wd}-------------.html'
        else:
            url = f'{self.host}/vodsearch/{wd}----------{pg}---.html'
        html = self._txt(url)
        return {
            'list': self._parse_cards(html),
            'page': pg,
            'pagecount': self._pagecount(html, pg),
            'limit': 20,
            'total': 999999,
        }

    # ---------- 播放 ----------
    def playerContent(self, flag, id, vipFlags):
        url = id
        if not str(url).startswith('http'):
            url = self._url(url)

        # 如果已经是直链，直接返回
        if re.search(r'\.(m3u8|mp4|flv|mkv|avi)(\?|$)', url, re.I):
            return {'parse': 0, 'playUrl': '', 'url': url, 'header': self.header}

        html = self._txt(url, referer=self.host + '/', timeout=30)
        if not html:
            # 网络超时或失败时，让壳子尝试解析
            return {'parse': 1, 'playUrl': '', 'url': url}

        real = ''
        jx_from = ''

        # 1. 从 var player_aaaa = {...} 中提取 JSON（最常用）
        m = re.search(r'var\s+player_[a-zA-Z0-9_]+\s*=\s*(\{.*?\})\s*</script>', html, re.S)
        if m:
            try:
                data = json.loads(m.group(1))
                real = data.get('url', '') or ''
                jx_from = data.get('from', '') or ''
                encrypt = data.get('encrypt', 0)
                if encrypt == 1 and real:
                    try:
                        real = base64.b64decode(real).decode('utf-8')
                    except Exception:
                        pass
                elif encrypt == 2 and real:
                    # 某些站点使用自定义编码，尝试 base64 兜底
                    try:
                        real = base64.b64decode(real).decode('utf-8')
                    except Exception:
                        pass
            except Exception:
                # JSON 解析失败时，直接正则提取 url 字段
                real = self._match(r'"url"\s*:\s*"([^"]+)"', m.group(1))
                jx_from = self._match(r'"from"\s*:\s*"([^"]+)"', m.group(1))

        # 2. 如果 player_aaaa 没找到，尝试 iframe
        if not real:
            iframe = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.S)
            if iframe:
                iframe_url = iframe.group(1)
                if not iframe_url.startswith('http'):
                    iframe_url = self._url(iframe_url)
                iframe_html = self._txt(iframe_url, referer=url, timeout=30)
                if iframe_html:
                    real = self._match(r'"url"\s*:\s*"([^"]+)"', iframe_html)
                    if not real:
                        real = self._match(r'src=["\']([^"\']+\.(?:m3u8|mp4|flv))["\']', iframe_html)

        # 3. 如果还没找到，从页面 script 中全局匹配 m3u8/mp4 URL
        if not real:
            for pat in [
                r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']',
                r'["\'](https?://[^"\']+\.mp4[^"\']*)["\']',
                r'["\'](https?://[^"\']+index\.m3u8[^"\']*)["\']',
            ]:
                m2 = re.search(pat, html, re.I)
                if m2:
                    real = m2.group(1)
                    break

        if real:
            real = real.replace('\\/', '/')
            if '.m3u8' in real.lower():
                real = self._resolve_m3u8_child(real, referer=url)
            # 某些 CDN 需要播放页 URL 作为 referer
            play_header = {
                'User-Agent': self.header['User-Agent'],
                'Referer': url,
            }
            trouble = ['YZ', 'FF', 'IQ', 'DB', 'MT', 'WW']
            out_url = real
            if '.m3u8' in real.lower() and any(x in str(flag).upper() for x in trouble):
                out_url = self._proxy_url(real, url)
            result = {
                'parse': 0,
                'playUrl': '',
                'url': out_url,
                'header': play_header,
                'format': 'application/x-mpegURL',
                'contentType': 'application/x-mpegURL',
            }
            if jx_from:
                result['jxFrom'] = jx_from
            return result

        # 没取到直链时交给壳子解析
        return {'parse': 1, 'playUrl': '', 'url': url}

    # ---------- 可选 ----------
    def isVideoFormat(self, url):
        return bool(re.search(r'\.(m3u8|mp4|flv|mkv|avi)(\?|$)', url or '', re.I))

    def manualVideoCheck(self):
        return True

    def localProxy(self, param):
        try:
            raw_url = param.get('url') or param.get('u') or ''
            referer = param.get('referer') or param.get('ref') or self.host + '/'
            media_url = unquote(raw_url)
            referer = unquote(referer)
            if not media_url:
                return [404, 'text/plain', b'']

            headers = {
                'User-Agent': self.header['User-Agent'],
                'Referer': referer,
            }

            if rq:
                r = rq.get(media_url, headers=headers, timeout=30, verify=False)
                content = r.content
                ctype = r.headers.get('content-type') or ''
            else:
                r = self.fetch(media_url, headers=headers, timeout=30)
                content = r.content if hasattr(r, 'content') else r.text.encode('utf-8')
                ctype = ''

            # m3u8 内容：统一改成绝对地址，并继续走本地代理，解决相对路径、证书、Referer 问题
            text = ''
            try:
                text = content.decode('utf-8')
            except Exception:
                text = ''
            if '#EXTM3U' in text:
                out = []
                for line in text.splitlines():
                    s = line.strip()
                    if not s or s.startswith('#'):
                        out.append(line)
                    else:
                        abs_url = urljoin(media_url, s)
                        out.append(self._proxy_url(abs_url, referer))
                data = '\n'.join(out).encode('utf-8')
                return [200, 'application/x-mpegURL', data]

            return [200, ctype or 'application/octet-stream', content]
        except Exception:
            return [500, 'text/plain', b'proxy error']

    def destroy(self):
        pass

    def close(self):
        self.destroy()
