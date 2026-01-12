import os
import json
from itertools import cycle

# ===================== 基础配置 =====================

PY_DIR = "py"
OUTPUT = "config.json"

PRIORITY_PREFIX = "剧透社"

# ===================== Android 通用 Emoji 池 =====================
# 说明：
# - 均为 Android 8+ 稳定显示
# - 无肤色、无组合、无国旗
# - 可放心用于 TV / 手机 / 壳

EMOJI_POOL = [
    "😀","😃","😄","😁","😆","😅","😂","🙂","😉","😊",
    "😇","😍","🤩","😎","🤓","🧐","🤖","👻","💀","👽",
    "👁","👀","🧠","🫀","🦾","🦿","💪","✋","👋","👌",
    "👍","👎","👏","🙏","🫶","💡","🔥","⚡","💥","🌟",
    "⭐","✨","🌈","☀","🌙","🌍","🌎","🌏","🌐","🗺",
    "🧭","⏱","⏰","⌛","📡","🛰","📺","📻","📱","💻",
    "🖥","🖨","⌨","🖱","💽","💾","📀","🎬","🎥","📽",
    "🍿","🎞","🎮","🕹","🎲","♟","🎯","🎵","🎶","🎧",
    "📦","📁","📂","🗂","🧩","🧱","⚙","🛠","🔧","🔩",
    "🔍","🔎","🔒","🔓","🔑","🗝","🧲","🧪","🧬","🔮",
    "🚀","🛸","✈","🚁","🚢","🚗","🚕","🚙","🚌","🚇",
    "🏁","🏆","🎖","🥇","🥈","🥉","🎗","📊","📈","📉"
]

emoji_cycle = cycle(EMOJI_POOL)

# ===================== 固定模板 =====================

BASE_CONFIG = {
    "wallpaper": "https://imgs.catvod.com/",
    "logo": "https://cnb.cool/junchao.tang/jtv/-/git/raw/main/Pictures/junmeng.gif",
    "spider": "./jar/custom_spider.jpg",
    "sites": []
}

# ===================== 核心逻辑 =====================

def build_sites():
    files = [f for f in os.listdir(PY_DIR) if f.endswith(".py")]

    # 1️⃣ 按“剧透社”前缀分组
    priority_files = []
    normal_files = []

    for file in files:
        name = file[:-3]
        if name.startswith(PRIORITY_PREFIX):
            priority_files.append(file)
        else:
            normal_files.append(file)

    # 排序
    priority_files.sort()
    normal_files.sort()

    used_emojis = set()
    sites = []

    # 2️⃣ 剧透社系，永远最前
    for file in priority_files:
        sites.append(create_site(file, used_emojis))

    # 3️⃣ 其它站点
    for file in normal_files:
        sites.append(create_site(file, used_emojis))

    return sites


def create_site(file: str, used_emojis: set) -> dict:
    raw_name = file[:-3]
    emoji = get_unique_emoji(used_emojis)
    used_emojis.add(emoji)

    return {
        "key": raw_name,
        "name": f"{emoji}┃{raw_name}",
        "type": 3,
        "api": f"./py/{file}",
        "searchable": 1,
        "quickSearch": 0,
        "filterable": 0,
        "changeable": 0
    }


def get_unique_emoji(used: set) -> str:
    """
    优先返回未使用过的 Emoji
    Emoji 池真的用尽时，才允许重复
    """
    for _ in range(len(EMOJI_POOL)):
        e = next(emoji_cycle)
        if e not in used:
            return e
    return next(emoji_cycle)


# ===================== 主入口 =====================

if __name__ == "__main__":
    BASE_CONFIG["sites"] = build_sites()

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(BASE_CONFIG, f, ensure_ascii=False, indent=4)

    print(f"✅ 已生成 {OUTPUT}，共 {len(BASE_CONFIG['sites'])} 个 site")
