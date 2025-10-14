#coding=utf-8
#!/usr/bin/python
import re
import sys
import json
import time
from datetime import datetime
from urllib.parse import quote, unquote

import requests

sys.path.append('..')
from base.spider import Spider

class Spider(Spider):  # 元类 默认的元类 type
	def getName(self):
		return "B站视频"

	def init(self, extend):
		try:
			self.extendDict = json.loads(extend)
		except:
			self.extendDict = {}

	def isVideoFormat(self, url):
		pass

	def manualVideoCheck(self):
		pass

	def homeContent(self, filter):
		result = {}
		result['filters'] = {}
		cookie = ''
		if 'cookie' in self.extendDict:
			cookie = self.extendDict['cookie']
		if 'json' in self.extendDict:
			r = self.fetch(self.extendDict['json'], timeout=10)
			if 'cookie' in r.json():
				cookie = r.json()['cookie']
		if cookie == '':
			cookie = '{}'
		elif type(cookie) == str and cookie.startswith('http'):
			cookie = self.fetch(cookie, timeout=10).text.strip()
		try:
			if type(cookie) == dict:
				cookie = json.dumps(cookie, ensure_ascii=False)
		except:
			pass
		_, _, _ = self.getCookie(cookie)
		bblogin = self.getCache('bblogin')
		if bblogin:
			result['class'] = []
		else:
			result['class'] = []
		if 'json' in self.extendDict:
			r = self.fetch(self.extendDict['json'], timeout=10)
			params = r.json()
			if 'classes' in params:
				result['class'] = result['class'] + params['classes']
			if filter:
				if 'filter' in params:
					result['filters'] = params['filter']
		elif 'categories' in self.extendDict or 'type' in self.extendDict:
			if 'categories' in self.extendDict:
				cateList = self.extendDict['categories'].split('#')
			else:
				cateList = self.extendDict['type'].split('#')
			for cate in cateList:
				result['class'].append({'type_name': cate, 'type_id': cate})
		if not 'class' in result or result['class'] == []:
			result['class'] = [{"type_name":"傻屌仙逆","type_id":"沙雕仙逆"},{"type_name":"沙雕动画","type_id":"沙雕动画"},{"type_name":"纪录片","type_id":"纪录片超清"},{"type_name":"演唱会","type_id":"演唱会超清"},{"type_name":"流行音乐","type_id":"音乐超清"},{"type_name":"美食","type_id":"美食超清"},{"type_name":"食谱","type_id":"食谱"},{"type_name":"体育","type_id":"体育超清"},{"type_name":"球星","type_id":"球星"},{"type_name":"教育","type_id":"中小学教育"},{"type_name":"幼儿教育","type_id":"幼儿教育"},{"type_name":"旅游","type_id":"旅游"},{"type_name":"风景","type_id":"风景4K"},{"type_name":"说案","type_id":"说案"},{"type_name":"知名UP主","type_id":"知名UP主"},{"type_name":"探索发现","type_id":"探索发现超清"},{"type_name":"鬼畜","type_id":"鬼畜"},{"type_name":"搞笑","type_id":"搞笑超清"},{"type_name":"儿童","type_id":"儿童超清"},{"type_name":"动物世界","type_id":"动物世界超清"},{"type_name":"相声小品","type_id":"相声小品超清"},{"type_name":"戏曲","type_id":"戏曲"},{"type_name":"解说","type_id":"解说"},{"type_name":"演讲","type_id":"演讲"},{"type_name":"小姐姐","type_id":"小姐姐超清"},{"type_name":"荒野求生","type_id":"荒野求生超清"},{"type_name":"健身","type_id":"健身"},{"type_name":"帕梅拉","type_id":"帕梅拉"},{"type_name":"太极拳","type_id":"太极拳"},{"type_name":"广场舞","type_id":"广场舞"},{"type_name":"舞蹈","type_id":"舞蹈"},{"type_name":"音乐","type_id":"音乐"},{"type_name":"歌曲","type_id":"歌曲"},{"type_name":"MV","type_id":"MV4K"},{"type_name":"舞曲","type_id":"舞曲超清"},{"type_name":"4K","type_id":"4K"},{"type_name":"电影","type_id":"电影"},{"type_name":"电视剧","type_id":"电视剧"},{"type_name":"白噪音","type_id":"白噪音超清"},{"type_name":"考公考证","type_id":"考公考证"},{"type_name":"平面设计教学","type_id":"平面设计教学"},{"type_name":"软件教程","type_id":"软件教程"},{"type_name":"Windows","type_id":"Windows"}]
		return result

	def homeVideoContent(self):
		result = {}
		cookie = ''
		if 'cookie' in self.extendDict:
			cookie = self.extendDict['cookie']
		if 'json' in self.extendDict:
			r = self.fetch(self.extendDict['json'], timeout=10)
			if 'cookie' in r.json():
				cookie = r.json()['cookie']
		if cookie == '':
			cookie = '{}'
		elif type(cookie) == str and cookie.startswith('http'):
			cookie = self.fetch(cookie, timeout=10).text.strip()
		try:
			if type(cookie) == dict:
				cookie = json.dumps(cookie, ensure_ascii=False)
		except:
			pass
		cookie, imgKey, subKey = self.getCookie(cookie)
		url = 'https://api.bilibili.com/x/web-interface/index/top/feed/rcmd?y_num=1&fresh_type=3&feed_version=SEO_VIDEO&fresh_idx_1h=1&fetch_row=1&fresh_idx=1&brush=0&homepage_ver=1&ps=20'
		r = requests.get(url, cookies=cookie, headers=self.header, timeout=5)
		data = json.loads(self.cleanText(r.text))
		try:
			result['list'] = []
			vodList = data['data']['item']
			for vod in vodList:
				aid = str(vod['id']).strip()
				title = self.removeHtmlTags(vod['title']).strip()
				img = vod['pic'].strip()
				remark = time.strftime('%H:%M:%S', time.gmtime(vod['duration']))
				if remark.startswith('00:'):
					remark = remark[3:]
				if remark == '00:00':
					continue
				result['list'].append({
					'vod_id': aid,
					'vod_name': title,
					'vod_pic': img,
					'vod_remarks': remark
				})
		except:
			pass
		return result

	def categoryContent(self, cid, page, filter, ext):
		page = int(page)
		result = {}
		videos = []
		cookie = ''
		pagecount = page
		if 'cookie' in self.extendDict:
			cookie = self.extendDict['cookie']
		if 'json' in self.extendDict:
			r = self.fetch(self.extendDict['json'], timeout=10)
			if 'cookie' in r.json():
				cookie = r.json()['cookie']
		if cookie == '':
			cookie = '{}'
		elif type(cookie) == str and cookie.startswith('http'):
			cookie = self.fetch(cookie, timeout=10).text.strip()
		try:
			if type(cookie) == dict:
				cookie = json.dumps(cookie, ensure_ascii=False)
		except:
			pass
		cookie, imgKey, subKey = self.getCookie(cookie)
		if cid == '动态':
			if page > 1:
				offset = self.getCache('offset')
				if not offset:
					offset = ''
				url = f'https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/all?timezone_offset=-480&type=all&offset={offset}&page={page}'
			else:
				url = f'https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/all?timezone_offset=-480&type=all&page={page}'
			r = self.fetch(url, cookies=cookie, headers=self.header, timeout=5)
			data = json.loads(self.cleanText(r.text))
			self.setCache('offset', data['data']['offset'])
			vodList = data['data']['items']
			if data['data']['has_more']:
				pagecount = page + 1
			for vod in vodList:
				if vod['type'] != 'DYNAMIC_TYPE_AV':
					continue
				vid = str(vod['modules']['module_dynamic']['major']['archive']['aid']).strip()
				remark = vod['modules']['module_dynamic']['major']['archive']['duration_text'].strip()
				title = self.removeHtmlTags(vod['modules']['module_dynamic']['major']['archive']['title']).strip()
				img = vod['modules']['module_dynamic']['major']['archive']['cover']
				videos.append({
					"vod_id": vid,
					"vod_name": title,
					"vod_pic": img,
					"vod_remarks": remark
				})
		elif cid == "收藏夹":
			userid = self.getUserid(cookie)
			if userid is None:
				return {}, 1
			url = f'http://api.bilibili.com/x/v3/fav/folder/created/list-all?up_mid={userid}&jsonp=jsonp'
			r = self.fetch(url, cookies=cookie, headers=self.header, timeout=5)
			data = json.loads(self.cleanText(r.text))
			vodList = data['data']['list']
			pagecount = page
			for vod in vodList:
				vid = vod['id']
				title = vod['title'].strip()
				remark = vod['media_count']
				img = 'https://api-lmteam.koyeb.app/files/shoucang.png'
				videos.append({
					"vod_id": f'fav&&&{vid}',
					"vod_name": title,
					"vod_pic": img,
					"vod_tag": 'folder',
					"vod_remarks": remark
				})
		elif cid.startswith('fav&&&'):
			cid = cid[6:]
			url = f'http://api.bilibili.com/x/v3/fav/resource/list?media_id={cid}&pn={page}&ps=20&platform=web&type=0'
			r = self.fetch(url, cookies=cookie, headers=self.header, timeout=5)
			data = json.loads(self.cleanText(r.text))
			if data['data']['has_more']:
				pagecount = page + 1
			else:
				pagecount = page
			vodList = data['data']['medias']
			for vod in vodList:
				vid = str(vod['id']).strip()
				title = self.removeHtmlTags(vod['title']).replace("&quot;", '"')
				img = vod['cover'].strip()
				remark = time.strftime('%H:%M:%S', time.gmtime(vod['duration']))
				if remark.startswith('00:'):
					remark = remark[3:]
				videos.append({
					"vod_id": vid,
					"vod_name": title,
					"vod_pic": img,
					"vod_remarks": remark
				})
		elif cid.startswith('UP主&&&'):
			cid = cid[6:]
			params = {'mid': cid, 'ps': 30, 'pn': page}
			params = self.encWbi(params, imgKey, subKey)
			url = 'https://api.bilibili.com/x/space/wbi/arc/search?'
			for key in params:
				url += f'&{key}={quote(params[key])}'
			r = self.fetch(url, cookies=cookie, headers=self.header, timeout=5)
			data = json.loads(self.cleanText(r.text))
			if page < data['data']['page']['count']:
				pagecount = page + 1
			else:
				pagecount = page
			if page == 1:
				videos = [{"vod_id": f'UP主&&&{tid}', "vod_name": '播放列表'}]
			vodList = data['data']['list']['vlist']
			for vod in vodList:
				vid = str(vod['aid']).strip()
				title = self.removeHtmlTags(vod['title']).replace("&quot;", '"')
				img = vod['pic'].strip()
				remarkinfos = vod['length'].split(':')
				minutes = int(remarkinfos[0])
				if minutes >= 60:
					hours = str(minutes // 60)
					minutes = str(minutes % 60)
					if len(hours) == 1:
						hours = '0' + hours
					if len(minutes) == 1:
						minutes = '0' + minutes
					remark = hours + ':' + minutes + ':' + remarkinfos[1]
				else:
					remark = vod['length']
				videos.append({
					"vod_id": vid,
					"vod_name": title,
					"vod_pic": img,
					"vod_remarks": remark
				})
		elif cid == '历史记录':
			url = f'http://api.bilibili.com/x/v2/history?pn={page}'
			r = self.fetch(url, cookies=cookie, headers=self.header, timeout=5)
			data = json.loads(self.cleanText(r.text))
			if len(data['data']) == 300:
				pagecount = page + 1
			else:
				pagecount = page
			vodList = data['data']
			for vod in vodList:
				if vod['duration'] <= 0:
					continue
				vid = str(vod["aid"]).strip()
				img = vod["pic"].strip()
				title = self.removeHtmlTags(vod["title"]).replace("&quot;", '"')
				if vod['progress'] != -1:
					process = time.strftime('%H:%M:%S', time.gmtime(vod['progress']))
					totalTime = time.strftime('%H:%M:%S', time.gmtime(vod['duration']))
					if process.startswith('00:'):
						process = process[3:]
					if totalTime.startswith('00:'):
						totalTime = totalTime[3:]
					remark = process + '|' + totalTime
					videos.append({
						"vod_id": vid,
						"vod_name": title,
						"vod_pic": img,
						"vod_remarks": remark
					})
		else:
			url = 'https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword={}&page={}'
			for key in ext:
				if key == 'tid':
					cid = ext[key]
					continue
				url += f'&{key}={ext[key]}'
			url = url.format(cid, page)
			r = self.fetch(url, cookies=cookie, headers=self.header, timeout=5)
			data = json.loads(self.cleanText(r.text))
			pagecount = data['data']['numPages']
			vodList = data['data']['result']
			for vod in vodList:
				if vod['type'] != 'video':
					continue
				vid = str(vod['aid']).strip()
				title = self.removeHtmlTags(self.cleanText(vod['title']))
				img = 'https:' + vod['pic'].strip()
				remarkinfo = vod['duration'].split(':')
				minutes = int(remarkinfo[0])
				seconds = remarkinfo[1]
				if len(seconds) == 1:
					seconds = '0' + seconds
				if minutes >= 60:
					hour = str(minutes // 60)
					minutes = str(minutes % 60)
					if len(hour) == 1:
						hour = '0' + hour
					if len(minutes) == 1:
						minutes = '0' + minutes
					remark = f'{hour}:{minutes}:{seconds}'
				else:
					minutes = str(minutes)
					if len(minutes) == 1:
						minutes = '0' + minutes
					remark = f'{minutes}:{seconds}'
				videos.append({
					"vod_id": vid,
					"vod_name": title,
					"vod_pic": img,
					"vod_remarks": remark
				})
		lenvideos = len(videos)
		result['list'] = videos
		result['page'] = page
		result['pagecount'] = pagecount
		result['limit'] = lenvideos
		result['total'] = lenvideos
		return result

	def detailContent(self, did):
		aid = did[0]
		if aid.startswith('UP主&&&'):
			bizId = aid[6:]
			oid = ''
			url = f'https://api.bilibili.com/x/v2/medialist/resource/list?mobi_app=web&type=1&oid={oid}&biz_id={bizId}&otype=1&ps=100&direction=false&desc=true&sort_field=1&tid=0&with_current=false'
			r = self.fetch(url, headers=self.header, timeout=5)
			videoList = r.json()['data']['media_list']
			vod = {
				"vod_id": aid,
				"vod_name": '播放列表',
				'vod_play_from': 'B站视频'
			}
			playUrl = ''
			for video in videoList:
				remark = time.strftime('%H:%M:%S', time.gmtime(video['duration']))
				name = self.removeHtmlTags(video['title']).strip().replace("#", "-").replace('$', '*')
				if remark.startswith('00:'):
					remark = remark[3:]
				playUrl += f"[{remark}]/{name}$bvid&&&{video['bv_id']}#"
			vod['vod_play_url'] = playUrl.strip('#')
			result = {'list': [vod]}
			return result
		url = f"https://api.bilibili.com/x/web-interface/view?aid={aid}"
		r = self.fetch(url, headers=self.header, timeout=10)
		data = json.loads(self.cleanText(r.text))
		if "staff" in data['data']:
			director = ''
			for staff in data['data']['staff']:
				director += '[a=cr:{{"id":"UP主&&&{}","name":"{}"}}/]{}[/a],'.format(staff['mid'], staff['name'], staff['name'])
		else:
			director = '[a=cr:{{"id":"UP主&&&{}","name":"{}"}}/]{}[/a]'.format(data['data']['owner']['mid'], data['data']['owner']['name'], data['data']['owner']['name'])
		vod = {
			"vod_id": aid,
			"vod_name": self.removeHtmlTags(data['data']['title']),
			"vod_pic": data['data']['pic'],
			"type_name": data['data']['tname'],
			"vod_year": datetime.fromtimestamp(data['data']['pubdate']).strftime('%Y-%m-%d %H:%M:%S'),
			"vod_content": data['data']['desc'].replace('\xa0', ' ').replace('\n\n', '\n').strip(),
			"vod_director": director
		}
		videoList = data['data']['pages']
		playUrl = ''
		for video in videoList:
			remark = time.strftime('%H:%M:%S', time.gmtime(video['duration']))
			name = self.removeHtmlTags(video['part']).strip().replace("#", "-").replace('$', '*')
			if remark.startswith('00:'):
				remark = remark[3:]
			playUrl = playUrl + f"[{remark}]/{name}${aid}_{video['cid']}#"
		url = f'https://api.bilibili.com/x/web-interface/archive/related?aid={aid}'
		r = self.fetch(url, headers=self.header, timeout=5)
		data = json.loads(self.cleanText(r.text))
		videoList = data['data']
		playUrl = playUrl.strip('#') + '$$$'
		for video in videoList:
			remark = time.strftime('%H:%M:%S', time.gmtime(video['duration']))
			if remark.startswith('00:'):
				remark = remark[3:]
			name = self.removeHtmlTags(video['title']).strip().replace("#", "-").replace('$', '*')
			playUrl = playUrl + '[{}]/{}${}_{}#'.format(remark, name, video['aid'], video['cid'])
		vod['vod_play_from'] = 'B站视频$$$相关视频'
		vod['vod_play_url'] = playUrl.strip('#')
		result = {
			'list': [
				vod
			]
		}
		return result

	def searchContent(self, key, quick):
		return self.searchContentPage(key, quick, '1')

	def searchContentPage(self, key, quick, page):
		videos = []
		if quick:
			result = {
				'list': videos
			}
			return result
		cookie = ''
		if 'cookie' in self.extendDict:
			cookie = self.extendDict['cookie']
		if 'json' in self.extendDict:
			r = self.fetch(self.extendDict['json'], timeout=10)
			if 'cookie' in r.json():
				cookie = r.json()['cookie']
		if cookie == '':
			cookie = '{}'
		elif type(cookie) == str and cookie.startswith('http'):
			cookie = self.fetch(cookie, timeout=10).text.strip()
		try:
			if type(cookie) == dict:
				cookie = json.dumps(cookie, ensure_ascii=False)
		except:
			pass
		cookie, _, _ = self.getCookie(cookie)
		url = f'https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword={key}&page={page}'
		r = self.fetch(url, headers=self.header, cookies=cookie, timeout=5)
		jo = json.loads(self.cleanText(r.text))
		if 'result' not in jo['data']:
			return {'list': videos}, 1
		vodList = jo['data']['result']
		for vod in vodList:
			aid = str(vod['aid']).strip()
			title = self.removeHtmlTags(self.cleanText(vod['title']))
			img = 'https:' + vod['pic'].strip()
			try:
				remarkinfo = vod['duration'].split(':')
				minutes = int(remarkinfo[0])
				seconds = remarkinfo[1]
			except:
				continue
			if len(seconds) == 1:
				seconds = '0' + seconds
			if minutes >= 60:
				hour = str(minutes // 60)
				minutes = str(minutes % 60)
				if len(hour) == 1:
					hour = '0' + hour
				if len(minutes) == 1:
					minutes = '0' + minutes
				remark = f'{hour}:{minutes}:{seconds}'
			else:
				minutes = str(minutes)
				if len(minutes) == 1:
					minutes = '0' + minutes
				remark = f'{minutes}:{seconds}'
			videos.append({
				"vod_id": aid,
				"vod_name": title,
				"vod_pic": img,
				"vod_remarks": remark
			})
		result = {
			'list': videos
		}
		return result

	def playerContent(self, flag, pid, vipFlags):
		result = {}
		if pid.startswith('bvid&&&'):
			url = "https://api.bilibili.com/x/web-interface/view?bvid={}".format(pid[7:])
			r = self.fetch(url, headers=self.header, timeout=10)
			data = r.json()['data']
			aid = data['aid']
			cid = data['cid']
		else:
			idList = pid.split("_")
			aid = idList[0]
			cid = idList[1]
		url = 'https://api.bilibili.com/x/player/playurl?avid={}&cid={}&qn=120&fnval=4048&fnver=0&fourk=1'.format(aid, cid)
		cookie = ''
		extendDict = self.extendDict
		if 'cookie' in extendDict:
			cookie = extendDict['cookie']
		if 'json' in extendDict:
			r = self.fetch(extendDict['json'], timeout=10)
			if 'cookie' in r.json():
				cookie = r.json()['cookie']
		if cookie == '':
			cookie = '{}'
		elif type(cookie) == str and cookie.startswith('http'):
			cookie = self.fetch(cookie, timeout=10).text.strip()
		try:
			if type(cookie) == dict:
				cookie = json.dumps(cookie, ensure_ascii=False)
		except:
			pass
		cookiesDict, _, _ = self.getCookie(cookie)
		cookies = quote(json.dumps(cookiesDict))
		if 'thread' in extendDict:
			thread = str(extendDict['thread'])
		else:
			thread = '0'
		result["parse"] = 0
		result["playUrl"] = ''
		result["url"] = f'http://127.0.0.1:9978/proxy?do=py&type=mpd&cookies={cookies}&url={quote(url)}&aid={aid}&cid={cid}&thread={thread}'
		result["header"] = self.header
		result['danmaku'] = 'https://api.bilibili.com/x/v1/dm/list.so?oid={}'.format(cid)
		result["format"] = 'application/dash+xml'
		return result

	def localProxy(self, params):
		if params['type'] == "mpd":
			return self.proxyMpd(params)
		if params['type'] == "media":
			return self.proxyMedia(params)
		return None

	def destroy(self):
		pass

	def proxyMpd(self, params):
		content, durlinfos, mediaType = self.getDash(params)
		if mediaType == 'mpd':
			return [200, "application/dash+xml", content]
		else:
			url = ''
			urlList = [content] + durlinfos['durl'][0]['backup_url'] if 'backup_url' in durlinfos['durl'][0] and durlinfos['durl'][0]['backup_url'] else [content]
			for url in urlList:
				if 'mcdn.bilivideo.cn' not in url:
					break
			header = self.header.copy()
			if 'range' in params:
				header['Range'] = params['range']
			if '127.0.0.1:7777' in url:
				header["Location"] = url
				return [302, "video/MP2T", None, header]
			r = requests.get(url, headers=header, stream=True)
			return [206, "application/octet-stream", r.content]

	def proxyMedia(self, params, forceRefresh=False):
		_, dashinfos, _ = self.getDash(params)
		if 'videoid' in params:
			videoid = int(params['videoid'])
			dashinfo = dashinfos['video'][videoid]
		elif 'audioid' in params:
			audioid = int(params['audioid'])
			dashinfo = dashinfos['audio'][audioid]
		else:
			return [404, "text/plain", ""]
		url = ''
		urlList = [dashinfo['baseUrl']] + dashinfo['backupUrl'] if 'backupUrl' in dashinfo and dashinfo['backupUrl'] else [dashinfo['baseUrl']]
		for url in urlList:
			if 'mcdn.bilivideo.cn' not in url:
				break
		if url == "":
			return [404, "text/plain", ""]
		header = self.header.copy()
		if 'range' in params:
			header['Range'] = params['range']
		r = requests.get(url, headers=header, stream=True)
		return [206, "application/octet-stream", r.content]

	def getDash(self, params, forceRefresh=False):
		aid = params['aid']
		cid = params['cid']
		url = unquote(params['url'])
		if 'thread' in params:
			thread = params['thread']
		else:
			thread = 0
		header = self.header.copy()
		cookieDict = json.loads(params['cookies'])
		key = f'bilivdmpdcache_{aid}_{cid}'
		if forceRefresh:
			self.delCache(key)
		else:
			data = self.getCache(key)
			if data:
				return data['content'], data['dashinfos'], data['type']

		cookies = cookieDict.copy()
		r = self.fetch(url, cookies=cookies, headers=header, timeout=5)
		data = json.loads(self.cleanText(r.text))
		if data['code'] != 0:
			return '', {}, ''
		if not 'dash' in data['data']:
			purl = data['data']['durl'][0]['url']
			try:
				expiresAt = int(re.search(r'deadline=(\d+)', purl).group(1)) - 60
			except:
				expiresAt = int(time.time()) + 600
			if int(thread) > 0:
				try:
					self.fetch('http://127.0.0.1:7777')
				except:
					self.fetch('http://127.0.0.1:9978/go')
				purl = f'http://127.0.0.1:7777?url={quote(purl)}&thread={thread}'
			self.setCache(key, {'content': purl, 'type': 'mp4', 'dashinfos':  data['data'], 'expiresAt': expiresAt})
			return purl,  data['data'], 'mp4'

		dashinfos = data['data']['dash']
		duration = dashinfos['duration']
		minBufferTime = dashinfos['minBufferTime']
		videoinfo = ''
		videoid = 0
		deadlineList = []
		for video in dashinfos['video']:
			try:
				deadline = int(re.search(r'deadline=(\d+)', video['baseUrl']).group(1))
			except:
				deadline = int(time.time()) + 600
			deadlineList.append(deadline)
			codecs = video['codecs']
			bandwidth = video['bandwidth']
			frameRate = video['frameRate']
			height = video['height']
			width = video['width']
			void = video['id']
			vidparams = params.copy()
			vidparams['videoid'] = videoid
			baseUrl = f'http://127.0.0.1:9978/proxy?do=py&type=media&cookies={quote(json.dumps(cookies))}&url={quote(url)}&aid={aid}&cid={cid}&videoid={videoid}'
			videoinfo = videoinfo + f"""	      <Representation bandwidth="{bandwidth}" codecs="{codecs}" frameRate="{frameRate}" height="{height}" id="{void}" width="{width}">
	        <BaseURL>{baseUrl}</BaseURL>
	        <SegmentBase indexRange="{video['SegmentBase']['indexRange']}">
	        <Initialization range="{video['SegmentBase']['Initialization']}"/>
	        </SegmentBase>
	      </Representation>\n"""
			videoid += 1
		audioinfo = ''
		audioid = 0
		# audioList = sorted(dashinfos['audio'], key=lambda x: x['bandwidth'], reverse=True)
		for audio in dashinfos['audio']:
			try:
				deadline = int(re.search(r'deadline=(\d+)', audio['baseUrl']).group(1))
			except:
				deadline = int(time.time()) + 600
			deadlineList.append(deadline)
			bandwidth = audio['bandwidth']
			codecs = audio['codecs']
			aoid = audio['id']
			aidparams = params.copy()
			aidparams['audioid'] = audioid
			baseUrl = f'http://127.0.0.1:9978/proxy?do=py&type=media&cookies={quote(json.dumps(cookies))}&url={quote(url)}&aid={aid}&cid={cid}&audioid={audioid}'
			audioinfo = audioinfo + f"""	      <Representation audioSamplingRate="44100" bandwidth="{bandwidth}" codecs="{codecs}" id="{aoid}">
	        <BaseURL>{baseUrl}</BaseURL>
	        <SegmentBase indexRange="{audio['SegmentBase']['indexRange']}">
	        <Initialization range="{audio['SegmentBase']['Initialization']}"/>
	        </SegmentBase>
	      </Representation>\n"""
			audioid += 1
		mpd = f"""<?xml version="1.0" encoding="UTF-8"?>
	<MPD xmlns="urn:mpeg:dash:schema:mpd:2011" profiles="urn:mpeg:dash:profile:isoff-on-demand:2011" type="static" mediaPresentationDuration="PT{duration}S" minBufferTime="PT{minBufferTime}S">
	  <Period>
	    <AdaptationSet mimeType="video/mp4" startWithSAP="1" scanType="progressive" segmentAlignment="true">
	      {videoinfo.strip()}
	    </AdaptationSet>
	    <AdaptationSet mimeType="audio/mp4" startWithSAP="1" segmentAlignment="true" lang="und">
	      {audioinfo.strip()}
	    </AdaptationSet>
	  </Period>
	</MPD>"""
		expiresAt = min(deadlineList) - 60
		self.setCache(key, {'type': 'mpd', 'content': mpd.replace('&', '&amp;'), 'dashinfos': dashinfos, 'expiresAt': expiresAt})
		return mpd.replace('&', '&amp;'), dashinfos, 'mpd'

	def getCookie(self, cookie):
		if '{' in cookie and '}' in cookie:
			cookies = json.loads(cookie)
		else:
			cookies = dict([co.strip().split('=', 1) for co in cookie.strip(';').split(';')])
		bblogin = self.getCache('bblogin')
		if bblogin:
			imgKey = bblogin['imgKey']
			subKey = bblogin['subKey']
			return cookies, imgKey, subKey

		header = {
			"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.54 Safari/537.36"
		}
		r = requests.get("http://api.bilibili.com/x/web-interface/nav", cookies=cookies, headers=header, timeout=10)
		data = json.loads(r.text)
		code = data["code"]
		if code == 0:
			imgKey = data['data']['wbi_img']['img_url'].rsplit('/', 1)[1].split('.')[0]
			subKey = data['data']['wbi_img']['sub_url'].rsplit('/', 1)[1].split('.')[0]
			self.setCache('bblogin', {'imgKey': imgKey, 'subKey': subKey, 'expiresAt': int(time.time()) + 1200})
			return cookies, imgKey, subKey
		r = self.fetch("https://www.bilibili.com/", headers=header, timeout=5)
		cookies = r.cookies.get_dict()
		imgKey = ''
		subKey = ''
		return cookies, imgKey, subKey

	def getUserid(self, cookie):
		# 获取自己的userid(cookies拥有者)
		url = 'http://api.bilibili.com/x/space/myinfo'
		r = self.fetch(url, cookies=cookie, headers=self.header, timeout=5)
		data = json.loads(self.cleanText(r.text))
		if data['code'] == 0:
			return data['data']['mid']

	def removeHtmlTags(self, src):
		from re import sub, compile
		clean = compile('<.*?>')
		return sub(clean, '', src)

	def encWbi(self, params, imgKey, subKey):
		from hashlib import md5
		from functools import reduce
		from urllib.parse import urlencode
		mixinKeyEncTab = [46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52]
		orig = imgKey + subKey
		mixinKey = reduce(lambda s, i: s + orig[i], mixinKeyEncTab, '')[:32]
		params['wts'] = round(time.time())  # 添加 wts 字段
		params = dict(sorted(params.items()))  # 按照 key 重排参数
		# 过滤 value 中的 "!'()*" 字符
		params = {
			k: ''.join(filter(lambda chr: chr not in "!'()*", str(v)))
			for k, v
			in params.items()
		}
		query = urlencode(params)  # 序列化参数
		params['w_rid'] = md5((query + mixinKey).encode()).hexdigest()  # 计算 w_rid
		return params

	retry = 0
	header = {
		"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.54 Safari/537.36",
		"Referer": "https://www.bilibili.com"
	}

