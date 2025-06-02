import os
import hashlib
from collections import OrderedDict

def calculate_hash(content):
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def parse_template(template_file):
    """
    解析demo.txt，返回结构：
    OrderedDict{
        分类: [(频道名, url), ...]
    }
    """
    template_channels = OrderedDict()
    current_category = None
    if not os.path.exists(template_file):
        return template_channels
    with open(template_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):  # 跳过注释和空行
                continue
            if line.startswith('[') and line.endswith(']'):
                current_category = line[1:-1].strip()
                if current_category not in template_channels:
                    template_channels[current_category] = []
            elif ',' in line and current_category:
                channel_name, url = line.split(',', 1)
                template_channels[current_category].append((channel_name.strip(), url.strip()))
            elif current_category:
                # 兼容只有频道名没有url的格式
                template_channels[current_category].append((line.strip(), ''))
    return template_channels

def parse_channels_auto(content):
    """
    支持解析m3u和txt格式
    返回结构：OrderedDict{ 分类: {频道名: [url, ...], ...}, ... }
    """
    import re
    channels = OrderedDict()
    current_category = "未分组"
    lines = content.splitlines()
    last_name = None
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#EXTM3U'):
            continue
        if line.startswith('#EXTINF:'):
            # m3u频道名
            m = re.match(r'.*?,(.+)', line)
            last_name = m.group(1).strip() if m else None
        elif line.startswith('http'):
            if last_name:
                if current_category not in channels:
                    channels[current_category] = OrderedDict()
                if last_name not in channels[current_category]:
                    channels[current_category][last_name] = []
                channels[current_category][last_name].append(line)
            last_name = None
        elif line.startswith('[') and line.endswith(']'):
            current_category = line[1:-1].strip()
        elif ',' in line:
            # txt格式
            channel_name, url = line.split(',', 1)
            if current_category not in channels:
                channels[current_category] = OrderedDict()
            channel_name = channel_name.strip()
            if channel_name not in channels[current_category]:
                channels[current_category][channel_name] = []
            channels[current_category][channel_name].append(url.strip())
    return channels

def merge_channels(target, source):
    """
    target, source: OrderedDict{分类: {频道名: [url, ...], ...}, ... }
    合并source到target
    """
    for category, chans in source.items():
        if category not in target:
            target[category] = OrderedDict()
        for name, urls in chans.items():
            if name not in target[category]:
                target[category][name] = []
            target[category][name].extend(urls)

def merge_with_template(all_channels, template_channels):
    """
    保证模板里的频道分类结构优先。
    返回合并后的 OrderedDict{分类: {频道名: [url, ...], ...}, ...}
    """
    merged = OrderedDict()
    # 先用模板顺序
    for category, chans in template_channels.items():
        merged[category] = OrderedDict()
        for channel_name, _ in chans:
            # 尝试在all_channels里找同名频道
            found = False
            for cat, chs in all_channels.items():
                if channel_name in chs:
                    merged[category][channel_name] = list(set(chs[channel_name]))
                    found = True
                    break
            if not found:
                merged[category][channel_name] = []
    return merged

def deduplicate_and_alias_channels(merged_channels):
    """
    简单去重（url去重），可扩展为别名逻辑
    """
    for category in merged_channels:
        for name in merged_channels[category]:
            if isinstance(merged_channels[category][name], list):
                merged_channels[category][name] = list(OrderedDict.fromkeys(merged_channels[category][name]))

def optimize_and_output_files(merged_channels, speed_map, output_folder):
    """
    按测速结果排序并输出m3u和txt，最终只保留模板里的频道和分类
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder, exist_ok=True)
    # 输出txt
    txt_path = os.path.join(output_folder, "output.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        for category, chans in merged_channels.items():
            if not chans: continue
            f.write(f'[{category}]\n')
            for channel_name, urls in chans.items():
                if not urls: continue
                # 按测速升序
                urls_sorted = sorted(urls, key=lambda u: speed_map.get(u, (float('inf'), False))[0])
                for url in urls_sorted:
                    f.write(f"{channel_name},{url}\n")
    # 输出m3u
    m3u_path = os.path.join(output_folder, "output.m3u")
    with open(m3u_path, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for category, chans in merged_channels.items():
            if not chans: continue
            f.write(f"#------ {category} ------\n")
            for channel_name, urls in chans.items():
                if not urls: continue
                urls_sorted = sorted(urls, key=lambda u: speed_map.get(u, (float('inf'), False))[0])
                for url in urls_sorted:
                    f.write(f'#EXTINF:-1 group-title="{category}",{channel_name}\n')
                    f.write(f"{url}\n")
