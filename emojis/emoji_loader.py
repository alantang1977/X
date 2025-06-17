# emojis/emoji_loader.py

import os
import re
import requests

UNICODE_EMOJI_URL = "https://unicode.org/Public/emoji/15.1/emoji-test.txt"
LOCAL_EMOJI_FILE = "emojis/emoji-test.txt"

def download_emoji_file():
    os.makedirs(os.path.dirname(LOCAL_EMOJI_FILE), exist_ok=True)
    if not os.path.exists(LOCAL_EMOJI_FILE):
        print("Downloading emoji-test.txt from Unicode...")
        r = requests.get(UNICODE_EMOJI_URL)
        if r.status_code == 200:
            with open(LOCAL_EMOJI_FILE, "w", encoding="utf-8") as f:
                f.write(r.text)
        else:
            raise Exception("Failed to download emoji list.")

def parse_emoji_file(path):
    emojis = set()
    with open(path, encoding='utf-8') as f:
        for line in f:
            if line.startswith('#') or not line.strip():
                continue
            parts = line.split(';')
            if 'fully-qualified' in parts[1]:
                hex_values = parts[0].strip().split()
                emoji = ''.join(chr(int(h, 16)) for h in hex_values)
                emojis.add(emoji)
    return sorted(emojis)

def get_emoji_pool():
    download_emoji_file()
    return parse_emoji_file(LOCAL_EMOJI_FILE)
