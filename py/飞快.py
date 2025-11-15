# coding=utf-8
# !/usr/bin/python
import sys
import datetime
from copy import deepcopy
from urllib.parse import quote_plus, unquote, urlparse, urljoin
from lxml import etree

sys.path.append('..')
from base.spider import Spider
import json
import re
import base64


class Spider(Spider):
    def getName(self):
        return "飞快"

    def init(self, extend=""):
        print(f"[飞快] ============{extend}============")
        pass

    def homeContent(self, filter):
        result = {}
        cateManual = {
            "电影": "1",
            "欧美剧": "16",
            "日韩剧": "15",
            "日韩动漫": "27",
            "欧美动漫": "28",
            "短剧": "32"
        }
        classes = []
        for k in cateManual:
            classes.append({'type_name': k, 'type_id': cateManual[k]})
        result['class'] = classes
        if filter:
            result['filters'] = self.get_filters()
        return result

    def get_filters(self):
        filt = deepcopy(self.config.get('filter', {}))
        current_year = datetime.datetime.now().year
        years = [{"n": "全部", "v": ""}] + [{"n": str(y), "v": str(y)} for y in range(current_year, 2009, -1)]
        for tid, arr in filt.items():
            for item in arr:
                key = item.get('key') or item.get('k')
                if key in ('year', '11'):
                    item['value'] = years
        return filt

    def homeVideoContent(self):
        return {'list': []}

    def _parse_html(self, rsp):
        try:
            if hasattr(rsp, 'content'):
                parser = etree.HTMLParser(encoding='utf-8', recover=True, remove_blank_text=True)
                return etree.HTML(rsp.content, parser=parser)
            else:
                parser = etree.HTMLParser(encoding='utf-8', recover=True, remove_blank_text=True)
                return etree.HTML(rsp.text.encode('utf-8', errors='ignore'), parser=parser)
        except Exception:
            return self.html(rsp.text)

    def _build_vodshow_url(self, tid, pg, ext):
        area = (ext.get('area') or ext.get('1') or '').strip()
        cate = (ext.get('class') or ext.get('3') or '').strip()
        year = (ext.get('year') or ext.get('11') or '').strip()
        by = (ext.get('by') or ext.get('2') or '').strip()
        by_map = {'最新': 'time', '最热': 'hits', '评分': 'score'}
        by_val = by_map.get(by, '')
        enc_area = quote_plus(area) if area else ''
        enc_cate = quote_plus(cate) if cate else ''
        pg_str = '' if str(pg) in ('', '1') else str(pg)
        url = f'https://feikuai.tv/vodshow/{tid}-{enc_area}-{by_val}-{enc_cate}-----{pg_str}---{year}.html'
        return url

    def categoryContent(self, tid, pg, filter, extend):
        result = {'list': [], 'page': pg, 'pagecount': 9999, 'limit': 90, 'total': 999999}
        try:
            ext = extend or {}
            url = self._build_vodshow_url(tid, pg, ext)
        except Exception:
            url = f'https://feikuai.tv/vodshow/{tid}-----------.html'
        print(f"[飞快] Category URL: {url}")
        headers = self.header.copy()
        # Prefer a realistic referer like browser does
        tid_str = str(tid)
        if tid_str == '1':
            headers['Referer'] = 'https://feikuai.tv/vodtype/1.html'
        elif tid_str in ('15', '16', '32'):
            headers['Referer'] = 'https://feikuai.tv/vodtype/2.html'
        elif tid_str in ('27', '28'):
            headers['Referer'] = 'https://feikuai.tv/vodtype/4.html'
        else:
            headers['Referer'] = 'https://feikuai.tv/'
        rsp = self.fetch(url, headers=headers)
        if not rsp or not rsp.text:
            return result
        root = self._parse_html(rsp)
        videos = []
        seen = set()
        try:
            # Primary: category pages use poster-style list
            links = root.xpath('//div[contains(@class, "module-items") and contains(@class, "module-poster-items")]//a[contains(@href, "/voddetail/")]')
            # Fallback: direct poster item anchors
            if not links:
                links = root.xpath('//a[contains(@class, "module-poster-item") and contains(@href, "/voddetail/")]')
            # Fallback: card-style list (e.g., search-style cards reused)
            if not links:
                links = root.xpath('//div[contains(@class, "module-card-items")]//a[contains(@href, "/voddetail/")]')
            for a in links:
                try:
                    href = a.xpath('./@href')
                    if not href:
                        continue
                    href = href[0]
                    m = re.search(r'/voddetail/(\d+)\.html', href)
                    if not m:
                        continue
                    sid = m.group(1)
                    if sid in seen:
                        continue
                    seen.add(sid)
                    # Prefer poster-style title on category pages
                    title_nodes = a.xpath('.//div[contains(@class, "module-poster-item-title")]//text()')
                    if not title_nodes:
                        title_nodes = a.xpath('.//div[contains(@class, "module-card-item-title")]/a//text()')
                    if not title_nodes:
                        title_nodes = a.xpath('./@title')
                    if not title_nodes:
                        title_nodes = a.xpath('.//img/@alt')
                    name = title_nodes[0].strip() if title_nodes else ''
                    img = ''
                    img_nodes = a.xpath('.//img[contains(@class, "lazy")]/@data-original')
                    if not img_nodes:
                        img_nodes = a.xpath('.//img[contains(@class, "lazy")]/@src')
                    if not img_nodes:
                        img_nodes = a.xpath('.//img/@data-original')
                    if not img_nodes:
                        img_nodes = a.xpath('.//img/@src')
                    if img_nodes:
                        img = img_nodes[0]
                        if img.startswith('/'):
                            img = 'https://feikuai.tv' + img
                    remark_nodes = a.xpath('.//div[contains(@class, "module-item-note")]//text()')
                    remark = ''
                    if remark_nodes:
                        remark = ''.join([x.strip() for x in remark_nodes if x.strip()])
                    videos.append({"vod_id": sid, "vod_name": name, "vod_pic": img, "vod_remarks": remark})
                except Exception:
                    continue
        except Exception:
            pass
        result['list'] = videos
        return result

    def _extract_text(self, root, xps):
        for xp in xps:
            nodes = root.xpath(xp)
            if nodes:
                if isinstance(nodes[0], str):
                    return nodes[0].strip()
                return ''.join(root.xpath(f'string({xp})')).strip()
        return ''

    def _map_api_and_referer(self, vurl):
        try:
            host = urlparse(vurl).netloc.lower()
        except Exception:
            host = ''
        api_path = 'dytM3U8.php'
        ref_html = 'dyttdpplayer.html'
        if 'ffzy' in host:
            api_path = 'ffM3U8.php'
            ref_html = 'ffdplayer.html'
        elif 'fengbao' in host or 'bfzy' in host:
            api_path = 'bfM3U8.php'
            ref_html = 'bfdplayer.html'
        elif 'yzzy' in host:
            api_path = 'yzm3u8.php'
            ref_html = 'yzdplayer.html'
        elif 'modu' in host or 'modujx' in host:
            api_path = 'mdm3u8.php'
            ref_html = 'mddplayer.html'
        elif 'maoyan' in host or 'maoyanplay' in host:
            api_path = 'mym3u8.php'
            ref_html = 'mydplayer.html'
        elif 'dytt' in host:
            api_path = 'dytM3U8.php'
            ref_html = 'dyttdpplayer.html'
        return api_path, ref_html

    def _select_hls_variant(self, m3u8_text, base_url):
        try:
            lines = [ln.strip() for ln in m3u8_text.splitlines() if ln.strip()]
            variants = []
            i = 0
            while i < len(lines):
                ln = lines[i]
                if ln.startswith('#EXT-X-STREAM-INF:') and i + 1 < len(lines):
                    attrs = ln[len('#EXT-X-STREAM-INF:'):]
                    bw = None
                    codecs = ''
                    height = None
                    for part in attrs.split(','):
                        kv = part.split('=', 1)
                        if len(kv) != 2:
                            continue
                        k, v = kv[0].strip().upper(), kv[1].strip()
                        if k == 'BANDWIDTH':
                            try:
                                bw = int(re.sub(r'\D', '', v))
                            except Exception:
                                bw = None
                        elif k == 'CODECS':
                            codecs = v.strip('"')
                        elif k == 'RESOLUTION':
                            try:
                                h = v.split('x')[-1]
                                height = int(re.sub(r'\D', '', h))
                            except Exception:
                                height = None
                    u = lines[i + 1]
                    absu = urljoin(base_url, u)
                    is_avc = ('avc1' in codecs.lower()) or ('h264' in codecs.lower())
                    variants.append({'url': absu, 'bw': bw or 0, 'h': height or 0, 'avc': is_avc})
                    i += 2
                    continue
                i += 1
            if not variants:
                return None
            avc = [v for v in variants if v['avc']]
            cand = avc if avc else variants
            # Prefer <= 1500k if available, else the lowest
            under = [v for v in cand if v['bw'] and v['bw'] <= 1500000]
            pick = None
            if under:
                pick = sorted(under, key=lambda x: (x['bw'] or 0, x['h']))[0]
            else:
                pick = sorted(cand, key=lambda x: (x['bw'] or 0, x['h']))[0]
            return pick['url']
        except Exception:
            return None

    def _extract_player_fields_js(self, obj_text):
        """Tolerant extractor for player object fields when JSON parsing fails.
        Returns dict with possibly 'url', 'encrypt', 'from'.
        """
        fields = {}
        try:
            # url: handle "url":"..." or 'url':'...' or url:"..." or url:... (until , or })
            m = re.search(r'(?i)(?:"url"|\'url\'|\burl\b)\s*:\s*(?:"([^"]*)"|\'([^\']*)\'|([^,}\s]+))', obj_text)
            if m:
                fields['url'] = m.group(1) or m.group(2) or m.group(3) or ''
            if not fields.get('url'):
                # Advanced: url: unescape('...') / decodeURIComponent('...')
                m2a = re.search(r'\burl\b\s*:\s*(unescape|decodeURIComponent)\("([^"]+)"\)', obj_text, re.I)
                if not m2a:
                    m2a = re.search(r'\burl\b\s*:\s*(unescape|decodeURIComponent)\(\'([^\']+)\'\)', obj_text, re.I)
                if m2a:
                    fn = m2a.group(1).lower()
                    inner = m2a.group(2)
                    try:
                        if 'unescape' in fn or 'decodeuri' in fn:
                            fields['url'] = unquote(inner)
                    except Exception:
                        pass
            if not fields.get('url'):
                # Advanced: url: atob('...') / Base64.decode('...') / MacPlayer.Base64.decode('...')
                m2b = re.search(r'\burl\b\s*:\s*(atob|Base64\.decode|MacPlayer\.Base64\.decode)\("([^"]+)"\)', obj_text, re.I)
                if not m2b:
                    m2b = re.search(r'\burl\b\s*:\s*(atob|Base64\.decode|MacPlayer\.Base64\.decode)\(\'([^\']+)\'\)', obj_text, re.I)
                if m2b:
                    fn = m2b.group(1).lower()
                    inner = m2b.group(2)
                    try:
                        b = base64.b64decode(inner + '===')
                        fields['url'] = b.decode('utf-8', errors='ignore')
                    except Exception:
                        pass
            if not fields.get('url'):
                # Advanced: concatenation like url:'a'+'b'+'c'
                m3 = re.search(r"\burl\b\s*:\s*((?:['\"][^'\"]*['\"][\s\r\n]*\+\s*)+['\"][^'\"]*['\"])", obj_text)
                if m3:
                    expr = m3.group(1)
                    parts = re.findall(r"['\"]([^'\"]*)['\"]", expr)
                    if parts:
                        fields['url'] = ''.join(parts)
        except Exception:
            pass
        try:
            # encrypt: numeric
            m = re.search(r'(?i)(?:"encrypt"|\'encrypt\'|\bencrypt\b)\s*:\s*(\d+)', obj_text)
            if m:
                fields['encrypt'] = m.group(1)
        except Exception:
            pass
        try:
            # from/source code: string
            m = re.search(r'(?i)(?:"from"|\'from\'|\bfrom\b)\s*:\s*(?:"([^"]*)"|\'([^\']*)\'|([^,}\s]+))', obj_text)
            if m:
                fields['from'] = (m.group(1) or m.group(2) or m.group(3) or '').lower()
        except Exception:
            pass
        return fields

    def _decode_url_field(self, raw, encrypt):
        try:
            if not raw:
                return ''
            enc = str(encrypt or '0').strip()
            if enc == '1':
                return unquote(raw)
            if enc == '2':
                try:
                    b = base64.b64decode(raw + '===')
                    return unquote(b.decode('utf-8', errors='ignore'))
                except Exception:
                    return unquote(raw)
            return raw
        except Exception:
            return raw

    def _scan_page_for_url(self, html):
        """Scan full HTML for a plausible video URL, including encoded forms.
        Returns a URL string or empty string if none found.
        """
        try:
            # 1) Plain HLS
            m = re.search(r'https?://[^\s"\']+\.m3u8[^\s"\']*', html, re.I)
            if m:
                return m.group(0)
            # 2) atob/base64-likes
            for mm in re.finditer(r'atob\("([^"]+)"\)|atob\(\'([^\']+)\'\)', html, re.I):
                try:
                    s = mm.group(1) or mm.group(2)
                    b = base64.b64decode(s + '===')
                    dec = b.decode('utf-8', errors='ignore')
                    m2 = re.search(r'https?://[^\s"\']+\.(?:m3u8|mp4)[^\s"\']*', dec, re.I)
                    if m2:
                        return m2.group(0)
                except Exception:
                    pass
            for mm in re.finditer(r'(?:Base64\.decode|MacPlayer\.Base64\.decode)\("([^"]+)"\)|(\bBase64\.decode|MacPlayer\.Base64\.decode)\(\'([^\']+)\'\)', html, re.I):
                try:
                    # groups could be (1) or (3) depending on which alt matched
                    s = mm.group(1) or mm.group(3)
                    b = base64.b64decode(s + '===')
                    dec = b.decode('utf-8', errors='ignore')
                    m2 = re.search(r'https?://[^\s"\']+\.(?:m3u8|mp4)[^\s"\']*', dec, re.I)
                    if m2:
                        return m2.group(0)
                except Exception:
                    pass
            # 3) decodeURIComponent/unescape
            for mm in re.finditer(r'(?:decodeURIComponent|unescape)\("([^"]+)"\)|(?:decodeURIComponent|unescape)\(\'([^\']+)\'\)', html, re.I):
                try:
                    s = mm.group(1) or mm.group(2)
                    dec = unquote(s)
                    m2 = re.search(r'https?://[^\s"\']+\.(?:m3u8|mp4)[^\s"\']*', dec, re.I)
                    if m2:
                        return m2.group(0)
                except Exception:
                    pass
            # 4) Concatenated strings producing URLs
            for mm in re.finditer(r"(['\"][^'\"]*['\"][\s\r\n]*\+\s*)+['\"][^'\"]*['\"]", html):
                expr = mm.group(0)
                parts = re.findall(r"['\"]([^'\"]*)['\"]", expr)
                if parts:
                    cand = ''.join(parts)
                    if cand.startswith('http') and ('.m3u8' in cand or '.mp4' in cand):
                        return cand
        except Exception:
            pass
        return ''

    def detailContent(self, ids):
        if not ids:
            return {'list': []}
        tid = str(ids[0]).strip()
        url = f'https://feikuai.tv/voddetail/{tid}.html'
        print(f"[飞快] detail: {url}")
        try:
            rsp = self.fetch(url, headers=self.header)
            if not rsp or not rsp.text:
                return self._create_fallback_vod(tid, '获取页面失败')
            root = self._parse_html(rsp)
            if root is None:
                return self._create_fallback_vod(tid, '解析HTML失败')
        except Exception as e:
            return self._create_fallback_vod(tid, f'异常: {str(e)}')
        title = ''
        try:
            tnodes = root.xpath('//h1/text() | //div[contains(@class, "module-info-heading")]//h1/text()')
            title = tnodes[0].strip() if tnodes else ''
        except Exception:
            title = ''
        pic = ''
        try:
            pnodes = root.xpath('//div[contains(@class, "module-info-poster")]//img/@data-original | //div[contains(@class, "module-info-poster")]//img/@src | //img[contains(@class, "lazy")]/@data-original | //img[contains(@class, "lazy")]/@src')
            if pnodes:
                pic = pnodes[0]
                if pic.startswith('/'):
                    pic = 'https://feikuai.tv' + pic
        except Exception:
            pic = ''
        detail = ''
        try:
            dnodes = root.xpath('//div[contains(@class, "module-info-introduction-content")]//text()')
            if dnodes:
                detail = '\n'.join([x.strip() for x in dnodes if x.strip()])
        except Exception:
            detail = ''
        vod = {
            "vod_id": tid,
            "vod_name": title,
            "vod_pic": pic,
            "type_name": "",
            "vod_year": "",
            "vod_area": "",
            "vod_remarks": "",
            "vod_actor": "",
            "vod_director": "",
            "vod_content": detail
        }
        playFrom = []
        playList = []
        try:
            # Only collect episode links inside playlist containers to avoid grabbing buttons like “立即播放”
            ep_links = root.xpath('//div[contains(@class, "module-play-list")]//a[contains(@href, "/vodplay/")] | //ul[contains(@class, "module-play-list")]//a[contains(@href, "/vodplay/")]')
            groups = {}
            for a in ep_links:
                try:
                    hrefs = a.xpath('./@href')
                    if not hrefs:
                        continue
                    href = hrefs[0]
                    m = re.search(r'/vodplay/(\d+)-(\d+)-(\d+)\.html', href)
                    if not m:
                        continue
                    vid, sid, epid = m.group(1), m.group(2), m.group(3)
                    if vid != tid:
                        continue
                    name = ''.join(a.xpath('string(.)')).strip()
                    if not name or name in ('立即播放', '收藏', '追更', '分享', '报错', '下载'):
                        continue
                    if sid not in groups:
                        groups[sid] = []
                    groups[sid].append(f"{name}${vid}-{sid}-{epid}")
                except Exception:
                    continue
            # Determine source order by his-tab-list blocks
            ordered_sids = []
            for blk in root.xpath('//div[contains(@class, "his-tab-list")]'):
                try:
                    first = blk.xpath('.//a[contains(@href, "/vodplay/")][1]/@href')
                    if not first:
                        continue
                    mm = re.search(r'/vodplay/(\d+)-(\d+)-(\d+)\.html', first[0])
                    if not mm:
                        continue
                    sid = mm.group(2)
                    if sid not in ordered_sids:
                        ordered_sids.append(sid)
                except Exception:
                    continue
            labels = []
            try:
                labels = [x.strip() for x in root.xpath('//div[contains(@class, "module-tab-items-box")]//div[contains(@class, "module-tab-item")]//span/text()') if x.strip()]
            except Exception:
                labels = []
            for idx, sid in enumerate(ordered_sids):
                sname = labels[idx] if idx < len(labels) else f"线路{sid}"
                playFrom.append(sname)
                playList.append('#'.join(groups.get(sid, [])))
        except Exception:
            pass
        if not playFrom or not playList:
            playFrom = ['飞快']
            playList = [f'暂无播放源$https://feikuai.tv/voddetail/{tid}.html']
        vod['vod_play_from'] = '$$$'.join(playFrom) if playFrom else ""
        vod['vod_play_url'] = '$$$'.join(playList)
        return {'list': [vod]}

    def _create_fallback_vod(self, tid, error_msg):
        return {
            'list': [{
                'vod_id': tid,
                'vod_name': f'加载失败: {error_msg}',
                'vod_pic': '',
                'vod_content': f'无法加载视频详情。错误: {error_msg}',
                'vod_play_from': '飞快',
                'vod_play_url': f'错误$https://feikuai.tv/voddetail/{tid}.html'
            }]
        }

    def searchContent(self, key, quick, pg='1'):
        return self.searchContentPage(key, quick, pg)

    def searchContentPage(self, key, quick, pg='1'):
        videos = []
        try:
            if str(pg) in ('', '1'):
                url = f'https://feikuai.tv/vodsearch/-------------.html?wd={quote_plus(key)}'
                headers = self.header.copy()
                headers['Referer'] = f'https://feikuai.tv/vodsearch/-------------.html?wd={quote_plus(key)}'
            else:
                url = f'https://feikuai.tv/label/search_ajax.html?wd={quote_plus(key)}&by=time&order=desc&page={pg}'
                headers = self.header.copy()
                headers['X-Requested-With'] = 'XMLHttpRequest'
                headers['Accept'] = '*/*'
                headers['Referer'] = f'https://feikuai.tv/vodsearch/-------------.html?wd={quote_plus(key)}'
            print(f"[飞快] search url: {url}")
            rsp = self.fetch(url, headers=headers)
            if not rsp or not rsp.text:
                return {'list': []}
            root = self._parse_html(rsp)
            items = root.xpath('//div[@id="resultList"]//a[contains(@href, "/voddetail/")]')
            if not items:
                items = root.xpath('//div[contains(@class, "module-card-items")]//a[contains(@href, "/voddetail/")]')
            if not items:
                items = root.xpath('//div[contains(@class, "module-items") and contains(@class, "module-poster-items")]//a[contains(@href, "/voddetail/")]')
            if not items:
                items = root.xpath('//a[contains(@href, "/voddetail/")]')
            seen = set()
            for a in items:
                try:
                    hrefs = a.xpath('./@href')
                    if not hrefs:
                        continue
                    href = hrefs[0]
                    m = re.search(r'/voddetail/(\d+)\.html', href)
                    if not m:
                        continue
                    sid = m.group(1)
                    if sid in seen:
                        continue
                    seen.add(sid)
                    title_nodes = a.xpath('.//div[contains(@class, "module-card-item-title")]//text()')
                    if not title_nodes:
                        title_nodes = a.xpath('.//div[contains(@class, "module-poster-item-title")]/text()')
                    if not title_nodes:
                        title_nodes = a.xpath('./@title')
                    if not title_nodes:
                        title_nodes = a.xpath('.//img/@alt')
                    name = title_nodes[0].strip() if title_nodes else ''
                    img = ''
                    img_nodes = a.xpath('.//img[contains(@class, "lazy")]/@data-original')
                    if not img_nodes:
                        img_nodes = a.xpath('.//img[contains(@class, "lazy")]/@src')
                    if not img_nodes:
                        img_nodes = a.xpath('.//img/@data-original')
                    if not img_nodes:
                        img_nodes = a.xpath('.//img/@src')
                    if img_nodes:
                        img = img_nodes[0]
                        if img.startswith('/'):
                            img = 'https://feikuai.tv' + img
                    remark_nodes = a.xpath('.//div[contains(@class, "module-item-note")]//text()')
                    remark = ''
                    if remark_nodes:
                        remark = ''.join([x.strip() for x in remark_nodes if x.strip()])
                    videos.append({"vod_id": sid, "vod_name": name, "vod_pic": img, "vod_remarks": remark})
                except Exception:
                    continue
            print(f"[飞快] search items: {len(videos)}")
            return {'list': videos}
        except Exception:
            return {'list': []}

    def playerContent(self, flag, id, vipFlags):
        print(f"[飞快 DEBUG] playerContent flag={flag} id={id}")
        norm_flag = (flag or "").strip().lower()
        force_dytt = norm_flag.startswith("高清4".lower())
        play_url = f'https://feikuai.tv/vodplay/{id}.html'
        try:
            rsp = self.fetch(play_url, headers=self.header, timeout=45)
            try:
                print(f"[飞快 DEBUG] fetched play page status={getattr(rsp, 'status_code', None)} len={len(rsp.text) if rsp and hasattr(rsp, 'text') and rsp.text else 0}")
            except Exception:
                pass
            if rsp and rsp.text:
                text = rsp.text
                m = re.search(r'(?:var\s+)?player_[a-zA-Z0-9_]+\s*=\s*(\{.*?\})', text, re.S)
                if not m:
                    try:
                        print("[飞快 DEBUG] primary player regex miss; trying player_data ...")
                    except Exception:
                        pass
                    mp = re.search(r'player_data\s*=\s*(\{.*?\})', text, re.S)
                    if mp:
                        m = mp
                if m:
                    try:
                        raw_obj = m.group(1)
                        try:
                            data = json.loads(raw_obj)
                            fsource = (data.get('from') or '').lower()
                            vurl = (
                                data.get('url') or data.get('url_next') or data.get('link') or
                                data.get('video') or data.get('playurl') or data.get('vurl') or data.get('src') or ''
                            )
                            encrypt = str(data.get('encrypt', '0'))
                            try:
                                print(f"[飞快 DEBUG] player json keys from={fsource} encrypt={encrypt} url_len={len(vurl) if isinstance(vurl, str) else 0}")
                            except Exception:
                                pass
                        except Exception:
                            fields = self._extract_player_fields_js(raw_obj)
                            fsource = (fields.get('from') or '').lower()
                            vurl = fields.get('url') or ''
                            encrypt = str(fields.get('encrypt') or '0')
                            try:
                                print(f"[飞快 DEBUG] player tolerant keys from={fsource} encrypt={encrypt} url_len={len(vurl) if isinstance(vurl, str) else 0}")
                            except Exception:
                                pass
                        if vurl:
                            vurl = self._decode_url_field(vurl, encrypt)
                            # Extra fallback: sometimes encrypt=0 but url is percent-encoded
                            if not vurl.startswith('http') and ('%' in vurl):
                                try:
                                    v_try = unquote(vurl)
                                    if v_try.startswith('http'):
                                        vurl = v_try
                                except Exception:
                                    pass
                            if vurl.startswith('//'):
                                vurl = 'https:' + vurl
                            if vurl.startswith('http'):
                                lower = vurl.split('?', 1)[0].lower()
                                try:
                                    print(f"[飞快 DEBUG] vurl normalized={vurl[:160]}")
                                except Exception:
                                    pass
                                # RADICAL: for 高清4 (dytt) with dytt-cine upstream, bypass Feikuai API and play upstream directly
                                try:
                                    u = urlparse(vurl)
                                    host = (u.netloc or '').lower()
                                except Exception:
                                    host = ''
                                if force_dytt and host and ('dytt-cine.com' in host) and lower.endswith('index.m3u8'):
                                    scheme = u.scheme or 'https'
                                    base = f"{scheme}://{u.netloc}" if u and u.netloc else 'https://vip.dytt-cine.com'
                                    play_headers = {
                                        "User-Agent": self.header.get("User-Agent", ""),
                                        "Referer": base + "/",
                                        "Origin": base,
                                        "Accept": "*/*",
                                        "Accept-Language": self.header.get("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8"),
                                        "Connection": "keep-alive"
                                    }
                                    print(f"[飞快 DEBUG] dytt DIRECT url={vurl}")
                                    return {"parse": 0, "url": vurl, "header": play_headers}
                                # If HLS, resolve master -> stable child variant and return Feikuai API URL
                                if lower.endswith('.m3u8'):
                                    try:
                                        print(f"[飞快 DEBUG] HLS detected lower={lower}")
                                    except Exception:
                                        pass
                                    api_path, ref_html = self._map_api_and_referer(vurl)
                                    try:
                                        print(f"[飞快 DEBUG] api_path={api_path} ref_html={ref_html} fsource={fsource}")
                                    except Exception:
                                        pass
                                    api_url = (
                                        f'https://feikuai.tv/api/{api_path}?url=' + quote_plus(vurl) +
                                        '&ref=' + quote_plus(play_url) +
                                        '&ua=' + quote_plus(self.header.get('User-Agent', ''))
                                    )
                                    try:
                                        print(f"[飞快 DEBUG] api_url={api_url[:200]}")
                                    except Exception:
                                        pass
                                    api_headers = {
                                        "User-Agent": self.header.get("User-Agent", ""),
                                        "Referer": f"https://feikuai.tv/static/player/{ref_html}",
                                        "Origin": "https://feikuai.tv",
                                        "Accept": "*/*",
                                        "Accept-Language": self.header.get("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8"),
                                        "Accept-Encoding": "gzip, deflate",
                                        "Connection": "keep-alive"
                                    }
                                    # For 高清4 (dytt), avoid prefetch/variant and route through local proxy
                                    is_dytt = force_dytt or (api_path == 'dytM3U8.php') or ('dytt' in (fsource or ''))
                                    if is_dytt:
                                        proxy_url = f"{self.getProxyUrl()}&do=playlist&url=" + quote_plus(api_url) + f"&ref_html={ref_html}"
                                        print(f"[飞快 DEBUG] dytt proxy_url={proxy_url}")
                                        return {"parse": 0, "url": proxy_url, "header": {}}
                                    try:
                                        m3 = self.fetch(api_url, headers=api_headers, timeout=30)
                                        try:
                                            print(f"[飞快 DEBUG] api fetch status={getattr(m3,'status_code',None)} has_m3u8={bool(m3 and m3.text and '#EXTM3U' in m3.text)}")
                                        except Exception:
                                            pass
                                        child = None
                                        if m3 and m3.text and '#EXTM3U' in m3.text:
                                            child = self._select_hls_variant(m3.text, vurl)
                                        target_api = None
                                        if child:
                                            try:
                                                print(f"[飞快 DEBUG] variant child selected={child}")
                                            except Exception:
                                                pass
                                            target_api = (
                                                f'https://feikuai.tv/api/{api_path}?url=' + quote_plus(child) +
                                                '&ref=' + quote_plus(play_url) +
                                                '&ua=' + quote_plus(self.header.get('User-Agent', ''))
                                            )
                                        target_api = target_api or api_url
                                        # Return Feikuai API URL with static-player headers
                                        play_headers = {
                                            "User-Agent": self.header.get("User-Agent", ""),
                                            "Referer": f"https://feikuai.tv/static/player/{ref_html}",
                                            "Origin": "https://feikuai.tv",
                                            "Accept": "*/*",
                                            "Accept-Language": self.header.get("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8"),
                                            "Accept-Encoding": "gzip, deflate",
                                            "Connection": "keep-alive"
                                        }
                                        try:
                                            print(f"[飞快 DEBUG] return api target={target_api}")
                                        except Exception:
                                            pass
                                        return {"parse": 0, "url": target_api, "header": play_headers}
                                    except Exception:
                                        pass
                                # Non-HLS: use direct host with host-based headers
                                try:
                                    u = urlparse(vurl)
                                    base = f"{u.scheme}://{u.netloc}" if u.scheme and u.netloc else "https://feikuai.tv"
                                except Exception:
                                    base = "https://feikuai.tv"
                                play_headers = {
                                    "User-Agent": self.header.get("User-Agent", ""),
                                    "Referer": base + "/",
                                    "Origin": base,
                                    "Accept": "*/*",
                                    "Accept-Language": self.header.get("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8"),
                                    "Connection": "keep-alive"
                                }
                                try:
                                    print(f"[飞快 DEBUG] non-HLS return url={vurl}")
                                except Exception:
                                    pass
                                return {"parse": 0, "url": vurl, "header": play_headers}
                    except Exception:
                        pass
                # If no m or no vurl found yet, try scanning whole page before MacPlayer fallback
                try:
                    scan_url = self._scan_page_for_url(text)
                    if scan_url:
                        lower = scan_url.split('?', 1)[0].lower()
                        api_path, ref_html = self._map_api_and_referer(scan_url)
                        if lower.endswith('.m3u8'):
                            api_url = (
                                f'https://feikuai.tv/api/{api_path}?url=' + quote_plus(scan_url) +
                                '&ref=' + quote_plus(play_url) +
                                '&ua=' + quote_plus(self.header.get('User-Agent', ''))
                            )
                            play_headers = {
                                "User-Agent": self.header.get("User-Agent", ""),
                                "Referer": f"https://feikuai.tv/static/player/{ref_html}",
                                "Origin": "https://feikuai.tv",
                                "Accept": "*/*",
                                "Accept-Language": self.header.get("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8"),
                                "Accept-Encoding": "gzip, deflate",
                                "Connection": "keep-alive"
                            }
                            try:
                                print(f"[飞快 DEBUG] pre-MacPlayer page-scan api_url={api_url[:200]}")
                            except Exception:
                                pass
                            return {"parse": 0, "url": api_url, "header": play_headers}
                except Exception:
                    pass
                if not m:
                    try:
                        mt = re.search(r'(?:player_data\s*=\s*\{.*?\}|(?:var\s+)?player_[a-zA-Z0-9_]+\s*=\s*\{.*?\})', text, re.S)
                        if mt:
                            obj_text_m = re.search(r'\{.*\}', mt.group(0), re.S)
                            obj_text = obj_text_m.group(0) if obj_text_m else ''
                            fields = self._extract_player_fields_js(obj_text)
                            fsource = (fields.get('from') or '').lower()
                            vurl = fields.get('url') or ''
                            encrypt = str(fields.get('encrypt') or '0')
                            try:
                                print(f"[飞快 DEBUG] tolerant object matched from={fsource} encrypt={encrypt} url_len={len(vurl) if isinstance(vurl, str) else 0}")
                            except Exception:
                                pass
                            if vurl:
                                vurl = self._decode_url_field(vurl, encrypt)
                                if not vurl.startswith('http') and ('%' in vurl):
                                    try:
                                        v_try = unquote(vurl)
                                        if v_try.startswith('http'):
                                            vurl = v_try
                                    except Exception:
                                        pass
                                if vurl.startswith('//'):
                                    vurl = 'https:' + vurl
                                if vurl.startswith('http'):
                                    lower = vurl.split('?', 1)[0].lower()
                                    try:
                                        print(f"[飞快 DEBUG] vurl normalized={vurl[:160]}")
                                    except Exception:
                                        pass
                                    try:
                                        u = urlparse(vurl)
                                        host = (u.netloc or '').lower()
                                    except Exception:
                                        host = ''
                                    if force_dytt and host and ('dytt-cine.com' in host) and lower.endswith('index.m3u8'):
                                        scheme = u.scheme or 'https'
                                        base = f"{scheme}://{u.netloc}" if u and u.netloc else 'https://vip.dytt-cine.com'
                                        play_headers = {
                                            "User-Agent": self.header.get("User-Agent", ""),
                                            "Referer": base + "/",
                                            "Origin": base,
                                            "Accept": "*/*",
                                            "Accept-Language": self.header.get("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8"),
                                            "Connection": "keep-alive"
                                        }
                                        print(f"[飞快 DEBUG] dytt DIRECT url={vurl}")
                                        return {"parse": 0, "url": vurl, "header": play_headers}
                                    if lower.endswith('.m3u8'):
                                        api_path, ref_html = self._map_api_and_referer(vurl)
                                        api_url = (
                                            f'https://feikuai.tv/api/{api_path}?url=' + quote_plus(vurl) +
                                            '&ref=' + quote_plus(play_url) +
                                            '&ua=' + quote_plus(self.header.get('User-Agent', ''))
                                        )
                                        api_headers = {
                                            "User-Agent": self.header.get("User-Agent", ""),
                                            "Referer": f"https://feikuai.tv/static/player/{ref_html}",
                                            "Origin": "https://feikuai.tv",
                                            "Accept": "*/*",
                                            "Accept-Language": self.header.get("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8"),
                                            "Accept-Encoding": "gzip, deflate",
                                            "Connection": "keep-alive"
                                        }
                                        is_dytt = force_dytt or (api_path == 'dytM3U8.php') or ('dytt' in (fsource or ''))
                                        if is_dytt:
                                            proxy_url = f"{self.getProxyUrl()}&do=playlist&url=" + quote_plus(api_url) + f"&ref_html={ref_html}"
                                            print(f"[飞快 DEBUG] dytt proxy_url={proxy_url}")
                                            return {"parse": 0, "url": proxy_url, "header": {}}
                                        try:
                                            m3 = self.fetch(api_url, headers=api_headers, timeout=30)
                                            child = None
                                            if m3 and m3.text and '#EXTM3U' in m3.text:
                                                child = self._select_hls_variant(m3.text, vurl)
                                            target_api = None
                                            if child:
                                                target_api = (
                                                    f'https://feikuai.tv/api/{api_path}?url=' + quote_plus(child) +
                                                    '&ref=' + quote_plus(play_url) +
                                                    '&ua=' + quote_plus(self.header.get('User-Agent', ''))
                                                )
                                            target_api = target_api or api_url
                                            play_headers = {
                                                "User-Agent": self.header.get("User-Agent", ""),
                                                "Referer": f"https://feikuai.tv/static/player/{ref_html}",
                                                "Origin": "https://feikuai.tv",
                                                "Accept": "*/*",
                                                "Accept-Language": self.header.get("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8"),
                                                "Accept-Encoding": "gzip, deflate",
                                                "Connection": "keep-alive"
                                            }
                                            return {"parse": 0, "url": target_api, "header": play_headers}
                                        except Exception:
                                            pass
                                try:
                                    u = urlparse(vurl)
                                    base = f"{u.scheme}://{u.netloc}" if u.scheme and u.netloc else "https://feikuai.tv"
                                except Exception:
                                    base = "https://feikuai.tv"
                                play_headers = {
                                    "User-Agent": self.header.get("User-Agent", ""),
                                    "Referer": base + "/",
                                    "Origin": base,
                                    "Accept": "*/*",
                                    "Accept-Language": self.header.get("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8"),
                                    "Connection": "keep-alive"
                                }
                                return {"parse": 0, "url": vurl, "header": play_headers}
                    except Exception:
                        pass
                # Fallback: MacCMS style MacPlayer variable
                try:
                    m_play = re.search(r'MacPlayer\s*=\s*\{[\s\S]*?PlayUrl\s*[:=]\s*(["\'])(.+?)\1', text)
                    if m_play:
                        vurl = m_play.group(2)
                        enc_m = re.search(r'Encrypt\s*[:=]\s*(\d+)', text)
                        encrypt = enc_m.group(1) if enc_m else '0'
                        try:
                            print(f"[飞快 DEBUG] MacPlayer PlayUrl found encrypt={encrypt} vurl_len={len(vurl) if isinstance(vurl, str) else 0}")
                        except Exception:
                            pass
                        if vurl:
                            vurl = self._decode_url_field(vurl, encrypt)
                            if not vurl.startswith('http') and ('%' in vurl):
                                try:
                                    v_try = unquote(vurl)
                                    if v_try.startswith('http'):
                                        vurl = v_try
                                except Exception:
                                    pass
                            if vurl.startswith('//'):
                                vurl = 'https:' + vurl
                            if vurl.startswith('http'):
                                lower = vurl.split('?', 1)[0].lower()
                                # Choose site proxy by upstream host and resolve to variant, return Feikuai API URL
                                api_path, ref_html = self._map_api_and_referer(vurl)
                                if lower.endswith('.m3u8'):
                                    api_url = (
                                        f'https://feikuai.tv/api/{api_path}?url=' + quote_plus(vurl) +
                                        '&ref=' + quote_plus(play_url) +
                                        '&ua=' + quote_plus(self.header.get('User-Agent', ''))
                                    )
                                    api_headers = {
                                        "User-Agent": self.header.get("User-Agent", ""),
                                        "Referer": f"https://feikuai.tv/static/player/{ref_html}",
                                        "Origin": "https://feikuai.tv",
                                        "Accept": "*/*",
                                        "Accept-Language": self.header.get("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8"),
                                        "Accept-Encoding": "gzip, deflate",
                                        "Connection": "keep-alive"
                                    }
                                    # For 高清4 (dytt), route through local proxy
                                    is_dytt = force_dytt or (api_path == 'dytM3U8.php')
                                    if is_dytt:
                                        proxy_url = f"{self.getProxyUrl()}&do=playlist&url=" + quote_plus(api_url) + f"&ref_html={ref_html}"
                                        print(f"[飞快 DEBUG] dytt proxy_url={proxy_url}")
                                        return {"parse": 0, "url": proxy_url, "header": {}}
                                    try:
                                        m3 = self.fetch(api_url, headers=api_headers, timeout=30)
                                        child = None
                                        if m3 and m3.text and '#EXTM3U' in m3.text:
                                            child = self._select_hls_variant(m3.text, vurl)
                                        target_api = None
                                        if child:
                                            target_api = (
                                                f'https://feikuai.tv/api/{api_path}?url=' + quote_plus(child) +
                                                '&ref=' + quote_plus(play_url) +
                                                '&ua=' + quote_plus(self.header.get('User-Agent', ''))
                                            )
                                        target_api = target_api or api_url
                                        play_headers = {
                                            "User-Agent": self.header.get("User-Agent", ""),
                                            "Referer": f"https://feikuai.tv/static/player/{ref_html}",
                                            "Origin": "https://feikuai.tv",
                                            "Accept": "*/*",
                                            "Accept-Language": self.header.get("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8"),
                                            "Accept-Encoding": "gzip, deflate",
                                            "Connection": "keep-alive"
                                        }
                                        return {"parse": 0, "url": target_api, "header": play_headers}
                                    except Exception:
                                        pass
                                # non-HLS
                                try:
                                    u = urlparse(vurl)
                                    base = f"{u.scheme}://{u.netloc}" if u.scheme and u.netloc else "https://feikuai.tv"
                                except Exception:
                                    base = "https://feikuai.tv"
                                play_headers = {
                                    "User-Agent": self.header.get("User-Agent", ""),
                                    "Referer": base + "/",
                                    "Origin": base,
                                    "Accept": "*/*",
                                    "Accept-Language": self.header.get("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8"),
                                    "Connection": "keep-alive"
                                }
                                return {"parse": 0, "url": vurl, "header": play_headers}
                except Exception:
                    pass
        except Exception:
            pass
        # Last-chance: scan for Feikuai API URL embedded in HTML and return it directly
        try:
            # Example: absolute https://feikuai.tv/api/dytM3U8.php?url=ENCODED
            m_api = re.search(r'https://feikuai\.tv/api/([a-zA-Z0-9_]+\.php)\?url=([^\s"\'&]+)', text)
            if m_api:
                api_path_found = m_api.group(1)
                raw_v = unquote(m_api.group(2))
                api_path_map, ref_html = self._map_api_and_referer(raw_v)
                api_path_use = api_path_found or (api_path_map + '')
                api_url = (
                    f'https://feikuai.tv/api/{api_path_use}?url=' + quote_plus(raw_v) +
                    '&ref=' + quote_plus(play_url) +
                    '&ua=' + quote_plus(self.header.get('User-Agent', ''))
                )
                play_headers = {
                    "User-Agent": self.header.get("User-Agent", ""),
                    "Referer": f"https://feikuai.tv/static/player/{ref_html}",
                    "Origin": "https://feikuai.tv",
                    "Accept": "*/*",
                    "Accept-Language": self.header.get("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8"),
                    "Accept-Encoding": "gzip, deflate",
                    "Connection": "keep-alive"
                }
                try:
                    print(f"[飞快 DEBUG] last-chance api_url={api_url[:220]}")
                except Exception:
                    pass
                return {"parse": 0, "url": api_url, "header": play_headers}
            # Relative /api/*.php?url=...
            m_api_rel = re.search(r'/api/([a-zA-Z0-9_]+\.php)\?url=([^\s"\'&]+)', text)
            if m_api_rel:
                api_path_found = m_api_rel.group(1)
                raw_v = unquote(m_api_rel.group(2))
                api_path_map, ref_html = self._map_api_and_referer(raw_v)
                api_path_use = api_path_found or (api_path_map + '')
                api_url = (
                    f'https://feikuai.tv/api/{api_path_use}?url=' + quote_plus(raw_v) +
                    '&ref=' + quote_plus(play_url) +
                    '&ua=' + quote_plus(self.header.get('User-Agent', ''))
                )
                play_headers = {
                    "User-Agent": self.header.get("User-Agent", ""),
                    "Referer": f"https://feikuai.tv/static/player/{ref_html}",
                    "Origin": "https://feikuai.tv",
                    "Accept": "*/*",
                    "Accept-Language": self.header.get("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8"),
                    "Accept-Encoding": "gzip, deflate",
                    "Connection": "keep-alive"
                }
                try:
                    print(f"[飞快 DEBUG] last-chance rel api_url={api_url[:220]}")
                except Exception:
                    pass
                return {"parse": 0, "url": api_url, "header": play_headers}
            # Relative /vid/*.php?url=... (map to api via host)
            m_vid_rel = re.search(r'/vid/([a-zA-Z0-9_]+)\.php\?([^"\']+)', text)
            if m_vid_rel:
                q = m_vid_rel.group(2)
                raw_v = ''
                for part in q.split('&'):
                    if part.startswith('url='):
                        raw_v = unquote(part.split('=', 1)[1])
                        break
                if raw_v:
                    api_path, ref_html = self._map_api_and_referer(raw_v)
                    api_url = (
                        f'https://feikuai.tv/api/{api_path}?url=' + quote_plus(raw_v) +
                        '&ref=' + quote_plus(play_url) +
                        '&ua=' + quote_plus(self.header.get('User-Agent', ''))
                    )
                    play_headers = {
                        "User-Agent": self.header.get("User-Agent", ""),
                        "Referer": f"https://feikuai.tv/static/player/{ref_html}",
                        "Origin": "https://feikuai.tv",
                        "Accept": "*/*",
                        "Accept-Language": self.header.get("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8"),
                        "Accept-Encoding": "gzip, deflate",
                        "Connection": "keep-alive"
                    }
                    try:
                        print(f"[飞快 DEBUG] last-chance vid->api_url={api_url[:220]}")
                    except Exception:
                        pass
                    return {"parse": 0, "url": api_url, "header": play_headers}
        except Exception:
            pass
        # If we reach here without resolving a direct playable URL, fall back to page URL (last resort)
        print(f"[飞快 DEBUG] fallback parse=1 url={play_url}")
        return {"parse": 1, "playUrl": "", "url": play_url, "header": self.header}

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def localProxy(self, param):
        # do=playlist: fetch Feikuai API playlist and rewrite segments through this proxy
        # do=segment: relay segment with Feikuai static-player headers
        try:
            do = param.get('do', '')
            ref_html = param.get('ref_html', 'dyttdpplayer.html')
            ua = self.header.get('User-Agent', '')
            base_headers = {
                "User-Agent": ua,
                "Referer": f"https://feikuai.tv/static/player/{ref_html}",
                "Origin": "https://feikuai.tv",
                "Accept": "*/*",
                "Accept-Language": self.header.get("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8"),
                "Connection": "keep-alive"
            }
            if do == 'playlist':
                api_url = param.get('url', '')
                if not api_url:
                    return [404, "text/plain", ""]
                from urllib.parse import urlparse
                api_url_dec = unquote(api_url)
                rsp = self.fetch(api_url_dec, headers=base_headers, timeout=45)
                if not rsp or rsp.status_code != 200:
                    return [404, "text/plain", ""]
                text = rsp.text
                # Determine upstream base from api url's query ?url=
                upstream = ''
                q = ''
                if '?' in api_url_dec:
                    q = api_url_dec.split('?', 1)[1]
                for part in q.split('&'):
                    if part.startswith('url='):
                        upstream = unquote(part.split('=', 1)[1])
                        break
                base = upstream or api_url_dec
                # Rewrite playlist: proxy all URIs (segments and nested m3u8) and URI="..." attributes
                lines = text.strip().split('\n')
                out = []
                for line in lines:
                    s = line.strip()
                    if not s:
                        out.append(line)
                        continue
                    if s.startswith('#'):
                        # Rewrite URI="..." inside tags like EXT-X-KEY, EXT-X-MAP, EXT-X-MEDIA
                        def _repl(m):
                            uri = m.group(1)
                            absu = urljoin(base, uri)
                            prox = f"{self.getProxyUrl()}&do=fetch&u=" + quote_plus(absu) + f"&ref_html={ref_html}"
                            return f'URI="{prox}"'
                        line2 = re.sub(r'URI="([^"]+)"', _repl, line)
                        out.append(line2)
                    else:
                        absu = urljoin(base, s)
                        prox = f"{self.getProxyUrl()}&do=fetch&u=" + quote_plus(absu) + f"&ref_html={ref_html}"
                        out.append(prox)
                data = '\n'.join(out)
                return [200, "application/vnd.apple.mpegurl; charset=utf-8", data]
            elif do == 'fetch' or do == 'segment':
                # Unified fetch for nested playlists, keys, and segments
                u = param.get('u') or param.get('seg') or ''
                if not u:
                    return [404, "text/plain", ""]
                u_dec = unquote(u)
                resp = self.fetch(u_dec, headers=base_headers, timeout=35)
                if not resp or resp.status_code != 200:
                    return [404, "text/plain", ""]
                # Detect playlist
                text = ''
                try:
                    text = resp.text
                except Exception:
                    text = ''
                if ('#EXTM3U' in text) or u_dec.lower().endswith('.m3u8'):
                    base = u_dec
                    lines = text.strip().split('\n')
                    out = []
                    for line in lines:
                        s = line.strip()
                        if not s:
                            out.append(line)
                            continue
                        if s.startswith('#'):
                            def _repl2(m):
                                uri = m.group(1)
                                absu = urljoin(base, uri)
                                prox = f"{self.getProxyUrl()}&do=fetch&u=" + quote_plus(absu) + f"&ref_html={ref_html}"
                                return f'URI="{prox}"'
                            line2 = re.sub(r'URI="([^"]+)"', _repl2, line)
                            out.append(line2)
                        else:
                            absu = urljoin(base, s)
                            prox = f"{self.getProxyUrl()}&do=fetch&u=" + quote_plus(absu) + f"&ref_html={ref_html}"
                            out.append(prox)
                    data = '\n'.join(out)
                    return [200, "application/vnd.apple.mpegurl; charset=utf-8", data]
                # Binary segment/key
                content = resp.content if hasattr(resp, 'content') else resp.text
                ctype = "application/octet-stream"
                lo = u_dec.lower()
                if lo.endswith('.ts') or 'video/MP2T' in resp.headers.get('Content-Type', ''):
                    ctype = "video/MP2T"
                elif lo.endswith('.mp4'):
                    ctype = "video/mp4"
                elif lo.endswith('.aac'):
                    ctype = "audio/aac"
                elif lo.endswith('.m4s') or lo.endswith('.cmfv'):
                    ctype = "video/iso.segment"
                elif lo.endswith('.key'):
                    ctype = "application/octet-stream"
                return [200, ctype, content]
            else:
                return [404, "text/plain", ""]
        except Exception:
            return [500, "text/plain", ""]

    config = {
        "filter": {
            "1": [
                {"key": "class", "name": "类型", "value": [{"n": "全部", "v": ""}, {"n": "恐怖", "v": "恐怖"}, {"n": "惊悚", "v": "惊悚"}, {"n": "爱情", "v": "爱情"}, {"n": "同性", "v": "同性"}, {"n": "喜剧", "v": "喜剧"}, {"n": "动画", "v": "动画"}, {"n": "纪录片", "v": "纪录片"}]},
                {"key": "area", "name": "地区", "value": [{"n": "全部", "v": ""}, {"n": "日本", "v": "日本"}, {"n": "韩国", "v": "韩国"}, {"n": "美国", "v": "美国"}, {"n": "英国", "v": "英国"}, {"n": "法国", "v": "法国"}, {"n": "德国", "v": "德国"}, {"n": "意大利", "v": "意大利"}, {"n": "巴西", "v": "巴西"}, {"n": "瑞典", "v": "瑞典"}]},
                {"key": "year", "name": "年份", "value": []},
                {"key": "by", "name": "排序", "value": [{"n": "最新", "v": "最新"}, {"n": "最热", "v": "最热"}, {"n": "评分", "v": "评分"}]}
            ],
            "16": [
                {"key": "class", "name": "类型", "value": [{"n": "全部", "v": ""}, {"n": "恐怖", "v": "恐怖"}, {"n": "惊悚", "v": "惊悚"}, {"n": "爱情", "v": "爱情"}, {"n": "同性", "v": "同性"}, {"n": "喜剧", "v": "喜剧"}, {"n": "动画", "v": "动画"}, {"n": "纪录片", "v": "纪录片"}]},
                {"key": "area", "name": "地区", "value": [{"n": "全部", "v": ""}, {"n": "美国", "v": "美国"}, {"n": "英国", "v": "英国"}, {"n": "法国", "v": "法国"}, {"n": "德国", "v": "德国"}, {"n": "意大利", "v": "意大利"}, {"n": "巴西", "v": "巴西"}, {"n": "瑞典", "v": "瑞典"}]},
                {"key": "year", "name": "年份", "value": []},
                {"key": "by", "name": "排序", "value": [{"n": "最新", "v": "最新"}, {"n": "评分", "v": "评分"}]}
            ],
            "15": [
                {"key": "class", "name": "类型", "value": [{"n": "全部", "v": ""}, {"n": "恐怖", "v": "恐怖"}, {"n": "惊悚", "v": "惊悚"}, {"n": "爱情", "v": "爱情"}, {"n": "同性", "v": "同性"}, {"n": "喜剧", "v": "喜剧"}, {"n": "动画", "v": "动画"}, {"n": "纪录片", "v": "纪录片"}]},
                {"key": "area", "name": "地区", "value": [{"n": "全部", "v": ""}, {"n": "日本", "v": "日本"}, {"n": "韩国", "v": "韩国"}]},
                {"key": "year", "name": "年份", "value": []},
                {"key": "by", "name": "排序", "value": [{"n": "最新", "v": "最新"}, {"n": "评分", "v": "评分"}]}
            ],
            "27": [
                {"key": "area", "name": "地区", "value": [{"n": "全部", "v": ""}, {"n": "日本", "v": "日本"}, {"n": "韩国", "v": "韩国"}]},
                {"key": "class", "name": "类型", "value": [{"n": "全部", "v": ""}, {"n": "同性", "v": "同性"}, {"n": "恐怖", "v": "恐怖"}, {"n": "情色", "v": "情色"}, {"n": "搞笑", "v": "搞笑"}]},
                {"key": "year", "name": "年份", "value": []},
                {"key": "by", "name": "排序", "value": [{"n": "最新", "v": "最新"}, {"n": "评分", "v": "评分"}]}
            ],
            "28": [
                {"key": "area", "name": "地区", "value": [{"n": "全部", "v": ""}, {"n": "美国", "v": "美国"}, {"n": "其他", "v": "其他"}]},
                {"key": "class", "name": "类型", "value": [{"n": "全部", "v": ""}, {"n": "同性", "v": "同性"}, {"n": "恐怖", "v": "恐怖"}, {"n": "搞笑", "v": "搞笑"}]},
                {"key": "year", "name": "年份", "value": []},
                {"key": "by", "name": "排序", "value": [{"n": "最新", "v": "最新"}, {"n": "评分", "v": "评分"}]}
            ],
            "32": [
                {"key": "year", "name": "年份", "value": []},
                {"key": "by", "name": "排序", "value": [{"n": "最新", "v": "最新"}, {"n": "评分", "v": "评分"}]}
            ]
        }
    }

    header = {
        "Referer": "https://feikuai.tv/",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive"
    }
