import os
import re
import json
import shutil

# Emoji pools（仅选安卓常见的，涵盖动物与自然、食物与饮料、活动、物体、旅行与地点等）
EMOJI_POOL = [
    # 动物与自然
    "🐶", "🐱", "🦁", "🐯", "🦊", "🐻", "🐼", "🐨", "🐸", "🐵", "🦄", "🐔", "🐧", "🐦", "🐤", "🐣", "🐺", "🐍", "🐢", "🐬", "🦋",
    # 食物与饮料
    "🍏", "🍎", "🍌", "🍉", "🍇", "🍓", "🍈", "🍒", "🍑", "🥭", "🍍", "🥝", "🍅", "🥑", "🥦", "🍆", "🍔", "🍟", "🍕", "🌭", "🍿",
    # 活动
    "⚽", "🏀", "🏈", "⚾", "🥎", "🎾", "🏐", "🏉", "🎱", "🏓", "🏸", "🥅", "🎣", "🥊", "⛳", "🏹", "🎮", "🕹️",
    # 物体
    "📱", "💻", "🖨️", "🖱️", "📷", "📸", "🎥", "🕰️", "⏰", "📺", "📻", "🔋", "🔌", "💡", "🔦", "📦", "🎁", "🗝️", "🔑", "🔒", "🔓",
    # 旅行与地点
    "🚗", "🚕", "🚌", "🚎", "🏎️", "🚓", "🚑", "🚒", "🚜", "✈️", "🚀", "🚁", "⛴️", "🚢", "🛳️", "🚤", "🚲", "🏠", "🏡", "🏢", "🏣", "🏤", "🏥"
]
EMOJI_POOL_LEN = len(EMOJI_POOL)

# Emoji正则（宽泛匹配，兼容多平台，主要安卓）
EMOJI_REGEX = re.compile(
    "["
    "\U0001F300-\U0001F6FF"  # 运输与地图、物体、活动
    "\U0001F900-\U0001F9FF"  # 补充表情
    "\U0001FA70-\U0001FAFF"  # 物体补充
    "\U0001F680-\U0001F6FF"  # 交通运输
    "\U0001F1E0-\U0001F1FF"  # 国旗
    "\U00002600-\U000026FF"  # 杂项符号
    "\U00002700-\U000027BF"  # 杂项符号
    "\U0001F700-\U0001F77F"  # 炼金术符号
    "\U0001F780-\U0001F7FF"  # 地理符号
    "\U0001F800-\U0001F8FF"  # 补充箭头
    "\U0001F000-\U0001F02F"  # 麻将
    "\U00002300-\U000023FF"  # 技术符号
    "\U0001F0A0-\U0001F0FF"  # 扑克牌
    "]+", flags=re.UNICODE
)

# 支持的文本文件扩展名
SUPPORTED_EXT = [".json", ".txt", ".md", ".csv", ".xml", ".html"]

def extract_emojis(text):
    """提取文本中所有emoji"""
    return EMOJI_REGEX.findall(text)

def replace_emojis(text, emoji_map):
    """替换文本中emoji为emoji_map中的对应新emoji"""
    def repl(match):
        emoji = match.group(0)
        return emoji_map.get(emoji, emoji)
    return EMOJI_REGEX.sub(repl, text)

def process_file(input_path, output_path, emoji_iter):
    """处理单个文件，输出为json格式，文件名同输入"""
    ext = os.path.splitext(input_path)[1].lower()
    with open(input_path, "r", encoding="utf-8") as f:
        content = f.read()
    emojis = extract_emojis(content)
    unique_emojis = list(set(emojis))
    emoji_map = {}
    # 循环分配替换的emoji
    for i, emoji in enumerate(unique_emojis):
        emoji_map[emoji] = next(emoji_iter)
    # 替换emoji
    new_content = replace_emojis(content, emoji_map)
    # 构建输出内容
    if ext == ".json":
        try:
            json_obj = json.loads(content)
            # 递归替换json中所有字符串的emoji
            def replace_json(obj):
                if isinstance(obj, str):
                    return replace_emojis(obj, emoji_map)
                elif isinstance(obj, list):
                    return [replace_json(i) for i in obj]
                elif isinstance(obj, dict):
                    return {k: replace_json(v) for k, v in obj.items()}
                else:
                    return obj
            new_json_obj = replace_json(json_obj)
            output_data = new_json_obj
        except Exception as e:
            # 若解析失败则按普通文本处理
            output_data = new_content
    else:
        output_data = new_content
    # 输出为json格式
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"content": output_data}, f, ensure_ascii=False, indent=2)

def emoji_cycle():
    """返回一个循环emoji迭代器"""
    while True:
        for emoji in EMOJI_POOL:
            yield emoji

def main(input_dir):
    input_dir = os.path.abspath(input_dir)
    output_dir = os.path.join(input_dir, "output")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    emoji_iter = emoji_cycle()
    for filename in os.listdir(input_dir):
        file_path = os.path.join(input_dir, filename)
        if os.path.isfile(file_path):
            ext = os.path.splitext(filename)[1].lower()
            if ext in SUPPORTED_EXT:
                output_path = os.path.join(output_dir, os.path.splitext(filename)[0] + ".json")
                process_file(file_path, output_path, emoji_iter)
    print(f"处理完成！结果已存放在 {output_dir}/")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Emoji智能识别与替换工具")
    parser.add_argument("--input", type=str, required=True, help="输入目录路径")
    args = parser.parse_args()
    main(args.input)
