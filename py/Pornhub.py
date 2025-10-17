import json
import requests

# 定义数据模型（使用普通类代替 Scrapy Item）
class CategoryItem:
    def __init__(self, type_id, type_name, source):
        self.type_id = type_id
        self.type_name = type_name
        self.source = source
    
    def to_dict(self):
        return {
            'type_id': self.type_id,
            'type_name': self.type_name,
            'source': self.source
        }

def parse_local_data():
    """解析本地数据"""
    try:
        # 模拟数据源
        your_data = '{"class":[{"type_id":"/video","type_name":"\u89c6\u9891"},{"type_id":"/playlists","type_name":"\u7247\u5355"},{"type_id":"/channels","type_name":"\u9891\u9053"},{"type_id":"/categories","type_name":"\u5206\u7c7b"},{"type_id":"/pornstars","type_name":"\u660e\u661f"}],"filters":{}}'
        
        data = json.loads(your_data)
        results = []
        
        print("开始处理分类数据...")
        for category in data['class']:
            print(f"处理分类: {category['type_name']} ({category['type_id']})")
            
            # 创建 Item 对象
            item = CategoryItem(
                type_id=category['type_id'],
                type_name=category['type_name'],
                source='local_data'
            )
            
            results.append(item.to_dict())
        
        # 保存到 JSON 文件
        with open('output.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print("数据已保存到 output.json")
        return results
        
    except Exception as e:
        print(f"处理数据时出错: {e}")
        return []

# 如果是从网络获取数据
def parse_from_url(https://cn.pornhub.com):
    """从URL获取数据并解析"""
    try:
        response = requests.get(https://cn.pornhub.com)
        response.raise_for_status()  # 检查请求是否成功
        
        data = response.json()
        results = []
        
        print("开始处理分类数据...")
        for category in data['class']:
            print(f"处理分类: {category['type_name']} ({category['type_id']})")
            
            item = CategoryItem(
                type_id=category['type_id'],
                type_name=category['type_name'],
                source='web_data'
            )
            
            results.append(item.to_dict())
        
        # 保存到 JSON 文件
        with open('output.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print("数据已保存到 output.json")
        return results
        
    except Exception as e:
        print(f"处理数据时出错: {e}")
        return []

if __name__ == "__main__":
    # 使用本地数据
    results = parse_local_data()
    
    # 如果需要从网络获取，取消下面的注释并替换为真实URL
    # results = parse_from_url("https://cn.pornhub.com")