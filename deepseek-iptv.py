import requests
import pandas as pd
import re
import os
from collections import defaultdict

# 配置分类规则（可自由扩展）
CATEGORY_RULES = {
    "中央频道": ["CCTV", "中央", "CGTN", "央视"],
    "广东频道": ["广州","广东", "GD", "珠江", "南方卫视", "大湾区"],
    "港澳台": ["香港", "澳门", "台湾", "翡翠", "明珠", "凤凰卫视", "澳视"],
    "卫视频道": ["卫视", "STV"],
    "体育": ["体育", "足球", "篮球", "奥运"],
    "少儿动漫": ["少儿", "卡通", "动漫", "动画"],
    "其他": []
}

urls = [
    "https://gh.tryxd.cn/https://raw.githubusercontent.com/alantang1977/JunTV/refs/heads/main/output/result.m3u",
    "https://gh.tryxd.cn/https://raw.githubusercontent.com/zwc456baby/iptv_alive/master/live.txt",
    "http://rihou.cc:55/lib/kx2024.txt",
    "http://aktv.space/live.m3u",
    "https://gh.tryxd.cn/https://raw.githubusercontent.com/tianya7981/jiekou/refs/heads/main/野火959",
    "https://codeberg.org/alfredisme/mytvsources/raw/branch/main/mylist-ipv6.m3u",
    "https://codeberg.org/lxxcp/live/raw/branch/main/gsdx.txt",  
    "https://live.zbds.top/tv/iptv6.txt",
    "https://live.zbds.top/tv/iptv4.txt",
]

ipv4_pattern = re.compile(r'^http://(\d{1,3}\.){3}\d{1,3}')
ipv6_pattern = re.compile(r'^http://\[([a-fA-F0-9:]+)\]')

def classify_program(program_name):
    """智能分类频道"""
    program_lower = program_name.lower()
    for category, keywords in CATEGORY_RULES.items():
        if any(re.search(re.escape(kw.lower()), program_lower) for kw in keywords if kw):
            return category
    return "其他"

def fetch_streams_from_url(url):
    print(f"正在爬取网站源: {url}")
    try:
        response = requests.get(url, timeout=20)
        response.encoding = 'utf-8'
        return response.text if response.status_code == 200 else None
    except Exception as e:
        print(f"请求异常: {str(e)[:50]}")
        return None

def fetch_all_streams():
    return "\n".join(filter(None, (fetch_streams_from_url(url) for url in urls)))

def parse_m3u(content):
    streams = []
    current_program = None
    for line in content.splitlines():
        if line.startswith("#EXTINF"):
            match = re.search(r'tvg-name="([^"]+)"', line)
            if match:
                current_program = match.group(1).strip()
            else:
                current_program = None
        elif line.startswith("http") and current_program:
            streams.append({
                "program_name": current_program,
                "stream_url": line.strip(),
                "category": classify_program(current_program)
            })
            current_program = None
    return streams

def parse_txt(content):
    streams = []
    for line in content.splitlines():
        if match := re.match(r"(.+?),\s*(http.+)", line):
            program = match.group(1).strip()
            streams.append({
                "program_name": program,
                "stream_url": match.group(2).strip(),
                "category": classify_program(program)
            })
    return streams

def organize_streams(content):
    parser = parse_m3u if content.startswith("#EXTM3U") else parse_txt
    df = pd.DataFrame(parser(content))
    return df.drop_duplicates(subset=['program_name', 'stream_url'])

def save_to_txt(df, filename="mytv.txt"):
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
    print("\n频道分类统计:")
    stats = df['category'].value_counts().to_dict()
    for cat, count in stats.items():
        print(f"{cat.ljust(8)}: {count}个频道")
    print(f"总频道数: {len(df)}")

if __name__ == "__main__":
    print("开始抓取IPTV源...")
    if content := fetch_all_streams():
        df = organize_streams(content)
        print_statistics(df)
        save_to_txt(df)
        save_to_m3u(df)
    else:
        print("未能获取有效数据")
