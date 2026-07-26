import sys
import re
import requests
from base.spider import Spider
from urllib3 import disable_warnings

disable_warnings()

class Spider(Spider):
    host = "https://35awards.com"

    def getName(self):
        return "35Awards摄影赏析"

    def init(self, extend=""):
        pass

    def homeContent(self, filter):
        classes = [
            {"type_id": "/en/authors/ru/nude/", "type_name": "人体艺术 (Nude)"},
            {"type_id": "/en/authors/genre/fashion/", "type_name": "时尚摄影 (Fashion)"}
        ]
        return {"class": classes}

    def categoryContent(self, tid, pg, filter, extend):
        curr_pg = int(pg)
        # 构造翻页 URL，该站通常使用 page/2/ 格式或 ?page=2
        if curr_pg > 1:
            url = f"{self.host}{tid}page/{curr_pg}/"
        else:
            url = f"{self.host}{tid}"

        res = requests.get(url, verify=False, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        html = res.text

        # 匹配摄影师（影片）列表
        matches = re.findall(r'authorHeader">.*?href="([^"]+author/([^/]+)/)".*?src="([^"]+)".*?itemprop="name">([^<]+)</span>', html, re.S)

        vod_list = []
        for link, author_id, pic, name in matches:
            vod_list.append({
                "vod_id": author_id,
                "vod_name": name.strip(),
                "vod_pic": pic,
                "vod_remarks": "点击查看作品集"
            })

        # 核心翻页逻辑
        has_next = "next-page" in html or len(vod_list) >= 12
        last_page = curr_pg + 1 if has_next else curr_pg

        return {
            "page": curr_pg,
            "pagecount": last_page,
            "limit": len(vod_list),
            "total": 999,
            "list": vod_list
        }

    def detailContent(self, ids):
        author_id = ids[0]
        # 构造详情页：https://35awards.com/en/author/{摄影师}/
        url = f"{self.host}/en/author/{author_id}/"
        res = requests.get(url, verify=False, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        html = res.text

        # 1. 提取基本信息
        name_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
        pic_match = re.search(r'class="authorAvatar">.*?src="([^"]+)"', html, re.S)
        
        # 2. 提取图片数组
        img_matches = re.findall(r'class="[^"]*lozadGridPhoto[^"]*"[^>]+data-src="([^"]+)"', html)
        
        # 处理图片链接（确保是完整 URL）
        clean_imgs = []
        for img in img_matches:
            if img.startswith('//'): img = "https:" + img
            elif img.startswith('/') : img = self.host + img
            clean_imgs.append(img)

        # 3. 构造播放列表 (pics:// 格式)
        play_url = "作品集$" + "pics://" + "&&".join(clean_imgs)

        vod = {
            "vod_id": author_id,
            "vod_name": name_match.group(1).strip() if name_match else author_id,
            "vod_pic": pic_match.group(1) if pic_match else "",
            "vod_play_from": "35Awards",
            "vod_play_url": play_url,
            "vod_content": f"摄影师 {author_id} 的精选作品集。"
        }
        
        return {"list": [vod]}

    def searchContent(self, key, quick, pg="1"):
        return {"list": []}

    def playerContent(self, flag, id, vipFlags):
        return {
            "parse": 0, 
            "url": id, 
            "header": {"User-Agent": "Mozilla/5.0"}
        }
