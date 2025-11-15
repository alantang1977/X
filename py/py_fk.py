# coding=utf-8
# !/usr/bin/python
import sys
import datetime
from copy import deepcopy
from urllib.parse import quote_plus, unquote
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

    def _decode_url_field(self, raw, encrypt):
        try:
            if not raw:
                return ''
            enc = str(encrypt or '0').strip()

            # 1. 先按业务规则解开第一层
            if enc == '1':
                txt = unquote(raw)
            elif enc == '2':
                try:
                    b = base64.b64decode(raw + '===')
                    txt = unquote(b.decode('utf-8', errors='ignore'))
                except Exception:
                    txt = unquote(raw)
            else:
                txt = raw

            # 2. 把 %uXXXX 转成真正的汉字
            #    %u7B2C01%u96C6 -> 第01集
            txt = re.sub(r'%u([0-9a-fA-F]{4})',
                         lambda m: chr(int(m.group(1), 16)), txt)

            return txt
        except Exception:
            return raw

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
        play_url = f'https://feikuai.tv/vodplay/{id}.html'
        vurl = play_url
        rsp = self.fetch(play_url, headers=self.header, timeout=45)
        text = rsp.text
        m = re.search(r'(?:var\s+)?player_[a-zA-Z0-9_]+\s*=\s*(\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\})(?=\s*</script>)', text, re.S)
        if m:
            data = json.loads(m.group(1))
            vurl = data.get('url') or ''
            vurl = self._decode_url_field(vurl, str(data.get('encrypt', '0')))
            if vurl.startswith('//'):
                vurl = 'https:' + vurl
            # 👇 只要它是 playlist.m3u8，就走本地代理
        return {"parse": 0, "url": vurl, "header": self.header}
    
    def localProxy(self, params):
        pass
    def isVideoFormat(self, url):
        return url

    def manualVideoCheck(self):
        return []

    def destroy(self):
        pass

    def getProxyUrl(self, local=True):
        return 'http://127.0.0.1:9978/proxy?do=py'

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
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive"
    }
