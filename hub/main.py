#!/usr/bin/env python3
"""Content Hub 入口 - CLI 命令行工具"""
import argparse
import json
import sys
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.config import Config
from src.fetcher import ContentFetcher
from src.storage import ContentStorage
from src.search import ContentSearch


def print_results(results, verbose=False):
    """打印搜索结果"""
    if not results:
        print("没有找到结果")
        return

    print(f"\n找到 {len(results)} 条结果:\n")
    print("-" * 80)

    for i, result in enumerate(results, 1):
        title = result.get('title', '无标题')
        source = result.get('source', '未知来源')
        category = result.get('category', '')
        url = result.get('url', '')
        score = result.get('_score', 0)
        published = result.get('published_at', '')[:10] if result.get('published_at') else ''

        print(f"{i}. [{source}] {title}")
        if category:
            print(f"   分类: {category}")
        if published:
            print(f"   日期: {published}")
        if score:
            print(f"   相关度: {score:.4f}")
        if url:
            print(f"   链接: {url}")

        if verbose and result.get('content'):
            content_preview = result['content'][:200].replace('\n', ' ')
            print(f"   摘要: {content_preview}...")

        print()

    print("-" * 80)


def cmd_search(args, config):
    """执行搜索"""
    storage = ContentStorage(config)
    search = ContentSearch(storage)

    filters = {}
    if args.source:
        filters['source'] = args.source
    if args.category:
        filters['category'] = args.category
    if args.date_from:
        filters['date_from'] = args.date_from
    if args.date_to:
        filters['date_to'] = args.date_to

    if args.fulltext:
        results = search.full_text_search(args.query, args.top_k, filters or None)
    elif args.hybrid:
        results = search.hybrid_search(args.query, args.top_k, filters or None)
    else:
        results = search.search(args.query, args.top_k, filters or None)

    print_results(results, args.verbose)


def cmd_index(args, config):
    """索引文章"""
    fetcher = ContentFetcher(config)
    storage = ContentStorage(config)

    if args.url:
        # 索引单个 URL
        article = fetcher.fetch_full_content(args.url)
        if article:
            if storage.add_article(article):
                storage.save_to_s3(article)
                print(f"成功索引: {article['title']}")
            else:
                print("索引失败")
        else:
            print("抓取失败")

    elif args.file:
        # 从 JSON 文件索引
        with open(args.file, 'r', encoding='utf-8') as f:
            items = json.load(f)

        if isinstance(items, dict):
            items = items.get('items', [items])

        articles = fetcher.fetch_batch(items)
        success, failed = storage.add_batch(articles)

        for article in articles:
            storage.save_to_s3(article)

        print(f"完成: {success} 成功, {failed} 失败")

    elif args.from_daily:
        # 从日报数据索引
        import boto3
        from datetime import datetime, timedelta, timezone

        s3 = boto3.client('s3')
        bucket = 'cls-whatsnew'
        beijing_tz = timezone(timedelta(hours=8))
        date_str = args.date or datetime.now(beijing_tz).strftime('%Y-%m-%d')

        key = f'ai/{date_str}.json'
        try:
            response = s3.get_object(Bucket=bucket, Key=key)
            data = json.loads(response['Body'].read())
            items = data.get('items', [])

            print(f"从 s3://{bucket}/{key} 加载 {len(items)} 条新闻")

            articles = fetcher.fetch_batch(items)
            success, failed = storage.add_batch(articles)

            for article in articles:
                storage.save_to_s3(article)

            print(f"完成: {success} 成功, {failed} 失败")

        except Exception as e:
            print(f"加载日报数据失败: {e}")

    else:
        print("请指定 --url, --file 或 --from-daily")


def cmd_stats(args, config):
    """显示统计信息"""
    storage = ContentStorage(config)
    search = ContentSearch(storage)

    stats = storage.get_stats()
    print("\n索引统计:")
    print(f"  状态: {stats.get('status')}")
    print(f"  索引: {stats.get('index')}")
    print(f"  文档数: {stats.get('doc_count', 'N/A')}")
    print(f"  大小: {stats.get('size_bytes', 0) / 1024 / 1024:.2f} MB")

    sources = search.list_sources()
    if sources:
        print("\n来源分布:")
        for s in sources[:10]:
            print(f"  {s['source']}: {s['count']}")

    categories = search.list_categories()
    if categories:
        print("\n类别分布:")
        for c in categories[:10]:
            print(f"  {c['category']}: {c['count']}")


def main():
    parser = argparse.ArgumentParser(
        description='Content Hub - WhatsNew 内容中心',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('--config', '-c', default='config.yaml',
                        help='配置文件路径')
    parser.add_argument('--no-s3', action='store_true',
                        help='不从 S3 加载配置')

    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # search 命令
    search_parser = subparsers.add_parser('search', help='搜索文章')
    search_parser.add_argument('query', help='搜索查询')
    search_parser.add_argument('-k', '--top-k', type=int, default=10,
                               help='返回结果数量 (默认: 10)')
    search_parser.add_argument('--fulltext', '-f', action='store_true',
                               help='使用全文搜索 (BM25)')
    search_parser.add_argument('--hybrid', '-H', action='store_true',
                               help='使用混合搜索')
    search_parser.add_argument('--source', '-s', help='按来源过滤')
    search_parser.add_argument('--category', help='按类别过滤')
    search_parser.add_argument('--date-from', help='开始日期 (YYYY-MM-DD)')
    search_parser.add_argument('--date-to', help='结束日期 (YYYY-MM-DD)')
    search_parser.add_argument('--verbose', '-v', action='store_true',
                               help='显示详细信息')

    # index 命令
    index_parser = subparsers.add_parser('index', help='索引文章')
    index_parser.add_argument('--url', '-u', help='抓取并索引单个 URL')
    index_parser.add_argument('--file', '-f', help='从 JSON 文件批量索引')
    index_parser.add_argument('--from-daily', '-d', action='store_true',
                              help='从日报数据索引')
    index_parser.add_argument('--date', help='指定日期 (YYYY-MM-DD), 用于 --from-daily')

    # stats 命令
    stats_parser = subparsers.add_parser('stats', help='显示统计信息')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # 加载配置
    config = Config(args.config, use_s3=not args.no_s3)

    # 执行命令
    if args.command == 'search':
        cmd_search(args, config)
    elif args.command == 'index':
        cmd_index(args, config)
    elif args.command == 'stats':
        cmd_stats(args, config)


if __name__ == '__main__':
    main()
