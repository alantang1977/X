#coding=utf-8
#!/usr/bin/python
import sys
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
	def init(self,extend=""):
		self.base_url='http://api.hclyz.com:81/mf'

	def homeContent(self,filter):
		classes = [{"type_name": "色播聚合","type_id":"/json.txt"}]
		result = {"class": classes}
		return result

	def categoryContent(self,tid,pg,filter,extend):
		home = self.fetch(f'{self.base_url}/json.txt').json()
		data = home.get("pingtai")[1:]
		videos = [
			{
				"vod_id": "/" + item['address'],
				"vod_name": item['title'],
				"vod_pic": item['xinimg'].replace("http://cdn.gcufbd.top/img/",
												  "https://slink.ltd/https://raw.githubusercontent.com/fish2018/lib/refs/heads/main/imgs/"),
				"vod_remarks": item['Number'],
				"style": {"type": "rect", "ratio": 1.33}
			} for item in sorted(data, key=lambda x: int(x['Number']), reverse=True)
		]
		result = {
			"page": pg,
			"pagecount": 1,
			"limit": len(videos),
			"total": len(videos),
			"list": videos
		}
		return result

	def detailContent(self,array):
		id = array[0]
		data = self.fetch(f'{self.base_url}/{id}').json()
		zhubo = data['zhubo']
		playUrls = '#'.join([f"{vod['title']}${vod['address']}" for vod in zhubo])
		vod = [{
			"vod_play_from": 'sebo',
			"vod_play_url": playUrls,
			"vod_content": 'https://github.com/fish2018',
		}]
		result = {"list": vod}
		return result

	def playerContent(self,flag,id,vipFlags):
		result = {
			'parse': 0,
			'url': id
		}
		return result

	def getName(self):
		return '色播聚合'

	def homeVideoContent(self):
		pass
	def isVideoFormat(self,url):
		pass
	def manualVideoCheck(self):
		pass
	def searchContent(self,key,quick):
		pass
	def destroy(self):
		pass
	def localProxy(self, param):
		pass