"""测试运行一次"""
import sys
from pathlib import Path
from src.config import Config
from src.storage import Storage
from src.crawler import Crawler
from src.mailer import Mailer


def index_to_hub(items, config):
    """将新闻索引到 Content Hub"""
    hub_enabled = config.get('hub.enabled', True)
    if not hub_enabled:
        print("[Hub] Content Hub 已禁用，跳过索引")
        return

    try:
        # 添加 hub 模块路径
        hub_path = Path(__file__).parent.parent / 'hub'
        if hub_path.exists():
            sys.path.insert(0, str(hub_path))
            from src.config import Config as HubConfig
            from src.storage import ContentStorage
            from src.fetcher import ContentFetcher
            from src.browser_fetcher import BrowserFetcher

            print("\n[Hub] 开始索引到 Content Hub...")
            hub_config = HubConfig()
            storage = ContentStorage(hub_config)
            fetcher = ContentFetcher(hub_config)
            browser_fetcher = BrowserFetcher(hub_config)

            success = 0
            captured = 0
            for item in items:
                url = item.get('link')
                if not url:
                    continue

                # 检查是否已存在
                article_id = fetcher._generate_id(url)
                if storage.exists(article_id):
                    continue

                metadata = {
                    'title': item.get('title'),
                    'source': item.get('source'),
                    'category': item.get('category'),
                    'published': item.get('published')
                }

                # 1. 抓取全文并索引到 OpenSearch (快速)
                article = fetcher.fetch_full_content(url, metadata=metadata)

                if article and storage.add_article(article):
                    storage.save_to_s3(article)
                    success += 1

                    # 2. 完整抓取保存到 S3 (截图 + HTML + 图片)
                    try:
                        result = browser_fetcher.capture(
                            url,
                            metadata=metadata,
                            save_screenshot=True,
                            save_html=True,
                            save_images=True,
                            save_to_s3=True
                        )
                        if result:
                            captured += 1
                            # 更新 OpenSearch 中的快照路径
                            storage.update_snapshot(article_id, {
                                'folder_name': result.get('folder_name', ''),
                                'screenshot_s3': result.get('screenshot_s3', ''),
                                'html_s3': result.get('html_s3', ''),
                                'images_s3': result.get('images_s3', [])
                            })
                    except Exception as e:
                        print(f"[Hub] 完整抓取失败 {url}: {e}")

            print(f"[Hub] 索引完成: {success}/{len(items)} 篇")
            print(f"[Hub] 完整抓取: {captured}/{success} 篇")
        else:
            print("[Hub] hub 模块未找到，跳过索引")
    except Exception as e:
        print(f"[Hub] 索引失败: {e}")


print("测试运行 WhatsNew...")
print("="*50)

# 加载配置
config = Config('config.yaml')

# 初始化模块
storage = Storage(config.get('data_file', 'data/sent_news.json'))
keyword_filter = config.get('filter.keyword_filter', None)
crawler = Crawler(storage, keyword_filter=keyword_filter)
mailer = Mailer(config.email_config)

print(f"关键词过滤: {keyword_filter or '未启用'}")

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
    print(f"\n共发现 {len(new_items)} 条新内容")
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
        s3_config = config.get('s3', {})
        storage.save_to_s3(content, new_items, ai_analysis, s3_config)

        # 索引到 Content Hub
        index_to_hub(new_items, config)
else:
    print("没有新内容")

# 统计信息
stats = storage.get_stats()
print(f"\n统计: 累计已发送 {stats['total_sent']} 条新闻")
print("="*50)
