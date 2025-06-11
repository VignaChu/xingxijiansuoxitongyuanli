from elasticsearch import Elasticsearch
es = Elasticsearch("https://localhost:9200", basic_auth=("elastic", "k=tZtUL_df+sFlV-Q*87"), verify_certs=False)
es.indices.delete(index="vignachu1")