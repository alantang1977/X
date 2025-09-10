# -*- coding: utf-8 -*-
# 麦田影院 - 七哥定制版
import re
import sys
import json
import time
import random
from urllib.parse import quote, unquote, urljoin
from pyquery import PyQuery as pq
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def init(self, extend=""):
        """初始化 适配配置"""
        # 修复：删除末尾空格
        self.host = "https://www.mtyy1.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 11; MI 11 Build/RKQ1.201022.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/92.0.4515.159 Mobile Safari/537.36 TVBox/1.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': self.host
        }
        self.source_map = {"NBY": "高清NB源", "1080zyk": "超清YZ源", "ffm3u8": "极速FF源", "lzm3u8": "稳定LZ源", "yzzy": "YZ源"}
        self.ua_list = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
        ]

    def getName(self):
        return "麦田影院"

    def isVideoFormat(self, url):
        """判断是否为直接播放格式"""
        video_exts = ['.mp4', '.m3u8', '.flv', '.avi', '.mov', '.rmvb', '.m3u8']
        return any(ext in url.lower() for ext in video_exts)

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    def fix_encoding(self, text):
        """加强版编码修复，适配中文显示"""
        if not text:
            return ""
        try:
            # 处理可能的乱码情况
            if isinstance(text, bytes):
                try:
                    text = text.decode('utf-8')
                except UnicodeDecodeError:
                    text = text.decode('gbk', errors='ignore')
            
            # 处理Unicode转义序列
            if '\\u' in text:
                try:
                    text = text.encode('utf-8').decode('unicode_escape')
                except:
                    pass
            
            garbled_replace = {
                '\u00e4\u00b8\u00ad': '中', '\u00e6\u0096\u0087': '文',
                '\u00e5\u00bd\u00b1': '影', '\u00e8\u00a7\u0086': '视',
                '\u00e9\u00a2\u0091': '频', '\u00c3\u00a4': 'ä', '\u00c3\u00b6': 'ö'
            }
            for garbled, correct in garbled_replace.items():
                text = text.replace(garbled, correct)
            
            # 清理不可见字符
            text = re.sub(r'[\x00-\x1f\x7f]', '', text).strip()
            return text
        except Exception as e:
            self.log(f"编码修复异常: {str(e)}")
            return str(text) if text else ""

    def fetch_with_encoding(self, url, **kwargs):
        """带编码处理的请求方法，确保正确获取页面内容"""
        try:
            # 随机延迟，避免被识别为爬虫
            time.sleep(random.uniform(0.5, 1.5))
            
            # 随机选择User-Agent
            headers = kwargs.get('headers', self.headers.copy())
            headers['User-Agent'] = random.choice(self.ua_list)
            kwargs['headers'] = headers
            
            response = self.fetch(
                url,
                timeout=15,
                allow_redirects=True,
                **kwargs
            )
            response.encoding = 'utf-8'
            if response.status_code != 200 or len(response.text) < 1000:
                self.log(f"请求失败，状态码: {response.status_code}，内容长度: {len(response.text)}")
                raise Exception(f"页面内容无效或获取失败")
            return response
        except Exception as e:
            self.log(f"请求 {url} 出错: {str(e)}")
            raise

    def getpq(self, text):
        """安全的pyquery解析，处理可能的解析错误"""
        try:
            return pq(text)
        except Exception as e:
            self.log(f"PyQuery 解析失败: {str(e)}")
            clean_text = re.sub(r'[^\x20-\x7e\u4e00-\u9fff]', '', text)
            return pq(clean_text) if clean_text else pq('')

    def homeContent(self, filter):
        """获取首页内容和分类"""
        try:
            response = self.fetch_with_encoding(self.host)
            doc = self.getpq(response.text)

            result = {}
            classes = []
            nav_items = doc('div.head-nav a[href*="/vodtype/"], .this-wap a[href*="/vodtype/"]').items()
            seen_cate = set()
            for item in nav_items:
                cate_text = self.fix_encoding(item.text().strip())
                cate_href = item.attr('href')
                if not cate_text or not cate_href or '/vodtype/' not in cate_href:
                    continue
                cate_id = re.search(r'/vodtype/(\d+)\.html', cate_href)
                if not cate_id or cate_id.group(1) in seen_cate:
                    continue
                cate_id = cate_id.group(1)
                seen_cate.add(cate_id)
                classes.append({
                    'type_name': cate_text,
                    'type_id': cate_id
                })

            videos = []
            seen_ids = set()
            # 修复：精准选择器，确保抓取首页影片
            video_boxes = doc('.public-list-box.public-pic-b, .wap-diy-vod-a .public-list-box').items()
            for box in video_boxes:
                link = box.find('a.public-list-exp')
                if not link:
                    continue
                vod_href = link.attr('href')
                vod_id = re.search(r'/voddetail/(\d+)\.html', vod_href)
                if not vod_id or vod_id.group(1) in seen_ids:
                    continue
                vod_id = vod_id.group(1)
                seen_ids.add(vod_id)

                img = link.find('img')
                # --- 修复标题：优先使用 a 标签的 title 属性或文本，避免使用 img.alt ---
                vod_title = self.fix_encoding(
                    link.attr('title') or 
                    link.text().strip() or 
                    img.attr('alt') or ""
                )
                if not vod_title:
                    continue

                # --- 修复封面图：优先使用 data-src ---
                vod_pic = img.attr('data-src') or img.attr('src') or ""
                vod_pic = urljoin(self.host, vod_pic) if vod_pic else ""
                
                vod_remarks = self.fix_encoding(
                    box.find('.public-prt, .episode, .public-list-prb').text().strip() or
                    (re.search(r'第\d+[集期]|更新至|完结|HD|超清', box.text()).group() if re.search(r'第\d+[集期]|更新至|完结|HD|超清', box.text()) else "")
                )
                videos.append({
                    'vod_id': vod_id,
                    'vod_name': vod_title,
                    'vod_pic': vod_pic,
                    'vod_year': '',
                    'vod_remarks': vod_remarks
                })
            
            result['class'] = classes
            result['list'] = videos
            return result
        except Exception as e:
            self.log(f"获取首页内容时出错: {e}")
            return {'class': [], 'list': []}

    def homeVideoContent(self):
        return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        """获取分类内容"""
        try:
            url = f"{self.host}/vodtype/{tid}.html"
            if int(pg) > 1:
                url = f"{self.host}/vodtype/{tid}-{pg}.html"

            response = self.fetch_with_encoding(url)
            doc = self.getpq(response.text)

            videos = []
            seen_ids = set()
            # 修复：精准选择器
            video_boxes = doc('.public-list-box.public-pic-b').items()
            for box in video_boxes:
                link = box.find('a.public-list-exp')
                if not link:
                    continue
                vod_href = link.attr('href')
                vod_id = re.search(r'/voddetail/(\d+)\.html', vod_href)
                if not vod_id or vod_id.group(1) in seen_ids:
                    continue
                vod_id = vod_id.group(1)
                seen_ids.add(vod_id)

                img = link.find('img')
                # --- 修复标题：优先使用 a 标签的 title 属性或文本 ---
                vod_title = self.fix_encoding(
                    link.attr('title') or 
                    link.text().strip() or 
                    img.attr('alt') or ""
                )
                # --- 修复封面图：优先使用 data-src ---
                vod_pic = urljoin(self.host, img.attr('data-src') or img.attr('src') or "")
                vod_remarks = self.fix_encoding(box.find('.public-prt, .public-list-prb').text().strip() or "")

                if vod_title:
                    videos.append({
                        'vod_id': vod_id,
                        'vod_name': vod_title,
                        'vod_pic': vod_pic,
                        'vod_year': '',
                        'vod_remarks': vod_remarks
                    })

            result = {
                'list': videos,
                'page': pg,
                'pagecount': 9999,
                'limit': 80,
                'total': 999999
            }
            return result
        except Exception as e:
            self.log(f"获取分类内容时出错: {e}")
            return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 80, 'total': 0}

    def detailContent(self, ids):
        """获取视频详情，修复播放源显示问题"""
        result = {"list": []}
        if not ids or len(ids) == 0:
            return result
        vod_id = ids[0]

        try:
            # 先访问详情页获取基本信息
            detail_url = f"{self.host}/voddetail/{vod_id}.html"
            response = self.fetch_with_encoding(detail_url)
            doc = self.getpq(response.text)

            vod_info = {
                "vod_id": vod_id,
                "vod_name": self.fix_encoding(doc('h1.player-title-link').text().strip()),
                # --- 修复封面图：优先使用 data-src ---
                "vod_pic": urljoin(self.host, doc('.role-card img').attr('data-src') or doc('.role-card img').attr('src') or ""),
                "vod_year": self.fix_encoding(doc('.player-details a[href*="2025"]').text().strip() or doc('.player-details li:contains("年份")').text().split('：')[-1].strip()),
                "vod_remarks": self.fix_encoding(doc('.co3').text().strip() or "7.7分"),
                "vod_actor": self.fix_encoding(doc('.vod_data').attr('vod_actor') if doc('.vod_data') else ""),
                "vod_director": self.fix_encoding(doc('.vod_data').attr('vod_director') if doc('.vod_data') else ""),
                "vod_content": self.fix_encoding(doc('.card-text').text().strip()),
                "vod_play_from": "",
                "vod_play_url": ""
            }
            
            # 尝试获取播放页URL
            play_page_url = None
            play_link = doc('.anthology-list-play a:first').attr('href')
            if play_link:
                play_page_url = urljoin(self.host, play_link)
            
            # 如果无法获取播放页URL，使用默认URL
            if not play_page_url:
                play_page_url = f"{self.host}/vodplay/{vod_id}-1-1.html"
            
            # 访问播放页获取播放源信息
            play_response = self.fetch_with_encoding(play_page_url)
            play_doc = self.getpq(play_response.text)
            
            # 存储所有线路信息
            all_sources_data = {} # {source_name: [episode1$url1, episode2$url2], ...}
            
            # --- 解析所有播放源 ---
            # 查找播放源选项卡
            tab_items = play_doc('a.vod-playerUrl[data-form]').items()
            
            for tab in tab_items:
                data_form = tab.attr('data-form')
                source_name = self.fix_encoding(tab.text().replace('', '').strip())
                
                # 标准化线路名称
                display_source_name = self.source_map.get(data_form, source_name)
                
                # 查找对应的播放列表
                episodes = []
                # 获取当前选项卡的索引
                tab_index = list(play_doc('a.vod-playerUrl[data-form]')).index(tab[0])
                
                # 找到对应的剧集列表
                episode_boxes = play_doc('.anthology-list-box').eq(tab_index)
                episode_links = episode_boxes.find('a').items()
                
                for ep in episode_links:
                    ep_title = self.fix_encoding(ep.text().strip())
                    ep_href = ep.attr('href')
                    if ep_title and ep_href:
                        # 为每个播放源生成不同的URL（根据data-form参数）
                        full_href = urljoin(self.host, ep_href)
                        # 添加播放源标识到URL
                        if '?' in full_href:
                            full_href += f'&source={data_form}'
                        else:
                            full_href += f'?source={data_form}'
                        episodes.append(f"{ep_title}${full_href}")
                
                if episodes:
                    all_sources_data[display_source_name] = '#'.join(episodes)

            # --- 排序和优先使用YZ源 ---
            final_play_from = []
            final_play_url = []
            
            yz_source_name = "超清YZ源"
            if yz_source_name in all_sources_data:
                final_play_from.append(yz_source_name)
                final_play_url.append(all_sources_data.pop(yz_source_name))

            for src_name, src_urls in all_sources_data.items():
                final_play_from.append(src_name)
                final_play_url.append(src_urls)
            
            if not final_play_from:
                default_ep = play_doc('.anthology-list-play a:first').attr('href')
                if default_ep:
                    final_play_from.append("默认源")
                    final_play_url.append(f"正片${urljoin(self.host, default_ep)}")

            vod_info["vod_play_from"] = "$$$".join(final_play_from)
            vod_info["vod_play_url"] = "$$$".join(final_play_url)
            
            result["list"].append(vod_info)
            return result
        except Exception as e:
            self.log(f"获取视频详情时出错: {e}")
            return {'list': []}

    def searchContent(self, key, quick, pg="1"):
        """搜索功能 - 带验证码处理"""
        result = {"list": [], "page": int(pg)}
        
        try:
            # 编码搜索关键词
            encoded_key = quote(key)
            search_url = f"{self.host}/vodsearch/-------------.html?wd={encoded_key}"
            
            if int(pg) > 1:
                search_url = f"{self.host}/vodsearch/-------------.html?wd={encoded_key}&page={pg}"
            
            # 添加随机延迟，避免被识别为爬虫
            time.sleep(random.uniform(1.0, 2.5))
            
            # 使用更真实的浏览器头
            headers = self.headers.copy()
            headers.update({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0',
                'TE': 'Trailers'
            })
            
            response = self.fetch(search_url, headers=headers, timeout=15)
            
            # 检查是否被重定向到验证码页面
            if response.url and "captcha" in response.url.lower():
                self.log("检测到验证码页面，尝试绕过...")
                # 尝试使用不同的方法绕过验证码
                return self.handle_captcha_search(key, pg)
                
            # 检查响应内容是否包含验证码提示
            html_content = response.text
            if "验证码" in html_content or "captcha" in html_content.lower():
                self.log("页面包含验证码提示，尝试绕过...")
                return self.handle_captcha_search(key, pg)
                
            # 正常解析搜索结果
            doc = self.getpq(html_content)
            
            # 多种选择器尝试获取结果
            selectors = [
                '.public-list-box',
                '.public-pic-b',
                '.public-list-div',
                '.vod-item',
                '.search-result-item',
                '[class*="vod"]'
            ]
            
            videos = []
            seen_ids = set()
            
            for selector in selectors:
                items = doc(selector)
                if items.length > 0:
                    for item in items.items():
                        try:
                            link = item.find('a[href*="/voddetail/"]').first()
                            if not link:
                                continue
                                
                            vod_href = link.attr('href')
                            if not vod_href:
                                continue
                                
                            vod_id_match = re.search(r'/voddetail/(\d+)\.html', vod_href)
                            if not vod_id_match:
                                continue
                                
                            vod_id = vod_id_match.group(1)
                            if vod_id in seen_ids:
                                continue
                                
                            seen_ids.add(vod_id)
                            
                            # 提取标题
                            title_selectors = [
                                '.time-title', '.vod-name', '.title', 
                                'img[alt]', '[title]', 'h3', 'h4'
                            ]
                            
                            vod_title = ""
                            for title_sel in title_selectors:
                                title_elem = item.find(title_sel).first()
                                if title_elem:
                                    title_text = title_elem.attr('title') or title_elem.attr('alt') or title_elem.text()
                                    if title_text and len(title_text.strip()) > 0:
                                        vod_title = self.fix_encoding(title_text.strip())
                                        break
                            
                            if not vod_title:
                                continue
                                
                            # 提取封面
                            img = item.find('img').first()
                            vod_pic = img.attr('data-src') or img.attr('src') or ""
                            if vod_pic and not vod_pic.startswith(('http://', 'https://')):
                                vod_pic = urljoin(self.host, vod_pic)
                                
                            # 提取备注
                            remark_selectors = ['.public-prt', '.public-list-prb', '.remark', '.episode']
                            vod_remarks = ""
                            for remark_sel in remark_selectors:
                                remark_elem = item.find(remark_sel).first()
                                if remark_elem:
                                    remark_text = remark_elem.text()
                                    if remark_text and len(remark_text.strip()) > 0:
                                        vod_remarks = self.fix_encoding(remark_text.strip())
                                        break
                                        
                            videos.append({
                                "vod_id": vod_id,
                                "vod_name": vod_title,
                                "vod_pic": vod_pic,
                                "vod_year": "",
                                "vod_remarks": vod_remarks
                            })
                        except:
                            continue
                    
                    if videos:
                        break
            
            result["list"] = videos
            self.log(f"搜索 '{key}' 找到 {len(videos)} 个结果")
            
        except Exception as e:
            self.log(f"搜索失败: {str(e)}")
            # 尝试备用搜索方法
            try:
                return self.backupSearch(key, pg)
            except Exception as backup_error:
                self.log(f"备用搜索也失败: {str(backup_error)}")
                
        return result

    def handle_captcha_search(self, key, pg):
        """处理验证码的搜索方法"""
        result = {"list": [], "page": int(pg)}
        
        try:
            # 方法1: 尝试使用不同的User-Agent
            encoded_key = quote(key)
            search_url = f"{self.host}/vodsearch/-------------.html?wd={encoded_key}"
            
            if int(pg) > 1:
                search_url = f"{self.host}/vodsearch/-------------.html?wd={encoded_key}&page={pg}"
            
            # 尝试不同的User-Agent
            for ua in self.ua_list:
                try:
                    headers = {
                        'User-Agent': ua,
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                        'Cache-Control': 'max-age=0'
                    }
                    
                    time.sleep(random.uniform(2.0, 4.0))
                    response = self.fetch(search_url, headers=headers, timeout=15)
                    
                    # 检查是否仍然有验证码
                    html_content = response.text
                    if "验证码" not in html_content and "captcha" not in html_content.lower():
                        # 解析搜索结果
                        doc = self.getpq(html_content)
                        videos = []
                        seen_ids = set()
                        
                        # 简化选择器
                        items = doc('.public-list-box, .public-pic-b, .public-list-div')
                        for item in items.items():
                            link = item.find('a[href*="/voddetail/"]').first()
                            if not link:
                                continue
                                
                            vod_href = link.attr('href')
                            vod_id_match = re.search(r'/voddetail/(\d+)\.html', vod_href)
                            if not vod_id_match:
                                continue
                                
                            vod_id = vod_id_match.group(1)
                            if vod_id in seen_ids:
                                continue
                                
                            seen_ids.add(vod_id)
                            
                            # 提取标题
                            vod_title = self.fix_encoding(
                                link.attr('title') or 
                                item.find('.time-title').text() or 
                                item.find('img').attr('alt') or 
                                link.text() or ""
                            ).strip()
                            
                            if not vod_title:
                                continue
                                
                            # 提取封面
                            img = item.find('img').first()
                            vod_pic = img.attr('data-src') or img.attr('src') or ""
                            if vod_pic and not vod_pic.startswith(('http://', 'https://')):
                                vod_pic = urljoin(self.host, vod_pic)
                                
                            videos.append({
                                "vod_id": vod_id,
                                "vod_name": vod_title,
                                "vod_pic": vod_pic,
                                "vod_year": "",
                                "vod_remarks": ""
                            })
                        
                        result["list"] = videos
                        self.log(f"使用备用UA成功搜索 '{key}'，找到 {len(videos)} 个结果")
                        return result
                        
                except Exception as e:
                    self.log(f"使用UA {ua[:30]}... 搜索失败: {str(e)}")
                    continue
                    
            # 如果所有方法都失败，返回空结果
            self.log("所有绕过验证码的方法都失败了")
            
        except Exception as e:
            self.log(f"验证码处理失败: {str(e)}")
            
        return result

    def backupSearch(self, key, pg):
        """备用搜索方法 - 使用更简单的选择器"""
        result = {"list": [], "page": int(pg)}
        
        try:
            encoded_key = quote(key)
            search_url = f"{self.host}/vodsearch/-------------.html?wd={encoded_key}"
            
            response = self.fetch_with_encoding(search_url)
            html_content = response.text
            
            # 使用正则表达式提取搜索结果
            pattern = r'<a\s+href="(/voddetail/\d+\.html)"[^>]*>(.*?)</a>'
            matches = re.findall(pattern, html_content, re.DOTALL)
            
            seen_ids = set()
            for href, content in matches:
                vod_id_match = re.search(r'/voddetail/(\d+)\.html', href)
                if not vod_id_match:
                    continue
                    
                vod_id = vod_id_match.group(1)
                if vod_id in seen_ids:
                    continue
                    
                seen_ids.add(vod_id)
                
                # 提取标题
                title_match = re.search(r'<img[^>]*alt="([^"]*)"', content)
                if not title_match:
                    title_match = re.search(r'title="([^"]*)"', content)
                if not title_match:
                    # 尝试从链接内容提取文本
                    text_match = re.search(r'>([^<]+)<', content)
                    if text_match:
                        vod_title = text_match.group(1).strip()
                    else:
                        continue
                else:
                    vod_title = title_match.group(1)
                    
                vod_title = self.fix_encoding(vod_title)
                if not vod_title:
                    continue
                    
                # 提取封面图
                img_match = re.search(r'<img[^>]*src="([^"]*)"', content)
                vod_pic = img_match.group(1) if img_match else ""
                if vod_pic and not vod_pic.startswith(('http://', 'https://')):
                    vod_pic = urljoin(self.host, vod_pic)
                    
                result["list"].append({
                    "vod_id": vod_id,
                    "vod_name": vod_title,
                    "vod_pic": vod_pic,
                    "vod_year": "",
                    "vod_remarks": ""
                })
                
        except Exception as e:
            self.log(f"备用搜索失败: {str(e)}")
            
        return result

    def playerContent(self, flag, id, vipFlags):
        """播放地址解析 - 终极修复版"""
        try:
            play_page_url = urljoin(self.host, id)
            if not play_page_url.startswith(('http://', 'https://')):
                self.log(f"无效播放地址: {id}")
                return {"parse": 1, "url": "", "header": self.headers}

            response = self.fetch_with_encoding(play_page_url)
            html_content = response.text

            # --- 核心：提取播放器配置 ---
            player_match = re.search(r'var\s+player_aaaa\s*=\s*({[^}]+?url\s*:\s*["\'][^"\']+["\'][^}]*})', html_content, re.DOTALL)
            if not player_match:
                self.log("未找到播放器配置脚本 player_aaaa")
                return {"parse": 1, "url": play_page_url, "header": self.headers}

            player_json_str = player_match.group(1)
            # 修复可能的JSON格式问题（尾部逗号）
            player_json_str = re.sub(r',\s*([}\]])', r'\1', player_json_str)

            try:
                player_data = json.loads(player_json_str)
            except json.JSONDecodeError as e:
                self.log(f"解析播放器 JSON 失败: {str(e)}")
                return {"parse": 1, "url": play_page_url, "header": self.headers}

            # --- 提取主播放地址和备用地址 ---
            main_url = player_data.get("url", "").strip()
            backup_url = player_data.get("url_next", "").strip()

            # URL解码
            if '%' in main_url:
                main_url = unquote(main_url)
            if '%' in backup_url:
                backup_url = unquote(backup_url)

            self.log(f"[修复版] 提取的主播放地址: {main_url}")
            self.log(f"[修复版] 提取的备用播放地址: {backup_url}")

            # --- 极简播放逻辑：谁有效播谁 ---
            # 优先使用主地址
            if main_url and self.isVideoFormat(main_url):
                return {
                    "parse": 0,  # 0 = 直接播放
                    "url": main_url,
                    "header": {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
                        "Referer": play_page_url,  # ⚠️ 关键！必须添加 Referer
                        "Origin": self.host.rstrip('/')
                    }
                }
            # 主地址无效，尝试备用地址
            elif backup_url and self.isVideoFormat(backup_url):
                return {
                    "parse": 0,
                    "url": backup_url,
                    "header": {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
                        "Referer": play_page_url,  # ⚠️ 关键！必须添加 Referer
                        "Origin": self.host.rstrip('/')
                    }
                }

            # --- 万不得已的兜底方案 ---
            self.log("未能提取有效视频地址，返回播放页")
            return {
                "parse": 1,
                "url": play_page_url,
                "header": self.headers
            }

        except Exception as e:
            self.log(f"播放地址解析异常: {str(e)}")
            return {
                "parse": 1,
                "url": urljoin(self.host, id),
                "header": self.headers
            }

    def localProxy(self, param):
        pass