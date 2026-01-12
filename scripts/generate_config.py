import os
import json

# ===================== 基础配置 =====================

PY_DIR = "py"
OUTPUT = "config.json"

# 优先级前缀（最高优先级，整体排最前）
PRIORITY_PREFIXES = [
    "剧透社"
]

# Emoji 分组规则（顺序即优先级）
EMOJI_GROUPS = [
    {
        "emoji": "🤖┃",
        "keywords": ["剧透社", "AI", "智能"]
    },
    {
        "emoji": "🎬┃",
        "keywords": ["影视", "电影", "影院"]
    },
    {
        "emoji": "⚡┃",
        "keywords": ["飞快", "快", "秒播"]
    },
    {
        "emoji": "📺┃",
        "keywords": ["TV", "电视", "直播"]
    },
    {
        "emoji": "🌐┃",
        "keywords": ["海外", "国际"]
    }
]

# ===================== 固定模板 =====================

BASE_CONFIG = {
    "wallpaper": "https://imgs.catvod.com/",
    "logo": "https://cnb.cool/junchao.tang/jtv/-/git/raw/main/Pictures/junmeng.gif",
    "spider": "./jar/custom_spider.jpg",
    "sites": []
}

# ===================== 核心逻辑 =====================

def build_sites():
    py_files = [f for f in os.listdir(PY_DIR) if f.endswith(".py")]

    priority_files = []
    normal_files = []

    # 1️⃣ 按优先前缀拆分
    for file in py_files:
        name = file[:-3]
        if any(name.startswith(p) for p in PRIORITY_PREFIXES):
            priority_files.append(file)
        else:
            normal_files.append(file)

    sites = []

    # 2️⃣ 优先组先输出
    for file in sorted(priority_files):
        sites.append(create_site(file))

    # 3️⃣ 普通组后输出
    for file in sorted(normal_files):
        sites.append(create_site(file))

    return sites


def decorate_name(raw_name: str) -> str:
    """
    根据关键字自动添加 Emoji 分组前缀
    """
    for group in EMOJI_GROUPS:
        for kw in group["keywords"]:
            if kw in raw_name:
                return f"{group['emoji']}{raw_name}"
    return raw_name


def create_site(file: str) -> dict:
    raw_name = file[:-3]

    return {
        "key": raw_name,
        "name": decorate_name(raw_name),
        "type": 3,
        "api": f"./py/{file}",
        "searchable": 1,
        "quickSearch": 0,
        "filterable": 0,
        "changeable": 0
    }


# ===================== 主入口 =====================

if __name__ == "__main__":
    BASE_CONFIG["sites"] = build_sites()

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(BASE_CONFIG, f, ensure_ascii=False, indent=4)

    print(f"✨ 已生成 {OUTPUT}，共 {len(BASE_CONFIG['sites'])} 个 site")
