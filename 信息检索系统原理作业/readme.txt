本项目的树形结构图
├── .idea
└── src
    ├── crawl
    │   ├── pages  #存储被爬取的页面的页面文件
    │   │   └── pages.json  #记录爬取页面的信息
    │   ├── to_visit.txt  #记录还需爬取（入队列）的网站url
    │   └── visited.txt  #记录已爬取页面避免重复爬取
    └── main
        ├── htmls  #前端页面
        │   ├── file_search.html  #文档查询（前端后端代码实现但爬取数据未记录这一信息）
        │   ├── login.html  #登录界面
        │   ├── phrase_search.html  #短语搜索
        │   ├── register.html  #注册界面
        │   ├── site_search.html  #站内搜索
        │   └── wildcard_search.html  #通配搜索
        ├── app.py  #后端代码
        ├── users.json  #存储用户信息
        ├── buildindex.py #通过本地部署的Elasticsearch建立索引
        ├── check.py  #调试用，检查索引中是否含有哪个词条
        ├── crawl.py  #爬取南开大学计算机学院网站数据并记录每个页面的信息
        ├── datacleaner.py  #将爬取到的信息进行清理与标准化
        ├── delete.py  #调试用，删除索引
        ├── result.json  #存储清理后的爬取数据
        └── readme.txt

运行方式
1.通过crawl.py爬取页面，可以自己设置从哪个网站开始爬取
2.通过datacleaner.py对爬取记录进行清理与格式化
3.通过buildindex.py连接本地Elasticsearch构建索引
4.通过app.py运行后端服务
5.访问app.py输出栏弹出的页面进入搜索系统