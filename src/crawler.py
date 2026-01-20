"""爬虫模块 - 支持RSS订阅源"""
import feedparser
import hashlib
import re
from datetime import datetime, timedelta
import time


class Crawler:
    def __init__(self, storage):
        self.storage = storage

    def _clean_html(self, text):
        """清理 HTML 标签和多余空白"""
        if not text:
            return ""

        # 移除 HTML 标签
        text = re.sub(r'<[^>]+>', '', text)

        # 解码 HTML 实体
        text = text.replace('&lt;', '<').replace('&gt;', '>') \
                   .replace('&amp;', '&').replace('&quot;', '"') \
                   .replace('&#39;', "'").replace('&nbsp;', ' ')

        # 移除多余空白
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def _extract_summary(self, entry):
        """智能提取摘要"""
        # 尝试多个字段
        summary = entry.get('summary', '') or \
                  entry.get('description', '') or \
                  entry.get('content', [{}])[0].get('value', '') if entry.get('content') else ''

        # 清理 HTML
        summary = self._clean_html(summary)

        # 如果摘要太短或无效，尝试使用标题
        if not summary or len(summary) < 20 or summary.lower() == 'comments':
            # 对于 Hacker News 这类，使用标题作为摘要
            summary = entry.get('title', '暂无描述')

        return summary

    def fetch_rss(self, url, source_name, max_items=5, max_days=2):
        """抓取RSS源

        Args:
            url: RSS源地址
            source_name: 来源名称
            max_items: 最多抓取条数
            max_days: 最多几天前的新闻（默认2天，即48小时）
        """
        print(f"正在抓取 {source_name} ...")

        try:
            feed = feedparser.parse(url)

            if feed.bozo:
                print(f"  警告: RSS解析可能有问题 - {source_name}")

            # 计算时间阈值
            cutoff_date = datetime.now() - timedelta(days=max_days)

            new_items = []
            filtered_count = 0

            for entry in feed.entries[:max_items * 2]:  # 多抓取一些以防都是旧的
                # 检查发布日期
                published_time = entry.get('published_parsed') or entry.get('updated_parsed')
                if published_time:
                    try:
                        pub_datetime = datetime(*published_time[:6])
                        if pub_datetime < cutoff_date:
                            filtered_count += 1
                            continue  # 跳过超过 max_days 天的新闻
                    except Exception as e:
                        # 如果日期解析失败，保留这条新闻
                        pass

                # 生成唯一ID
                item_id = self._generate_id(entry.get('link', entry.get('id', '')))

                # 检查是否已发送
                if self.storage.is_sent(item_id):
                    continue

                # 提取并清理信息
                title = self._clean_html(entry.get('title', '无标题'))
                summary = self._extract_summary(entry)

                # 提取信息
                item = {
                    'id': item_id,
                    'title': title,
                    'link': entry.get('link', ''),
                    'summary': summary,
                    'published': entry.get('published', ''),
                    'source': source_name
                }

                new_items.append(item)

                if len(new_items) >= max_items:
                    break

            if filtered_count > 0:
                print(f"  找到 {len(new_items)} 条新内容 (过滤掉 {filtered_count} 条过期新闻)")
            else:
                print(f"  找到 {len(new_items)} 条新内容")
            return new_items

        except Exception as e:
            print(f"  抓取失败 {source_name}: {e}")
            return []

    def fetch_all(self, sources, max_items=5, max_days=2):
        """抓取所有新闻源

        Args:
            sources: 新闻源列表
            max_items: 每个源最多抓取条数
            max_days: 最多几天前的新闻（默认2天，即48小时）
        """
        all_items = []

        for source in sources:
            source_type = source.get('type', 'rss')

            if source_type == 'rss':
                items = self.fetch_rss(
                    source['url'],
                    source['name'],
                    max_items,
                    max_days
                )
                all_items.extend(items)
            else:
                print(f"不支持的源类型: {source_type}")

        return all_items

    def _generate_id(self, text):
        """生成唯一ID"""
        return hashlib.md5(text.encode()).hexdigest()
