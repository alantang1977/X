# -*- coding: utf-8 -*-
# by @嗷呜
import os,copy,requests,gzip,json,re,sys,time,uuid
from urllib.parse import unquote
from base64 import b64decode
from Crypto.Hash import SHA1, HMAC
from pyquery import PyQuery as pq
sys.path.append('..')
from base.spider import Spider


class Spider(Spider):

    def init(self, extend="{}"):
        config = json.loads(extend)
        self.process = None
        self.host = config['site']
        self.plp = config.get('plp', '')
        self.proxy = config.get('proxy', {})
        self.one_mark, gobool = self.start_proxy(config.get('cfgo'))
        self.cfproxy = 'http://127.0.0.1:12525?url=' if gobool else ''
        self.headers = {
            'referer': f'{self.host}',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0) Gecko/20100101 Firefox/140.0'
        }
        pass

    def getName(self):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    def copy_file(self, source_path):
        target_filename = os.path.basename(source_path)
        try:
            from java.io import File
            from java.lang import Class
            from java.nio.file import Files, Paths, StandardCopyOption

            source_file = File(source_path)
            if not source_file.exists() or not source_file.isFile():
                self.log(f"❌ 源文件不存在: {source_path}")
                return False

            python_class = Class.forName("com.chaquo.python.Python")
            get_instance_method = python_class.getMethod("getInstance")
            python_instance = get_instance_method.invoke(None)

            get_platform_method = python_class.getMethod("getPlatform")
            platform = get_platform_method.invoke(python_instance)

            get_application_method = platform.getClass().getMethod("getApplication")
            application = get_application_method.invoke(platform)
            context = application.getApplicationContext()
            files_dir = context.getFilesDir().getAbsolutePath()
            target_path = files_dir + "/" + target_filename

            target_file = File(target_path)
            if target_file.exists() and target_file.isFile() and target_file.length() == source_file.length():
                target_file.setExecutable(True)
                self.log(f"⚠️ 文件已存在: {target_path}")
                return target_path

            Files.copy(
                Paths.get(source_path),
                Paths.get(target_path),
                StandardCopyOption.REPLACE_EXISTING
            )

            File(target_path).setExecutable(True)
            self.log(f"✅ 复制完成: {target_path}")
            return target_path

        except Exception as e:
            self.log(f"❌ 复制失败: {e}")
            return False

    def start_proxy(self,path, port=12525):
        try:
            if not path:
                msg = "文件不存在"
                self.log(msg)
                return msg, False
            from java.lang import ProcessBuilder
            from java.io import File
            from android.os import Environment
            external_storage = Environment.getExternalStorageDirectory().getAbsolutePath()
            absolute_path = os.path.abspath(path)
            absolute_path = unquote(external_storage + absolute_path.split('/file')[-1])
            c_file=self.copy_file(absolute_path)
            if not c_file:
                msg = f"无法复制文件"
                self.log(msg)
                return msg, False
            if self.examine(port):
                self.proxy={}
                msg = f"✅ 代理已启动:{port}"
                self.log(msg)
                return msg, True
            oder=[c_file, "-port", str(port)]
            proxy=self.proxy.get('http','')
            if proxy:
                oder.extend(['-proxy',proxy])
            pb = ProcessBuilder(oder)
            pb.directory(File(c_file).getParentFile())
            self.process = pb.start()
            time.sleep(1)
            if self.process and self.process.isAlive() and self.examine(port):
                self.proxy = {}
                msg = f"✅ 代理已启动:{port}"
                self.log(msg)
                return msg,True
            else:
                msg = "❌ 代理启动失败"
                self.log(msg)
                return msg,False

        except Exception as e:
            msg = "❌ 启动代理异常"
            self.log(f"{msg}: {e}")
            return msg, False

    def examine(self,port):
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', int(port)))
        sock.close()
        if result == 0:
            return  True
        return  False

    xhost='https://client-rapi-missav.recombee.com'

    countr='/dm15/cn'

    ccccc='H4sIAAAAAAAAA6WVW0sbQRTHv4rk2WB2s7ls34JEG6hticamLaWMu6NZkp0Ne9GkRUhEtGihqBihTdtY0AdJisEW0qTSL5PZxG/RvZSieyZ96UPYwPx/5z5nnr8OmdUyfkmQikP3pkLDXsdu7NLOCf1xHJr2zxTZPZFVPh6bkciMVFAINnDYsFZMxSzh0OZ0wIjdrI1/HdgfvtmNy6CRGCe4RgjeYHCNy+F1c9jbo70twCWTLqfjEkYGw+do+3T05af9vU53+0E2znMuaxEJE0PTsRx2jBShDXp2Rbcvhr3a+Pz6rg2HRpKpY8PABsN3d0A/7QNiDROdJafvDsanb+nxDiBUVMQ6g1jOgl5ERC8n38eMIwDQcLBnn5yNdro3jRrAfdrUZFQNFzST1cP2Ta3Lprm46NIbGBdLk3G7+WaC81jCxVWNmIVJ/GIm+whwURczFF2D+ge5fA7WyNWXrIoF9fOphymQlhfWGiII6h9n04tLmfm0813I5BaCaDLOeykhRBi5hGdzS+kJ2UiWyZjmVBZG59Uc6Yzg7JPWqFX/v9mfm+WDqOh5XJV4qL6ffvoM9CfKiaLorYgCrr5iNMn+2B32285QwHH0p7FY1ZjT4FxJdx7rRyA7MRZLeDBX1ojM8DmLdGVlBSMiaSooKZ/g+KiHS7dl/zRS1oEZIZLkgkYcGTDDRVTLsJz/QQMcl+AFb7/9lQC4jCTN/alIRaDyiYjg79U7Kjj1yF3ekgYCiMb80f9zvDk9FSDz+Xw4tczuW6VSQeuMpvX79HxgN9qAEpyLousKlo0SMgqQvGkdjN5/FeJchH0JCLLWCmbVE0yAI2IUwDx/C/YEEO4Pxt0dunVFLw5BkQX/issaY58sPYHV8feJucEqzpylW0U4CF4bVv0zGNznI9rcHznP6mEHPB3FkrLOYJz3fDIj+cyL38kN2ZoFCAAA'

    fts = 'H4sIAAAAAAAAA23P30rDMBQG8FeRXM8X8FVGGZk90rA0HU3SMcZgXjn8V6p2BS2KoOiFAwUn2iK+TBP7GBpYXbG9/c6Pc77TnaABjNHOFtojVIDPUQcx7IJJvl9ydX30GwSYSpN0J4iZgTqJiywrPlN1vm/GJiPMJgGxJaZo2qnc3WXDuZIKMqSwUcX7Ui8O1DJRH3Gldh3CgMM2l31BhNGW8euq3PNFrac+PVNZ2NYzjMrbY53c6/Sm2uwDBczB7mGxqaDTWfkV6atXvXiu4FD2KeHOf3nxViahjv8YxwHYtWfyQ3NvFZYP85oSno3HvYDAiNevPqnosWFHAAPahnU6b2DXY8Jp0bO8QdfEmlo/SBd5PPUBAAA='

    actfts = 'H4sIAAAAAAAAA5WVS2sUQRRG/0rT6xTcqq5Xiwjm/X6sQxZjbBLRBBeOIEGIIEgWrtwI4lJEQsjGhU6Iv2bGcf6FVUUydW/d1SxT55sDfbpmsn9WP+/e1A+q+rh7dnT8qp6rT3snXTz4N7icXH4OB697L/rxZP+sPo1g+Ot8PPg+vvoyOb+IOJ7Vb+fuqGxkJSrZmMOTexiORDjAGxs3GvDGinCANjp5NPbo4NHYo5PHYI8OHoM9JnkM9pjgMdhjksdijwkeiz02eSz22OCx2GOTx2GPDR6HPS55HPa44HHY45LHY48LHo89Pnk89vjg8djjk6fFHh88bfAcxNXduz/sv0Qvfnz74+/X65lf/OMqfzD9ndF8geYzWijQQkaLBVrMaKlASxktF2g5o5UCrWS0WqDVjNYKtJbReoHWM9oo0EZGmwXazGirQFsZbRdoO6OdAu1ktFug3Yz2CrRH70TvqEN3YvT75+TP+5nvxMNKwf0pCIWur4JwM5spVCAaRJtI9ZQ2IPBPg47UTKkGgb/wJlI7pQYE/ho/QsiCaFv61E+7J338Izj6MJi8+xSefnhzO/PTK1CmGt58G118zM+pDBloPtBk0PBBQwaKDxQZSD6QZAB8QN6UbNlAtmTg+cCTgeMDRwaWDywZ8JKSlJS8pCQlJS8pSUnJS0pSUvKSkpSUvKQkJYGXBFISeEkgJYGXBFISeEkgJYGXBFISeEkgJYGXBFISeEkgJYGXBFISeElI/7QO/gOZ7bAksggAAA=='
    def homeContent(self, filter):
        one={"vod_name": "go状态","vod_pic": "https://img-blog.csdnimg.cn/6f8b58d3daf14b5696e85c710f18a571.png","action": "action","vod_remarks": self.one_mark,"style": {"type": "rect","ratio": 1.33}}
        html = pq(requests.get(f"{self.cfproxy}{self.host}{self.countr}",headers=self.headers,proxies=self.proxy).content)
        result = {}
        filters = {}
        classes=self.ungzip(self.ccccc)
        for i in classes:
            id=i['type_id']
            filters[id] = copy.deepcopy(self.ungzip(self.fts))
            if 'cn/actresses' in id:filters[id].extend(self.ungzip(self.actfts))
        result['class'] = classes
        result['filters'] = filters
        result['list'] = self.getlist(html('.grid-cols-2.md\\:grid-cols-3 .thumbnail.group'))
        result['list'].insert(0, one)
        return result

    def homeVideoContent(self):
        pass

    def categoryContent(self, tid, pg, filter, extend):
        params={
            'page':pg
        }
        ft = {
            'filters': extend.get('filters', ''),
            'sort': extend.get('sort', '')
        }
        if tid in ['cn/genres', 'cn/makers']:
            ft = {}
        elif tid == 'cn/actresses':
            ft = {
                'height': extend.get('height', ''),
                'cup': extend.get('cup', ''),
                'debut': extend.get('debut', ''),
                'age': extend.get('age', ''),
                'sort': extend.get('sort', '')
            }
        params.update(ft)
        params={k: v for k, v in params.items() if v}
        req = requests.Request(
            url=f"{self.host}/{tid}",
            params=params,
        ).prepare()
        data=pq(requests.get(f"{self.cfproxy}{req.url}",headers=self.headers,proxies=self.proxy).content)
        result = {}
        if tid in ['cn/genres', 'cn/makers']:
            videos = self.gmsca(data)
        elif tid == 'cn/actresses':
            videos = self.actca(data)
        else:
            videos = self.getlist(data('.grid-cols-2.md\\:grid-cols-3 .thumbnail.group'))
        result['list'] = videos
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        return result

    def detailContent(self, ids):
        urlllll=f"{self.cfproxy}{self.host}/{ids[0]}"
        v=pq(requests.get(urlllll,headers=self.headers,proxies=self.proxy).content)
        sctx=v('body script').text()
        urls=self.execute_js(sctx)
        if not urls:urls=f"嗅探${urlllll}"
        c=v('.space-y-2 .text-secondary')
        ac,dt,cd,bq=[],[],[],['点击展开↓↓↓\n']
        for i in c.items():
            xxx=i('span').text()
            if re.search(r"导演:|发行商:",xxx):
                dt.extend(['[a=cr:' + json.dumps({'id': j.attr('href').split('/',3)[-1], 'name': j.text()}) + '/]' + j.text() + '[/a]' for j in i('a').items()])
            elif re.search(r"女优:",xxx):
                ac.extend(['[a=cr:' + json.dumps({'id': j.attr('href').split('/',3)[-1], 'name': j.text()}) + '/]' + j.text() + '[/a]' for j in i('a').items()])
            elif re.search(r"类型:|系列:",xxx):
                bq.extend(['[a=cr:' + json.dumps({'id': j.attr('href').split('/',3)[-1], 'name': j.text()}) + '/]' + j.text() + '[/a]' for j in i('a').items()])
            elif re.search(r"标籤:",xxx):
                cd.extend(['[a=cr:' + json.dumps({'id': j.attr('href').split('/',3)[-1], 'name': j.text()}) + '/]' + j.text() + '[/a]' for j in i('a').items()])
        np={'MissAV':urls,'Recommend':self.getfov(ids[0])}
        vod = {
            'type_name': c.eq(-3)('a').text(),
            'vod_year': c.eq(0)('time').text(),
            'vod_remarks': ' '.join(cd),
            'vod_actor': ' '.join(ac),
            'vod_director': ' '.join(dt),
            'vod_content': f"{' '.join(bq)}\n{v('.text-secondary.break-all').text()}"
        }
        names,plist=[],[]
        for i,j in np.items():
            if j:
                names.append(i)
                plist.append(j)
        vod['vod_play_from']='$$$'.join(names)
        vod['vod_play_url']='$$$'.join(plist)
        return {'list': [vod]}

    def searchContent(self, key, quick, pg="1"):
        req = requests.Request(
            url=f"{self.host}/search/{key}",
            params={'page': pg},
        ).prepare()
        data = pq(requests.get(f"{self.cfproxy}{req.url}", headers=self.headers, proxies=self.proxy).content)
        return {'list': self.getlist(data('.grid-cols-2.md\\:grid-cols-3 .thumbnail.group')),'page':pg}

    def playerContent(self, flag, id, vipFlags):
        p=0 if '.m3u8' in id else 1
        if flag == 'Recommend':
            urlllll = f"{self.cfproxy}{self.host}/{id}"
            try:
                v = pq(requests.get(urlllll, headers=self.headers, proxies=self.proxy).content)
                sctx = v('body script').text()
                url = self.execute_js(sctx)
                if not url: raise Exception("没有找到地址")
                p,id=0,url.split('$')[-1]
            except:
                p,id=1,urlllll
        return {'parse': p, 'url': id if p else f"{self.plp}{id}", 'header': self.headers}

    def localProxy(self, param):
        pass

    def getlist(self,data):
        videos = []
        names,ids=[],[]
        for i in data.items():
            k = i('.overflow-hidden.shadow-lg a')
            id=k.eq(0).attr('href')
            name=i('.text-secondary').text()
            if id and id not in ids and name not in names:
                ids.append(id)
                names.append(name)
                videos.append({
                    'vod_id': id.split('/',3)[-1],
                    'vod_name': name,
                    'vod_pic': k.eq(0)('img').attr('data-src'),
                    'vod_year': '' if len(list(k.items())) < 3 else k.eq(1).text(),
                    'vod_remarks': k.eq(-1).text(),
                    'style': {"type": "rect", "ratio": 1.33}
                })
        return videos

    def gmsca(self,data):
        acts=[]
        for i in data('.grid.grid-cols-2.md\\:grid-cols-3 div').items():
            id=i('.text-nord13').attr('href')
            acts.append({
                'vod_id':id.split('/', 3)[-1] if id else id,
                'vod_name': i('.text-nord13').text(),
                'vod_pic': '',
                'vod_remarks': i('.text-nord10').text(),
                'vod_tag': 'folder',
                'style': {"type": "rect", "ratio": 2}
            })
        return acts

    def actca(self,data):
        acts=[]
        for i in data('.max-w-full ul li').items():
            id=i('a').attr('href')
            acts.append({
                'vod_id': id.split('/', 3)[-1] if id else id,
                'vod_name': i('img').attr('alt'),
                'vod_pic': i('img').attr('src'),
                'vod_year': i('.text-nord10').eq(-1).text(),
                'vod_remarks': i('.text-nord10').eq(0).text(),
                'vod_tag': 'folder',
                'style': {"type": "oval"}
            })
        return acts

    def getfov(self, url):
        try:
            h=self.headers.copy()
            ids=url.split('/')
            h.update({'referer':f'{self.host}/{url}/'})
            t=str(int(time.time()))
            params = {
                'frontend_timestamp': t,
                'frontend_sign': self.getsign(f"/missav-default/batch/?frontend_timestamp={t}"),
            }
            uid=str(uuid.uuid4())
            json_data = {
                'requests': [
                    {
                        'method': 'POST',
                        'path': f'/recomms/items/{ids[-1]}/items/',
                        'params': {
                            'targetUserId': uid,
                            'count': 13,
                            'scenario': 'desktop-watch-next-side',
                            'returnProperties': True,
                            'includedProperties': [
                                'title_cn',
                                'duration',
                                'has_chinese_subtitle',
                                'has_english_subtitle',
                                'is_uncensored_leak',
                                'dm',
                            ],
                            'cascadeCreate': True,
                        },
                    },
                    {
                        'method': 'POST',
                        'path': f'/recomms/items/{ids[-1]}/items/',
                        'params': {
                            'targetUserId': uid,
                            'count': 12,
                            'scenario': 'desktop-watch-next-bottom',
                            'returnProperties': True,
                            'includedProperties': [
                                'title_cn',
                                'duration',
                                'has_chinese_subtitle',
                                'has_english_subtitle',
                                'is_uncensored_leak',
                                'dm',
                            ],
                            'cascadeCreate': True,
                        },
                    },
                ],
                'distinctRecomms': True,
            }
            data = requests.post(f'{self.xhost}/missav-default/batch/', params=params,headers=h, json=json_data,proxies=self.proxy).json()
            vdata=[]
            for i in data:
                for j in i['json']['recomms']:
                    if j.get('id'):
                        vdata.append(f"{j['values']['title_cn']}${j['id']}")
            return '#'.join(vdata)
        except Exception as e:
            self.log(f"获取推荐失败: {e}")
            return ''

    def getsign(self, text):
        message_bytes = text.encode('utf-8')
        key_bytes = b'Ikkg568nlM51RHvldlPvc2GzZPE9R4XGzaH9Qj4zK9npbbbTly1gj9K4mgRn0QlV'
        h = HMAC.new(key_bytes, digestmod=SHA1)
        h.update(message_bytes)
        signature = h.hexdigest()
        return signature

    def ungzip(self, data):
        result=gzip.decompress(b64decode(data)).decode('utf-8')
        return json.loads(result)

    def execute_js(self, jstxt):
        js_code = re.search(r"eval\(function\(p,a,c,k,e,d\).*?return p}(.*?)\)\)", jstxt).group(0)
        try:
            from com.whl.quickjs.wrapper import QuickJSContext
            ctx = QuickJSContext.create()
            result=ctx.evaluate(f"{js_code}\nsource")
            ctx.destroy()
            return f"多画质${result}"
        except Exception as e:
            self.log(f"执行失败: {e}")
            return None



