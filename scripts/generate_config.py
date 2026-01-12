import os
import json
from collections import defaultdict

# ===================== 基础配置 =====================

PY_DIR = "py"
OUTPUT = "config.json"

# ===================== Emoji 分类池 =====================

EMOJI_POOLS = [
    {
        "keywords": ["剧透", "AI", "智能"],
        "emojis": ["🤖", "🧠", "👁️"]
    },
    {
        "keywords": ["电影", "影视", "猎手", "影院"],
        "emojis": ["🎬", "🍿", "📽️"]
    },
    {
        "keywords": ["飞快", "快", "秒播"],
        "emojis": ["⚡", "🚀", "💨"]
    },
    {
        "keywords": ["TV", "电视", "直播"],
        "emojis": ["📺", "📡", "🛰️"]
    },
    {
        "keywords": ["海外", "国际", "global"],
        "emojis": ["🌐", "🗺️", "✈️"]
    }
]

DEFAULT_EMOJIS = ["📦", "📁", "🧩"]

# ===================== 内部状态（防重复） =====================

emoji_index = defaultdict(int)

# ===================== 固定模板 =====================

BASE_CONFIG = {
    "wallpaper": "https://imgs.catvod.com/",
    "logo": "https://cnb.cool/junchao.tang/jtv/-/git/raw/main/Pictures/junmeng.gif",
    "spider": "./jar/custom_spider.jpg",
    "sites": []
}

# ===================== 核心逻辑 =====================

def pick_emoji(name: str) -> str:
    """
    根据名称关键字选择 Emoji，并在同分类中轮换，尽量避免重复
    """
    lname = name.lower()

    for group in EMOJI_POOLS:
        if any(k.lower() in lname for k in group["keywords"]):
            idx = emoji_index[id(group)] % len(group["emojis"])
            emoji_index[id(group)] += 1
            return group["emojis"][idx]

    # 默认兜底 Emoji
    idx = emoji_index["default"] % len(DEFAULT_EMOJIS)
    emoji_index["default"] += 1
    return DEFAULT_EMOJIS[idx]


def build_sites():
    files = sorted(f for f in os.listdir(PY_DIR) if f.endswith(".py"))
    sites = []

    for file in files:
        raw_name = file[:-3]
        emoji = pick_emoji(raw_name)

        sites.append({
            "key": raw_name,
            "name": f"{emoji}┃{raw_name}",
            "type": 3,
            "api": f"./py/{file}",
            "searchable": 1,
            "quickSearch": 0,
            "filterable": 0,
            "changeable": 0
        })

    return sites


# ===================== 主入口 =====================

if __name__ == "__main__":
    BASE_CONFIG["sites"] = build_sites()

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(BASE_CONFIG, f, ensure_ascii=False, indent=4)

    print(f"✨ 已生成 {OUTPUT}，共 {len(BASE_CONFIG['sites'])} 个 site")
