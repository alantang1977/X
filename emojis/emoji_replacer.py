import json
import re
from pathlib import Path
from typing import Dict, List
import argparse

# 完整的安卓系统支持 Emoji 表情分类
ANDROID_EMOJI_CATEGORIES = {
    "人物和身体": [
        "👶","🧒","👦","👧","🧑","👨","👩","🧓","👴","👵",
        "👮","🦸","🧙","🚴","👨‍⚕️","👩‍⚕️","👨‍🎓","👩‍🎓","👨‍🏫","👩‍🏫",
        "👨‍⚖️","👩‍⚖️","👨‍🌾","👩‍🌾","👨‍🍳","👩‍🍳","👨‍🔧","👩‍🔧","👨‍🏭","👩‍🏭",
        "👨‍💼","👩‍💼","👨‍🔬","👩‍🔬","👨‍💻","👩‍💻","👨‍🎤","👩‍🎤","👨‍🎨","👩‍🎨",
        "👨‍✈️","👩‍✈️","👨‍🚀","👩‍🚀","👨‍🚒","👩‍🚒","🕵️","💂","🥷","👷",
        "🤴","👸","👳","👲","🧕","🤵","👰","🤰","🤱","👼",
        "💆","💇","🚶","🧍","🧎","🏃","💃","🕺","🕴️","👯",
        "🧖","🧗","🤺","🏇","⛷️","🏂","🏌️","🏄","🚣","🏊",
        "⛹️","🏋️","🚴","🚵","🤸","🤼","🤽","🤾","🤹","🧘",
        "🛀","🛌","👭","👫","👬","💏","💑","👪"
    ],
    "食物和饮料": [
        "🍏","🍎","🍐","🍊","🍋","🍌","🍉","🍇","🍓","🫐","🍈",
        "🍒","🍑","🥭","🍍","🥥","🥝","🍅","🍆","🥑","🥦","🥬",
        "🥒","🌶️","🫑","🌽","🥕","🫒","🥔","🍠","🥐","🥯","🍞",
        "🥖","🥨","🧀","🥚","🍳","🧈","🥞","🧇","🥓","🥩","🍗",
        "🍖","🌭","🍔","🍟","🍕","🫓","🥪","🥙","🌮","🌯","🫔",
        "🥗","🍝","🍜","🍲","🍛","🍣","🍱","🥟","🦪","🍤","🍙",
        "🍚","🍘","🍥","🥠","🥮","🍢","🍡","🍧","🍨","🍦","🥧",
        "🧁","🍰","🎂","🍮","🍭","🍬","🍫","🍿","🧋","🍩","🍪"
    ],
    "旅行和地点": [
        "🚗","🚕","🚙","🚌","🚎","🏎️","🚓","🚑","🚒","🚐","🛻",
        "🚚","🚛","🚜","🦯","🦽","🦼","🚲","🛴","🛵","🏍️","🛺",
        "🚨","🚔","🚍","🚘","🚖","🚡","🚠","🚟","🚃","🚋","🚞",
        "🚝","🚄","🚅","🚈","🚂","🚆","🚇","🚊","🚉","✈️","🛫",
        "🛬","🛰️","🚀","🛸","🚁","🛶","⛵","🛥️","🚤","🦢","🦩",
        "🗼","🗽","🗿","🗻","🏔️","⛰️","🌋","🏕️","🏖️","🏜️","🏝️",
        "🏟️","🏛️","🏗️","🧱","🏘️","🏚️","🏠","🏡","🏢","🏣","🏤",
        "🏥","🏦","🏨","🏩","🏪","🏫","🏬","🏭","🏯","🏰","💒",
        "🕌","🕍","🛕","🕋","⛪","🛤️","🛣️","🌁","🌃","🏙️","🌄"
    ],
}

# 扁平化完整安卓 Emoji 池
ANDROID_EMOJIS = [e for cat in ANDROID_EMOJI_CATEGORIES.values() for e in cat]

# 匹配常见 Emoji Unicode 区间的正则
EMOJI_PATTERN = re.compile(
    '[\U0001F600-\U0001F64F'
    '\U0001F300-\U0001F5FF'
    '\U0001F680-\U0001F6FF'
    '\U0001F1E0-\U0001F1FF'
    '\U00002500-\U00002BEF'
    '\U00002702-\U000027B0'
    '\U000024C2-\U0001F251'
    '\U0001F900-\U0001F9FF'
    '\U0001FA70-\U0001FAFF]' 
    '+', flags=re.UNICODE)


