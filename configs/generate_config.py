#!/usr/bin/env python3
"""
Python文件索引生成器 - 最终修复版
自动扫描py文件夹并生成格式化的JSON配置文件
"""

import os
import json
import sys
import logging
import difflib
from pathlib import Path
from typing import List, Dict, Tuple, Any

class PythonFileIndexGenerator:
    """Python文件索引生成器"""
    
    def __init__(self, input_folder: str = "./py", output_file: str = "./configs/plugins.json"):
        """
        初始化生成器
        
        Args:
            input_folder: 输入文件夹路径
            output_file: 输出JSON文件路径
        """
        self.input_folder = Path(input_folder)
        self.output_file = Path(output_file)
        self.logger = self._setup_logging()
        
    def _setup_logging(self) -> logging.Logger:
        """配置日志系统"""
        logger = logging.getLogger("PyIndexGenerator")
        logger.setLevel(logging.INFO)
        
        # 清除现有handlers避免重复
        logger.handlers.clear()
        
        # 控制台输出
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        return logger
    
    def _calculate_similarity(self, name1: str, name2: str) -> float:
        """
        计算两个字符串的相似度
        返回0-1之间的值，越高越相似
        """
        # 转换为小写比较
        name1_lower = name1.lower()
        name2_lower = name2.lower()
        
        # 如果完全相同
        if name1_lower == name2_lower:
            return 1.0
        
        # 使用SequenceMatcher计算相似度
        return difflib.SequenceMatcher(None, name1_lower, name2_lower).ratio()
    
    def _extract_name_prefix(self, name: str) -> str:
        """提取名称前缀（用于分组）"""
        # 去除常见的后缀
        suffixes = ['ai', 'bot', 'tool', 'utils', 'helper', 'assistant', 'test']
        
        name_lower = name.lower()
        for suffix in suffixes:
            if name_lower.endswith(suffix):
                # 检查是否有分隔符
                for sep in ['_', '-', ' ']:
                    if sep + suffix in name_lower:
                        return name_lower.split(sep + suffix)[0]
        
        # 按常见分隔符分割
        for sep in ['_', '-', ' ']:
            if sep in name:
                parts = name_lower.split(sep)
                if len(parts) > 1:
                    # 返回主要部分
                    return parts[0]
        
        return name_lower
    
    def _group_similar_files(self, files: List[Tuple[str, str]]) -> List[List[Tuple[str, str]]]:
        """
        将相似文件分组
        Args:
            files: 文件列表，每个元素为(文件名, 相对路径)
        Returns:
            分组后的文件列表
        """
        if not files:
            return []
        
        # 提取前缀并创建映射
        prefix_map = {}
        for name, path in files:
            prefix = self._extract_name_prefix(name)
            if prefix not in prefix_map:
                prefix_map[prefix] = []
            prefix_map[prefix].append((name, path))
        
        # 将分组转换为列表并排序
        groups = []
        for prefix, file_list in prefix_map.items():
            # 按文件名排序
            sorted_files = sorted(file_list, key=lambda x: x[0])
            
            # 如果组内文件需要进一步排序
            if len(sorted_files) > 1:
                # 将包含完整名称的文件放在前面
                sorted_files.sort(key=lambda x: (
                    x[0].lower() == prefix,  # 完全匹配前缀的在前
                    -len(x[0]),              # 名称长的在前（如"剧透社ai"在"剧透社"前）
                    x[0].lower()
                ))
            
            groups.append(sorted_files)
        
        # 按组的大小和名称排序
        groups.sort(key=lambda g: (
            -len(g),                    # 大组优先
            self._extract_name_prefix(g[0][0]),  # 按前缀字母排序
            g[0][0].lower()             # 按第一个文件名排序
        ))
        
        return groups
    
    def find_py_files(self) -> List[Tuple[str, str]]:
        """
        查找所有Python文件
        
        Returns:
            文件列表，每个元素为(文件名, 相对路径)
        """
        self.logger.info(f"扫描目录: {self.input_folder}")
        
        if not self.input_folder.exists():
            self.logger.error(f"目录不存在: {self.input_folder}")
            return []
        
        py_files = []
        
        try:
            # 遍历目录
            for root, dirs, files in os.walk(self.input_folder):
                # 跳过隐藏目录
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                
                for file in files:
                    if file.endswith('.py') and not file.startswith('.'):
                        file_path = Path(root) / file
                        rel_path = file_path.relative_to(self.input_folder)
                        base_name = Path(file).stem  # 去除.py后缀
                        
                        py_files.append((base_name, str(rel_path)))
                        
                        self.logger.debug(f"找到: {base_name} -> {rel_path}")
            
            self.logger.info(f"找到 {len(py_files)} 个Python文件")
            return py_files
            
        except Exception as e:
            self.logger.error(f"扫描文件时出错: {str(e)}")
            return []
    
    def generate_config_item(self, name: str, path: str) -> Dict[str, Any]:
        """
        生成单个文件的配置项
        
        Args:
            name: 文件名（不含.py）
            path: 相对路径
        
        Returns:
            配置字典
        """
        # 确保路径使用正斜杠
        api_path = f"./py/{path.replace(os.sep, '/')}"
        
        # 严格按照指定格式
        return {
            "key": name,
            "name": name,
            "type": 3,
            "api": api_path,
            "searchable": 1,
            "quickSearch": 0,
            "filterable": 0,
            "changeable": 0
        }
    
    def generate_json_config(self) -> List[Dict[str, Any]]:
        """生成完整的JSON配置"""
        # 查找所有文件
        files = self.find_py_files()
        
        if not files:
            self.logger.warning("未找到Python文件")
            return []
        
        # 按文件名排序
        files.sort(key=lambda x: x[0].lower())
        
        # 分组相似文件
        groups = self._group_similar_files(files)
        
        self.logger.info(f"创建了 {len(groups)} 个相似文件组")
        
        # 生成配置项
        config_items = []
        
        for group in groups:
            for name, path in group:
                config_item = self.generate_config_item(name, path)
                config_items.append(config_item)
                
                self.logger.info(f"添加: {name}")
        
        return config_items
    
    def save_to_file(self, config_data: List[Dict[str, Any]]) -> bool:
        """保存配置到文件"""
        try:
            # 确保输出目录存在
            self.output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入JSON文件
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"配置已保存到: {self.output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存文件失败: {str(e)}")
            return False
    
    def run(self) -> bool:
        """运行完整流程"""
        self.logger.info("开始生成Python文件索引...")
        
        # 生成配置
        config_data = self.generate_json_config()
        
        if not config_data:
            self.logger.error("未生成任何配置数据")
            return False
        
        # 保存文件
        success = self.save_to_file(config_data)
        
        if success:
            self.logger.info(f"成功生成 {len(config_data)} 个配置项")
        else:
            self.logger.error("生成配置失败")
        
        return success


def main():
    """主函数入口"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="生成Python文件索引配置",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python generate_config.py
  python generate_config.py -i ./my_py_files
  python generate_config.py -o ./output/plugins.json
        """
    )
    
    parser.add_argument(
        '-i', '--input',
        default='./py',
        help='Python文件目录（默认: ./py）'
    )
    
    parser.add_argument(
        '-o', '--output',
        default='./configs/plugins.json',
        help='输出JSON文件（默认: ./configs/plugins.json）'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='显示详细日志'
    )
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 运行生成器
    generator = PythonFileIndexGenerator(args.input, args.output)
    success = generator.run()
    
    # 返回退出码
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
