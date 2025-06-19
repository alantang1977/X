import os
import re
import json
import csv
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from collections import Counter, deque

# Android-safe emoji pool（可自定义扩充）
EMOJI_POOL = [
    # 动物与自然
    "🐶", "🐱", "🐭", "🐹", "🐰", "🦊", "🐻", "🐼", "🐨", "🐯",
    "🦁", "🐮", "🐷", "🐸", "🐵", "🦄", "🐔", "🐧", "🐦", "🐤",
    "🐝", "🐞", "🦋", "🐢", "🐍", "🐠", "🐬", "🐳", "🦑", "🦀",
    "🌸", "🌻", "🌹", "🌺", "🌼", "🌷", "🌱", "🌲", "🌳", "🌴",
    # 食物与饮料
    "🍏", "🍎", "🍐", "🍊", "🍋", "🍌", "🍉", "🍇", "🍓", "🫐",
    "🍈", "🍒", "🍑", "🥭", "🍍", "🥥", "🥝", "🍅", "🍆", "🥑",
    "🥦", "🥬", "🥕", "🌽", "🌶️", "🧄", "🧅", "🥔", "🥚", "🍞",
    "🥐", "🥯", "🥨", "🧀", "🥓", "🍗", "🍖", "🌭", "🍔", "🍟",
    # 活动
    "⚽", "🏀", "🏈", "⚾", "🎾", "🏐", "🏉", "🎱", "🏓", "🏸",
    "🥅", "🏒", "🏑", "🏏", "⛳", "🏹", "🎣", "🤿", "🥊", "🥋",
    "🎯", "🎳", "🪁", "🛹", "🥌", "🛷", "⛷️", "🏂", "🏄‍♂️", "🏊‍♀️",
    "🎮", "🎲", "🧩", "🀄", "♟️", "🃏", "🧗", "🏆", "🥇", "🥈", "🥉",
    # 物体
    "⌚", "📱", "💻", "🖨️", "🕹️", "🎮", "📷", "📸", "📹", "🎥",
    "📺", "📻", "🎙️", "🎚️", "🎛️", "☎️", "📞", "📟", "📠", "🔋",
    "🔌", "💡", "🔦", "🕯️", "🛢️", "💰", "💳", "🗝️", "🔑", "🚪",
    "🔒", "🔓", "🔑", "🔐", "🛡️", "🧲", "⚖️", "🔗", "🧰", "🔧",
    "🔨", "🪓", "⛏️", "🛠️", "🗡️", "⚔️", "🔫", "🏹", "🛏️", "🛋️",
    # 旅行与地点
    "🚗", "🚕", "🚙", "🚌", "🚎", "🏎️", "🚓", "🚑", "🚒", "🚐",
    "🛻", "🚚", "🚛", "🚜", "🏍️", "🛵", "🚲", "🛴", "🚨", "🚔",
    "🚦", "🚧", "🛣️", "🛤️", "✈️", "🛩️", "🚁", "🚀", "🛸", "⛵",
    "🚢", "🛳️", "⛴️", "🚤", "🛥️", "🗽", "🗼", "🏰", "🏯", "🌋",
    "🗻", "🏕️", "🏞️", "🏜️", "🏝️", "🏖️", "🏟️", "🏛️", "🏗️",
    # 人物
    "😀", "😃", "😄", "😁", "😆", "😅", "😂", "🤣", "😊", "😇",
    "🙂", "🙃", "😉", "😌", "😍", "🥰", "😘", "😗", "😙", "😚",
    "😋", "😜", "😝", "😛", "🤑", "🤗", "🤩", "🥳", "😎", "🤓",
    "🧐", "😕", "🫠", "😟", "🙁", "☹️", "😮", "😯", "😲", "😳",
    "🥺", "😦", "😧", "😨", "😰", "😥", "😢", "😭", "😱", "😖",
    "😣", "😞", "😓", "😩", "😫", "🥱", "😤", "😡", "😠", "🤬",
    "😈", "👿", "👹", "👺", "💀", "☠️", "👻", "👽", "👾", "🤖",
    "👋", "🤚", "🖐️", "✋", "🖖", "👌", "🤌", "🤏", "✌️", "🤞",
    "🫰", "🤟", "🤘", "🤙", "🫵", "🫶", "👐", "🤲", "🙏", "👏",
    "🫡", "🫥", "🤝", "👍", "👎", "👊", "✊", "👈", "👉", "👆",
    "🖕", "👇", "☝️", "🫳", "🫴", "💪", "🦾", "🦿", "🦵", "🦶",
    "👀", "👁️", "👅", "👄", "🧑", "👦", "👧", "👨", "👩", "🧓",
    "👴", "👵", "🧔", "👱‍♂️", "👱‍♀️", "👨‍🦰", "👩‍🦰", "👨‍🦱", "👩‍🦱",
    # 符号
    "❤️", "🧡", "💛", "💚", "💙", "💜", "🤎", "🖤", "🤍", "💔",
    "❣️", "💕", "💞", "💓", "💗", "💖", "💘", "💝", "💟", "☮️",
    "✝️", "☪️", "🕉️", "☸️", "✡️", "🔯", "🕎", "☯️", "☦️", "🛐",
    "⛎", "♈", "♉", "♊", "♋", "♌", "♍", "♎", "♏", "♐", "♑", "♒", "♓",
    "🆗", "🆕", "🆙", "🆒", "🆓", "ℹ️", "🆖", "🆚", "🈁", "🈯",
    "🈚", "🈷️", "🈶", "🈸", "🈴", "🈳", "🈲", "🉐", "🉑", "㊗️", "㊙️",
    "🈹", "🈺", "🈵", "🔞", "💯", "🔢", "🔤", "🔡", "🔠", "🆎", "🅰️", "🅱️", "🅾️", "🅿️",
    "©️", "®️", "™️", "#️⃣", "*️⃣", "0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟",
    "🔔", "🔕", "🎵", "🎶", "💤", "💢", "💬", "💭", "🗯️", "♨️", "💦", "💨", "💫", "🕳️", "💣", "💥", "🚨", "💦",
    "💡", "🔑", "🔒", "🔓", "🔏", "🔐", "🛡️", "🧲", "🔗", "⚖️", "🧰", "🔧", "🔨", "🪓", "⛏️", "🛠️", "🗡️", "⚔️",
    "🔫", "🏹", "🛏️", "🛋️", "🛒", "🧺", "🧻", "🧼", "🪥", "🧽", "🪣", "🧴", "🧷", "🧹", "🪒", "🧯", "🛎️"
]

