import hashlib
from collections import OrderedDict

def calculate_hash(content):
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def parse_template(template_file):
    return OrderedDict()

def parse_channels_auto(content):
    return OrderedDict()

def merge_channels(target, source):
    for k, v in source.items():
        if k in target:
            target[k].extend(v)
        else:
            target[k] = v

def merge_with_template(all_channels, template_channels):
    return all_channels

def deduplicate_and_alias_channels(channels_dict):
    return

def optimize_and_output_files(merged_channels, speed_map, output_folder):
    # 简单写入一个文件，避免主流程报错
    with open(f"{output_folder}/dummy.txt", "w") as f:
        f.write("dummy")
