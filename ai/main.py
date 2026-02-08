"""WhatsNew - 新闻爬虫聚合平台主程序"""
import time
import schedule
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from src.config import Config
from src.storage import Storage
from src.crawler import Crawler
from src.mailer import Mailer


# 北京时区
BEIJING_TZ = timezone(timedelta(hours=8))


def index_to_hub(items):
    """将新闻索引到 Content Hub"""
    try:
        # 添加 hub 模块路径
        hub_path = Path(__file__).parent.parent / 'hub'
        if hub_path.exists():
            sys.path.insert(0, str(hub_path))
            from src.config import Config as HubConfig
            from src.storage import ContentStorage
            from src.fetcher import ContentFetcher

            print("\n[Hub] 开始索引到 Content Hub...")
            hub_config = HubConfig()
            storage = ContentStorage(hub_config)
            fetcher = ContentFetcher(hub_config)

            success = 0
            for item in items:
                url = item.get('link')
                if not url:
                    continue

                # 检查是否已存在
                article_id = fetcher._generate_id(url)
                if storage.exists(article_id):
                    continue

                # 抓取全文并索引
                article = fetcher.fetch_full_content(url, metadata={
                    'title': item.get('title'),
                    'source': item.get('source'),
                    'category': item.get('category')
                })

                if article and storage.add_article(article):
                    storage.save_to_s3(article)
                    success += 1

            print(f"[Hub] 索引完成: {success}/{len(items)} 篇")
        else:
            print("[Hub] hub 模块未找到，跳过索引")
    except Exception as e:
        print(f"[Hub] 索引失败: {e}")


def run_task():
    """执行一次任务"""
    separator = "=" * 50
    print(f"\n{separator}")
    print(f"开始执行任务...")
    print(separator)

    # 加载配置
    config = Config('config.yaml')

    # 初始化模块
    storage = Storage(config.get('data_file', 'data/sent_news.json'))
    keyword_filter = config.get('filter.keyword_filter', None)
    crawler = Crawler(storage, keyword_filter=keyword_filter)
    mailer = Mailer(config.email_config)

    # 抓取新闻
    sources = config.sources
    max_items = config.get('max_items_per_source', 5)
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
    if new_items:
        print(f"\n共发现 {len(new_items)} 条新内容")
        subject, content = mailer.format_news_email(new_items, ai_analysis=ai_analysis)

        if mailer.send(subject, content):
            # 标记为已发送
            for item in new_items:
                storage.mark_sent(
                    item['id'],
                    item['title'],
                    link=item.get('link'),
                    source=item.get('source'),
                    category=item.get('category')
                )
            print("所有新闻已发送并标记")

            # 索引到 Content Hub
            hub_enabled = config.get('hub.enabled', True)
            if hub_enabled:
                index_to_hub(new_items)
    else:
        print("没有新内容")

    # 统计信息
    stats = storage.get_stats()
    print(f"\n统计: 累计已发送 {stats['total_sent']} 条新闻")
    print(f"{separator}\n")


