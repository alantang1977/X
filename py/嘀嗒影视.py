
# -*- coding: utf-8 -*-
# FongMi/TVBox Python Spider - 嘀嗒影视 didahd.xyz
import re, json, html, base64, binascii, hashlib, time
from urllib.parse import urljoin, quote, unquote
try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import unpad
except Exception:
    AES = None
    def unpad(data, bs): return data

try:
    from base.spider import Spider as BaseSpider
except Exception:
    class BaseSpider(object):
        def fetch(self, url, headers=None, timeout=15, **kwargs):
            import requests
            return requests.get(url, headers=headers, timeout=timeout, verify=False)
        def post(self, url, headers=None, data=None, timeout=15, **kwargs):
            import requests
            return requests.post(url, headers=headers, data=data, timeout=timeout, verify=False)

class Spider(BaseSpider):
    def __init__(self):
        self.host = 'https://www.didahd.xyz'
        self.headers = {
            'User-Agent':'Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36',
            'Referer':self.host + '/',
            'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
        self.classes = [
            {'type_id':'1','type_name':'电影'},
            {'type_id':'2','type_name':'电视剧'},
            {'type_id':'3','type_name':'纪录片'},
            {'type_id':'4','type_name':'动漫'},
            {'type_id':'5','type_name':'综艺'}
        ]

    def getName(self): return '嘀嗒影视'
    def getDependence(self): return []
    def init(self, extend=''): pass
    def isVideoFormat(self, url): return bool(re.search(r'\.(m3u8|mp4|flv|mkv)(\?|$)', str(url), re.I))
    def manualVideoCheck(self): return True
    def action(self, action): return None
    def destroy(self): pass
    def liveContent(self, url): return {'list': []}
    def localProxy(self, param): return [404, 'text/plain', 'Not Found']

    def log(self, msg):
        try: print('[嘀嗒影视] ' + str(msg))
        except Exception: pass

    def getHtml(self, url, referer=None):
        if not url.startswith('http'): url = urljoin(self.host, url)
        h = dict(self.headers)
        if referer: h['Referer'] = referer
        try:
            r = self.fetch(url, headers=h, timeout=15)
            if hasattr(r, 'content'):
                enc = getattr(r, 'encoding', None) or 'utf-8'
                return r.content.decode(enc, 'ignore')
            return getattr(r, 'text', '') or ''
        except Exception as e:
            self.log('请求失败 %s %s' % (url, e)); return ''

    def postHtml(self, url, data, referer=None):
        if not url.startswith('http'): url = urljoin(self.host, url)
        h = dict(self.headers)
        if referer: h['Referer'] = referer
        h['Content-Type'] = 'application/x-www-form-urlencoded'
        try:
            if hasattr(super(), 'post'):
                r = self.post(url, headers=h, data=data, timeout=15)
            else:
                raise Exception('no post')
            if hasattr(r, 'content'):
                enc = getattr(r, 'encoding', None) or 'utf-8'
                return r.content.decode(enc, 'ignore')
            return getattr(r, 'text', '') or ''
        except Exception as e:
            self.log('POST失败 %s %s' % (url, e)); return ''

    def clean(self, s):
        s = html.unescape(str(s or ''))
        s = re.sub(r'<script[\s\S]*?</script>|<style[\s\S]*?</style>', ' ', s, flags=re.I)
        s = re.sub(r'<[^>]+>', ' ', s)
        return re.sub(r'\s+', ' ', s).strip()

    def fix(self, u):
        if not u: return ''
        u = html.unescape(str(u)).replace('\\/', '/').strip()
        return urljoin(self.host, u)

    def homeContent(self, filter):
        return {'class': self.classes, 'filters': self.makeFilters() if filter else {}}

    def makeFilters(self):
        years = [{'n':'全部','v':''}] + [{'n':str(y),'v':str(y)} for y in range(2026, 2009, -1)]
        areas = [{'n':'全部','v':''}] + [{'n':x,'v':x} for x in ['大陆','香港','台湾','美国','日本','韩国','英国','法国','德国','泰国','印度','其它']]
        langs = [{'n':'全部','v':''}] + [{'n':x,'v':x} for x in ['国语','英语','粤语','韩语','日语','泰语','其它']]
        bys = [{'n':'时间','v':'time'},{'n':'人气','v':'hits'},{'n':'评分','v':'score'}]
        letters = [{'n':'全部','v':''}] + [{'n':c,'v':c} for c in list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')] + [{'n':'0-9','v':'0-9'}]
        fs = [{'key':'area','name':'地区','value':areas},{'key':'year','name':'年份','value':years},{'key':'lang','name':'语言','value':langs},{'key':'letter','name':'字母','value':letters},{'key':'by','name':'排序','value':bys}]
        return {c['type_id']:fs for c in self.classes}

    def homeVideoContent(self):
        return {'list': self.parseList(self.getHtml(self.host + '/'))[:30]}

    def buildCategoryUrl(self, tid, pg, extend):
        pg = str(pg or '1'); ext = extend or {}
        area = str(ext.get('area','') or '')
        by = str(ext.get('by','') or '')
        lang = str(ext.get('lang','') or '')
        letter = str(ext.get('letter','') or '')
        year = str(ext.get('year','') or '')
        if any([area, by, lang, letter, year]):
            # 真实 href 是 12 段 join：tid-area-by-lang-空-空-空-空-pg-空-空-year
            # 例：/show/1-----------2025.html -> /show/1--------2---2025.html
            p = '' if pg == '1' else pg
            fields = [str(tid), area, by, lang, '', '', '', '', p, '', '', year]
            return self.host + '/show/' + '-'.join(fields) + '.html'
        if pg == '1': return self.host + '/type/%s.html' % tid
        return self.host + '/type/%s-%s.html' % (tid, pg)

    def isNoResultPage(self, txt):
        return bool(re.search(r'没有找到您想要的结果|没有找到.*?结果|搜索无结果|暂无数据', txt or '', re.I))

    def categoryContent(self, tid, pg, filter, extend):
        url = self.buildCategoryUrl(tid, pg, extend or {})
        txt = self.getHtml(url, self.host + '/')
        vods = [] if self.isNoResultPage(txt) else self.parseList(txt)
        return {'list':vods, 'page':int(pg or 1), 'pagecount':999999 if vods else int(pg or 1), 'limit':len(vods), 'total':999999 if vods else 0}

    def parseList(self, txt):
        vods, seen = [], set()
        blocks = re.findall(r'(<a\b(?=[^>]*class=["\'][^"\']*myui-vodlist__thumb[^"\']*["\'])(?=[^>]*href=["\'][^"\']*/detail/\d+\.html["\'])[\s\S]*?</a>)', txt or '', re.I)
        if not blocks:
            blocks = re.findall(r'(<div\b[^>]*class=["\'][^"\']*myui-vodlist__box[^"\']*["\'][\s\S]*?</div>\s*</div>)', txt or '', re.I)
        if not blocks:
            blocks = re.findall(r'(<a\b[^>]+href=["\'][^"\']*/detail/\d+\.html["\'][\s\S]*?</a>)', txt or '', re.I)
        for b in blocks:
            try:
                hm = re.search(r'href=["\']([^"\']*/detail/(\d+)\.html)["\']', b, re.I)
                if not hm: continue
                vid = self.fix(hm.group(1))
                if vid in seen: continue
                seen.add(vid)
                tm = re.search(r'title=["\']([^"\']+)["\']', b, re.I) or re.search(r'alt=["\']([^"\']+)["\']', b, re.I) or re.search(r'<h4[^>]*>[\s\S]*?<a[^>]*>([\s\S]*?)</a>', b, re.I)
                title = self.clean(tm.group(1)) if tm else ''
                pm = re.search(r'(?:data-original|data-src)=["\']([^"\']+)["\']', b, re.I) or re.search(r'<img[^>]+src=["\']((?!/template/|/static/)[^"\']+)["\']', b, re.I)
                rm = re.search(r'<span[^>]*class=["\'][^"\']*pic-text[^"\']*["\'][^>]*>([\s\S]*?)</span>', b, re.I)
                if title:
                    vods.append({'vod_id':vid,'vod_name':title,'vod_pic':self.fix(pm.group(1)) if pm else '', 'vod_remarks':self.clean(rm.group(1)) if rm else ''})
            except Exception as e:
                self.log('列表单条失败 %s' % e)
        return vods

    def detailContent(self, ids):
        url = ids[0]
        txt = self.getHtml(url, self.host + '/')
        mt = re.search(r'<h1[^>]*class=["\'][^"\']*title[^"\']*["\'][^>]*>([\s\S]*?)</h1>', txt, re.I) or re.search(r'<title>(.*?)\s*-\s*嘀嗒影视', txt, re.S)
        title = self.clean(mt.group(1)) if mt else ''
        pic_block = re.search(r'<a[^>]*class=["\'][^"\']*myui-vodlist__thumb[^"\']*picture[^"\']*["\'][\s\S]*?</a>', txt, re.I)
        picm = None
        if pic_block:
            pb = pic_block.group(0)
            picm = re.search(r'(?:data-original|data-src)=["\']([^"\']+)["\']', pb, re.I) or re.search(r'<img[^>]+src=["\']((?!/template/|/static/)[^"\']+)["\']', pb, re.I)
        def info(name):
            m = re.search(r'<span[^>]*class=["\'][^"\']*text-muted[^"\']*["\'][^>]*>%s[:：]</span>([\s\S]*?)(?:<span[^>]*class=["\'][^"\']*split-line|</p>)' % name, txt, re.I)
            return self.clean(m.group(1)) if m else ''
        cm = re.search(r'剧情简介[:：]</span>[\s\S]*?<span>([\s\S]*?)</span>', txt, re.I) or re.search(r'剧情简介[:：]</span>([\s\S]*?)<br', txt, re.I)
        content = self.clean(cm.group(1)) if cm else ''
        tab_area = re.search(r'<ul[^>]*class=["\'][^"\']*nav-tabs[^"\']*active[^"\']*["\'][^>]*>([\s\S]*?)</ul>', txt, re.I)
        names = [self.clean(x[1]) for x in re.findall(r'href=["\']#playlist(\d+)["\'][^>]*>([\s\S]*?)</a>', tab_area.group(1) if tab_area else '', re.I)]
        groups = []
        for m in re.finditer(r'<div[^>]*id=["\']playlist(\d+)["\'][^>]*>([\s\S]*?)(?=<div[^>]*id=["\']playlist\d+["\']|</div>\s*</div>\s*<!--|<!-- 下载地址|$)', txt, re.I):
            groups.append(m.group(2))
        play_from, play_url = [], []
        for i,g in enumerate(groups):
            eps, used = [], set()
            for h,n in re.findall(r'<a\b[^>]+href=["\']([^"\']*/play/\d+-\d+-\d+\.html)["\'][^>]*>([\s\S]*?)</a>', g, re.I):
                fu = self.fix(h)
                if fu in used: continue
                used.add(fu)
                name = self.clean(n) or ('第%d集' % (len(eps)+1))
                eps.append(name + '$' + fu)
            if eps:
                line = names[i] if i < len(names) and names[i] else '线路%d' % (i+1)
                if re.search(r'网盘|云盘|夸克|百度|UC|PikPak|阿里', line, re.I):
                    continue
                play_from.append(line); play_url.append('#'.join(eps))
        if not play_url:
            eps=[]
            for h,n in re.findall(r'href=["\']([^"\']*/play/\d+-\d+-\d+\.html)["\'][^>]*>([\s\S]*?)</a>', txt, re.I):
                item=(self.clean(n) or '播放') + '$' + self.fix(h)
                if item not in eps: eps.append(item)
            if eps: play_from, play_url = ['默认'], ['#'.join(eps)]
        vod = {'vod_id':url,'vod_name':title,'vod_pic':self.fix(picm.group(1)) if picm else '', 'type_name':info('分类'), 'vod_year':info('年份')[:4], 'vod_area':info('地区'), 'vod_remarks':info('更新时间'), 'vod_actor':info('主演'), 'vod_director':info('导演'), 'vod_content':content, 'vod_play_from':'$$$'.join(play_from), 'vod_play_url':'$$$'.join(play_url)}
        return {'list':[vod]}

    def searchContent(self, key, quick, pg='1'):
        url = self.host + '/search/%s-------------.html' % quote(key)
        txt = self.getHtml(url, self.host + '/')
        vods = [] if self.isNoResultPage(txt) else self.parseList(txt)
        return {'list':vods, 'page':int(pg or 1), 'pagecount':1, 'limit':len(vods), 'total':len(vods)}

    def decodePlayerUrl(self, data):
        url = data.get('url','') if isinstance(data, dict) else ''
        enc = str(data.get('encrypt','0')) if isinstance(data, dict) else '0'
        try:
            if enc == '1': url = unquote(url)
            elif enc == '2': url = unquote(base64.b64decode(url).decode('utf-8','ignore'))
            elif enc == '3' and re.fullmatch(r'[0-9a-fA-F]+', url or ''):
                # didahd 的 artplayer 线路要求把 hex 原文作为 url 参数，解码值仅作备用
                return url
        except Exception as e:
            self.log('播放器URL解码失败 %s' % e)
        return url.replace('\\/', '/')

    def decodeArtUrl(self, cipher_text, timestamp):
        if not AES or not cipher_text or not timestamp: return ''
        try:
            seed = str(timestamp) + 'RY7e48naFXPsLJC'
            md5 = hashlib.md5(seed.encode('utf-8')).hexdigest()
            key = md5[16:32].encode('utf-8')
            iv = md5[0:16].encode('utf-8')
            raw = cipher_text.replace('\\/', '/')
            dec = AES.new(key, AES.MODE_CBC, iv).decrypt(base64.b64decode(raw))
            return unpad(dec, 16).decode('utf-8', 'ignore')
        except Exception as e:
            self.log('artplayer AES解密失败 %s' % e); return ''
    def parseSmartPlay(self, txt, timestamp, referer):
        try:
            if 'isSmartPlay' not in txt or 'true' not in txt[:8000]: return ''
            vm = re.search(r'const\s+playPageUrl\s*=\s*["\']([^"\']+)', txt, re.I)
            cm = re.search(r'const\s+secretKeySeed\s*=\s*["\']([^"\']+)', txt, re.I)
            if not vm or not cm or not timestamp: return ''
            api = 'https://hd.ticktockwow.com/smartplay-cache/api/webvideo_ty.php'
            t = int(time.time())
            body = json.dumps({'vkey':vm.group(1), 'code':cm.group(1), 't':t, 'signature':hashlib.md5(str(t).encode('utf-8')).hexdigest()})
            h = dict(self.headers)
            h.update({'Referer':self.host + '/static/player/artplayer/', 'Origin':self.host, 'Content-Type':'application/json', 'Accept':'application/json,text/plain,*/*'})
            r = self.post(api, headers=h, data=body, timeout=15)
            text = r.content.decode(getattr(r, 'encoding', None) or 'utf-8', 'ignore') if hasattr(r, 'content') else (getattr(r, 'text', '') or '')
            js = json.loads(text)
            enc = (js or {}).get('url','')
            u = self.decodeArtUrl(enc, timestamp)
            u = u.replace('\\/', '/') if u else ''
            return u if self.isVideoFormat(u) else ''
        except Exception as e:
            self.log('smartplay解析失败 %s' % e); return ''

    def makePlayHeader(self, url):
        # 播放端优先“空防盗链头”：不主动带 Referer/Origin，避免第三方 CDN 因来源不匹配而限速/卡顿。
        # 实测 didahd 的 didahd secure、天翼云、快手、超星、小红书分片均可用 UA-only；p.ananas 空 UA 可能 403，所以保留 UA。
        h = {'User-Agent':self.headers['User-Agent']}
        try:
            if re.search(r'\.m3u8(?:\?|$)|qd-tjwq-person\.tjtele\.com|ctyunxs\.cn|PERSONCLOUD|video_m3u8/secure\.php', url, re.I):
                r = self.fetch(url, headers=h, timeout=8)
                txt = r.content[:2048].decode('utf-8', 'ignore') if hasattr(r, 'content') else (getattr(r, 'text', '') or '')[:2048]
                # 只做健康探测，不再返回 Referer/Origin；减少 EXO 分片请求卡顿。
                if '#EXTM3U' not in txt and txt:
                    self.log('m3u8探测异常片段 ' + txt[:60].replace('\n',' '))
        except Exception as e:
            self.log('播放头检测失败 %s' % e)
        return h

    def parseArtPlayer(self, raw_url, referer, next_url=''):
        if not raw_url or re.match(r'https?://(?:pan\.quark|pan\.baidu|www\.aliyundrive|drive\.uc)', raw_url, re.I): return ''
        art = self.host + '/static/player/artplayer/?url=' + quote(raw_url, safe='')
        if next_url: art += '&next=' + quote(next_url, safe='')
        txt = self.getHtml(art, referer)
        ts = re.search(r'const\s+timestamp\s*=\s*["\']([^"\']+)', txt, re.I)
        if not ts: return ''
        sm = self.parseSmartPlay(txt, ts.group(1), referer)
        if sm: return sm
        qm = re.search(r'const\s+qualities\s*=\s*(\[[\s\S]*?\]);', txt, re.I)
        if not qm: return ''
        try:
            arr = json.loads(qm.group(1))
            for it in arr:
                u = self.decodeArtUrl(it.get('url',''), ts.group(1))
                if u:
                    u = self.fix(u)
                    if self.isVideoFormat(u): return u
        except Exception as e:
            self.log('artplayer qualities解析失败 %s' % e)
        return ''


    def playerContent(self, flag, id, vipFlags):
        if self.isVideoFormat(id): return {'parse':0, 'url':id, 'header':self.makePlayHeader(id)}
        txt = self.getHtml(id, self.host + '/')
        data = None
        m = re.search(r'var\s+player_[a-zA-Z0-9_]+\s*=\s*(\{[\s\S]*?\})\s*</script>', txt, re.I)
        if m:
            try: data = json.loads(m.group(1))
            except Exception as e: self.log('播放器JSON失败 %s' % e)
        url = self.decodePlayerUrl(data or {})
        if self.isVideoFormat(url):
            fu = self.fix(url)
            return {'parse':0, 'url':fu, 'header':self.makePlayHeader(fu)}
        final = self.parseArtPlayer(url, id, (data or {}).get('link_next',''))
        if final:
            return {'parse':0, 'url':final, 'header':self.makePlayHeader(final)}
        mm = re.search(r'(https?:\\?/\\?/[^"\']+?\.(?:m3u8|mp4)[^"\']*)', txt, re.I)
        if mm:
            u = self.fix(mm.group(1))
            return {'parse':0, 'url':u, 'header':self.makePlayHeader(u)}
        if url and re.match(r'https?://', url):
            return {'parse':1, 'url':url, 'header':self.headers}
        return {'parse':1, 'url':id, 'header':self.headers}

spider = Spider()