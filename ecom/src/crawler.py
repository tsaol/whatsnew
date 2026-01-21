"""爬虫模块 - 支持RSS订阅源和网页爬虫"""
import feedparser
import hashlib
import re
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup


class Crawler:
    # Agentic AI 相关关键词（用于过滤高价值内容）
    AGENT_KEYWORDS = [
        # 核心概念
        'agent', 'agentic', 'multi-agent', 'multiagent',
        'autonomous agent', 'ai agent', 'llm agent',
        # 工具和协议
        'mcp', 'model context protocol',
        'tool use', 'tool calling', 'function calling',
        'tool-use', 'tool-calling', 'function-calling',
        # 框架和技术
        'langchain', 'llamaindex', 'llama-index', 'langgraph',
        'crewai', 'crew ai', 'autogen', 'semantic kernel',
        'agent framework', 'agent orchestration',
        'dify', 'flowise', 'langflow',
        # RAG 和记忆
        'rag', 'retrieval augmented', 'retrieval-augmented',
        'vector database', 'embedding',
        # AWS 相关
        'bedrock agent', 'bedrock agents', 'amazon bedrock',
        'amazon q', 'sagemaker',
        # LLM 核心
        'claude', 'gpt-4', 'gpt4', 'llm', 'large language model',
        'anthropic', 'openai',
        'prompt engineering', 'prompt',
        # 其他 Agent 相关
        'chain of thought', 'cot', 'react pattern',
        'reflection', 'self-reflection',
        'code interpreter', 'code execution',
    ]

    # 电商 + AI 相关关键词
    ECOMMERCE_KEYWORDS = [
        # 电商核心
        'ecommerce', 'e-commerce', 'retail', 'shopping',
        'marketplace', 'online store', 'storefront',
        # 电商平台
        'shopify', 'amazon', 'alibaba', 'taobao', 'tmall',
        'ebay', 'etsy', 'walmart', 'jd.com', 'pinduoduo',
        # 推荐系统
        'recommendation', 'recommender', 'personalization',
        'collaborative filtering', 'content-based filtering',
        'product recommendation', 'similar products',
        # 搜索和排序
        'search ranking', 'product search', 'semantic search',
        'search relevance', 'query understanding',
        # 定价和库存
        'dynamic pricing', 'price optimization',
        'demand forecasting', 'inventory optimization',
        'supply chain', 'fulfillment',
        # 客户体验
        'chatbot', 'customer service', 'virtual assistant',
        'conversational commerce', 'voice commerce',
        # 视觉 AI
        'visual search', 'image recognition', 'virtual try-on',
        'product recognition', 'visual ai',
        # 广告和营销
        'ad targeting', 'marketing automation',
        'customer segmentation', 'churn prediction',
        'lifetime value', 'ltv', 'conversion optimization',
        # 支付和风控
        'fraud detection', 'payment', 'checkout',
        'risk assessment', 'anti-fraud',
        # 中文关键词
        '电商', '零售', '推荐系统', '个性化',
        '智能客服', '搜索排序', '供应链',
    ]

    # 排除关键词
    EXCLUDE_KEYWORDS = [
        # 人事/公司新闻（非技术）
        'appoints', 'appointed', 'hire', 'hiring',
        'office opening', 'headquarters',
        'valuation', 'funding round', 'series a', 'series b', 'series c',
    ]

    def __init__(self, storage, keyword_filter=None):
        self.storage = storage
        self.keyword_filter = keyword_filter  # None = 不过滤, 'agent' = Agent相关
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

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
            summary = entry.get('title', '暂无描述')

        return summary

    def _is_agent_related(self, title, summary):
        """检查内容是否与 Agent/Agentic AI 相关"""
        text = f"{title} {summary}".lower()

        # 先检查排除关键词
        for keyword in self.EXCLUDE_KEYWORDS:
            if keyword.lower() in text:
                return False

        # 再检查包含关键词
        for keyword in self.AGENT_KEYWORDS:
            if keyword.lower() in text:
                return True
        return False

    def _is_ecommerce_related(self, title, summary):
        """检查内容是否与电商 + AI 相关"""
        text = f"{title} {summary}".lower()

        # 先检查排除关键词
        for keyword in self.EXCLUDE_KEYWORDS:
            if keyword.lower() in text:
                return False

        # 检查电商关键词
        for keyword in self.ECOMMERCE_KEYWORDS:
            if keyword.lower() in text:
                return True
        return False

    def _should_include(self, title, summary, source_name):
        """判断是否应该包含这条新闻"""
        # 如果没有设置关键词过滤，包含所有
        if not self.keyword_filter:
            return True

        # Agent 相关源总是包含（仅限 agent 过滤模式）
        if self.keyword_filter == 'agent':
            agent_sources = ['LangChain', 'LlamaIndex', 'CrewAI', 'Semantic Kernel',
                            'Anthropic', 'Simon Willison', 'Latent Space']
            if any(s.lower() in source_name.lower() for s in agent_sources):
                return True
            return self._is_agent_related(title, summary)

        # 电商相关源总是包含（仅限 ecommerce 过滤模式）
        if self.keyword_filter == 'ecommerce':
            ecom_sources = ['Shopify', 'Amazon Science', 'eBay', 'Etsy', 'Walmart',
                           'Alibaba', 'Retail Dive', 'Pinterest', 'Instacart']
            if any(s.lower() in source_name.lower() for s in ecom_sources):
                return True
            return self._is_ecommerce_related(title, summary)

        return True

    def fetch_rss(self, url, source_name, max_items=5, max_days=2):
        """抓取RSS源"""
        print(f"正在抓取 {source_name} ...")

        try:
            feed = feedparser.parse(url)

            if feed.bozo:
                print(f"  警告: RSS解析可能有问题 - {source_name}")

            # 计算时间阈值
            cutoff_date = datetime.now() - timedelta(days=max_days)

            new_items = []
            filtered_count = 0
            keyword_filtered = 0

            for entry in feed.entries[:max_items * 3]:  # 多抓取一些
                # 检查发布日期
                published_time = entry.get('published_parsed') or entry.get('updated_parsed')
                if published_time:
                    try:
                        pub_datetime = datetime(*published_time[:6])
                        if pub_datetime < cutoff_date:
                            filtered_count += 1
                            continue
                    except:
                        pass

                # 生成唯一ID
                item_id = self._generate_id(entry.get('link', entry.get('id', '')))

                # 检查是否已发送
                if self.storage.is_sent(item_id):
                    continue

                # 提取并清理信息
                title = self._clean_html(entry.get('title', '无标题'))
                summary = self._extract_summary(entry)

                # 关键词过滤
                if not self._should_include(title, summary, source_name):
                    keyword_filtered += 1
                    continue

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

            # 输出统计
            stats = []
            if filtered_count > 0:
                stats.append(f"过期 {filtered_count}")
            if keyword_filtered > 0:
                stats.append(f"关键词过滤 {keyword_filtered}")

            if stats:
                print(f"  找到 {len(new_items)} 条新内容 ({', '.join(stats)})")
            else:
                print(f"  找到 {len(new_items)} 条新内容")

            return new_items

        except Exception as e:
            print(f"  抓取失败 {source_name}: {e}")
            return []

    def fetch_web_anthropic(self, max_items=5, max_days=2):
        """爬取 Anthropic News"""
        source_name = "Anthropic News"
        print(f"正在抓取 {source_name} (网页) ...")

        try:
            resp = requests.get('https://www.anthropic.com/news',
                              headers=self.headers, timeout=15)
            soup = BeautifulSoup(resp.text, 'html.parser')

            # 找到所有新闻链接
            articles = soup.find_all('a', href=True)
            news_links = []
            seen_hrefs = set()
            for a in articles:
                href = a.get('href', '')
                if href.startswith('/news/') and href != '/news' and href not in seen_hrefs:
                    seen_hrefs.add(href)
                    news_links.append(href)

            new_items = []
            for href in news_links[:max_items * 2]:
                full_url = f"https://www.anthropic.com{href}"
                item_id = self._generate_id(full_url)

                if self.storage.is_sent(item_id):
                    continue

                # 获取文章详情页
                try:
                    detail_resp = requests.get(full_url, headers=self.headers, timeout=10)
                    detail_soup = BeautifulSoup(detail_resp.text, 'html.parser')

                    # 从 og:title 获取正确的标题
                    og_title = detail_soup.find('meta', {'property': 'og:title'})
                    title = og_title.get('content', '') if og_title else ''

                    # 备选：从 h1 获取
                    if not title:
                        h1 = detail_soup.find('h1')
                        title = h1.get_text(strip=True) if h1 else ''

                    # 备选：从 URL 生成
                    if not title:
                        title = href.split('/')[-1].replace('-', ' ').title()

                    # 从 og:description 获取摘要
                    og_desc = detail_soup.find('meta', {'property': 'og:description'})
                    summary = og_desc.get('content', '') if og_desc else ''

                    # 备选：meta description
                    if not summary:
                        meta_desc = detail_soup.find('meta', {'name': 'description'})
                        summary = meta_desc.get('content', '') if meta_desc else ''

                    # 备选：获取文章前几段
                    if not summary or len(summary) < 50:
                        paragraphs = detail_soup.find_all('p')
                        text_parts = []
                        for p in paragraphs[:3]:
                            text = p.get_text(strip=True)
                            if len(text) > 30:
                                text_parts.append(text)
                        if text_parts:
                            summary = ' '.join(text_parts)[:500]

                    # 获取日期
                    time_tag = detail_soup.find('time')
                    published = time_tag.get('datetime', '') if time_tag else ''

                    # 备选：从 article:published_time 获取
                    if not published:
                        pub_meta = detail_soup.find('meta', {'property': 'article:published_time'})
                        published = pub_meta.get('content', '') if pub_meta else ''

                except Exception as e:
                    # 从 URL 生成标题
                    title = href.split('/')[-1].replace('-', ' ').title()
                    summary = title
                    published = ''

                if not title:
                    continue

                item = {
                    'id': item_id,
                    'title': title,
                    'link': full_url,
                    'summary': summary or title,
                    'published': published,
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

    def fetch_web_langchain(self, max_items=5, max_days=2):
        """爬取 LangChain Blog"""
        source_name = "LangChain Blog"
        print(f"正在抓取 {source_name} (网页) ...")

        try:
            resp = requests.get('https://blog.langchain.dev/',
                              headers=self.headers, timeout=15)
            soup = BeautifulSoup(resp.text, 'html.parser')

            # 找文章卡片
            new_items = []
            seen_urls = set()

            # 找所有链接
            for a in soup.find_all('a', href=True):
                href = a.get('href', '')
                # LangChain 博客文章 URL 格式
                if href.startswith('https://blog.langchain.dev/') and \
                   len(href) > 35 and \
                   href not in seen_urls and \
                   not href.endswith('/tag/') and \
                   '/author/' not in href:

                    seen_urls.add(href)
                    title = a.get_text(strip=True)

                    if not title or len(title) < 10:
                        continue

                    item_id = self._generate_id(href)
                    if self.storage.is_sent(item_id):
                        continue

                    item = {
                        'id': item_id,
                        'title': title,
                        'link': href,
                        'summary': title,  # 简化，不获取详情
                        'published': '',
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

    def fetch_web_llamaindex(self, max_items=5, max_days=2):
        """爬取 LlamaIndex Blog"""
        source_name = "LlamaIndex Blog"
        print(f"正在抓取 {source_name} (网页) ...")

        try:
            resp = requests.get('https://www.llamaindex.ai/blog',
                              headers=self.headers, timeout=15)
            soup = BeautifulSoup(resp.text, 'html.parser')

            new_items = []
            seen_urls = set()
            cutoff = datetime.now() - timedelta(days=max_days)

            for a in soup.find_all('a', href=True):
                href = a.get('href', '')
                # LlamaIndex 博客文章 URL
                if '/blog/' in href and href != '/blog' and href not in seen_urls:
                    # 构建完整 URL
                    if href.startswith('/'):
                        full_url = f"https://www.llamaindex.ai{href}"
                    else:
                        full_url = href

                    seen_urls.add(href)
                    title = a.get_text(strip=True)

                    if not title or len(title) < 10:
                        continue

                    # 尝试从 URL 或标题中提取日期 (格式: YYYY-MM-DD)
                    pub_date = ''
                    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', href + ' ' + title)
                    if date_match:
                        pub_date = date_match.group(1)
                        # 检查日期是否在时间范围内
                        try:
                            item_date = datetime.strptime(pub_date, '%Y-%m-%d')
                            if item_date < cutoff:
                                continue  # 跳过过期内容
                        except:
                            pass

                    item_id = self._generate_id(full_url)
                    if self.storage.is_sent(item_id):
                        continue

                    item = {
                        'id': item_id,
                        'title': title,
                        'link': full_url,
                        'summary': title,
                        'published': pub_date,
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

    def fetch_all(self, sources, max_items=5, max_days=2):
        """抓取所有新闻源"""
        all_items = []

        for source in sources:
            if not source.get('enabled', True):
                continue

            source_type = source.get('type', 'rss')
            source_name = source.get('name', '')

            if source_type == 'rss':
                items = self.fetch_rss(
                    source['url'],
                    source_name,
                    max_items,
                    max_days
                )
                all_items.extend(items)
            elif source_type == 'web':
                # 网页爬虫
                web_func = source.get('web_func', '')
                if web_func == 'anthropic':
                    items = self.fetch_web_anthropic(max_items, max_days)
                elif web_func == 'langchain':
                    items = self.fetch_web_langchain(max_items, max_days)
                elif web_func == 'llamaindex':
                    items = self.fetch_web_llamaindex(max_items, max_days)
                else:
                    print(f"  未知的爬虫函数: {web_func}")
                    items = []
                all_items.extend(items)
            else:
                print(f"不支持的源类型: {source_type}")

        # Newsletter 去重：同一来源的 Newsletter 只保留最新一条
        all_items = self._dedup_newsletters(all_items)

        # 过滤企业新闻（对所有来源）
        all_items = self._filter_corporate_news(all_items)

        return all_items

    def _dedup_newsletters(self, items):
        """Newsletter 去重：同一来源只保留最新一条"""
        newsletter_keywords = ['newsletter', 'weekly', 'roundup', 'digest', 'recap']

        # 按来源分组 Newsletter
        newsletters_by_source = {}
        other_items = []

        for item in items:
            title_lower = item.get('title', '').lower()
            is_newsletter = any(kw in title_lower for kw in newsletter_keywords)

            if is_newsletter:
                source = item.get('source', '')
                if source not in newsletters_by_source:
                    newsletters_by_source[source] = item
                # 保留第一个（通常是最新的）
            else:
                other_items.append(item)

        # 统计去重数量
        deduped_count = sum(1 for items in newsletters_by_source.values()) if newsletters_by_source else 0
        original_newsletter_count = sum(1 for item in items
                                       if any(kw in item.get('title', '').lower() for kw in newsletter_keywords))
        removed = original_newsletter_count - deduped_count

        if removed > 0:
            print(f"  [Newsletter 去重] 移除 {removed} 条重复 Newsletter")

        # 合并结果
        return other_items + list(newsletters_by_source.values())

    def _filter_corporate_news(self, items):
        """过滤企业新闻（人事、政策等非技术内容）和低价值内容"""
        corporate_keywords = [
            'appoints', 'appointed', 'hire', 'hiring', 'joins',
            'office opening', 'headquarters', 'expansion',
            'funding', 'valuation', 'series a', 'series b', 'series c', 'series d', 'series e', 'series f',
            'compliance', 'regulatory', 'policy response',
            'managing director', 'ceo', 'cto', 'cfo',
        ]

        # 低价值内容模式（如纯引用、转发）
        low_value_patterns = [
            'quoting ',  # Quoting someone
            'via @',     # Twitter quote
            'rt @',      # Retweet
        ]

        filtered_items = []
        removed_count = 0

        for item in items:
            title_lower = item.get('title', '').lower()
            summary_lower = item.get('summary', '').lower()
            text = f"{title_lower} {summary_lower}"

            # 检查是否是企业新闻
            is_corporate = any(kw in text for kw in corporate_keywords)

            # 检查是否是低价值内容（纯引用、转发）
            is_low_value = any(pattern in title_lower for pattern in low_value_patterns)

            # 检查是否是纯项目链接（标题只有项目名，无描述）
            # 例如 "user/repo" 格式且标题和摘要相同
            is_bare_link = (
                '/' in item.get('title', '') and
                len(item.get('title', '').split()) <= 2 and
                item.get('title', '') == item.get('summary', '')
            )

            if is_corporate or is_low_value or is_bare_link:
                removed_count += 1
            else:
                filtered_items.append(item)

        if removed_count > 0:
            print(f"  [内容过滤] 移除 {removed_count} 条非技术/低价值内容")

        return filtered_items

    def _generate_id(self, text):
        """生成唯一ID"""
        return hashlib.md5(text.encode()).hexdigest()
