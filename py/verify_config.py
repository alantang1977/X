#!/usr/bin/env python3
"""
配置文件验证脚本
验证生成的plugins.json是否符合紧凑格式要求
"""

import json
import sys
from pathlib import Path

def verify_compact_format(file_path: str) -> bool:
    """
    验证配置文件是否符合紧凑格式要求
    
    Args:
        file_path: 配置文件路径
        
    Returns:
        是否符合要求
    """
    path = Path(file_path)
    
    if not path.exists():
        print(f"❌ 文件不存在: {file_path}")
        return False
    
    try:
        # 读取文件内容
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 解析JSON
        data = json.loads(content)
        
        print(f"✅ JSON格式正确")
        
        # 检查是否为数组
        if not isinstance(data, list):
            print("❌ 根元素不是数组")
            return False
        
        print(f"📊 配置项数量: {len(data)}")
        
        # 检查每个配置项
        for i, item in enumerate(data[:10]):  # 只检查前10个
            if not isinstance(item, dict):
                print(f"❌ 第{i+1}项不是字典")
                return False
            
            # 检查必需字段
            required_fields = ['key', 'name', 'type', 'api', 
                              'searchable', 'quickSearch', 'filterable', 'changeable']
            
            missing_fields = [field for field in required_fields if field not in item]
            if missing_fields:
                print(f"❌ 第{i+1}项缺少字段: {missing_fields}")
                return False
            
            # 检查字段值
            if item.get('type') != 3:
                print(f"❌ 第{i+1}项type不是3")
                return False
            
            if item.get('searchable') != 1:
                print(f"❌ 第{i+1}项searchable不是1")
                return False
            
            if item.get('quickSearch') != 0:
                print(f"❌ 第{i+1}项quickSearch不是0")
                return False
        
        # 检查格式是否为紧凑格式
        lines = content.strip().split('\n')
        if len(lines) < 3:
            print("⚠️  文件行数过少，可能不是紧凑格式")
            return True
        
        # 检查数组格式
        if not lines[0].strip().startswith('['):
            print("⚠️  第一行不是'['")
        
        if not lines[-1].strip().endswith(']'):
            print("⚠️  最后一行不是']'")
        
        # 检查每行配置
        for i, line in enumerate(lines[1:-1], 1):
            stripped = line.strip()
            if stripped.endswith(','):
                stripped = stripped[:-1]
            
            if stripped.startswith('{') and stripped.endswith('}'):
                # 尝试解析单行配置
                try:
                    json.loads(stripped)
                except:
                    print(f"⚠️  第{i+1}行不是有效的紧凑JSON: {stripped[:50]}...")
        
        print("✅ 紧凑格式验证通过")
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析错误: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ 验证时出错: {str(e)}")
        return False

def main():
    """主函数"""
    if len(sys.argv) > 1:
        files = sys.argv[1:]
    else:
        files = ["./configs/plugins.json"]
    
    all_success = True
    
    for file_path in files:
        print(f"\n🔍 验证文件: {file_path}")
        print("-" * 40)
        
        success = verify_compact_format(file_path)
        
        if not success:
            all_success = False
    
    print("\n" + "=" * 40)
    if all_success:
        print("✅ 所有文件验证通过！")
    else:
        print("❌ 部分文件验证失败")
    
    sys.exit(0 if all_success else 1)

if __name__ == "__main__":
    main()
