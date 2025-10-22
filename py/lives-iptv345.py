# -*- coding: utf-8 -*-
# @Author  : Doubebly
# @Time    : 2025/3/23 21:55
import base64
import sys
import time
import json
import requests
import re  # 新增导入re模块
sys.path.append('..')
from base.spider import Spider
from bs4 import BeautifulSoup

class Spider(Spider):
    def getName(self):
        return "Litv"

    def init(self, extend):
        self.extend = extend
        try:
            self.extendDict = json.loads(extend)
        except:
            self.extendDict = {}

        proxy = self.extendDict.get('proxy', None)
        if proxy is None:
            self.is_proxy = False
        else:
            self.proxy = proxy
            self.is_proxy = True
        pass

    def getDependence(self):
        return []

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def liveContent(self, url):
        channel_list = ["#EXTM3U"]
        try:
            base_url = "https://iptv345.com/"
            fenlei = ["央视,ys", "卫视,ws", "综合,itv", "体育,ty", "电影,movie", "其他,other"]
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }

            for group in fenlei:
                try:
                    group_name, group_id = group.split(",")
                    api_url = f"{base_url.rstrip('/')}/?tid={group_id}"
                    
                    response = requests.get(api_url, headers=headers, timeout=10)
                    response.raise_for_status()  

                    soup = BeautifulSoup(response.text, 'html.parser')
                    ul_tag = soup.find('ul', {
                        'data-role': 'listview',
                        'data-inset': 'true',
                        'data-divider-theme': 'a'
                    })

                    if not ul_tag:
                        print(f"警告：未找到{group_name}分类的列表")
                        continue

                    for li in ul_tag.find_all('li'):
                        a_tag = li.find('a')
                        if not a_tag:
                            continue

                        channel_path = a_tag.get('href', '').strip()
                        if not channel_path:
                            continue

                        full_url = requests.compat.urljoin(base_url, channel_path)
                        name = a_tag.text.strip()
                        
                        m3u_entry = (
                            f'#EXTINF:-1 tvg-id="{name}" '
                            f'tvg-name="{name}" '
                            f'tvg-logo="https://logo.doube.eu.org/{name}.png" '
                            f'group-title="{group_name}",{name}\n'
                            f'video://{full_url}'
                        )
                        channel_list.append(m3u_entry)

                except requests.exceptions.RequestException as e:
                    print(f"{group_name}分类请求失败: {str(e)}")
                except Exception as e:
                    print(f"{group_name}分类处理异常: {str(e)}")

        except Exception as e:
            print(f"全局异常: {str(e)}")

        return '\n'.join(channel_list)

    def homeContent(self, filter):
        return {}

    def homeVideoContent(self):
        return {}

    def categoryContent(self, cid, page, filter, ext):
        return {}

    def detailContent(self, did):
        return {}

    def searchContent(self, key, quick, page='1'):
        return {}

    def searchContentPage(self, keywords, quick, page):
        return {}

    def playerContent(self, flag, pid, vipFlags):
        return {}

    def localProxy(self, params):
        if params['type'] == "m3u8":
            return self.proxyM3u8(params)
        if params['type'] == "ts":
            return self.get_ts(params)
        return [302, "text/plain", None, {'Location': 'https://sf1-cdn-tos.huoshanstatic.com/obj/media-fe/xgplayer_doc_video/mp4/xgplayer-demo-720p.mp4'}]
    def proxyM3u8(self, params):
        pid = params['pid']
        info = pid.split(',')
        a = info[0]
        b = info[1]
        c = info[2]
        timestamp = int(time.time() / 4 - 355017625)
        t = timestamp * 4
        m3u8_text = f'#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:4\n#EXT-X-MEDIA-SEQUENCE:{timestamp}\n'
        for i in range(10):
            url = f'https://ntd-tgc.cdn.hinet.net/live/pool/{a}/litv-pc/{a}-avc1_6000000={b}-mp4a_134000_zho={c}-begin={t}0000000-dur=40000000-seq={timestamp}.ts'
            if self.is_proxy:
                url = f'http://127.0.0.1:9978/proxy?do=py&type=ts&url={self.b64encode(url)}'

            m3u8_text += f'#EXTINF:4,\n{url}\n'
            timestamp += 1
            t += 4
        return [200, "application/vnd.apple.mpegurl", m3u8_text]

    def get_ts(self, params):
        url = self.b64decode(params['url'])
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, stream=True, proxies=self.proxy)
        return [206, "application/octet-stream", response.content]

    def destroy(self):
        return '正在Destroy'

    def b64encode(self, data):
        return base64.b64encode(data.encode('utf-8')).decode('utf-8')

    def b64decode(self, data):
        return base64.b64decode(data.encode('utf-8')).decode('utf-8')


if __name__ == '__main__':
    pass
































import requests
from bs4 import BeautifulSoup
base_url = "https://iptv345.com/"
fenlei = ["央视,ys","卫视,ws","综合,itv","体育,ty","电影,movie","其他,other"]
channel_list = []
for i in fenlei:
    group_name,group_id = i.split(",")
    api_url = f"https://iptv345.com?tid={group_id}"
 
    response = requests.get(api_url)

    if response.status_code == 200:
        print("请求成功！")
        #print(response.text)  # 打印返回的内容
        
        html_content = response.text

        soup = BeautifulSoup(html_content, 'html.parser')
        # 根据HTML结构定位目标<ul>标签
        ul_tag = soup.find('ul', {
            'data-role': 'listview',
            'data-inset': 'true',
            'data-divider-theme': 'a'
        })
        

        for li in ul_tag.find_all('li'):
            a_tag = li.find('a')
            if a_tag:
                # 处理相对路径链接
                channel_url = base_url.rstrip('/') + '/' + a_tag['href'].lstrip('/')
                channel_list.append(f"{a_tag.text.strip()},{channel_url}")            

    else:
        print("请求失败，状态码：", response.status_code)

# 打印结果
for channel in channel_list:
    print(channel)