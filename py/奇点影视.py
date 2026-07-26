# -*- coding: utf-8 -*-
# 奇点影视 qdys2.cc / qdys1.cc
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
        return '奇点影视'

    def init(self, extend=''):
        self.host = 'https://www.qdys2.cc'
        self.backup_host = 'https://www.qdys1.cc'
        if isinstance(extend, str) and extend.startswith('http'):
            self.host = extend.rstrip('/')
        self._home_cache = []
        self._home_cache_time = 0
        self.header = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36',
            'Referer': self.host + '/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }

    # ---------- 基础工具 ----------
    def _clean(self, text):
        if not text:
            return ''
        text = re.sub(r'(?is)<script.*?</script>|<style.*?</style>', '', text)
        text = re.sub(r'(?is)<br\s*/?>', ' ', text)
        text = re.sub(r'(?is)<.*?>', '', text)
        text = unescape(text).replace('\xa0', ' ')
        return re.sub(r'\s+', ' ', text).strip()

    def _match(self, pattern, text, default='', flags=re.S):
        m = re.search(pattern, text or '', flags)
        return self._clean(m.group(1)) if m else default

    def _url(self, path, host=None):
        host = host or self.host
        if not path:
            return ''
        path = path.strip()
        if path.startswith('//'):
            return 'https:' + path
        if path.startswith('http'):
            return path
        return urljoin(host + '/', path)

    def _headers(self, referer=None):
        h = dict(self.header)
        h['Referer'] = referer or (self.host + '/')
        return h

    def _swap_host(self, url):
        if not isinstance(url, str):
            return url
        if self.host in url:
            return url.replace(self.host, self.backup_host)
        if self.backup_host in url:
            return url.replace(self.backup_host, self.host)
        return url

    def _txt(self, url, referer=None, timeout=30):
        url = self._url(url)
        for u in (url, self._swap_host(url)):
            try:
                headers = self._headers(referer or u)
                rsp = self.fetch(u, headers=headers, timeout=timeout)
                try:
                    rsp.encoding = 'utf-8'
                except Exception:
                    pass
                text = rsp.text or ''
                # qdys1/2 偶尔有广告页或短错误页，短内容就试备用域名。
                if len(text) > 2000 and '页面不存在' not in text and 'Cloudflare' not in text:
                    if self.backup_host in u:
                        text = text.replace(self.backup_host, self.host)
                    return text
            except Exception:
                pass
        return ''

    def _json_player(self, html):
        if not html:
            return {}
        m = re.search(r'var\s+player_aaaa\s*=\s*(\{.*?\})\s*</script>', html, re.S)
        if not m:
            m = re.search(r'player_aaaa\s*=\s*(\{.*?\});', html, re.S)
        if not m:
            return {}
        try:
            return json.loads(m.group(1))
        except Exception:
            try:
                return json.loads(m.group(1).replace('\\/', '/'))
            except Exception:
                return {}

    def _decode_play_url(self, data):
        url = data.get('url') or ''
        enc = str(data.get('encrypt', '0'))
        try:
            if enc == '1':
                url = unquote(url)
            elif enc == '2':
                url = unquote(base64.b64decode(url).decode('utf-8'))
        except Exception:
            pass
        return (url or '').replace('\\/', '/')

    def _is_direct_media(self, url):
        url = (url or '').lower()
        if not url:
            return False
        if '.m3u8' in url or '.mp4' in url or '.flv' in url:
            return True
        return False

    def _is_external_sniff_line(self, source_name, data, url):
        text = '{} {} {}'.format(source_name or '', data.get('from') or '', url or '').lower()
        external_keys = [
            'tx', 'qq', 'v.qq.com', 'yk', 'youku', 'v.youku.com',
            'qy', 'qiyi', 'iqiyi', 'www.iqiyi.com', 'mgtv', 'bilibili',
        ]
        return any(k in text for k in external_keys) and not self._is_direct_media(url)

    def _probe_source_url(self, vid, sid, nid):
        path = '/play/{}-{}-{}.html'.format(vid, sid, nid)
        play_url = self.host + path
        html = self._txt(play_url, referer=self.host + '/', timeout=15)
        data = self._json_player(html)
        url = self._decode_play_url(data)
        return data, url

    def _resolve_sniff_to_media(self, url):
        if not url or self._is_direct_media(url):
            return url
        lower = url.lower()
        if not any(k in lower for k in ('v.youku.com', 'youku', 'iqiyi.com', 'qiyi.com', 'v.qq.com', 'mgtv.com', 'bilibili.com')):
            return ''
        try:
            page_url = 'https://svip.qlplayer.cyou/?url=' + quote(url, safe='')
            page_headers = {
                'User-Agent': self.header['User-Agent'],
                'Referer': self.host + '/',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9',
            }
            rsp = self.fetch(page_url, headers=page_headers, timeout=15)
            try:
                rsp.encoding = 'utf-8'
            except Exception:
                pass
            html = rsp.text or ''
            token = ''
            for pattern in (
                r'apiToken\s*:\s*["\']([^"\']+)["\']',
                r'["\']apiToken["\']\s*:\s*["\']([^"\']+)["\']',
                r'apiToken\s*=\s*["\']([^"\']+)["\']',
            ):
                m = re.search(pattern, html)
                if m:
                    token = m.group(1)
                    break
            if not token:
                return ''

            api = 'https://svip.qlplayer.cyou/api/resolve.php?token=' + quote(token, safe='')
            api_headers = {
                'User-Agent': self.header['User-Agent'],
                'Referer': page_url,
                'Origin': 'https://svip.qlplayer.cyou',
                'Accept': '*/*',
                'X-Requested-With': 'mark.via',
            }
            res = self.fetch(api, headers=api_headers, timeout=15)
            try:
                res.encoding = 'utf-8'
            except Exception:
                pass
            data = json.loads(res.text or '{}')
            media = (data.get('url') or '').replace('\\/', '/')
            if media and self._is_direct_media(media):
                if '.m3u8' in media:
                    media = self._resolve_m3u8_child(media, referer=page_url)
                return media
        except Exception:
            pass
        return ''

    def _resolve_m3u8_child(self, m3u8_url, referer=''):
        try:
            text = self._txt(m3u8_url, referer=referer or self.host + '/', timeout=15)
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
            {'type_id': '7', 'type_name': '纪录片'},
            {'type_id': '39', 'type_name': '短剧'},
        ]
        return {'class': classes}

    def homeVideoContent(self):
        now = int(time.time())
        if self._home_cache and now - self._home_cache_time < 300:
            return {'list': self._home_cache}

        urls = [self.host + '/list/{}.html'.format(t) for t in ('1', '2', '3', '4', '7', '39')]
        videos, seen = [], set()

        def load(url):
            return self._parse_cards(self._txt(url, timeout=12))

        try:
            if ThreadPoolExecutor and as_completed:
                pool = ThreadPoolExecutor(max_workers=6)
                futures = [pool.submit(load, u) for u in urls]
                try:
                    for fu in as_completed(futures, timeout=20):
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
        except Exception:
            pass

        if not videos:
            videos = self._parse_cards(self._txt(self.host + '/', timeout=20))
        self._home_cache = videos[:72]
        self._home_cache_time = now
        return {'list': self._home_cache}

    # ---------- 列表解析 ----------
    def _parse_cards(self, html):
        if not html:
            return []
        videos, seen = [], set()

        # 优先解析标准卡片，能拿到封面和备注。
        blocks = re.findall(r'<div[^>]+class=["\'][^"\']*vod-item[^"\']*["\'][^>]*>(.*?)</div>\s*</a>\s*</div>', html, re.S)
        if not blocks:
            blocks = re.findall(r'(<a[^>]+href=["\']/html/\d+\.html["\'][\s\S]{0,900?</a>)', html, re.S)

        for block in blocks:
            m = re.search(r'href=["\']/html/(\d+)\.html["\']', block)
            if not m:
                continue
            vid = m.group(1)
            if vid in seen:
                continue
            seen.add(vid)
            name = self._match(r'alt=["\']([^"\']+)["\']', block)
            if not name:
                name = self._match(r'<div[^>]+class=["\'][^"\']*vod-title[^"\']*["\'][^>]*>(.*?)</div>', block)
            if not name:
                name = self._match(r'<span[^>]+class=["\'][^"\']*hot-name[^"\']*["\'][^>]*>(.*?)</span>', block)
            pic = self._match(r'data-original=["\']([^"\']+)["\']', block)
            if not pic:
                pic = self._match(r'<img[^>]+src=["\']([^"\']+)["\']', block)
            remarks = self._match(r'<div[^>]+class=["\'][^"\']*poster-remarks[^"\']*["\'][^>]*>(.*?)</div>', block)
            if not remarks:
                remarks = self._match(r'<span[^>]+class=["\'][^"\']*pic-text[^"\']*["\'][^>]*>(.*?)</span>', block)
            if name and '广告' not in name and '/go/ad/' not in block:
                videos.append({
                    'vod_id': vid,
                    'vod_name': name,
                    'vod_pic': self._url(pic),
                    'vod_remarks': remarks,
                })

        # 兜底：WebFetch 结构或聚合页中可能只有文字链接。
        if not videos:
            for href, text in re.findall(r'<a[^>]+href=["\']/html/(\d+)\.html["\'][^>]*>(.*?)</a>', html, re.S):
                name = self._clean(text)
                if not name or href in seen or len(name) > 60:
                    continue
                seen.add(href)
                videos.append({
                    'vod_id': href,
                    'vod_name': name,
                    'vod_pic': self.host + '/static/upload/localized/placeholder.webp',
                    'vod_remarks': '',
                })
        return videos

    # ---------- 分类 ----------
    def categoryContent(self, tid, pg, filter, extend):
        pg = str(pg or '1')
        tid = str(tid or '1')
        if pg == '1':
            url = self.host + '/list/{}.html'.format(tid)
        else:
            url = self.host + '/list/{}-{}.html'.format(tid, pg)
        html = self._txt(url, timeout=25)
        videos = self._parse_cards(html)
        pagecount = int(pg) + 1 if videos else int(pg)
        return {
            'list': videos,
            'page': int(pg),
            'pagecount': pagecount,
            'limit': len(videos) or 30,
            'total': pagecount * (len(videos) or 30),
        }

    # ---------- 搜索 ----------
    def searchContent(self, key, quick, pg='1'):
        key = key or ''
        # 站点搜索路径是 /search/关键词-------------.html
        url = self.host + '/search/{}-------------.html'.format(quote(key))
        if str(pg or '1') != '1':
            # 常见分页形式，若站点没有分页也会返回第一页或空列表。
            url = self.host + '/search/{}-------------{}---.html'.format(quote(key), pg)
        html = self._txt(url, timeout=25)
        videos = []
        seen = set()

        # 搜索结果标题在 h3 里，页面侧边还有热榜，必须优先只取 h3 结果，避免混入热榜。
        for m in re.finditer(r'<h3[^>]*>\s*<a[^>]+href=["\']/(?:html/(\d+)\.html|play/(\d+)-\d+-\d+\.html)["\'][^>]*>(.*?)</a>\s*</h3>', html, re.S):
            vid = m.group(1) or m.group(2)
            if not vid or vid in seen:
                continue
            block = html[max(0, m.start() - 500):m.end() + 800]
            name = self._clean(m.group(3))
            if not name:
                name = self._match(r'alt=["\']([^"\']+)["\']', block)
            pic = self._match(r'data-original=["\']([^"\']+)["\']', block) or self._match(r'<img[^>]+src=["\']([^"\']+)["\']', block)
            remarks = self._match(r'<span[^>]+class=["\'][^"\']*pic-text[^"\']*["\'][^>]*>(.*?)</span>', block)
            if name and '/go/ad/' not in block:
                seen.add(vid)
                videos.append({
                    'vod_id': vid,
                    'vod_name': name,
                    'vod_pic': self._url(pic),
                    'vod_remarks': remarks,
                })
        if not videos:
            videos = self._parse_cards(html)
        return {'list': videos}

    def searchContentPage(self, key, quick, pg):
        return self.searchContent(key, quick, pg)

    # ---------- 详情 ----------
    def detailContent(self, ids):
        vid = ids[0] if isinstance(ids, list) else ids
        vid = str(vid or '').strip()
        vid = re.sub(r'\D', '', vid)
        detail_url = self.host + '/html/{}.html'.format(vid)
        html = self._txt(detail_url, timeout=25)

        name = self._match(r'<h1[^>]+class=["\'][^"\']*knowledge-title[^"\']*["\'][^>]*>(.*?)</h1>', html)
        if not name:
            name = self._match(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', html)
        pic = self._match(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html)
        if not pic:
            pic = self._match(r'data-original=["\']([^"\']+)["\'][^>]+alt=["\']%s["\']' % re.escape(name), html)

        sub = self._match(r'<div[^>]+class=["\'][^"\']*knowledge-sub[^"\']*["\'][^>]*>(.*?)</div>', html)
        parts = [x.strip() for x in re.split(r'[·/]', sub) if x.strip()]
        type_name = parts[0] if len(parts) > 0 else ''
        year = parts[1] if len(parts) > 1 else ''
        area = parts[2] if len(parts) > 2 else ''
        lang = parts[3] if len(parts) > 3 else ''
        remarks = parts[4] if len(parts) > 4 else ''

        director = self._match(r'<b>\s*导演\s*</b>\s*<span>(.*?)</span>', html)
        actor = self._match(r'<b>\s*主演\s*</b>\s*<span>(.*?)</span>', html)
        content = self._match(r'<h2>\s*%s剧情介绍\s*</h2>\s*<p[^>]*>(.*?)</p>' % re.escape(name), html)
        if not content:
            content = self._match(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']', html)

        # 详情页不含完整选集，进入第一集播放页解析线路和集数。
        first_play = self._match(r'href=["\'](/play/%s-\d+-\d+\.html)["\']' % vid, html)
        if not first_play:
            first_play = '/play/{}-1-1.html'.format(vid)
        play_html = self._txt(self.host + first_play, referer=detail_url, timeout=25)

        sources = []
        # 只从真正的“播放源”按钮读取线路，避免把“正片、1、2、3...”误识别成线路。
        source_links = re.findall(
            r'<a[^>]+class=["\'][^"\']*source-flat[^"\']*["\'][^>]+href=["\'](/play/%s-(\d+)-\d+\.html)["\'][^>]*>(.*?)</a>' % vid,
            play_html,
            re.S
        )
        if not source_links:
            source_links = re.findall(r'<a[^>]+href=["\'](/play/%s-(\d+)-\d+\.html)["\'][^>]*>(.*?)</a>' % vid, play_html, re.S)
        for href, sid, title in source_links:
            title = self._clean(title)
            # 线路名必须像 TX线路、4K高清、线路① 这类；纯数字/正片/集数都不是线路。
            if not title or '第' in title or title in ('正片', 'HD'):
                continue
            if re.fullmatch(r'\d+', title):
                continue
            if not (('线路' in title) or ('高清' in title) or ('4K' in title.upper())):
                continue
            if (sid, title) not in sources:
                sources.append((sid, title))
        # 先按名字粗排；后面探测后再按直连稳定性重排。
        def source_rank(item):
            name = item[1]
            if '4K' in name or '高清' in name:
                return 0
            if '①' in name or '1' in name:
                return 1
            if '②' in name or '2' in name:
                return 2
            if '⑨' in name or '9' in name:
                return 9
            return 5
        sources = sorted(sources, key=source_rank)

        eps = []
        for href, nid_text, title in re.findall(r'<a[^>]+href=["\'](/play/%s-\d+-(\d+)\.html)["\'][^>]*>(.*?)</a>' % vid, play_html, re.S):
            title = self._clean(title)
            if not title:
                continue
            # 播放页选集有的显示“第1集”，有的只显示“1/2/3”，线路按钮则是“YK线路/QY线路”。
            if ('线路' in title) or ('高清' in title) or ('4K' in title.upper()):
                continue
            if not (('第' in title) or re.fullmatch(r'\d+', title) or title in ('正片', 'HD')):
                continue
            nid = int(nid_text)
            if re.fullmatch(r'\d+', title):
                title = '第{}集'.format(title)
            item = (nid, title)
            if item not in eps:
                eps.append(item)
        eps = sorted(eps, key=lambda x: x[0])

        if not sources:
            sources = [('1', '默认')]
        if not eps:
            eps = [(1, '正片')]

        play_from, play_urls = [], []
        for sid, sname in sources:
            play_from.append(sname)
            play_urls.append('#'.join(['{}${}-{}-{}'.format(title, vid, sid, nid) for nid, title in eps]))

        vod = {
            'vod_id': vid,
            'vod_name': name,
            'vod_pic': self._url(pic),
            'type_name': type_name,
            'vod_year': year,
            'vod_area': area,
            'vod_lang': lang,
            'vod_remarks': remarks,
            'vod_actor': actor,
            'vod_director': director,
            'vod_content': content,
            'vod_play_from': '$$$'.join(play_from),
            'vod_play_url': '$$$'.join(play_urls),
        }
        return {'list': [vod]}

    # ---------- 播放 ----------
    def playerContent(self, flag, id, vipFlags):
        play_id = str(id or '').strip()
        if play_id == '__NO_DIRECT__':
            return {
                'parse': 0,
                'playUrl': '',
                'url': '',
                'header': {'User-Agent': self.header['User-Agent'], 'Referer': self.host + '/'},
            }
        if play_id.startswith('/play/'):
            path = play_id
        elif play_id.startswith('play/'):
            path = '/' + play_id
        else:
            path = '/play/{}.html'.format(play_id)
        if not path.endswith('.html'):
            path += '.html'

        play_url = self.host + path
        html = self._txt(play_url, referer=self.host + '/', timeout=25)
        data = self._json_player(html)
        url = self._decode_play_url(data)

        # 部分线路是优酷/爱奇艺/腾讯等外站地址，先按浏览器抓包流程尝试换成真实 m3u8。
        parse = 0
        if url and not self._is_direct_media(url):
            resolved = self._resolve_sniff_to_media(url)
            if resolved:
                url = resolved
            else:
                parse = 1
        if url and '.m3u8' in url:
            url = self._resolve_m3u8_child(url, referer=play_url)

        return {
            'parse': parse,
            'playUrl': '',
            'url': url or play_url,
            'header': {
                'User-Agent': self.header['User-Agent'],
                'Referer': self.host + '/',
            },
            'format': 'application/x-mpegURL' if '.m3u8' in (url or '') else '',
            'contentType': 'application/x-mpegURL' if '.m3u8' in (url or '') else '',
        }

    def localProxy(self, params):
        return [404, 'text/plain', {}, b'not found']
