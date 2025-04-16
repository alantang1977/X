# -*- coding: utf-8 -*-
# by @嗷呜
import binascii
import json
import os
import re
import sys
import time
import uuid
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
sys.path.append('..')
from base.spider import Spider
from base64 import b64encode, b64decode
from Crypto.PublicKey import RSA
from Crypto.Cipher import AES, PKCS1_v1_5
from Crypto.Util.Padding import unpad, pad
from Crypto.Hash import MD5


class Spider(Spider):

    def init(self, extend=""):
        self.host = self.gethost()
        pass

    def getName(self):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    headers = {
        'AppID': '534',
        'app_id': '534',
        'version': '1.0.3',
        'package': 'com.hjmore.wallpaper',
        'user_id': '3507f394e83d2424',
        'user-id': '3507f394e83d2424',
        'app_name': 'lanlan',
        'app-name': 'lanlan',
        'Content-Type': 'application/json; charset=utf-8;',
        'User-Agent': 'okhttp/4.9.0'
    }

    def homeContent(self, filter):
        hdata=self.getdata('/api.php/provide/index',self.getbody({'tid':'0'}))
        vlist=hdata['data'].get('tj',[])
        result = {}
        classes = []
        filters = {}
        for i in hdata['data']['sub_data']:
            id=str(i['type_id'])
            classes.append({'type_id': id, 'type_name': i['type_name']})
            if len(i['data']):
                vlist.extend(i['data'])
        with ThreadPoolExecutor(max_workers=len(classes)) as executor:
            results = executor.map(self.getf, classes)
            for id, ft in results:
                if len(ft):filters[id] = ft
        result['class'] = classes
        result['filters'] = filters
        result['list'] = vlist
        return result

    def homeVideoContent(self):
        pass

    def categoryContent(self, tid, pg, filter, extend):
        body={
        "tid": tid,
        "type": extend.get('type'),
        "lang": extend.get('lang'),
        "area": extend.get('area'),
        "year": extend.get('year'),
        "pg": pg
        }
        body = {k: v for k, v in body.items() if v is not None and v != ""}
        data=self.getdata('/api.php/provide/nav',self.getbody(body))
        result = {}
        result['list'] = data['data']['data']
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        return result
        pass

    def detailContent(self, ids):
        data=self.getdata('/api.php/provide/vod',self.getbody({'ids':ids[0]}))
        vod=data['data']
        plist=[]
        names=[]
        for i in vod['vod_play_url']:
            ulist=[]
            names.append(i['name'].split(' ')[0])
            jdata={'parse':''}
            if i.get('parse') and isinstance(i['parse'], list) and len(i['parse']):
                jdata['parse']=self.e64(json.dumps(i['parse']))
            for j in i['data']:
                jdata['url']=j['url']
                ulist.append(f'{j["name"]}${self.e64(json.dumps(jdata))}')
            plist.append('#'.join(ulist))
        vod['vod_play_from']='$$$'.join(names)
        vod['vod_play_url']='$$$'.join(plist)
        vod.pop('cover_list', None)
        return {'list':[vod]}

    def searchContent(self, key, quick, pg="1"):
        body={"wd":key,"tid":"0","pg":pg}
        data=self.getdata('/api.php/provide/search',self.getbody(body))
        vlist=[]
        for i in data['data']:
            i.pop('vod_play_from', None)
            vlist.append(i)
        return {'list':vlist,'page':pg}

    def playerContent(self, flag, id, vipFlags):
        data=json.loads(self.d64(id))
        parse=data.get('parse')
        url,p,head = data.get('url'),1,''
        if parse:
            parse=json.loads(self.d64(parse))
        if not re.search(r'\.m3u8|.mp4|\.flv', url) and parse:
            for p in parse:
                try:
                    data=self.fetch(f'{p}{url}',self.headers).json()
                    url=data.get('data',{}).get('url') or data.get('url')
                    head=data.get('data',{}).get('header') or data.get('header')
                    p=0
                    break
                except:
                    p,url=1,data.get('url')
                    head = {'User-Agent': 'okhttp/4.9.0'}
        return  {'parse': p, 'url': url, 'header': head}

    def localProxy(self, param):
        pass

    def getf(self, map):
        ft,id =[], map['type_id']
        try:
            fdata = self.getdata('/api.php/provide/nav', self.getbody({'tid': id, 'pg': '1'}))
            dy = ['area', 'year', 'lang', 'type']
            fd = fdata['data']['type_extend']
            has_non_empty_field = False
            for key in dy:
                if key in fd and fd[key].strip() != "":
                    has_non_empty_field = True
                    break
            if has_non_empty_field:
                for dkey in fd:
                    if dkey in dy and fd[dkey].strip() != "":
                        values = fd[dkey].split(",")
                        value_array = [{"n": value.strip(), "v": value.strip()} for value in values if
                                    value.strip() != ""]
                        ft.append({"key": dkey, "name": dkey, "value": value_array})
            return (id, ft)
        except:
            return (id, ft)

    def getskey(self):
        random_bytes = os.urandom(16)
        return binascii.hexlify(random_bytes).decode()

    def getohost(self):
        url='https://bianyuan001.oss-cn-beijing.aliyuncs.com/huidu1.0.0.json'
        response = self.fetch(url, headers=self.headers).json()
        return response['servers'][0]

    def gethost(self):
        body={
            "gr_rp_size": "1080*2272",
            "gr_app_list": "%E5%B1%8F%E5%B9%95%E5%BD%95%E5%88%B6%EF%BC%88com.miui.screenrecorder%29%0A%E5%A4%B8%E5%85%8B%EF%BC%88com.quark.browser%29%0A%E8%BE%B9%E7%BC%98%E8%A7%86%E9%A2%91%EF%BC%88com.hjmore.wallpaper%29%0A%E5%93%94%E5%93%A9%E5%93%94%E5%93%A9%EF%BC%88tv.danmaku.bili%29%0A%E7%81%AB%E6%98%9F%E6%90%9C%E9%A2%98%EF%BC%88com.fenbi.android.souti%29%0A%E6%94%AF%E4%BB%98%E5%AE%9D%EF%BC%88com.eg.android.AlipayGphone%29%0AWPS%20Office%EF%BC%88cn.wps.moffice_eng%29",
            "gr_lal": "0.0%2C0.0",
            "gr_system_type": "android",
            "gr_device_imei": "3507f394e83d2424",
            "gr_app_version": "1.0.3",
            "gr_device_model": "Xiaomi%20M2012K10C%20%28Android%20%E7%89%88%E6%9C%AC%3A%2011%2C%20SDK%E7%89%88%E6%9C%AC%3A%2030%29",
            "gr_city": "%E8%B4%B5%E5%B7%9E%2C%E6%9C%AA%E7%9F%A5%2C%E6%9C%AA%E7%9F%A5",
            "requestId": self.uuid(),
            "timeStamp": str(int(time.time() * 1000)),
            "version": "1.0.3",
            "package": "com.hjmore.wallpaper",
            "userLoginToken": "",
            "app_id": "534",
            "appName": 2131951658,
            "device_id": "3507f394e83d2424",
            "device-id": "3507f394e83d2424",
            "oaid": "",
            "imei": "",
            "referer_shop": "边缘影视",
            "referer-shop": "边缘影视",
            "access_fine_location": 0,
            "access-fine-location": 0
        }
        ohost = self.getohost()
        data=self.getdata(f'/api.php/settings/grayscale_list',body,ohost)
        parsed_url = urlparse(data['data']['grayscale']['server_url'][0])
        domain = parsed_url.scheme + "://" + parsed_url.netloc
        return domain

    def drsa(self, encrypted_data):
        private_key_pem = """-----BEGIN RSA PRIVATE KEY-----
    MIIEvwIBADANBgkqhkiG9w0BAQEFAASCBKkwggSlAgEAAoIBAQDA5NWiAwRjH50/
    IJY1N0zLopa4jpuWE7kWMn1Qunu6SjBgTvNRmRUoPDHn54haLfbfXIa2X+/sIaMB
    /O3HhrpVsz55E5W2vpZ5fBYWh+M65bQERKTW+l72H7GR9x0yj3QPByzzfsj/QkyP
    81prpwR9i8yMe7yG9TFKqUQCPE+/GrhNU1Qf6nFmV+vMnlP9DantkwAt4fPOMZn3
    j4da65/1YQV+F5bYzaLenNVKbHf8U8fVYLZWIy4yk2Vpe4R2Z+JX/eHWsChE9hOu
    iFm02eTW5NJLZlWUxYrSE23VXi8oXSEdON3UEOrwSdAUh4SXxLZ9U7KpNVdTwWyR
    AS4GyzJ/AgMBAAECggEBAKzmcXefLLeNBu4mz30z7Go7es5DRcLoOudiqmFKRs1c
    4q/xFLj3drdx/WnZZ6ctvDPKRBYFOJF4NRz7Ekfew/c9i6oLnA8KFuceCs53T37j
    ltCclwT7t1L2ZbxovIsteuJdlDVOV+w2CVqez1Xfh27heKAT6ZEvBtfdkVBPr0uj
    oVwa2+XlJmYZw5dHeB7ySVeAQ+69zDuADB8OWxPWsv6Del+Fhf0kTHAw4WgqcYsd
    JUunCjgLdJUlDgXzH/M/Nj8NYVEuq6QpmhaktJ4fwn/F7u3lQllVCFKj5lr0Xb92
    y7lvQlGqMKX1oxf+P5c5/vie1kDx1Rj4S++flIcVlUECgYEA4BuxCZ1c8oOF98bs
    KTAONnnZniQ1BRt7rA+O9+++lDjxJhxkuthwjB9YzrnZtxHJtvIIie9Jv8MVfzHa
    p2woDtiEh3YYwmIlgNUFvTcGe++tTiEiLDcGc/xNhpvfbLaw9QB7/HQ+LT1QCMxJ
    ufdBrR98l0khIGjYqxDW3W5pV70CgYEA3Ff/9+GM2XI/EUSTYrpnwp5R5OsXz1DL
    3CFFgp1EPCNk/c3YNWnrUtTkfmKAlRqWIHfphvH/jS6jpGrfRxDggPwGMtBc134b
    brIM5i4KNj/EcE+w5g03HaKBf1ZihHDQ53c6wTn6IFOHJNSPRLqMNqRymfbclNyO
    lBMHQmB8yOsCgYBCdZPTwRnuRTi2WQRx1nFwkEQL1Lrwb80GInsIZc2DkTtaTPNG
    QadmtmkUrSK2Wo0SNsZ3eUHKn2TBmpw4KCfc9zKeJVSEWKy8fu+7xBSlLlebotHK
    gOrl/H1VHOZuC+OAVItwO1yw98zDPynh/0Q3ve2pw6MSRGV0nYLKmdKdlQKBgQCJ
    Ty1rw1qKhu9WS22tMIxIc3CFPxtvTeI8I1+1rVtAPq5Im2YIoyDKVXCucaO/RvoW
    8aLNPTELQe0oIJFTL+k3d9ZFBCNXBncB3GK9biNe+w3nD0IlmkamaQZZ2/M4pTUJ
    iPtMPlzomCS3ht5g7f9CbegcmgGLooYXMGRtsMMSUQKBgQCoj+3UciH2i+HyUla5
    1FxivjH3MqSTE4Q7OdzrELb6DoLYzjgWAbpG8HIuodD4uG5xz1oR5H7vkblf1itB
    hwOwDEiabyX76e/I3Q0ovwBV+9PMjM4UVU0kHoiu3Z2s90ckwNh58w3QH5fn9E0b
    fqMnB6uWze+xrXWijaOzVZhIZg==
    -----END RSA PRIVATE KEY-----"""
        private_key = RSA.import_key(private_key_pem)
        cipher = PKCS1_v1_5.new(private_key)
        decrypted_data = cipher.decrypt(b64decode(encrypted_data), None)
        return decrypted_data.decode('utf-8')

    def ersa(self, data):
        public_key = """-----BEGIN PUBLIC KEY-----
    MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA+0QMb3WDXjNBRovRhTLH
    g3d+CliZAva2tepWNNN0Pj6DgE3ZTnPR34iL/cjo9Jbd3dqAJs/YkKnFurGkDxz5
    TthIqvmz244wiFcHt+FGWoJsj5ZVvrH3pPwH85ggmI1DjxSJEUhB12Z9X6FGli8D
    drR9xeLe5y8vFekux8xCQ7pwH1mNQu4Wy32WVM8aLjmRjNzEWOvEMAWCRuwymEdS
    zlWoH53qk1dqd6DAmOJhWU2hH6Yt2ZY9LTaDGiHrS+g0DuwajAQzhbM8eonGYMph
    nP4q0UTHWEfaGR3HoILmeM32M+qF/UCGfgfR6tCMiXPoHwnD2zoxbZ2p+QlYuTZL
    vQIDAQAB
    -----END PUBLIC KEY-----"""
        key = RSA.importKey(public_key)
        cipher = PKCS1_v1_5.new(key)
        encrypted = cipher.encrypt(data.encode())
        return b64encode(encrypted).decode()

    def eaes(self, data, key):
        key = key.encode('utf-8')
        cipher = AES.new(key, AES.MODE_ECB)
        padded = pad(data.encode('utf-8'), AES.block_size)
        encrypted = cipher.encrypt(padded)
        word = b64encode(encrypted).decode('utf-8')
        return word

    def daes(self, encrypted_data, key):
        key = key.encode('utf-8')
        cipher = AES.new(key, AES.MODE_ECB)
        encrypted = b64decode(encrypted_data)
        decrypted = cipher.decrypt(encrypted)
        unpadded = unpad(decrypted, AES.block_size)
        return unpadded.decode('utf-8')

    def getbody(self,params=None):
        body = {
            "requestId": self.uuid(),
            "timeStamp": str(int(time.time()*1000)),
            "version": "1.0.3",
            "package": "com.hjmore.wallpaper",
            "userLoginToken": "",
            "app_id": "534",
            "appName": 2131951658,
            "device_id": "3507f394e83d2424",
            "device-id": "3507f394e83d2424",
            "oaid": "",
            "imei": "",
            "referer_shop": "边缘影视",
            "referer-shop": "边缘影视",
            "access_fine_location": 0,
            "access-fine-location": 0
        }
        if params:
            body.update(params)
        return body

    def getdata(self, path, body,host=None):
        jdata=json.dumps(body)
        msign = self.md5(jdata)
        skey = self.getskey()
        jsign={'key': skey,'sign': msign}
        Sign=self.ersa(json.dumps(jsign))
        header=self.headers.copy()
        header['Sign']=Sign
        dbody=self.eaes(jdata, skey)
        response = self.post(f'{host or self.host}{path}', headers=header, data=dbody)
        rdata=response.text
        if response.headers.get('Sign'):
            dkey=self.drsa(response.headers['Sign'])
            rdata=self.daes(rdata, dkey)
        return json.loads(rdata)
        
    def e64(self, text):
        try:
            text_bytes = text.encode('utf-8')
            encoded_bytes = b64encode(text_bytes)
            return encoded_bytes.decode('utf-8')
        except Exception as e:
            print(f"Base64编码错误: {str(e)}")
            return ""

    def d64(self,encoded_text):
        try:
            encoded_bytes = encoded_text.encode('utf-8')
            decoded_bytes = b64decode(encoded_bytes)
            return decoded_bytes.decode('utf-8')
        except Exception as e:
            print(f"Base64解码错误: {str(e)}")
            return ""
        
    def md5(self,text):
        h = MD5.new()
        h.update(text.encode('utf-8'))
        return h.hexdigest()
    
    def uuid(self):
        return str(uuid.uuid4())



