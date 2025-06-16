import json
import re
import hashlib
import argparse
from pathlib import Path
from typing import Dict, List
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

try:
    from tqdm import tqdm
except ImportError:
    tqdm = lambda x, desc=None: x  # 如果没有tqdm，使用普通迭代

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
    
    def create_deterministic_mapping(self, emojis: List[str]) -> Dict[str, str]:
        """创建确定性的Emoji映射（相同原始Emoji始终映射到相同替换项）"""
        mapping = {}
        for e in emojis:
            # 使用哈希值确定在安卓表情池中的位置
            index = hash(e) % len(ANDROID_EMOJIS)
            mapping[e] = ANDROID_EMOJIS[index]
        return mapping
    
    def replace_emojis(self, text: str) -> str:
        """替换文本中的Emoji"""
        # 提取文本中所有唯一的Emoji
        emojis = self.extract_emojis(text)
        
        # 为新发现的Emoji创建映射
        new_emojis = [e for e in emojis if e not in self.emoji_mapping]
        if new_emojis:
            new_mapping = self.create_deterministic_mapping(new_emojis)
            self.emoji_mapping.update(new_mapping)
        
        # 替换文本中的Emoji
        result = text
        for orig, sub in self.emoji_mapping.items():
            if orig in result:
                result = result.replace(orig, sub)
                
        return result
    
    def process_file(self, input_path: Path, output_path: Path) -> int:
        """处理单个文件并返回替换的Emoji数量"""
        try:
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
            
        except Exception as e:
            print(f"❌ 处理文件 {input_path} 时发生错误: {e}")
            return 0
    
    def save_mapping(self, mapping_file: Path):
        """保存Emoji映射表到文件"""
        with open(mapping_file, 'w', encoding='utf-8') as f:
            json.dump(self.emoji_mapping, f, ensure_ascii=False, indent=2)
    
    def load_mapping(self, mapping_file: Path):
        """从文件加载Emoji映射表"""
        if mapping_file.exists():
            try:
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    self.emoji_mapping = json.load(f)
                print(f"✅ 已加载现有Emoji映射表: {len(self.emoji_mapping)} 个映射")
            except Exception as e:
                print(f"⚠️ 加载映射表失败: {e}")
    
    def generate_report(self, report_file: Path):
        """生成处理报告"""
        counts = {}
        for orig, sub in self.emoji_mapping.items():
            category = next(
                (cat for cat, emojis in ANDROID_EMOJI_CATEGORIES.items() if sub in emojis),
                "未知分类"
            )
            counts[category] = counts.get(category, 0) + 1
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("Emoji替换报告\n")
            f.write("=" * 30 + "\n")
            for category, count in counts.items():
                f.write(f"{category}: {count} 个替换\n")
            f.write(f"\n总计: {len(self.emoji_mapping)} 个不同Emoji被替换\n")


def get_file_hash(file_path: Path) -> str:
    """计算文件的SHA-256哈希值"""
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def process_files_concurrently(files: List[Path], replacer: EmojiReplacer, output_path: Path, verbose: bool):
    """使用线程池并行处理文件"""
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        for file in files:
            relative_path = file.relative_to(file.parent.parent)
            output_file = output_path / relative_path
            future = executor.submit(replacer.process_file, file, output_file)
            futures.append((file, output_file, future))
        
        # 收集结果
        total_replaced = 0
        for i, (file, output_file, future) in enumerate(futures, 1):
            try:
                replaced_count = future.result()
                total_replaced += replaced_count
                if verbose:
                    print(f"[{i}/{len(files)}] 已处理: {file} → {output_file} ({replaced_count} 个Emoji)")
            except Exception as e:
                print(f"⚠️ 处理文件 {file} 时出错: {e}")
    
    return total_replaced


def main():
    """主函数，处理命令行参数并执行Emoji替换"""
    # 获取当前脚本所在目录
    script_dir = Path(__file__).parent.resolve()
    
    parser = argparse.ArgumentParser(
        description="将emojis目录下的JSON/文本文件中的Emoji替换为安卓系统支持的Emoji"
    )
    parser.add_argument(
        '-i', '--input', type=Path, default=script_dir,
        help='输入目录路径（默认为脚本所在目录）'
    )
    parser.add_argument(
        '-o', '--output', type=Path, default=script_dir.parent / "output",
        help='输出目录路径（默认为与emojis同级的output文件夹）'
    )
    parser.add_argument(
        '-r', '--recursive', action='store_true',
        help='递归处理子目录中的文件'
    )
    parser.add_argument(
        '-v', '--verbose', action='store_true',
        help='显示详细处理信息'
    )
    parser.add_argument(
        '-m', '--mapping', type=Path, default=script_dir / ".emoji_mapping.json",
        help='Emoji映射文件路径'
    )
    parser.add_argument(
        '--report', type=Path, default=script_dir.parent / "emoji_report.txt",
        help='生成报告的路径'
    )
    parser.add_argument(
        '--extensions', type=str, default='json,txt,md,csv,xml,html',
        help='要处理的文件扩展名，逗号分隔（默认：json,txt,md,csv,xml,html）'
    )
    parser.add_argument(
        '--incremental', action='store_true',
        help='仅处理有变化的文件（增量模式）'
    )
    args = parser.parse_args()
    
    # 初始化Emoji替换器
    replacer = EmojiReplacer()
    
    # 加载现有映射表
    if args.mapping:
        replacer.load_mapping(args.mapping)
    
    # 处理输入路径
    input_path = args.input.resolve()
    if not input_path.exists():
        print(f"错误：输入路径 '{input_path}' 不存在")
        return
    
    # 确定输出路径
    output_path = args.output.resolve()
    
    # 确保输出目录存在
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 允许的文件类型
    allowed_extensions = {f'.{ext.strip()}' for ext in args.extensions.split(',')}
    
    # 处理目录
    if args.recursive:
        files = list(input_path.rglob("*.*"))
    else:
        files = list(input_path.glob("*.*"))
        
    # 过滤允许的文件类型
    files = [f for f in files if f.is_file() and f.suffix.lower() in allowed_extensions]
    
    if not files:
        print(f"警告：在目录 '{input_path}' 中未找到可处理的文件")
        return
        
    print(f"找到 {len(files)} 个可处理的文件")
    
    # 处理文件
    total_replaced = process_files_concurrently(files, replacer, output_path, args.verbose)
    
    # 保存映射表
    if args.mapping:
        replacer.save_mapping(args.mapping)
        print(f"✅ 已保存Emoji映射表: {args.mapping}")
    
    # 生成报告
    if args.report:
        replacer.generate_report(args.report)
        print(f"✅ 已生成处理报告: {args.report}")
    
    print(f"\n处理完成！共替换了 {total_replaced} 个Emoji")
    print(f"输出目录: {output_path}")


if __name__ == "__main__":
    main()
