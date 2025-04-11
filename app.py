import re
import requests
import os
from collections import defaultdict
import time

# ================== 配置区域 ==================
# 需要删除的分组 (这些分组下的频道会被过滤)
DELETE_GROUPS = ["4K频道", "8K频道"]
PROVINCE_GROUPS = ["北京", "安徽", "甘肃", "广东", "贵州", "海南", "河北", "河南", "黑龙江", "湖北", "湖南",
                   "吉林", "江苏", "江西", "辽宁", "青海", "山东", "上海", "四川", "云南", "浙江", "重庆", "香港"]
GROUP_REPLACEMENTS = {"央视": "央视频道", "卫视": "卫视频道", "其他": "其他频道"}
DELETE_CHARS = ["iHOT-", "NewTV-", "SiTV-", "-HEVC", "-50-FPS", "-高码", "-4K", "-BPTV", "咪咕视频_8M1080_"]
GROUP_ORDER = ["收藏频道", "央视频道", "卫视频道", "其他频道", "地方频道"]

M3U_SOURCES = [
    {"name": "aktv", "url": "https://git.gra.phite.ro/alantang/tvbs/raw/branch/main/output/result.m3u", "ua": "okhttp/4.12.0"},
    {"name": "mytv", "url": "https://codeberg.org/sy147258/iptv/raw/branch/main/电视", "ua": "okhttp/4.12.0"},
    {"name": "自用收藏", "url": "http://aktv.space/live.m3u", "ua": "okhttp/4.12.0"},
    {"name": "big", "url": "https://git.gra.phite.ro/alantang/auto-iptv/raw/branch/main/live_ipv4.m3u", "ua": "okhttp/4.12.0"},
    {"name": "xhztv", "url": "http://xhztv.top/new.txt", "ua": "okhttp/4.12.0"},
    {"name": "top", "url": "http://tot.totalh.net/tttt.txt", "ua": "okhttp/4.12.0"},
    {"name": "zbds", "url": "https://live.zbds.top/tv/iptv6.txt", "ua": "okhttp/4.12.0"},
    {"name": "野火", "url": "https://gh.tryxd.cn/https://raw.githubusercontent.com/tianya7981/jiekou/main/野火959", "ua": "okhttp/4.12.0"},
    {"name": "jundie", "url": "http://home.jundie.top:81/Cat/tv/live.txt", "ua": "okhttp/4.12.0"},
    {"name": "MyIPTV", "url": "https://git.gra.phite.ro/alantang/auto-iptv/raw/branch/main/live_ipv6.m3u", "ua": "okhttp/4.12.0"}
]

# 最大响应时间（秒），超过此时间的频道将被视为异常
MAX_RESPONSE_TIME = 5

# ================== 核心功能 ==================
def robust_download(url, ua, max_retries=3):
    headers = {'User-Agent': ua}
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            return response.text
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            print(f"正在重试 {url} (第 {attempt + 1} 次)")


def process_channel(line):
    """频道信息处理流水线"""
    # 过滤不需要的分组
    if any(f'group-title="{g}"' in line for g in DELETE_GROUPS):
        return None

    # 分组名称替换
    for old, new in GROUP_REPLACEMENTS.items():
        line = line.replace(f'group-title="{old}"', f'group-title="{new}"')

    # 省份频道处理
    for province in PROVINCE_GROUPS:
        if f'group-title="{province}"' in line:
            new_group = '地方频道' if "卫视" not in line else '卫视频道'
            line = line.replace(f'group-title="{province}"', f'group-title="{new_group}"')

    # 特殊频道修正
    if "凤凰卫视" in line:
        line = line.replace('group-title="地方频道"', 'group-title="卫视频道"')

    # 清洗频道名称
    for char in DELETE_CHARS:
        line = line.replace(char, "")

    # 标准化CCTV写法
    line = re.sub(r'cctv-?', 'CCTV', line, flags=re.IGNORECASE)

    return line


