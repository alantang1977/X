# -*- coding: utf-8 -*-
# by @嗷呜
import json
import sys
from base64 import b64decode, b64encode
from pyquery import PyQuery as pq
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
sys.path.append('..')
from base.spider import Spider


class Spider(Spider):

    def init(self, extend="{}"):
        """初始化并加载代理配置
        示例：{"proxy":{"http":"http://127.0.0.1:10172","https":"https://127.0.0.1:10172"}}
        """
        # 解析代理配置
        self.proxies = {}
        if extend:
            try:
                config = json.loads(extend)
                self.proxies = config.get('proxy', {})
            except Exception as e:
                print(f"代理配置解析错误: {str(e)}")
        
        # 初始化会话（保持原始代码的会话模式）
        self.host = self.gethost()
        self.headers['referer'] = f'{self.host}/'
        self.session = self._create_session()
        self.session.headers.update(self.headers)
        self.session.proxies = self.proxies  # 仅在此处添加代理配置

    def _create_session(self):
        """创建带重试机制的会话，优化连接稳定性"""
        session = Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.3,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def getName(self):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        if hasattr(self, 'session'):
            self.session.close()

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'sec-ch-ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
        'sec-ch-ua-full-version-list': '"Not(A:Brand";v="99.0.0.0", "Google Chrome";v="133.0.6943.98", "Chromium";v="133.0.6943.98"',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }

    def homeContent(self, filter):
        result = {}
        cateManual = {
            "4K": "/4k",
            "国产": "two_click_/categories/chinese",
            "最新": "/newest",
            "最佳": "/best",
            "频道": "/channels",
            "类别": "/categories",
            "明星": "/pornstars"
        }
        classes = []
        filters = {}
        for k in cateManual:
            classes.append({
                'type_name': k,
                'type_id': cateManual[k]
            })
            if k !='4K':filters[cateManual[k]]=[{'key':'type','name':'类型','value':[{'n':'4K','v':'/4k'}]}]
        result['class'] = classes
        result['filters'] = filters
        return result

    def homeVideoContent(self):
        data = self.getpq()
        return {'list': self.getlist(data(".thumb-list--sidebar .thumb-list__item"))}

    def categoryContent(self, tid, pg, filter, extend):
        vdata = []
        result = {}
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        if tid in ['/4k', '/newest', '/best'] or 'two_click_' in tid:
            if 'two_click_' in tid: tid = tid.split('click_')[-1]
            data = self.getpq(f'{tid}{extend.get("type","")}/{pg}')
            vdata = self.getlist(data(".thumb-list--sidebar .thumb-list__item"))
        elif tid == '/channels':
            data = self.getpq(f'{tid}/{pg}')
            jsdata = self.getjsdata(data)
            for i in jsdata['channels']:
                vdata.append({
                    'vod_id': f"two_click_" + i.get('channelURL'),
                    'vod_name': i.get('channelName'),
                    'vod_pic': i.get('siteLogoURL'),
                    'vod_year': f'videos:{i.get("videoCount")}',
                    'vod_tag': 'folder',
                    'vod_remarks': f'subscribers:{i["subscriptionModel"].get("subscribers")}',
                    'style': {'ratio': 1.33, 'type': 'rect'}
                })
        elif tid == '/categories':
            result['pagecount'] = pg
            data = self.getpq(tid)
            self.cdata = self.getjsdata(data)
            for i in self.cdata['layoutPage']['store']['popular']['assignable']:
                vdata.append({
                    'vod_id': "one_click_" + i.get('id'),
                    'vod_name': i.get('name'),
                    'vod_pic': '',
                    'vod_tag': 'folder',
                    'style': {'ratio': 1.33, 'type': 'rect'}
                })
        elif tid == '/pornstars':
            data = self.getpq(f'{tid}/{pg}')
            pdata = self.getjsdata(data)
            for i in pdata['pagesPornstarsComponent']['pornstarListProps']['pornstars']:
                vdata.append({
                    'vod_id': f"two_click_" + i.get('pageURL'),
                    'vod_name': i.get('name'),
                    'vod_pic': i.get('imageThumbUrl'),
                    'vod_remarks': i.get('translatedCountryName'),
                    'vod_tag': 'folder',
                    'style': {'ratio': 1.33, 'type': 'rect'}
                })
        elif 'one_click' in tid:
            result['pagecount'] = pg
            tid = tid.split('click_')[-1]
            for i in self.cdata['layoutPage']['store']['popular']['assignable']:
                if i.get('id') == tid:
                    for j in i['items']:
                        vdata.append({
                            'vod_id': f"two_click_" + j.get('url'),
                            'vod_name': j.get('name'),
                            'vod_pic': j.get('thumb'),
                            'vod_tag': 'folder',
                            'style': {'ratio': 1.33, 'type': 'rect'}
                        })
        result['list'] = vdata
        return result

    def detailContent(self, ids):
        data = self.getpq(ids[0])
        link = data('link[rel="preload"][as="fetch"][crossorigin="true"]').attr('href')
        if  link:
            ggggx = f"多音画$666_{link}"
        else:
            ggggx = f"嗅探${ids[0]}"
        vn = data('meta[property="og:title"]').attr('content')
        dtext = data('#video-tags-list-container')
        href = dtext('a').attr('href')
        title = dtext('span[class*="body-bold-"]').eq(0).text()
        pdtitle = ''
        if href:
            pdtitle = '[a=cr:' + json.dumps({'id': 'two_click_' + href, 'name': title}) + '/]' + title + '[/a]'
        vod = {
            'vod_name': vn,
            'vod_director': pdtitle,
            'vod_remarks': data('.rb-new__info').text(),
            'vod_play_from': 'Xhamster',
            'vod_play_url': ggggx
        }
        return {'list': [vod]}

    def searchContent(self, key, quick, pg="1"):
        data = self.getpq(f'/search/{key}?page={pg}')
        return {'list': self.getlist(data(".thumb-list--sidebar .thumb-list__item")), 'page': pg}

    def playerContent(self, flag, id, vipFlags):
        # 完全保留原始代码的播放逻辑，不做本地代理转发
        p, url = 1, id
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.5410.0 Safari/537.36',
            'origin': self.host,
            'referer': f'{self.host}/',
        }
        if id.startswith("666_"):
            p, url = 0, id[4:]
        
        # 关键优化：将代理配置传递给播放器
        return {
            'parse': p, 
            'url': url, 
            'header': headers,
            'proxy': self.proxies  # 新增：将代理配置传递给播放器
        }

    # 禁用本地代理转发，保持和原始代码一致
    def localProxy(self, param):
        pass

    def gethost(self):
        try:
            # 使用带代理的会话获取主机
            response = self.session.get(
                'https://xhamster.com',
                headers=self.headers,
                allow_redirects=False,
                timeout=10
            )
            return response.headers.get('Location', 'https://xhamster.com')
        except Exception as e:
            print(f"获取主页失败: {str(e)}")
            return "https://xhamster.com"

    def e64(self, text):
        try:
            text_bytes = text.encode('utf-8')
            encoded_bytes = b64encode(text_bytes)
            return encoded_bytes.decode('utf-8')
        except Exception as e:
            print(f"Base64编码错误: {str(e)}")
            return ""

    def d64(self, encoded_text):
        try:
            encoded_bytes = encoded_text.encode('utf-8')
            decoded_bytes = b64decode(encoded_bytes)
            return decoded_bytes.decode('utf-8')
        except Exception as e:
            print(f"Base64解码错误: {str(e)}")
            return ""

    def getlist(self, data):
        vlist = []
        for i in data.items():
            vlist.append({
                'vod_id': i('.role-pop').attr('href'),
                'vod_name': i('.video-thumb-info a').text(),
                'vod_pic': i('.role-pop img').attr('src'),
                'vod_year': i('.video-thumb-info .video-thumb-views').text().split(' ')[0],
                'vod_remarks': i('.role-pop div[data-role="video-duration"]').text(),
                'style': {'ratio': 1.33, 'type': 'rect'}
            })
        return vlist

    def getpq(self, path=''):
        h = '' if path.startswith('http') else self.host
        try:
            response = self.session.get(f'{h}{path}', timeout=10)
            response.raise_for_status()
            return pq(response.content)
        except Exception as e:
            print(f"页面请求错误({h}{path}): {str(e)}")
            return pq('')

    def getjsdata(self, data):
        vhtml = data("script[id='initials-script']").text()
        try:
            jst = json.loads(vhtml.split('initials=')[-1][:-1])
            return jst
        except Exception as e:
            print(f"解析js数据错误: {str(e)}")
            return {}