class EmojiReplacer:
    """Emoji替换工具类"""
    
    def __init__(self):
        """初始化Emoji替换器"""
        self.emoji_mapping = {}
        
    def extract_emojis(self, text: str) -> List[str]:
        """从文本中提取所有Emoji并去重"""
        return list(set(EMOJI_PATTERN.findall(text)))
    
    def create_emoji_mapping(self, emojis: List[str]) -> Dict[str, str]:
        """创建Emoji映射关系"""
        mapping = {}
        pool = ANDROID_EMOJIS.copy()
        for e in sorted(emojis):
            if not pool:
                pool = ANDROID_EMOJIS.copy()  # 重置表情池
            mapping[e] = pool.pop(0)
        return mapping
    
    def replace_emojis(self, text: str) -> str:
        """替换文本中的Emoji"""
        # 提取文本中所有唯一的Emoji
        emojis = self.extract_emojis(text)
        
        # 为新发现的Emoji创建映射
        new_emojis = [e for e in emojis if e not in self.emoji_mapping]
        if new_emojis:
            new_mapping = self.create_emoji_mapping(new_emojis)
            self.emoji_mapping.update(new_mapping)
        
        # 替换文本中的Emoji
        result = text
        for orig, sub in self.emoji_mapping.items():
            if orig in result:
                result = result.replace(orig, sub)
                
        return result
    
    def process_file(self, input_path: Path, output_path: Path) -> int:
        """处理单个文件并返回替换的Emoji数量"""
        # 读取文件内容
        content = input_path.read_text(encoding='utf-8')
        
        # 处理JSON文件（如果是JSON）
        try:
            data = json.loads(content)
            text = json.dumps(data, ensure_ascii=False, indent=2)
            is_json = True
        except json.JSONDecodeError:
            text = content
            is_json = False
            
        # 替换Emoji
        original_emojis = self.extract_emojis(text)
        replaced_text = self.replace_emojis(text)
        replaced_count = len([e for e in original_emojis if e in self.emoji_mapping])
        
        # 写入输出文件
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(replaced_text, encoding='utf-8')
        
        return replaced_count


def main():
    """主函数，处理命令行参数并执行Emoji替换"""
    # 获取当前脚本所在目录
    script_dir = Path(__file__).parent.resolve()
    
    parser = argparse.ArgumentParser(
        description="将emojis目录下的JSON/文本文件中的Emoji替换为安卓系统支持的Emoji"
    )
    parser.add_argument(
        '-i', '--input', type=Path, default=script_dir / "emojis",
        help='输入文件或目录路径（默认为脚本所在目录下的emojis文件夹）'
    )
    parser.add_argument(
        '-o', '--output', type=Path, default=script_dir / "output",
        help='输出文件或目录路径（默认为脚本所在目录下的output文件夹）'
    )
    parser.add_argument(
        '-r', '--recursive', action='store_true',
        help='递归处理子目录中的文件'
    )
    parser.add_argument(
        '-v', '--verbose', action='store_true',
        help='显示详细处理信息'
    )
    args = parser.parse_args()
    
    # 初始化Emoji替换器
    replacer = EmojiReplacer()
    
    # 处理输入路径
    input_path = args.input.resolve()
    if not input_path.exists():
        print(f"错误：输入路径 '{input_path}' 不存在")
        return
    
    # 确定输出路径
    output_path = args.output.resolve()
    
    # 确保输出目录存在
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 处理文件或目录
    if input_path.is_file():
        # 处理单个文件
        output_file = output_path / input_path.name
        replaced_count = replacer.process_file(input_path, output_file)
        print(f"已处理文件: {input_path} → {output_file}")
        print(f"替换了 {replaced_count} 个Emoji")
        
    elif input_path.is_dir():
        # 处理目录
        # 获取所有要处理的文件
        if args.recursive:
            files = list(input_path.rglob("*.*"))
        else:
            files = list(input_path.glob("*.*"))
            
        # 过滤允许的文件类型
        allowed_extensions = {'.json', '.txt'}
        files = [f for f in files if f.is_file() and f.suffix.lower() in allowed_extensions]
        
        if not files:
            print(f"警告：在目录 '{input_path}' 中未找到可处理的文件")
            return
            
        # 处理所有文件
        total_files = len(files)
        total_replaced = 0
        
        for i, file in enumerate(files, 1):
            # 计算相对路径以保持目录结构
            relative_path = file.relative_to(input_path)
            output_file = output_path / relative_path
            
            # 处理文件
            replaced_count = replacer.process_file(file, output_file)
            total_replaced += replaced_count
            
            if args.verbose:
                print(f"[{i}/{total_files}] 已处理: {file} → {output_file} ({replaced_count} 个Emoji)")
        
        print(f"\n处理完成！共处理 {total_files} 个文件，替换了 {total_replaced} 个Emoji")
        print(f"输出目录: {output_path}")


if __name__ == "__main__":
    main()
