import os
import re
import json
import argparse
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
    """文件处理类，处理JSON和TXT文件"""
    
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
    
    def process_text_file(self, content: str) -> str:
        """处理文本文件中的Emoji"""
        return self.emoji_manager.replace_emojis(content)
    
    def process_file(self, input_path: Path, output_path: Path) -> None:
        """处理单个文件，区分JSON和TXT格式"""
        try:
            # 读取文件内容
            with open(input_path, 'r', encoding='utf-8') as f:
                if input_path.suffix.lower() == '.json':
                    # 处理JSON文件
                    content = json.load(f)
                    processed_content = self.process_json(content)
                    with open(output_path, 'w', encoding='utf-8') as out_f:
                        json.dump(processed_content, out_f, ensure_ascii=False, indent=2)
                elif input_path.suffix.lower() == '.txt':
                    # 处理TXT文件
                    content = f.read()
                    processed_content = self.process_text_file(content)
                    with open(output_path, 'w', encoding='utf-8') as out_f:
                        out_f.write(processed_content)
                else:
                    print(f"警告: 文件 '{input_path}' 不是JSON或TXT格式，跳过")
                    return
            
            print(f"已处理: {input_path} -> {output_path}")
            
        except Exception as e:
            print(f"处理文件 {input_path} 时出错: {str(e)}")

def process_files(input_dir: Path, output_dir: Path) -> None:
    """处理emojis文件夹下的JSON和TXT文件"""
    emoji_manager = EmojiManager()
    file_processor = FileProcessor(emoji_manager)
    
    # 创建输出目录
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 遍历emojis文件夹下的所有文件
    for root, _, files in os.walk(input_dir):
        for file in files:
            input_file = Path(root) / file
            
            # 检查文件是否为JSON或TXT格式
            if input_file.suffix.lower() not in ['.json', '.txt']:
                continue
                
            # 计算输出文件路径，保持目录结构
            relative_path = input_file.relative_to(input_dir)
            output_file = output_dir / relative_path
            
            # 确保输出目录存在
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 处理文件
            file_processor.process_file(input_file, output_file)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='处理emojis文件夹下的JSON和TXT文件')
    parser.add_argument('--input-dir', default='emojis', help='输入目录')
    parser.add_argument('--output-dir', default='emojis/output', help='输出目录')
    
    args = parser.parse_args()
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    
    if not input_dir.exists():
        print(f"错误: 输入目录 '{input_dir}' 不存在")
        return
    
    print(f"开始处理文件，输入目录: {input_dir}")
    process_files(input_dir, output_dir)
    print(f"处理完成! 结果保存在: {output_dir}")

if __name__ == "__main__":
    main()
