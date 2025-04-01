import requests
import pandas as pd
import re
import os

urls = [
    "https://git.gra.phite.ro/alantang/tvbs/raw/branch/main/output/result.m3u",
    "https://gh.tryxd.cn/https://raw.githubusercontent.com/zwc456baby/iptv_alive/master/live.txt",
    "http://rihou.cc:55/lib/kx2024.txt",
    "http://aktv.space/live.m3u",
    "https://fofa.info/result?qbase64=ImlwdHYvbGl2ZS96aF9jbi5qcyIgJiYgY291bnRyeT0iQ04iICYmIHJlZ2lvbj0iU2ljaHVhbiI%3D",  # 四川
    "https://fofa.info/result?qbase64=ImlwdHYvbGl2ZS96aF9jbi5qcyIgJiYgY291bnRyeT0iQ04iICYmIHJlZ2lvbj0i5LqR5Y2XIg%3D%3D",  # 云南
    "https://fofa.info/result?qbase64=ImlwdHYvbGl2ZS96aF9jbi5qcyIgJiYgY291bnRyeT0iQ04iICYmIHJlZ2lvbj0iQ2hvbmdxaW5nIg%3D%3D",  # 重庆
    "https://fofa.info/result?qbase64=ImlwdHYvbGl2ZS96aF9jbi5qcyIgJiYgY291bnRyeT0iQ04iICYmIHJlZ2lvbj0iR3VpemhvdSI%3D",  # 贵州
    "https://fofa.info/result?qbase64=ImlwdHYvbGl2ZS96aF9jbi5qcyIgJiYgY291bnRyeT0iQ04iICYmIHJlZ2lvbj0iU2hhbnhpIg%3D%3D",  # 山西
    "https://fofa.info/result?qbase64=ImlwdHYvbGl2ZS96aF9jbi5qcyIgJiYgY291bnRyeT0iQ04iICYmIHJlZ2lvbj0i5bm%2F5LicIg%3D%3D",  # 广东
    "https://gh.tryxd.cn/https://raw.githubusercontent.com/tianya7981/jiekou/refs/heads/main/野火959",
    "https://codeberg.org/alfredisme/mytvsources/raw/branch/main/mylist-ipv6.m3u",
    "https://codeberg.org/lxxcp/live/raw/branch/main/gsdx.txt",  
    "https://live.zbds.top/tv/iptv6.txt",
    "https://live.zbds.top/tv/iptv4.txt",
]

ipv4_pattern = re.compile(r'^http://(\d{1,3}\.){3}\d{1,3}')
ipv6_pattern = re.compile(r'^http://\[([a-fA-F0-9:]+)\]')

def fetch_streams_from_url(url):
    print(f"正在爬取网站源: {url}")
    try:
        response = requests.get(url, timeout=20)
        response.encoding = 'utf-8'
        if response.status_code == 200:
            return response.text
        print(f"从 {url} 获取数据失败，状态码: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"请求 {url} 时发生错误: {e}")
    return None

def fetch_all_streams():
    all_streams = []
    for url in urls:
        if content := fetch_streams_from_url(url):
            all_streams.append(content)
        else:
            print(f"跳过来源: {url}")
    return "\n".join(all_streams)

def parse_m3u(content):
    streams = []
    current_program = None
    
    for line in content.splitlines():
        if line.startswith("#EXTINF"):
            if match := re.search(r'tvg-name="([^"]+)"', line):
                current_program = match.group(1).strip()
        elif line.startswith("http"):
            if current_program:
                streams.append({"program_name": current_program, "stream_url": line.strip()})
                current_program = None
    return streams

def parse_txt(content):
    streams = []
    for line in content.splitlines():
        if match := re.match(r"(.+?),\s*(http.+)", line):
            streams.append({
                "program_name": match.group(1).strip(),
                "stream_url": match.group(2).strip()
            })
    return streams

def organize_streams(content):
    parser = parse_m3u if content.startswith("#EXTM3U") else parse_txt
    df = pd.DataFrame(parser(content))
    df = df.drop_duplicates(subset=['program_name', 'stream_url'])
    return df.groupby('program_name')['stream_url'].apply(list).reset_index()

def save_to_txt(grouped_streams, filename="iptv.txt"):
    ipv4 = []
    ipv6 = []
    
    for _, row in grouped_streams.iterrows():
        program = row['program_name']
        for url in row['stream_url']:
            if ipv4_pattern.match(url):
                ipv4.append(f"{program},{url}")
            elif ipv6_pattern.match(url):
                ipv6.append(f"{program},{url}")

    with open(filename, 'w', encoding='utf-8') as f:
        f.write("# IPv4 Streams\n" + "\n".join(ipv4))
        f.write("\n\n# IPv6 Streams\n" + "\n".join(ipv6))
    print(f"文本文件已保存: {os.path.abspath(filename)}")

def save_to_m3u(grouped_streams, filename="iptv.m3u"):
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        for _, row in grouped_streams.iterrows():
            program = row['program_name']
            for url in row['stream_url']:
                f.write(f'#EXTINF:-1 tvg-name="{program}",{program}\n{url}\n')
    print(f"M3U文件已保存: {os.path.abspath(filename)}")

if __name__ == "__main__":
    print("开始抓取所有源...")
    if content := fetch_all_streams():
        print("整理源数据中...")
        organized = organize_streams(content)
        save_to_txt(organized)
        save_to_m3u(organized)
    else:
        print("未能获取有效数据")
