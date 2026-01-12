import os
import json

PY_DIR = "py"
OUTPUT = "config.json"
PRIORITY_FILE = "剧透.py"

BASE_CONFIG = {
    "wallpaper": "https://imgs.catvod.com/",
    "logo": "https://cnb.cool/junchao.tang/jtv/-/git/raw/main/Pictures/junmeng.gif",
    "spider": "./jar/custom_spider.jpg",
    "sites": [],
    "headers": [
        {
            "host": "mgtv.ottiptv.cc",
            "header": {
                "User-Agent": "okHttp/Mod-1.4.0.0",
                "Referer": "https://mgtv.ottiptv.cc/"
            }
        }
    ],
    "lives": [
        {
            "name": "冰茶",
            "type": 0,
            "playerType": 2,
            "url": "https://fy.188766.xyz/?ip=&mima=mianfeidehaimaiqian&json=true",
            "ua": "bingcha/1.1(mianfeifenxiang)"
        }
    ],
    "parses": [
        {"name": "解析聚合", "type": 3, "url": "Web"},
        {"name": "777", "type": 0, "url": "https://www.huaqi.live/?url="},
        {"name": "jsonplayer", "type": 0, "url": "https://jx.jsonplayer.com/player/?url="},
        {"name": "xmflv", "type": 0, "url": "https://jx.xmflv.com/?url="}
    ],
    "flags": [
        "youku","tudou","qq","qiyi","iqiyi","leshi","letv",
        "sohu","imgo","mgtv","bilibili","pptv","PPTV","migu"
    ],
    "doh": [
        {
            "name": "Google",
            "url": "https://dns.google/dns-query",
            "ips": ["8.8.4.4", "8.8.8.8"]
        }
    ]
}


def build_sites():
    files = [
        f for f in os.listdir(PY_DIR)
        if f.endswith(".py")
    ]

    sites = []

    # 1️⃣ 剧透.py 永远第一
    if PRIORITY_FILE in files:
        files.remove(PRIORITY_FILE)
        sites.append(create_site(PRIORITY_FILE))

    # 2️⃣ 其余文件按排序追加
    for file in sorted(files):
        sites.append(create_site(file))

    return sites


def create_site(file):
    name = file[:-3]

    site = {"key": name,"name": name,"type": 3,"api": f"./py/{file}","searchable": 1,"quickSearch": 0,"filterable": 0,"changeable": 0}

    # 示例：单独定制
    if name == "界影视":
        site["style"] = {"type": "rect", "ratio": 0.75}
        site["changeable"] = 1

    return site


if __name__ == "__main__":
    BASE_CONFIG["sites"] = build_sites()

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(BASE_CONFIG, f, ensure_ascii=False, indent=4)

    print(f"✅ 已生成 {OUTPUT}，共 {len(BASE_CONFIG['sites'])} 个 site")
