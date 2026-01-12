#!/usr/bin/env python3
"""
自动生成TVBox配置文件
扫描py文件夹并生成配置
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

def scan_py_files(py_dir="py"):
    """扫描py文件夹，获取所有Python文件"""
    sites = []
    
    if not os.path.exists(py_dir):
        print(f"⚠️  警告: {py_dir} 文件夹不存在")
        return sites
    
    for file_path in Path(py_dir).glob("*.py"):
        file_name = file_path.stem  # 去除扩展名
        
        # 跳过以_开头的文件
        if file_name.startswith("_"):
            continue
            
        site_config = {
            "key": file_name,
            "name": file_name,
            "type": 3,
            "api": f"./py/{file_path.name}",
            "searchable": 1,
            "quickSearch": 0,
            "filterable": 0,
            "changeable": 0
        }
        
        # 特殊处理（根据需要添加）
        if "界影视" in file_name:
            site_config.update({
                "style": {
                    "type": "rect",
                    "ratio": 0.75
                },
                "changeable": 1
            })
            # 移除不需要的字段
            site_config.pop("searchable", None)
            site_config.pop("quickSearch", None)
            site_config.pop("filterable", None)
        
        sites.append(site_config)
    
    return sites

def generate_config(output_file="tvbox_config.json"):
    """生成完整的配置文件"""
    
    # 基础配置模板
    config = {
        "wallpaper": "https://imgs.catvod.com/",
        "logo": "https://cnb.cool/junchao.tang/jtv/-/git/raw/main/Pictures/junmeng.gif",
        "spider": "./jar/custom_spider.jpg",
        "sites": scan_py_files(),
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
            {
                "name": "解析聚合",
                "type": 3,
                "url": "Web"
            },
            {
                "name": "777",
                "type": 0,
                "url": "https://www.huaqi.live/?url="
            },
            {
                "name": "jsonplayer",
                "type": 0,
                "url": "https://jx.jsonplayer.com/player/?url="
            },
            {
                "name": "xmflv",
                "type": 0,
                "url": "https://jx.xmflv.com/?url="
            }
        ],
        "flags": [
            "youku", "tudou", "qq", "qiyi", "iqiyi", "leshi", "letv",
            "sohu", "imgo", "mgtv", "bilibili", "pptv", "PPTV", "migu"
        ],
        "doh": [
            {
                "name": "Google",
                "url": "https://dns.google/dns-query",
                "ips": ["8.8.4.4", "8.8.8.8"]
            },
            {
                "name": "Cloudflare",
                "url": "https://cloudflare-dns.com/dns-query",
                "ips": ["1.1.1.1", "1.0.0.1", "2606:4700:4700::1111", "2606:4700:4700::1001"]
            },
            {
                "name": "AdGuard",
                "url": "https://dns.adguard.com/dns-query",
                "ips": ["94.140.14.140", "94.140.14.141"]
            },
            {
                "name": "DNSWatch",
                "url": "https://resolver2.dns.watch/dns-query",
                "ips": ["84.200.69.80", "84.200.70.40"]
            },
            {
                "name": "Quad9",
                "url": "https://dns.quad9.net/dns-query",
                "ips": ["9.9.9.9", "149.112.112.112"]
            }
        ],
        "_meta": {
            "generated_at": datetime.now().isoformat(),
            "generator": "TVBox Config Generator"
        }
    }
    
    # 写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    # 生成压缩版
    minified_file = output_file.replace('.json', '.min.json')
    with open(minified_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, separators=(',', ':'))
    
    print(f"✅ 配置文件已生成:")
    print(f"   - {output_file}")
    print(f"   - {minified_file}")
    print(f"📊 共扫描到 {len(config['sites'])} 个站点")
    
    return config

if __name__ == "__main__":
    generate_config()
