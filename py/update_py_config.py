#!/usr/bin/env python3
"""
智能Python配置更新器
只在py文件夹有增删文件时才运行，生成紧凑格式配置
"""

import os
import json
import hashlib
import logging
import sys
from pathlib import Path
from typing import Dict, List, Set, Any, Tuple

class SmartPyConfigUpdater:
    """智能配置更新器"""
    
    def __init__(self, py_folder: str = "./py", 
                 output_file: str = "./configs/plugins.json",
                 state_file: str = "py_state.json"):
        """
        初始化更新器
        
        Args:
            py_folder: Python文件目录
            output_file: 输出文件路径
            state_file: 状态文件路径，记录文件变化
        """
        self.py_folder = Path(py_folder)
        self.output_file = Path(output_file)
        self.state_file = Path(state_file)
        self.logger = self._setup_logging()
        
    def _setup_logging(self) -> logging.Logger:
        """配置日志系统"""
        logger = logging.getLogger("SmartPyConfigUpdater")
        logger.setLevel(logging.INFO)
        
        if logger.handlers:
            logger.handlers.clear()
        
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', 
                                     datefmt='%H:%M:%S')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def _get_file_hash(self, file_path: Path) -> str:
        """计算文件的MD5哈希值"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""
    
    def _scan_py_files(self) -> Dict[str, Tuple[str, str]]:
        """
        扫描py文件夹中的所有Python文件
        
        Returns:
            字典：文件名 -> (相对路径, 文件哈希)
        """
        self.logger.info(f"📁 扫描目录: {self.py_folder}")
        
        if not self.py_folder.exists():
            self.logger.warning(f"⚠️  Python目录不存在，创建目录")
            self.py_folder.mkdir(parents=True, exist_ok=True)
            return {}
        
        py_files = {}
        
        try:
            for root, dirs, files in os.walk(self.py_folder):
                # 跳过隐藏目录
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                
                for file in files:
                    if file.endswith('.py') and not file.startswith('.'):
                        file_path = Path(root) / file
                        rel_path = file_path.relative_to(self.py_folder)
                        base_name = Path(file).stem  # 去除.py后缀
                        
                        # 计算文件哈希
                        file_hash = self._get_file_hash(file_path)
                        
                        # 使用base_name作为键，避免重复
                        if base_name not in py_files:
                            py_files[base_name] = (str(rel_path), file_hash)
                            self.logger.debug(f"找到: {base_name} -> {rel_path}")
            
            self.logger.info(f"✅ 找到 {len(py_files)} 个Python文件")
            return py_files
            
        except Exception as e:
            self.logger.error(f"❌ 扫描文件时出错: {str(e)}")
            return {}
    
    def _load_previous_state(self) -> Dict[str, str]:
        """加载之前的状态"""
        if not self.state_file.exists():
            self.logger.info("🆕 首次运行，创建初始状态")
            return {}
        
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"❌ 读取状态文件失败: {str(e)}")
            return {}
    
    def _save_current_state(self, file_hashes: Dict[str, str]) -> bool:
        """保存当前状态"""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(file_hashes, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"💾 状态已保存到: {self.state_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 保存状态失败: {str(e)}")
            return False
    
    def has_files_changed(self) -> Tuple[bool, Dict[str, Tuple[str, str]]]:
        """
        检查py文件夹中的文件是否有变化
        
        Returns:
            (是否有变化, 当前文件信息)
        """
        # 扫描当前文件
        current_files = self._scan_py_files()
        
        if not current_files:
            self.logger.warning("⚠️  当前没有Python文件")
            # 提取文件名和哈希值
            file_hashes = {name: info[1] for name, info in current_files.items()}
            self._save_current_state(file_hashes)
            return False, current_files
        
        # 加载之前的状态
        previous_state = self._load_previous_state()
        
        # 提取当前文件的哈希值
        current_hashes = {name: info[1] for name, info in current_files.items()}
        
        # 比较变化
        current_names = set(current_hashes.keys())
        previous_names = set(previous_state.keys())
        
        added = current_names - previous_names
        removed = previous_names - current_names
        changed = set()
        
        # 检查哈希值变化
        for name in current_names.intersection(previous_names):
            if current_hashes[name] != previous_state.get(name):
                changed.add(name)
        
        if added:
            self.logger.info(f"➕ 新增文件: {', '.join(sorted(added))}")
        if removed:
            self.logger.info(f"➖ 删除文件: {', '.join(sorted(removed))}")
        if changed:
            self.logger.info(f"🔄 修改文件: {', '.join(sorted(changed))}")
        
        has_changes = bool(added or removed or changed)
        
        if has_changes:
            self.logger.info(f"📈 检测到 {len(added)+len(removed)+len(changed)} 个变化")
            # 保存新状态
            self._save_current_state(current_hashes)
        else:
            self.logger.info("✅ 没有检测到文件变化")
        
        return has_changes, current_files
    
    def generate_compact_config_item(self, name: str, rel_path: str) -> Dict[str, Any]:
        """
        生成紧凑格式的配置项
        
        Args:
            name: 文件名（不含.py）
            rel_path: 相对路径
        """
        # 统一路径格式
        api_path = f"./py/{rel_path.replace(os.sep, '/')}"
        
        # 紧凑格式：严格遵循指定格式
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
    
    def _format_json_compact(self, configs: List[Dict[str, Any]]) -> str:
        """将配置列表格式化为紧凑JSON字符串"""
        if not configs:
            return "[]"
        
        # 生成紧凑格式的配置项字符串
        config_strings = []
        for config in configs:
            # 使用紧凑格式序列化
            config_str = json.dumps(config, separators=(',', ':'), ensure_ascii=False)
            config_strings.append(config_str)
        
        # 组合成完整的JSON数组
        return "[\n  " + ",\n  ".join(config_strings) + "\n]"
    
    def generate_configs(self, py_files: Dict[str, Tuple[str, str]]) -> bool:
        """
        生成配置文件
        
        Args:
            py_files: Python文件信息字典
        """
        if not py_files:
            self.logger.warning("⚠️  没有Python文件可生成配置")
            return False
        
        # 生成配置项
        config_items = []
        
        # 按文件名排序，确保一致性
        sorted_names = sorted(py_files.keys())
        
        for name in sorted_names:
            rel_path, _ = py_files[name]
            config = self.generate_compact_config_item(name, rel_path)
            config_items.append(config)
            self.logger.info(f"📝 生成配置: {name}")
        
        # 确保输出目录存在
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 写入配置文件（紧凑格式）
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                # 使用自定义的紧凑格式化
                compact_json = self._format_json_compact(config_items)
                f.write(compact_json)
            
            self.logger.info(f"💾 配置已保存到: {self.output_file}")
            self.logger.info(f"📊 共生成 {len(config_items)} 个配置项")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 保存配置文件失败: {str(e)}")
            return False
    
    def run(self) -> bool:
        """运行更新流程"""
        self.logger.info("🔍 开始检查文件变化...")
        
        # 检查文件变化
        has_changes, py_files = self.has_files_changed()
        
        if not has_changes:
            self.logger.info("⏭️  没有变化，跳过配置生成")
            return True
        
        # 生成配置
        self.logger.info("🔄 文件有变化，开始生成配置...")
        success = self.generate_configs(py_files)
        
        if success:
            self.logger.info("✅ 配置生成完成！")
        else:
            self.logger.error("❌ 配置生成失败")
        
        return success


def main():
    """主函数入口"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="智能Python配置更新器 - 只在文件变化时运行",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python update_py_config.py                    # 基本使用
  python update_py_config.py --force            # 强制重新生成
  python update_py_config.py --verbose          # 详细日志
        """
    )
    
    parser.add_argument(
        '--py-folder',
        default='./py',
        help='Python文件目录（默认: ./py）'
    )
    
    parser.add_argument(
        '--output-file',
        default='./configs/plugins.json',
        help='输出配置文件（默认: ./configs/plugins.json）'
    )
    
    parser.add_argument(
        '--state-file',
        default='py_state.json',
        help='状态文件路径（默认: py_state.json）'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='强制重新生成配置，忽略状态检查'
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
    
    # 运行更新器
    updater = SmartPyConfigUpdater(
        py_folder=args.py_folder,
        output_file=args.output_file,
        state_file=args.state_file
    )
    
    if args.force:
        # 强制模式：清除状态文件，强制重新生成
        if Path(args.state_file).exists():
            Path(args.state_file).unlink()
            updater.logger.info("🧹 已清除状态文件，强制重新生成")
    
    success = updater.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
