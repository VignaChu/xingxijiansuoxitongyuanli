import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os
import json
import time
import chardet
import datetime

# 配置常量
OUTPUT_DIR = 'crawl'
PAGES_DIR = os.path.join(OUTPUT_DIR, 'pages')
VISITED_FILE = os.path.join(OUTPUT_DIR, 'visited.txt')
TO_VISIT_FILE = os.path.join(OUTPUT_DIR, 'to_visit.txt')
JSON_FILE = os.path.join(OUTPUT_DIR, 'pages.json')


def validate_url(url):
    """验证 URL 是否合法"""
    parsed_url = urlparse(url)
    return bool(parsed_url.netloc) and bool(parsed_url.scheme) and parsed_url.scheme in ['http', 'https']


def extract_links(base_url, page_content):
    """从页面内容中提取所有有效链接"""
    soup = BeautifulSoup(page_content, 'html.parser')
    link_set = set()
    for anchor in soup.find_all('a', href=True):
        href = anchor['href']
        full_url = urljoin(base_url, href)
        if validate_url(full_url):
            link_set.add(full_url)
    return link_set


def save_page(base_url, content):
    """将页面内容保存为HTML文件"""
    if not os.path.exists(PAGES_DIR):
        os.makedirs(PAGES_DIR)

    file_name = os.path.basename(urlparse(base_url).path) or 'index.html'
    file_path = os.path.join(PAGES_DIR, file_name)

    counter = 1
    original_path = file_path
    while os.path.exists(file_path):
        file_path = f"{original_path}_{counter}.html"
        counter += 1

    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(content)
    return os.path.basename(file_path)


def load_visited():
    """读取已访问的URL集合"""
    if not os.path.exists(VISITED_FILE):
        return set()
    with open(VISITED_FILE, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f)


def save_visited(urls):
    """将已访问的URL写入文件"""
    with open(VISITED_FILE, 'w', encoding='utf-8') as f:
        for url in urls:
            f.write(url + '\n')


def load_to_visit():
    """读取待爬的URL列表"""
    if not os.path.exists(TO_VISIT_FILE):
        return []
    with open(TO_VISIT_FILE, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f]


def save_to_visit(urls):
    """将待爬的URL列表写入文件"""
    with open(TO_VISIT_FILE, 'w', encoding='utf-8') as f:
        for url in urls:
            f.write(url + '\n')


def append_json(data):
    """将单个页面的数据追加到JSON文件中（每页一行）"""
    mode = 'w' if not os.path.exists(JSON_FILE) else 'a'
    with open(JSON_FILE, mode, encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
        f.write('\n')


def scrape_site(starting_url):
    visited = load_visited()
    to_visit = load_to_visit()

    # 如果队列为空，则初始化为起始页
    if not to_visit:
        to_visit = [starting_url]

    while to_visit:
        current_page = to_visit.pop(0)
        if current_page in visited:
            continue

        print(f"Scraping: {current_page}")
        try:
            response = requests.get(current_page, timeout=10)
            response.encoding = chardet.detect(response.content)['encoding'] or 'utf-8'

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                title = soup.title.string if soup.title else 'No Title'
                content = soup.get_text(strip=True, separator=' ')
                referenced_urls = [a['href'] for a in soup.find_all('a', href=True) if validate_url(a['href'])]

                saved_file = save_page(current_page, response.text)

                # 新增快照时间
                snapshot_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                data = {
                    'title': title,
                    'url': current_page,
                    'content': content,
                    'referenced_urls': referenced_urls,
                    'html_filename': saved_file,
                    'snapshot_time': snapshot_time   # 新增字段
                }

                append_json(data)
                visited.add(current_page)
                save_visited(visited)

                new_links = extract_links(current_page, response.text)
                for link in new_links:
                    if link not in visited and 'nankai.edu.cn' in link and \
                            not link.endswith(('.doc', '.pdf', '.docx', '.rar', '.zip', '.xlsx', '.xls', '.ppt', '.pptx', '.jpg', '.png')):
                        if link not in to_visit:
                            to_visit.append(link)

                save_to_visit(to_visit)  # 每爬完一页就更新待爬队列
                time.sleep(0.1)
            else:
                print(f"Failed to retrieve {current_page}. Status code: {response.status_code}")

        except Exception as e:
            print(f"Error processing {current_page}: {e}")


if __name__ == "__main__":
    starting_url = "https://cs.nankai.edu.cn/"
    scrape_site(starting_url)