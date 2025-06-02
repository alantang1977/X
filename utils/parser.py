"""
解析工具模块
包含模板解析、输入源解析等功能
"""
import re
from config import URL_BLACKLIST, IP_VERSION_PRIORITY

def parse_template(template_path):
    """
    解析频道模板文件
    返回结构化的频道分类和名称列表
    """
    with open(template_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    
    categories = {}
    current_category = None
    
    for line in lines:
        if line.startswith("[") and line.endswith("]"):
            current_category = line[1:-1].strip()
            categories[current_category] = []
        else:
            if current_category:
                categories[current_category].append(line.strip())
    
    return categories

def parse_source_content(content, source_type):
    """
    解析不同格式的数据源内容（M3U/TXT）
    返回频道名称到URL列表的映射
    """
    channels = {}
    if source_type == "m3u":
        return _parse_m3u(content)
    elif source_type == "txt":
        return _parse_txt(content)
    return channels

def _parse_m3u(content):
    """解析M3U格式内容"""
    entries = content.split("#EXTINF:-1,")
    for entry in entries[1:]:  # 跳过第一个空元素
        parts = entry.split("\n", 1)
        channel_name = parts[0].strip()
        url = parts[1].strip()
        if not _is_blacklisted(url) and _has_valid_ip(url):
            _add_channel(channels, channel_name, url)
    return channels

def _parse_txt(content):
    """解析TXT格式内容（每行格式：频道名,URL）"""
    for line in content.splitlines():
        if "," in line:
            channel_name, url = line.split(",", 1)
            channel_name = channel_name.strip()
            url = url.strip()
            if not _is_blacklisted(url) and _has_valid_ip(url):
                _add_channel(channels, channel_name, url)
    return channels

def _add_channel(channels, name, url):
    """添加频道到映射，按IP版本分类"""
    ip_version = "IPV6" if "[" in url else "IPV4"  # 判断IPv6格式
    if name not in channels:
        channels[name] = {"IPV4": [], "IPV6": []}
    channels[name][ip_version].append(url)

def _is_blacklisted(url):
    """检查URL是否在黑名单中"""
    return any(bl in url for bl in URL_BLACKLIST)

def _has_valid_ip(url):
    """检查URL是否包含有效IP地址"""
    return re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b|\[([0-9a-fA-F:]+)\]", url) is not None
