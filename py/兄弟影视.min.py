#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Author  : Doubebly
# @Time    : 2025/11/16 22:12
# @file    : 兄弟影视.min.py
#!/usr/bin/python3

R='vod_pic'
Q='span.public-list-prb.hide.ft2'
P='data-src'
O=print
L='vod_remarks'
K='vod_name'
J='vod_id'
I='href'
G='a'
F='jx'
E='parse'
D='type_name'
B='list'
A=''
import hashlib as Z,json,re,sys,time as M,requests as C
from urllib import parse as N
from pyquery import PyQuery as H
sys.path.append('..')
from base.spider import Spider as S
class Spider(S):
	def __init__(A):super().__init__();A.debug=False;A.name='兄弟影视';A.error_play_url='https://sf1-cdn-tos.huoshanstatic.com/obj/media-fe/xgplayer_doc_video/mp4/xgplayer-demo-720p.mp4';A.home_url='https://www.brovods.top';A.headers={'User-Agent':'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Mobile Safari/537.36'}
	def getName(A):return A.name
	def init(A,extend='{}'):A.extend=extend
	def getDependence(A):return[]
	def isVideoFormat(A,url):0
	def manualVideoCheck(A):0
	def liveContent(B,url):return A
	def homeContent(G,filter):A='type_id';C={'class':[{A:'Movies',D:'电影'},{A:'TV',D:'剧集'},{A:'Shows',D:'综艺'},{A:'Anime',D:'动漫'},{A:'Snaps',D:'短剧'},{A:'Documentaries',D:'纪录片'}],'filters':{},B:[],E:0,F:0};return C
	def homeVideoContent(C):A={B:[],E:0,F:0};return A
	def categoryContent(D,cid,page,filter,ext):
		M={B:[],E:0,F:0};N=D.home_url+f"/show/{cid}--------{page}---/";O=C.get(N,headers=D.headers);S=H(O.text.encode());T=S('div.public-list-box.public-pic-b div.public-list-div.public-list-bj')
		for A in T.items():U=A(G).attr(I);V=A(G).attr('title');W=A('img').attr(P);X=A(Q).text();M[B].append({J:U,K:V,R:W,L:X})
		return M
	def detailContent(N,did):
		U='$$$';O={B:[],E:0,F:0};P=did[0];M=N.home_url+P;V=C.get(M,headers=N.headers);Q=H(V.text.encode());W=[A.text()for A in Q('div.anthology-tab div.swiper-wrapper a').items()];X=Q('ul.anthology-list-play');R=[]
		for Y in X.items():
			S=[]
			for T in Y('li').items():Z=T(G).text();M=T(G).attr(I);S.append(f"{Z}${M}")
			R.append('#'.join(S))
		O[B].append({D:A,J:P,K:A,L:A,'vod_year':A,'vod_area':A,'vod_actor':A,'vod_director':A,'vod_content':A,'vod_play_from':U.join(W),'vod_play_url':U.join(R)});return O
	def searchContent(D,key,quick,page='1'):
		M='div.thumb-content div.thumb-txt.cor4.hide a';G={B:[],E:0,F:0};N=D.home_url+f"/ss/{key}----------{page}---/";O=C.get(N,headers=D.headers);S=H(O.text.encode());T=S('div.public-list-box.search-box')
		for A in T.items():U=A(M).attr(I);V=A(M).text();W=A('img.gen-movie-img').attr(P);X=A(Q).text();G[B].append({J:U,K:V,R:W,L:X})
		return G
	def playerContent(B,flag,pid,vipFlags):
		Y='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36';X='https://play.brovods.top';W='user-agent';V='origin';U='header';G='url';D={G:B.error_play_url,E:0,F:0,U:{}};a=B.home_url+pid;H=C.get(a,headers=B.headers);J=re.search('var player_aaaa=(.*?)</script>',H.text)
		if J:
			K=json.loads(J.group(1));b=N.quote(K[G]);c=B.home_url+K['link_next'];d='https://play.brovods.top?url='+b+'&next='+N.quote(c,safe=A);I=C.get(d,headers=B.headers);L=re.search('"url":"(.*?)",',I.text);P=re.search('"pbgjz":"(.*?)",',I.text);Q=re.search('"dmkey":"(.*?)",',I.text)
			if L and P and Q:
				e=L.group(1);f=P.group(1);g=Q.group(1);h={'accept':'application/json, text/javascript, */*; q=0.01','accept-language':'zh-CN,zh;q=0.9','content-type':'application/x-www-form-urlencoded; charset=UTF-8',V:X,W:Y};R=M.time();S=M.localtime(R);i=S.tm_min*60+S.tm_sec;j=int(R-i);k=f"{j}cnmdhb";l={G:e,'pbgjz':f,'dmkey':g,'key':Z.sha256(k.encode('utf-8')).hexdigest()};H=C.post('https://play.brovods.top/JX',headers=h,json=l);T=H.json()
				if T['code']==200:D[G]=T['cnmdhb'];m={W:Y,V:X};D[U]=m
		O(D);return D
	def localProxy(A,params):0
	def destroy(A):return'正在Destroy'
if __name__=='__main__':0
