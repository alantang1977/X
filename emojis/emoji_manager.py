import os
import re
import json
import shutil

# 完整 Emoji 表情池（部分展示，实际使用可补充更多）
EMOJI_POOL = [
    "😀", "😁", "😂", "🤣", "😃", "😄", "😅", "😆", "😉", "😊",
    "😋", "😎", "😍", "😘", "🥰", "😗", "😙", "😚", "🙂", "🤗",
    "🤩", "🤔", "🤨", "😐", "😑", "😶", "🙄", "😏", "😣", "😥",
    "😮", "🤐", "😯", "😪", "😫", "🥱", "😴", "😌", "😛", "😜",
    "😝", "🤤", "😒", "😓", "😔", "😕", "🙃", "🤑", "😲", "☹️",
    "🙁", "😖", "😞", "😟", "😤", "😢", "😭", "😦", "😧", "😨",
    "😩", "🤯", "😬", "😰", "😱", "🥵", "🥶", "😳", "🤪", "😵",
    "😡", "😠", "🤬", "😷", "🤒", "🤕", "🤢", "🤮", "🤧", "😇",
    "🥳", "🥺", "🤠", "🤡", "🤥", "🤫", "🤭", "🧐", "🤓", "😈",
    "👿", "👹", "👺", "💀", "👻", "👽", "🤖", "💩", "😺", "😸"
]

# Emoji 正则表达式（覆盖大部分 Emoji）
EMOJI_REGEX = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # Emoticons
    "\U0001F300-\U0001F5FF"  # Symbols & Pictographs
    "\U0001F680-\U0001F6FF"  # Transport & Map Symbols
    "\U0001F1E0-\U0001F1FF"  # Flags
    "\U00002700-\U000027BF"
    "\U000024C2-\U0001F251"
    "]+", flags=re.UNICODE
)

SUPPORTED_EXTS = {'.json', '.txt', '.md', '.csv', '.xml', '.html'}

def extract_emojis(text):
    return EMOJI_REGEX.findall(text)

def replace_emojis(text, emoji_map):
    def _repl(match):
        return emoji_map.get(match.group(0), match.group(0))
    return EMOJI_REGEX.sub(_repl, text)

def build_emoji_map(unique_emojis, emoji_pool):
    pool = list(emoji_pool)
    mapping = {}
    cnt = 0
    n = len(pool)
    for e in unique_emojis:
        mapping[e] = pool[cnt % n]
        cnt += 1
    return mapping

def process_json(obj, emoji_map):
    if isinstance(obj, str):
        return replace_emojis(obj, emoji_map)
    elif isinstance(obj, list):
        return [process_json(item, emoji_map) for item in obj]
    elif isinstance(obj, dict):
        return {k: process_json(v, emoji_map) for k, v in obj.items()}
    else:
        return obj

def process_file(filepath, output_dir, emoji_pool):
    filename = os.path.basename(filepath)
    name, ext = os.path.splitext(filename)
    if ext.lower() not in SUPPORTED_EXTS:
        return

    # 读取内容
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # 提取并去重
    file_emojis = set(extract_emojis(content))
    if not file_emojis:
        # 没有 Emoji，直接跳过
        return

    # 构建映射
    emoji_map = build_emoji_map(file_emojis, emoji_pool)

    # 替换 Emoji
    if ext.lower() == ".json":
        try:
            data = json.loads(content)
            new_data = process_json(data, emoji_map)
            output_content = json.dumps(new_data, ensure_ascii=False, indent=2)
        except Exception:
            # JSON 解析失败，作为普通文本处理
            output_content = replace_emojis(content, emoji_map)
    else:
        output_content = replace_emojis(content, emoji_map)

    # 输出同名 json 文件
    output_path = os.path.join(output_dir, f"{name}.json")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output_content)

def main(input_dir):
    # 自动在输入目录下创建 output 文件夹
    output_dir = os.path.join(input_dir, "output")
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    # 遍历目录下所有支持的文件
    for fname in os.listdir(input_dir):
        fpath = os.path.join(input_dir, fname)
        if os.path.isfile(fpath):
            process_file(fpath, output_dir, EMOJI_POOL)

if __name__ == "__main__":
    # 操作示例：python emoji_manager.py ./emojis
    import sys
    if len(sys.argv) < 2:
        print("用法: python emoji_manager.py <要处理的目录>")
    else:
        main(sys.argv[1])
