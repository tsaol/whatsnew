#!/usr/bin/env python3
"""Content Hub 回填脚本 - 从 S3 日报归档回填缺失数据"""

import sys
import json
import boto3
import argparse
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, '/home/ubuntu/codes/whatsnew/hub')
sys.path.insert(0, '/home/ubuntu/codes/whatsnew/hub/src')

from src.config import Config
from src.fetcher import ContentFetcher
from src.storage import ContentStorage


def get_daily_json(s3_client, bucket: str, date_str: str) -> dict:
    """从 S3 获取日报 JSON"""
    key = f"ai/{date_str}.json"
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        return json.loads(response['Body'].read().decode('utf-8'))
    except Exception as e:
        print(f"[S3] 无法获取 {key}: {e}")
        return None


def backfill_date(config, fetcher, storage, s3_client, date_str: str, dry_run: bool = False) -> tuple:
    """回填指定日期的数据

    Returns:
        tuple: (成功数, 跳过数, 失败数)
    """
    print(f"\n{'='*60}")
    print(f"回填日期: {date_str}")
    print('='*60)

    # 获取日报数据
    data = get_daily_json(s3_client, 'cls-whatsnew', date_str)
    if not data:
        return 0, 0, 0

    items = data.get('items', [])
    print(f"找到 {len(items)} 条新闻")

    success = 0
    skipped = 0
    failed = 0

    for item in items:
        url = item.get('link')
        title = item.get('title', '')[:50]

        if not url:
            skipped += 1
            continue

        # 检查是否已存在 (通过 URL hash)
        import hashlib
        article_id = hashlib.md5(url.encode()).hexdigest()

        if dry_run:
            print(f"  [DRY-RUN] 将索引: {title}...")
            success += 1
            continue

        # 抓取全文
        metadata = {
            'title': item.get('title'),
            'source': item.get('source'),
            'category': item.get('category'),
            'published': item.get('published')
        }

        article = fetcher.fetch_full_content(url, metadata)
        if not article:
            print(f"  [跳过] 无法抓取: {title}...")
            failed += 1
            continue

        # 索引到 OpenSearch
        if storage.add_article(article):
            # 保存到 S3
            storage.save_to_s3(article)
            success += 1
        else:
            failed += 1

    print(f"\n日期 {date_str} 完成: {success} 成功, {skipped} 跳过, {failed} 失败")
    return success, skipped, failed


def main():
    parser = argparse.ArgumentParser(description='Content Hub 回填脚本')
    parser.add_argument('--start', required=True, help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end', required=True, help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--dry-run', action='store_true', help='仅显示将要执行的操作')
    parser.add_argument('--config', default='/home/ubuntu/codes/whatsnew/hub/config.yaml', help='配置文件路径')
    args = parser.parse_args()

    # 解析日期范围
    start_date = datetime.strptime(args.start, '%Y-%m-%d')
    end_date = datetime.strptime(args.end, '%Y-%m-%d')

    if start_date > end_date:
        print("错误: 开始日期必须早于结束日期")
        sys.exit(1)

    # 初始化
    print("初始化 Content Hub...")
    config = Config(args.config)
    fetcher = ContentFetcher(config)
    storage = ContentStorage(config)
    s3_client = boto3.client('s3')

    if args.dry_run:
        print("\n*** DRY-RUN 模式 - 不会实际写入数据 ***\n")

    # 遍历日期
    total_success = 0
    total_skipped = 0
    total_failed = 0

    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        success, skipped, failed = backfill_date(
            config, fetcher, storage, s3_client,
            date_str, args.dry_run
        )
        total_success += success
        total_skipped += skipped
        total_failed += failed
        current_date += timedelta(days=1)

    # 汇总
    print(f"\n{'='*60}")
    print("回填完成汇总")
    print('='*60)
    print(f"日期范围: {args.start} ~ {args.end}")
    print(f"成功: {total_success}")
    print(f"跳过: {total_skipped}")
    print(f"失败: {total_failed}")


if __name__ == '__main__':
    main()