def run_weekly_task():
    """执行周报任务"""
    separator = "=" * 50
    print(f"\n{separator}")
    print(f"开始执行周报任务...")
    print(separator)

    # 加载配置
    config = Config('config.yaml')

    # 检查周报是否启用
    weekly_enabled = config.get('weekly.enabled', False)
    if not weekly_enabled:
        print("周报功能未启用，跳过")
        return

    # 初始化模块
    storage = Storage(config.get('data_file', 'data/sent_news.json'))
    mailer = Mailer(config.email_config)

    # 获取本周新闻
    lookback_days = config.get('weekly.lookback_days', 7)
    week_news = storage.get_week_news(days=lookback_days)

    if not week_news:
        print("本周没有新闻，跳过周报生成")
        return

    print(f"本周共有 {len(week_news)} 条新闻")

    # 计算周期
    beijing_now = datetime.now(BEIJING_TZ)
    week_end = beijing_now.date()
    week_start = week_end - timedelta(days=lookback_days - 1)

    # AI 分析
    try:
        print(f"\n[AI] 正在生成周报分析...")
        from src.analyzer import create_analyzer

        aws_region = config.get('ai.aws_region', 'us-west-2')
        top_n = config.get('weekly.top_n', 10)

        analyzer = create_analyzer(aws_region=aws_region)
        weekly_analysis = analyzer.analyze_weekly(week_news, top_n=top_n)

        print(f"[OK] 周报分析完成")
        print(f"   - 趋势数: {len(weekly_analysis.get('trends', []))}")
        print(f"   - TOP 新闻: {len(weekly_analysis.get('top_news', []))}")
        print(f"   - 重点事件: {len(weekly_analysis.get('highlights', []))}")

    except Exception as e:
        print(f"[WARN] 周报分析失败: {e}")
        weekly_analysis = {
            "summary": "",
            "trends": [],
            "top_news": week_news[:10],
            "highlights": [],
            "weekly_stats": {"total_news": len(week_news)}
        }

    # 发送周报邮件
    from datetime import date as date_type
    week_start_dt = datetime.combine(week_start, datetime.min.time())
    week_end_dt = datetime.combine(week_end, datetime.min.time())

    subject, content = mailer.format_weekly_email(weekly_analysis, week_start_dt, week_end_dt)

    if subject and content:
        if mailer.send(subject, content):
            print("周报发送成功！")

            # 保存周报摘要
            storage.save_weekly_summary({
                "week_start": str(week_start),
                "week_end": str(week_end),
                "total_news": len(week_news),
                "trends": weekly_analysis.get('trends', []),
                "summary": weekly_analysis.get('summary', '')
            })
        else:
            print("周报发送失败")

    print(f"{separator}\n")


def main():
    """主程序入口"""
    print("WhatsNew 新闻聚合平台启动")

    # 加载配置
    config = Config('config.yaml')

    # 日报调度
    beijing_time = config.get('schedule.daily_time', '06:00')
    hour, minute = map(int, beijing_time.split(':'))
    utc_hour = (hour - 8) % 24
    utc_time = f"{utc_hour:02d}:{minute:02d}"

    print(f"日报调度: 每天北京时间 {beijing_time} (UTC {utc_time})")

    # 周报调度
    weekly_enabled = config.get('weekly.enabled', False)
    if weekly_enabled:
        weekly_day = config.get('weekly.day_of_week', 0)  # 0=周一
        weekly_time = config.get('weekly.time', '09:00')
        day_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        print(f"周报调度: 每{day_names[weekly_day]}北京时间 {weekly_time}")
    else:
        print("周报调度: 未启用")

    print(f"按 Ctrl+C 退出\n")

    # 立即执行日报
    run_task()

    # 设置每日定时任务（使用UTC时间）
    schedule.every().day.at(utc_time).do(run_task)

    # 设置周报定时任务
    if weekly_enabled:
        weekly_time = config.get('weekly.time', '09:00')
        weekly_day = config.get('weekly.day_of_week', 0)
        w_hour, w_minute = map(int, weekly_time.split(':'))
        w_utc_hour = (w_hour - 8) % 24
        w_utc_time = f"{w_utc_hour:02d}:{w_minute:02d}"

        # 根据星期几设置调度
        day_schedulers = {
            0: schedule.every().monday,
            1: schedule.every().tuesday,
            2: schedule.every().wednesday,
            3: schedule.every().thursday,
            4: schedule.every().friday,
            5: schedule.every().saturday,
            6: schedule.every().sunday
        }
        day_schedulers[weekly_day].at(w_utc_time).do(run_weekly_task)

    # 显示下次执行时间
    next_run = schedule.next_run()
    if next_run:
        print(f"\n下次执行时间: {next_run.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        beijing_next = next_run + timedelta(hours=8)
        print(f"             ({beijing_next.strftime('%Y-%m-%d %H:%M:%S')} 北京时间)\n")

    # 循环执行
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次
    except KeyboardInterrupt:
        print("\n程序已停止")


if __name__ == '__main__':
    main()
