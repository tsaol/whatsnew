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
