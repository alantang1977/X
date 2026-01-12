import json
import os
import re

def load_py_json():
    """加载py.json配置文件"""
    try:
        with open("py.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("sites", [])
    except FileNotFoundError:
        print("错误：py.json文件不存在")
        return []
    except json.JSONDecodeError:
        print("错误：py.json格式无效")
        return []

def get_py_files():
    """获取py文件夹下的所有.py文件路径"""
    py_dir = "py"
    if not os.path.exists(py_dir):
        print("警告：py文件夹不存在")
        return []
    
    py_files = []
    for file in os.listdir(py_dir):
        if file.endswith(".py"):
            py_files.append(f"./py/{file}")
    return py_files

def format_site(site):
    """将site对象格式化为单行无缩进的JSON字符串"""
    # 移除多余的空格和换行，生成单行JSON
    formatted = json.dumps(site, ensure_ascii=False, separators=(",", ":"))
    return formatted

def generate_plugins_json():
    """生成最终的plugins.json文件"""
    # 1. 加载py.json的sites配置
    sites = load_py_json()
    if not sites:
        return
    
    # 2. 获取py文件夹下的py文件列表
    py_files = get_py_files()
    
    # 3. 过滤出py文件夹中存在的配置项（匹配api字段）
    valid_sites = []
    for site in sites:
        api = site.get("api", "")
        if api in py_files:
            # 只保留核心字段（可根据需要调整）
            core_site = {
                "key": site.get("key", ""),
                "name": site.get("name", ""),
                "type": site.get("type", 3),
                "api": api,
                "searchable": site.get("searchable", 0),
                "quickSearch": site.get("quickSearch", 0),
                "filterable": site.get("filterable", 0),
                "changeable": site.get("changeable", 0)
            }
            valid_sites.append(core_site)
    
    # 4. 格式化为单行JSON数组（每个元素单行，无缩进）
    # 最终生成：[{"key":"py_fk",...}, {"key":"py_xiong_di_ying_shi",...}]
    formatted_items = [format_site(site) for site in valid_sites]
    final_content = f"[{','.join(formatted_items)}]"
    
    # 5. 写入configs/plugins.json
    output_path = os.path.join("configs", "plugins.json")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_content)
    
    print(f"成功生成plugins.json，共{len(valid_sites)}个配置项")
    print(f"文件路径：{output_path}")

if __name__ == "__main__":
    generate_plugins_json()
