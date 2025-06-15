import os
import glob
import json
import re
import random
from typing import Any, List

# -----------------------------------------------------------------------------
# Emoji 候选池（请补充到足够多，下面为示例）
# -----------------------------------------------------------------------------
EMOJI_POOL: List[str] = [
    # 食物和饮料相关Emoji (部分示例)
    "🍎", "🍏", "🍐", "🍊", "🍋", "🍌", "🍉", "🍇", "🍓", "🫐",
    "🍈", "🍒", "🍑", "🥭", "🍍", "🥥", "🥝", "🍅", "🫒", "🥑",
    "🍆", "🥔", "🥕", "🌽", "🌶️", "🫑", "🥒", "🥬", "🥦", "🧄",
    "🧅", "🍄", "🥜", "🌰", "🍞", "🥐", "🥖", "🫓", "🥨", "🥯",
    "🥞", "🧇", "🧀", "🍖", "🍗", "🥩", "🥓", "🍔", "🍟", "🍕",
    "🌮", "🌯", "🫔", "🥙", "🧆", "🥚", "🍳", "🥘", "🍲", "🫕",
    "🥣", "🥗", "🍱", "🍘", "🍙", "🍚", "🍛", "🍜", "🍝", "🍠",
    "🍢", "🍣", "🍤", "🍥", "🥮", "🍡", "🥟", "🥠", "🥡", "🦀",
    "🦞", "🦐", "🦑", "🍦", "🍧", "🍨", "🥧", "🍰", "🎂", "🍮",
    "🍭", "🍬", "🍫", "🍿", "🍩", "🍪", "🧂", "🫘", "🍯", "🧈", 
    "🥛", "🍼", "☕", "🫖", "🍵", "🍶", "🍾", "🍷", "🍸", "🍹",
    "🍺", "🍻", "🥂", "🥃", "🥤", "🧋", "🧃", "🧉", "🧊", "🥢", 
    "🍽️", "🔪", "🍴", "🥄",
    # 动物和自然相关Emoji (部分示例)
    "🐶", "🐱", "🐭", "🐹", "🐰", "🦊", "🐻", "🐼", "🐨", "🐯",
    "🦁", "🐮", "🐷", "🐸", "🐵", "🐔", "🐧", "🐦", "🐤", "🐣",
    "🐥", "🦆", "🦅", "🦉", "🦇", "🐺", "🐗", "🐴", "🦄", "🐝",
    "🐛", "🦋", "🐌", "🐞", "🐜", "🕷️", "🦂", "🦟", "🦗", "🐢",
    "🐍", "🦎", "🦖", "🦕", "🐙", "🦑", "🦐", "🦀", "🐡", "🐠",
    "🐟", "🐬", "🐳", "🐋", "🦈", "🐊", "🐅", "🐆", "🦓", "🦍",
    "🦧", "🦣", "🐘", "🦛", "🦏", "🐪", "🐫", "🦒", "🦘", "🦬",
    "🐃", "🐂", "🐄", "🐎", "🐖", "🐏", "🐑", "🐐", "🦌", "🦙",
    "🦥", "🦘", "🦨", "🦡", "🦃", "🕊️", "🦢", "🦚", "🦜", "🦝",
    "🐕‍🦺", "🦮", "🐕", "🐈", "🐈‍⬛", "🐾", "🌱", "🌲", "🌳", "🌴",
    "🌵", "🌾", "🌿", "🍀", "🍁", "🍃", "🍂", "🌼", "🌻", "🌷",
    "🌹", "🥀", "🌺", "🌸", "💐",
    # 旅行和地点相关Emoji (部分示例)
    "✈️", "🛫", "🛬", "🚁", "🚀", "🛸", "🚢", "🛳️", "⛴️", "🚂",
    "🚅", "🚆", "🚊", "🚉", "🚌", "🚍", "🚎", "🚐", "🚑", "🚒",
    "🚓", "🚔", "🚕", "🚖", "🚗", "🚘", "🚙", "🚚", "🚛", "🚜",
    "🛵", "🚲", "🚏", "⛽", "🚧", "🚨", "🚥", "🚦", "🏮", "🏰",
    "🏯", "🏭", "🏢", "🏬", "🏤", "🏥", "🏦", "🏨", "🏩", "🏪",
    "🏫", "🏭", "🏰", "🗼", "🗽", "🗿", "🗺️", "🗾", "🏝️", "🏜️",
    "🏕️", "🏖️", "🏔️", "🌋", "🗻", "🏞️", "🌅", "🌄", "🌇", "🌆",
    "🌉", "🌌", "🌃", "🏙️",
    # 如需更多请自行扩充
]

