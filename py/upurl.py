import json
import requests
import warnings
import re
import os
import time
from urllib3.exceptions import InsecureRequestWarning
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor

# 自定义 jsm.json 的路径或网络地址，留空则使用当前目录下的 jsm.json
jsm_file_path = ""

# 读取 jsm.json 文件
jsm_data = {}
if jsm_file_path:
    if jsm_file_path.startswith(("http://", "https://")):
        try:
            response = requests.get(jsm_file_path)
            jsm_data = response.json()
        except Exception as e:
            print(f"从网络读取 jsm.json 配置文件失败: {str(e)}")
    else:
        if os.path.exists(jsm_file_path):
            try:
                with open(jsm_file_path, 'r', encoding='utf-8') as f:
                    jsm_data = json.load(f)
            except Exception as e:
                print(f"读取本地 jsm.json 配置文件失败: {str(e)}")
        else:
            print(f"本地 jsm.json 文件 {jsm_file_path} 不存在")
else:
    local_path = os.path.join(os.getcwd(), 'jsm.json')
    if os.path.exists(local_path):
        try:
            with open(local_path, 'r', encoding='utf-8') as f:
                jsm_data = json.load(f)
        except Exception as e:
            print(f"读取默认 jsm.json 配置文件失败: {str(e)}")
    else:
        print("默认的 jsm.json 文件不存在")

# 站点映射关系
site_mappings = {
    '立播': 'libo', '闪电':'shandian', '欧哥': 'ouge', '小米': 'xiaomi', '多多': 'duoduo',
    '蜡笔': 'labi', '至臻': 'zhizhen', '木偶':'mogg', '六趣': 'liuqu', '虎斑': 'huban',
    '下饭': 'xiafan', '玩偶': 'wogg', '星剧社':'star2', '二小': 'xhww'
}

# 代理配置
proxy_config = {
    "enabled": False,
    "proxies": {
        "http": "http://127.0.0.1:7890",
        "https": "http://127.0.0.1:7890"
    }
}

# 文件路径配置
file_path_config = {
    "input_dir": "",
    "output_dir": ""
}

# 新增jsm映射配置
jsm_mapping = {
    "Libvio": "libo",
    "Xiaomi": "xiaomi",
    "yydsys": "duoduo",
    "蜡笔网盘": "labi",
    "玩偶 | 蜡笔": "labi",
    "至臻|网盘": "zhizhen",
    "Huban": "huban",
    "Wogg": "wogg",
    "Mogg": "mogg",
    "玩偶 | 闪电uc": "shandian",
    "玩偶 | 二小": "xhww",
    "玩偶 | 小米": "xiaomi",
    "玩偶 | 多多": "duoduo",
    "玩偶 | 木偶": "mogg",
    "玩偶gg": "wogg",
    "星剧社": "star2"
}

# 需要拼接搜索路径的站点配置
search_path_config = {
    '闪电': '/index.php/vod/search.html?wd=仙台有树',
    '欧哥': '/index.php/vod/search.html?wd=仙台有树',
    '小米': '/index.php/vod/search.html?wd=仙台有树',
    '多多': '/index.php/vod/search.html?wd=仙台有树',
    '蜡笔': '/index.php/vod/search.html?wd=仙台有树',
    '至臻': '/index.php/vod/search.html?wd=仙台有树',
    '六趣': '/index.php/vod/search.html?wd=仙台有树',
    '虎斑': '/index.php/vod/search.html?wd=仙台有树',
    '下饭': '/index.php/vod/search.html?wd=仙台有树',
    '玩偶': '/vodsearch/-------------.html?wd=仙台有树',
    '木偶': '/index.php/vod/search.html?wd=仙台有树',
    '二小': '/index.php/vod/search.html?wd=仙台有树',
    '立播': '/search/-------------.html?wd=仙台有树&submit='
}

