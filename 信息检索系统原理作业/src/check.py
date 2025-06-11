from elasticsearch import Elasticsearch
es = Elasticsearch("https://localhost:9200", basic_auth=("elastic", "k=tZtUL_df+sFlV-Q*87"), verify_certs=False)
res = es.search(
    index="vignachu1",
    body={
        "query": {
            "exists": {"field": "referenced_urls"}
        },
        "_source": ["document_title", "referenced_urls"],
        "size": 10
    }
)
for hit in res['hits']['hits']:
    print(hit['_source'])