import subprocess
import threading
import time

def parse_live_txt(txt_file):
    channels = []
    with open(txt_file, encoding="utf-8") as f:
        current_group = None
        for line in f:
            line = line.strip()
            if line.endswith(",#genre#"):
                current_group = line.split(",")[0]
            elif line and "," in line and current_group:
                channel_name, url, *_ = line.split(",", 2)
                if url.startswith("http"):
                    channels.append((current_group, channel_name, url))
    return channels

def push_stream_ffmpeg(src_url, out_url):
    # 死循环守护推流
    while True:
        print(f"推流: {src_url} -> {out_url}")
        p = subprocess.Popen([
            'ffmpeg', '-re', '-i', src_url, '-c', 'copy', '-f', 'flv', out_url
        ])
        p.wait()
        print("推流中断，10秒后重启...")
        time.sleep(10)

def main():
    # 1. 解析已生成的 live_ipv4.txt
    channels = parse_live_txt("live/live_ipv4.txt")
    # 2. 只推前5个频道做演示
    for group, name, src_url in channels[:5]:
        # 3. 生成推流目标地址
        stream_key = name.replace(" ", "").replace(",", "").replace("/", "")
        out_url = f"rtmp://localhost/live/{stream_key}"
        # 4. 多线程推流（实际生产建议 supervisor/docker 守护）
        t = threading.Thread(target=push_stream_ffmpeg, args=(src_url, out_url))
        t.daemon = True
        t.start()
        time.sleep(2)  # 防止瞬时拉爆本地带宽
    # 保持主线程
    while True:
        time.sleep(3600)

if __name__ == "__main__":
    main()