# 定义需要校验关键字的站点及其关键字
keyword_required_sites = {
    '闪电': 'class="search-stat"',
    '欧哥': 'class="search-stat"',
    '小米': 'class="search-stat"',
    '多多': 'class="search-stat"',
    '蜡笔': 'class="search-stat"',
    '至臻': 'class="search-stat"',
    '六趣': 'class="search-stat"',
    '虎斑': 'class="search-stat"',
    '下饭': 'class="search-stat"',
    '玩偶': 'class="search-stat"',
    '木偶': 'class="search-stat"',
    '二小': 'class="search-stat"',
    '立播': 'class="stui-screen"'
}

# 新增可选的URL加权配置，默认权重为50
url_weight_config = {
    "木偶": {
        "https://aliii.deno.dev": 60,
        "http://149.88.87.72:5666": 60
    },
    "至臻": {
        "http://www.xhww.net": 10,
        "http://xhww.net": 10
    },
    "立播": {
        "https://libvio.mov": 60,
        "https://www.libvio.cc": 60
    }
}

# 兜底URL配置
fallback_url_config = {
    "立播": [
        "https://libvio.mov",
        "https://www.libvio.cc",
        "https://libvio.la",
        "https://libvio.pro",
        "https://libvio.fun",
        "https://libvio.me",
        "https://libvio.in",
        "https://libvio.site",
        "https://libvio.art",
        "https://libvio.com",
        "https://libvio.vip",
        "https://libvio.pw",
        "https://libvio.link"
    ],
    "闪电": [
        "http://1.95.79.193",
        "http://1.95.79.193:666"
    ],
    "欧哥": [
        "https://woog.nxog.eu.org"
    ],
    "小米": [
        "http://www.54271.fun",
        "https://www.milvdou.fun",
        "http://www.54271.fun",
        "https://www.mucpan.cc",
        "https://mucpan.cc",
        "http://milvdou.fun"
    ],
    "多多": [
        "https://tv.yydsys.top",
        "https://tv.yydsys.cc",
        "https://tv.214521.xyz",
        "http://155.248.200.65"
    ],
    "蜡笔": [
        "http://feimaoai.site",
        "https://feimao666.fun",
        "http://feimao888.fun"
    ],
    "至臻": [
        "https://mihdr.top",
        "http://www.miqk.cc",
        "http://www.xhww.net",
        "http://xhww.net",
        "https://xiaomiai.site"
    ],
    "六趣": [
        "https://wp.0v.fit"
    ],
    "虎斑": [
        "http://103.45.162.207:20720"
    ],
    "下饭": [
        "http://txfpan.top",
        "http://www.xn--ghqy10g1w0a.xyz"
    ],
    "玩偶": [
        "https://wogg.xxooo.cf",
        "https://wogg.333232.xyz",
        "https://www.wogg.one",
        "https://www.wogg.lol",
        "https://www.wogg.net"
    ],
    "木偶": [
        "https://tv.91muou.icu",
        "https://mo.666291.xyz",
        "https://mo.muouso.fun",
        "https://aliii.deno.dev",
        "http://149.88.87.72:5666"
    ],
    "星剧社": [
        "https://mlink.cc/520TV"
    ],
    "二小": [
        "https://xhww.net",
        "https://www.xhww.net"
    ]
}

# 全局状态
last_site = None


def log_message(message, site_name=None, step="", max_error_length=80):
    """格式化日志打印"""
    global last_site

    status_emojis = {
        '[开始]': '🚀', '[成功]': '✅', '[完成]': '🎉', '[失败]': '❌',
        '[超时]': '⏳', '[警告]': '⚠️', '[错误]': '🚨', '[信息]': 'ℹ️',
        '[选择]': '🔍', '[连接失败]': '🔌'
    }

    if site_name and site_name != last_site:
        print(f"\n{'✨ ' + '=' * 38 + ' ✨'}")
        print(f"🌐 [站点: {site_name}]")
        print(f"{'✨ ' + '=' * 38 + ' ✨'}")
        last_site = site_name

    for status, emoji in status_emojis.items():
        if status in message:
            message = message.replace(status, f"{status} {emoji}")
            break
    else:
        message = f"{message} 📢"

    # 截断过长的错误信息
    if "[连接失败]" in message or "[错误]" in message:
        if len(message) > max_error_length:
            message = message[:max_error_length] + "..."

    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [{step}] {message}") if step else print(message)


