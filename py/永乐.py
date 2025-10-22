# coding=utf-8
#!/usr/bin/env python3
#七哥定制版
import re
import sys
import urllib.parse
import requests
from bs4 import BeautifulSoup

# 禁用SSL证书验证警告
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def getName(self):
        return "永乐视频"
    
    def init(self, extend=""):
        self.host = "https://www.ylys.tv/"
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', 'Referer': self.host}
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update(self.headers)

    def fetch(self, url, timeout=30):
        try:
            response = self.session.get(url, timeout=timeout, verify=False)
            response.encoding = response.encoding if response.encoding != 'ISO-8859-1' else 'UTF-8'
            return response
        except:
            return None

    def homeContent(self, filter):
        result = {
            "class": [{'type_id': str(i), 'type_name': t} for i, t in enumerate(['电影', '剧集', '综艺', '动漫'], 1)],
            "filters": self._get_filters(),
            "list": []
        }
        rsp = self.fetch(self.host)
        if rsp and rsp.status_code == 200:
            result['list'] = self._extract_videos(rsp.text, 20)
        return result

    def categoryContent(self, tid, pg, filter, extend):
        result = {"list": [], "page": int(pg), "pagecount": 99, "limit": 20, "total": 1980}
        url = f"{self.host}/vodtype/{tid}/page/{pg}/" if int(pg) > 1 else f"{self.host}/vodtype/{tid}/"
        rsp = self.fetch(url)
        if rsp and rsp.status_code == 200:
            result['list'] = self._extract_videos(rsp.text)
        return result

    def searchContent(self, key, quick, pg=1):
        result = {"list": []}
        search_key = urllib.parse.quote(key)
        url = f"{self.host}/vodsearch/{search_key}-------------/page/{pg}/" if int(pg) > 1 else f"{self.host}/vodsearch/{search_key}-------------/"
        rsp = self.fetch(url)
        if rsp and rsp.status_code == 200:
            result['list'] = self._extract_search_results(rsp.text)
        return result

    def detailContent(self, ids):
        result = {"list": []}
        vid = ids[0]
        rsp = self.fetch(f"{self.host}/voddetail/{vid}/")
        if not rsp or rsp.status_code != 200:
            return result
            
        html = rsp.text
        play_from, play_url = self._extract_play_info(html, vid)
        
        if play_from:
            result['list'] = [{
                'vod_id': vid,
                'vod_name': self._extract_title(html),
                'vod_pic': self._extract_pic(html),
                'vod_content': self._extract_desc(html),
                'vod_remarks': self._extract_remarks(html),
                'vod_play_from': "$$$".join(play_from),
                'vod_play_url': "$$$".join(play_url)
            }]
        return result

    def playerContent(self, flag, id, vipFlags):
        result = {"parse": 1, "playUrl": "", "url": ""}
        if "-" not in id:
            return result
            
        rsp = self.fetch(f"{self.host}/play/{id}/")
        if not rsp or rsp.status_code != 200:
            return result
            
        real_url_match = re.search(r'var player_aaaa=.*?"url":"([^"]+\.m3u8)"', rsp.text, re.S | re.I)
        if real_url_match:
            real_url = real_url_match.group(1).replace(r'\u002F', '/').replace(r'\/', '/')
            result["parse"] = 0
            result["url"] = real_url
        else:
            result["url"] = f"{self.host}/play/{id}/"
        return result

    def _get_filters(self):
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

    def _extract_videos(self, html, limit=0):
        videos = []
        pattern = r'<a href="/voddetail/(\d+)/".*?title="([^"]+)".*?<div class="module-item-note">([^<]+)</div>.*?data-original="([^"]+)"'
        for vid, title, remark, pic in re.findall(pattern, html, re.S | re.I):
            videos.append({
                'vod_id': vid.strip(),
                'vod_name': title.strip(),
                'vod_pic': (self.host + pic if pic.startswith('/') else pic).strip(),
                'vod_remarks': remark.strip()
            })
        return videos[:limit] if limit and len(videos) > limit else videos

    def _extract_search_results(self, html):
        videos = []
        soup = BeautifulSoup(html, 'html.parser')
        for item in soup.select('.module-card-item'):
            link = item.select_one('a[href^="/voddetail/"]')
            if not link:
                continue
                
            href = link.get('href', '')
            vid_match = re.search(r'/voddetail/(\d+)/', href)
            if not vid_match:
                continue
                
            vid = vid_match.group(1)
            title_elem = item.select_one('.module-card-item-title strong')
            img_elem = item.select_one('img')
            pic = (img_elem.get('data-original') or img_elem.get('src')) if img_elem else ""
            note_elem = item.select_one('.module-item-note')
            
            videos.append({
                'vod_id': vid,
                'vod_name': title_elem.get_text(strip=True) if title_elem else "",
                'vod_pic': self.host + pic if pic.startswith('/') else pic,
                'vod_remarks': note_elem.get_text(strip=True) if note_elem else ""
            })
        return videos

    def _extract_play_info(self, html, vid):
        play_from, play_url = [], []
        line_pattern = r'<(?:div|a)[^>]*class="[^"]*module-tab-item[^"]*"[^>]*>(?:.*?<span>([^<]+)</span>.*?<small>(\d+)</small>|.*?<span>([^<]+)</span>.*?<small class="no">(\d+)</small>)</(?:div|a)>'
        
        for match in re.findall(line_pattern, html, re.S | re.I):
            line_name = match[0] or match[2]
            if line_name in play_from:
                continue
                
            play_from.append(line_name)
            line_id = self._get_line_id(html, vid, line_name)
            
            ep_matches = re.findall(rf'<a class="module-play-list-link" href="/play/{vid}-{line_id}-(\d+)/"[^>]*>.*?<span>([^<]+)</span></a>', html, re.S | re.I)
            eps = [f"{ep_name.strip()}${vid}-{line_id}-{ep_num.strip()}" for ep_num, ep_name in ep_matches]
            play_url.append("#".join(eps))
            
        return play_from, play_url

    def _get_line_id(self, html, vid, line_name):
        line_id_match = re.search(rf'<a[^>]*href="/play/{vid}-(\d+)-1/"[^>]*>.*?<span>{re.escape(line_name)}</span>', html, re.S | re.I)
        if line_id_match:
            return line_id_match.group(1)
            
        line_id_map = {"全球3线": "3", "大陆0线": "1", "大陆3线": "4", "大陆5线": "2", "大陆6线": "3"}
        return line_id_map.get(line_name, "1")

    def _extract_title(self, html):
        title_match = re.search(r'<meta property="og:title" content="([^"]+)-[^-]+$"', html, re.S | re.I)
        return title_match.group(1).strip() if title_match else ""

    def _extract_pic(self, html):
        pic_match = re.search(r'<meta property="og:image" content="([^"]+)"', html, re.S | re.I)
        pic = pic_match.group(1).strip() if pic_match else ""
        return self.host + pic if pic and pic.startswith('/') else pic

    def _extract_desc(self, html):
        desc_match = re.search(r'<meta property="og:description" content="([^"]+)"', html, re.S | re.I)
        return desc_match.group(1).strip() if desc_match else "暂无简介"

    def _extract_remarks(self, html):
        year_match = re.search(r'<a title="(\d+)" href="/vodshow/\d+-----------\1/">', html, re.S | re.I)
        year = year_match.group(1) if year_match else "未知年份"
        
        area_match = re.search(r'<a title="([^"]+)" href="/vodshow/\d+-%E5%A2%A8%E8%A5%BF%E5%93%A5----------/">', html, re.S | re.I)
        area = area_match.group(1) if area_match else "未知产地"
        
        type_match = re.search(r'vod_class":"([^"]+)"', html, re.S | re.I)
        type_str = type_match.group(1).replace(",", "/") if type_match else "未知类型"
        
        return f"{year} | {area} | {type_str}"

# 本地测试
if __name__ == "__main__":
    spider = Spider()
    spider.init()
    
    # 测试详情页解析
    detail_result = spider.detailContent(["86027"])
    if detail_result['list']:
        detail = detail_result['list'][0]
        print(f"视频名称: {detail.get('vod_name', '未知')}")
    
    # 测试搜索功能
    search_result = spider.searchContent("仙逆", False, 1)
    print(f"搜索结果数量: {len(search_result['list'])}")
    
    # 测试播放功能
    play_result = spider.playerContent("", "86027-5-1", {})
    print(f"播放URL: {play_result.get('url', '')}")