import os
import json
import random
import re

# 安卓主流支持 emoji 列表（可自行添加扩展）
ANDROID_SUPPORTED_EMOJIS = [
    "😀","😁","😂","🤣","😃","😄","😅","😆","😉","😊","😋","😎","😍","😘","🥰","😗","😙","😚",
    "🙂","🤗","🤩","🤔","🤨","😐","😑","😶","🙄","😏","😣","😥","😮","🤐","😯","😪","😫",
    "🥱","😴","😌","😛","😜","😝","🤤","😒","😓","😔","😕","🙃","🤑","😲","☹️","🙁","😖",
    "😞","😟","😤","😢","😭","😦","😧","😨","😩","🤯","😬","😰","😱","🥵","🥶","😳","🤪",
    "😵","😡","😠","🤬","😷","🤒","🤕","🤢","🤮","🤧","😇","🥳","🥺","🥲","🤠","🥸","🤓",
    "🧐","🤖","👻","💀","☠️","👽","👾","👹","👺","💩","😺","😸","😹","😻","😼","😽",
    "🙀","😿","😾","🙈","🙉","🙊","🐶","🐱","🐭","🐹","🐰","🦊","🐻","🐼","🐨","🐯","🦁",
    "🐮","🐷","🐽","🐸","🐵","🐔","🐧","🐦","🐤","🐣","🐥","🦆","🦅","🦉","🦇","🐺","🐗",
    "🐴","🦄","🐝","🐛","🦋","🐌","🐚","🐞","🐜","🦗","🕷️","🦂","🐢","🐍","🦎","🦖","🦕",
    "🐙","🦑","🦐","🦞","🦀","🐡","🐠","🐟","🐬","🐳","🐋","🦈","🐊","🐅","🐆","🐘","🦏",
    "🦛","🐪","🐫","🦙","🦒","🐃","🐂","🐄","🐎","🐖","🐏","🐑","🐐","🦌","🐕","🐩","🦮",
    "🐕‍🦺","🐈","🐓","🦃","🦚","🦜","🦢","🦩","🕊️","🐇","🦝","🦨","🦡","🦦","🦥","🐁",
    "🐀","🐿️","🦔"
]

# 精确匹配安卓支持 emoji
ANDROID_EMOJI_PATTERN = re.compile(
    r'({})'.format('|'.join(re.escape(emoji) for emoji in ANDROID_SUPPORTED_EMOJIS))
)

def replace_android_emojis_in_line(line, used_emojis):
    """
    替换行内所有安卓支持的 emoji（全局唯一，除非用尽），其它全部不变
    """
    def emoji_replacer(match):
        available = list(set(ANDROID_SUPPORTED_EMOJIS) - used_emojis)
        if not available:
            available = ANDROID_SUPPORTED_EMOJIS  # 用尽后可重复
        chosen = random.choice(available)
        used_emojis.add(chosen)
        return chosen
    return ANDROID_EMOJI_PATTERN.sub(emoji_replacer, line)

def process_txt_file(input_path, output_path):
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"读取失败：{input_path}，错误：{e}")
        return
    used_emojis = set()
    processed_lines = []
    for line in lines:
        # 保持每行换行符，内容除了 emoji 替换外全部保留
        replaced_line = replace_android_emojis_in_line(line, used_emojis)
        processed_lines.append(replaced_line)
    # 写为json数组，每项为一行的原始内容（含换行符）
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(processed_lines, f, ensure_ascii=False, indent=2)
        print(f"已生成文件: {output_path}")
    except Exception as e:
        print(f"写入失败：{output_path}，错误：{e}")

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    emojis_dir = script_dir
    output_dir = os.path.join(emojis_dir, "output")
    os.makedirs(output_dir, exist_ok=True)
    for file in os.listdir(emojis_dir):
        if file.endswith('.txt'):
            input_path = os.path.join(emojis_dir, file)
            out_name = os.path.splitext(file)[0] + ".json"
            output_path = os.path.join(output_dir, out_name)
            process_txt_file(input_path, output_path)

if __name__ == "__main__":
    main()
