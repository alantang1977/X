import os
import json
import re
from pathlib import Path
from typing import List, Dict, Any

def normalize_key(name: str) -> str:
    """将站点名称转换为key格式"""
    # 移除特殊字符，保留中英文和数字
    key = re.sub(r'[^\w\u4e00-\u9fa5]', '_', name.strip())
    # 将连续的下划线替换为单个下划线
    key = re.sub(r'_+', '_', key)
    return key

def get_py_files(py_dir: str) -> List[str]:
    """获取py文件夹下所有.py文件"""
    py_files = []
    for file in os.listdir(py_dir):
        if file.endswith('.py'):
            py_files.append(file)
    return sorted(py_files)  # 排序确保一致性

def generate_site_config(py_file: str) -> Dict[str, Any]:
    """根据py文件名生成站点配置"""
    name = py_file.replace('.py', '').replace('.min', '')  # 移除.py和.min
    key = normalize_key(name)
    
    # 基础配置
    config = {
        "key": key,
        "name": name,
        "type": 3,
        "api": f"./py/{py_file}",
        "searchable": 1,
        "quickSearch": 1,
        "filterable": 1,
        "changeable": 1
    }
    
    # 特殊站点处理（根据原始py.json的配置）
    special_configs = {
        "飞快TV": {"key": "py_fk", "searchable": 1, "quickSearch": 0, "filterable": 0, "changeable": 0},
        "兄弟影视": {"key": "py_xiong_di_ying_shi", "searchable": 1, "quickSearch": 0, "filterable": 0, "changeable": 0},
        "哔哩直播": {"style": {"type": "rect", "ratio": 0.75}, "searchable": 0, "quickSearch": 0, "filterable": 0},
        "4KVM": {"style": {"type": "rect", "ratio": 0.75}, "searchable": 0, "quickSearch": 0, "filterable": 0},
        "小苹果": {"style": {"type": "rect", "ratio": 0.75}, "searchable": 0, "quickSearch": 0, "filterable": 0},
        "小鸡暴走": {"style": {"type": "rect", "ratio": 0.75}, "searchable": 0, "quickSearch": 0, "filterable": 0},
        "hohaiemby": {"ext": {"server": "https://emby.hohai.eu.org:443", "username": "chuxin666", "password": "ycc123456", "proxy": "", "thread": 0, "device_name": "My Computer", "client": "Hills Windows", "client_version": "0.2.2", "device_id": "a9f74849-83d5-4a28-8b85-a087af1402e3"}},
        "4K影视": {"style": {"type": "rect", "ratio": 0.75}, "searchable": 0, "quickSearch": 0, "filterable": 0},
        "HMDJ": {"style": {"type": "rect", "ratio": 0.75}, "searchable": 0, "quickSearch": 0, "filterable": 0},
        "LSYS": {"style": {"type": "rect", "ratio": 0.75}, "searchable": 0, "quickSearch": 0, "filterable": 0},
        "YYMP3音乐网": {"style": {"type": "rect", "ratio": 0.75}, "searchable": 0, "quickSearch": 0, "filterable": 0},
        "云端影视": {"style": {"type": "rect", "ratio": 0.75}, "searchable": 0, "quickSearch": 0, "filterable": 0},
        "优酷视频": {"style": {"type": "rect", "ratio": 0.75}, "searchable": 0, "quickSearch": 0, "filterable": 0},
        "剧王短剧": {"style": {"type": "rect", "ratio": 0.75}, "searchable": 0, "quickSearch": 0, "filterable": 0},
        "奇优动漫": {"style": {"type": "rect", "ratio": 0.75}, "searchable": 0, "quickSearch": 0, "filterable": 0},
        "柯南影视": {"style": {"type": "rect", "ratio": 0.75}, "searchable": 0, "quickSearch": 0, "filterable": 0},
        "永乐视频": {"style": {"type": "rect", "ratio": 0.75}, "searchable": 0, "quickSearch": 0, "filterable": 0},
        "爱瓜影视": {"style": {"type": "rect", "ratio": 0.75}, "searchable": 0, "quickSearch": 0, "filterable": 0},
        "猎手影视": {"style": {"type": "rect", "ratio": 0.75}, "searchable": 0, "quickSearch": 0, "filterable": 0},
        "甜圈短剧": {"style": {"type": "rect", "ratio": 0.75}, "searchable": 0, "quickSearch": 0, "filterable": 0},
        "电影猎手": {"style": {"type": "rect", "ratio": 0.75}, "searchable": 0, "quickSearch": 0, "filterable": 0},
        "界影视": {"style": {"type": "rect", "ratio": 0.75}, "searchable": 0, "quickSearch": 0, "filterable": 0}
    }
    
    # 应用特殊配置
    for special_name, special_settings in special_configs.items():
        if special_name in name:
            config.update(special_settings)
            break
    
    # 移除未设置的字段（保持整洁）
    if config.get("searchable") == 1 and config.get("quickSearch") == 1 and config.get("filterable") == 1 and config.get("changeable") == 1:
        # 如果都是默认值1，可以省略（根据原始格式选择是否省略）
        pass  # 这里选择保留，因为原始格式都包含
    
    return config

def group_sites_by_name(sites: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """按名称分组站点，相同名称的放在一起"""
    grouped = {}
    
    for site in sites:
        name = site["name"]
        if name not in grouped:
            grouped[name] = []
        grouped[name].append(site)
    
    # 展平并按名称排序
    result = []
    for name in sorted(grouped.keys()):
        result.extend(grouped[name])
    
    return result

def main():
    # 读取原始py.json作为模板
    with open('py.json', 'r', encoding='utf-8') as f:
        template = json.load(f)
    
    # 获取py文件夹中的所有.py文件
    py_dir = 'py'
    if not os.path.exists(py_dir):
        print(f"警告: {py_dir} 文件夹不存在")
        return
    
    py_files = get_py_files(py_dir)
    print(f"找到 {len(py_files)} 个.py文件: {py_files}")
    
    # 为每个.py文件生成配置
    sites = []
    for py_file in py_files:
        site_config = generate_site_config(py_file)
        sites.append(site_config)
    
    # 按名称分组排序
    sites = group_sites_by_name(sites)
    
    # 更新模板中的sites部分
    template["sites"] = sites
    
    # 写入plugins.json
    with open('plugins.json', 'w', encoding='utf-8') as f:
        json.dump(template, f, ensure_ascii=False, indent=4)
    
    print("✅ plugins.json 生成完成")

if __name__ == "__main__":
    main()
