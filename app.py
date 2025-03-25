import re
import requests
import os

# ========== 配置区域 ==========

# 定义需要删除的 group-title 属性值
# 这些分组下的频道将不会出现在最终的 m3u 文件中
delete_groups = ["4K频道", "8K频道"]

# 定义需要替换为 "地方频道" 的省份
# 当频道的 group-title 为这些省份时，会根据频道名称是否包含 "卫视" 进行不同处理
# 若不包含 "卫视"，则将 group-title 替换为 "地方频道"；若包含 "卫视"，则替换为 "卫视频道"
province_groups = ["北京", "安徽", "甘肃", "广东", "贵州", "海南", "河北", "河南", "黑龙江", "湖北", "湖南",
                   "吉林", "江苏", "江西", "辽宁", "青海", "山东", "上海", "四川", "云南", "浙江", "重庆", "香港"]

# 定义需要替换的 group-title 属性值
# 这里指定了一些旧的 group-title 名称和对应的新名称，程序会将旧名称替换为新名称
replace_groups = {
    "央视": "央视频道",
    "卫视": "卫视频道",
    "其他": "其他频道"
}

# 定义需要删除的频道名称中的字符
# 这些字符会从频道名称中被移除，以达到清洗频道名称的目的
delete_chars = ["iHOT-", "NewTV-", "SiTV-", "-HEVC", "-50-FPS", "-高码", "-4K", "-BPTV", "咪咕视频_8M1080_"]

# 定义最终 group 排序顺序
# 最终生成的 m3u 文件中，频道分组会按照这个顺序进行排列
# 未在这个列表中的分组会排在最后，并按分组名称排序
sort_order = ["收藏频道", "央视频道", "卫视频道", "其他频道", "地方频道"]

# 需要下载的 m3u 链接及对应 UA 和名称
# 每个字典代表一个 m3u 文件的下载信息
# "name" 是该 m3u 文件的名称，用于日志输出
# "url" 是 m3u 文件的下载地址
# "ua" 是请求时使用的 User-Agent
m3u_list = [
    {"name": "aktv", "url": "https://gh.tryxd.cn/https://raw.githubusercontent.com/alantang1977/JunTV/refs/heads/main/output/result.m3u", "ua": "okhttp/4.12.0"},
    {"name": "自用收藏", "url": "http://aktv.space/live.m3u", "ua": "okhttp/4.12.0"},
    {"name": "big", "url": "https://gh.tryxd.cn/https://raw.githubusercontent.com/big-mouth-cn/tv/main/iptv-ok.m3u", "ua": "okhttp/4.12.0"},
    {"name": "xhztv", "url": "http://xhztv.top/new.txt", "ua": "okhttp/4.12.0"},
    {"name": "top", "url": "http://tot.totalh.net/tttt.txt", "ua": "okhttp/4.12.0"},
    {"name": "zbds", "url": "https://live.zbds.top/tv/iptv6.txt", "ua": "okhttp/4.12.0"},
    {"name": "野火", "url": "https://gh.tryxd.cn/https://raw.githubusercontent.com/tianya7981/jiekou/refs/heads/main/野火959", "ua": "okhttp/4.12.0"},
    {"name": "jundie", "url": "http://home.jundie.top:81/Cat/tv/live.txt", "ua": "okhttp/4.12.0"},
    {"name": "MyIPTV", "url": "https://gh.tryxd.cn/https://raw.githubusercontent.com/SPX372928/MyIPTV/master/黑龙江PLTV移动CDN版.txt", "ua": "okhttp/4.12.0"},
    {"name": "mylist", "url": "https://gh.tryxd.cn/https://raw.githubusercontent.com/yuanzl77/IPTV/main/live.m3u", "ua": "okhttp/4.12.0"},  
    {"name": "Kimentanm", "url": "https://gh.tryxd.cn/https://raw.githubusercontent.com/Kimentanm/aptv/master/m3u/iptv.m3u", "ua": "okhttp/4.12.0"},
    {"name": "Chinese", "url": "https://gh.tryxd.cn/https://raw.githubusercontent.com/BurningC4/Chinese-IPTV/master/TV-IPV4.m3u", "ua": "okhttp/4.12.0"},
    {"name": "kimwang1978", "url": "https://gh.tryxd.cn/https://raw.githubusercontent.com/kimwang1978/collect-tv-txt/main/merged_output_simple.txt", "ua": "okhttp/4.12.0"},
    {"name": "电视", "url": "https://codeberg.org/sy147258/iptv/raw/branch/main/电视", "ua": "okhttp/4.12.0"},
    {"name": "Gather", "url": "https://gh.tryxd.cn/https://raw.githubusercontent.com/Guovin/iptv-api/gd/output/result.txt", "ua": "okhttp/4.12.0"},
    # 可以继续增加
]

