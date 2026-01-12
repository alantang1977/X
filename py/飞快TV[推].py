"""
@header({
  searchable: 1,
  filterable: 1,
  quickSearch: 1,
  title: '飞快',
  author: 'EylinSir修复版-网盘推送播放',
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
        _r1 = {}
        _c1 = {
            "电影": "1",
            "剧集": "2",
            "综艺": "3",
            "动漫": "4"
        }
        _c2 = [{'type_name': _k1, 'type_id': _v1} for _k1, _v1 in _c1.items()]
        _r1['class'] = _c2
        return _r1

    def homeVideoContent(self):
        _l1 = []
        try:
            _u1 = "".join(['h', 't', 't', 'p', 's', ':', '/', '/', 'f', 'e', 'i', 'k', 'u', 'a', 'i', '.', 't', 'v', '/'])
            _r2 = self.fetch(_u1, headers=self._get_header())
            if not _r2 or not _r2.text:
                return {'list': _l1}

            _h1 = self._parse_dom(_r2)
            if not _h1:
                return {'list': _l1}

            _x1 = _h1.xpath(
                '//div[contains(@class, "module-focus")]//a[contains(@href, "/voddetail/")] | '
                '//div[contains(@class, "module-hot")]//a[contains(@href, "/voddetail/")] | '
                '//div[contains(@class, "module-recommend")]//a[contains(@href, "/voddetail/")] | '
                '//div[contains(@class, "module-items") and contains(@class, "module-poster-items")]//a[contains(@href, "/voddetail/")]'
            )

            _s1 = set()
            for _a1 in _x1:
                _v1 = self._parse_item(_a1)
                if _v1 and _v1["vod_id"] not in _s1:
                    _s1.add(_v1["vod_id"])
                    _l1.append(_v1)

            _l1 = _l1[:30]
        except Exception:
            pass
        return {'list': _l1}

    def categoryContent(self, tid, pg, filter, extend):
        if tid == '0':
            return self.homeVideoContent()
        
        _r3 = {'list': [], 'page': pg, 'pagecount': 9999, 'limit': 90, 'total': 999999}
        try:
            _e1 = json.loads(extend) if extend and isinstance(extend, str) else {}
            _u2 = self._build_url(tid, pg, _e1)
        except Exception:
            _u2 = f'{"".join(["h","t","t","p","s",":","/","/","f","e","i","k","u","a","i",".","t","v","/","v","o","d","s","h","o","w","/",tid,"-","-","-","-","-","-","-","-","-",".","h","t","m","l"])}'
        
        _h2 = self._get_header().copy()
        _h2['Referer'] = f'https://feikuai.tv/vodtype/{tid}.html'
        
        _r4 = self.fetch(_u2, headers=_h2)
        if not _r4 or not _r4.text:
            return _r3
        
        _h3 = self._parse_dom(_r4)
        _v2 = []
        _s2 = set()
        try:
            _l2 = _h3.xpath('//div[contains(@class, "module-items") and contains(@class, "module-poster-items")]//a[contains(@href, "/voddetail/")]') or \
                    _h3.xpath('//a[contains(@class, "module-poster-item") and contains(@href, "/voddetail/")]') or \
                    _h3.xpath('//div[contains(@class, "module-card-items")]//a[contains(@href, "/voddetail/")]')
            
            for _a2 in _l2:
                _v3 = self._parse_item(_a2)
                if _v3 and _v3["vod_id"] not in _s2:
                    _s2.add(_v3["vod_id"])
                    _v2.append(_v3)
        except Exception:
            pass
        
        _r3['list'] = _v2
        return _r3

    def detailContent(self, ids):
        if not ids:
            return {'list': []}
        _t1 = str(ids[0]).strip()
        _u3 = f'https://feikuai.tv/voddetail/{_t1}.html'
        try:
            _r5 = self.fetch(_u3, headers=self._get_header())
            if not _r5 or not _r5.text:
                return {'list': []}
            _h4 = self._parse_dom(_r5)
            if not _h4:
                return {'list': []}
        except Exception:
            return {'list': []}
        
        _t2 = _h4.xpath('//h1/text() | //div[contains(@class, "module-info-heading")]//h1/text()')
        _t3 = _t2[0].strip() if _t2 else ''
        _p1 = self._get_img(_h4)
        _d1 = self._get_desc(_h4)
        
        _v4 = {
            "vod_id": _t1,
            "vod_name": _t3,
            "vod_pic": _p1,
            "type_name": "",
            "vod_year": "",
            "vod_area": "",
            "vod_remarks": "",
            "vod_actor": "",
            "vod_director": "",
            "vod_content": _d1
        }
        
        _f1, _l3 = self._get_sources(_h4, _t1)
        
        if not _f1 or not _l3:
            _f1 = ['飞快']
            _l3 = [f'{"".join(["暂","无","播","放","源"])}${"".join(["h","t","t","p","s",":","/","/","f","e","i","k","u","a","i",".","t","v","/","v","o","d","d","e","t","a","i","l","/",_t1,".","h","t","m","l"])}']
        
        _v4['vod_play_from'] = '$$$'.join(_f1) if _f1 else ""
        _v4['vod_play_url'] = '$$$'.join(_l3)
        return {'list': [_v4]}

    def searchContent(self, key, quick, pg='1'):
        _v5 = []
        try:
            _p2 = str(pg)
            if _p2 in ('', '1'):
                _u4 = f'https://feikuai.tv/vodsearch/-------------.html?wd={quote_plus(key)}'
                _h5 = self._get_header().copy()
                _h5['Referer'] = f'https://feikuai.tv/vodsearch/-------------.html?wd={quote_plus(key)}'
            else:
                _u4 = f'https://feikuai.tv/label/search_ajax.html?wd={quote_plus(key)}&by=time&order=desc&page={_p2}'
                _h5 = self._get_header().copy()
                _h5['X-Requested-With'] = 'XMLHttpRequest'
                _h5['Accept'] = '*/*'
                _h5['Referer'] = f'https://feikuai.tv/vodsearch/-------------.html?wd={quote_plus(key)}'
            
            _r6 = self.fetch(_u4, headers=_h5)
            if not _r6 or not _r6.text:
                return {'list': []}
            
            _h6 = self._parse_dom(_r6)
            _i1 = _h6.xpath('//div[@id="resultList"]//a[contains(@href, "/voddetail/")]') or \
                    _h6.xpath('//div[contains(@class, "module-card-items")]//a[contains(@href, "/voddetail/")]') or \
                    _h6.xpath('//div[contains(@class, "module-items") and contains(@class, "module-poster-items")]//a[contains(@href, "/voddetail/")]') or \
                    _h6.xpath('//a[contains(@href, "/voddetail/")]')
            
            _s3 = set()
            for _a3 in _i1:
                _v6 = self._parse_item(_a3)
                if _v6 and _v6["vod_id"] not in _s3:
                    _s3.add(_v6["vod_id"])
                    _v5.append(_v6)
        except Exception:
            pass
        return {'list': _v5}

    def playerContent(self, flag, id, vipFlags):

        if isinstance(id, str) and id.startswith(''.join(['p','u','s','h',':','/','/'])):
            return {"parse": 0, "url": id}
        

        _u5 = f'https://feikuai.tv/vodplay/{id}.html'
        _v7 = _u5
        try:
            _r7 = self.fetch(_u5, headers=self._get_header(), timeout=45)
            if not _r7 or not _r7.text:
                return {"parse": 0, "url": _v7, "header": self._get_header()}
            
            _p3 = r'(?:var\s+)?player_[a-zA-Z0-9_]+\s*=\s*(\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\})(?=\s*</script>)'
            _m1 = re.search(_p3, _r7.text, re.S)
            if _m1:
                _d2 = json.loads(_m1.group(1))
                _v7 = _d2.get('url') or ''
                _v7 = self._decode_str(_v7, str(_d2.get('encrypt', '0')))
                if _v7.startswith('//'):
                    _v7 = 'https:' + _v7
                if _v7.endswith('.m3u8'):
                    return {"parse": 1, "url": _v7, "header": self._get_header()}
        except Exception:
            pass
        return {"parse": 0, "url": _v7, "header": self._get_header()}
    
    def _parse_item(self, a_element):
        try:
            _h7 = a_element.xpath('./@href')[0] if a_element.xpath('./@href') else ''
            _m2 = re.search(r'/voddetail/(\d+)\.html', _h7)
            if not _m2:
                return None
            _s4 = _m2.group(1)

            _t4 = (a_element.xpath('.//div[contains(@class, "module-poster-item-title")]//text()') or
                          a_element.xpath('.//div[contains(@class, "module-card-item-title")]/a//text()') or
                          a_element.xpath('./@title') or a_element.xpath('.//img/@alt'))
            _n1 = _t4[0].strip() if _t4 else f"视频_{_s4}"
            
            _i2 = self._get_img(a_element)
            
            _r8 = a_element.xpath('.//div[contains(@class, "module-item-note")]//text()')
            _r9 = ''.join([x.strip() for x in _r8 if x.strip()]) if _r8 else ""

            return {
                "vod_id": _s4,
                "vod_name": _n1,
                "vod_pic": _i2,
                "vod_remarks": _r9
            }
        except Exception:
            return None

    def _get_img(self, element):
        _i3 = (element.xpath('.//img[contains(@class, "lazy")]/@data-original[contains(., ".webp") or contains(., ".jpg") or contains(., ".png")]') or
                    element.xpath('.//img[contains(@class, "lazy")]/@src[contains(., ".webp") or contains(., ".jpg") or contains(., ".png")]') or
                    element.xpath('.//img/@data-original[contains(., ".webp") or contains(., ".jpg") or contains(., ".png")]') or
                    element.xpath('.//img/@src[contains(., ".webp") or contains(., ".jpg") or contains(., ".png")]'))
        
        if _i3:
            _i4 = _i3[0]
            if _i4.startswith('/'):
                _i4 = 'https://feikuai.tv' + _i4
            return _i4
        return ''

    def _get_desc(self, root):
        try:
            _d3 = root.xpath('//div[contains(@class, "module-info-introduction-content")]//text()')
            _d4 = '\n'.join([x.strip() for x in _d3 if x.strip()]) if _d3 else ''
            return _d4
        except Exception:
            return ''

    def _parse_dom(self, rsp):
        try:
            _p4 = etree.HTMLParser(encoding='utf-8', recover=True, remove_blank_text=True)
            if hasattr(rsp, 'content'):
                return etree.HTML(rsp.content, parser=_p4)
            return etree.HTML(rsp.text.encode('utf-8', errors='ignore'), parser=_p4)
        except Exception:
            return None

    def _build_url(self, tid, pg, ext):
        _a1 = (ext.get('area') or ext.get('1') or '').strip()
        _c3 = (ext.get('class') or ext.get('3') or '').strip()
        _y1 = (ext.get('year') or ext.get('11') or '').strip()
        
        _e2 = quote_plus(_a1) if _a1 else ''
        _e3 = quote_plus(_c3) if _c3 else ''
        _p5 = '' if str(pg) in ('', '1') else str(pg)
        return f'https://feikuai.tv/vodshow/{tid}-{_e2}--{_e3}-----{_p5}---{_y1}.html'

    def _get_sources(self, root, tid):
        _f2 = []
        _l4 = []
        
        self._get_normal_sources(root, tid, _f2, _l4)
        
        self._get_pan_sources(root, tid, _f2, _l4)
        
        return _f2, _l4

    def _get_normal_sources(self, root, tid, playFrom, playList):
        try:
            _e4 = root.xpath('//div[contains(@class, "module-play-list")]//a[contains(@href, "/vodplay/")] | //ul[contains(@class, "module-play-list")]//a[contains(@href, "/vodplay/")]')
            _g1 = {}
            for _a4 in _e4:
                try:
                    _h8 = _a4.xpath('./@href')[0] if _a4.xpath('./@href') else ''
                    _m3 = re.search(r'/vodplay/(\d+)-(\d+)-(\d+)\.html', _h8)
                    if not _m3:
                        continue
                    _v8, _s5, _e5 = _m3.groups()
                    if _v8 != tid:
                        continue
                    _n2 = ''.join(_a4.xpath('string(.)')).strip()
                    if not _n2 or _n2 in ('立即播放', '收藏', '追更', '分享', '报错', '下载'):
                        continue
                    if _s5 not in _g1:
                        _g1[_s5] = []
                    _g1[_s5].append(f"{_n2}${_v8}-{_s5}-{_e5}")
                except Exception:
                    continue
            
            _o1 = []
            for _b1 in root.xpath('//div[contains(@class, "his-tab-list")]'):
                try:
                    _f3 = _b1.xpath('.//a[contains(@href, "/vodplay/")][1]/@href')
                    if _f3:
                        _m4 = re.search(r'/vodplay/(\d+)-(\d+)-(\d+)\.html', _f3[0])
                        if _m4:
                            _s6 = _m4.group(2)
                            if _s6 not in _o1:
                                _o1.append(_s6)
                except Exception:
                    continue
            
            _l5 = [x.strip() for x in root.xpath('//div[contains(@class, "module-tab-items-box")]//div[contains(@class, "module-tab-item")]//span/text()') if x.strip()]
            
            for _i5, _s7 in enumerate(_o1):
                _s8 = _l5[_i5] if _i5 < len(_l5) else f"线路{_s7}"
                playFrom.append(_s8)
                playList.append('#'.join(_g1.get(_s7, [])))
        except Exception:
            pass

    def _get_pan_sources(self, root, tid, playFrom, playList):
        try:
            _d5 = root.xpath('//div[@id="download-list"]')
            if not _d5:
                return
                
            _t5 = root.xpath('//div[@id="y-downList"]//div[contains(@class, "module-tab-item")]')
            
            _p6 = {
                '百度网盘': '百度网盘',
                '夸克网盘': '夸克网盘',
                '迅雷云盘': '迅雷云盘',
                '阿里云盘': '阿里云盘',
                '天翼云盘': '天翼云盘',
                'UC网盘': 'UC网盘',
                '115网盘': '115网盘',
                '移动云盘': '移动云盘'
            }
            
            for _t6 in _t5:
                try:
                    _s9 = ''.join(_t6.xpath('.//span/text()')).strip()
                    if not _s9 or _s9 == '磁力链接':
                        continue
                    
                    _s10 = _p6.get(_s9, _s9)
                    
                    _t7 = _t6.xpath('./@data-index')
                    if not _t7:
                        continue
                    _t8 = _t7[0]
                    
                    _c4 = root.xpath(f'//div[@id="tab-content-{_t8}"]//div[@class="module-row-info"]//a')
                    
                    _e6 = []
                    for _i6, _l6 in enumerate(_c4, 1):
                        try:
                            _u6 = _l6.xpath('./@href')
                            if not _u6:
                                continue
                            _u7 = _u6[0].strip()
                            
                            _h9 = _l6.xpath('.//h4/text()')
                            if _h9:
                                _e7 = _h9[0].strip()
                                _e7 = re.sub(r'@一键搜片-\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}$', '', _e7).strip()
                            else:
                                _e7 = f"资源{_i6}"
                            
                            _u8 = self._process_url(_u7)
                            if _u8:
                                _e6.append(f"{_e7}${_u8}")
                        except Exception:
                            continue
                    
                    if _e6:
                        playFrom.append(_s10)
                        playList.append('#'.join(_e6))
                except Exception:
                    continue
        except Exception:
            pass

    def _process_url(self, raw_url):
        try:
            if not raw_url:
                return None
            
            if not raw_url.startswith(('http://', 'https://')):
                if raw_url.startswith('//'):
                    _u9 = 'https:' + raw_url
                elif raw_url.startswith('/'):
                    _u9 = 'https://feikuai.tv' + raw_url
                else:
                    return None
            else:
                _u9 = raw_url
            
            return f"push://{_u9}"
                
        except Exception:
            return None

    def _decode_str(self, raw, encrypt):
        try:
            if not raw:
                return ''
            _e8 = str(encrypt or '0').strip()
            if _e8 == '1':
                _t9 = unquote(raw)
            elif _e8 == '2':
                try:
                    _b2 = base64.b64decode(raw + '===')
                    _t9 = unquote(_b2.decode('utf-8', errors='ignore'))
                except Exception:
                    _t9 = unquote(raw)
            else:
                _t9 = raw
                
            _t9 = re.sub(r'%u([0-9a-fA-F]{4})',
                         lambda _m5: chr(int(_m5.group(1), 16)), _t9)
            return _t9
        except Exception:
            return raw
    
    def _get_header(self):
        return {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive"
        }
    
    def localProxy(self, params):
        pass

    def isVideoFormat(self, url):
        return url

    def manualVideoCheck(self):
        return []

    def destroy(self):
        pass
