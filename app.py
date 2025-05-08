import re
import requests
import os
from collections import defaultdict

# ================== 配置区域 ==================
DELETE_GROUPS = ["4K频道", "8K频道"]
PROVINCE_GROUPS = ["北京", "安徽", "甘肃", "广东", "贵州", "海南", "河北", "河南", "黑龙江", "湖北", "湖南",
                   "吉林", "江苏", "江西", "辽宁", "青海", "山东", "上海", "四川", "云南", "浙江", "重庆", "香港"]
GROUP_REPLACEMENTS = {"央视": "央视频道", "卫视": "卫视频道", "其他": "其他频道"}
DELETE_CHARS = ["iHOT-", "NewTV-", "SiTV-", "-HEVC", "-50-FPS", "-高码", "-4K", "-BPTV", "咪咕视频_8M1080_"]
GROUP_ORDER = ["收藏频道", "央视频道", "卫视频道", "其他频道", "地方频道"]

M3U_SOURCES = [
    {"name": "dsy", "url": "http://xn--elt51t.azip.dpdns.org:5008/?type=txt", "ua": "okhttp/4.12.0"},
    {"name": "dsy", "url": "https://gitee.com/xxy002/zhiboyuan/raw/master/dsy", "ua": "okhttp/4.12.0"},
    {"name": "小云TV", "url": "https://cnb.cool/junchao.tang/llive/-/git/raw/main/小云TV直播", "ua": "okhttp/4.12.0"},
    {"name": "mytv", "url": "http://gg.7749.org/z/0/dzh.txt", "ua": "okhttp/4.12.0"},
    {"name": "自用收藏", "url": "http://aktv.space/live.m3u", "ua": "okhttp/4.12.0"},
    {"name": "big", "url": "http://api.mytv666.top/lives/free.php?type=txt", "ua": "okhttp/4.12.0"},
    {"name": "xhztv", "url": "https://gh.tryxd.cn/https://raw.githubusercontent.com/qingtingjjjjjjj/iptv-auto-update/main/my.txt", "ua": "okhttp/4.12.0"},
    {"name": "top", "url": "https://tv.iill.top/m3u/Gather", "ua": "okhttp/4.12.0"},
    {"name": "zbds", "url": "https://gh.tryxd.cn/https://raw.githubusercontent.com/pxiptv/live/main/iptv.m3u", "ua": "okhttp/4.12.0"},
    {"name": "Collect", "url": "https://gh.tryxd.cn/https://raw.githubusercontent.com/alantang1977/Collect-IPTV/refs/heads/main/mylive.m3u", "ua": "okhttp/4.12.0"},
    {"name": "jundie", "url": "https://codeberg.org/alfredisme/mytvsources/raw/branch/main/mylist-ipv6.m3u", "ua": "okhttp/4.12.0"},
    {"name": "MyIPTV", "url": "https://gh.tryxd.cn/https://raw.githubusercontent.com/alantang1977/iptv_api/refs/heads/main/live_ipv4.m3u", "ua": "okhttp/4.12.0"}
]

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
                print(f"❌ 无法下载: {url}. 错误: {str(e)}")
                return None
            print(f"正在重试 {url} (第 {attempt+1} 次)")

def process_channel(line):
    if any(f'group-title="{g}"' in line for g in DELETE_GROUPS):
        return None

    for old, new in GROUP_REPLACEMENTS.items():
        line = line.replace(f'group-title="{old}"', f'group-title="{new}"')

    for province in PROVINCE_GROUPS:
        if f'group-title="{province}"' in line:
            new_group = '地方频道' if "卫视" not in line else '卫视频道'
            line = line.replace(f'group-title="{province}"', f'group-title="{new_group}"')

    if "凤凰卫视" in line:
        line = line.replace('group-title="地方频道"', 'group-title="卫视频道"')

    for char in DELETE_CHARS:
        line = line.replace(char, "")
    
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

def generate_m3u_output(channels):
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
        for item in items:
            output.append(item["meta"])
            output.append(item["url"])
    return "\n".join(output)

def generate_txt_output(channels):
    output_lines = []
    for channel in channels:
        meta = channel["meta"]
        url = channel["url"]

        # 提取频道名称
        name_match = re.search(r'tvg-name="([^"]+)"', meta)
        channel_name = name_match.group(1) if name_match else "Unknown Channel"

        # 提取频道组
        group_match = re.search(r'group-title="([^"]+)"', meta)
        channel_group = group_match.group(1) if group_match else "Unknown Group"

        # 提取电视台ID
        tvg_id_match = re.search(r'tvg-id="([^"]+)"', meta)
        tvg_id = tvg_id_match.group(1) if tvg_id_match else "Unknown ID"

        output_lines.append(f"名称: {channel_name}, 组: {channel_group}, 电视台ID: {tvg_id}, URL: {url}")
    
    return "\n".join(output_lines)

def save_file(content, filename):
    live_folder = 'live'
    if not os.path.exists(live_folder):
        os.makedirs(live_folder)
    file_path = os.path.join(live_folder, filename)
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ 成功生成 {filename} 文件")
        return True
    except Exception as e:
        print(f"❌ 保存文件失败: {str(e)}")
    return False

def main():
    all_channels = []
    
    print("开始下载和处理数据源...")
    for source in M3U_SOURCES:
        content = robust_download(source["url"], source["ua"])
        if not content:
            print(f"[×] {source['name']} 无法处理，跳过")
            continue
        
        channels = parse_m3u(content)
        processed = []
        for ch in channels:
            # 修复: 检查 "meta" 键是否存在
            if "meta" in ch and (cleaned_meta := process_channel(ch["meta"])):
                processed.append({"meta": cleaned_meta, "url": ch["url"]})
        
        all_channels.extend(processed)
        print(f"[✓] {source['name']} 处理完成 ({len(processed)} 频道)")

    if not all_channels:
        print("❌ 没有可用的频道数据，终止生成文件")
        return

    print("\n生成最终文件...")
    m3u_content = generate_m3u_output(all_channels)
    save_file(m3u_content, "live.m3u")

    txt_content = generate_txt_output(all_channels)
    save_file(txt_content, "live.txt")
    
    print(f"\n处理完成！有效频道总数: {len(all_channels)}")

if __name__ == "__main__":
    main()