# ========== 功能函数 ==========

def download_m3u(url, ua):
    """下载 m3u 文件，支持自定义 User-Agent"""
    headers = {'User-Agent': ua}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    response.encoding = 'utf-8'
    return response.text

def remove_extm3u_lines(lines):
    """删除带有 #EXTM3U 的行"""
    return [line for line in lines if not line.startswith("#EXTM3U")]

def process_m3u(content):
    """预处理 m3u 内容：清洗、替换、标准化"""
    # 先删除 #EXTM3U 行
    lines = remove_extm3u_lines(content.splitlines())
    processed = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("#EXTINF"):
            url_line = lines[i + 1]
            # 删除不需要的 group
            if any(group in line for group in delete_groups):
                i += 2
                continue
            # 替换 group-title
            for old, new in replace_groups.items():
                line = line.replace(f'group-title="{old}"', f'group-title="{new}"')
            # 省份处理
            for province in province_groups:
                if f'group-title="{province}"' in line:
                    line = line.replace(f'group-title="{province}"', 'group-title="地方频道"') if "卫视" not in line else line.replace(f'group-title="{province}"', 'group-title="卫视频道"')
            # 特殊频道修正
            if "凤凰卫视" in line:
                line = line.replace('group-title="地方频道"', 'group-title="卫视频道"')
            if "SiTV-" in line:
                line = line.replace('group-title="地方频道"', 'group-title="SiTV"')
            # 删除无用字符
            for char in delete_chars:
                line = line.replace(char, "")
            # CCTV 标准化
            line = re.sub(r'cctv-?', 'CCTV', line, flags=re.IGNORECASE)
            # 替换 i.880824.xyz 为 192.168.31.2
            url_line = url_line.replace("i.880824.xyz", "192.168.31.2")
            # 添加处理后频道
            processed.append(line)
            processed.append(url_line)
            i += 2
        else:
            processed.append(line)
            i += 1
    return processed

def merge_m3u(all_m3u_lists):
    """合并所有 m3u 列表，并删除空行"""
    merged = []
    for m3u_list in all_m3u_lists:
        merged.extend(m3u_list)
    # 删除空行
    merged = [line for line in merged if line.strip()]
    return merged

def sort_m3u(lines):
    """按 group-title 排序，未包含的组排最后"""
    sorted_result = []
    remaining_lines = lines[:]
    remaining_groups = {}

    for group in sort_order:
        i = 0
        while i < len(remaining_lines):
            if remaining_lines[i].startswith("#EXTINF") and f'group-title="{group}"' in remaining_lines[i]:
                sorted_result.append(remaining_lines[i])
                sorted_result.append(remaining_lines[i + 1])
                del remaining_lines[i:i + 2]
            else:
                i += 1

    # 处理未在 sort_order 中的分组
    i = 0
    while i < len(remaining_lines):
        if remaining_lines[i].startswith("#EXTINF"):
            group_match = re.search(r'group-title="([^"]+)"', remaining_lines[i])
            if group_match:
                group = group_match.group(1)
                if group not in remaining_groups:
                    remaining_groups[group] = []
                remaining_groups[group].extend([remaining_lines[i], remaining_lines[i + 1]])
            i += 2
        else:
            i += 1

    # 按分组名称排序未在 sort_order 中的分组
    for group in sorted(remaining_groups.keys()):
        sorted_result.extend(remaining_groups[group])

    return sorted_result

