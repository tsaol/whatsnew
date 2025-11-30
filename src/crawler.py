"""爬虫模块 - 支持RSS订阅源"""
import feedparser
import hashlib
from datetime import datetime


class Crawler:
    def __init__(self, storage):
        self.storage = storage

    def fetch_rss(self, url, source_name, max_items=5):
        """抓取RSS源"""
        print(f"正在抓取 {source_name} ...")

        try:
            feed = feedparser.parse(url)

            if feed.bozo:
                print(f"  警告: RSS解析可能有问题 - {source_name}")

            new_items = []
            for entry in feed.entries[:max_items * 2]:  # 多抓取一些以防都是旧的
                # 生成唯一ID
                item_id = self._generate_id(entry.get('link', entry.get('id', '')))

                # 检查是否已发送
                if self.storage.is_sent(item_id):
                    continue

                # 提取信息
                item = {
                    'id': item_id,
                    'title': entry.get('title', '无标题'),
                    'link': entry.get('link', ''),
                    'summary': entry.get('summary', entry.get('description', '')),
                    'published': entry.get('published', ''),
                    'source': source_name
                }

                new_items.append(item)

                if len(new_items) >= max_items:
                    break

            print(f"  找到 {len(new_items)} 条新内容")
            return new_items

        except Exception as e:
            print(f"  抓取失败 {source_name}: {e}")
            return []

    def fetch_all(self, sources, max_items=5):
        """抓取所有新闻源"""
        all_items = []

        for source in sources:
            source_type = source.get('type', 'rss')

            if source_type == 'rss':
                items = self.fetch_rss(
                    source['url'],
                    source['name'],
                    max_items
                )
                all_items.extend(items)
            else:
                print(f"不支持的源类型: {source_type}")

        return all_items

    def _generate_id(self, text):
        """生成唯一ID"""
        return hashlib.md5(text.encode()).hexdigest()
