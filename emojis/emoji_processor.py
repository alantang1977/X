import os
import re
import json
import argparse
import chardet
from pathlib import Path
from typing import Dict, List, Union, Any

# Emoji 表情集合
EMOJI_POOL = [
    # 动物与自然
    '🐶', '🐱', '🐭', '🐹', '🐰', '🦊', '🐻', '🐼', '🐨', '🐯', 
    '🦁', '🐮', '🐷', '🐸', '🐵', '🐔', '🐧', '🐦', '🐤', '🐣', 
    '🌱', '🌲', '🌳', '🌴', '🌵', '🌼', '🌸', '🌹', '🌺', '🌻', 
    '🌍', '🌎', '🌏', '🌕', '🌖', '🌗', '🌘', '🌙', '🌚', '🌛', 
    '☀️', '⭐', '✨', '🌠', '☁️', '🌧️', '⛅', '❄️', '💦', '🔥',
    # 其他类别...（保持原有Emoji池不变）
]

# Emoji 正则表达式模式
EMOJI_REGEX = re.compile(
    r'[\U0001F300-\U0001F64F\U0001F680-\U0001F6FF\U0001F900-\U0001F9FF\U0001F1E0-\U0001F1FF]'
)

class EmojiManager:
    """Emoji表情管理类"""
    
    def __init__(self):
        self.emoji_pool = EMOJI_POOL
        self.emoji_index = 0
    
    def get_next_emoji(self) -> str:
        """获取下一个Emoji，池用尽时循环使用"""
        emoji = self.emoji_pool[self.emoji_index]
        self.emoji_index = (self.emoji_index + 1) % len(self.emoji_pool)
        return emoji
    
    def replace_emojis(self, text: str) -> str:
        """替换文本中的Emoji为新的Emoji"""
        if not text:
            return text
            
        unique_emojis = set(EMOJI_REGEX.findall(text))
        if not unique_emojis:
            return text
            
        emoji_mapping = {old_emoji: self.get_next_emoji() for old_emoji in unique_emojis}
        return EMOJI_REGEX.sub(lambda m: emoji_mapping.get(m.group(0), m.group(0)), text)

class FileProcessor:
    """文件处理类，智能识别并处理不同格式文件"""
    
    def __init__(self, emoji_manager: EmojiManager):
        self.emoji_manager = emoji_manager
    
    def process_json(self, content: Union[Dict, List]) -> Union[Dict, List]:
        """递归处理JSON内容中的Emoji"""
        if isinstance(content, dict):
            return {k: self.process_json(v) for k, v in content.items()}
        elif isinstance(content, list):
            return [self.process_json(item) for item in content]
        elif isinstance(content, str):
            return self.emoji_manager.replace_emojis(content)
        return content
    
    def process_text_file(self, content: str, input_path: Path) -> Dict[str, Any]:
        """处理文本文件中的Emoji"""
        return {
            "original_file": str(input_path),
            "content": self.emoji_manager.replace_emojis(content)
        }
    
    def is_valid_json(self, content_str: str) -> bool:
        """检查字符串是否为有效的JSON"""
        try:
            json.loads(content_str)
            return True
        except json.JSONDecodeError:
            return False
    
    def process_file(self, input_path: Path, output_path: Path) -> None:
        """处理单个文件，智能识别JSON格式"""
        try:
            # 检测文件编码
            with open(input_path, 'rb') as f:
                raw_data = f.read()
                encoding = chardet.detect(raw_data)['encoding'] or 'utf-8'
            
            content_str = raw_data.decode(encoding, errors='replace')
            
            # 智能识别JSON文件
            is_json = self.is_valid_json(content_str)
            
            if is_json:
                # 处理JSON文件（保持JSON格式）
                content = json.loads(content_str)
                processed_content = self.process_json(content)
                with open(output_path, 'w', encoding='utf-8') as out_f:
                    json.dump(processed_content, out_f, ensure_ascii=False, indent=2)
            else:
                # 处理非JSON文本文件
                processed_data = self.process_text_file(content_str, input_path)
                with open(output_path, 'w', encoding='utf-8') as out_f:
                    json.dump(processed_data, out_f, ensure_ascii=False, indent=2)
            
            print(f"已处理: {input_path} -> {output_path} ({'JSON' if is_json else '文本'})")
            
        except Exception as e:
            print(f"处理文件 {input_path} 时出错: {str(e)}")
            # 生成错误报告
            error_data = {
                "original_file": str(input_path),
                "error": str(e),
                "content": None
            }
            with open(output_path, 'w', encoding='utf-8') as out_f:
                json.dump(error_data, out_f, ensure_ascii=False, indent=2)

def process_files(target_files: List[str], input_dir: Path, output_dir: Path) -> None:
    """处理指定的目标文件"""
    emoji_manager = EmojiManager()
    file_processor = FileProcessor(emoji_manager)
    
    # 创建输出目录
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for file_name in target_files:
        input_file = input_dir / file_name
        if not input_file.exists():
            print(f"警告: 文件 '{input_file}' 不存在，跳过")
            continue
            
        if input_file.is_file():
            # 处理文件
            output_file = output_dir / (input_file.stem + '.json')
            file_processor.process_file(input_file, output_file)
        else:
            print(f"警告: '{input_file}' 不是文件，跳过")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='智能处理文件中的Emoji')
    parser.add_argument('--files', nargs='+', required=True, help='目标文件列表')
    parser.add_argument('--input-dir', default='emojis', help='输入目录')
    parser.add_argument('--output-dir', default='emojis/output', help='输出目录')
    
    args = parser.parse_args()
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    
    if not input_dir.exists():
        print(f"错误: 输入目录 '{input_dir}' 不存在")
        return
    
    print(f"开始处理文件，输入目录: {input_dir}")
    process_files(args.files, input_dir, output_dir)
    print(f"处理完成! 结果保存在: {output_dir}")

if __name__ == "__main__":
    main()    