def sort_channels_in_groups(lines):
    """将每个分组中相同的频道名称放在一起，分组内按默认顺序排序"""
    grouped_channels = {}
    i = 0
    while i < len(lines):
        if lines[i].startswith("#EXTINF"):
            group_match = re.search(r'group-title="([^"]+)"', lines[i])
            if group_match:
                group = group_match.group(1)
                channel_name = re.search(r',([^,]+)$', lines[i]).group(1)
                if group not in grouped_channels:
                    grouped_channels[group] = {}
                if channel_name not in grouped_channels[group]:
                    grouped_channels[group][channel_name] = []
                grouped_channels[group][channel_name].extend([lines[i], lines[i + 1]])
            i += 2
        else:
            i += 1

    sorted_lines = []
    for group in sort_order:
        if group in grouped_channels:
            for channel_name in grouped_channels[group]:
                sorted_lines.extend(grouped_channels[group][channel_name])

    # 处理未在 sort_order 中的分组
    remaining_groups = [group for group in grouped_channels if group not in sort_order]
    for group in sorted(remaining_groups):
        for channel_name in grouped_channels[group]:
            sorted_lines.extend(grouped_channels[group][channel_name])

    return sorted_lines

def save_m3u(lines, filename):
    """保存 m3u 文件"""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))

def save_txt(lines, filename):
    """保存为 live.txt 格式（格式：分组名称,频道名称,URL）"""
    with open(filename, 'w', encoding='utf-8') as f:
        i = 0
        while i < len(lines):
            if lines[i].startswith("#EXTINF"):
                # 提取分组名称
                group_match = re.search(r'group-title="([^"]+)"', lines[i])
                group = group_match.group(1) if group_match else ""
                
                # 提取频道名称（最后一个逗号后的内容）
                channel_name = lines[i].split(',')[-1].strip()
                
                # 获取URL（确保索引不越界）
                if i+1 < len(lines):
                    url = lines[i+1].strip()
                    f.write(f"{group},{channel_name},{url}\n")
                i += 2
            else:
                i += 1

# ========== 主流程 ==========

def main():
    all_processed_m3u = []

    # 下载并处理所有 m3u 文件
    for idx, item in enumerate(m3u_list, start=1):
        name = item["name"]
        url = item["url"]
        ua = item["ua"]
        print(f"正在处理: {name} ({url}) (UA: {ua})")

        try:
            raw_content = download_m3u(url, ua)
            processed = process_m3u(raw_content)
            all_processed_m3u.append(processed)
            print(f"成功处理第 {idx} 个 m3u，频道数：{len(processed)//2}")
        except Exception as e:
            print(f"⚠️ 下载或处理失败：{url}, 错误：{e}")

    # 合并所有列表
    merged_m3u = merge_m3u(all_processed_m3u)
    print(f"共合并频道数：{len(merged_m3u)//2}")

    # 全局排序
    sorted_m3u = sort_m3u(merged_m3u)

    # 对每个分组内的频道进行排序
    sorted_channels = sort_channels_in_groups(sorted_m3u)

    # 保存最终文件
    output_file = "live.m3u"
    save_m3u(sorted_channels, output_file)
    print(f"✅ 最终合并排序文件已保存为 {output_file}")

    # 新增：保存为live.txt格式
    save_txt(sorted_channels, "live.txt")
    print(f"✅ 新增TXT格式文件已保存为 live.txt")

if __name__ == "__main__":
    main()
