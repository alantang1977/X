# 文件: emojis/process_emojis.py

import os
import re
import json
import shutil
from pathlib import Path
from itertools import cycle
from emojis.emoji_loader import get_emoji_pool

# 支持处理的文件后缀
SUPPORTED_EXTENSIONS = ['.json', '.txt', '.md', '.csv', '.xml', '.html']

# 加载完整 Emoji 列表，并创建循环迭代器
emoji_pool = get_emoji_pool()
emoji_cycle = cycle(emoji_pool)

# 通用 Emoji 匹配正则
emoji_pattern = re.compile(
    "[\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "]+", flags=re.UNICODE
)

def replace_emojis(text: str) -> str:
    """
    将文本中匹配到的每个 Emoji，用 emoji_cycle 循环提供的新 Emoji 依次替换。
    只替换已有的 Emoji，不增删其他符号/文字。
    """
    def _replacer(match):
        return next(emoji_cycle)
    return emoji_pattern.sub(_replacer, text)

def process_file(file_path: Path, output_dir: Path):
    content = file_path.read_text(encoding='utf-8')
    new_content = replace_emojis(content)

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / (file_path.stem + '.json')

    # 如果原文件是合法 JSON，就保持 JSON 结构，否则当作普通文本封装
    try:
        parsed = json.loads(new_content)
        output_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding='utf-8')
    except json.JSONDecodeError:
        wrapped = {'content': new_content}
        output_path.write_text(json.dumps(wrapped, ensure_ascii=False, indent=2), encoding='utf-8')

    print(f"Processed {file_path} → {output_path}")

def main(input_dir: str = '.', output_dir: str = './output'):
    in_path = Path(input_dir)
    out_path = Path(output_dir)

    # 清理旧输出
    if out_path.exists():
        shutil.rmtree(out_path)

    for file in in_path.rglob('*'):
        if file.is_file() and file.suffix.lower() in SUPPORTED_EXTENSIONS:
            process_file(file, out_path)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Emoji 替换工具")
    parser.add_argument("--input_dir", type=str, default=".", help="输入目录")
    parser.add_argument("--output_dir", type=str, default="./output", help="输出目录")
    args = parser.parse_args()
    main(args.input_dir, args.output_dir)
