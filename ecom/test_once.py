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
keyword_filter = config.get('filter.keyword_filter', None)
key_companies = config.get('key_companies', [])
crawler = Crawler(storage, keyword_filter=keyword_filter, key_companies=key_companies)
mailer = Mailer(config.email_config)

print(f"关键词过滤: {keyword_filter or '未启用'}")
if key_companies:
    print(f"关键企业: {', '.join(key_companies)}")

# 抓取新闻
sources = config.sources
max_items = config.get('max_items_per_source', 8)
max_days = config.get('max_days', 2)  # 默认2天（48小时）
new_items = crawler.fetch_all(sources, max_items, max_days)

# AI 分析（如果启用）
ai_analysis = None
ai_enabled = config.get('ai.enabled', False)
min_news = config.get('ai.min_news_for_analysis', 5)

if new_items and ai_enabled and len(new_items) >= min_news:
    try:
        print(f"\n[AI] 分析已启用，正在使用 Claude 4.5 分析...")
        from src.analyzer import create_analyzer

        aws_region = config.get('ai.aws_region', 'us-west-2')
        analyzer = create_analyzer(aws_region=aws_region)
        ai_analysis = analyzer.analyze(new_items)

        print(f"[OK] AI 分析完成")
        print(f"   - 总结: {ai_analysis.get('summary', 'N/A')[:50]}...")
        print(f"   - 趋势数: {len(ai_analysis.get('trends', []))}")
        print(f"   - TOP 新闻: {len(ai_analysis.get('top_news', []))}")

        # 如果有翻译后的数据，使用翻译后的数据替换原始数据
        if ai_analysis and ai_analysis.get('translated_items'):
            new_items = ai_analysis['translated_items']
            print(f"[OK] 使用翻译后的新闻数据")
    except Exception as e:
        print(f"[WARN] AI 分析失败: {e}")
        print(f"   继续使用传统方式发送邮件...")
        ai_analysis = None

# 发送邮件
email_enabled = config.get('email.enabled', True)

if new_items:
    # 统计关键企业新闻
    key_company_count = sum(1 for item in new_items if item.get('is_key_company', False))
    print(f"\n共发现 {len(new_items)} 条新内容")
    if key_company_count > 0:
        print(f"  其中关键企业新闻: {key_company_count} 条")
    subject, content = mailer.format_news_email(new_items, ai_analysis=ai_analysis)

    if not email_enabled:
        print("[跳过] 邮件发送已禁用 (email.enabled: false)")
        print("使用 preview_email.py 生成预览")
    elif mailer.send(subject, content):
        # 标记为已发送
        for item in new_items:
            storage.mark_sent(item['id'], item['title'])
        print("所有新闻已发送并标记")

        # 保存到 S3
        storage.save_to_s3(content, new_items, ai_analysis, category='ecom')
else:
    print("没有新内容")

# 统计信息
stats = storage.get_stats()
print(f"\n统计: 累计已发送 {stats['total_sent']} 条新闻")
print("="*50)
