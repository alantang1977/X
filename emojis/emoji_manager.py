
import os
import re
import json
from pathlib import Path
from typing import Dict, List, Set

EMOJI_POOL = [
    "😀", "😃", "😄", "😁", "😆", "😅", "😂", "🤣", "😊", "😇",
    "🙂", "🙃", "😉", "😌", "😍", "🥰", "😘", "😗", "😙", "😚",
    "😋", "😛", "😝", "😜", "🤪", "🤨", "🧐", "🤓", "😎", "🥸"
]

class EmojiProcessor:
    def __init__(self, input_dir: str = "input"):
        self.input_dir = Path(input_dir)
        self.output_dir = self.input_dir.parent / "output"
        self.emoji_mapping: Dict[str, str] = {}
        
    def _extract_emojis(self, text: str) -> List[str]:
        pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"
            "\U0001F300-\U0001F5FF"
            "\U0001F680-\U0001F6FF"
            "\U0001F1E0-\U0001F1FF"
            "]+", 
            flags=re.UNICODE
        )
        return pattern.findall(text)
    
    def _get_replacement(self, emoji: str) -> str:
        if emoji not in self.emoji_mapping:
            idx = len(self.emoji_mapping) % len(EMOJI_POOL)
            self.emoji_mapping[emoji] = EMOJI_POOL[idx]
        return self.emoji_mapping[emoji]
    
    def process_file(self, file_path: Path):
        try:
            content = file_path.read_text(encoding='utf-8')
            emojis = set(self._extract_emojis(content))
            
            for emoji in emojis:
                content = content.replace(emoji, self._get_replacement(emoji))
                
            output_path = self.output_dir / f"{file_path.stem}.json"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            if file_path.suffix.lower() == '.json':
                json.dump(json.loads(content), output_path.open('w', encoding='utf-8'), 
                         ensure_ascii=False, indent=2)
            else:
                json.dump({"content": content}, output_path.open('w', encoding='utf-8'),
                         ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")
    
    def run(self):
        self.output_dir.mkdir(exist_ok=True)
        for ext in ['.json', '.txt', '.md', '.csv', '.xml', '.html']:
            for file in self.input_dir.rglob(f'*{ext}'):
                self.process_file(file)
        # Save mapping
        json.dump(self.emoji_mapping, 
                 (self.output_dir / 'emoji_mapping.json').open('w', encoding='utf-8'),
                 ensure_ascii=False, indent=2)

if __name__ == "__main__":
    EmojiProcessor().run()
