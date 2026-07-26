# -*- coding: utf-8 -*-
# 多瑙影院 dnvod.org
# 兼容 FongMi/TV 与 WebHomeTV/PeekPro 的 Python Spider

import sys
import re
import json
import time
from html import unescape
from urllib.parse import urlencode, quote, urljoin

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
        return '多瑙影院'

    def init(self, extend=''):
        self.host = 'https://dnvod.org'
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
        self._type_map = {
            'tv': '电视剧',
            'movie': '电影',
            'show': '综艺',
            'anime': '动漫',
            'doc': '纪录片',
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

    def _json(self, url, referer=None, timeout=20):
        headers = dict(self.header)
        headers['X-Requested-With'] = 'XMLHttpRequest'
        if referer:
            headers['Referer'] = referer
        try:
            rsp = self.fetch(url, headers=headers, timeout=timeout)
            if hasattr(rsp, 'json'):
                return rsp.json()
            return json.loads(rsp.text)
        except Exception:
            return {}

    def _url(self, path):
        if not path:
            return ''
        if path.startswith('//'):
            return 'https:' + path
        return urljoin(self.host + '/', path)

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

    def _split_id(self, vod_id):
        if isinstance(vod_id, list):
            vod_id = vod_id[0]
        vod_id = str(vod_id or '')
        if '$' in vod_id:
            cate, vid = vod_id.split('$', 1)
        else:
            m = re.search(r'/(tv|movie|show|anime|doc)/detail/(\d+)', vod_id)
            if m:
                cate, vid = m.group(1), m.group(2)
            else:
                cate, vid = 'movie', vod_id
        return cate, vid

    def _source_name(self, src_site):
        src_site = (src_site or '').lower()
        table = {
            'xlzy': 'XL',
            'jyzy': 'JY',
            'mdzy': 'MD',
            'hnzy': 'HN',
            'gszy': 'GS',
            'jszy': 'JS',
            'yhzy': 'YH',
        }
        return table.get(src_site, src_site.replace('zy', '').upper() or '默认')

    def _episode_to_api(self, play_path):
        # /play/202642024-ep40 -> 202642024, ep40
        # /play/202642181-m    -> 202642181, m
        play_path = str(play_path or '').split('#')[0].strip('/')
        play_path = play_path.replace('play/', '')
        if '-' in play_path:
            vid, ep = play_path.split('-', 1)
        else:
            vid, ep = play_path, ''
        return vid, ep

    def _normalize_episodes(self, episodes):
        """
        修正 dnvod 选集页常见问题：
        1. 页面经常倒序显示：40、39、38...
        2. 页面只给一部分集数，缺失的集数接口会 404，不能硬补假集。
        3. 有些页面中间会漏几集，只按源站实际存在的链接做正序排序。
        """
        if not episodes:
            return []

        nums = []
        for title, path in episodes:
            m = re.search(r'play/\d+-ep(\d+)', path)
            if m:
                try:
                    nums.append(int(m.group(1)))
                except Exception:
                    pass

        # 电影或只有少量非数字选集时，保持页面原有顺序；如果是数字集数则做正序排序。
        def sort_key(item):
            m = re.search(r'-ep(\d+)', item[1])
            return int(m.group(1)) if m else 999999

        if nums:
            return sorted(episodes, key=sort_key)
        return episodes

    def _play_api_url(self, play_path):
        vid, ep = self._episode_to_api(play_path)
        return self.host + '/vod_plays/{}/{}'.format(vid, ep)

    def _resolve_m3u8_child(self, m3u8_url, referer=''):
        """部分 Exo 对主 m3u8 跳转不稳定，优先解析到子 m3u8。"""
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
            {'type_id': 'movie', 'type_name': '电影'},
            {'type_id': 'tv', 'type_name': '电视剧'},
            {'type_id': 'show', 'type_name': '综艺'},
            {'type_id': 'anime', 'type_name': '动漫'},
            {'type_id': 'doc', 'type_name': '纪录片'},
        ]
        result = {'class': classes}
        if filter:
            result['filters'] = {
                'movie': self._filters('movie'),
                'tv': self._filters('tv'),
                'show': self._filters('show'),
                'anime': self._filters('anime'),
                'doc': self._filters('doc'),
            }
        return result

    def _filters(self, cate):
        common_region = [
            {'n': '全部', 'v': ''},
            {'n': '大陆', 'v': 'cn'},
            {'n': '港台', 'v': 'hk_tw'},
            {'n': '日韩', 'v': 'jp_kr'},
            {'n': '欧美', 'v': 'west'},
            {'n': '东南亚', 'v': 'sea'},
            {'n': '其他', 'v': 'other'},
        ]
        anime_region = [
            {'n': '全部', 'v': ''},
            {'n': '日本', 'v': 'jp'},
            {'n': '大陆', 'v': 'cn'},
            {'n': '欧美', 'v': 'west'},
        ]
        years = [
            {'n': '全部', 'v': ''}, {'n': '2026', 'v': '2026'}, {'n': '2025', 'v': '2025'},
            {'n': '2024', 'v': '2024'}, {'n': '2023', 'v': '2023'}, {'n': '2022', 'v': '2022'},
            {'n': '2021', 'v': '2021'}, {'n': '2020', 'v': '2020'},
            {'n': '2010年代', 'v': 'range__2010_2019'}, {'n': '2000年代', 'v': 'range__2000_2009'},
            {'n': '更早', 'v': 'lt__2000'},
        ]
        movie_genres = [
            ('全部', ''), ('喜剧', 'xi-ju'), ('爱情', 'ai-qing'), ('动作', 'dong-zuo'),
            ('犯罪', 'fan-zui'), ('科幻', 'ke-huan'), ('奇幻', 'qi-huan'), ('冒险', 'mao-xian'),
            ('灾难', 'zai-nan'), ('惊悚', 'jing-song'), ('剧情', 'ju-qing'), ('战争', 'zhan-zheng'),
            ('歌舞', 'ge-wu'), ('经典', 'jing-dian'), ('悬疑', 'xuan-yi'),
        ]
        show_genres = [
            ('全部', ''), ('真人秀', 'zhen-ren-xiu'), ('搞笑', 'gao-xiao'), ('选秀', 'xuan-xiu'),
            ('脱口秀', 'tuo-kou-xiu'), ('音乐', 'yin-le'), ('晚会', 'wan-hui'), ('美食', 'mei-shi'),
            ('访谈', 'fang-tan'),
        ]
        anime_genres = [
            ('全部', ''), ('热血', 're-xue'), ('动作', 'dong-zuo'), ('战争', 'zhan-zheng'),
            ('青春', 'qing-chun'), ('治愈', 'zhi-yu'), ('运动', 'yun-dong'), ('科幻', 'ke-huan'),
            ('魔幻', 'mo-huan'), ('冒险', 'mao-xian'), ('推理', 'tui-li'), ('搞笑', 'gao-xiao'),
            ('校园', 'xiao-yuan'), ('百合', 'bai-he'),
        ]
        filters = []
        if cate in ('movie', 'show', 'anime'):
            genres = movie_genres if cate == 'movie' else show_genres if cate == 'show' else anime_genres
            filters.append({'key': 'genre', 'name': '分类', 'value': [{'n': n, 'v': v} for n, v in genres]})
        filters.append({'key': 'region', 'name': '地区', 'value': anime_region if cate == 'anime' else common_region})
        filters.append({'key': 'year', 'name': '年代', 'value': years})
        return filters

    def homeVideoContent(self):
        now = int(time.time())
        if self._home_cache and now - self._home_cache_time < 300:
            return {'list': self._home_cache[:72]}

        urls = [
            self.host + '/movie/list/',
            self.host + '/tv/list/',
            self.host + '/show/list/',
            self.host + '/anime/list/',
            self.host + '/doc/list/',
        ]
        videos, seen = [], set()

        def load(url):
            return self._parse_cards(self._txt(url, timeout=12))

        try:
            if ThreadPoolExecutor and as_completed:
                pool = ThreadPoolExecutor(max_workers=5)
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
        pattern = re.compile(r'href=["\']/(movie|tv|show|anime|doc)/detail/(\d+)["\']', re.I)
        matches = list(pattern.finditer(html))
        for m in matches:
            cate, vid = m.group(1), m.group(2)
            key = cate + '$' + vid
            if key in seen:
                continue
            seen.add(key)
            pos = m.start()
            window = html[pos:pos + 1800]
            back = html[max(0, pos - 600):pos + 800]
            title = self._match(r'<div[^>]+class=["\'][^"\']*text-left\s+text-truncate\s+text-dark[^"\']*["\'][^>]*>(.*?)</div>', window)
            if not title:
                title = self._match(r'href=["\']/%s/detail/%s["\'][^>]*>(.*?)</a>' % (cate, vid), window)
            pic = self._match(r'<img[^>]+src=["\']([^"\']+)["\']', window)
            if not pic:
                pic = self._match(r'<img[^>]+src=["\']([^"\']+)["\']', back)
            lines = [self._clean(x) for x in re.findall(r'<div[^>]+class=["\'][^"\']*small\s+text-truncate[^"\']*["\'][^>]*>(.*?)</div>', window, re.S)]
            remarks = ''
            for x in lines:
                if x and ('人气' in x or '第' in x or 'HD' in x or '4K' in x or 'TC' in x or '正片' in x):
                    remarks = x
                    break
            if not remarks and lines:
                remarks = lines[0]
            if title and len(title) < 80:
                videos.append({
                    'vod_id': key,
                    'vod_name': title,
                    'vod_pic': self._url(pic),
                    'vod_remarks': remarks,
                })
        return videos

    # ---------- 分类 ----------
    def categoryContent(self, tid, pg, filter, extend):
        tid = tid or 'movie'
        pg = str(pg or '1')
        params = {}
        extend = extend or {}
        for k in ('genre', 'region', 'year'):
            v = extend.get(k) if isinstance(extend, dict) else ''
            if v:
                params[k] = v
        if pg != '1':
            params['page'] = pg
        url = self.host + '/{}/list/'.format(tid)
        if params:
            url += '?' + urlencode(params)
        html = self._txt(url, timeout=25)
        videos = self._parse_cards(html)
        pagecount = int(pg) + 1 if videos else int(pg)
        return {
            'list': videos,
            'page': int(pg),
            'pagecount': pagecount,
            'limit': len(videos) or 48,
            'total': pagecount * (len(videos) or 48),
        }

    # ---------- 搜索 ----------
    def searchContent(self, key, quick, pg='1'):
        params = {'q': key or ''}
        if str(pg or '1') != '1':
            params['page'] = str(pg)
        url = self.host + '/search?' + urlencode(params)
        html = self._txt(url, timeout=25)
        return {'list': self._parse_cards(html)}

    def searchContentPage(self, key, quick, pg):
        return self.searchContent(key, quick, pg)

    # ---------- 详情 ----------
    def detailContent(self, ids):
        cate, vid = self._split_id(ids)
        detail_url = self.host + '/{}/detail/{}'.format(cate, vid)
        html = self._txt(detail_url, timeout=25)

        name = self._match(r'<h1[^>]*class=["\'][^"\']*title[^"\']*["\'][^>]*>(.*?)</h1>', html)
        if not name:
            name = self._match(r'<title>(.*?)在线', html)
        pic = self._match(r'<img[^>]+alt=["\']%s["\'][^>]+src=["\']([^"\']+)["\']' % re.escape(name), html)
        if not pic:
            pic = '/vod-img/{}.jpg'.format(vid)

        type_name = self._match(r'分类：\s*(.*?)</div>', html)
        year = self._match(r'年份：\s*(.*?)</div>', html)
        area = self._match(r'区域：\s*(.*?)</div>', html)
        lang = self._match(r'语言：\s*(.*?)</div>', html)
        director = self._match(r'导演：\s*(.*?)</div>', html)
        actor = self._match(r'主演：</span>(.*?)<br>', html)
        desc = self._match(r'<small[^>]+class=["\']text-secondary["\'][^>]*>(.*?)</small>', html)

        episodes = []
        for href, title in re.findall(r'<a[^>]+class=["\'][^"\']*ep-btn[^"\']*["\'][^>]+href=["\'](/play/[^"\']+)["\'][^>]*>(.*?)</a>', html, re.S):
            title = self._clean(title) or '播放'
            play_path = href.split('#')[0].strip('/')
            if play_path and (title, play_path) not in episodes:
                episodes.append((title, play_path))
        episodes = self._normalize_episodes(episodes)

        play_from = ['多瑙优选']
        play_urls = ['#'.join(['{}${}'.format(n, p) for n, p in episodes])]

        # 用最新一集探测线路，生成 XL/JY/MD 等可切换线路。
        # 不能用第一集，因为源站有些剧前几集接口不存在，会导致线路探测失败。
        if episodes:
            probe_ep = episodes[-1][1]
            api = self._play_api_url(probe_ep)
            data = self._json(api, referer=self.host + '/' + probe_ep, timeout=15)
            lines = data.get('video_plays') or []
            if lines:
                play_from, play_urls = [], []
                for idx, item in enumerate(lines):
                    line_name = self._source_name(item.get('src_site'))
                    if line_name in play_from:
                        line_name = line_name + str(idx + 1)
                    play_from.append(line_name)
                    play_urls.append('#'.join(['{}${}@@{}'.format(n, p, idx) for n, p in episodes]))

        if not play_urls or not play_urls[0]:
            play_from = ['多瑙']
            play_urls = ['暂无播放$']

        vod = {
            'vod_id': cate + '$' + vid,
            'vod_name': name,
            'vod_pic': self._url(pic),
            'type_name': type_name,
            'vod_year': year,
            'vod_area': area,
            'vod_lang': lang,
            'vod_actor': actor,
            'vod_director': director,
            'vod_content': desc,
            'vod_play_from': '$$$'.join(play_from),
            'vod_play_url': '$$$'.join(play_urls),
        }
        return {'list': [vod]}

    # ---------- 播放 ----------
    def playerContent(self, flag, id, vipFlags):
        # id: play/202642024-ep40@@线路序号
        play_id = str(id or '')
        line_idx = None
        if '@@' in play_id:
            play_id, idx = play_id.rsplit('@@', 1)
            try:
                line_idx = int(idx)
            except Exception:
                line_idx = None

        api = self._play_api_url(play_id)
        data = self._json(api, referer=self.host + '/' + play_id, timeout=20)
        plays = data.get('video_plays') or []

        url = ''
        if line_idx is not None and 0 <= line_idx < len(plays):
            url = plays[line_idx].get('play_data') or ''
        if not url and plays:
            # 默认优先 XL/JY/MD，这几类通常对 Exo/MPV 更稳定。
            priority = ['xlzy', 'jyzy', 'mdzy', 'hnzy', 'gszy', 'jszy', 'yhzy']
            for p in priority:
                for item in plays:
                    if (item.get('src_site') or '').lower() == p and item.get('play_data'):
                        url = item.get('play_data')
                        break
                if url:
                    break
            if not url:
                url = plays[0].get('play_data') or ''

        if url and url.startswith('//'):
            url = 'https:' + url
        if '.m3u8' in url:
            url = self._resolve_m3u8_child(url, referer=self.host + '/' + play_id)

        return {
            'parse': 0,
            'playUrl': '',
            'url': url,
            'header': {
                'User-Agent': self.header['User-Agent'],
                'Referer': self.host + '/',
            },
            'format': 'application/x-mpegURL' if '.m3u8' in url else '',
            'contentType': 'application/x-mpegURL' if '.m3u8' in url else '',
        }

    # ---------- 本地代理 ----------
    def localProxy(self, params):
        return [404, 'text/plain', {}, b'not found']
