# emojis/process_emojis.py

import os
import re
import json
from pathlib import Path
from emojis.emoji_loader import get_emoji_pool

SUPPORTED_EXTENSIONS = ['.json', '.txt', '.md', '.csv', '.xml', '.html']

emoji_pool = get_emoji_pool()
emoji_index = 0

emoji_pattern = re.compile(
    "[\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "]+", flags=re.UNICODE
)

def replace_emojis(text):
    global emoji_index
    def replacer(match):
        nonlocal emoji_index
        emoji = emoji_pool[emoji_index % len(emoji_pool)]
        emoji_index += 1
        return emoji
    return emoji_pattern.sub(replacer, text)

def process_file(file_path, output_dir):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    new_content = replace_emojis(content)

    output_path = output_dir / (file_path.stem + '.json')
    os.makedirs(output_dir, exist_ok=True)

    try:
        json_obj = json.loads(new_content)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(json_obj, f, ensure_ascii=False, indent=2)
    except json.JSONDecodeError:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({'content': new_content}, f, ensure_ascii=False, indent=2)

def main(input_dir, output_dir):
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    for file in input_path.rglob("*"):
        if file.suffix.lower() in SUPPORTED_EXTENSIONS:
            print(f"Processing: {file}")
            process_file(file, output_path)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Emoji 替换工具")
    parser.add_argument("--input_dir", type=str, default=".", help="输入目录")
    parser.add_argument("--output_dir", type=str, default="./output", help="输出目录")
    args = parser.parse_args()
    main(args.input_dir, args.output_dir)
