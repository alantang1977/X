
import os
import re
import json
import shutil
from pathlib import Path
from typing import Dict, List, Set

# 完整的Emoji表情集合（兼容安卓）
EMOJI_POOL = [
    "😀", "😃", "😄", "😁", "😆", "😅", "😂", "🤣", "😊", "😇",
    "🙂", "🙃", "😉", "😌", "😍", "🥰", "😘", "😗", "😙", "😚",
    "😋", "😛", "😝", "😜", "🤪", "🤨", "🧐", "🤓", "😎", "🥸",
    "🤩", "🥳", "😏", "😒", "😞", "😔", "😟", "😕", "🙁", "☹️",
    "😣", "😖", "😫", "😩", "🥺", "😢", "😭", "😤", "😠", "😡",
    # 更多emoji...
]

class EmojiManager:
    def __init__(self, input_dir: str):
        self.input_dir = Path(input_dir)
        self.output_dir = self.input_dir / "output"
        self.emoji_map: Dict[str, str] = {}
        self.used_emojis: Set[str] = set()
        
        if not self.input_dir.exists():
            raise FileNotFoundError(f"输入目录不存在: {input_dir}")
            
        self.output_dir.mkdir(exist_ok=True)

    def _extract_emojis(self, text: str) -> List[str]:
        """使用正则表达式提取所有emoji"""
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F700-\U0001F77F"  # alchemical symbols
            "\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
            "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
            "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
            "\U0001FA00-\U0001FA6F"  # Chess Symbols
            "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
            "\U00002702-\U000027B0"  # Dingbats
            "\U000024C2-\U0001F251" 
            "]+",
            flags=re.UNICODE
        )
        return emoji_pattern.findall(text)

    def _get_replacement(self, original: str) -> str:
        """获取替换emoji（循环使用池）"""
        if original in self.emoji_map:
            return self.emoji_map[original]
            
        available = [e for e in EMOJI_POOL if e not in self.used_emojis]
        if not available:
            # 池用尽时重置使用记录
            self.used_emojis.clear()
            available = EMOJI_POOL.copy()
            
        replacement = available[0]
        self.emoji_map[original] = replacement
        self.used_emojis.add(replacement)
        return replacement

    def _process_text(self, text: str) -> str:
        """处理文本中的emoji"""
        emojis = self._extract_emojis(text)
        for emoji in emojis:
            replacement = self._get_replacement(emoji)
            text = text.replace(emoji, replacement)
        return text

    def _process_json(self, file_path: Path) -> dict:
        """处理JSON文件并保持结构"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        def process_item(item):
            if isinstance(item, str):
                return self._process_text(item)
            elif isinstance(item, dict):
                return {k: process_item(v) for k, v in item.items()}
            elif isinstance(item, list):
                return [process_item(i) for i in item]
            return item
            
        return process_item(data)

    def process_file(self, file_path: Path):
        """处理单个文件"""
        rel_path = file_path.relative_to(self.input_dir)
        output_path = self.output_dir / rel_path.with_suffix('.json')
        
        if file_path.suffix.lower() == '.json':
            processed = self._process_json(file_path)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(processed, f, ensure_ascii=False, indent=2)
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            processed = self._process_text(content)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump({"content": processed}, f, ensure_ascii=False, indent=2)

    def run(self):
        """处理目录下所有支持的文件"""
        supported_ext = ['.json', '.txt', '.md', '.csv', '.xml', '.html']
        for ext in supported_ext:
            for file_path in self.input_dir.rglob(f'*{ext}'):
                try:
                    self.process_file(file_path)
                    print(f"处理完成: {file_path}")
                except Exception as e:
                    print(f"处理失败 {file_path}: {str(e)}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("用法: python emoji_manager.py <输入目录>")
        sys.exit(1)
        
    manager = EmojiManager(sys.argv[1])
    manager.run()
