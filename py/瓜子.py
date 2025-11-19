# coding = utf-8
#!/usr/bin/python
import re
import sys
import json
import time
import base64
import hashlib
import urllib.parse
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
from base.spider import Spider

sys.path.append('..')

class Spider(Spider):
    def __init__(self):
        self.name = "瓜子"
        self.host = 'https://api.w32z7vtd.com'
        self.token = '1be86e8e18a9fa18b2b8d5432699dad0.ac008ed650fd087bfbecf2fda9d82e9835253ef24843e6b18fcd128b10763497bcf9d53e959f5377cde038c20ccf9d17f604c9b8bb6e61041def86729b2fc7408bd241e23c213ac57f0226ee656e2bb0a583ae0e4f3bf6c6ab6c490c9a6f0d8cdfd366aacf5d83193671a8f77cd1af1ff2e9145de92ec43ec87cf4bdc563f6e919fe32861b0e93b118ec37d8035fbb3c.59dd05c5d9a8ae726528783128218f15fe6f2c0c8145eddab112b374fcfe3d79'
        self.header = {
            'Cache-Control': 'no-cache',
            'Version': '2406025',
            'PackageName': 'com.uf076bf0c246.qe439f0d5e.m8aaf56b725a.ifeb647346f',
            'Ver': '1.9.2',
            'Referer': self.host,
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'okhttp/3.12.0'
        }
        # 添加缓存机制
        self.cache = {}
        self.cache_timeout = 300  # 5分钟缓存
        
    def getName(self):
        return self.name

    def init(self, extend=''):
        pass

    def homeContent(self, filter):
        result = {}
        classes = [
            {"type_name": "电影", "type_id": "1"},
            {"type_name": "电视剧", "type_id": "2"},
            {"type_name": "动漫", "type_id": "4"},
            {"type_name": "综艺", "type_id": "3"},
            {"type_name": "短剧", "type_id": "64"}
        ]
        
        result['class'] = classes
        
        # 设置筛选条件 - 为所有分类添加筛选
        filters = {}
        for cate in classes:
            tid = cate['type_id']
            filters[tid] = [
                {"key": "area", "name": "地区", "value": [
                    {"n": "全部", "v": "0"},
                    {"n": "大陆", "v": "大陆"},
                    {"n": "香港", "v": "香港"},
                    {"n": "台湾", "v": "台湾"},
                    {"n": "美国", "v": "美国"},
                    {"n": "韩国", "v": "韩国"},
                    {"n": "日本", "v": "日本"},
                    {"n": "英国", "v": "英国"},
                    {"n": "法国", "v": "法国"},
                    {"n": "泰国", "v": "泰国"},
                    {"n": "印度", "v": "印度"},
                    {"n": "其他", "v": "其他"}
                ]},
                {"key": "year", "name": "年份", "value": [
                    {"n": "全部", "v": "0"},
                    {"n": "2025", "v": "2025"},
                    {"n": "2024", "v": "2024"},
                    {"n": "2023", "v": "2023"},
                    {"n": "2022", "v": "2022"},
                    {"n": "2021", "v": "2021"},
                    {"n": "2020", "v": "2020"},
                    {"n": "2019", "v": "2019"},
                    {"n": "2018", "v": "2018"},
                    {"n": "2017", "v": "2017"},
                    {"n": "2016", "v": "2016"},
                    {"n": "2015", "v": "2015"},
                    {"n": "2014", "v": "2014"},
                    {"n": "2013", "v": "2013"},
                    {"n": "2012", "v": "2012"},
                    {"n": "2011", "v": "2011"},
                    {"n": "2010", "v": "2010"},
                    {"n": "2009", "v": "2009"},
                    {"n": "2008", "v": "2008"},
                    {"n": "2007", "v": "2007"},
                    {"n": "2006", "v": "2006"},
                    {"n": "2005", "v": "2005"},
                    {"n": "更早", "v": "2004"}
                ]},
                {"key": "sort", "name": "排序", "value": [
                    {"n": "最新", "v": "d_id"},
                    {"n": "最热", "v": "d_hits"},
                    {"n": "推荐", "v": "d_score"}
                ]}
            ]
        
        result['filters'] = filters
        return result

    def homeVideoContent(self):
        # 首页推荐直接返回空列表，避免加载问题
        return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        videos = []
        try:
            body = {
                "area": extend.get('area', '0'),
                "year": extend.get('year', '0'),
                "pageSize": "30",
                "sort": extend.get('sort', 'd_id'),
                "page": str(pg),
                "tid": tid
            }
            
            cache_key = f"category_{tid}_{pg}_{hash(str(body))}"
            data = self.get_cached_data(cache_key, body, '/App/IndexList/indexList')
            
            if data and 'list' in data:
                for item in data['list']:
                    vod_continu = item.get('vod_continu', 0)
                    remarks = '电影' if vod_continu == 0 else f'更新至{vod_continu}集'
                    
                    video = {
                        "vod_id": f"{item.get('vod_id', '')}/{vod_continu}",
                        "vod_name": item.get('vod_name', ''),
                        "vod_pic": item.get('vod_pic', ''),
                        "vod_remarks": remarks
                    }
                    videos.append(video)
        except Exception as e:
            print(f"获取分类内容失败: {e}")
        
        return {
            'list': videos,
            'page': int(pg),
            'pagecount': 9999,
            'limit': 30,
            'total': 999999
        }

    def detailContent(self, ids):
        try:
            vod_id = ids[0].split('/')[0]
            
            # 获取视频详情
            t = str(int(time.time()))
            body1 = {
                "token_id": "1649412",
                "vod_id": vod_id,
                "mobile_time": t,
                "token": self.token
            }
            qdata = self.get_data(body1, '/App/IndexPlay/playInfo')
            
            # 获取播放列表
            body2 = {
                "vurl_cloud_id": "2",
                "vod_d_id": vod_id
            }
            jdata = self.get_data(body2, '/App/Resource/Vurl/show')
            
            if not qdata or 'vodInfo' not in qdata:
                return {'list': []}
                
            vod = qdata['vodInfo']
            
            # 构建视频信息
            video_detail = {
                "vod_id": vod_id,
                "vod_name": vod.get('vod_name', ''),
                "vod_pic": vod.get('vod_pic', ''),
                "vod_year": vod.get('vod_year', ''),
                "vod_area": vod.get('vod_area', ''),
                "vod_actor": vod.get('vod_actor', ''),
                "vod_director": vod.get('vod_director', ''),
                "vod_content": vod.get('vod_use_content', '').strip(),
                "vod_play_from": "嗷呜要吃瓜"
            }
            
            # 构建播放列表
            play_list = []
            if jdata and 'list' in jdata:
                for index, item in enumerate(jdata['list']):
                    if 'play' in item:
                        n = []  # 播放源名称
                        p = []  # 播放参数
                        for key, value in item['play'].items():
                            if 'param' in value and value['param']:
                                n.append(key)
                                p.append(value['param'])
                        
                        if p:
                            play_name = str(index + 1)
                            if len(jdata['list']) == 1:
                                play_name = vod.get('vod_name', '')
                            
                            play_url = f"{p[-1]}||{'@'.join(n)}"
                            play_list.append(f"{play_name}${play_url}")
            
            video_detail["vod_play_url"] = "#".join(play_list)
            
            return {'list': [video_detail]}
            
        except Exception as e:
            print(f"获取详情失败: {e}")
            return {'list': []}

    def searchContent(self, key, quick, pg=1):
        videos = []
        try:
            body = {
                "keywords": key,
                "order_val": "1",
                "page": str(pg)
            }
            
            # 搜索不使用缓存，确保实时性
            start_time = time.time()
            data = self.get_data(body, '/App/Index/findMoreVod', use_cache=False)
            end_time = time.time()
            
            print(f"搜索请求耗时: {end_time - start_time:.2f}秒")
            
            if data and 'list' in data:
                for item in data['list']:
                    vod_continu = item.get('vod_continu', 0)
                    remarks = '电影' if vod_continu == 0 else f'更新至{vod_continu}集'
                    
                    video = {
                        "vod_id": f"{item.get('vod_id', '')}/{vod_continu}",
                        "vod_name": item.get('vod_name', ''),
                        "vod_pic": item.get('vod_pic', ''),
                        "vod_remarks": remarks
                    }
                    videos.append(video)
        except Exception as e:
            print(f"搜索失败: {e}")
        
        return {
            'list': videos,
            'page': int(pg),
            'pagecount': 9999,
            'limit': 30,
            'total': 999999
        }

    def playerContent(self, flag, id, vipFlags):
        try:
            # 解析播放信息
            parts = id.split('||')
            if len(parts) < 2:
                return {"parse": 0, "playUrl": "", "url": ""}
            
            param_str = parts[0]
            resolutions = parts[1].split('@') if len(parts) > 1 else []
            
            # 解析参数
            params = {}
            for pair in param_str.split('&'):
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    params[key] = value
            
            # 获取播放链接
            if resolutions:
                # 分辨率从大到小排序
                resolutions.sort(key=lambda x: int(x) if x.isdigit() else 0, reverse=True)
                
                # 使用最大分辨率
                params['resolution'] = resolutions[0]
                body = params
                
                start_time = time.time()
                data = self.get_data(body, '/App/Resource/VurlDetail/showOne', use_cache=False)
                end_time = time.time()
                print(f"播放链接获取耗时: {end_time - start_time:.2f}秒")
                
                if data and 'url' in data:
                    return {
                        "parse": 0,
                        "playUrl": "",
                        "url": data['url'],
                        "header": json.dumps(self.header)
                    }
            
            return {"parse": 0, "playUrl": "", "url": ""}
            
        except Exception as e:
            print(f"播放解析失败: {e}")
            return {"parse": 0, "playUrl": "", "url": ""}

    def isVideoFormat(self, url):
        video_formats = ['.m3u8', '.mp4', '.avi', '.mkv', '.flv', '.ts']
        return any(url.lower().endswith(fmt) for fmt in video_formats)

    def manualVideoCheck(self):
        pass

    def localProxy(self, params):
        return None

    def aes_encrypt(self, text, key, iv):
        """AES加密"""
        try:
            key_bytes = key.encode('utf-8')
            iv_bytes = iv.encode('utf-8')
            cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
            encrypted = cipher.encrypt(pad(text.encode('utf-8'), AES.block_size))
            return encrypted.hex().upper()
        except Exception as e:
            print(f"AES加密失败: {e}")
            return ""

    def aes_decrypt(self, text, key, iv):
        """AES解密"""
        try:
            key_bytes = key.encode('utf-8')
            iv_bytes = iv.encode('utf-8')
            cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
            encrypted_bytes = bytes.fromhex(text)
            decrypted = unpad(cipher.decrypt(encrypted_bytes), AES.block_size)
            return decrypted.decode('utf-8')
        except Exception as e:
            print(f"AES解密失败: {e}")
            return ""

    def rsa_decrypt(self, encrypted_data, private_key):
        """RSA解密"""
        try:
            # 解码base64数据
            encrypted_bytes = base64.b64decode(encrypted_data)
            
            # 导入私钥
            rsa_key = RSA.import_key(private_key)
            cipher = PKCS1_v1_5.new(rsa_key)
            
            # 解密
            decrypted = cipher.decrypt(encrypted_bytes, None)
            return decrypted.decode('utf-8') if decrypted else ""
        except Exception as e:
            print(f"RSA解密失败: {e}")
            return ""

    def get_cached_data(self, cache_key, data, path):
        """带缓存的数据获取"""
        current_time = time.time()
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if current_time - timestamp < self.cache_timeout:
                return cached_data
        
        # 缓存不存在或已过期，重新获取
        result = self.get_data(data, path)
        if result:
            self.cache[cache_key] = (result, current_time)
        return result

    def get_data(self, data, path, use_cache=True):
        """获取数据的主要方法"""
        try:
            # 构建缓存键
            cache_key = f"{path}_{hash(str(data))}" if use_cache else None
            
            if use_cache and cache_key in self.cache:
                cached_data, timestamp = self.cache[cache_key]
                if time.time() - timestamp < self.cache_timeout:
                    return cached_data

            start_time = time.time()
            
            # AES加密请求数据
            request_key = self.aes_encrypt(json.dumps(data), 'mvXBSW7ekreItNsT', '2U3IrJL8szAKp0Fj')
            if not request_key:
                return None
            
            # 生成签名
            t = str(int(time.time()))
            keys = "Qmxi5ciWXbQzkr7o+SUNiUuQxQEf8/AVyUWY4T/BGhcXBIUz4nOyHBGf9A4KbM0iKF3yp9M7WAY0rrs5PzdTAOB45plcS2zZ0wUibcXuGJ29VVGRWKGwE9zu2vLwhfgjTaaDpXo4rby+7GxXTktzJmxvneOUdYeHi+PZsThlvPI="
            sign_str = f"token_id=,token={self.token},phone_type=1,request_key={request_key},app_id=1,time={t},keys={keys}*&zvdvdvddbfikkkumtmdwqppp?|4Y!s!2br"
            signature = hashlib.md5(sign_str.encode()).hexdigest()
            
            # 构建请求体
            body = {
                'token': self.token,
                'token_id': '',
                'phone_type': '1',
                'time': t,
                'phone_model': 'xiaomi-22021211rc',
                'keys': keys,
                'request_key': request_key,
                'signature': signature,
                'app_id': '1',
                'ad_version': '1'
            }
            
            # 发送请求 - 设置超时时间
            url = f"{self.host}{path}"
            response = self.post(url, headers=self.header, data=body, timeout=10)
            
            if response.status_code != 200:
                print(f"API请求失败: {response.status_code}, 路径: {path}")
                return None
                
            response_data = response.json()
            if 'data' not in response_data:
                print(f"API返回数据格式错误, 路径: {path}")
                return None
                
            data_response = response_data['data']
            
            # RSA解密响应密钥
            private_key = """-----BEGIN PRIVATE KEY-----
MIICdgIBADANBgkqhkiG9w0BAQEFAASCAmAwggJcAgEAAoGAe6hKrWLi1zQmjTT1
ozbE4QdFeJGNxubxld6GrFGximxfMsMB6BpJhpcTouAqywAFppiKetUBBbXwYsYU
1wNr648XVmPmCMCy4rY8vdliFnbMUj086DU6Z+/oXBdWU3/b1G0DN3E9wULRSwcK
ZT3wj/cCI1vsCm3gj2R5SqkA9Y0CAwEAAQKBgAJH+4CxV0/zBVcLiBCHvSANm0l7
HetybTh/j2p0Y1sTXro4ALwAaCTUeqdBjWiLSo9lNwDHFyq8zX90+gNxa7c5EqcW
V9FmlVXr8VhfBzcZo1nXeNdXFT7tQ2yah/odtdcx+vRMSGJd1t/5k5bDd9wAvYdI
DblMAg+wiKKZ5KcdAkEA1cCakEN4NexkF5tHPRrR6XOY/XHfkqXxEhMqmNbB9U34
saTJnLWIHC8IXys6Qmzz30TtzCjuOqKRRy+FMM4TdwJBAJQZFPjsGC+RqcG5UvVM
iMPhnwe/bXEehShK86yJK/g/UiKrO87h3aEu5gcJqBygTq3BBBoH2md3pr/W+hUM
WBsCQQChfhTIrdDinKi6lRxrdBnn0Ohjg2cwuqK5zzU9p/N+S9x7Ck8wUI53DKm8
jUJE8WAG7WLj/oCOWEh+ic6NIwTdAkEAj0X8nhx6AXsgCYRql1klbqtVmL8+95KZ
K7PnLWG/IfjQUy3pPGoSaZ7fdquG8bq8oyf5+dzjE/oTXcByS+6XRQJAP/5ciy1b
L3NhUhsaOVy55MHXnPjdcTX0FaLi+ybXZIfIQ2P4rb19mVq1feMbCXhz+L1rG8oa
t5lYKfpe8k83ZA==
-----END PRIVATE KEY-----"""
            
            bodyki_json = self.rsa_decrypt(data_response['keys'], private_key)
            if not bodyki_json:
                print("RSA解密失败")
                return None
                
            bodyki = json.loads(bodyki_json)
            
            # AES解密响应数据
            decrypted_data = self.aes_decrypt(data_response['response_key'], bodyki['key'], bodyki['iv'])
            if not decrypted_data:
                print("AES解密失败")
                return None
                
            result = json.loads(decrypted_data)
            
            end_time = time.time()
            print(f"数据获取耗时: {end_time - start_time:.2f}秒, 路径: {path}")
            
            # 缓存结果
            if use_cache and cache_key:
                self.cache[cache_key] = (result, time.time())
                
            return result
            
        except Exception as e:
            print(f"获取数据失败: {e}, 路径: {path}")
            return None

    def get_md5(self, text):
        """计算MD5"""
        return hashlib.md5(text.encode()).hexdigest()

if __name__ == '__main__':
    pass