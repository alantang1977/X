# -*- coding: utf-8 -*-
# 本资源来源于互联网公开渠道，仅可用于个人学习爬虫技术。
# 严禁将其用于任何商业用途，下载后请于 24 小时内删除，搜索结果均来自源站，本人不承担任何责任。
import sys
import logging
import urllib3
from typing import Dict, List, Any

sys.path.append('..')
try:
    from base.spider import Spider  # 假设base.spider的fetch是requests封装的请求方法
except ImportError:
    # 兼容无base.spider的情况，使用requests实现基础fetch
    import requests
    class BaseSpider:
        def fetch(self, url, headers=None, verify=False, timeout=10):
            try:
                resp = requests.get(url, headers=headers, verify=verify, timeout=timeout)
                resp.raise_for_status()
                return resp
            except Exception as e:
                logging.error(f"请求失败 {url}: {str(e)}")
                return None
    Spider = BaseSpider

# 配置日志（方便调试定位问题）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# 禁用不安全请求警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class FilmSpider(Spider):
    # 初始化请求头（增加超时+优化UA）
    DEFAULT_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'accept-language': 'zh-CN,zh;q=0.9',
        'cache-control': 'no-cache',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin'
    }
    DEFAULT_HOST = 'https://film.symx.club'
    REQUEST_TIMEOUT = 10  # 请求超时时间

    def __init__(self):
        self.host = self.DEFAULT_HOST
        self.headers = self.DEFAULT_HEADERS
        super().__init__()

    def init(self, extend: str = '') -> None:
        """初始化宿主地址"""
        try:
            if not extend:
                return
            host = extend.strip().rstrip('/')
            if host.startswith(('http://', 'https://')):
                self.host = host
                logging.info(f"成功初始化宿主地址: {self.host}")
        except Exception as e:
            logging.error(f'初始化异常：{str(e)}')

    def _safe_fetch_json(self, url: str) -> Dict[str, Any]:
        """安全请求JSON接口（封装异常处理）"""
        try:
            resp = self.fetch(
                url=url,
                headers=self.headers,
                verify=False,
                timeout=self.REQUEST_TIMEOUT
            )
            if not resp:
                logging.error(f"请求无响应: {url}")
                return {}
            return resp.json()
        except ValueError as e:
            logging.error(f"JSON解析失败 {url}: {str(e)}")
            return {}
        except Exception as e:
            logging.error(f"请求异常 {url}: {str(e)}")
            return {}

    def homeContent(self, filter: Any = None) -> Dict[str, List[Dict]]:
        """获取首页分类"""
        url = f'{self.host}/api/category/top'
        response = self._safe_fetch_json(url)
        classes = []
        for item in response.get('data', []):
            if isinstance(item, dict) and 'id' in item and 'name' in item:
                classes.append({
                    'type_id': item['id'],
                    'type_name': item['name']
                })
        logging.info(f"获取到分类数量: {len(classes)}")
        return {'class': classes}

    def homeVideoContent(self) -> Dict[str, List[Dict]]:
        """获取首页视频列表"""
        url = f'{self.host}/api/film/category'
        response = self._safe_fetch_json(url)
        videos = []
        for cate_item in response.get('data', []):
            for film in cate_item.get('filmList', []):
                if not isinstance(film, dict):
                    continue
                videos.append({
                    'vod_id': film.get('id', ''),
                    'vod_name': film.get('name', ''),
                    'vod_pic': film.get('cover', ''),
                    'vod_remarks': film.get('doubanScore', '')
                })
        logging.info(f"获取首页视频数量: {len(videos)}")
        return {'list': videos}

    def categoryContent(self, tid: str, pg: str, filter: Any = None, extend: str = '') -> Dict[str, Any]:
        """获取分类视频列表"""
        # 参数校验与转换
        try:
            pg_int = int(pg) if pg else 1
            tid_str = str(tid) if tid else ''
        except ValueError:
            pg_int = 1
            tid_str = ''
            logging.warning("分页/分类ID参数异常，使用默认值")

        url = (
            f'{self.host}/api/film/category/list?'
            f'area=&categoryId={tid_str}&language=&pageNum={pg_int}&pageSize=15&sort=updateTime&year='
        )
        response = self._safe_fetch_json(url)
        videos = []
        total = response.get('data', {}).get('total', 0)  # 补充总页数/总数
        for film in response.get('data', {}).get('list', []):
            if not isinstance(film, dict):
                continue
            videos.append({
                'vod_id': film.get('id', ''),
                'vod_name': film.get('name', ''),
                'vod_pic': film.get('cover', ''),
                'vod_remarks': film.get('updateStatus', '')
            })
        logging.info(f"分类{tid_str}第{pg_int}页获取视频数量: {len(videos)}")
        return {
            'list': videos,
            'page': pg_int,
            'total': total,  # 补充总数，方便前端分页
            'pagecount': (total + 14) // 15  # 总页数
        }

    def searchContent(self, key: str, quick: Any = None, pg: str = '1') -> Dict[str, Any]:
        """搜索视频"""
        if not key:
            logging.warning("搜索关键词为空")
            return {'list': [], 'page': 1, 'total': 0}
        # 参数校验
        try:
            pg_int = int(pg)
        except ValueError:
            pg_int = 1
            logging.warning("搜索分页参数异常，使用默认值1")

        url = f'{self.host}/api/film/search?keyword={key}&pageNum={pg_int}&pageSize=10'
        response = self._safe_fetch_json(url)
        videos = []
        total = response.get('data', {}).get('total', 0)
        for film in response.get('data', {}).get('list', []):
            if not isinstance(film, dict):
                continue
            videos.append({
                'vod_id': film.get('id', ''),
                'vod_name': film.get('name', ''),
                'vod_pic': film.get('cover', ''),
                'vod_remarks': film.get('updateStatus', ''),
                'vod_year': film.get('year', ''),
                'vod_area': film.get('area', ''),
                'vod_director': film.get('director', '')
            })
        logging.info(f"关键词[{key}]第{pg_int}页获取视频数量: {len(videos)}")
        return {
            'list': videos,
            'page': pg_int,
            'total': total,
            'pagecount': (total + 9) // 10
        }

    def detailContent(self, ids: List[str]) -> Dict[str, List[Dict]]:
        """获取视频详情"""
        if not ids or not ids[0]:
            logging.warning("视频ID为空")
            return {'list': []}
        vid = ids[0]
        url = f'{self.host}/api/film/detail?id={vid}'
        response = self._safe_fetch_json(url)
        data = response.get('data', {})
        if not data:
            logging.error(f"视频{vid}无详情数据")
            return {'list': []}

        video = {}
        show_list = []
        play_url_list = []
        # 解析播放线路
        for play_line in data.get('playLineList', []):
            if not isinstance(play_line, dict):
                continue
            player_name = play_line.get('playerName', '')
            if not player_name:
                continue
            show_list.append(player_name)
            # 解析线路下的播放源
            line_urls = []
            for line in play_line.get('lines', []):
                if isinstance(line, dict):
                    line_name = line.get('name', '')
                    line_id = line.get('id', '')
                    if line_name and line_id:
                        line_urls.append(f"{line_name}${line_id}")
            play_url_list.append('#'.join(line_urls))

        # 组装详情数据（修正原代码vod_area取值错误）
        video.update({
            'vod_id': data.get('id', ''),
            'vod_name': data.get('name', ''),
            'vod_pic': data.get('cover', ''),
            'vod_year': data.get('year', ''),
            'vod_area': data.get('area', ''),  # 原代码取other，修正为area
            'vod_actor': data.get('actor', ''),
            'vod_director': data.get('director', ''),
            'vod_content': data.get('blurb', ''),
            'vod_score': data.get('doubanScore', ''),
            'vod_play_from': '$$$'.join(show_list),
            'vod_play_url': '$$$'.join(play_url_list)
        })
        logging.info(f"获取视频{vid}详情成功")
        return {'list': [video]}

    def playerContent(self, flag: str, id: str, vipflags: Any = None) -> Dict[str, Any]:
        """解析播放地址"""
        if not id:
            logging.warning("播放线路ID为空")
            return {'jx': '0', 'parse': '0', 'url': '', 'header': {}}
        url = f'{self.host}/api/line/play/parse?lineId={id}'
        response = self._safe_fetch_json(url)
        play_url = response.get('data', '')
        logging.info(f"解析线路{id}地址: {play_url[:50]}..." if play_url else f"线路{id}无播放地址")
        return {
            'jx': '0',
            'parse': '0',
            'url': play_url,
            'header': {'User-Agent': self.headers['User-Agent']}
        }

    # 补全原代码未实现的方法
    def getName(self) -> str:
        """返回爬虫名称"""
        return "山有木兮影视爬虫"

    def isVideoFormat(self, url: str) -> bool:
        """判断是否为视频格式URL"""
        video_ext = ('.mp4', '.m3u8', '.flv', '.avi', '.mov', '.wmv', '.mkv')
        return any(url.lower().endswith(ext) for ext in video_ext)

    def manualVideoCheck(self) -> bool:
        """手动视频校验"""
        return True

    def destroy(self) -> None:
        """销毁爬虫资源"""
        logging.info("爬虫资源已销毁")

    def localProxy(self, param: Any) -> Dict[str, Any]:
        """本地代理处理"""
        return {'code': 0, 'msg': 'success', 'data': {}}

# 测试代码（可选，用于验证功能）
if __name__ == '__main__':
    spider = FilmSpider()
    # 测试首页分类
    print("=== 首页分类 ===")
    home_cate = spider.homeContent()
    print(home_cate)
    # 测试首页视频
    print("\n=== 首页视频 ===")
    home_video = spider.homeVideoContent()
    print(f"视频数量: {len(home_video['list'])}")
    # 测试分类视频（假设分类ID为1，第1页）
    print("\n=== 分类视频 ===")
    cate_video = spider.categoryContent(tid='1', pg='1', filter=None, extend='')
    print(f"分类视频数量: {len(cate_video['list'])}")
    # 测试搜索（关键词：测试）
    print("\n=== 搜索视频 ===")
    search_video = spider.searchContent(key='测试', quick=None, pg='1')
    print(f"搜索结果数量: {len(search_video['list'])}")
