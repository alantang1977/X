import json, re, requests, threading, base64, random
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from urllib.parse import urlparse, quote
from pyquery import PyQuery as pq
from base.spider import Spider

class Spider(Spider):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36', 'sec-ch-ua-platform': '"Windows"', 'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="141", "Google Chrome";v="141"', 'origin': 'https://456movie.net', 'referer': 'https://456movie.net/'}

    def init(self, extend=""):
        self.site = 'https://456movie.net'
        self.chost, self.token = self.gettoken()
        self.phost = 'https://image.tmdb.org/t/p/w500'
        self.servers = {'vidlink': 'https://vidlink.pro', 'vidfast': 'https://vidfast.pro', '111movies': 'https://111movies.com', 'vidrock': 'https://vidrock.net', 'vidzee': 'https://player.vidzee.wtf'}
        self.server_order = ['vidfast','vidlink', '111movies', 'vidrock', 'vidzee']
        self.headers.update({'origin': self.site, 'referer': f'{self.site}/', 'accept': 'application/json'})
        self._111movies_key = bytes([1, 157, 45, 74, 228, 243, 24, 124, 194, 12, 184, 70, 3, 93, 102, 187, 254, 72, 230, 97, 57, 129, 254, 216, 223, 113, 82, 42, 62, 208, 244, 63])
        self._111movies_iv = bytes([147, 233, 144, 118, 246, 33, 110, 119, 13, 209, 140, 42, 32, 186, 47, 89])
        self._111movies_xkey = bytes([238, 123, 35, 56, 43, 184, 57, 233, 233, 41])
        self.vidzee_key_hex = '6966796f75736372617065796f75726179676179000000000000000000000000'
        self.jx = 'https://111movies.com'

    def getName(self): return "Movies"
    def isVideoFormat(self, url): return '.m3u8' in url or '.mp4' in url
    def manualVideoCheck(self): return True
    def destroy(self): pass

    def homeContent(self, filter):
        cate = {"电影": "movie", "剧集": "tv"}
        return {'class': [{'type_name': k, 'type_id': v} for k, v in cate.items()], 'filters': {}}

    def homeVideoContent(self):
        data = self.fetch(f"{self.chost}/trending/all/week", params={'api_key': self.token, 'language': 'zh-CN', 'page': 1}, headers=self.headers).json()
        return {'list': self.getlist(data['results'])}

    def categoryContent(self, tid, pg, filter, extend):
        params = {'page': pg, 'api_key': self.token, 'language': 'zh-CN'}
        data = self.fetch(f'{self.chost}/discover/{tid}', params=params, headers=self.headers).json()
        return {'list': self.getlist(data['results'], tid), 'page': pg, 'pagecount': 9999, 'limit': 90, 'total': 999999}

    def detailContent(self, ids):
        path = ids[0]
        v = self.fetch(f'{self.chost}{path}', params={'api_key': self.token, 'language': 'zh-CN'}, headers=self.headers).json()
        is_movie = '/movie/' in path
        if is_movie:
            play_str = f"{v.get('title') or v.get('name')}${path}"
        else:
            play_items = []
            for season in v.get('seasons') or []:
                season_number = season.get('season_number')
                if not season_number or season_number < 1: continue
                tv_id = re.findall(r'/tv/(\d+)', path)[0]
                season_data = self.fetch(f"{self.chost}/tv/{tv_id}/season/{season_number}", params={'api_key': self.token, 'language': 'zh-CN'}, headers=self.headers).json()
                for episode in season_data.get('episodes', []):
                    episode_number = episode.get('episode_number')
                    if episode_number:
                        name = episode.get('name') or f'S{season_number:02d}E{episode_number:02d}'
                        play_items.append(f"{name}$/tv/{tv_id}/{season_number}/{episode_number}")
            play_str = '#'.join(play_items) if play_items else f"{v.get('name')}${path}/1/1"
        origin_country = v.get('origin_country', [])
        vod_area = ', '.join(origin_country) if origin_country else '未知'
        play_from_list, play_url_list = [], []
        for server_id in self.server_order:
            play_from_list.append(server_id)
            play_url_list.append(play_str)
        play_from, play_url = '$$$'.join(play_from_list), '$$$'.join(play_url_list)
        return {'list': [{'vod_id': path, 'vod_name': v.get('title') or v.get('name'), 'vod_year': (v.get('release_date') or v.get('last_air_date') or '')[:4], 'vod_area': vod_area, 'vod_remarks': v.get('tagline') or '', 'vod_content': v.get('overview') or '', 'vod_play_from': play_from, 'vod_play_url': play_url}]}

    def searchContent(self, key, quick, pg="1"):
        params = {'query': key, 'page': pg, 'api_key': self.token, 'language': 'zh-CN', 'include_adult': 'false'}
        data = self.fetch(f'{self.chost}/search/multi', params=params, headers=self.headers).json()
        return {'list': self.getlist(data.get('results', [])), 'page': pg}

    def getlist(self, data, tid=''):
        return [{'vod_id': f"/{media_type}/{i['id']}", 'vod_name': i.get('title') or i.get('name') or '', 'vod_pic': f"{self.phost}{poster}" if (poster := i.get('poster_path') or i.get('backdrop_path')) else '', 'vod_remarks': ''} for i in data or [] if (media_type := tid or i.get('media_type')) in ('movie', 'tv') and i.get('id')]

    def jxh(self):
        header = self.headers.copy()
        header.update({'referer': f'{self.jx}/', 'origin': self.jx, 'content-type': 'text/plain'})
        header.pop('authorization', None)
        return header

    def get_server_headers(self, server_id):
        domain = self.servers[server_id]
        header = self.headers.copy()
        header.update({'referer': f'{domain}/', 'origin': domain, 'content-type': 'text/plain'})
        header.pop('authorization', None)
        return header

    def _parse_play_id(self, id_str):
        m = re.match(r'^/(movie|tv)/(\d+)(?:/(\d+)/(\d+))?$', id_str or '')
        if not m:
            if '/movie/' in id_str: return 'movie', re.findall(r'/movie/(\d+)', id_str)[0], None, None
            elif '/tv/' in id_str:
                parts = re.findall(r'/tv/(\d+)(?:/(\d+)/(\d+))?', id_str)[0]
                return 'tv', parts[0], (parts[1] or '1'), (parts[2] or '1')
            else: raise ValueError('Unrecognized play id')
        media_type, tmdb_id, season, episode = m.groups()
        return media_type, tmdb_id, season, episode

    def _get_vidrock_url(self, tmdb_id, media_type, season, episode):
        default_domain = 'https://vidrock.net'
        passphrase = "x7k9mPqT2rWvY8zA5bC3nF6hJ2lK4mN9"
        item_id = str(tmdb_id) if media_type == 'movie' else f"{tmdb_id}_{season}_{episode}"
        key, iv = passphrase.encode(), passphrase.encode()[0:16]
        cipher = AES.new(key, AES.MODE_CBC, iv)
        ct = cipher.encrypt(pad(item_id.encode(), AES.block_size))
        encoded = quote(base64.b64encode(ct).decode())
        headers = {"Referer": default_domain, "Origin": default_domain, "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36"}
        response = requests.get(f'{default_domain}/api/{media_type}/{encoded}', headers=headers).json()
        sources = [src['url'] for src in response.values() if src.get('url') and ('.m3u8' in src['url'] or '.mp4' in src['url'])]
        return random.choice(sorted(sources, key=lambda x: '.m3u8' not in x)) if sources else None

    def _111movies_encrypt_data(self, data_str):
        cipher = AES.new(self._111movies_key, AES.MODE_CBC, self._111movies_iv)
        padded_data = pad(data_str.encode(), AES.block_size)
        encrypted_data = cipher.encrypt(padded_data)
        hex_data = encrypted_data.hex()
        result = "".join(chr(ord(hex_data[i]) ^ self._111movies_xkey[i % len(self._111movies_xkey)]) for i in range(len(hex_data)))
        base64_result = base64.b64encode(result.encode('utf-8')).decode('ascii').replace('+', '-').replace('/', '_').replace('=', '')
        source_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
        target_chars = "PpowE6rtqQ9OxFNzg_vLTJmHKi07j45fXubCVecGURsaS1ny8lBWdAD2ZkM3-YhI"
        char_map = {source_chars[i]: target_chars[i] for i in range(len(source_chars))}
        return ''.join([char_map.get(c, c) for c in base64_result])

    def _get_111movies_url(self, encrypted_txt):
        rsp = self.post(f"{self.jx}/rijevra/{encrypted_txt}/sr", headers=self.jxh(), timeout=10)
        data = rsp.json()
        urls = []
        for i in data:
            if name := i.get('name'):
                if dat := i.get('data'):
                    urls.extend([name, f"{self.getProxyUrl()}&dddd={dat}"])
        return urls

    def _get_vidzee_url(self, tmdb_id, media_type, season, episode):
        user_agent = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
        default_domain = 'https://player.vidzee.wtf'
        headers = {'Referer': default_domain, 'Origin': default_domain, 'User-Agent': user_agent}
        server = 1 
        api_url = f'{default_domain}/api/server?id={tmdb_id}&sr={server}' if media_type == 'movie' else f'{default_domain}/api/server?id={tmdb_id}&sr={server}&ss={season}&ep={episode}'
        response = requests.get(api_url, headers=headers, timeout=10).json()
        if encrypted_url := response.get('url', [{}])[0].get('link'):
            iv_b64, ciphertext_b64 = base64.b64decode(encrypted_url).decode().split(':', 1)
            iv, ciphertext = base64.b64decode(iv_b64), base64.b64decode(ciphertext_b64)
            key = bytes.fromhex(self.vidzee_key_hex)
            cipher = AES.new(key, AES.MODE_CBC, iv)
            decrypted_data = cipher.decrypt(ciphertext)
            plaintext_bytes = unpad(decrypted_data, AES.block_size)
            return plaintext_bytes.decode('utf-8')
        return None

    def _vf_custom_encode(self, input_bytes):
        source_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
        target_chars = "4stjqN6BT05-L8rQe_HxWmAVv9icYKaCDzIP1fZ7kwXRyFhd2GEng3SMJlUubOop"
        translation_table = str.maketrans(source_chars, target_chars)
        encoded = base64.urlsafe_b64encode(input_bytes).decode().rstrip('=')
        return encoded.translate(translation_table)

    def _get_vidfast_streams(self, tmdb_id, media_type, season, episode):
        base_url = f"https://vidfast.pro/movie/{tmdb_id}" if media_type == 'movie' else f"https://vidfast.pro/tv/{tmdb_id}/{season}/{episode}"
        ua = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36"
        default_domain = '{uri.scheme}://{uri.netloc}/'.format(uri=urlparse(base_url))
        headers = {"Accept": "*/*", "Referer": default_domain, "User-Agent": ua, "X-Csrf-Token": "iwwuf3C7tleIfqxlgG5NUxOrOROfn5d9", "X-Requested-With": "XMLHttpRequest"}
        sess = requests.Session()
        requests.packages.urllib3.disable_warnings()
        def _get(url, hdrs):
            last = None
            for _ in range(3):
                r = sess.get(url, headers=hdrs, timeout=10, verify=False)
                last = r
                if r.status_code == 200: return r
            return last
        html_resp = _get(base_url, {"User-Agent": ua, "Referer": default_domain})
        if not html_resp or html_resp.status_code != 200: return []
        if m := re.search(r'\\"en\\":\\"(.*?)\\"', html_resp.text):
            raw_data = m.group(1)
            key_hex, iv_hex = '1f9b96f4e6604062c39f69f4c2edd92210d44d185434b0d569b077a72975bf08', '70ed610a03c6a59c7967abf77db57f71'
            aes_key, aes_iv = bytes.fromhex(key_hex), bytes.fromhex(iv_hex)
            cipher = AES.new(aes_key, AES.MODE_CBC, aes_iv)
            padded = pad(raw_data.encode(), AES.block_size)
            aes_encrypted = cipher.encrypt(padded)
            xor_key = bytes.fromhex("d6f87ef72c")
            xor_bytes = bytes(b ^ xor_key[i % len(xor_key)] for i, b in enumerate(aes_encrypted))
            encoded_final = self._vf_custom_encode(xor_bytes)
            static_path = "hezushon/ira/2264ec23bfa5e4891e26d563e5daac61bcb05688/b544e02b"
            api_servers = f"https://vidfast.pro/{static_path}/wfPFjh__qQ/{encoded_final}"
            resp = _get(api_servers, headers)
            if not resp or resp.status_code != 200: return []
            servers_list = resp.json()
            wanted = {"Oscar", "Alpha", "vFast"}
            results = []
            for item in servers_list or []:
                if (name := item.get('name')) and (data := item.get('data')) and name in wanted:
                    api_stream = f"https://vidfast.pro/{static_path}/AddlBFe5/{data}"
                    r2 = _get(api_stream, headers)
                    if r2 and r2.status_code == 200 and (url := r2.json().get('url')) and ('.m3u8' in url or '.mp4' in url):
                        results.append((name, url))
            return results
        return []

    def playerContent(self, flag, id, vipFlags):
        subs = []
        media_type, tmdb_id, season, episode = self._parse_play_id(id)
        s, e = season or '1', episode or '1'
        server_id = flag if flag in self.servers else self.server_order[0]
        domain = self.servers.get(server_id)
        lang_map = {'english': 'en', 'chinese': 'zh', 'zh': 'zh', '简体': 'zh-CN', '繁體': 'zh-TW', 'japanese': 'ja', 'korean': 'ko'}
        def _map_lang(label):
            name = (label or '').lower()
            if name in lang_map: return lang_map[name]
            for k, v in lang_map.items():
                if name.startswith(k) or k in name: return v
            return ''
        hdr = self.jxh().copy()
        hdr.update({'referer': 'https://vidrock.net/'})
        sub_api = f"https://s.vdrk.site/subfetch.php?id={tmdb_id}" + (f'&s={s}&e={e}' if media_type == 'tv' else '')
        resp = self.fetch(sub_api, headers=hdr, timeout=7)
        if resp and resp.status_code == 200:
            items = resp.json() if hasattr(resp, 'json') else json.loads(resp.text or '[]')
            if not items and media_type == 'tv':
                resp2 = self.fetch(f"https://s.vdrk.site/subfetch.php?id={tmdb_id}", headers=hdr, timeout=7)
                if resp2 and resp2.status_code == 200:
                    items = resp2.json() if hasattr(resp2, 'json') else json.loads(resp2.text or '[]')
            for it in items or []:
                if u := it.get('file') or it.get('url') or it.get('src'):
                    fmt = 'application/x-subrip' if 'srt' in u.lower() else 'text/vtt'
                    subs.append({'url': u, 'name': it.get('label') or it.get('name') or 'Subtitle (vdrk)', 'lang': _map_lang(it.get('label')), 'format': fmt})
        if server_id == 'vidrock':
            if video_url := self._get_vidrock_url(tmdb_id, media_type, s, e):
                return {'parse': 0, 'url': video_url, 'header': self.get_server_headers(server_id), 'subs': subs}
            embed = f"{domain}/movie/{tmdb_id}" if media_type == 'movie' else f"{domain}/tv/{tmdb_id}/{s}/{e}?autoplay=true&autonext=true"
            return {'parse': 1, 'url': embed, 'header': self.get_server_headers(server_id), 'subs': subs}
        elif server_id == '111movies':
            html = self.fetch(f'{self.jx}{id}', headers=self.get_server_headers(server_id)).text
            next_data = pq(html)('#__NEXT_DATA__').text()
            jstr = json.loads(next_data)
            data_token = (jstr.get('props', {}).get('pageProps', {}) or {}).get('data')
            encrypted_txt = self._111movies_encrypt_data(data_token)
            if video_urls := self._get_111movies_url(encrypted_txt):
                return {'parse': 0, 'url': video_urls, 'header': self.get_server_headers(server_id), 'subs': subs}
            return {'parse': 1, 'url': f'{self.jx}{id}', 'header': self.get_server_headers(server_id), 'subs': subs}
        elif server_id == 'vidzee':
            if video_url := self._get_vidzee_url(tmdb_id, media_type, s, e):
                vidzee_headers = {'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36', 'Referer': 'https://player.vidzee.wtf/', 'Origin': 'https://player.vidzee.wtf', 'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="141", "Google Chrome";v="141"', 'sec-ch-ua-mobile': '?1', 'sec-ch-ua-platform': '"Android"'}
                return {'parse': 0, 'url': video_url, 'header': vidzee_headers, 'subs': subs}
            embed = f"{domain}/embed/{media_type}/{tmdb_id}" + (f"/{s}/{e}" if media_type == 'tv' else "")
            return {'parse': 1, 'url': embed, 'header': self.get_server_headers(server_id), 'subs': subs}
        elif server_id == 'vidfast':
            if pairs := self._get_vidfast_streams(tmdb_id, media_type, s, e):
                url_list = []
                for name, u in pairs: url_list.extend([name, u])
                vf_headers = {'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36', 'Referer': 'https://vidfast.pro/', 'Origin': 'https://vidfast.pro'}
                return {'parse': 0, 'url': url_list, 'header': vf_headers, 'subs': subs}
            embed = f"{domain}/movie/{tmdb_id}" if media_type == 'movie' else f"{domain}/tv/{tmdb_id}/{s}/{e}?autoNext=true&nextButton=false&title=true&poster=true&autoPlay=true"
            return {'parse': 1, 'url': embed, 'header': self.get_server_headers(server_id), 'subs': subs}
        else:
            if media_type == 'movie':
                embed = f"{domain}/movie/{tmdb_id}"
            else:
                if server_id == 'vidfast':
                    embed = f"{domain}/tv/{tmdb_id}/{s}/{e}?autoNext=true&nextButton=false&title=true&poster=true&autoPlay=true"
                elif server_id == 'vidlink':
                    embed = f"{domain}/tv/{tmdb_id}/{s}/{e}?primaryColor=63b8bc&secondaryColor=a2a2a2&iconColor=eefdec&icons=default&player=default&title=true&poster=true&autoplay=true&nextbutton=true"
                else:
                    embed = f"{domain}/embed/{'movie' if media_type=='movie' else 'tv'}/{tmdb_id}{'' if media_type=='movie' else f'/{s}/{e}'}"
            return {'parse': 1, 'url': embed, 'header': self.get_server_headers(server_id), 'subs': subs}

    def localProxy(self, param):
        if dddd := param.get('dddd', ''):
            headers = self.jxh()
            data = self.post(f"{self.jx}/rijevra/{dddd}", headers=headers).json()
            return [302, 'application/vnd.apple.mpegurl', None, {'Location': data['url']}]
        return ''

    def gettoken(self):
        hosts, paths = [self.site], ['/', '/movies', '/tv-shows']
        key_pattern = re.compile(r'TMDB_API_KEY\s*[:=]\s*[\"\']([A-Za-z0-9]+)[\"\']')
        for host in hosts:
            for path in paths:
                hdr = self.headers.copy()
                hdr.update({'origin': host, 'referer': f'{host}/'})
                html = self.fetch(f'{host}{path}', headers=hdr, timeout=10).text
                if mod := pq(html)('script[type="module"]').attr('src'):
                    murl = mod if mod.startswith('http') else f'{host}{mod}'
                    mjs = self.fetch(murl, headers=hdr, timeout=10).text
                    if m := key_pattern.search(mjs): return 'https://api.themoviedb.org/3', m.group(1)
                    if mw := re.search(r'player-watch-([\w-]+)\.js', mjs):
                        pjs = self.fetch(f"{host}/assets/player-watch-{mw.group(1)}.js", headers=hdr, timeout=10).text
                        if m2 := key_pattern.search(pjs): return 'https://api.themoviedb.org/3', m2.group(1)
        return 'https://api.themoviedb.org/3', '524c16f6e2a0a13c49ff7b99d27b5efb'