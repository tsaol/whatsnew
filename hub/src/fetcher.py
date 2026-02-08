"""全文抓取器 - 使用 trafilatura 提取正文"""
import hashlib
import requests
from datetime import datetime, timezone, timedelta
from typing import Optional

try:
    import trafilatura
except ImportError:
    trafilatura = None


class ContentFetcher:
    def __init__(self, config):
        self.config = config
        self.fetch_config = config.fetch_config
        self.timeout = self.fetch_config.get('timeout', 30)
        self.max_content_length = self.fetch_config.get('max_content_length', 50000)
        self.user_agent = self.fetch_config.get(
            'user_agent',
            'WhatsNew ContentHub/1.0'
        )
        self.headers = {
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }

    def fetch_full_content(self, url: str, metadata: dict = None) -> Optional[dict]:
        """抓取并提取文章全文

        Args:
            url: 文章 URL
            metadata: 可选的元数据 (title, source, category 等)

        Returns:
            dict: {id, url, title, content, author, published_at, source, category, ...}
        """
        if trafilatura is None:
            print("[Fetcher] trafilatura 未安装，请运行 pip install trafilatura")
            return None

        try:
            # 获取页面
            response = requests.get(
                url,
                headers=self.headers,
                timeout=self.timeout,
                allow_redirects=True
            )
            response.raise_for_status()
            html = response.text

            # 使用 trafilatura 提取正文
            content = trafilatura.extract(
                html,
                include_comments=False,
                include_tables=True,
                include_images=False,
                include_links=False,
                output_format='txt'
            )

            if not content:
                print(f"[Fetcher] 无法提取正文: {url}")
                return None

            # 截断过长内容
            if len(content) > self.max_content_length:
                content = content[:self.max_content_length] + '...[内容已截断]'

            # 提取元数据 (bare_extraction 返回 Document 对象)
            extracted = trafilatura.bare_extraction(html)

            # 生成唯一 ID
            article_id = self._generate_id(url)

            # 从 Document 对象提取属性
            extracted_title = getattr(extracted, 'title', None) if extracted else None
            extracted_author = getattr(extracted, 'author', None) if extracted else None
            extracted_date = getattr(extracted, 'date', None) if extracted else None

            # 构建结果
            beijing_tz = timezone(timedelta(hours=8))
            result = {
                'id': article_id,
                'url': url,
                'title': (metadata or {}).get('title') or extracted_title or '',
                'content': content,
                'author': extracted_author,
                'published_at': self._parse_date(extracted_date),
                'source': (metadata or {}).get('source', ''),
                'category': (metadata or {}).get('category', ''),
                'fetched_at': datetime.now(beijing_tz).isoformat(),
                'content_length': len(content)
            }

            print(f"[Fetcher] 抓取成功: {result['title'][:50]}... ({len(content)} 字符)")
            return result

        except requests.RequestException as e:
            print(f"[Fetcher] 请求失败 {url}: {e}")
            return None
        except Exception as e:
            print(f"[Fetcher] 处理失败 {url}: {e}")
            return None

    def fetch_batch(self, items: list) -> list:
        """批量抓取文章全文

        Args:
            items: 新闻列表，每项包含 {link, title, source, category, ...}

        Returns:
            list: 成功抓取的文章列表
        """
        results = []
        for item in items:
            url = item.get('link') or item.get('url')
            if not url:
                continue

            metadata = {
                'title': item.get('title'),
                'source': item.get('source'),
                'category': item.get('category')
            }

            article = self.fetch_full_content(url, metadata)
            if article:
                results.append(article)

        print(f"[Fetcher] 批量抓取完成: {len(results)}/{len(items)} 成功")
        return results

    def _generate_id(self, url: str) -> str:
        """生成文章唯一 ID"""
        return hashlib.md5(url.encode()).hexdigest()

    def _parse_date(self, date_str: str) -> Optional[str]:
        """解析日期字符串为 ISO 格式"""
        if not date_str:
            return None

        try:
            # trafilatura 通常返回 YYYY-MM-DD 格式
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            return dt.isoformat()
        except:
            return date_str
