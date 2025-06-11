from elasticsearch import Elasticsearch, helpers
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import json
import os

# 本地Elasticsearch配置
VIGNACHU_HOST = "https://localhost:9200"
USERNAME = "elastic"
PASSWORD = "k=tZtUL_df+sFlV-Q*87"  # 替换为你刚刚重置的密码
INDEX_NAME = "vignachu1"   # 你指定的索引名


def setup_index(es, index_name):
    """设置索引并定义映射"""
    index_config = {
        "settings": {
            "analysis": {
                "analyzer": {
                    "custom_analyzer": {
                        "type": "custom",
                        "tokenizer": "standard"
                    }
                }
            }
        },
        "mappings": {
            "properties": {
                "document_title": {
                    "type": "text",
                    "analyzer": "custom_analyzer",
                    "fields": {
                        "keyword": { "type": "keyword" }
                    }
                },
                "document_url": {"type": "keyword"},
                "document_content": {
                    "type": "text",
                    "analyzer": "custom_analyzer",
                    "fields": {
                        "keyword": { "type": "keyword" }
                    }
                },
                "referenced_urls": {"type": "keyword"},
                "html_file_name": {"type": "keyword"},
                "page_rank": {"type": "float"},
                "snapshot_time": {"type": "date", "format": "yyyy-MM-dd HH:mm:ss||yyyy-MM-dd||epoch_millis"}
            }
        }
    }

    if not es.indices.exists(index=index_name):
        response = es.indices.create(index=index_name, body=index_config)
        print(f"Index '{index_name}' created. Response: {response}")
    else:
        print(f"Index '{index_name}' already exists.")


def load_json(file_path):
    """加载JSON数据"""
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"The file {file_path} does not exist.")

    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data


def bulk_index(es, index_name, data, batch_size=100, chunk_size=5):
    """使用Bulk API批量索引数据，分批次"""
    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        actions = [
            {
                "_index": index_name,
                "_source": item
            }
            for item in batch
        ]

        try:
            helpers.bulk(es, actions, chunk_size=chunk_size)
            print(f"Batch {i // batch_size + 1} indexed successfully.")
        except Exception as e:
            print(f"An error occurred while indexing batch {i // batch_size + 1}: {e}")


def main():
    # 创建本地Elasticsearch客户端
    es_client = Elasticsearch(
        VIGNACHU_HOST,
        basic_auth=(USERNAME, PASSWORD),
        verify_certs=False,  # 本地自签名证书时关闭校验
        request_timeout=30,
        max_retries=5,
        retry_on_timeout=True,
        headers={"Content-Type": "application/json"},
        http_compress=True
    )

    # 检查Elasticsearch是否可用
    if not es_client.ping():
        print("Elasticsearch is not running or unreachable.")
        return

    # 设置索引
    setup_index(es_client, INDEX_NAME)

    # 加载数据
    data_file = 'result.json'  # 推荐用字段已转换的文件
    data = load_json(data_file)

    # 批量索引数据
    bulk_index(es_client, INDEX_NAME, data)


if __name__ == "__main__":
    main()