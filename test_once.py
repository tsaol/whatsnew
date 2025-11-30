"""测试运行一次"""
from src.config import Config
from src.storage import Storage
from src.crawler import Crawler
from src.mailer import Mailer

print("测试运行 WhatsNew...")
print("="*50)

# 加载配置
config = Config('config.yaml')

# 初始化模块
storage = Storage(config.get('data_file', 'data/sent_news.json'))
crawler = Crawler(storage)
mailer = Mailer(config.email_config)

# 抓取新闻
sources = config.sources
max_items = config.get('max_items_per_source', 5)
new_items = crawler.fetch_all(sources, max_items)

# 发送邮件
if new_items:
    print(f"\n共发现 {len(new_items)} 条新内容")
    subject, content = mailer.format_news_email(new_items)

    if mailer.send(subject, content):
        # 标记为已发送
        for item in new_items:
            storage.mark_sent(item['id'], item['title'])
        print("所有新闻已发送并标记")
else:
    print("没有新内容")

# 统计信息
stats = storage.get_stats()
print(f"\n统计: 累计已发送 {stats['total_sent']} 条新闻")
print("="*50)
