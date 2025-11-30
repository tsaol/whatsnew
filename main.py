"""WhatsNew - 新闻爬虫聚合平台主程序"""
import time
import schedule
from src.config import Config
from src.storage import Storage
from src.crawler import Crawler
from src.mailer import Mailer


def run_task():
    """执行一次任务"""
    print(f"\n{'='*50}")
    print(f"开始执行任务...")
    print(f"{'='*50}")

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

    # AI 分析（如果启用）
    ai_analysis = None
    ai_enabled = config.get('ai.enabled', False)
    min_news = config.get('ai.min_news_for_analysis', 5)

    if new_items and ai_enabled and len(new_items) >= min_news:
        try:
            print(f"\n🤖 AI 分析已启用，正在使用 Claude 4.5 分析...")
            from src.analyzer import create_analyzer

            aws_region = config.get('ai.aws_region', 'us-west-2')
            analyzer = create_analyzer(aws_region=aws_region)
            ai_analysis = analyzer.analyze(new_items)

            print(f"✅ AI 分析完成")
            print(f"   - 趋势数: {len(ai_analysis.get('trends', []))}")
            print(f"   - TOP 新闻: {len(ai_analysis.get('top_news', []))}")

            # 如果有翻译后的数据，使用翻译后的数据替换原始数据
            if ai_analysis and ai_analysis.get('translated_items'):
                new_items = ai_analysis['translated_items']
                print(f"✅ 使用翻译后的新闻数据")
        except Exception as e:
            print(f"⚠️  AI 分析失败: {e}")
            print(f"   继续使用传统方式发送邮件...")
            ai_analysis = None

    # 发送邮件
    if new_items:
        print(f"\n共发现 {len(new_items)} 条新内容")
        subject, content = mailer.format_news_email(new_items, ai_analysis=ai_analysis)

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
    print(f"{'='*50}\n")


def main():
    """主程序入口"""
    print("WhatsNew 新闻聚合平台启动")

    # 加载配置
    config = Config('config.yaml')
    interval = config.get('schedule.interval_hours', 1)

    print(f"调度间隔: 每 {interval} 小时")
    print(f"按 Ctrl+C 退出\n")

    # 立即执行一次
    run_task()

    # 设置定时任务
    schedule.every(interval).hours.do(run_task)

    # 循环执行
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次
    except KeyboardInterrupt:
        print("\n程序已停止")


if __name__ == '__main__':
    main()
