# coding=utf-8
#!/usr/bin/python
import sys
import json
import re
import requests
import urllib.parse
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# 忽略SSL证书警告
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# 基础爬虫类
try:
    sys.path.append('..')
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        def __init__(self):
            self.logs = []
        
        def log(self, msg):
            print(f"[LOG] {msg}")
            self.logs.append(msg)
        
        def fetch(self, url, headers=None, timeout=15):
            try:
                response = requests.get(
                    url,
                    headers=headers or {},
                    timeout=timeout,
                    verify=False,
                    allow_redirects=True
                )
                return response
            except Exception as e:
                self.log(f"请求失败: {str(e)}")
                return None


class Spider(BaseSpider):
    def getName(self):
        """定义爬虫名称"""
        return "影视工厂"
    
    def init(self, extend=""):
        """初始化：域名、请求头、编码"""
        self.host = "https://ylsp.tv"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': self.host,
            'Accept-Encoding': 'gzip, deflate'
        }
        self.encoding = "UTF-8"
        self.last_search_key = ""  # 记录最后一次搜索关键词
        self.log(f"影视工厂爬虫初始化完成，主站: {self.host}")

    def isVideoFormat(self, url):
        """校验是否为视频地址"""
        return any(ext in url.lower() for ext in ['.m3u8', '.mp4', '.flv', '.avi', '.mov'])

    def manualVideoCheck(self):
        """预留：手动视频校验逻辑"""
        return True

    # -------------------------- 首页与分类内容 --------------------------
    def homeContent(self, filter):
        result = {"class": [], "filters": [], "list": []}
        # 1. 分类配置
        result['class'] = [
            {'type_id': '1', 'type_name': '电影'},
            {'type_id': '2', 'type_name': '剧集'},
            {'type_id': '3', 'type_name': '综艺'},
            {'type_id': '4', 'type_name': '动漫'}
        ]
        # 2. 筛选配置
        result['filters'] = self._get_filters()
        # 3. 首页推荐列表
        try:
            rsp = self.fetch(self.host, headers=self.headers)
            if rsp and rsp.status_code == 200:
                html = rsp.text if rsp.encoding else rsp.content.decode(self.encoding, errors='ignore')
                videos = self._extract_videos_from_html(html)
                result['list'] = videos[:20]
                self.log(f"首页提取到{len(result['list'])}条推荐数据")
        except Exception as e:
            self.log(f"首页获取出错: {str(e)}")
        return result

    def homeVideoContent(self):
        """首页视频内容"""
        return self.homeContent(False)

    def categoryContent(self, tid, pg, filter, extend):
        """分类内容"""
        result = {"list": [], "page": int(pg), "pagecount": 99, "limit": 20, "total": 1980}
        try:
            url = f"{self.host}/vodtype/{tid}/" if int(pg) == 1 else f"{self.host}/vodtype/{tid}/page/{pg}/"
            self.log(f"请求分类页: {url}")
            
            rsp = self.fetch(url, headers=self.headers)
            if rsp and rsp.status_code == 200:
                html = rsp.text if rsp.encoding else rsp.content.decode(self.encoding, errors='ignore')
                videos = self._extract_videos_from_html(html)
                result['list'] = videos
                result['total'] = len(videos) * result['pagecount']
                self.log(f"分类页{pg}提取到{len(videos)}条数据")
        except Exception as e:
            self.log(f"分类内容获取出错: {str(e)}")
        return result

    def searchContent(self, key, quick, pg=1):
        """搜索功能：修复搜索页面解析"""
        result = {"list": []}
        try:
            self.last_search_key = key  # 记录搜索关键词
            search_key = urllib.parse.quote(key)
            search_url = f"{self.host}/vodsearch/{search_key}-------------/" if int(pg) == 1 else f"{self.host}/vodsearch/{search_key}-------------/page/{pg}/"
            self.log(f"搜索URL: {search_url}")
            
            rsp = self.fetch(search_url, headers=self.headers)
            if rsp and rsp.status_code == 200:
                html = rsp.text if rsp.encoding else rsp.content.decode(self.encoding, errors='ignore')
                
                # 使用新的解析方法处理搜索页面
                videos = self._extract_search_results_from_html(html)
                result['list'] = videos
                self.log(f"搜索'{key}'第{pg}页提取到{len(videos)}条数据")
            else:
                self.log(f"搜索请求失败，状态码: {rsp.status_code if rsp else '无响应'}")
        except Exception as e:
            self.log(f"搜索出错: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
        return result

    # -------------------------- 详情页 --------------------------
    def detailContent(self, ids):
        """获取影视详情：适配新的播放线路结构"""
        result = {"list": []}
        try:
            vid = ids[0]
            detail_url = f"{self.host}/voddetail/{vid}/"
            self.log(f"请求详情页: {detail_url}")
            
            rsp = self.fetch(detail_url, headers=self.headers)
            if not rsp or rsp.status_code != 200:
                raise Exception(f"详情页请求失败，状态码: {rsp.status_code if rsp else '无响应'}")
            html = rsp.text if rsp.encoding else rsp.content.decode(self.encoding, errors='ignore')

            # 1. 提取播放线路列表
            play_from = []  # 线路名称
            play_url = []   # 线路对应的集数链接
            
            # 1.1 提取所有线路
            line_pattern = r'<(?:div|a)[^>]*class="[^"]*module-tab-item[^"]*"[^>]*>(?:.*?<span>([^<]+)</span>.*?<small>(\d+)</small>|.*?<span>([^<]+)</span>.*?<small class="no">(\d+)</small>)</(?:div|a)>'
            line_matches = re.findall(line_pattern, html, re.S | re.I)
            
            # 1.2 为每条线路提取集数链接
            for match in line_matches:
                # 处理两种匹配结果格式
                if match[0]:  # 第一种格式: a标签
                    line_name, ep_total = match[0], match[1]
                else:  # 第二种格式: div标签
                    line_name, ep_total = match[2], match[3]
                
                if line_name in play_from:
                    continue  # 避免重复线路
                    
                play_from.append(line_name)
                
                # 尝试从href属性提取线路ID
                line_id_pattern = r'<a[^>]*href="/play/%s-(\d+)-1/"[^>]*>.*?<span>%s</span>' % (vid, re.escape(line_name))
                line_id_match = re.search(line_id_pattern, html, re.S | re.I)
                
                if line_id_match:
                    line_id = line_id_match.group(1)
                else:
                    # 如果没有找到href，使用默认线路ID（根据线路名称映射）
                    line_id_map = {
                        "全球3线": "3",
                        "大陆0线": "1",
                        "大陆3线": "4",
                        "大陆5线": "2",
                        "大陆6线": "3"
                    }
                    line_id = line_id_map.get(line_name, "1")  # 默认使用1
                
                # 匹配该线路下所有集数
                ep_pattern = r'<a class="module-play-list-link" href="/play/%s-%s-(\d+)/"[^>]*>.*?<span>([^<]+)</span></a>' % (vid, line_id)
                ep_matches = re.findall(ep_pattern, html, re.S | re.I)
                
                # 整理集数格式："集数名$播放参数"
                eps = [f"{ep_name.strip()}${vid}-{line_id}-{ep_num.strip()}" for ep_num, ep_name in ep_matches]
                play_url.append("#".join(eps))

            # 2. 提取基础信息
            # 2.1 标题
            title_match = re.search(r'<meta property="og:title" content="([^"]+)-[^-]+$"', html, re.S | re.I)
            if not title_match:
                title_match = re.search(r'<h1>.*?<a href="/voddetail/\d+/" title="([^"]+)">', html, re.S | re.I)
            title = title_match.group(1).strip() if title_match else ""

            # 2.2 封面图
            pic_match = re.search(r'<meta property="og:image" content="([^"]+)"', html, re.S | re.I)
            if not pic_match:
                pic_match = re.search(r'<div class="module-item-pic">.*?data-original="([^"]+)"', html, re.S | re.I)
            pic = pic_match.group(1).strip() if pic_match else ""
            if pic and pic.startswith('/'):
                pic = self.host + pic

            # 2.3 简介
            desc_match = re.search(r'<meta property="og:description" content="([^"]+)"', html, re.S | re.I)
            desc = desc_match.group(1).strip() if desc_match else "暂无简介"

            # 2.4 基础备注
            year_match = re.search(r'<a title="(\d+)" href="/vodshow/\d+-----------\1/">', html, re.S | re.I)
            year = year_match.group(1) if year_match else "未知年份"
            area_match = re.search(r'<a title="([^"]+)" href="/vodshow/\d+-%E5%A2%A8%E8%A5%BF%E5%93%A5----------/">', html, re.S | re.I)
            area = area_match.group(1) if area_match else "未知产地"
            type_match = re.search(r'vod_class":"([^"]+)"', html, re.S | re.I)
            type_str = type_match.group(1).replace(",", "/") if type_match else "未知类型"
            remarks = f"{year} | {area} | {type_str} | 共{ep_total}集完结"

            # 3. 整理详情结果
            if play_from:
                result['list'] = [{
                    'vod_id': vid,
                    'vod_name': title,
                    'vod_pic': pic,
                    'vod_content': desc,
                    'vod_remarks': remarks,
                    'vod_play_from': "$$$".join(play_from),
                    'vod_play_url': "$$$".join(play_url)
                }]
                self.log(f"详情页提取到{len(play_from)}条线路: {play_from}")
            else:
                self.log("详情页未提取到播放线路")

        except Exception as e:
            self.log(f"详情获取出错: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            result['list'] = []
        return result

    # -------------------------- 播放页 --------------------------
    def playerContent(self, flag, id, vipFlags):
        """获取播放链接：适配新格式播放参数"""
        result = {"parse": 1, "playUrl": "", "url": "", "header": json.dumps(self.headers)}
        try:
            # 解析id：格式为"剧集ID-线路ID-集数ID"
            if "-" not in id:
                raise Exception(f"播放参数格式错误，应为'剧集ID-线路ID-集数ID'，当前: {id}")
            vid, line_id, ep_id = id.split("-")[:3]
            
            # 线路名称映射
            line_name_map = {
                "1": "大陆0线",
                "2": "大陆5线",
                "3": "大陆6线",
                "4": "大陆3线"
            }
            play_from = line_name_map.get(line_id, f"线路{line_id}")
            
            # 1. 请求播放页
            play_url = f"{self.host}/play/{id}/"
            self.log(f"请求{play_from}第{ep_id}集播放页: {play_url}")
            
            rsp = self.fetch(play_url, headers=self.headers)
            if not rsp or rsp.status_code != 200:
                raise Exception(f"播放页请求失败，状态码: {rsp.status_code if rsp else '无响应'}")
            html = rsp.text if rsp.encoding else rsp.content.decode(self.encoding, errors='ignore')

            # 2. 提取真实播放地址
            real_url_pattern = r'var player_aaaa=.*?"url":"([^"]+\.m3u8)"'
            real_url_match = re.search(real_url_pattern, html, re.S | re.I)
            
            if real_url_match:
                real_url = real_url_match.group(1).strip()
                # 处理转义字符
                real_url = real_url.replace(r'\u002F', '/').replace(r'\/', '/')
                result["parse"] = 0
                result["url"] = real_url
                self.log(f"成功提取{play_from}第{ep_id}集播放地址: {real_url[:60]}...")
            else:
                # 兜底：若未提取到m3u8，返回播放页让播放器自动嗅探
                result["parse"] = 1
                result["url"] = play_url
                self.log("未提取到直接播放地址，返回播放页URL")

        except Exception as e:
            self.log(f"播放链接获取出错: {str(e)}")
            result["url"] = f"{self.host}/play/{id}/" if "-" in id else f"{self.host}/voddetail/{id}/"
        return result

    # -------------------------- 辅助方法 --------------------------
    def _get_filters(self):
        """分类筛选配置"""
        return {
            "1": [{"key": "class", "name": "类型", "value": [
                {"n": "全部", "v": ""}, {"n": "动作片", "v": "6"}, {"n": "喜剧片", "v": "7"},
                {"n": "爱情片", "v": "8"}, {"n": "科幻片", "v": "9"}, {"n": "恐怖片", "v": "11"}
            ]}],
            "2": [{"key": "class", "name": "类型", "value": [
                {"n": "全部", "v": ""}, {"n": "国产剧", "v": "13"}, {"n": "港台剧", "v": "14"},
                {"n": "日剧", "v": "15"}, {"n": "韩剧", "v": "33"}, {"n": "欧美剧", "v": "16"}
            ]}],
            "3": [{"key": "class", "name": "类型", "value": [
                {"n": "全部", "v": ""}, {"n": "内地综艺", "v": "27"}, {"n": "港台综艺", "v": "28"},
                {"n": "日本综艺", "v": "29"}, {"n": "韩国综艺", "v": "36"}
            ]}],
            "4": [{"key": "class", "name": "类型", "value": [
                {"n": "全部", "v": ""}, {"n": "国产动漫", "v": "31"}, {"n": "日本动漫", "v": "32"},
                {"n": "欧美动漫", "v": "42"}, {"n": "其他动漫", "v": "43"}
            ]}]
        }

    def _extract_videos_from_html(self, html):
        """从HTML提取影视列表（首页和分类页）"""
        videos = []
        try:
            # 匹配卡片式布局
            pattern = r'<a href="/voddetail/(\d+)/".*?title="([^"]+)".*?<div class="module-item-note">([^<]+)</div>.*?data-original="([^"]+)"'
            matches = re.findall(pattern, html, re.S | re.I)
            
            for vid, title, remark, pic in matches:
                if pic and pic.startswith('/'):
                    pic = self.host + pic
                videos.append({
                    'vod_id': vid.strip(),
                    'vod_name': title.strip(),
                    'vod_pic': pic.strip(),
                    'vod_remarks': remark.strip()
                })
                
            # 如果没有找到结果，尝试另一种匹配模式
            if not videos:
                pattern = r'<a href="/voddetail/(\d+)/".*?<img.*?src="([^"]+)".*?alt="([^"]+)".*?<div class="module-item-note">([^<]+)</div>'
                matches = re.findall(pattern, html, re.S | re.I)
                
                for vid, pic, title, remark in matches:
                    if pic and pic.startswith('/'):
                        pic = self.host + pic
                    videos.append({
                        'vod_id': vid.strip(),
                        'vod_name': title.strip(),
                        'vod_pic': pic.strip(),
                        'vod_remarks': remark.strip()
                    })
                    
        except Exception as e:
            self.log(f"列表提取出错: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
        return videos

    def _extract_search_results_from_html(self, html):
        """从搜索页面HTML提取搜索结果 - 最终修复版"""
        videos = []
        try:
            # 方法1：匹配卡片式布局（新版）
            card_pattern = r'<div class="module-card-item">.*?<a href="/voddetail/(\d+)/".*?<img.*?(?:data-original|src)="([^"]+)".*?alt="([^"]+)".*?<div class="module-item-note">([^<]+)</div>'
            card_matches = re.findall(card_pattern, html, re.S | re.I)
            
            # 方法2：匹配列表式布局（旧版）
            list_pattern = r'<a href="/voddetail/(\d+)/".*?<img.*?(?:data-original|src)="([^"]+)".*?alt="([^"]+)".*?<div class="module-item-note">([^<]+)</div>'
            list_matches = re.findall(list_pattern, html, re.S | re.I)
            
            # 方法3：匹配更简单的布局（备用）
            simple_pattern = r'<a href="/voddetail/(\d+)/".*?>(.*?)</a>'
            simple_matches = re.findall(simple_pattern, html, re.S | re.I)
            
            # 合并所有匹配结果（优先使用卡片式）
            all_matches = card_matches + list_matches
            
            # 使用字典去重（以视频ID为key）
            video_dict = {}
            for vid, pic, title, remark in all_matches:
                if vid not in video_dict:
                    if pic and pic.startswith('/'):
                        pic = self.host + pic
                    video_dict[vid] = {
                        'vod_id': vid.strip(),
                        'vod_name': title.strip(),
                        'vod_pic': pic.strip(),
                        'vod_remarks': remark.strip()
                    }
            
            # 处理简单匹配结果
            for vid, content in simple_matches:
                if vid not in video_dict:
                    # 从内容中提取标题
                    title_match = re.search(r'alt="([^"]+)"', content)
                    title = title_match.group(1) if title_match else re.sub(r'<.*?>', '', content)
                    
                    # 从内容中提取图片
                    pic_match = re.search(r'(?:data-original|src)="([^"]+)"', content)
                    pic = pic_match.group(1) if pic_match else ""
                    if pic and pic.startswith('/'):
                        pic = self.host + pic
                    
                    # 从内容中提取备注
                    remark_match = re.search(r'<div class="module-item-note">([^<]+)</div>', content)
                    remark = remark_match.group(1) if remark_match else ""
                    
                    video_dict[vid] = {
                        'vod_id': vid.strip(),
                        'vod_name': title.strip(),
                        'vod_pic': pic.strip(),
                        'vod_remarks': remark.strip()
                    }
            
            # 转换为列表并按相关性排序（包含搜索关键词的排前面）
            search_key = self.last_search_key.lower()
            videos = sorted(
                video_dict.values(),
                key=lambda x: (
                    -int(search_key in x['vod_name'].lower()),
                    x['vod_name']
                )
            )
            
            self.log(f"最终提取到{len(videos)}条搜索结果")
            
        except Exception as e:
            self.log(f"搜索列表提取出错: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
        return videos


# -------------------------- 本地测试入口 --------------------------
if __name__ == "__main__":
    # 初始化爬虫
    spider = Spider()
    spider.init()
    
    # 测试搜索功能
    print("\n=== 测试搜索功能：搜索'仙逆' ===")
    search_result = spider.searchContent(key="仙逆", quick=False, pg=1)
    print(f"找到{len(search_result['list'])}条结果:")
    for i, item in enumerate(search_result['list'], 1):
        print(f"{i}. {item['vod_name']} (ID:{item['vod_id']}, 备注:{item['vod_remarks']})")
    
    # 测试详情功能
    if search_result['list']:
        print("\n=== 测试详情功能 ===")
        first_video = search_result['list'][0]
        detail_result = spider.detailContent(ids=[first_video['vod_id']])
        if detail_result['list']:
            detail = detail_result['list'][0]
            print(f"剧集名称: {detail['vod_name']}")
            print(f"播放线路: {detail['vod_play_from'].split('$$$')}")
            print(f"第1条线路前3集: {detail['vod_play_url'].split('$$$')[0].split('#')[:3]}")
    
    print("\n=== 测试完成 ===")