def test_url(url, site_name=None):
    """增强版URL测试函数"""
    search_path = search_path_config.get(site_name)
    test_url = url.strip() + search_path if search_path else url.strip()
    keyword = keyword_required_sites.get(site_name)

    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(max_retries=2)
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    try:
        # 直接请求测试
        response = session.get(
            test_url,
            timeout=7,
            verify=False,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        )

        if response.status_code == 200:
            latency = response.elapsed.total_seconds()
            has_keyword = keyword in response.text if keyword else True

            log_msg = f"直接访问成功 | 延迟: {latency:.2f}s"
            if keyword:
                log_msg += f" | 关键字: {'✅' if has_keyword else '❌'}"

            log_message(f"[成功] {test_url} {log_msg}", site_name, "URL测试")
            return latency, has_keyword

        log_message(f"[失败] HTTP状态码 {response.status_code}", site_name, "URL测试")
        return None, None

    except requests.RequestException as e:
        error_type = "[超时]" if isinstance(e, requests.Timeout) else "[连接失败]"
        log_message(f"{error_type} {str(e)}", site_name, "URL测试")

        # 代理重试逻辑
        if proxy_config["enabled"]:
            try:
                response = session.get(
                    test_url,
                    timeout=7,
                    verify=False,
                    proxies=proxy_config["proxies"],
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
                )
                if response.status_code == 200:
                    latency = response.elapsed.total_seconds()
                    has_keyword = keyword in response.text if keyword else True
                    log_message(f"[成功] 代理访问成功 | 延迟: {latency:.2f}s | 关键字: {'✅' if has_keyword else '❌'}",
                                site_name, "URL测试")
                    return latency, has_keyword
            except Exception as proxy_e:
                log_message(f"[失败] 代理访问错误: {str(proxy_e)}", site_name, "URL测试")

        return None, None


def get_best_url(urls, site_name=None, existing_url=None):
    """优化后的URL选择算法"""
    if not isinstance(urls, list):
        return urls

    weights = url_weight_config.get(site_name, {})
    default_weight = 50
    sorted_urls = sorted([(url, weights.get(url, default_weight)) for url in urls],
                         key=lambda x: -x[1])

    def test_single_url(url_weight):
        url, weight = url_weight
        latency, has_keyword = test_url(url, site_name)
        if latency is not None:
            return {
                "url": url,
                "latency": latency,
                "has_keyword": has_keyword,
                "weight": weight,
                "score": (weight * 0.6) + ((1 / (latency + 0.1)) * 40)
            }
        return None

    with ThreadPoolExecutor() as executor:
        candidates = [result for result in executor.map(test_single_url, sorted_urls) if result]

    if not candidates:
        log_message(f"[警告] 无可用URL，使用现有配置: {existing_url}" if existing_url else
                    "[错误] 无可用URL且无历史配置", site_name, "URL选择")
        return existing_url if existing_url else None

    # 按评分排序：关键字存在 > 评分 > 延迟
    sorted_candidates = sorted(candidates,
                               key=lambda x: (-x['has_keyword'], -x['score'], x['latency']))

    log_message("候选URL评估结果:\n" + "\n".join(
        [f"{item['url']} | 权重:{item['weight']} 延迟:{item['latency']:.2f}s 评分:{item['score']:.1f}"
         for item in sorted_candidates]), site_name, "URL选择")

    best = sorted_candidates[0]
    log_message(f"[选择] 最优URL: {best['url']} (评分: {best['score']:.1f})", site_name, "URL选择")
    return best['url']


