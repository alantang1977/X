# -*- coding: utf-8 -*-
import json,re,sys,base64,requests,threading,time,random,colorsys
from Crypto.Cipher import AES
from pyquery import PyQuery as pq
from urllib.parse import quote, unquote
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    SELECTORS=['.video-item','.video-list .item','.list-item','.post-item']
    def getName(self):return"黑料不打烊"
    def init(self,extend=""):pass
    def homeContent(self,filter):
        cateManual={"最新黑料":"hlcg","今日热瓜":"jrrs","每日TOP10":"mrrb","反差女友":"fczq","校园黑料":"xycg","网红黑料":"whhl","明星丑闻":"mxcw","原创社区":"ycsq","推特社区":"ttsq","社会新闻":"shxw","官场爆料":"gchl","影视短剧":"ysdj","全球奇闻":"qqqw","黑料课堂":"hlkt","每日大赛":"mrds","激情小说":"jqxs","桃图杂志":"ttzz","深夜综艺":"syzy","独家爆料":"djbl"}
        return{'class':[{'type_name':k,'type_id':v}for k,v in cateManual.items()]}
    def homeVideoContent(self):return{}
    def categoryContent(self,tid,pg,filter,extend):
        url=f'https://heiliao.com/{tid}/'if int(pg)==1 else f'https://heiliao.com/{tid}/page/{pg}/'
        videos=self.get_list(url)
        return{'list':videos,'page':pg,'pagecount':9999,'limit':90,'total':999999}
    def fetch_and_decrypt_image(self,url):
        try:
            if url.startswith('//'):url='https:'+url
            elif url.startswith('/'):url='https://heiliao.com'+url
            r=requests.get(url,headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.7049.96 Safari/537.36','Referer':'https://heiliao.com/'},timeout=15,verify=False)
            if r.status_code!=200:return b''
            return AES.new(b'f5d965df75336270',AES.MODE_CBC,b'97b60394abc2fbe1').decrypt(r.content)
        except: return b''
    def _extract_img_from_onload(self,node):
        try:
            m=re.search(r"load(?:Share)?Img\s*\([^,]+,\s*['\"]([^'\"]+)['\"]",(node.attr('onload')or''))
            return m.group(1)if m else''
        except:return''
    def _should_decrypt(self,url:str)->bool:
        u=(url or'').lower();return any(x in u for x in['pic.gylhaa.cn','new.slfpld.cn','/upload_01/','/upload/'])
    def _abs(self,u:str)->str:
        if not u:return''
        if u.startswith('//'):return'https:'+u
        if u.startswith('/'):return'https://heiliao.com'+u
        return u
    def e64(self,s:str)->str:
        try:return base64.b64encode((s or'').encode()).decode()
        except:return''
    def d64(self,s:str)->str:
        try:return base64.b64decode((s or'').encode()).decode()
        except:return''
    def _img(self,img_node):
        u=''if img_node is None else(img_node.attr('src')or img_node.attr('data-src')or'')
        enc=''if img_node is None else self._extract_img_from_onload(img_node)
        t=enc or u
        return f"{self.getProxyUrl()}&url={self.e64(t)}&type=hlimg"if t and(enc or self._should_decrypt(t))else self._abs(t)
    def _parse_items(self,root):
        vids=[]
        for sel in self.SELECTORS:
            for it in root(sel).items():
                title=it.find('.title, h3, h4, .video-title').text()
                if not title:continue
                link=it.find('a').attr('href')
                if not link:continue
                vids.append({'vod_id':self._abs(link),'vod_name':title,'vod_pic':self._img(it.find('img')),'vod_remarks':it.find('.date, .time, .remarks, .duration').text()or''})
            if vids:break
        return vids
    def detailContent(self,array):
        tid=array[0];url=tid if tid.startswith('http')else f'https://heiliao.com{tid}'
        rsp=self.fetch(url)
        if not rsp:return{'list':[]}
        rsp.encoding='utf-8';html_text=rsp.text
        try:root_text=pq(html_text)
        except:root_text=None
        try:root_content=pq(rsp.content)
        except:root_content=None
        title=(root_text('title').text()if root_text else'')or''
        if' - 黑料网'in title:title=title.replace(' - 黑料网','')
        pic=''
        if root_text:
            og=root_text('meta[property="og:image"]').attr('content')
            if og and(og.endswith('.png')or og.endswith('.jpg')or og.endswith('.jpeg')):pic=og
            else:pic=self._img(root_text('.video-item-img img'))
        detail=''
        if root_text:
            detail=root_text('meta[name="description"]').attr('content')or''
            if not detail:detail=root_text('.content').text()[:200]
        play_from,play_url=[],[]
        if root_content:
            for i,p in enumerate(root_content('.dplayer').items()):
                c=p.attr('config')
                if not c:continue
                try:s=(c.replace('&quot;','"').replace('&#34;','"').replace('&amp;','&').replace('&#38;','&').replace('&lt;','<').replace('&#60;','<').replace('&gt;','>').replace('&#62;','>'));u=(json.loads(s).get('video',{})or{}).get('url','')
                except:m=re.search(r'"url"\s*:\s*"([^"]+)"',c);u=m.group(1)if m else''
                if u:
                    u=u.replace('\\/','/');u=self._abs(u)
                    # Extract article ID for danmaku
                    article_id = self._extract_article_id(tid)
                    if article_id:
                        play_from.append(f'视频{i+1}');play_url.append(f"{article_id}_dm_{u}")
                    else:
                        play_from.append(f'视频{i+1}');play_url.append(u)
        if not play_url:
            for pat in[r'https://hls\.[^"\']+\.m3u8[^"\']*',r'https://[^"\']+\.m3u8\?auth_key=[^"\']+',r'//hls\.[^"\']+\.m3u8[^"\']*']:
                for u in re.findall(pat,html_text):
                    u=self._abs(u)
                    article_id = self._extract_article_id(tid)
                    if article_id:
                        play_from.append(f'视频{len(play_from)+1}');play_url.append(f"{article_id}_dm_{u}")
                    else:
                        play_from.append(f'视频{len(play_from)+1}');play_url.append(u)
                    if len(play_url)>=3:break
                if play_url:break
        if not play_url:
            js_patterns=[r'video[\s\S]{0,500}?url[\s"\'`:=]+([^"\'`\s]+)',r'videoUrl[\s"\'`:=]+([^"\'`\s]+)',r'src[\s"\'`:=]+([^"\'`\s]+\.m3u8[^"\'`\s]*)']
            for pattern in js_patterns:
                js_urls=re.findall(pattern,html_text)
                for js_url in js_urls:
                    if'.m3u8'in js_url:
                        if js_url.startswith('//'):js_url='https:'+js_url
                        elif js_url.startswith('/'):js_url='https://heiliao.com'+js_url
                        elif not js_url.startswith('http'):js_url='https://'+js_url
                        article_id = self._extract_article_id(tid)
                        if article_id:
                            play_from.append(f'视频{len(play_from)+1}');play_url.append(f"{article_id}_dm_{js_url}")
                        else:
                            play_from.append(f'视频{len(play_from)+1}');play_url.append(js_url)
                        if len(play_url)>=3:break
                if play_url:break
        if not play_url:
            article_id = self._extract_article_id(tid)
            example_url = "https://hls.obmoti.cn/videos5/b9699667fbbffcd464f8874395b91c81/b9699667fbbffcd464f8874395b91c81.m3u8?auth_key=1760372539-68ed273b94e7a-0-3a53bc0df110c5f149b7d374122ef1ed&v=2"
            if article_id:
                play_from.append('示例视频');play_url.append(f"{article_id}_dm_{example_url}")
            else:
                play_from.append('示例视频');play_url.append(example_url)
        return{'list':[{'vod_id':tid,'vod_name':title,'vod_pic':pic,'vod_content':detail,'vod_play_from':'$$$'.join(play_from),'vod_play_url':'$$$'.join(play_url)}]}
    def searchContent(self,key,quick,pg="1"):
        rsp=self.fetch(f'https://heiliao.com/index/search?word={key}')
        if not rsp:return{'list':[]}
        return{'list':self._parse_items(pq(rsp.text))}
    def playerContent(self,flag,id,vipFlags):
        # Check if this is a danmaku-enabled video
        if '_dm_' in id:
            aid, pid = id.split('_dm_', 1)
            p = 0 if re.search(r'\.(m3u8|mp4|flv|ts|mkv|mov|avi|webm)', pid) else 1
            if not p:
                pid = f"{self.getProxyUrl()}&pdid={quote(id)}&type=m3u8"
            return {'parse': p, 'url': pid, 'header': {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.7049.96 Safari/537.36","Referer":"https://heiliao.com/"}}
        else:
            return{"parse":0,"playUrl":"","url":id,"header":{"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.7049.96 Safari/537.36","Referer":"https://heiliao.com/"}}
    def get_list(self,url):
        rsp=self.fetch(url)
        return[]if not rsp else self._parse_items(pq(rsp.text))
    def fetch(self,url,params=None,cookies=None,headers=None,timeout=5,verify=True,stream=False,allow_redirects=True):
        h=headers or{"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.7049.96 Safari/537.36","Referer":"https://heiliao.com/"}
        return super().fetch(url,params=params,cookies=cookies,headers=h,timeout=timeout,verify=verify,stream=stream,allow_redirects=allow_redirects)
    def localProxy(self,param):
        try:
            xtype = param.get('type', '')
            if xtype == 'hlimg':
                url=self.d64(param.get('url'))
                if url.startswith('//'):url='https:'+url
                elif url.startswith('/'):url='https://heiliao.com'+url
                r=requests.get(url,headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.7049.96 Safari/537.36","Referer":"https://heiliao.com/"},timeout=15,verify=False)
                if r.status_code!=200:return[404,'text/plain','']
                b=AES.new(b'f5d965df75336270',AES.MODE_CBC,b'97b60394abc2fbe1').decrypt(r.content)
                ct='image/jpeg'
                if b.startswith(b'\x89PNG'):ct='image/png'
                elif b.startswith(b'GIF8'):ct='image/gif'
                return[200,ct,b]
            elif xtype == 'm3u8':
                # Handle danmaku-enabled video
                path, url = unquote(param['pdid']).split('_dm_', 1)
                data = requests.get(url, headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.7049.96 Safari/537.36","Referer":"https://heiliao.com/"}, timeout=10).text
                lines = data.strip().split('\n')
                times = 0.0
                for i in lines:
                    if i.startswith('#EXTINF:'):
                        times += float(i.split(':')[-1].replace(',', ''))
                # Start background thread to refresh danmaku
                thread = threading.Thread(target=self.some_background_task, args=(path, int(times)))
                thread.start()
                print('[INFO] 获取视频时长成功', times)
                return [200, 'text/plain', data]
            elif xtype == 'hlxdm':
                # Return danmaku XML for heiliao comments
                article_id = param.get('path', '')
                times = int(param.get('times', 0))
                comments = self._fetch_heiliao_comments(article_id)
                return self._generate_danmaku_xml(comments, times)
        except Exception as e:
            print(f'[ERROR] localProxy: {e}')
        return[404,'text/plain','']
    
    def _extract_article_id(self, url):
        """Extract article ID from heiliao.com URL"""
        try:
            if '/archives/' in url:
                match = re.search(r'/archives/(\d+)/?', url)
                return match.group(1) if match else None
            return None
        except:
            return None
    
    def _fetch_heiliao_comments(self, article_id, max_pages=3):
        """Fetch comments from heiliao.com API"""
        comments = []
        try:
            for page in range(1, max_pages + 1):
                url = f"https://heiliao.com/comments/1/{article_id}/{page}.json"
                resp = requests.get(url, headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.7049.96 Safari/537.36","Referer":"https://heiliao.com/"}, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    if 'data' in data and 'list' in data['data'] and data['data']['list']:
                        for comment in data['data']['list']:
                            text = comment.get('content', '').strip()
                            if text and len(text) <= 100:  # Filter out too long comments
                                comments.append(text)
                            # Also get replies from comments.list
                            if 'comments' in comment and 'list' in comment['comments'] and comment['comments']['list']:
                                for reply in comment['comments']['list']:
                                    reply_text = reply.get('content', '').strip()
                                    if reply_text and len(reply_text) <= 100:
                                        comments.append(reply_text)
                        # Check if there are more pages
                        if not data['data'].get('next', False):
                            break
                    else:
                        break  # No more comments
                else:
                    break
        except Exception as e:
            print(f'[ERROR] _fetch_heiliao_comments: {e}')
        return comments[:50]  # Limit to 50 comments max
    
    def _generate_danmaku_xml(self, comments, video_duration):
        """Generate danmaku XML from comments"""
        try:
            total_comments = len(comments)
            tsrt = f'共有{total_comments}条弹幕来袭！！！'
            danmu_xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<i>\n\t<chatserver>chat.heiliao.com</chatserver>\n\t<chatid>88888888</chatid>\n\t<mission>0</mission>\n\t<maxlimit>99999</maxlimit>\n\t<state>0</state>\n\t<real_name>0</real_name>\n\t<source>heiliao</source>\n'
            danmu_xml += f'\t<d p="0,5,25,16711680,0">{tsrt}</d>\n'
            
            for i, comment in enumerate(comments):
                # Distribute comments across video duration
                base_time = (i / total_comments) * video_duration if total_comments > 0 else 0
                dm_time = base_time + random.uniform(-3, 3)
                dm_time = round(max(0, min(dm_time, video_duration)), 1)
                dm_color = self._get_danmaku_color()
                # Clean comment text
                dm_text = re.sub(r'[<>&\u0000\b]', '', comment)
                danmu_xml += f'\t<d p="{dm_time},1,25,{dm_color},0">{dm_text}</d>\n'
            
            danmu_xml += '</i>'
            return [200, "text/xml", danmu_xml]
        except Exception as e:
            print(f'[ERROR] _generate_danmaku_xml: {e}')
            return [500, 'text/html', '']
    
    def _get_danmaku_color(self):
        """Get danmaku color (90% white, 10% random)"""
        if random.random() < 0.1:
            h = random.random()
            s = random.uniform(0.7, 1.0)
            v = random.uniform(0.8, 1.0)
            r, g, b = colorsys.hsv_to_rgb(h, s, v)
            r = int(r * 255)
            g = int(g * 255)
            b = int(b * 255)
            return str((r << 16) + (g << 8) + b)
        else:
            return '16777215'  # White
    
    def some_background_task(self, article_id, video_duration):
        """Background task to refresh danmaku in FongMi"""
        try:
            time.sleep(1)
            danmaku_url = f"{self.getProxyUrl()}&path={quote(article_id)}&times={video_duration}&type=hlxdm"
            self.fetch(f"http://127.0.0.1:9978/action?do=refresh&type=danmaku&path={quote(danmaku_url)}")
            print(f'[INFO] 弹幕刷新成功: {article_id}')
        except Exception as e:
            print(f'[ERROR] some_background_task: {e}')