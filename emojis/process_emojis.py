# 文件: emojis/process_emojis.py
"""
遍历目录下所有文件（支持 JSON、TXT、MD、CSV、XML、HTML），
提取内容中的 Emoji 表情，使用正则表达式，
通过一个预定义的 Emoji 列表去重并循环分配，
并将结果以 JSON 格式写入 output 文件夹，保持原文件名。
"""
import os
import re
import json
import csv
import shutil
from itertools import cycle

# 完整的 Emoji 列表，可根据需要扩充
EMOJI_POOL = [
    '😀', '😂', '😅', '😊', '😍', '😎', '😢', '😭', '😡', '😱',
    '👍', '👎', '👌', '🙏', '✌️', '🤞', '💪', '🚀', '🌟', '🔥',
    '🍎', '🍉', '🍕', '⚽', '🏀', '🎲', '🎉', '🎁', '❤️', '💔',
    '🐶', '🐱', '🦊', '🐸', '🐟', '🦄', '🌈', '☀️', '🌙', '⭐',
    '⚡', '💧', '❄️', '🔥', '🍀', '🍄', '🔔', '🎵', '🎬', '📚',
    # ... 可继续添加到完整列表
]
# Emoji 正则（简化版）
EMOJI_REGEX = re.compile(r'[\U0001F300-\U0001F6FF\U0001F900-\U0001F9FF\u2600-\u26FF\u2700-\u27BF]+')


def extract_unique_emojis(text):
    """提取所有 emoji 并返回去重集合"""
    found = EMOJI_REGEX.findall(text)
    return list(dict.fromkeys(''.join(found)))


def replace_emojis(text, replacer):
    """将文本中的 emoji 按 replacer 映射替换"""
    def repl(match):
        return replacer.get(match.group(0), match.group(0))
    return EMOJI_REGEX.sub(repl, text)


def load_file(path):
    ext = os.path.splitext(path)[1].lower()
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    return ext, content


def save_output(data, out_path):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def process_file(src_path, out_dir, emoji_cycle):
    ext, content = load_file(src_path)
    emojis = extract_unique_emojis(content)
    # 构造替换映射
    mapping = {}
    for orig in emojis:
        mapping[orig] = next(emoji_cycle)
    # 替换内容
    new_content = replace_emojis(content, mapping)

    # 输出 JSON 格式
    result = {
        'original_file': os.path.basename(src_path),
        'mapping': mapping,
        'content': new_content
    }
    out_path = os.path.join(out_dir, os.path.basename(src_path) + '.json')
    save_output(result, out_path)
    print(f"Processed {src_path} -> {out_path}")


def main(input_dir='.', output_dir='output'):
    # 清理旧输出
    if os.path.isdir(output_dir):
        shutil.rmtree(output_dir)
    # 开始循环池
    emoji_cycle = cycle(EMOJI_POOL)
    # 遍历目录
    for root, _, files in os.walk(input_dir):
        # 跳过 output 目录
        if output_dir in root:
            continue
        for file in files:
            if file.lower().endswith(('.json', '.txt', '.md', '.csv', '.xml', '.html')):
                process_file(os.path.join(root, file), output_dir, emoji_cycle)

if __name__ == '__main__':
    main()

# 使用说明：
# 1. 将本脚本放置于 GitHub 仓库的 emojis 文件夹下。
# 2. 在仓库根目录执行： python emojis/process_emojis.py --input_dir=your_dir --output_dir=emojis/output
# 3. 脚本仅替换已有的 Emoji，不会增删其他字符。
