"""
主程序入口：高校网站搜索引擎后端
- 用户注册/登录/登出
- 个性化推荐
- 多种搜索（站内、短语、通配、文档）
- 用户行为记录
- 快照与静态文件服务
"""

from flask import Flask, request, jsonify, render_template, redirect, url_for, session, send_from_directory
import os
import json
from functools import wraps

# ========== 配置 ==========
APP_SECRET = 'replace_with_a_secure_random_string'
USER_DATA_FILE = 'users.json'
ES_HOST = 'https://localhost:9200'
ES_INDEX = 'vignachu1'
ES_USERNAME = 'elastic'
ES_PASSWORD = 'k=tZtUL_df+sFlV-Q*87'

# ========== Flask 应用 ==========
app = Flask(__name__, template_folder='htmls')
app.config['SECRET_KEY'] = APP_SECRET

# ========== 工具函数 ==========
def load_user_data():
    """加载用户数据"""
    if not os.path.exists(USER_DATA_FILE):
        return {"users": []}
    with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_user_data(data):
    """保存用户数据"""
    with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user(username):
    """根据用户名获取用户对象"""
    users = load_user_data()
    return next((u for u in users['users'] if u['username'] == username), None)

def update_user(username, update_func):
    """更新指定用户，update_func(user)会被调用"""
    users = load_user_data()
    user = next((u for u in users['users'] if u['username'] == username), None)
    if user:
        update_func(user)
        save_user_data(users)
        return True
    return False