EMOJI_REGEX = re.compile(
    r"("
    r"(?:[\U0001F1E6-\U0001F1FF]{2})|"  # flags
    r"(?:[\U0001F600-\U0001F64F])|"
    r"(?:[\U0001F300-\U0001F5FF])|"
    r"(?:[\U0001F680-\U0001F6FF])|"
    r"(?:[\U0001F700-\U0001F77F])|"
    r"(?:[\U0001F780-\U0001F7FF])|"
    r"(?:[\U0001F800-\U0001F8FF])|"
    r"(?:[\U0001F900-\U0001F9FF])|"
    r"(?:[\U0001FA00-\U0001FA6F])|"
    r"(?:[\U0001FA70-\U0001FAFF])|"
    r"(?:[\u2600-\u26FF])|"
    r"(?:[\u2700-\u27BF])|"
    r"(?:[\u2300-\u23FF])|"
    r"(?:[\u2B05-\u2B07])|"
    r"(?:\u200D)"
    r")+",
    re.UNICODE
)

SUPPORTED_EXTS = (".json", ".txt", ".md", ".csv", ".xml", ".html", ".htm")

def extract_emoji(text):
    # Find all emoji/sequence, keeping order, including duplicates
    return [m.group(0) for m in EMOJI_REGEX.finditer(text)]

def build_duplicate_emoji_mapping(emoji_list, emoji_pool):
    """
    保留每个emoji首次出现不变，仅对重复出现的emoji做替换为pool中未用过的emoji。
    若emoji_pool用尽则循环使用。
    返回字典：{原emoji: [None, 替换1, 替换2...]}，None表示首个不换。
    """
    counts = Counter(emoji_list)
    duplicates = {em for em, c in counts.items() if c > 1}
    # 统计每个emoji出现了几次
    positions = {}
    for idx, em in enumerate(emoji_list):
        positions.setdefault(em, []).append(idx)
    # 新emoji分配池
    used = set(emoji_list)
    pool = deque([e for e in emoji_pool if e not in used])
    emoji_replace_map = {}
    for em in duplicates:
        occurrence = len(positions[em])
        repls = [None]  # 第一次出现不替换
        for _ in range(occurrence - 1):
            if not pool:
                pool = deque([e for e in emoji_pool if e not in used])
            if pool:
                new_em = pool.popleft()
                repls.append(new_em)
                pool.append(new_em)
            else:
                # 纯保险，理论不会到这里
                repls.append(em)
        emoji_replace_map[em] = repls
    return emoji_replace_map, positions

def replace_duplicates_in_text(text, emoji_replace_map, positions):
    """
    仅替换重复的emoji，第一次出现保留，后续出现才换。
    """
    matches = list(EMOJI_REGEX.finditer(text))
    # 记录每个emoji已出现次数
    occur_dict = {em:0 for em in emoji_replace_map}
    last_idx = 0
    result = []
    for m in matches:
        em = m.group(0)
        result.append(text[last_idx:m.start()])
        if em in emoji_replace_map:
            occur_dict[em] += 1
            # 首次出现用原emoji，后续用映射
            idx = occur_dict[em]
            repl = emoji_replace_map[em][idx-1]  # idx-1：第0次None, 从1开始替换
            if repl is None:
                result.append(em)
            else:
                result.append(repl)
        else:
            result.append(em)
        last_idx = m.end()
    result.append(text[last_idx:])
    return ''.join(result)

