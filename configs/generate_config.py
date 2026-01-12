#!/usr/bin/env python3
"""
Python文件索引生成器 - 优化版
功能：扫描指定目录下的所有.py文件，生成结构化JSON索引
特点：将相同或相似名称的文件分组排列，支持GitHub Actions自动化
"""

import os
import json
import sys
import logging
import difflib
from pathlib import Path
from datetime import datetime
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
        
        # 配置文件模板
        self.config_template = {
            "type": 3,
            "searchable": 1,
            "quickSearch": 1,
            "changeable": 1,
            "filterable": 1,
            "timeout": 60
        }
    
    def _setup_logging(self) -> logging.Logger:
        """配置日志系统"""
        logger = logging.getLogger("PyIndexGenerator")
        logger.setLevel(logging.INFO)
        
        # 避免重复添加handler
        if not logger.handlers:
            # 控制台输出
            console_handler = logging.StreamHandler(sys.stdout)
            console_formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
            
            # 文件日志
            log_file = Path("configs") / "generate_config.log"
            log_file.parent.mkdir(exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        
        return logger
    
    def _calculate_similarity(self, name1: str, name2: str) -> float:
        """
        计算两个字符串的相似度（0-1之间）
        
        Args:
            name1: 第一个字符串
            name2: 第二个字符串
        
        Returns:
            相似度分数
        """
        return difflib.SequenceMatcher(None, name1.lower(), name2.lower()).ratio()
    
    def _group_similar_names(self, file_list: List[Tuple[str, str]]) -> List[List[Tuple[str, str]]]:
        """
        将文件按名称相似度分组
        
        Args:
            file_list: 文件列表，每个元素为(文件名, 相对路径)
        
        Returns:
            分组后的文件列表
        """
        if not file_list:
            return []
        
        # 按名称排序作为基础
        sorted_files = sorted(file_list, key=lambda x: x[0])
        
        groups = []
        current_group = [sorted_files[0]]
        
        for i in range(1, len(sorted_files)):
            current_name = sorted_files[i][0]
            last_name = current_group[-1][0]
            
            # 计算相似度
            similarity = self._calculate_similarity(current_name, last_name)
            
            # 如果相似度高于阈值，或文件名有相同前缀，则归为一组
            if (similarity > 0.4 or 
                current_name.split('_')[0] == last_name.split('_')[0] or
                current_name.startswith(last_name.split('_')[0]) or
                last_name.startswith(current_name.split('_')[0])):
                current_group.append(sorted_files[i])
            else:
                groups.append(current_group)
                current_group = [sorted_files[i]]
        
        if current_group:
            groups.append(current_group)
        
        # 按组的大小和名称排序（大组优先，然后按首字母排序）
        groups.sort(key=lambda g: (-len(g), g[0][0].lower()))
        
        return groups
    
    def _collect_py_files(self) -> List[Tuple[str, str, str]]:
        """
        收集所有Python文件
        
        Returns:
            文件信息列表，每个元素为(基础名, 相对路径, 完整路径)
        """
        self.logger.info(f"开始扫描目录: {self.input_folder}")
        
        if not self.input_folder.exists():
            self.logger.error(f"输入目录不存在: {self.input_folder}")
            raise FileNotFoundError(f"输入目录不存在: {self.input_folder}")
        
        py_files = []
        
        for root, dirs, files in os.walk(self.input_folder):
            # 跳过以点开头的隐藏目录
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                if file.endswith('.py') and not file.startswith('.'):
                    file_path = Path(root) / file
                    rel_path = file_path.relative_to(self.input_folder)
                    base_name = file_path.stem  # 去掉扩展名的文件名
                    
                    py_files.append((base_name, str(rel_path), str(file_path)))
        
        self.logger.info(f"找到 {len(py_files)} 个Python文件")
        return py_files
    
    def _generate_config_item(self, base_name: str, rel_path: str) -> Dict[str, Any]:
        """
        生成单个文件的配置项
        
        Args:
            base_name: 文件名（不含扩展名）
            rel_path: 相对路径
        
        Returns:
            配置字典
        """
        # 统一路径格式（确保使用正斜杠）
        api_path = f"./py/{rel_path.replace(os.sep, '/')}"
        
        config_item = {
            "key": base_name,
            "name": base_name,
            "api": api_path,
            **self.config_template
        }
        
        return config_item
    
    def generate_index(self) -> List[Dict[str, Any]]:
        """
        生成索引配置
        
        Returns:
            排序和分组后的配置列表
        """
        # 收集所有Python文件
        py_files = self._collect_py_files()
        
        if not py_files:
            self.logger.warning("未找到任何Python文件")
            return []
        
        # 准备分组数据
        file_pairs = [(base_name, rel_path) for base_name, rel_path, _ in py_files]
        
        # 按相似度分组
        groups = self._group_similar_names(file_pairs)
        
        # 生成配置项并保持分组顺序
        config_items = []
        
        self.logger.info(f"将文件分为 {len(groups)} 个相似组")
        
        for i, group in enumerate(groups):
            group_size = len(group)
            group_names = [name for name, _ in group]
            
            self.logger.info(f"第 {i+1} 组 ({group_size}个文件): {', '.join(group_names[:3])}{'...' if group_size > 3 else ''}")
            
            # 为组内文件生成配置项
            for base_name, rel_path in group:
                config_item = self._generate_config_item(base_name, rel_path)
                config_items.append(config_item)
            
            # 在组之间添加分隔注释（通过特殊标记项实现）
            if i < len(groups) - 1:
                config_items.append({
                    "key": f"__group_separator_{i}__",
                    "name": f"--- 相似文件组 {i+1} ({len(group)}个文件) ---",
                    "type": -1,  # 特殊类型，表示分隔符
                    "api": "",
                    "searchable": 0,
                    "quickSearch": 0,
                    "changeable": 0,
                    "filterable": 0,
                    "timeout": 0
                })
        
        self.logger.info(f"共生成 {len(config_items)} 个配置项")
        
        return config_items
    
    def save_index(self, config_items: List[Dict[str, Any]]) -> bool:
        """
        保存索引到JSON文件
        
        Args:
            config_items: 配置项列表
        
        Returns:
            成功返回True，失败返回False
        """
        try:
            # 确保输出目录存在
            self.output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 过滤掉分隔符项（如果需要纯净的配置）
            clean_items = [item for item in config_items if item.get("type") != -1]
            
            # 保存到文件
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(clean_items, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"配置已保存到: {self.output_file}")
            self.logger.info(f"有效配置项: {len(clean_items)} 个")
            
            # 同时保存带注释的版本（便于调试）
            debug_file = self.output_file.with_name(f"plugins_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            with open(debug_file, 'w', encoding='utf-8') as f:
                json.dump(config_items, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"调试版本已保存到: {debug_file}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"保存配置时出错: {str(e)}", exc_info=True)
            return False
    
    def run(self) -> bool:
        """运行索引生成流程"""
        self.logger.info("=" * 60)
        self.logger.info("开始生成Python文件索引")
        self.logger.info(f"输入目录: {self.input_folder}")
        self.logger.info(f"输出文件: {self.output_file}")
        self.logger.info("=" * 60)
        
        try:
            # 生成索引
            config_items = self.generate_index()
            
            if not config_items:
                self.logger.warning("未生成任何配置项，跳过保存")
                return False
            
            # 保存索引
            success = self.save_index(config_items)
            
            if success:
                self.logger.info("索引生成完成！")
            else:
                self.logger.error("索引生成失败！")
            
            return success
            
        except Exception as e:
            self.logger.error(f"索引生成过程中出错: {str(e)}", exc_info=True)
            return False


def main():
    """主函数：处理命令行参数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="生成Python文件索引JSON配置",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python generate_config.py                    # 使用默认配置
  python generate_config.py -i ./plugins      # 指定输入目录
  python generate_config.py -o ./output.json  # 指定输出文件
  python generate_config.py -i ./src -o ./config/plugins.json  # 完全自定义
        """
    )
    
    parser.add_argument(
        '-i', '--input',
        default='./py',
        help='Python文件所在目录（默认: ./py）'
    )
    
    parser.add_argument(
        '-o', '--output',
        default='./configs/plugins.json',
        help='输出JSON文件路径（默认: ./configs/plugins.json）'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='显示详细日志信息'
    )
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 创建并运行生成器
    generator = PythonFileIndexGenerator(args.input, args.output)
    success = generator.run()
    
    # 返回退出码
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
