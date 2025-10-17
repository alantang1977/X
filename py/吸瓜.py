# -*- coding: utf-8 -*-
# by @嗷呜
import json
import random
import re
import sys
import threading
import time
from base64 import b64decode, b64encode
from urllib.parse import urlparse
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from pyquery import PyQuery as pq
sys.path.append('..')
from base.spider import Spider


class Spider(Spider):

    def init(self, extend=""):
        try:self.proxies = json.loads(extend).get('proxy',{})
        except:self.proxies = {}
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
            'sec-ch-ua-platform': '"macOS"',
            'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="134", "Google Chrome";v="134"',
            'DNT': '1',
            'sec-ch-ua-mobile': '?0',
            'Origin': '',
            'Sec-Fetch-Site': 'cross-site',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }
        self.host=self.host_late(self.gethosts())
        self.headers.update({'Origin': self.host, 'Referer': f"{self.host}/"})
        self.getcnh()
        pass

    def getName(self):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    def homeContent(self, filter):
        data=self.getpq(requests.get(self.host, headers=self.headers,proxies=self.proxies).text)
        result = {}
        classes = []
        for k in list(data('.navbar-nav.mr-auto').children('li').items())[1:-3]:
            if k('ul'):
                for j in k('ul li').items():
                    classes.append({
                        'type_name': j('a').text(),
                        'type_id': j('a').attr('href').strip()+'/',
                    })
            else:
                classes.append({
                    'type_name': k('a').text(),
                    'type_id': k('a').attr('href').strip()+'/',
                })
        result['class'] = classes
        result['list'] = self.getlist(data('#index article a'))
        return result

    def getcnh(self):
        data=self.getpq(requests.get(f"{self.host}/homeway.html", headers=self.headers,proxies=self.proxies).text)
        url=data('.post-content[itemprop="articleBody"] blockquote p').eq(0)('a').attr('href')
        parsed_url = urlparse(url)
        host = parsed_url.scheme + "://" + parsed_url.netloc
        self.setCache('host_51cn',host)

    def homeVideoContent(self):
        pass

    def categoryContent(self, tid, pg, filter, extend):
        if '@folder' in tid:
            id=tid.replace('@folder','')
            videos=self.getfod(id)
        else:
            data=self.getpq(requests.get(f"{self.host}{tid}{pg}", headers=self.headers,proxies=self.proxies).text)
            videos=self.getlist(data('#archive article a'),tid)
        result = {}
        result['list'] = videos
        result['page'] = pg
        result['pagecount'] = 1 if '@folder' in tid else 99999
        result['limit'] = 90
        result['total'] = 999999
        return result

    def getfod(self, id):
        url = f"{self.host}{id}"
        data = self.getpq(requests.get(url, headers=self.headers, proxies=self.proxies).text)
        vdata=data('.post-content[itemprop="articleBody"]')
        r=['.txt-apps','.line','blockquote','.tags','.content-tabs']
        for i in r:vdata.remove(i)
        p=vdata('p')
        videos=[]
        for i,x in enumerate(vdata('h2').items()):
            c=i*2
            videos.append({
                'vod_id': p.eq(c)('a').attr('href'),
                'vod_name': p.eq(c).text(),
                'vod_pic': f"{self.getProxyUrl()}&url={p.eq(c+1)('img').attr('data-xkrkllgl')}&type=img",
                'vod_remarks':x.text()
                })
        return videos

    def detailContent(self, ids):
        url=f"{self.host}{ids[0]}"
        data=self.getpq(requests.get(url, headers=self.headers,proxies=self.proxies).text)
        vod = {'vod_play_from': '老僧酿酒、名妓读经'}
        try:
            clist = []
            if data('.tags .keywords a'):
                for k in data('.tags .keywords a').items():
                    title = k.text()
                    href = k.attr('href')
                    clist.append('[a=cr:' + json.dumps({'id': href, 'name': title}) + '/]' + title + '[/a]')
            vod['vod_content'] = ' '.join(clist)
        except:
            vod['vod_content'] = data('.post-title').text()
        try:
            plist=[]
            if data('.dplayer'):
                for c, k in enumerate(data('.dplayer').items(), start=1):
                    config = json.loads(k.attr('data-config'))
                    plist.append(f"视频{c}${config['video']['url']}")
            vod['vod_play_url']='#'.join(plist)
        except:
            vod['vod_play_url']=f"可能没有视频${url}"
        return {'list':[vod]}

    def searchContent(self, key, quick, pg="1"):
        data=self.getpq(requests.get(f"{self.host}/search/{key}/{pg}", headers=self.headers,proxies=self.proxies).text)
        return {'list':self.getlist(data('#archive article a')),'page':pg}

    def playerContent(self, flag, id, vipFlags):
        p=1
        if '.m3u8' in id:p,id=0,self.proxy(id)
        return  {'parse': p, 'url': id, 'header': self.headers}

    def localProxy(self, param):
        if param.get('type') == 'img':
            res=requests.get(param['url'], headers=self.headers, proxies=self.proxies, timeout=10)
            return [200,res.headers.get('Content-Type'),self.aesimg(res.content)]
        elif param.get('type') == 'm3u8':return self.m3Proxy(param['url'])
        else:return self.tsProxy(param['url'])

    def proxy(self, data, type='m3u8'):
        if data and len(self.proxies):return f"{self.getProxyUrl()}&url={self.e64(data)}&type={type}"
        else:return data

    def m3Proxy(self, url):
        url=self.d64(url)
        ydata = requests.get(url, headers=self.headers, proxies=self.proxies, allow_redirects=False)
        print(ydata.text)
        data = ydata.content.decode('utf-8')
        if ydata.headers.get('Location'):
            url = ydata.headers['Location']
            data = requests.get(url, headers=self.headers, proxies=self.proxies).content.decode('utf-8')
        lines = data.strip().split('\n')
        last_r = url[:url.rfind('/')]
        parsed_url = urlparse(url)
        durl = parsed_url.scheme + "://" + parsed_url.netloc
        iskey=True
        for index, string in enumerate(lines):
            if iskey and 'URI' in string:
                pattern = r'URI="([^"]*)"'
                match = re.search(pattern, string)
                if match:
                    lines[index] = re.sub(pattern, f'URI="{self.proxy(match.group(1), "mkey")}"', string)
                    iskey=False
                    continue
            if '#EXT' not in string:
                if 'http' not in string:
                    domain = last_r if string.count('/') < 2 else durl
                    string = domain + ('' if string.startswith('/') else '/') + string
                lines[index] = self.proxy(string, string.split('.')[-1].split('?')[0])
        data = '\n'.join(lines)
        return [200, "application/vnd.apple.mpegur", data]

    def tsProxy(self, url):
        url = self.d64(url)
        data = requests.get(url, headers=self.headers, proxies=self.proxies, stream=True)
        return [200, data.headers['Content-Type'], data.content]

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

    def gethosts(self):
        url='https://51cg.fun'
        curl=self.getCache('host_51cn')
        if curl:
            try:
                data=self.getpq(requests.get(curl, headers=self.headers, proxies=self.proxies).text)('a').attr('href')
                if data:
                    parsed_url = urlparse(data)
                    url = parsed_url.scheme + "://" + parsed_url.netloc
            except:
                pass
        try:
            html = self.getpq(requests.get(url, headers=self.headers, proxies=self.proxies).text)
            html_pattern = r"Base64\.decode\('([^']+)'\)"
            html_match = re.search(html_pattern, html('script').eq(-1).text(), re.DOTALL)
            if not html_match:raise Exception("未找到html")
            html = self.getpq(b64decode(html_match.group(1)).decode())('script').eq(-4).text()
            return self.hstr(html)
        except Exception as e:
            self.log(f"获取: {str(e)}")
            return ""

    def hstr(self, html):
        pattern = r"(backupLine\s*=\s*\[\])\s+(words\s*=)"
        replacement = r"\1, \2"
        html = re.sub(pattern, replacement, html)
        data = f"""
        var Vx = {{
            range: function(start, end) {{
                const result = [];
                for (let i = start; i < end; i++) {{
                    result.push(i);
                }}
                return result;
            }},

            map: function(array, callback) {{
                const result = [];
                for (let i = 0; i < array.length; i++) {{
                    result.push(callback(array[i], i, array));
                }}
                return result;
            }}
        }};

        Array.prototype.random = function() {{
            return this[Math.floor(Math.random() * this.length)];
        }};

        var location = {{
            protocol: "https:"
        }};

        function executeAndGetResults() {{
            var allLines = lineAry.concat(backupLine);
            var resultStr = JSON.stringify(allLines);
            return resultStr;
        }};
        {html}
        executeAndGetResults();
        """
        return self.p_qjs(data)

    def p_qjs(self, js_code):
        try:
            from com.whl.quickjs.wrapper import QuickJSContext
            ctx = QuickJSContext.create()
            result_json = ctx.evaluate(js_code)
            ctx.destroy()
            return json.loads(result_json)

        except Exception as e:
            self.log(f"执行失败: {e}")
            return []

    def get_domains(self):
        html = self.getpq(requests.get("https://51cg.fun", headers=self.headers,proxies=self.proxies).text)
        html_pattern = r"Base64\.decode\('([^']+)'\)"
        html_match = re.search(html_pattern, html('script').eq(-1).text(), re.DOTALL)
        if not html_match:
            raise Exception("未找到html")
        html = b64decode(html_match.group(1)).decode()
        words_pattern = r"words\s*=\s*'([^']+)'"
        words_match = re.search(words_pattern, html, re.DOTALL)
        if not words_match:
            raise Exception("未找到words")
        words = words_match.group(1).split(',')
        main_pattern = r"lineAry\s*=.*?words\.random\(\)\s*\+\s*'\.([^']+)'"
        domain_match = re.search(main_pattern, html, re.DOTALL)
        if not domain_match:
            raise Exception("未找到主域名")
        domain_suffix = domain_match.group(1)
        domains = []
        for _ in range(3):
            random_word = random.choice(words)
            domain = f"https://{random_word}.{domain_suffix}"
            domains.append(domain)
        return domains

    def host_late(self, url_list):
        if isinstance(url_list, str):
            urls = [u.strip() for u in url_list.split(',')]
        else:
            urls = url_list

        if len(urls) <= 1:
            return urls[0] if urls else ''

        results = {}
        threads = []

        def test_host(url):
            try:
                start_time = time.time()
                response = requests.head(url,headers=self.headers,proxies=self.proxies,timeout=1.0, allow_redirects=False)
                delay = (time.time() - start_time) * 1000
                results[url] = delay
            except Exception as e:
                results[url] = float('inf')

        for url in urls:
            t = threading.Thread(target=test_host, args=(url,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        return min(results.items(), key=lambda x: x[1])[0]

    def getlist(self,data,tid=''):
        videos = []
        l='/mrdg' in tid
        for k in data.items():
            a=k.attr('href')
            b=k('h2').text()
            c=k('span[itemprop="datePublished"]').text()
            if a and b and c:
                videos.append({
                    'vod_id': f"{a}{'@folder' if l else ''}",
                    'vod_name': b.replace('\n', ' '),
                    'vod_pic': self.getimg(k('script').text()),
                    'vod_remarks': c,
                    'vod_tag':'folder' if l else '',
                    'style': {"type": "rect", "ratio": 1.33}
                })
        return videos

    def getimg(self, text):
        match = re.search(r"loadBannerDirect\('([^']+)'", text)
        if match:
            url = match.group(1)
            return f"{self.getProxyUrl()}&url={url}&type=img"
        else:
            return ''

    def aesimg(self, word):
        key = b'f5d965df75336270'
        iv = b'97b60394abc2fbe1'
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = unpad(cipher.decrypt(word), AES.block_size)
        return decrypted

    def getpq(self, data):
        try:
            return pq(data)
        except Exception as e:
            print(f"{str(e)}")
            return pq(data.encode('utf-8'))
