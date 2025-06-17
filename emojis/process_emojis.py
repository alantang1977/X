#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文件: emojis/process_emojis.py

功能：
1. 从 Unicode 官网下载 emoji-test.txt（若本地不存在）。
2. 解析出“fully-qualified”状态的所有 Emoji，组成完整列表。
3. 遍历指定目录下的 .json/.txt/.md/.csv/.xml/.html 文件。
4. 提取文件中的所有 Emoji，并用循环池中新的 Emoji 依次替换。
5. 输出同名 JSON（保持原 JSON 结构或封装为 {'content': text}）到 output 文件夹。
6. 仅替换已有 Emoji，不增删其他文本或符号。
"""

import os
import re
import sys
import json
import shutil
import argparse
from pathlib import Path
from itertools import cycle
from urllib.request import urlopen

# —— 配置 —— #
UNICODE_EMOJI_URL = "https://unicode.org/Public/emoji/15.1/emoji-test.txt"
LOCAL_EMOJI_FILE = Path(__file__).parent / "emoji-test.txt"
SUPPORTED_EXTENSIONS = {".json", ".txt", ".md", ".csv", ".xml", ".html"}

# —— 下载 & 解析 Emoji —— #
def download_emoji_file():
    if not LOCAL_EMOJI_FILE.exists():
        print(f"Downloading emoji list to {LOCAL_EMOJI_FILE} ...")
        LOCAL_EMOJI_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = urlopen(UNICODE_EMOJI_URL).read().decode("utf-8")
        LOCAL_EMOJI_FILE.write_text(data, encoding="utf-8")
        print("Download complete.")

def parse_emoji_file():
    emojis = []
    for line in LOCAL_EMOJI_FILE.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split(";")
        status = parts[1].strip()
        if status == "fully-qualified":
            # parts[0] 是形如 "1F600" 或 "1F1E8 1F1F3" 的十六进制串
            codepoints = parts[0].strip().split()
            emoji = "".join(chr(int(cp, 16)) for cp in codepoints)
            emojis.append(emoji)
    return emojis

def get_emoji_pool():
    download_emoji_file()
    pool = parse_emoji_file()
    print(f"Loaded {len(pool)} emojis.")
    return pool

# —— 正则匹配已存在的 Emoji —— #
EMOJI_PATTERN = re.compile(
    "["   
    "\U0001F600-\U0001F64F"  # Emoticons
    "\U0001F300-\U0001F5FF"  # Symbols & Pictographs
    "\U0001F680-\U0001F6FF"  # Transport & Map
    "\U0001F1E0-\U0001F1FF"  # Flags
    "\U00002702-\U000027B0"  # Dingbats
    "\U000024C2-\U0001F251"  # Enclosed characters
    "]+", flags=re.UNICODE
)

def replace_emojis_in_text(text: str, emoji_cycle) -> str:
    return EMOJI_PATTERN.sub(lambda m: next(emoji_cycle), text)

# —— 处理单个文件 —— #
def process_file(src: Path, dst_dir: Path, emoji_cycle):
    content = src.read_text(encoding="utf-8")
    new_content = replace_emojis_in_text(content, emoji_cycle)

    # 准备输出目录
    dst_dir.mkdir(parents=True, exist_ok=True)
    out_file = dst_dir / (src.stem + ".json")

    # 如果替换后仍是合法 JSON，保持其结构；否则封装为 {'content': ...}
    try:
        obj = json.loads(new_content)
        out_file.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    except json.JSONDecodeError:
        wrapper = {"original_file": src.name, "content": new_content}
        out_file.write_text(json.dumps(wrapper, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Processed: {src} → {out_file}")

# —— 主函数 —— #
def main(input_dir: str, output_dir: str):
    inp = Path(input_dir)
    out = Path(output_dir)

    # 清理旧输出
    if out.exists():
        shutil.rmtree(out)

    # 加载 Emoji 循环池
    pool = get_emoji_pool()
    emoji_cycle = cycle(pool)

    # 遍历并处理文件
    for file in inp.rglob("*"):
        if file.is_file() and file.suffix.lower() in SUPPORTED_EXTENSIONS:
            process_file(file, out, emoji_cycle)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Emoji 替换管理器")
    parser.add_argument("--input_dir",  "-i", default=".", help="要处理的目录")
    parser.add_argument("--output_dir", "-o", default="./output", help="输出目录")
    args = parser.parse_args()
    main(args.input_dir, args.output_dir)
