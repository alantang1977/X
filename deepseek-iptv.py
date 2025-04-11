import requests
import pandas as pd
import re
import os
from collections import defaultdict

# 配置分类规则（可自由扩展）
CATEGORY_RULES = {
    "中央频道": ["CCTV", "中央", "CGTN", "央视"],
    "广东频道": ["广州", "广东", "GD", "珠江", "南方卫视", "大湾区"],
    "港澳台": ["香港", "澳门", "台湾", "翡翠", "明珠", "凤凰卫视", "澳视"],
    "卫视频道": ["卫视", "STV"],
    "体育": ["体育", "足球", "篮球", "奥运"],
    "少儿动漫": ["少儿", "卡通", "动漫", "动画"],
    "其他": []
}

# IPTV 源 URL 列表
urls = [
    #"http://rihou.cc:55/lib/kx2024.txt",
    "http://aktv.space/live.m3u",
    "https://fofa.info/result?qbase64=ImlwdHYvbGl2ZS96aF9jbi5qcyIgJiYgY291bnRyeT0iQ04iICYmIHJlZ2lvbj0iU2ljaHVhbiI%3D",  # 四川
    "https://fofa.info/result?qbase64=ImlwdHYvbGl2ZS96aF9jbi5qcyIgJiYgY291bnRyeT0iQ04iICYmIHJlZ2lvbj0i5LqR5Y2XIg%3D%3D",  # 云南
    "https://fofa.info/result?qbase64=ImlwdHYvbGl2ZS96aF9jbi5qcyIgJiYgY291bnRyeT0iQ04iICYmIHJlZ2lvbj0iQ2hvbmdxaW5nIg%3D%3D",  # 重庆
    "https://fofa.info/result?qbase64=ImlwdHYvbGl2ZS96aF9jbi5qcyIgJiYgY291bnRyeT0iQ04iICYmIHJlZ2lvbj0iR3VpemhvdSI%3D",  # 贵州
    "https://fofa.info/result?qbase64=ImlwdHYvbGl2ZS96aF9jbi5qcyIgJiYgY291bnRyeT0iQ04iICYmIHJlZ2lvbj0iU2hhbnhpIg%3D%3D",  # 山西
    #"https://fofa.info/result?qbase64=ImlwdHYvbGl2ZS96aF9jbi5qcyIgJiYgY291bnRyeT0iQ04iICYmIHJlZ2lvbj0i5bm%2F5LicIg%3D%3D",  # 广东
    "https://gh.tryxd.cn/https://raw.githubusercontent.com/tianya7981/jiekou/refs/heads/main/野火959",   
    "https://codeberg.org/lxxcp/live/raw/branch/main/gsdx.txt",  
    "https://live.zbds.top/tv/iptv6.txt",
    "https://live.zbds.top/tv/iptv4.txt",
]

def classify_program(program_name):
    """根据节目名称分类"""
    program_lower = program_name.lower()
    for category, keywords in CATEGORY_RULES.items():
        if any(re.search(re.escape(kw.lower()), program_lower) for kw in keywords if kw):
            return category
    return "其他"

def fetch_streams_from_url(url):
    """从指定 URL 获取 IPTV 流数据"""
    print(f"正在爬取网站源: {url}")
    try:
        response = requests.get(url, timeout=20)
        response.encoding = 'utf-8'
        if response.status_code == 200:
            return response.text
        else:
            print(f"请求失败: {response.status_code}")
    except Exception as e:
        print(f"请求异常: {str(e)[:50]}")
    return None

def fetch_all_streams():
    """获取所有 IPTV 流数据"""
    return "\n".join(filter(None, (fetch_streams_from_url(url) for url in URLS)))

def parse_m3u(content):
    """解析 M3U 格式内容"""
    streams = []
    current_program = None
    for line in content.splitlines():
        if line.startswith("#EXTINF"):
            match = re.search(r'tvg-name="([^"]+)"', line)
            current_program = match.group(1).strip() if match else None
        elif line.startswith("http") and current_program:
            streams.append({
                "program_name": current_program,
                "stream_url": line.strip(),
                "category": classify_program(current_program)
            })
            current_program = None
    return streams

def parse_txt(content):
    """解析 TXT 格式内容"""
    streams = []
    for line in content.splitlines():
        match = re.match(r"(.+?),\s*(http.+)", line)
        if match:
            program = match.group(1).strip()
            streams.append({
                "program_name": program,
                "stream_url": match.group(2).strip(),
                "category": classify_program(program)
            })
    return streams

def organize_streams(content):
    """组织 IPTV 流数据为 DataFrame 格式"""
    parser = parse_m3u if content.startswith("#EXTM3U") else parse_txt
    streams = parser(content)
    if not streams:
        print("未能解析任何流数据")
        return pd.DataFrame(columns=["program_name", "stream_url", "category"])
    df = pd.DataFrame(streams)
    return df.drop_duplicates(subset=['program_name', 'stream_url'])

def save_to_txt(df, filename="mytv.txt"):
    """保存流数据为 TXT 文件"""
    categorized = defaultdict(list)
    for _, row in df.iterrows():
        entry = f"{row['program_name']},{row['stream_url']}"
        categorized[row['category']].append(entry)
    
    with open(filename, 'w', encoding='utf-8') as f:
        for category in [*CATEGORY_RULES.keys(), "其他"]:
            if entries := categorized.get(category):
                f.write(f"\n# {category} ({len(entries)}个频道)\n")
                f.write("\n".join(sorted(entries)))
                f.write("\n")
    
    print(f"分类文本已保存: {os.path.abspath(filename)}")

def save_to_m3u(df, filename="mytv.m3u"):
    """保存流数据为 M3U 文件"""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        for category in CATEGORY_RULES:
            category_df = df[df['category'] == category]
            if not category_df.empty:
                f.write(f"\n# 分类: {category} ({len(category_df)}个频道)\n")
                for _, row in category_df.iterrows():
                    f.write(f'#EXTINF:-1 tvg-name="{row["program_name"]}",{row["program_name"]}\n{row["stream_url"]}\n')
    
    print(f"分类M3U已保存: {os.path.abspath(filename)}")

def print_statistics(df):
    """打印分类统计信息"""
    print("\n频道分类统计:")
    stats = df['category'].value_counts().to_dict()
    for cat, count in stats.items():
        print(f"{cat.ljust(8)}: {count}个频道")
    print(f"总频道数: {len(df)}")

if __name__ == "__main__":
    print("开始抓取IPTV源...")
    content = fetch_all_streams()
    if content:
        df = organize_streams(content)
        print_statistics(df)
        save_to_txt(df)
        save_to_m3u(df)
    else:
        print("未能获取有效数据")
