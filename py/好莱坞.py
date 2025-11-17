import re
import json
import base64
from urllib.parse import urljoin, urlparse
from base.spider import Spider

class Spider(Spider):
    def getName(self):
        return "HollyMovieHD"

    def init(self, extend=""):
        self.site = "https://hollymoviehd.cc"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "DNT": "1",
            "Upgrade-Insecure-Requests": "1",
            "Referer": self.site + "/",
            "Origin": self.site,
        }
        return None

    def isVideoFormat(self, url):
        return bool(re.search(r"\.m3u8($|\?)|\.mp4($|\?)", url))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass
    
    def e64(self, text):
        return base64.b64encode(text.encode('utf-8')).decode('utf-8')
    
    def d64(self, text):
        return base64.b64decode(text.encode('utf-8')).decode('utf-8')

    def _h(self, **kw):
        h = {
            "User-Agent": self.headers["User-Agent"],
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
        }
        h.update(kw)
        return h

    def homeContent(self, filter):
        classes = [
            {"type_id": "1", "type_name": "电影"},
            {"type_id": "2", "type_name": "电视剧"},
            {"type_id": "3", "type_name": "动漫"},
        ]
        years = [str(y) for y in range(2025, 1960, -1)]
        letters = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ") + ["0-9"]
        areas_cn = [
            ("USA","美国"),("UK","英国"),("Canada","加拿大"),("China","中国"),("Japan","日本"),("South Korea","韩国"),("Thailand","泰国"),
            ("Indonesia","印度尼西亚"),("India","印度"),("France","法国"),("Germany","德国"),("Spain","西班牙"),("Italy","意大利"),("Russia","俄罗斯"),
            ("Australia","澳大利亚"),("Taiwan","台湾"),("Hong Kong","香港"),("Malaysia","马来西亚"),("Singapore","新加坡"),("Philippines","菲律宾"),
            ("Vietnam","越南"),("Turkey","土耳其"),("Mexico","墨西哥"),("Brazil","巴西"),("Other","其他")
        ]
        area_vals = [{"n": "全部", "v": ""}] + [{"n": zh, "v": en} for en, zh in areas_cn]
        year_vals = [{"n": "全部", "v": ""}] + [{"n": y, "v": y} for y in years]
        letter_vals = [{"n": "全部", "v": ""}] + [{"n": l, "v": l} for l in letters]
        genres = [
            ("动作","action"),("冒险","adventure"),("动画","animation"),("喜剧","comedy"),("犯罪","crime"),
            ("纪录片","documentary"),("剧情","drama"),("家庭","family"),("奇幻","fantasy"),("海外","foreign"),
            ("历史","history"),("恐怖","horror"),("音乐","music"),("悬疑","mystery"),("爱情","romance"),
            ("科幻","science-fiction"),("惊悚","thriller"),("电视电影","tv-movie"),("战争","war"),("西部","western"),
            ("18+","erotic")
        ]
        genre_vals = [{"n": "全部", "v": ""}] + [{"n": zh, "v": slug} for zh, slug in genres]
        by_vals = [
            {"n": "全部", "v": ""},
            {"n": "时间", "v": "time"},
            {"n": "人气", "v": "hits"},
            {"n": "评分", "v": "score"},
        ]
        filters = {
            "1": [
                {"key": "cateId", "name": "类型", "value": [{"n": "全部", "v": "1"}, {"n": "电影", "v": "1"}]},
                {"key": "genre", "name": "分类", "value": genre_vals},
                {"key": "area", "name": "地区", "value": area_vals},
                {"key": "year", "name": "时间", "value": year_vals},
                {"key": "letter", "name": "字母", "value": letter_vals},
                {"key": "by", "name": "排序", "value": by_vals},
            ],
            "2": [
                {"key": "cateId", "name": "类型", "value": [{"n": "全部", "v": "2"}, {"n": "电视剧", "v": "2"}]},
                {"key": "area", "name": "地区", "value": area_vals},
                {"key": "year", "name": "时间", "value": year_vals},
                {"key": "letter", "name": "字母", "value": letter_vals},
                {"key": "by", "name": "排序", "value": by_vals},
            ],
            "3": [
                {"key": "cateId", "name": "类型", "value": [{"n": "全部", "v": "3"}, {"n": "动漫", "v": "3"}]},
                {"key": "area", "name": "地区", "value": area_vals},
                {"key": "year", "name": "时间", "value": year_vals},
                {"key": "letter", "name": "字母", "value": letter_vals},
                {"key": "by", "name": "排序", "value": by_vals},
            ],
        }
        home = self._list_page("1", 1, {})
        return {"class": classes, "filters": filters, "list": home.get("list", [])}

    def homeVideoContent(self):
        return []

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg)
        extend = extend or {}
        data = self._list_page(tid, pg, extend)
        data.update({"page": str(pg), "pagecount": 9999, "limit": 90, "total": 999999})
        return data

    def detailContent(self, ids):
        vid = ids[0]
        url = vid if vid.startswith("http") else urljoin(self.site, vid)
        html = self.fetch(url, headers=self.headers, timeout=20).text
        title = self.regStr(r"<h1[^>]*>(.*?)</h1>", html) or self.regStr(r"<title>(.*?)</title>", html)
        pic = self.regStr(r"<meta property=\"og:image\" content=\"(.*?)\"", html)
        
        play_from = []
        play_urls = []
        
        is_series = "/series/" in url or "/anime/" in url or "EPISODES" in html
        
        if is_series:
            episodes = self._extract_episodes(html, url)
            if episodes:
                play_from.append("选集")
                play_urls.append("#".join([f"第{n}集${u}" for n, u in episodes]))
        else:
            self._extract_video_sources(html, url, play_from, play_urls)
        
        vod = {
            "vod_id": url,
            "vod_name": self.removeHtmlTags(title) if title else url,
            "vod_pic": pic or "",
            "type_name": "",
            "vod_year": self.regStr(r"Release:\s*<a[^>]*>(\d{4})<", html),
            "vod_area": self.regStr(r"Country:\s*<a[^>]*>([^<]+)<", html),
            "vod_actor": ",".join(re.findall(r"/stars/[^>]+>([^<]+)<", html))[:200],
            "vod_director": self.regStr(r"Director:\s*<a[^>]*>([^<]+)<", html),
            "vod_content": self.removeHtmlTags(self.regStr(r"<p class=\"[^\"]*\">(.*?)</p>", html) or "").strip(),
        }
        if play_from and play_urls:
            vod["vod_play_from"] = "$$$".join(play_from)
            vod["vod_play_url"] = "$$$".join([u for u in play_urls])
        return {"list": [vod]}

    def searchContent(self, key, quick, pg="1"):
        pg = int(pg) if pg.isdigit() else 1
        path = f"/search/{key}"
        if pg > 1:
            path += f"/page/{pg}/"
        url = urljoin(self.site, path)
        html = self.fetch(url, headers=self.headers, timeout=20).text
        items = self._parse_cards(html)
        data = {"list": items}
        data.update({"page": str(pg), "pagecount": 9999, "limit": 90, "total": 999999})
        return data

    def playerContent(self, flag, id, vipFlags):
        try:
            data = json.loads(self.d64(id)) if not id.startswith("http") else {"url": id, "headers": {}}
        except:
            return {"parse": 1, "url": id}
        
        url = data.get("url")
        base_headers = data.get("headers") or {}
        
        if not url:
            return {"parse": 1, "url": id}
        
        if "/episode/" in url and not base_headers.get("_episode_processed"):
            return self._handle_episode_playback(url)
        
        headers = self._h(Accept="*/*")
        headers.update(base_headers)
        
        if "flashstream.cc" in url:
            if "/embed/" in url or "/download/" in url:
                embed_id = self.regStr(r"/embed/([A-Za-z0-9_-]+)", url) or self.regStr(r"/download/([A-Za-z0-9_-]+)", url)
                if embed_id:
                    # Try using e-param directly from the embed URL first (more reliable)
                    eparam = self.regStr(r"[?&]e=([^&]+)", url)
                    direct_url = None
                    if eparam:
                        for pathseg in ["0-11", "0-8", "1-8"]:
                            direct_url = self._resolve_flashstream(embed_id, eparam, pathseg)
                            if direct_url:
                                break
                    # Fallback to parsing the embed page if API path fails
                    if not direct_url:
                        direct_url = self._resolve_flashstream_direct(embed_id)
                    if not direct_url and base_headers.get("Referer"):
                        try:
                            ref_html = self.fetch(base_headers.get("Referer"), headers=self.headers, timeout=20).text
                            mm = re.search(r"https?://flashstream\\.cc/embed/([A-Za-z0-9_-]+)\\?e=([^\"'<> ]+)", ref_html)
                            if mm:
                                code = mm.group(1)
                                eparam = mm.group(2) or ""
                                direct_url = self._resolve_flashstream(code, eparam, "0-11") or self._resolve_flashstream(code, eparam, "0-8")
                        except:
                            pass
                    if direct_url:
                        headers.update(self._h(
                            Referer="https://flashstream.cc/",
                            Origin="https://flashstream.cc",
                            Accept="application/vnd.apple.mpegurl,application/x-mpegURL,*/*",
                            **{"Accept-Encoding": "identity"}
                        ))
                        return {"parse": 0, "url": direct_url, "header": headers}
            headers.update({
                "Referer": "https://flashstream.cc/",
                "Origin": "https://flashstream.cc",
            })
            return {"parse": 1, "url": url, "header": headers}
        
        elif any(domain in url for domain in ["streamtape", "doodstream", "mixdrop"]):
            domain = urlparse(url).netloc
            headers.update(self._h(Referer=f"https://{domain}/"))
            return {"parse": 1, "url": url, "header": headers}
        
        elif url.endswith((".m3u8", ".mp4")):
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            use_flash_referer = (
                "flashstream" in domain or
                re.search(r"(^|\.)hls\d+\.", domain) is not None or
                re.search(r"goodcdn|otdengdakey", domain) is not None
            )
            referer = "https://flashstream.cc/" if use_flash_referer else self.site + "/"
            accept_stream = "application/vnd.apple.mpegurl,application/x-mpegURL,*/*" if url.endswith(".m3u8") else "*/*"
            headers.update(self._h(
                Referer=referer,
                Origin="https://flashstream.cc",
                Accept=accept_stream,
                **{"Accept-Encoding": "identity"}
            ))
            if url.endswith(".mp4"):
                headers["Range"] = "bytes=0-"
            return {"parse": 0, "url": url, "header": headers}
        
        else:
            headers.update({"Referer": self.site + "/"})
            return {"parse": 1, "url": url, "header": headers}

    def localProxy(self, param):
        try:
            url = self.d64(param.get("url", ""))
            header = {
                "User-Agent": self.headers["User-Agent"],
                "Referer": "https://flashstream.cc/",
                "Origin": "https://flashstream.cc",
                "Accept": "*/*",
                "Accept-Encoding": "identity",
                "Accept-Language": "en-US,en;q=0.9",
                "Connection": "keep-alive",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            }
            ydata = self.fetch(url, headers=header, allow_redirects=False, timeout=20)
            data = ydata.content.decode('utf-8')
            if ydata.headers.get('Location'):
                url = ydata.headers['Location']
                ydata = self.fetch(url, headers=header, timeout=20)
                data = ydata.content.decode('utf-8')
            pu = urlparse(url)
            base = pu.scheme + "://" + pu.netloc
            lines = data.strip().split('\n')
            for i, line in enumerate(lines):
                if line and not line.startswith('#') and not line.startswith('http'):
                    if line.startswith('/'):
                        lines[i] = base + line
                    else:
                        path = pu.path.rsplit('/', 1)[0]
                        lines[i] = base + path + '/' + line
            body = '\n'.join(lines)
            return [200, "application/vnd.apple.mpegurl", body]
        except Exception as e:
            return [500, "text/plain", f"error: {e}"]

    def _list_page(self, tid, pg, extend):
        if tid == "1": base_path = "/movies"
        elif tid == "2": base_path = "/series"
        else: base_path = "/anime"
        
        area = extend.get("area", "")
        year = extend.get("year", "")
        letter = extend.get("letter", "")
        genre = extend.get("genre", "")
        
        area_map = {
            "China": "china", "USA": "usa", "UK": "uk", "Canada": "canada",
            "Japan": "japan", "South Korea": "south-korea", "Thailand": "thailand",
            "Indonesia": "indonesia", "India": "india", "France": "france",
            "Germany": "germany", "Spain": "spain", "Italy": "italy",
            "Russia": "russia", "Australia": "australia", "Taiwan": "taiwan",
            "Hong Kong": "hong-kong", "Malaysia": "malaysia", "Singapore": "singapore",
            "Philippines": "philippines", "Vietnam": "vietnam", "Turkey": "turkey",
            "Mexico": "mexico", "Brazil": "brazil"
        }
        
        if genre and genre != "":
            path = f"/genre/{genre}/"
            if pg > 1: path += f"page/{pg}/"
        elif area and area != "":
            area_slug = area_map.get(area, area.lower().replace(" ", "-"))
            path = f"{base_path}/country/{area_slug}/"
            if pg > 1: path += f"page/{pg}/"
        elif year and year != "":
            path = f"{base_path}/release-year/{year}/"
            if pg > 1: path += f"page/{pg}/"
        elif letter and letter != "":
            path = f"{base_path}/0-9/" if letter == "0-9" else f"{base_path}/{letter.lower()}/"
            if pg > 1: path += f"page/{pg}/"
        else:
            path = f"{base_path}/page/{pg}/" if pg > 1 else f"{base_path}/"
        
        url = urljoin(self.site, path)
        html = self.fetch(url, headers=self.headers, timeout=20).text
        return {"list": self._parse_cards(html)}

    def _parse_cards(self, html):
        items = []
        for m in re.finditer(r'<a[^>]+href=\"(https?://hollymoviehd\.cc/[^\"]+)\"[^>]*>\s*(?:<span[^>]*>.*?</span>)?\s*<img[^>]+alt=\"([^\"]+)\"[^>]*?src=\"([^\"]+)\"', html, re.S):
            href, title, pic = m.group(1), m.group(2), m.group(3)
            items.append({
                "vod_id": href,
                "vod_name": self.removeHtmlTags(title),
                "vod_pic": pic,
                "vod_remarks": ""
            })
        if not items:
            for m in re.finditer(r'<a[^>]+href=\"(https?://hollymoviehd\.cc/[^\"]+)\"[^>]*>\s*(?:<[^>]+>)*\s*<h2[^>]*>([^<]+)</h2>', html, re.S):
                href, title = m.group(1), m.group(2)
                pic = self.regStr(rf'{re.escape(href)}[\s\S]*?<img[^>]+src=\"([^\"]+)\"', html) or ""
                items.append({
                    "vod_id": href,
                    "vod_name": self.removeHtmlTags(title),
                    "vod_pic": pic,
                    "vod_remarks": ""
                })
        return items

    def _resolve_flashstream(self, code, eparam, pathseg):
        sv_url = f"https://flashstream.cc/streamsvr/{code}/{pathseg}?e={eparam}"
        try:
            resp = self.fetch(
                sv_url,
                headers=self._h(
                    Referer=f"https://flashstream.cc/embed/{code}?e={eparam}",
                    Origin="https://flashstream.cc",
                    Accept="application/json, text/plain, */*",
                    **{"X-Requested-With": "XMLHttpRequest"}
                ),
                timeout=20,
            )
            txt = resp.text
            m = re.search(r"(https?://[^\"'<> ]+\.m3u8[^\"'<> ]*)", txt)
            if m: return m.group(1)
            try:
                j = json.loads(txt)
                if isinstance(j, dict):
                    file = j.get("file") or (j.get("sources") and j["sources"][0].get("file"))
                    if file: return file
            except: pass
        except: pass
        em_url = f"https://flashstream.cc/embed/{code}?e={eparam}"
        try:
            em = self.fetch(
                em_url,
                headers={
                    "User-Agent": self.headers["User-Agent"],
                    "Referer": self.site+"/",
                    "Origin": "https://flashstream.cc",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Connection": "keep-alive",
                },
                timeout=20,
            ).text
            m = re.search(r"file\s*:\s*['\"](https?://[^'\"]+\.m3u8[^'\"]*)['\"]", em)
            if m: return m.group(1)
            m = re.search(r"(https?://hls\d+\.[^'\"]+\.m3u8[^'\"]*)", em)
            if m: return m.group(1)
        except: pass
        return None
    
    def _resolve_flashstream_direct(self, embed_id):
        try:
            embed_url = f"https://flashstream.cc/embed/{embed_id}"
            embed_headers = self._h(
                Referer=self.site + "/",
                Accept="text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                **{"Upgrade-Insecure-Requests": "1"}
            )
            embed_html = self.fetch(embed_url, headers=embed_headers, timeout=20).text
            
            patterns = [
                r'file\s*:\s*["\']([^"\'>]+\.m3u8[^"\'>]*)["\']',
                r'src\s*:\s*["\']([^"\'>]+\.m3u8[^"\'>]*)["\']',
                r'["\']https?://[^"\'>]+\.m3u8[^"\'>]*["\']'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, embed_html)
                for match in matches:
                    if isinstance(match, str) and match.startswith('http'):
                        return match
            
            api_urls = [
                f"https://flashstream.cc/api/source/{embed_id}",
                f"https://flashstream.cc/streamsvr/{embed_id}/0-8"
            ]
            
            for api_url in api_urls:
                try:
                    api_headers = self._h(
                        Referer=embed_url,
                        Origin="https://flashstream.cc",
                        Accept="application/json, text/plain, */*",
                        **{"X-Requested-With": "XMLHttpRequest"}
                    )
                    resp = self.fetch(api_url, headers=api_headers, timeout=15)
                    if resp.status_code == 200:
                        try:
                            data = resp.json()
                            if isinstance(data, dict):
                                file_url = data.get("file") or (data.get("sources") and data["sources"][0].get("file"))
                                if file_url: return file_url
                        except:
                            m3u8_match = re.search(r'(https?://[^"\'>\\s]+\.m3u8[^"\'>\\s]*)', resp.text)
                            if m3u8_match: return m3u8_match.group(1)
                except: continue
        except: pass
        return None
    
    def _extract_episodes(self, html, series_url):
        episodes = []
        episode_section_match = re.search(r'<div[^>]*>EPISODES</div>(.*?)</ul>', html, re.DOTALL)
        if episode_section_match:
            episode_section = episode_section_match.group(1)
            episode_matches = re.findall(r'<a[^>]+href=["\']([^"\']+episode[^"\']*)["\'][^>]*>(\d+)</a>', episode_section)
            for ep_url, ep_num in episode_matches:
                if not ep_url.startswith('http'): ep_url = urljoin(self.site, ep_url)
                episodes.append((ep_num, ep_url))
        if not episodes:
            episode_matches = re.findall(r'<a[^>]+href=["\']([^"\']+/episode/[^"\']*episode-(\d+)[^"\']*)["\']', html)
            for ep_url, ep_num in episode_matches:
                if not ep_url.startswith('http'): ep_url = urljoin(self.site, ep_url)
                episodes.append((ep_num, ep_url))
        if not episodes:
            episodes_area_match = re.search(r'(?i)(episodes.*?</ul>)', html, re.DOTALL)
            if episodes_area_match:
                episodes_area = episodes_area_match.group(1)
                number_links = re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(\d+)</a>', episodes_area)
                for link_url, num in number_links:
                    if not link_url.startswith('http'): link_url = urljoin(self.site, link_url)
                    episodes.append((num, link_url))
        return episodes
    
    def _extract_video_sources(self, html, url, play_from, play_urls):
        flashstream_match = re.search(r"https?://flashstream\.cc/embed/([A-Za-z0-9_-]+)\?e=([^\"'<> ]+)", html)
        if flashstream_match:
            code = flashstream_match.group(1)
            eparam = flashstream_match.group(2)
            for pathseg in ["0-11", "0-8", "1-8"]:
                stream_url = self._resolve_flashstream(code, eparam, pathseg)
                if stream_url:
                    payload = {"url": stream_url, "headers": {"User-Agent": self.headers["User-Agent"], "Referer": "https://flashstream.cc/", "Origin": "https://flashstream.cc"}}
                    play_from.append("FLASHSTREAM")
                    play_urls.append(f"FLASHSTREAM$" + self.e64(json.dumps(payload)))
        
        iframe_matches = re.findall(r'<iframe[^>]+src=["\']([^"\'>]+)["\'][^>]*>', html)
        for iframe_url in iframe_matches:
            if "flashstream.cc" in iframe_url:
                m = re.search(r"https?://flashstream\.cc/embed/([A-Za-z0-9_-]+)(?:\?e=([^\"'<> ]+))?", iframe_url)
                if m:
                    code = m.group(1)
                    eparam = m.group(2) or ""
                    for pathseg in ["0-11", "0-8", "1-8"]:
                        stream_url = self._resolve_flashstream(code, eparam, pathseg)
                        if stream_url:
                            payload = {"url": stream_url, "headers": {"User-Agent": self.headers["User-Agent"], "Referer": "https://flashstream.cc/", "Origin": "https://flashstream.cc"}}
                            play_from.append("FLASHSTREAM")
                            play_urls.append(f"FLASHSTREAM$" + self.e64(json.dumps(payload)))
                continue
            if any(domain in iframe_url for domain in ["streamtape", "doodstream", "mixdrop", "upstream", "vidoza"]):
                domain = urlparse(iframe_url).netloc.replace("www.", "")
                source_name = domain.split(".")[0].upper()
                headers = {"User-Agent": self.headers["User-Agent"], "Referer": f"https://{domain}/"}
                payload = {"url": iframe_url, "headers": headers}
                play_from.append(source_name)
                play_urls.append(f"{source_name}$" + self.e64(json.dumps(payload)))
        
        script_matches = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
        for script in script_matches:
            video_urls = re.findall(r'["\'](https?://[^"\'>]+\.(?:m3u8|mp4)[^"\'>]*)["\']', script)
            for video_url in video_urls:
                video_url = video_url.strip('\"\'')
                if video_url not in [p.split('$')[1] for p in play_urls if '$' in p]:
                    payload = {"url": video_url, "headers": {"User-Agent": self.headers["User-Agent"], "Referer": url}}
                    play_from.append("DIRECT")
                    play_urls.append(f"DIRECT$" + self.e64(json.dumps(payload)))
                    break
        
        download_match = re.search(r'href=["\']https://flashstream\.cc/download/([^"\'>]+)["\']', html)
        if download_match and not play_from:
            download_id = download_match.group(1)
            fallback_url = f"https://flashstream.cc/embed/{download_id}"
            payload = {"url": fallback_url, "headers": {"User-Agent": self.headers["User-Agent"], "Referer": "https://flashstream.cc/", "Origin": "https://flashstream.cc"}}
            play_from.append("FLASHSTREAM")
            play_urls.append(f"FLASHSTREAM$" + self.e64(json.dumps(payload)))
    
    def _handle_episode_playback(self, episode_url):
        try:
            episode_html = self.fetch(episode_url, headers=self.headers, timeout=20).text
            play_from, play_urls = [], []
            self._extract_video_sources(episode_html, episode_url, play_from, play_urls)
            if play_urls:
                first = play_urls[0]
                if '$' in first:
                    name, enc = first.split('$', 1)
                    try:
                        data = json.loads(self.d64(enc))
                        data["headers"] = data.get("headers", {})
                        data["headers"]["_episode_processed"] = True
                        return self.playerContent(name, self.e64(json.dumps(data)), [])
                    except:
                        return self.playerContent(name, enc, [])
            return {"parse": 1, "url": episode_url}
        except:
            return {"parse": 1, "url": episode_url}