import os
import re
import json
from pathlib import Path

EMOJI_POOL = [
    "😀", "😃", "😄", "😁", "😆", "😅", "😂", "🤣", "😊", "😇",
    "🙂", "🙃", "😉", "😌", "😍", "🥰", "😘", "😗", "😙", "😚",
    "😋", "😛", "😝", "😜", "🤪", "🤨", "🧐", "🤓", "😎", "🥸"
]

def extract_emojis(text):
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

def build_emoji_map(unique_emojis):
    pool = EMOJI_POOL
    mapping = {}
    n = len(pool)
    for i, e in enumerate(unique_emojis):
        mapping[e] = pool[i % n]
    return mapping

def replace_emojis(text, emoji_map):
    def _repl(match):
        return emoji_map.get(match.group(0), match.group(0))
    pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "]+", 
        flags=re.UNICODE
    )
    return pattern.sub(_repl, text)

def process_json(obj, emoji_map):
    if isinstance(obj, str):
        return replace_emojis(obj, emoji_map)
    elif isinstance(obj, list):
        return [process_json(item, emoji_map) for item in obj]
    elif isinstance(obj, dict):
        return {k: process_json(v, emoji_map) for k,v in obj.items()}
    else:
        return obj

def process_file(filepath, output_dir):
    suffix = filepath.suffix.lower()
    if suffix not in {'.json', '.txt', '.md', '.csv', '.xml', '.html'}:
        return

    content = filepath.read_text(encoding='utf-8')
    file_emojis = set(extract_emojis(content))
    if not file_emojis:
        return

    emoji_map = build_emoji_map(sorted(file_emojis))

    if suffix == '.json':
        try:
            data = json.loads(content)
            new_data = process_json(data, emoji_map)
            output_content = json.dumps(new_data, ensure_ascii=False, indent=2)
        except Exception as e:
            output_content = json.dumps({"content": replace_emojis(content, emoji_map)}, ensure_ascii=False, indent=2)
    else:
        output_content = json.dumps({"content": replace_emojis(content, emoji_map)}, ensure_ascii=False, indent=2)

    output_path = output_dir / (filepath.stem + '.json')
    output_path.write_text(output_content, encoding='utf-8')

def main(input_dir):
    input_dir = Path(input_dir)
    output_dir = input_dir / "output"
    if output_dir.exists():
        for f in output_dir.iterdir():
            if f.is_file():
                f.unlink()
    else:
        output_dir.mkdir(parents=True, exist_ok=True)
    for file in input_dir.iterdir():
        if file.is_file():
            process_file(file, output_dir)

if __name__ == "__main__":
    import sys
    input_dir = sys.argv[1] if len(sys.argv) > 1 else "emojis"
    main(input_dir)
