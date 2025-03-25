import re
import requests
import os
from collections import defaultdict

# ================== 配置区域 ==================
# 需要删除的分组 (这些分组下的频道会被过滤)
DELETE_GROUPS = ["4K频道", "8K频道"]

# 需要转换为地方频道的省份
PROVINCE_GROUPS = ["北京", "安徽", "甘肃", "广东", "贵州", "海南", "河北", "河南", "黑龙江", "湖北", "湖南",
                   "吉林", "江苏", "江西", "辽宁", "青海", "山东", "上海", "四川", "云南", "浙江", "重庆", "香港"]

# 分组名称替换规则
GROUP_REPLACEMENTS = {
    "央视": "央视频道",
    "卫视": "卫视频道",
    "其他": "其他频道"
}

# 需要删除的频道名称冗余字符
DELETE_CHARS = ["iHOT-", "NewTV-", "SiTV-", "-HEVC", "-50-FPS", "-高码", "-4K", "-BPTV", "咪咕视频_8M1080_"]

# 最终分组排序规则
GROUP_ORDER = ["收藏频道", "央视频道", "卫视频道", "其他频道", "地方频道"]

# 数据源配置 (包含重试机制)
M3U_SOURCES = [
    {"name": "aktv", "url": "https://gh.tryxd.cn/https://raw.githubusercontent.com/alantang1977/JunTV/main/output/result.m3u", "ua": "okhttp/4.12.0"},
    {"name": "自用收藏", "url": "http://aktv.space/live.m3u", "ua": "okhttp/4.12.0"},
    {"name": "big", "url": "https://gh.tryxd.cn/https://raw.githubusercontent.com/big-mouth-cn/tv/main/iptv-ok.m3u", "ua": "okhttp/4.12.0"},
    {"name": "xhztv", "url": "http://xhztv.top/new.txt", "ua": "okhttp/4.12.0"},
    {"name": "top", "url": "http://tot.totalh.net/tttt.txt", "ua": "okhttp/4.12.0"},
    {"name": "zbds", "url": "https://live.zbds.top/tv/iptv6.txt", "ua": "okhttp/4.12.0"},
    {"name": "野火", "url": "https://gh.tryxd.cn/https://raw.githubusercontent.com/tianya7981/jiekou/main/野火959", "ua": "okhttp/4.12.0"},
    {"name": "jundie", "url": "http://home.jundie.top:81/Cat/tv/live.txt", "ua": "okhttp/4.12.0"},
    {"name": "MyIPTV", "url": "https://gh.tryxd.cn/https://raw.githubusercontent.com/SPX372928/MyIPTV/master/黑龙江PLTV移动CDN版.txt", "ua": "okhttp/4.12.0"}
]

# ================== 核心功能 ==================
def robust_download(url, ua, max_retries=3):
    """带重试机制的下载函数"""
    headers = {'User-Agent': ua}
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            response.encoding = response.apparent_encoding  # 自动检测编码
            return response.text
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            print(f"正在重试 {url} (第 {attempt+1} 次)")

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
    """解析M3U内容并结构化存储"""
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

def generate_output(channels):
    """生成排序后的最终内容"""
    # 按分组归类
    group_dict = defaultdict(list)
    for channel in channels:
        if match := re.search(r'group-title="([^"]+)"', channel["meta"]):
            group = match.group(1)
            group_dict[group].append(channel)

    # 按自定义顺序排序
    ordered_groups = []
    for group in GROUP_ORDER:
        if group in group_dict:
            ordered_groups.append((group, group_dict.pop(group)))
    
    # 添加剩余分组并按字母排序
    for group in sorted(group_dict.keys()):
        ordered_groups.append((group, group_dict[group]))

    # 生成最终文本
    output = ["#EXTM3U"]
    for group, items in ordered_groups:
        for item in items:
            output.append(item["meta"])
            output.append(item["url"])
    return "\n".join(output)

def main():
    """主工作流程"""
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
            print(f"[✓] 成功处理 {source['name']} ({len(processed)} 个频道)")
        except Exception as e:
            print(f"[×] 处理 {source['name']} 失败: {str(e)}")
    
    print("生成最终文件...")
    final_content = generate_output(all_channels)
    
    try:
        with open("live.txt", "w", encoding="utf-8") as f:
            f.write(final_content)
        print("生成 live.txt 成功！")
    except Exception as e:
        print(f"生成 live.txt 失败: {str(e)}")
    
    try:
        with open("live.m3u", "w", encoding="utf-8") as f:
            f.write(final_content)
        print("生成 live.m3u 成功！")
    except Exception as e:
        print(f"生成 live.m3u 失败: {str(e)}")
    
    print(f"共处理 {len(all_channels)} 个频道，文件大小: {len(final_content)//1024}KB")

if __name__ == "__main__":
    main()
