#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Author  : Doubebly
# @Time    : 2025/12/19 21:27
# @file    : 小红影视.min

k='zh-CN,zh;q=0.9'
j='gzip, deflate, br, zstd'
i='same-origin'
h='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36'
g='"Windows"'
f='"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"'
e='accept-language'
d='sec-fetch-dest'
c='sec-fetch-mode'
b='sec-fetch-site'
a='sec-ch-ua-platform'
Z='sec-ch-ua-mobile'
Y='sec-ch-ua'
X='href'
W='type'
V='class'
U='origin'
T='User-Agent'
P='vod_pic'
O='1'
N='referer'
M='https://www.xiaohys.com'
K='vod_remarks'
J='vod_name'
I='vod_id'
H='type_name'
G='jx'
C='url'
F='parse'
E=print
D=Exception
B='list'
A=''
import base64 as l,hashlib as m,json as Q,re,sys,time,requests as R
from pyquery import PyQuery as S
from Crypto.Cipher import AES as L
from Crypto.Util.Padding import unpad
sys.path.append('..')
from base.spider import Spider as n
class Spider(n):
	def __init__(A):B='https://www.xiaohys.com/';super().__init__();A.debug=False;A.name='小红影视';A.error_play_url='https://kjjsaas-sh.oss-cn-shanghai.aliyuncs.com/u/3401405881/20240818-936952-fc31b16575e80a7562cdb1f81a39c6b0.mp4';A.home_url=M;A.headers={T:'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',U:B,N:B};A.session=R.session()
	def getName(A):return A.name
	def init(A,extend='{}'):A.extend=extend
	def homeContent(D,filter):A='type_id';C={V:[{A:O,H:'电影'},{A:'2',H:'剧集'},{A:'3',H:'综艺'},{A:'4',H:'动漫'}],'filters':{},B:[],F:0,G:0};return C
	def categoryContent(H,cid,page,filter,ext):
		L={B:[],F:0,G:0};N=H.home_url+'/index.php/api/vod'
		try:
			M=int(time.time());O=m.md5(f"DS{M}DCC147D11943AF75".encode()).hexdigest();Q={W:cid,V:A,'area':A,'lang':A,'version':A,'state':A,'letter':A,'page':page,'time':str(M),'key':O};R=H.session.post(N,data=Q,headers=H.headers,timeout=5)
			for C in R.json()[B]:L[B].append({I:str(C[I]),J:C[J],P:C[P],K:C[K]})
		except D as S:E(S)
		return L
	def detailContent(M,did):
		a='$$$';Z='vod_play_url';Q=' :';P='span';L='div.detail-info div.slide-info';R={B:[],F:0,G:0};T=did[0];N=M.home_url+f"/detail/{T}/"
		try:
			b=M.session.get(N,headers=M.headers,timeout=5);C=S(b.text.encode());O=C(L).eq(0);U={H:O(P).eq(2).text(),I:T,J:C('div.detail-info h1').text(),K:C(L).eq(1).text().split(Q)[-1],'vod_year':O(P).eq(0).text(),'vod_area':O(P).eq(1).text(),'vod_actor':C(L).eq(3).text().split(Q)[-1],'vod_director':C(L).eq(2).text().split(Q)[-1],'vod_content':C('#height_limit').text(),'vod_play_from':a.join([A.text()for A in C('div.swiper-wrapper a').items()]),Z:A};V=[]
			for c in C('ul.anthology-list-play').items():
				W=[]
				for Y in c('li').items():d=Y('a').text().strip();N=Y('a').attr(X);W.append(f"{d}${N}")
				V.append('#'.join(W))
			U[Z]=a.join(V);R[B].append(U)
		except D as e:E(e)
		return R
	def searchContent(C,key,quick,page=O):
		L='div.thumb-content div.thumb-txt a';H={B:[],F:0,G:0};M=C.home_url+f"/search{key}/page/{page}/"
		try:
			N=C.session.get(M,headers=C.headers,timeout=5);O=S(N.text.encode())
			for A in O('div.public-list-box.search-box').items():H[B].append({I:A(L).attr(X).split('/')[-2],J:A(L).text(),P:A('img.gen-movie-img').attr('data-src'),K:A('span.public-list-prb').text()})
		except D as Q:E(Q)
		return H
	def playerContent(H,flag,pid,vipFlags):
		K='http';B={C:H.error_play_url,F:0,G:0,'header':{}};L=H.home_url+pid
		try:
			P={Y:f,Z:'?0',a:g,'upgrade-insecure-requests':O,'user-agent':h,'accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',b:i,c:'navigate','sec-fetch-user':'?1',d:'document',N:M,'accept-encoding':j,e:k,'priority':'u=0, i'};R=H.session.get(L,headers=P,timeout=5);I=re.search('player_aaaa=(.*?)</script>',R.text)
			if I:
				S=Q.loads(I.group(1));A=S[C]
				if A.startswith('Ace_'):
					J=H.parse_url(A)
					if J:B[C]=J
				if A.startswith(K)and'.m3u8'in A:B[C]=A
				if A.startswith(K)and'.html'in A:B[C]='https://jx.hls.one/?url='+A;B[F]=1
		except D as T:E(T)
		return B
	def localProxy(A,params):0
	def log(A,msg):
		if A.debug:
			try:R.post('http://192.168.31.13:5000/log',data=msg,timeout=1)
			except D as B:E(B)
	def parse_url(F,uri):
		G=None
		try:
			H={C:uri,W:A,'name':A};I={T:h,'Accept':'application/json, text/javascript, */*; q=0.01','Accept-Encoding':j,a:g,'x-requested-with':'XMLHttpRequest',Y:f,Z:'?0',U:M,b:i,c:'cors',d:'empty',N:'https://www.xiaohys.com/static/player/artplayer.html',e:k};J=F.session.post(F.home_url+'/static/player/artplayer/api.php?ac=getdate',data=H,headers=I,timeout=5);B=J.json()
			if B['code']==200:K='d978a93ffb4d3a00';O=B['iv'];P=B['data'];R=L.new(K.encode(),L.MODE_CBC,O.encode());S=unpad(R.decrypt(l.b64decode(P)),L.block_size).decode();V=Q.loads(S);G=V['videoUrl']
		except D as X:E(X)
		return G
if __name__=='__main__':0