EMOJI_PATTERN = re.compile(
    r'('
    u'[\U0001F300-\U0001F5FF]'
    u'|[\U0001F600-\U0001F64F]'
    u'|[\U0001F680-\U0001F6FF]'
    u'|[\U0001F1E0-\U0001F1FF]'
    u'|[\u2600-\u27BF]'
    r')',
    flags=re.UNICODE
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = BASE_DIR
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

def find_emojis_in_head(text: str) -> List[str]:
    head = text.split('┃', 1)[0]
    return [m.group(0) for m in EMOJI_PATTERN.finditer(head)]

def collect_all_emojis(obj: Any, key: str = "name") -> List[str]:
    found = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key and isinstance(v, str):
                found.extend(find_emojis_in_head(v))
            else:
                found.extend(collect_all_emojis(v, key))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(collect_all_emojis(item, key))
    return found

def precise_replace_head_emojis(text: str, new_emojis: List[str]) -> str:
    head, *tail = text.split('┃', 1)
    matches = list(EMOJI_PATTERN.finditer(head))
    if len(matches) != len(new_emojis):
        raise ValueError("Emoji数目不一致，无法精准替换。")
    head_list = list(head)
    for match, new_emoji in zip(reversed(matches), reversed(new_emojis)):
        start, end = match.span()
        head_list[start:end] = [new_emoji]
    new_head = ''.join(head_list)
    return new_head + ('┃' + tail[0] if tail else '')

def replace_name_head_emojis(obj: Any, new_emojis: List[str], key: str = "name"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key and isinstance(v, str):
                old_count = len(find_emojis_in_head(v))
                this_new = [new_emojis.pop(0) for _ in range(old_count)]
                obj[k] = precise_replace_head_emojis(v, this_new)
            else:
                replace_name_head_emojis(v, new_emojis, key)
    elif isinstance(obj, list):
        for item in obj:
            replace_name_head_emojis(item, new_emojis, key)

def process_file(input_path: str, output_path: str):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    # 尝试解析JSON，如果失败则跳过并输出原文件
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"[错误] 无法解析 JSON 文件 {os.path.basename(input_path)}: {e}")
        # 尝试直接拷贝原始内容到 output 目录
        try:
            with open(input_path, 'r', encoding='utf-8') as fin, open(output_path, 'w', encoding='utf-8') as fout:
                fout.write(fin.read())
            print(f"[跳过] 已将原始内容拷贝到 {os.path.basename(output_path)}")
        except Exception as copy_exc:
            print(f"[错误] 拷贝原始文件失败: {copy_exc}")
        return False

    old_emojis = collect_all_emojis(data)
    total = len(old_emojis)
    if total == 0:
        print(f"[跳过] `{os.path.basename(input_path)}` 中 “name” 字段第一段无 Emoji。")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return False

    if total > len(set(EMOJI_POOL)):
        print(f"[错误] 需要替换 {total} 个 Emoji，但池中只有 {len(set(EMOJI_POOL))} 个，请补充 EMOJI_POOL。")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return False

    new_emojis = random.sample(list(set(EMOJI_POOL)), k=total)
    data_copy = json.loads(json.dumps(data, ensure_ascii=False))  # 深拷贝
    replace_name_head_emojis(data_copy, new_emojis.copy())

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data_copy, f, ensure_ascii=False, indent=2)
    print(f"[完成] `{os.path.basename(input_path)}` → `{os.path.basename(output_path)}`，已精准替换 {total} 个 Emoji")
    return True

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    json_files = glob.glob(os.path.join(INPUT_DIR, "*.json"))
    if not json_files:
        print("⚠️ 未找到任何 .json 文件。")
        return

    for path in json_files:
        fname = os.path.basename(path)
        out = os.path.join(OUTPUT_DIR, fname)
        process_file(path, out)

    print("🎉 全部处理完成，输出目录：", OUTPUT_DIR)

if __name__ == "__main__":
    main()