def get_star2_real_url(source_url):
    """改进的星剧社真实URL提取"""
    try:
        response = requests.get(
            source_url,
            timeout=8,
            verify=False,
            headers={'Referer': 'https://mlink.cc/'}
        )
        if response.status_code == 200:
            # 增强版正则匹配
            match = re.search(
                r'''(?i)(?:href|src|data-?url)=["'](https?://[^"']*?star2\.cn[^"']*)["']''',
                response.text
            )
            if match:
                real_url = match.group(1).strip().rstrip('/')
                log_message(f"[成功] 提取真实链接: {real_url}", "星剧社", "链接解析")
                return real_url
        log_message("[失败] 未找到有效链接", "星剧社", "链接解析")
    except Exception as e:
        log_message(f"[错误] 解析失败: {str(e)}", "星剧社", "链接解析")
    return None


def merge_url_data(*dicts):
    """数据合并去重"""
    merged = {}
    for d in dicts:
        if not d: continue
        for site, urls in d.items():
            merged.setdefault(site, []).extend(urls if isinstance(urls, list) else [urls])
    return {k: list(dict.fromkeys(v)) for k, v in merged.items()}


def get_file_path(filename, is_input=True):
    """路径处理函数"""
    base_dir = file_path_config.get("input_dir" if is_input else "output_dir", "")
    return os.path.join(base_dir or os.getcwd(), filename)