def process_json_file(src, dst, emoji_replace_map, positions):
    with open(src, "r", encoding="utf-8") as f:
        data = json.load(f)
    def recursive(obj):
        if isinstance(obj, str):
            return replace_duplicates_in_text(obj, emoji_replace_map, positions)
        elif isinstance(obj, list):
            return [recursive(o) for o in obj]
        elif isinstance(obj, dict):
            return {k: recursive(v) for k, v in obj.items()}
        return obj
    data_new = recursive(data)
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(data_new, f, ensure_ascii=False, indent=2)

def process_csv_file(src, dst, emoji_replace_map, positions):
    with open(src, "r", encoding="utf-8", newline='') as f:
        reader = list(csv.reader(f))
    new_rows = []
    for row in reader:
        new_row = [replace_duplicates_in_text(cell, emoji_replace_map, positions) for cell in row]
        new_rows.append(new_row)
    with open(dst, "w", encoding="utf-8", newline='') as f:
        writer = csv.writer(f)
        writer.writerows(new_rows)

def process_txt_file(src, dst, emoji_replace_map, positions):
    with open(src, "r", encoding="utf-8") as f:
        text = f.read()
    new_text = replace_duplicates_in_text(text, emoji_replace_map, positions)
    with open(dst, "w", encoding="utf-8") as f:
        f.write(new_text)

def process_md_file(src, dst, emoji_replace_map, positions):
    process_txt_file(src, dst, emoji_replace_map, positions)

def process_xml_file(src, dst, emoji_replace_map, positions):
    tree = ET.parse(src)
    root = tree.getroot()
    def recursive_xml(elem):
        if elem.text:
            elem.text = replace_duplicates_in_text(elem.text, emoji_replace_map, positions)
        if elem.tail:
            elem.tail = replace_duplicates_in_text(elem.tail, emoji_replace_map, positions)
        for child in elem:
            recursive_xml(child)
    recursive_xml(root)
    tree.write(dst, encoding="utf-8", xml_declaration=True)

class MyHTMLParser(HTMLParser):
    def __init__(self, emoji_replace_map, positions):
        super().__init__()
        self.emoji_replace_map = emoji_replace_map
        self.positions = positions
        self.result = []
    def handle_starttag(self, tag, attrs):
        attr_str = ''.join([f' {k}="{v}"' for k, v in attrs])
        self.result.append(f"<{tag}{attr_str}>")
    def handle_endtag(self, tag):
        self.result.append(f"</{tag}>")
    def handle_data(self, data):
        self.result.append(replace_duplicates_in_text(data, self.emoji_replace_map, self.positions))
    def handle_entityref(self, name):
        self.result.append(f"&{name};")
    def handle_charref(self, name):
        self.result.append(f"&#{name};")
    def get_html(self):
        return "".join(self.result)

def process_html_file(src, dst, emoji_replace_map, positions):
    with open(src, "r", encoding="utf-8") as f:
        text = f.read()
    parser = MyHTMLParser(emoji_replace_map, positions)
    parser.feed(text)
    with open(dst, "w", encoding="utf-8") as f:
        f.write(parser.get_html())

def main():
    src_dir = os.path.join(os.path.dirname(__file__))
    output_dir = os.path.join(src_dir, "output")
    os.makedirs(output_dir, exist_ok=True)
    files = [f for f in os.listdir(src_dir)
             if os.path.isfile(os.path.join(src_dir, f))
             and f.lower().endswith(SUPPORTED_EXTS)
             and not f.startswith("output")]
    for filename in files:
        src_path = os.path.join(src_dir, filename)
        dst_path = os.path.join(output_dir, filename)
        print(f"Processing {filename}")
        with open(src_path, "r", encoding="utf-8") as f:
            text = f.read()
        emoji_list = extract_emoji(text)
        if not emoji_list:
            print(f"  No emoji found in {filename}, skip.")
            continue
        emoji_replace_map, positions = build_duplicate_emoji_mapping(emoji_list, EMOJI_POOL)
        ext = os.path.splitext(filename)[-1].lower()
        if ext == ".json":
            process_json_file(src_path, dst_path, emoji_replace_map, positions)
        elif ext == ".txt":
            process_txt_file(src_path, dst_path, emoji_replace_map, positions)
        elif ext == ".md":
            process_md_file(src_path, dst_path, emoji_replace_map, positions)
        elif ext == ".csv":
            process_csv_file(src_path, dst_path, emoji_replace_map, positions)
        elif ext == ".xml":
            process_xml_file(src_path, dst_path, emoji_replace_map, positions)
        elif ext in (".html", ".htm"):
            process_html_file(src_path, dst_path, emoji_replace_map, positions)
        else:
            print(f"  Unsupported file type: {filename}")

if __name__ == "__main__":
    main()
