"""
@header({
  searchable: 1,
  filterable: 1,
  quickSearch: 1,
  title: '高清电影天堂',
  author: '完全修复推送版',
  lang: 'hipy'
})
"""

import sys
import json
import re
from urllib.parse import quote_plus, unquote

sys.path.append('..')
from base.spider import Spider


class Spider(Spider):
    def getName(self):
        return "高清电影天堂"

    def init(self, extend=""):
        self.baseUrl = "https://www.gaoqing888.com"
        self.siteUrl = self.baseUrl

    def homeContent(self, filter):
        return {
            'class': [
                {'type_name': '每日更新', 'type_id': 'home'},
                {'type_name': '选电影', 'type_id': 'movie'}
            ]
        }

    def homeVideoContent(self):
        result = []
        try:
            html = self.fetch(self.baseUrl, headers=self._get_header()).text
            if not html:
                return {'list': result}
            
            # 从首页提取视频
            video_matches = self._parse_video_items(html)
            
            for match in video_matches[:15]:  # 只取前15个
                try:
                    vod_id = match[0].strip()
                    vod_name = match[1].strip()
                    vod_pic = match[2].strip() if len(match) > 2 else ""
                    p_content = match[3] if len(match) > 3 else ""
                    
                    vod_name = self._clean_text(vod_name)
                    
                    # 提取评分
                    vod_rating = ""
                    if p_content:
                        rating_match = re.search(r'<strong[^>]*title="评分">([^<]+)</strong>', p_content, re.S)
                        vod_rating = rating_match.group(1).strip() if rating_match else ""
                    
                    # 检查是否可播
                    is_playable = bool(re.search(r'playable fa fa-play-circle-o', p_content, re.S)) if p_content else False
                    
                    remarks = []
                    if vod_rating and vod_rating not in ["0", "0.0"]:
                        remarks.append(f"评分:{vod_rating}")
                    if is_playable:
                        remarks.append("可播")
                        
                    result.append({
                        "vod_id": vod_id,
                        "vod_name": vod_name,
                        "vod_pic": vod_pic,
                        "vod_remarks": " ".join(remarks) if remarks else ""
                    })
                except:
                    continue
                    
        except Exception as e:
            print(f"homeVideoContent error: {str(e)}")
        return {'list': result}

    def categoryContent(self, tid, pg, filter, extend):
        result = {'list': [], 'page': pg, 'pagecount': 1, 'limit': 90, 'total': 999999}
        
        try:
            # 构建URL
            if tid == "home":
                url = f"{self.baseUrl}/?page={pg}" if pg and int(pg) > 1 else self.baseUrl
            elif tid == "movie":
                url = f"{self.baseUrl}/movie?page={pg}" if pg and int(pg) > 1 else f"{self.baseUrl}/movie"
            else:
                url = f"{self.baseUrl}/{tid}?page={pg}" if pg and int(pg) > 1 else f"{self.baseUrl}/{tid}"
            
            html = self.fetch(url, headers=self._get_header()).text
            if not html:
                return result
            
            # 提取视频列表
            video_matches = self._parse_video_items(html)
            
            for match in video_matches:
                try:
                    vod_id = match[0].strip()
                    vod_name = match[1].strip()
                    vod_pic = match[2].strip() if len(match) > 2 else ""
                    p_content = match[3] if len(match) > 3 else ""
                    
                    if not vod_id or not vod_name:
                        continue
                    
                    vod_name = self._clean_text(vod_name)
                    
                    # 提取评分
                    vod_rating = ""
                    if p_content:
                        rating_match = re.search(r'<strong[^>]*title="评分">([^<]+)</strong>', p_content, re.S)
                        vod_rating = rating_match.group(1).strip() if rating_match else ""
                    
                    # 检查是否可播
                    is_playable = bool(re.search(r'playable fa fa-play-circle-o', p_content, re.S)) if p_content else False
                    
                    remarks = []
                    if vod_rating and vod_rating not in ["0", "0.0"]:
                        remarks.append(f"评分:{vod_rating}")
                    if is_playable:
                        remarks.append("可播")
                    
                    result['list'].append({
                        "vod_id": vod_id,
                        "vod_name": vod_name,
                        "vod_pic": vod_pic,
                        "vod_remarks": " ".join(remarks) if remarks else ""
                    })
                except:
                    continue
            
            # 提取总页数
            result['pagecount'] = self._get_page_count(html, pg)
            
        except Exception as e:
            print(f"categoryContent error: {str(e)}")
        
        return result

    def detailContent(self, ids):
        if not ids:
            return {'list': []}
        
        vod_id = str(ids[0]).strip()
        url = f'{self.baseUrl}/{vod_id}/detail'
        
        try:
            html = self.fetch(url, headers=self._get_header()).text
            if not html:
                return {'list': []}
            
            # 提取标题
            title_match = re.search(r'<h1[^>]*class="page-title"[^>]*>(.*?)</h1>', html, re.S)
            if not title_match:
                title_match = re.search(r'<title>(.*?)</title>', html, re.S)
                if title_match:
                    title = title_match.group(1).strip()
                    title = re.sub(r'_.*|迅雷下载.*|高清下载.*|高清电影天堂.*', '', title)
                else:
                    return {'list': []}
            else:
                title = title_match.group(1).strip()
            
            title = self._clean_text(title)
            
            # 提取年份
            year_match = re.search(r'\((\d{4})\)', html)
            year = year_match.group(1) if year_match else ''
            
            # 提取封面
            pic_match = re.search(r'<img[^>]*class="[^"]*cover[^"]*"[^>]*src="([^"]+)"', html, re.S) or \
                       re.search(r'<img[^>]*src="([^"]+)"[^>]*alt="[^"]*"[^>]*>', html, re.S)
            pic = pic_match.group(1).strip() if pic_match else ''
            
            # 提取描述
            desc = self._extract_description(html)
            
            # 提取基本信息
            info = self._extract_video_info(html)
            
            # 提取播放资源
            play_lines = self._extract_play_resources(html)
            
            if not play_lines:
                play_lines = ["暂无资源$暂无资源"]
            
            # 播放来源
            play_from = []
            if any("夸克网盘" in line for line in play_lines):
                play_from.append("夸克网盘")
            if any("磁力链接" in line for line in play_lines):
                play_from.append("磁力链接")
            if not play_from:
                play_from = ["其他资源"]
            
            vod_info = {
                "vod_id": vod_id,
                "vod_name": title,
                "vod_pic": pic,
                "type_name": info.get('type', ''),
                "vod_year": info.get('year', year),
                "vod_area": info.get('area', ''),
                "vod_remarks": info.get('remarks', ''),
                "vod_actor": info.get('actor', ''),
                "vod_director": info.get('director', ''),
                "vod_content": desc,
                "vod_play_from": "$$$".join(play_from),
                "vod_play_url": "#".join(play_lines)
            }
            
            return {'list': [vod_info]}
            
        except Exception as e:
            print(f"detailContent error: {str(e)}")
            return {'list': []}

    # 搜索功能回退到原来的版本
    def searchContent(self, key, quick, pg='1'):
        result = {'list': [], 'page': int(pg) if pg else 1, 'pagecount': 1, 'limit': 90, 'total': 999999}
        try:
            encoded_key = quote_plus(key)
            url = f'{self.baseUrl}/search?kw={encoded_key}'
            if pg and int(pg) > 1:
                url = f'{url}&page={pg}'
            
            html = self.fetch(url, headers=self._get_header()).text
            if not html:
                return result
            
            # 从HTML中提取搜索结果 - 使用原来的方法
            video_items = []
            
            # 查找搜索列表
            search_pattern = r'<div class="wp-list[^"]*">(.*?)</div>\s*</div>'
            search_match = re.search(search_pattern, html, re.S)
            
            if search_match:
                search_html = search_match.group(1)
                # 匹配视频行
                row_pattern = r'<div class="video-row"[^>]*>.*?<a[^>]*href="[^"]*/(\d+)/detail"[^>]*class="cover-link">.*?<img[^>]*class="cover"[^>]*src="([^"]*)"[^>]*alt="([^"]*)"[^>]*>.*?<a[^>]*class="title-link"[^>]*href="[^"]*/(\d+)/detail"[^>]*>([^<]*)</a>'
                row_matches = re.findall(row_pattern, search_html, re.S)
                
                for match in row_matches:
                    if len(match) >= 5:
                        video_items.append((match[0], match[1], match[2], match[4]))
            
            # 如果没找到，使用备用方法
            if not video_items:
                item_pattern = r'<div class="video-row"[^>]*>.*?<a[^>]*href="/(\d+)/detail"[^>]*class="cover-link">.*?<img[^>]*class="cover"[^>]*src="([^"]*)"[^>]*alt="([^"]*)"[^>]*>.*?<a[^>]*class="title-link"[^>]*href="[^"]*/(\d+)/detail"[^>]*>([^<]*)</a>'
                row_matches = re.findall(item_pattern, html, re.S)
                
                for match in row_matches:
                    if len(match) >= 5:
                        video_items.append((match[0], match[1], match[2], match[4]))
            
            # 备用匹配 - 更宽松的正则
            if not video_items:
                item_pattern = r'<a[^>]*href="/(\d+)/detail"[^>]*>.*?<img[^>]*class="cover"[^>]*src="([^"]*)"[^>]*alt="([^"]*)"'
                matches = re.findall(item_pattern, html, re.S)
                
                for match in matches:
                    if len(match) >= 3:
                        video_items.append((match[0], match[1], match[2], match[2]))
            
            for item in video_items:
                try:
                    vod_id = item[0].strip()
                    vod_pic = item[1].strip() if len(item) > 1 else ""
                    vod_alt = item[2].strip() if len(item) > 2 else ""
                    vod_name = item[3].strip() if len(item) > 3 else vod_alt
                    
                    if not vod_id or not vod_name:
                        continue
                    
                    vod_name = self._clean_text(vod_name)
                    
                    # 尝试获取评分
                    rating_pattern = rf'/{vod_id}/detail.*?<span class="rate-num">([^<]+)</span>'
                    rating_match = re.search(rating_pattern, html, re.S)
                    vod_rating = rating_match.group(1).strip() if rating_match else ""
                    
                    remarks = []
                    if vod_rating and vod_rating != "0" and vod_rating != "0.0":
                        remarks.append(f"评分:{vod_rating}")
                    
                    result['list'].append({
                        "vod_id": vod_id,
                        "vod_name": vod_name,
                        "vod_pic": vod_pic,
                        "vod_remarks": " ".join(remarks) if remarks else ""
                    })
                except:
                    continue
            
            # 尝试获取总页数
            page_pattern = r'<a[^>]*href="[^"]*\?kw=[^&]*&page=(\d+)"[^>]*>'
            page_matches = re.findall(page_pattern, html)
            
            max_page = int(pg) if pg else 1
            for page_num in page_matches:
                if page_num.isdigit():
                    page_int = int(page_num)
                    if page_int > max_page:
                        max_page = page_int
            
            result['pagecount'] = max_page if max_page > 0 else 1
            
        except Exception as e:
            print(f"searchContent error: {str(e)}")
            
        return result

    def playerContent(self, flag, id, vipFlags):
        if id == "暂无资源":
            return {"parse": 0, "url": ""}
        
        if id.startswith('magnet:'):
            return {"parse": 0, "url": id}
        
        if 'pan.quark.cn' in id:
            if not id.startswith('http'):
                if id.startswith('//'):
                    id = f'https:{id}'
                elif id.startswith('/'):
                    id = f'https://pan.quark.cn{id}'
                else:
                    id = f'https://pan.quark.cn/{id}'
            
            return {"parse": 0, "url": f"push://{id}"}
        
        return {"parse": 0, "url": id, "header": self._get_header()}

    # 辅助方法
    def _parse_video_items(self, html):
        """解析视频列表项"""
        video_items = []
        
        # 主要匹配模式
        patterns = [
            r'<a class="video-item"[^>]*target="_blank"[^>]*href="[^"]*/(\d+)/detail"[^>]*title="([^"]*)"[^>]*>.*?<div class="wp-cover">.*?<img[^>]*src="([^"]*)"[^>]*alt="[^"]*"[^>]*>.*?<p>(.*?)</p>',
            r'<a class="video-item"[^>]*href="[^"]*/(\d+)/detail"[^>]*>.*?<img[^>]*src="([^"]*)"[^>]*alt="([^"]*)"',
            r'<a[^>]*href="/(\d+)/detail"[^>]*>.*?<img[^>]*class="cover"[^>]*src="([^"]*)"[^>]*alt="([^"]*)"'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html, re.S)
            if matches:
                video_items = matches
                break
        
        return video_items

    def _extract_quark_url(self, url):
        """提取夸克网盘链接"""
        try:
            if not url:
                return None
            
            url = url.strip()
            
            if '/go/play' in url:
                match = re.search(r'url=([^&]+)', url)
                if match:
                    return unquote(match.group(1))
            
            if 'pan.quark.cn' in url:
                if url.startswith('http'):
                    return url
                elif url.startswith('//'):
                    return f'https:{url}'
                elif url.startswith('/'):
                    return f'https://pan.quark.cn{url}'
                else:
                    return f'https://pan.quark.cn/{url}'
            
            return None
        except:
            return None

    def _extract_description(self, html):
        """提取视频描述"""
        desc_patterns = [
            r'剧情简介[^<]*</h5>\s*<p[^>]*>(.*?)</p>',
            r'<div[^>]*class="video-summary"[^>]*>.*?<div[^>]*class="meta"[^>]*>(.*?)</div>',
            r'<div[^>]*class="vod-content"[^>]*>(.*?)</div>',
            r'<p[^>]*class="[^"]*desc[^"]*"[^>]*>(.*?)</p>'
        ]
        
        for pattern in desc_patterns:
            desc_match = re.search(pattern, html, re.S)
            if desc_match:
                desc = desc_match.group(1).strip()
                return self._clean_text(desc)
        
        return ''

    def _extract_video_info(self, html):
        """提取视频基本信息"""
        info = {}
        
        meta_pattern = r'<div[^>]*class="meta"[^>]*>(.*?)</div>'
        meta_matches = re.findall(meta_pattern, html, re.S)
        
        if meta_matches and len(meta_matches) >= 1:
            meta1 = meta_matches[0]
            parts = [p.strip() for p in meta1.split('&nbsp;/&nbsp;') if p.strip()]
            
            if parts:
                # 提取国家
                country_match = re.search(r'([\u4e00-\u9fa5]+)', parts[0])
                if country_match:
                    info['area'] = country_match.group(1)
                
                # 提取类型
                if len(parts) > 1:
                    type_match = re.search(r'([\u4e00-\u9fa5]+)', parts[1])
                    if type_match:
                        info['type'] = type_match.group(1)
                
                # 提取时长
                for part in parts:
                    if '分钟' in part:
                        info['remarks'] = part.strip()
        
        if meta_matches and len(meta_matches) >= 2:
            info['actor'] = meta_matches[1].strip()
        
        return info

    def _extract_play_resources(self, html):
        """提取播放资源"""
        play_lines = []
        
        # 夸克网盘链接
        quark_pattern = r'<a[^>]*href="([^"]*pan\.quark\.cn[^"]*)"[^>]*>'
        quark_matches = re.findall(quark_pattern, html, re.S)
        
        for i, resource_url in enumerate(quark_matches[:5], 1):
            play_url = self._extract_quark_url(resource_url)
            if play_url:
                play_lines.append(f"夸克网盘{i}${play_url}")
        
        # 磁力链接
        magnet_patterns = [
            r'href="(magnet:\?[^"]+)"',
            r'<a[^>]*href="(magnet:[^"]+)"[^>]*>'
        ]
        
        for pattern in magnet_patterns:
            matches = re.findall(pattern, html, re.S)
            for i, match in enumerate(matches[:5], 1):
                if isinstance(match, str) and match.startswith('magnet:'):
                    play_lines.append(f"磁力链接{i}${match}")
        
        return play_lines

    def _get_page_count(self, html, current_page):
        """提取总页数"""
        current_page = int(current_page) if current_page else 1
        
        # 检查加载更多按钮
        load_more_pattern = r'<a[^>]*class="[^"]*btn-load[^"]*"[^>]*data-url="[^"]*\?page=(\d+)"[^>]*>'
        load_more_match = re.search(load_more_pattern, html, re.S)
        
        if load_more_match:
            return current_page + 1
        
        # 查找分页链接
        page_patterns = [
            r'<a[^>]*href="[^"]*\?page=(\d+)"[^>]*>',
            r'class="page-numbers">(\d+)</a>',
            r'page=(\d+)'
        ]
        
        max_page = current_page
        for pattern in page_patterns:
            page_matches = re.findall(pattern, html)
            for page_num in page_matches:
                if isinstance(page_num, str) and page_num.isdigit():
                    page_int = int(page_num)
                    if page_int > max_page:
                        max_page = page_int
        
        return max_page if max_page > 0 else 1

    def _clean_text(self, text):
        """清理文本"""
        if not text:
            return text
        
        replacements = {
            '&#39;': "'", '&amp;': '&', '&nbsp;': ' ', '&quot;': '"',
            '&lt;': '<', '&gt;': '>', '&ldquo;': '"', '&rdquo;': '"',
            '&lsquo;': "'", '&rsquo;': "'", '&#8217;': "'", '&#8220;': '"',
            '&#8221;': '"', '&#8230;': '...', '&amp;#39;': "'"
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _get_header(self):
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
            "Referer": self.baseUrl
        }
    
    def localProxy(self, params):
        pass

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return []

    def destroy(self):
        pass