def load_existing_config():
    """加载现有url.json配置"""
    url_path = get_file_path('url.json')
    if os.path.exists(url_path):
        try:
            with open(url_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            log_message(f"[错误] 读取现有配置失败: {str(e)}", step="配置加载")
    return {}


def get_api_urls():
    """从本地文件获取链接"""
    API_FILE_PATH = get_file_path('url.json')
    try:
        with open(API_FILE_PATH, 'r', encoding='utf-8') as f:
            api_data = json.load(f)
        print("成功读取 url.json 文件")

        # 基于 jsm_mapping 生成 url_mapping
        url_mapping = {key: api_data.get(value) for key, value in jsm_mapping.items()}

        print("生成的 url_mapping:", url_mapping)
        return url_mapping
    except FileNotFoundError:
        print("未找到 url.json 文件，请检查文件路径。")
    except json.JSONDecodeError:
        print("url.json 文件格式错误，请检查文件内容。")
    return {}


def replace_urls(data, urls):
    """替换 JSON 数据中的 URL"""
    # 根据 jsm_mapping 转换 api_urls
    api_urls = {
        jsm_key: urls.get(jsm_value)
        for jsm_key, jsm_value in jsm_mapping.items()
    }

    sites = data.get('sites', [])
    replaced_count = 0

    for item in sites:
        if isinstance(item, dict):
            key = item.get('key')
            ext = item.get('ext')
            new_url = api_urls.get(key)
            old_url = None

            if new_url and isinstance(ext, str):
                parts = ext.split('$$$')
                if len(parts) > 1 and parts[1].strip().startswith('http'):
                    old_url = parts[1]
                    parts[1] = new_url
                    item['ext'] = '$$$'.join(parts)
                    replaced_count += 1
                    print(f"成功替换 {key} 的链接: {old_url} -> {new_url}")
                    if 'url' in item:
                        del item['url']  # 删除 url 字段

            if old_url and not new_url:
                print(f"未成功替换 {key} 的链接，原链接: {old_url}")
        else:
            print(f"跳过非字典类型的 item: {item}")

    print(f"总共替换了 {replaced_count} 个链接。")
    return data


def update_jsm_config(urls):
    """更新jsm.json配置文件中的URL"""
    global jsm_data
    if not jsm_data:
        log_message("[错误] jsm_data 为空，无法更新配置", step="配置更新")
        return False

    updated_jsm_data = replace_urls(deepcopy(jsm_data), urls)

    try:
        jsm_output_path = get_file_path('jsm.json', is_input=False)
        os.makedirs(os.path.dirname(jsm_output_path), exist_ok=True)
        with open(jsm_output_path, 'w', encoding='utf-8') as f:
            json.dump(updated_jsm_data, f, ensure_ascii=False, indent=4)

        log_message("[完成] jsm.json 配置文件更新成功", step="配置更新")
        return True
    except Exception as e:
        log_message(f"[错误] 更新 jsm.json 配置文件失败: {str(e)}", step="配置更新")
        return False


def process_urls():
    """核心处理流程"""
    log_message("[开始] 启动URL更新流程", step="主流程")

    # 加载现有配置
    existing_config = load_existing_config()
    reverse_site_mapping = {v: k for k, v in site_mappings.items()}

    # 数据源处理
    data_sources = []
    try:
        remote_data = requests.get(
            'https://github.catvod.com/https://raw.githubusercontent.com/celin1286/xiaosa/main/yuan.json',
            timeout=10
        ).json()
        data_sources.append(remote_data)
        log_message("[成功] 远程数据加载完成", step="数据收集")
    except Exception as e:
        log_message(f"[错误] 远程数据获取失败: {str(e)}", step="数据收集")

    local_path = get_file_path('yuan.json')
    if os.path.exists(local_path):
        try:
            with open(local_path, 'r', encoding='utf-8') as f:
                data_sources.append(json.load(f))
                log_message("[成功] 本地数据加载完成", step="数据收集")
        except Exception as e:
            log_message(f"[错误] 本地数据读取失败: {str(e)}", step="数据收集")

    data_sources.append(fallback_url_config)
    merged_data = merge_url_data(*data_sources)

    # 结果存储
    result = {'url': {}}
    stats = {'total': 0,'success': 0, 'failed': [], 'changed': []}

    for cn_name, urls in merged_data.items():
        stats['total'] += 1
        site_key = site_mappings.get(cn_name)
        existing_url = existing_config.get(site_key, '')

        if cn_name == '星剧社':
            best_source = get_best_url(urls, cn_name, existing_url)
            final_url = get_star2_real_url(best_source) if best_source else existing_url
        else:
            final_url = get_best_url(urls, cn_name, existing_url) or existing_url

        if final_url:
            result['url'][site_key] = final_url
            if existing_url and existing_url != final_url:
                stats['changed'].append(f"{cn_name}: {existing_url} → {final_url}")
                log_message(f"[更新] 配置变更检测", cn_name, "结果处理")
            stats['success'] += 1
        else:
            stats['failed'].append(cn_name)
            log_message("[警告] 无可用URL", cn_name, "结果处理")

    # 文件保存
    output_files = {
        'yuan.json': merged_data,
        'url.json': result['url']
    }

    for filename, data in output_files.items():
        try:
            path = get_file_path(filename, is_input=False)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            log_message(f"[成功] 保存文件: {path}", step="数据持久化")
        except Exception as e:
            log_message(f"[错误] 文件保存失败: {str(e)}", step="数据持久化")

    # 新增jsm更新流程
    log_message("[开始] 启动jsm配置更新", step="主流程")
    update_success = update_jsm_config(result['url'])
    log_message(
        f"[{'成功' if update_success else '失败'}] jsm配置更新完成",
        step="主流程"
    )

    # 统计报告
    log_message(
        f"[完成] 处理结果: {stats['success']}/{stats['total']} 成功\n"
        f"url.json变更项 ({len(stats['changed'])}):\n" + "\n".join(stats['changed']) + "\n"
        f"url.json失败项 ({len(stats['failed'])}): {', '.join(stats['failed']) if stats['failed'] else '无'}",
        step="统计报告"
    )
    return stats['success'] > 0


def main():
    warnings.simplefilter('ignore', InsecureRequestWarning)
    process_urls()


if __name__ == "__main__":
    start_time = time.time()
    main()
    elapsed = time.time() - start_time
    print(f"总耗时: {elapsed:.2f}秒")

