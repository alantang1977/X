#coding=utf-8
#!/usr/bin/python
"""
==================================================
  作者: 飞鱼
  名称: GGJAV 媒体解析插件 (支持全分类/女优三层目录穿透)
  版本: 1.1.0
==================================================
"""
import sys
import json
import base64
import re
import requests
from bs4 import BeautifulSoup

sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def getName(self):
        return "ggjav-by-飞鱼"

    def init(self, extend=""):
        pass

    def isVideoFormat(self, url):
        if ".m3u8" in url or ".mp4" in url:
            return True
        return False

    def manualVideoCheck(self):
        return False

    def getHeader(self):
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0 (Chrome/120.0.0.0 Safari/537.0",
            "Referer": "https://ggjav.com/"
        }

    def homeContent(self, filter):
        result = {}
        classes = [
            {"type_id": "censored", "type_name": "有碼AV"},
            {"type_id": "uncensored", "type_name": "無碼AV"},
            {"type_id": "amateur", "type_name": "素人AV"},
            {"type_id": "chinese", "type_name": "中文字幕"},
            {"type_id": "europe", "type_name": "歐美"},
            {"type_id": "cartoon", "type_name": "動漫"},
            {"type_id": "all_censored_ctg", "type_name": "全部類別"},
            {"type_id": "all_censored_model?type=censored", "type_name": "女優大全"},
            {"type_id": "all_uncensored_model?type=uncensored", "type_name": "無碼女優"}
        ]
        result['class'] = classes
        
        if filter:
            video_filters = [{"key": "by", "name": "排序", "value": [{"v": "order=recommended", "n": "推荐"}, {"v": "order=pub_date", "n": "发布时间"}, {"v": "order=views", "n": "观看次数"}, {"v": "order=likes", "n": "点赞👍"}]}]
            model_filters = [{"key": "by", "name": "排序", "value": [{"v": "order=hot", "n": "热门"}, {"v": "order=name", "n": "姓名"}]}]
            
            filters = {
                "censored": video_filters,
                "uncensored": video_filters,
                "amateur": video_filters,
                "chinese": video_filters,
                "europe": video_filters,
                "cartoon": video_filters,
                "all_censored_ctg": [],
                "all_censored_model?type=censored": model_filters,
                "all_uncensored_model?type=uncensored": model_filters
            }
            result['filters'] = filters
            
        return result

    def parse_img_url(self, img_el):
        if not img_el:
            return ""
        pic = img_el.get('data-src') or img_el.get('src', '') or img_el.get('data-original', '')
        if not pic:
            return ""
        if pic.startswith('//'):
            pic = "https:" + pic
        elif not pic.startswith('http'):
            pic = "https://ggjav.com" + ("/" if not pic.startswith('/') else "") + pic
        return pic

    def parse_video_list(self, soup):
        videos = []
        items = soup.select('.large-3:has(img)')
        for item in items:
            title_el = item.select_one('.item_title')
            title = title_el.get_text(strip=True) if title_el else ""
            
            a_el = item.select_one('a')
            href = a_el.get('href') if a_el else ""
            if href and not href.startswith('http'):
                href = "https://ggjav.com" + href
            
            img = self.parse_img_url(item.select_one('img'))
            
            float_right = item.select_one('.float-right')
            float_left = item.select_one('.float-left')
            r_text = float_right.get_text(strip=True) if float_right else ""
            l_text = float_left.get_text(strip=True) if float_left else ""
            sub_title = f"❤️{r_text}👁️{l_text}"
            
            videos.append({
                "vod_id": href,
                "vod_name": title,
                "vod_pic": img,
                "vod_remarks": sub_title
            })
        return videos

    def homeVideoContent(self):
        videos = []
        try:
            url = "https://ggjav.com"
            resp = requests.get(url, headers=self.getHeader(), timeout=10)
            resp.encoding = 'UTF-8'
            soup = BeautifulSoup(resp.text, 'html.parser')
            videos = self.parse_video_list(soup)
        except Exception as e:
            print(e)
        return {"list": videos}

    def categoryContent(self, tid, pg, filter, extend):
        videos = []
        try:
            # 【穿透路由拦截 1】：处理分类标签下潜列表
            if tid.startswith("sub_ctg||"):
                target_url = tid.replace("sub_ctg||", "")
                if pg and int(pg) > 1:
                    target_url += f"&page={pg}"
                resp = requests.get(target_url, headers=self.getHeader(), timeout=10)
                resp.encoding = 'UTF-8'
                soup = BeautifulSoup(resp.text, 'html.parser')
                return {"list": self.parse_video_list(soup)}

            # 【穿透路由拦截 2】：处理女优个人作品列表下潜（关键修复点）
            if tid.startswith("sub_model||"):
                target_url = tid.replace("sub_model||", "")
                if pg and int(pg) > 1:
                    target_url += f"?page={pg}" if "?" not in target_url else f"&page={pg}"
                resp = requests.get(target_url, headers=self.getHeader(), timeout=10)
                resp.encoding = 'UTF-8'
                soup = BeautifulSoup(resp.text, 'html.parser')
                return {"list": self.parse_video_list(soup)}

            is_model = "model" in tid
            is_ctg = "ctg" in tid
            default_sort = 'order=hot' if is_model else 'order=recommended'
            by = extend.get('by', default_sort) if extend else default_sort
            
            if "?" in tid:
                url = f"https://ggjav.com/main/{tid}&{by}&page={pg}"
            else:
                url = f"https://ggjav.com/main/{tid}?{by}&page={pg}"

            resp = requests.get(url, headers=self.getHeader(), timeout=10)
            resp.encoding = 'UTF-8'
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            if is_ctg and "all_" in tid:
                ctg_inputs = soup.select('.select_ctg input[name="ctgs"]')
                for inp in ctg_inputs:
                    val = inp.get('value', '')
                    if not val:
                        continue
                    label_el = soup.select_one(f'label[for="{inp.get("id")}"]')
                    name = label_el.get_text(strip=True) if label_el else val
                    
                    ctg_url = f"sub_ctg||https://ggjav.com/main/ctg?ctgs={val}"
                    
                    videos.append({
                        "vod_id": ctg_url,
                        "vod_name": name,
                        "vod_pic": "https://ggjav.com/resources/icons/icon.png",
                        "vod_tag": "folder",
                        "vod_remarks": "点击进入分类"
                    })
            elif is_model:
                models = soup.select('div.model_chunk div.model')
                for item in models:
                    a_tag = item.select_one('a.gray_a') or item.select_one('a')
                    if not a_tag:
                        continue
                    name = a_tag.get_text(strip=True)
                    href = a_tag.get('href', '')
                    if href and not href.startswith('http'):
                        href = "https://ggjav.com" + href
                    
                    pic = self.parse_img_url(item.select_one('img'))
                    
                    # 给女优 ID 包装为二/三层路由前缀 sub_model||
                    model_url = f"sub_model||{href}"
                    
                    videos.append({
                        "vod_id": model_url,
                        "vod_name": name,
                        "vod_pic": pic,
                        "vod_tag": "folder",
                        "vod_remarks": "点击查看作品"
                    })
            else:
                videos = self.parse_video_list(soup)
        except Exception as e:
            print(e)
        return {"list": videos}

    def detailContent(self, ids):
        vod = {}
        try:
            url = ids[0]
            resp = requests.get(url, headers=self.getHeader(), timeout=10)
            resp.encoding = 'UTF-8'
            html_text = resp.text
            soup = BeautifulSoup(html_text, 'html.parser')

            vod_type = ""
            vod_year = ""
            for p in soup.find_all('p'):
                text = p.get_text()
                if "類型：" in text:
                    vod_type = text.replace("類型：", "").strip()
                if "更新：" in text:
                    vod_year = text.replace("更新：", "").strip()

            video_id_match = re.search(r'/main/video\?id=(\d+)', html_text)
            video_id = video_id_match.group(1) if video_id_match else ""

            server_buttons = []
            for el in soup.select('.server_bt'):
                sid = el.get('id')
                if sid and sid not in server_buttons:
                    server_buttons.append(sid)
            
            if not server_buttons:
                server_buttons = ["ggjav"]

            play_url_lists = []
            for srv in server_buttons:
                play_url_lists.append(f"正片${url}||{srv}||{video_id}")

            vod['vod_id'] = url
            vod['vod_name'] = soup.select_one('title').get_text(strip=True) if soup.select_one('title') else "未知"
            vod['type_name'] = vod_type
            vod['vod_year'] = vod_year
            vod['vod_play_from'] = "$$$".join(server_buttons)
            vod['vod_play_url'] = "$$$".join(play_url_lists)
        except Exception as e:
            print(e)
            
        return {"list": [vod]}

    def searchContent(self, key, quick, pg="1"):
        videos = []
        try:
            url = f"https://ggjav.com/main/search?string={key}"
            resp = requests.get(url, headers=self.getHeader(), timeout=10)
            resp.encoding = 'UTF-8'
            soup = BeautifulSoup(resp.text, 'html.parser')
            videos = self.parse_video_list(soup)
        except Exception as e:
            print(e)
        return {"list": videos}

    def playerContent(self, flag, id, vipFlags):
        real_url = ""
        parse_mode = 0
        try:
            parts = id.split('||')
            detail_url = parts[0]
            server_name = parts[1] if len(parts) > 1 else flag
            video_id = parts[2] if len(parts) > 2 else ""

            if not video_id:
                resp = requests.get(detail_url, headers=self.getHeader(), timeout=10)
                m = re.search(r'/main/video\?id=(\d+)', resp.text)
                if m:
                    video_id = m.group(1)

            if video_id:
                api_url = f"https://ggjav.com/main/video?id={video_id}"
                resp = requests.get(api_url, headers=self.getHeader(), timeout=10)
                resp.raise_for_status()
                html_text = resp.text

                match = re.search(r'var\s+l\s*=\s*"([^"]+)"', html_text)
                if match:
                    encrypted = match.group(1)
                    raw = base64.b64decode(encrypted).decode('latin-1')
                    decrypted_str = "".join(chr(ord(c) - 0x58) for c in raw)
                    links_dict = json.loads(decrypted_str)

                    urls = links_dict.get(server_name) or links_dict.get("ggjav", [])
                    if urls:
                        embed_url = urls[0]
                        
                        if server_name == "ggjav" and "u=" in embed_url:
                            u_match = re.search(r'[?&]u=([^&]+)', embed_url)
                            if u_match:
                                video_path = base64.b64decode(u_match.group(1)).decode('utf-8')
                                real_url = video_path + "/index.m3u8"
                            else:
                                real_url = embed_url
                        
                        elif "http" in embed_url:
                            player_headers = {
                                "User-Agent": self.getHeader()["User-Agent"],
                                "Referer": "https://ggjav.com/"
                            }
                            player_resp = requests.get(embed_url, headers=player_headers, timeout=10)
                            player_html = player_resp.text
                            
                            m3u8_patterns = [
                                r'(https?://[^\s<>"]+?/master\.m3u8)',
                                r'(https?://[^\s<>"]+?/index\.m3u8)',
                                r'(https?://[^\s<>"]+?\.m3u8)',
                                r'"url"\s*:\s*"(https?://[^"]+?\.m3u8)"',
                                r'src\s*:\s*["\'](https?://[^"\']+?\.m3u8)["\']',
                                r'file\s*:\s*["\'](https?://[^"\']+?\.m3u8)["\']',
                            ]
                            
                            found_m3u8 = False
                            for pattern in m3u8_patterns:
                                m3u8_match = re.search(pattern, player_html)
                                if m3u8_match:
                                    real_url = m3u8_match.group(1)
                                    found_m3u8 = True
                                    break
                            
                            if not found_m3u8:
                                domain_match = re.search(r'(https?://[^/]+)', embed_url)
                                file_id_match = re.search(r"file_id['\"],\s*['\"](\d+)['\"]", player_html)
                                stream_path_match = re.search(r'/stream/([a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+/\d+)', player_html)
                                
                                if domain_match and stream_path_match and file_id_match:
                                    base_domain = domain_match.group(1)
                                    stream_route = stream_path_match.group(1)
                                    file_id = file_id_match.group(1)
                                    real_url = f"{base_domain}/stream/{stream_route}/{file_id}/master.m3u8"
                                else:
                                    real_url = embed_url
                                    parse_mode = 1
                        else:
                            real_url = embed_url

            if not real_url:
                real_url = detail_url
        except Exception as e:
            print(e)
            real_url = id.split('||')[0]

        return {"parse": parse_mode, "url": real_url, "header": self.getHeader(), "playUrl": ""}
