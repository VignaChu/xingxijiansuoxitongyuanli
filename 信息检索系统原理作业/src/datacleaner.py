import json
import networkx as nx

# 1. 读取JSON文件（每行一个对象）
def load_json_files(paths):
    """从多个JSON文件中加载数据（每行一个对象）"""
    combined_data = []
    for path in paths:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        combined_data.append(json.loads(line))
                    except Exception as e:
                        print(f"Error parsing line: {e}")
    print(f"Loaded {len(combined_data)} entries.")
    return combined_data

# 2. 去重
def remove_duplicates(entries):
    """根据URL去除重复项"""
    seen = set()
    unique_entries = []
    for entry in entries:
        url = entry.get('url')
        if url and url not in seen:
            seen.add(url)
            unique_entries.append(entry)
    print(f"Removed duplicates, {len(unique_entries)} unique entries remain.")
    return unique_entries

# 3. 构建图（保留此步骤，但不用于PageRank计算）
def create_graph(entries):
    """构建网页链接图"""
    web_graph = nx.DiGraph()
    for entry in entries:
        url = entry.get('url')
        if not url:
            continue
        web_graph.add_node(url)
        links = entry.get('referenced_urls', [])
        if not isinstance(links, list):
            continue
        for link in links:
            web_graph.add_edge(url, link)
    return web_graph

# 6. 字段名转换
def convert_fields(entry):
    return {
        "document_title": entry.get("title", ""),
        "document_url": entry.get("url", ""),
        "document_content": entry.get("content", ""),
        "referenced_urls": entry.get("referenced_urls", []),  # 保持一致
        "html_file_name": entry.get("html_filename", ""),
        "page_rank": 0,  # 因为不再计算PageRank，设为默认值0
        "snapshot_time": entry.get("snapshot_time", "")  # 新增快照时间（如果有）
    }

# 7. 保存结果
def save_to_json(data, output_path):
    """将数据保存到JSON文件"""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# 主程序
def process_data(input_paths, output_path):
    """主程序流程，去除了PageRank部分"""
    all_data = load_json_files(input_paths)
    unique_data = remove_duplicates(all_data)
    
    # 可选：构建图（仅作为示例或后续扩展用途）
    _ = create_graph(unique_data)  # 如果不需要使用图结构，也可以直接删除这一行
    
    # 转换字段名称
    converted_data = [convert_fields(item) for item in unique_data]
    
    # 保存结果
    save_to_json(converted_data, output_path)

# 输入和输出文件路径
input_paths = [
    'crawl/pages.json'
]
output_path = 'result.json'

# 执行主程序
if __name__ == "__main__":
    process_data(input_paths, output_path)