def login_required(f):
    """登录保护装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated

def get_es_client():
    """获取 Elasticsearch 客户端"""
    from elasticsearch import Elasticsearch
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    return Elasticsearch(
        [ES_HOST],
        basic_auth=(ES_USERNAME, ES_PASSWORD),
        verify_certs=False
    )

# ========== 用户相关 ==========
@app.route('/register', methods=['GET', 'POST'])
def register_page():
    """用户注册"""
    if request.method == 'GET':
        return render_template('register.html')
    try:
        data = request.get_json()
        username, password = data.get('username'), data.get('password')
        if not username or not password:
            return jsonify({"error": "用户名或密码不能为空"}), 400
        if get_user(username):
            return jsonify({"error": "用户名已存在"}), 400
        users = load_user_data()
        users['users'].append({
            'username': username,
            'password': password,
            'search_history': [],
            'clicked_links': []
        })
        save_user_data(users)
        return jsonify({"message": "注册成功"}), 200
    except Exception as e:
        return jsonify({"error": f"注册失败: {e}"}), 500

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    """用户登录"""
    if request.method == 'GET':
        return render_template('login.html')
    try:
        data = request.get_json()
        username, password = data.get('username'), data.get('password')
        user = get_user(username)
        if not user or user['password'] != password:
            return jsonify({"error": "无效的用户名或密码"}), 400
        session['user'] = username
        return jsonify({"message": "登录成功"}), 200
    except Exception as e:
        return jsonify({"error": f"登录失败: {e}"}), 500

@app.route('/logout', methods=['POST'])
def logout_page():
    """用户登出"""
    session.pop('user', None)
    return jsonify({"message": "注销成功"}), 200

@app.route('/user')
@login_required
def user_info_page():
    """用户信息页"""
    user = get_user(session['user'])
    if user:
        return render_template('user_page.html', user=user)
    return "User not found", 404

# ========== 用户行为 ==========
def record_search(username, query):
    """记录用户搜索历史"""
    def updater(user):
        if query in user['search_history']:
            user['search_history'].remove(query)
        user['search_history'].append(query)
        if len(user['search_history']) > 20:
            user['search_history'] = user['search_history'][-20:]
    update_user(username, updater)

def record_click(username, url):
    """记录用户点击链接"""
    def updater(user):
        if url not in user['clicked_links']:
            user['clicked_links'].append(url)
            if len(user['clicked_links']) > 50:
                user['clicked_links'] = user['clicked_links'][-50:]
    update_user(username, updater)

@app.route('/update_click', methods=['POST'])
@login_required
def click_record_api():
    """前端点击链接时调用，记录点击"""
    url = request.json.get('url')
    if url:
        record_click(session['user'], url)
        return jsonify({"status": "success"}), 200
    return jsonify({"status": "failed", "message": "URL not provided"}), 400

# ========== 推荐 ==========
@app.route('/recommendations', methods=['GET'])
@login_required
def recommend_api():
    """个性化推荐接口"""
    user = get_user(session['user'])
    es = get_es_client()
    if user and user['search_history']:
        recent_terms = user['search_history'][-5:]
        query_str = " ".join(recent_terms)
        boost_terms = user['search_history']
        penalize_urls = user['clicked_links']
        search_body = {
            "query": {
                "function_score": {
                    "query": {
                        "multi_match": {
                            "query": query_str,
                            "fields": ["document_title", "document_content"],
                            "type": "best_fields"
                        }
                    },
                    "functions": [
                        *[{"filter": {"match_phrase": {"document_content": term}}, "weight": 2} for term in boost_terms],
                        *[{
                            "script_score": {
                                "script": {
                                    "source": "if (doc['document_url'].value == params.url) { return _score * 0.5 } else { return _score }",
                                    "params": {"url": url}
                                }
                            }
                        } for url in penalize_urls]
                    ],
                    "score_mode": "sum",
                    "boost_mode": "multiply"
                }
            },
            "collapse": {"field": "document_url"},
            "sort": [{"_score": {"order": "desc"}}, {"page_rank": {"order": "desc"}}],
            "size": 100
        }
    else:
        search_body = {
            "query": {"match_all": {}},
            "sort": [{"_score": {"order": "desc"}}, {"page_rank": {"order": "desc"}}],
            "size": 20
        }
    resp = es.search(index=ES_INDEX, body=search_body)
    results = [{
        'title': hit['_source'].get('document_title', 'No title'),
        'url': hit['_source'].get('document_url', ''),
        'content': hit['_source'].get('document_content', '')[:300] + '...',
        'html_filename': hit['_source'].get('html_file_name', ''),
    } for hit in resp['hits']['hits']]
    return jsonify({'hits': results})

# ========== 搜索 ==========
def build_search_body(query, user=None, mode='best_fields'):
    """构建通用搜索请求体"""
    boost_terms = user['search_history'] if user else []
    penalize_urls = user['clicked_links'] if user else []
    if mode == 'wildcard':
        query_part = {
            "bool": {
                "should": [
                    {"wildcard": {"document_title.keyword": {"value": query}}},
                    {"wildcard": {"document_content.keyword": {"value": query}}}
                ]
            }
        }
    elif mode == 'file':
        # 针对文档搜索，查 referenced_urls 里包含常见文件类型的文档
        file_exts = ['*.dox', '*.docx', '*.pdf', '*.rar', '*.zip', '*.xlsx', '*.xls', '*.ppt', '*.pptx', '*.jpg', '*.png']
        shoulds = [{"wildcard": {"referenced_urls": ext}} for ext in file_exts]
        query_part = {
            "bool": {
                "should": shoulds,
                "minimum_should_match": 1
            }
        }
    else:
        query_part = {
            "multi_match": {
                "query": query,
                "fields": ["document_title", "document_content"],
                "type": mode
            }
        }
    return {
        "query": {
            "function_score": {
                "query": query_part,
                "functions": [
                    *[{"filter": {"match_phrase": {"document_content": term}}, "weight": 2} for term in boost_terms],
                    *[{
                        "script_score": {
                            "script": {
                                "source": "if (doc['document_url'].value == params.url) { return _score * 0.5 } else { return _score }",
                                "params": {"url": url}
                            }
                        }
                    } for url in penalize_urls]
                ],
                "score_mode": "sum",
                "boost_mode": "multiply"
            }
        },
        "collapse": {"field": "document_url"},
        "sort": [{"_score": {"order": "desc"}}, {"page_rank": {"order": "desc"}}],
        "size": 50 if mode != 'file' else 1000
    }

def search_and_format(query, user, mode='best_fields'):
    """执行搜索并格式化结果"""
    es = get_es_client()
    body = build_search_body(query, user, mode)
    resp = es.search(index=ES_INDEX, body=body)
    results = []
    for hit in resp['hits']['hits']:
        src = hit['_source']
        result = {
            'title': src.get('document_title', 'No title'),
            'url': src.get('document_url', ''),
            'content': src.get('document_content', '')[:300] + '...',
            'html_filename': src.get('html_file_name', ''),
        }
        if mode == 'file':
            referenced_urls = src.get('referenced_urls', [])
            if not isinstance(referenced_urls, list):
                referenced_urls = []
            files = [ref for ref in referenced_urls
                     if isinstance(ref, str) and any(ref.lower().endswith(ext) for ext in [
                         '.dox', '.docx', '.pdf', '.rar', '.zip', '.xlsx', '.xls', '.ppt', '.pptx', '.jpg', '.png'])]
            if files:
                result['files'] = files
                results.append(result)
        else:
            results.append(result)
    return results

@app.route('/sitesearch', methods=['POST'])
def site_search_api():
    """站内搜索"""
    query = request.json.get('query')
    if not query:
        return jsonify({"error": "No query provided"}), 400
    user = get_user(session['user']) if 'user' in session else None
    results = search_and_format(query, user, 'best_fields')
    if user:
        record_search(user['username'], query)
    return jsonify({'hits': results})

@app.route('/phrasesearch', methods=['POST'])
def phrase_search_api():
    """短语搜索"""
    query = request.json.get('query')
    if not query:
        return jsonify({"error": "No query provided"}), 400
    user = get_user(session['user']) if 'user' in session else None
    results = search_and_format(query, user, 'phrase')
    if user:
        record_search(user['username'], query)
    return jsonify({'hits': results})

@app.route('/wildcardsearch', methods=['POST'])
def wildcard_search_api():
    """通配符搜索"""
    query = request.json.get('query')
    if not query:
        return jsonify({"error": "No query provided"}), 400
    user = get_user(session['user']) if 'user' in session else None
    results = search_and_format(query, user, 'wildcard')
    if user:
        record_search(user['username'], query)
    return jsonify({'hits': results})

@app.route('/filesearch', methods=['POST'])
def file_search_api():
    """文档搜索"""
    query = request.json.get('query')
    if not query:
        return jsonify({"error": "No query provided"}), 400
    user = get_user(session['user']) if 'user' in session else None
    results = search_and_format(query, user, 'file')
    if user:
        record_search(user['username'], query)
    return jsonify({'hits': results})

# ========== 页面路由 ==========
@app.route('/')
def home_page():
    """首页（登录页）"""
    return render_template('login.html')

@app.route('/site_search.html')
def site_search_page():
    return render_template('site_search.html')

@app.route('/phrase_search.html')
def phrase_search_page():
    return render_template('phrase_search.html')

@app.route('/wildcard_search.html')
def wildcard_search_page():
    return render_template('wildcard_search.html')

@app.route('/file_search.html')
def file_search_page():
    return render_template('file_search.html')

# ========== 快照 ==========
@app.route('/snapshot/<path:filename>')
def snapshot_api(filename):
    """快照文件服务"""
    # 适配你的目录结构：src/crawl/pages/filename
    directory = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'crawl', 'pages')
    try:
        return send_from_directory(directory, filename, as_attachment=False)
    except FileNotFoundError:
        return "File not found", 404

@app.route('/user_history')
@login_required
def user_history_api():
    user = get_user(session['user'])
    if user:
        return jsonify({"history": user.get("search_history", [])})
    return jsonify({"history": []})

@app.route('/suggest', methods=['GET'])
@login_required
def suggest_api():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({"suggestions": []})
    es = get_es_client()
    # 用 match_phrase_prefix 提供简单建议
    body = {
        "size": 0,
        "aggs": {
            "titles": {
                "terms": {
                    "field": "document_title.keyword",
                    "include": f".*{q}.*",
                    "size": 8
                }
            }
        }
    }
    resp = es.search(index=ES_INDEX, body=body)
    suggestions = [b['key'] for b in resp['aggregations']['titles']['buckets']]
    return jsonify({"suggestions": suggestions})

# ========== 启动 ==========
if __name__ == '__main__':
    app.run(debug=True)