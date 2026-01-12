"""
@header({
  searchable: 1,
  filterable: 1,
  quickSearch: 1,
  title: '飞快',
  lang: 'hipy'
})
"""

import sys
import json
import re
import base64
import datetime
from urllib.parse import quote_plus, unquote
from lxml import etree

sys.path.append('..')
from base.spider import Spider


class Spider(Spider):
    def getName(self):
        return "飞快"

    def init(self, extend=""):
        pass

    def homeContent(self, filter):
        result = {}
        cateManual = {
            "电影": "1",
            "剧集": "2",
            "综艺": "3",
            "动漫": "4"
        }
        classes = [{'type_name': k, 'type_id': v} for k, v in cateManual.items()]
        result['class'] = classes

        return result

    def _parse_video_item(self, a_element):
        """解析单个视频项的公共方法"""
        try:
            href = a_element.xpath('./@href')[0] if a_element.xpath('./@href') else ''
            m = re.search(r'/voddetail/(\d+)\.html', href)
            if not m:
                return None
            sid = m.group(1)

            title_nodes = (a_element.xpath('.//div[contains(@class, "module-poster-item-title")]//text()') or
                          a_element.xpath('.//div[contains(@class, "module-card-item-title")]/a//text()') or
                          a_element.xpath('./@title') or a_element.xpath('.//img/@alt'))
            name = title_nodes[0].strip() if title_nodes else f"视频_{sid}"
            
            img = self._parse_image_url(a_element)
            
            remark_nodes = a_element.xpath('.//div[contains(@class, "module-item-note")]//text()')
            remark = ''.join([x.strip() for x in remark_nodes if x.strip()]) if remark_nodes else ""

            return {
                "vod_id": sid,
                "vod_name": name,
                "vod_pic": img,
                "vod_remarks": remark
            }
        except Exception:
            return None

    def _parse_image_url(self, element):
        """解析图片URL的公共方法"""
        img_nodes = (element.xpath('.//img[contains(@class, "lazy")]/@data-original[contains(., ".webp") or contains(., ".jpg") or contains(., ".png")]') or
                    element.xpath('.//img[contains(@class, "lazy")]/@src[contains(., ".webp") or contains(., ".jpg") or contains(., ".png")]') or
                    element.xpath('.//img/@data-original[contains(., ".webp") or contains(., ".jpg") or contains(., ".png")]') or
                    element.xpath('.//img/@src[contains(., ".webp") or contains(., ".jpg") or contains(., ".png")]'))
        
        if img_nodes:
            img = img_nodes[0]
            if img.startswith('/'):
                img = 'https://feikuai.tv' + img
            return img
        return ''

    def homeVideoContent(self):
        recommend_list = []
        try:
            url = "https://feikuai.tv/"
            rsp = self.fetch(url, headers=self.header)
            if not rsp or not rsp.text:
                return {'list': recommend_list}

            root = self._parse_html(rsp)
            if not root:
                return {'list': recommend_list}

            recommend_links = root.xpath(
                '//div[contains(@class, "module-focus")]//a[contains(@href, "/voddetail/")] | '
                '//div[contains(@class, "module-hot")]//a[contains(@href, "/voddetail/")] | '
                '//div[contains(@class, "module-recommend")]//a[contains(@href, "/voddetail/")] | '
                '//div[contains(@class, "module-items") and contains(@class, "module-poster-items")]//a[contains(@href, "/voddetail/")]'
            )

            seen = set()
            for a in recommend_links:
                video_item = self._parse_video_item(a)
                if video_item and video_item["vod_id"] not in seen:
                    seen.add(video_item["vod_id"])
                    recommend_list.append(video_item)

            recommend_list = recommend_list[:30]
        except Exception:
            pass
        return {'list': recommend_list}

    def _parse_html(self, rsp):
        try:
            parser = etree.HTMLParser(encoding='utf-8', recover=True, remove_blank_text=True)
            if hasattr(rsp, 'content'):
                return etree.HTML(rsp.content, parser=parser)
            return etree.HTML(rsp.text.encode('utf-8', errors='ignore'), parser=parser)
        except Exception:

            return None

    def _build_vodshow_url(self, tid, pg, ext):
        area = (ext.get('area') or ext.get('1') or '').strip()
        cate = (ext.get('class') or ext.get('3') or '').strip()
        year = (ext.get('year') or ext.get('11') or '').strip()
        
        enc_area = quote_plus(area) if area else ''
        enc_cate = quote_plus(cate) if cate else ''
        pg_str = '' if str(pg) in ('', '1') else str(pg)
        return f'https://feikuai.tv/vodshow/{tid}-{enc_area}--{enc_cate}-----{pg_str}---{year}.html'

    def categoryContent(self, tid, pg, filter, extend):
        if tid == '0':
            return self.homeVideoContent()
        
        result = {'list': [], 'page': pg, 'pagecount': 9999, 'limit': 90, 'total': 999999}
        try:
            ext = json.loads(extend) if extend and isinstance(extend, str) else {}
            url = self._build_vodshow_url(tid, pg, ext)
        except Exception:
            url = f'https://feikuai.tv/vodshow/{tid}-----------.html'
        
        headers = self.header.copy()

        headers['Referer'] = f'https://feikuai.tv/vodtype/{tid}.html'
        
        rsp = self.fetch(url, headers=headers)
        if not rsp or not rsp.text:
            return result
        
        root = self._parse_html(rsp)
        videos = []
        seen = set()
        try:
            links = root.xpath('//div[contains(@class, "module-items") and contains(@class, "module-poster-items")]//a[contains(@href, "/voddetail/")]') or \
                    root.xpath('//a[contains(@class, "module-poster-item") and contains(@href, "/voddetail/")]') or \
                    root.xpath('//div[contains(@class, "module-card-items")]//a[contains(@href, "/voddetail/")]')
            
            for a in links:
                video_item = self._parse_video_item(a)
                if video_item and video_item["vod_id"] not in seen:
                    seen.add(video_item["vod_id"])
                    videos.append(video_item)
        except Exception:
            pass
        
        result['list'] = videos
        return result

    def _decode_url_field(self, raw, encrypt):
        try:
            if not raw:
                return ''
            enc = str(encrypt or '0').strip()
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
        try:
            rsp = self.fetch(url, headers=self.header)
            if not rsp or not rsp.text:
                return {'list': []}
            root = self._parse_html(rsp)
            if not root:
                return {'list': []}
        except Exception:
            return {'list': []}
        
        title = root.xpath('//h1/text() | //div[contains(@class, "module-info-heading")]//h1/text()')
        title = title[0].strip() if title else ''
        pic = ''
        try:
            pnodes = root.xpath('//div[contains(@class, "module-info-poster")]//img/@data-original[contains(., ".webp") or contains(., ".jpg") or contains(., ".png")]')
            if not pnodes:
                pnodes = root.xpath('//div[contains(@class, "module-info-poster")]//img/@src[contains(., ".webp") or contains(., ".jpg") or contains(., ".png")]')
            if not pnodes:
                pnodes = root.xpath('//img[contains(@class, "lazy")]/@data-original[contains(., ".webp") or contains(., ".jpg") or contains(., ".png")]')
            if not pnodes:
                pnodes = root.xpath('//img[contains(@class, "lazy")]/@src[contains(., ".webp") or contains(., ".jpg") or contains(., ".png")]')
            if pnodes:
                pic = pnodes[0]
                if pic.startswith('/'):
                    pic = 'https://feikuai.tv' + pic
        except Exception:
            pic = ''
        
        detail = ''
        try:
            dnodes = root.xpath('//div[contains(@class, "module-info-introduction-content")]//text()')
            detail = '\n'.join([x.strip() for x in dnodes if x.strip()]) if dnodes else ''
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
            ep_links = root.xpath('//div[contains(@class, "module-play-list")]//a[contains(@href, "/vodplay/")] | //ul[contains(@class, "module-play-list")]//a[contains(@href, "/vodplay/")]')
            groups = {}
            for a in ep_links:
                try:
                    href = a.xpath('./@href')[0] if a.xpath('./@href') else ''
                    m = re.search(r'/vodplay/(\d+)-(\d+)-(\d+)\.html', href)
                    if not m:
                        continue
                    vid, sid, epid = m.groups()
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
            
            ordered_sids = []
            for blk in root.xpath('//div[contains(@class, "his-tab-list")]'):
                try:
                    first = blk.xpath('.//a[contains(@href, "/vodplay/")][1]/@href')
                    if first:
                        mm = re.search(r'/vodplay/(\d+)-(\d+)-(\d+)\.html', first[0])
                        if mm:
                            sid = mm.group(2)
                            if sid not in ordered_sids:
                                ordered_sids.append(sid)
                except Exception:
                    continue
            
            labels = [x.strip() for x in root.xpath('//div[contains(@class, "module-tab-items-box")]//div[contains(@class, "module-tab-item")]//span/text()') if x.strip()]
            
            for idx, sid in enumerate(ordered_sids):
                sname = labels[idx] if idx < len(labels) else f"线路{sid}"
                playFrom.append(sname)
                playList.append('#'.join(groups.get(sid, [])))
        except Exception:
            pass
        
        vod['vod_play_from'] = '$$$'.join(playFrom) if playFrom else ""
        vod['vod_play_url'] = '$$$'.join(playList)
        return {'list': [vod]}

    def searchContent(self, key, quick, pg='1'):
        videos = []
        try:
            pg = str(pg)
            if pg in ('', '1'):
                url = f'https://feikuai.tv/vodsearch/-------------.html?wd={quote_plus(key)}'
                headers = self.header.copy()
                headers['Referer'] = f'https://feikuai.tv/vodsearch/-------------.html?wd={quote_plus(key)}'
            else:
                url = f'https://feikuai.tv/label/search_ajax.html?wd={quote_plus(key)}&by=time&order=desc&page={pg}'
                headers = self.header.copy()
                headers['X-Requested-With'] = 'XMLHttpRequest'
                headers['Accept'] = '*/*'
                headers['Referer'] = f'https://feikuai.tv/vodsearch/-------------.html?wd={quote_plus(key)}'
            
            rsp = self.fetch(url, headers=headers)
            if not rsp or not rsp.text:
                return {'list': []}
            
            root = self._parse_html(rsp)
            items = root.xpath('//div[@id="resultList"]//a[contains(@href, "/voddetail/")]') or \
                    root.xpath('//div[contains(@class, "module-card-items")]//a[contains(@href, "/voddetail/")]') or \
                    root.xpath('//div[contains(@class, "module-items") and contains(@class, "module-poster-items")]//a[contains(@href, "/voddetail/")]') or \
                    root.xpath('//a[contains(@href, "/voddetail/")]')
            
            seen = set()
            for a in items:
                video_item = self._parse_video_item(a)
                if video_item and video_item["vod_id"] not in seen:
                    seen.add(video_item["vod_id"])
                    videos.append(video_item)
        except Exception:
            pass
        return {'list': videos}

    def playerContent(self, flag, id, vipFlags):
        play_url = f'https://feikuai.tv/vodplay/{id}.html'
        vurl = play_url
        try:
            rsp = self.fetch(play_url, headers=self.header, timeout=45)
            if not rsp or not rsp.text:
                return {"parse": 0, "url": vurl, "header": self.header}
            pattern = r'(?:var\s+)?player_[a-zA-Z0-9_]+\s*=\s*(\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\})(?=\s*</script>)'
            m = re.search(pattern, rsp.text, re.S)
            if m:
                data = json.loads(m.group(1))
                vurl = data.get('url') or ''
                vurl = self._decode_url_field(vurl, str(data.get('encrypt', '0')))
                if vurl.startswith('//'):
                    vurl = 'https:' + vurl
                if vurl.endswith('.m3u8'):
                    return {"parse": 1, "url": vurl, "header": self.header}
        except Exception:
            pass
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

    header = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Connection": "keep-alive"
    }