def parse_m3u(content):
    channels = []
    current_channel = {}
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("#EXTINF"):
            current_channel = {"meta": line, "url": ""}
        elif line.startswith("http"):
            current_channel["url"] = line
            channels.append(current_channel)
            current_channel = {}
    return channels


def measure_response_time(url, ua):
    headers = {'User-Agent': ua}
    try:
        start_time = time.time()
        response = requests.head(url, headers=headers, timeout=MAX_RESPONSE_TIME)
        response.raise_for_status()
        return time.time() - start_time
    except Exception:
        return float('inf')


def sort_channels_by_response_time(channels):
    sorted_channels = []
    for channel in channels:
        url = channel["url"]
        ua = M3U_SOURCES[0]["ua"]  # 假设所有源使用相同的UA
        response_time = measure_response_time(url, ua)
        if response_time < MAX_RESPONSE_TIME:
            sorted_channels.append((response_time, channel))
    sorted_channels.sort(key=lambda x: x[0])
    return [channel for _, channel in sorted_channels]


def generate_m3u_output(channels):
    """生成M3U格式内容"""
    group_dict = defaultdict(list)
    for channel in channels:
        if match := re.search(r'group-title="([^"]+)"', channel["meta"]):
            group = match.group(1)
            group_dict[group].append(channel)

    ordered_groups = []
    for group in GROUP_ORDER:
        if group in group_dict:
            ordered_groups.append((group, group_dict.pop(group)))
    for group in sorted(group_dict.keys()):
        ordered_groups.append((group, group_dict[group]))

    output = ["#EXTM3U"]
    for group, items in ordered_groups:
        sorted_items = sort_channels_by_response_time(items)
        for item in sorted_items:
            output.append(item["meta"])
            output.append(item["url"])
    return "\n".join(output)


def generate_txt_output(channels):
    """生成TXT格式内容（分组名称,频道名称,URL）"""
    txt_lines = []
    for channel in channels:
        # 提取分组名称
        group_match = re.search(r'group-title="([^"]+)"', channel["meta"])
        group = group_match.group(1) if group_match else "未知分组"

        # 提取频道名称（最后一个逗号后的内容）
        channel_name = re.split(r',(?![^"]*\"\,)', channel["meta"])[-1].strip()

        # 清洗频道名称
        for char in DELETE_CHARS:
            channel_name = channel_name.replace(char, "")

        # 添加条目
        txt_lines.append(f"{group},{channel_name},{channel['url']}")

    return "\n".join(txt_lines)


def save_file(content, filename):
    """通用文件保存函数"""
    # 创建 live 文件夹，如果不存在
    live_folder = 'live'
    if not os.path.exists(live_folder):
        os.makedirs(live_folder)
    file_path = os.path.join(live_folder, filename)
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ 成功生成 {file_path} 文件")
        return True
    except PermissionError:
        print(f"❌ 无写入权限: {file_path}")
    except Exception as e:
        print(f"❌ 保存文件失败: {str(e)}")
    return False


def main():
    all_channels = []

    print("开始下载和处理数据源...")
    for source in M3U_SOURCES:
        try:
            content = robust_download(source["url"], source["ua"])
            channels = parse_m3u(content)

            processed = []
            for ch in channels:
                if cleaned_meta := process_channel(ch["meta"]):
                    processed.append({"meta": cleaned_meta, "url": ch["url"]})

            all_channels.extend(processed)
            print(f"[✓] {source['name']} 处理完成 ({len(processed)} 频道)")
        except Exception as e:
            print(f"[×] {source['name']} 失败: {str(e)}")

    print("\n生成最终文件...")
    # 生成M3U文件
    m3u_content = generate_m3u_output(all_channels)
    save_file(m3u_content, "live.m3u")

    # 生成TXT文件
    txt_content = generate_txt_output(all_channels)
    save_file(txt_content, "live.txt")

    print(f"\n处理完成！有效频道总数: {len(all_channels)}")


if __name__ == "__main__":
    main()    
