#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Author  : Doubebly
# @Time    : 2025/10/18 21:44
# @file    : 非凡资源.min
S='url'
R=enumerate
O='msg'
N=len
M='utf-8'
L='1'
K='cid'
B='vod_pic'
J='type_name'
I=''
H='jx'
G='parse'
F='vod_remarks'
E='vod_name'
D='vod_id'
A='list'
import base64 as P,re,sys,requests as C
from urllib import parse as Q
sys.path.append('..')
from base.spider import Spider as T
class Spider(T):
	def getName(A):return A.name
	def init(A,extend=I):A.name='非凡资源';A.home_url='https://ffzy.tv';A.headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'}
	def getDependence(A):return[]
	def isVideoFormat(A,url):0
	def manualVideoCheck(A):0
	def homeContent(H,filter):G='分类';F='value';E='name';D='key';C='type_id';B='v';A='n';return{'class':[{C:L,J:'电影片'},{C:'2',J:'连续剧'},{C:'3',J:'综艺片'},{C:'4',J:'动漫片'}],'filters':{L:{D:K,E:G,F:[{A:'动作片',B:'6'},{A:'喜剧片',B:'7'},{A:'爱情片',B:'8'},{A:'科幻片',B:'9'},{A:'恐怖片',B:'10'},{A:'剧情片',B:'11'},{A:'战争片',B:'12'},{A:'记录片',B:'20'},{A:'伦理片',B:'34'}]},'2':{D:K,E:G,F:[{A:'国产剧',B:'13'},{A:'香港剧',B:'14'},{A:'韩国剧',B:'15'},{A:'欧美剧',B:'16'},{A:'台湾剧',B:'21'},{A:'日本剧',B:'22'},{A:'海外剧',B:'23'},{A:'泰国剧',B:'24'},{A:'短剧',B:'36'}]},'3':{D:K,E:G,F:[{A:'大陆综艺',B:'25'},{A:'港台综艺',B:'26'},{A:'日韩综艺',B:'27'},{A:'欧美综艺',B:'28'}]},'4':{D:K,E:G,F:[{A:'国产动漫',B:'29'},{A:'日韩动漫',B:'30'},{A:'欧美动漫',B:'31'},{A:'港台动漫',B:'32'},{A:'海外动漫',B:'33'}]}}}
	def homeVideoContent(J):
		K=[]
		try:
			L=C.get(f"{J.home_url}/index.php/ajax/data?mid=1",headers=J.headers);M=L.json()[A]
			for I in M:K.append({D:I[D],E:I[E],B:I[B],F:I[F]})
		except C.RequestException as N:return{A:[],G:0,H:0}
		return{A:K,G:0,H:0}
	def categoryContent(L,cid,page,filter,ext):
		J=cid;J=ext.get(K,J);N=f"{L.home_url}/index.php/ajax/data?mid=1&tid={J}&page={page}&limit=20";M=[]
		try:
			P=C.get(N,headers=L.headers);Q=P.json()[A]
			for I in Q:M.append({D:I[D],E:I[E],B:I[B],F:I[F]})
		except C.RequestException as R:return{A:[],O:R}
		return{A:M,G:0,H:0}
	def detailContent(I,did):
		T='$$$';S='vod_play_url';R='vod_play_from';Q='vod_content';P='vod_director';N='vod_actor';M='vod_area';L='vod_year';U=did[0];K=[]
		try:V=C.get(f"{I.home_url}/api.php/provide/vod?ac=detail&ids={U}",headers=I.headers);B=V.json()[A][0];K.append({J:B[J],D:B[D],E:B[E],F:B[F],L:B[L],M:B[M],N:B[N],P:B[P],Q:B[Q],R:B[R].split(T)[-1],S:B[S].split(T)[-1]})
		except C.RequestException as W:return{A:[],O:W}
		return{A:K,G:0,H:0}
	def searchContent(K,key,quick,page=L):
		M=key;J=[]
		if page!=L:return{A:J,G:0,H:0}
		try:
			N=C.get(f"{K.home_url}/api.php/provide/vod?ac=detail&wd={M}",headers=K.headers);P=N.json()[A]
			for I in P:J.append({D:I[D],E:I[E],B:I[B],F:I[F]})
		except C.RequestException as Q:return{A:[],O:Q}
		return{A:J,G:0,H:0}
	def playerContent(A,flag,pid,vipFlags):B=A.getProxyUrl()+f"&url={A.b64encode(pid)}";return{S:B,'header':A.headers,G:0,H:0}
	def localProxy(A,params):B=A.b64decode(params[S]);C=A.del_ads(B);return[200,'application/vnd.apple.mpegurl',C]
	def destroy(A):return'正在Destroy'
	def b64encode(A,data):return P.b64encode(data.encode(M)).decode(M)
	def b64decode(A,data):return P.b64decode(data.encode(M)).decode(M)
	def del_ads(K,url):
		S='http';H=url;G='/';L=C.get(url=H,headers=K.headers);M=H.rsplit(G,maxsplit=1)[0]+G;O=Q.urlparse(H);P=Q.urlunparse([O.scheme,O.netloc,I,I,I,I])
		if L.status_code==200:
			D=L.text.splitlines()
			if D[0]=='#EXTM3U'and'mixed.m3u8'in D[2]:
				if D[2].startswith(S):J=D[2]
				elif D[2].startswith(G):J=P+D[2]
				else:J=M+D[2]
				return K.del_ads(J)
			else:
				E=[];A=[]
				for(T,B)in R(D):
					if'.ts'in B:
						if B.startswith(S):E.append(B)
						elif B.startswith(G):E.append(P+B)
						else:E.append(M+B)
					elif B=='#EXT-X-DISCONTINUITY':E.append(B);A.append(T)
					else:E.append(B)
				F=[]
				if N(A)>=1:F.append((A[0],A[0]))
				if N(A)>=3:F.append((A[1],A[2]))
				if N(A)>=5:F.append((A[3],A[4]))
				U=[B for(A,B)in R(E)if not any(B<=A<=C for(B,C)in F)];return'\n'.join(U)
		else:return I
if __name__=='__main__':0

