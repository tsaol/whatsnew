"""爬虫模块 - 支持RSS订阅源和网页爬虫"""
import feedparser
import hashlib
import json
import os
import re
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from dateutil.parser import parse as dateutil_parse


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

    # 排除关键词（明确与 Agent 无关的内容）
    EXCLUDE_KEYWORDS = [
        # 非 AI 编程语言/项目
        'programming language', 'compiler', 'interpreter',
        'syntax', 'parser', 'lexer',
        # 纯前端/后端
        'css', 'html', 'javascript framework',
        'react native', 'flutter', 'swift',
        # 游戏/娱乐
        'game', 'gaming', 'esports',
        # 硬件
        'hardware', 'chip', 'semiconductor',
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

    def _should_include(self, title, summary, source_name):
        """判断是否应该包含这条新闻"""
        # 如果没有设置关键词过滤，包含所有
        if not self.keyword_filter:
            return True

        # Agent 相关源总是包含
        agent_sources = ['LangChain', 'LlamaIndex', 'CrewAI', 'Semantic Kernel',
                        'Anthropic', 'Simon Willison', 'Latent Space']
        if any(s.lower() in source_name.lower() for s in agent_sources):
            return True

        # 检查关键词
        if self.keyword_filter == 'agent':
            return self._is_agent_related(title, summary)

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

                # 提取发布日期 (优先使用 parsed 格式)
                pub_date = ''
                published_time = entry.get('published_parsed') or entry.get('updated_parsed')
                if published_time:
                    try:
                        pub_date = datetime(*published_time[:6]).strftime('%Y-%m-%d')
                    except:
                        pass
                if not pub_date:
                    # 回退到字符串格式
                    pub_date = entry.get('published', '') or entry.get('updated', '')

                item = {
                    'id': item_id,
                    'title': title,
                    'link': entry.get('link', ''),
                    'summary': summary,
                    'published': pub_date,
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

            # 日期过滤
            cutoff_date = datetime.now() - timedelta(days=max_days)
            expired_count = 0

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
            for href in news_links[:max_items * 3]:
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

                    # 备选：从 "body-3 agate" div 获取 (Anthropic 特有格式)
                    if not published:
                        date_div = detail_soup.find('div', class_=lambda c: c and 'body-3' in c and 'agate' in c)
                        if date_div:
                            date_text = date_div.get_text(strip=True)
                            # 格式如 "Sep 29, 2025"
                            date_match = re.search(r'([A-Z][a-z]{2} \d{1,2}, \d{4})', date_text)
                            if date_match:
                                published = date_match.group(1)

                except Exception as e:
                    # 从 URL 生成标题
                    title = href.split('/')[-1].replace('-', ' ').title()
                    summary = title
                    published = ''

                if not title:
                    continue

                # 日期过滤
                if published:
                    try:
                        pub_datetime = dateutil_parse(published)
                        if pub_datetime.tzinfo:
                            pub_datetime = pub_datetime.replace(tzinfo=None)
                        if pub_datetime < cutoff_date:
                            expired_count += 1
                            continue  # 跳过过期内容
                    except:
                        pass  # 解析失败则不过滤

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

            # 打印统计
            if expired_count > 0:
                print(f"  找到 {len(new_items)} 条新内容 (过期 {expired_count})")
            else:
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
                        'published': datetime.now().strftime('%Y-%m-%d'),
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

    def fetch_web_tmtpost(self, max_items=5, max_days=2):
        """爬取钛媒体 AI 频道"""
        source_name = "钛媒体 AI"
        print(f"正在抓取 {source_name} (网页) ...")

        try:
            resp = requests.get('https://www.tmtpost.com/tag/1162442',
                              headers=self.headers, timeout=15)
            soup = BeautifulSoup(resp.text, 'html.parser')

            new_items = []
            seen_urls = set()

            # 找文章链接
            for a in soup.find_all('a', href=True):
                href = a.get('href', '')
                # 钛媒体文章格式: /数字.html 或完整URL
                if '/tml/' in href or (href.startswith('https://www.tmtpost.com/') and '.html' in href):
                    if href.startswith('/'):
                        full_url = f"https://www.tmtpost.com{href}"
                    else:
                        full_url = href

                    if full_url in seen_urls:
                        continue
                    seen_urls.add(full_url)

                    title = a.get_text(strip=True)
                    if not title or len(title) < 8:
                        continue

                    item_id = self._generate_id(full_url)
                    if self.storage.is_sent(item_id):
                        continue

                    item = {
                        'id': item_id,
                        'title': title,
                        'link': full_url,
                        'summary': title,
                        'published': datetime.now().strftime('%Y-%m-%d'),
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

    def fetch_web_xinzhiyuan(self, max_items=5, max_days=2):
        """爬取新智元"""
        source_name = "新智元"
        print(f"正在抓取 {source_name} (网页) ...")

        try:
            # 新智元主站
            resp = requests.get('https://www.xinzhiyuan.com/',
                              headers=self.headers, timeout=15)
            soup = BeautifulSoup(resp.text, 'html.parser')

            new_items = []
            seen_urls = set()

            # 查找文章链接
            for a in soup.find_all('a', href=True):
                href = a.get('href', '')
                # 新智元文章格式
                if '/article/' in href or '/news/' in href:
                    if href.startswith('/'):
                        full_url = f"https://www.xinzhiyuan.com{href}"
                    elif href.startswith('http'):
                        full_url = href
                    else:
                        continue

                    if full_url in seen_urls:
                        continue
                    seen_urls.add(full_url)

                    title = a.get_text(strip=True)
                    if not title or len(title) < 6:
                        continue

                    item_id = self._generate_id(full_url)
                    if self.storage.is_sent(item_id):
                        continue

                    item = {
                        'id': item_id,
                        'title': title,
                        'link': full_url,
                        'summary': title,
                        'published': datetime.now().strftime('%Y-%m-%d'),
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

    def fetch_web_36kr_ai(self, max_items=5, max_days=2):
        """爬取 36Kr AI 频道"""
        source_name = "36Kr AI"
        print(f"正在抓取 {source_name} (网页) ...")

        try:
            # 36Kr AI 频道
            resp = requests.get('https://36kr.com/information/AI/',
                              headers=self.headers, timeout=15)
            soup = BeautifulSoup(resp.text, 'html.parser')

            new_items = []
            seen_urls = set()

            # 查找文章链接
            for a in soup.find_all('a', href=True):
                href = a.get('href', '')
                # 36Kr 文章格式: /p/数字
                if '/p/' in href and href != '/p/':
                    if href.startswith('/'):
                        full_url = f"https://36kr.com{href}"
                    elif href.startswith('http'):
                        full_url = href
                    else:
                        continue

                    if full_url in seen_urls:
                        continue
                    seen_urls.add(full_url)

                    title = a.get_text(strip=True)
                    if not title or len(title) < 6:
                        continue

                    item_id = self._generate_id(full_url)
                    if self.storage.is_sent(item_id):
                        continue

                    item = {
                        'id': item_id,
                        'title': title,
                        'link': full_url,
                        'summary': title,
                        'published': datetime.now().strftime('%Y-%m-%d'),
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

    def fetch_web_jiqizhixin(self, max_items=5, max_days=2):
        """爬取机器之心"""
        source_name = "机器之心"
        print(f"正在抓取 {source_name} (网页) ...")

        try:
            # 机器之心主站
            resp = requests.get('https://www.jiqizhixin.com/',
                              headers=self.headers, timeout=15)
            soup = BeautifulSoup(resp.text, 'html.parser')

            new_items = []
            seen_urls = set()

            # 查找文章链接
            for a in soup.find_all('a', href=True):
                href = a.get('href', '')
                # 机器之心文章格式
                if '/article/' in href or '/daily/' in href:
                    if href.startswith('/'):
                        full_url = f"https://www.jiqizhixin.com{href}"
                    elif href.startswith('http'):
                        full_url = href
                    else:
                        continue

                    if full_url in seen_urls:
                        continue
                    seen_urls.add(full_url)

                    title = a.get_text(strip=True)
                    if not title or len(title) < 6:
                        continue

                    item_id = self._generate_id(full_url)
                    if self.storage.is_sent(item_id):
                        continue

                    item = {
                        'id': item_id,
                        'title': title,
                        'link': full_url,
                        'summary': title,
                        'published': datetime.now().strftime('%Y-%m-%d'),
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

    def fetch_web_github_trending(self, max_items=5, max_days=7):
        """爬取 GitHub Trending (最近7天高星项目)"""
        source_name = "GitHub Trending"
        print(f"正在抓取 {source_name} (GraphQL API) ...")

        token = self._load_github_token()
        if not token:
            print(f"  警告: GITHUB_TOKEN 未配置，跳过 {source_name}")
            return []

        # 计算日期范围
        days_ago = (datetime.now() - timedelta(days=max_days)).strftime("%Y-%m-%d")
        search_query = f"created:>{days_ago} sort:stars"

        graphql_query = """
        query($search_query: String!) {
          search(query: $search_query, type: REPOSITORY, first: 15) {
            edges {
              node {
                ... on Repository {
                  nameWithOwner
                  url
                  description
                  stargazerCount
                  createdAt
                  primaryLanguage {
                    name
                  }
                }
              }
            }
          }
        }
        """

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "WhatsNew-Crawler"
        }

        try:
            resp = requests.post(
                "https://api.github.com/graphql",
                json={"query": graphql_query, "variables": {"search_query": search_query}},
                headers=headers,
                timeout=30
            )

            if resp.status_code != 200:
                print(f"  GitHub API 返回 {resp.status_code}")
                return []

            data = resp.json()
            if "errors" in data:
                print(f"  GraphQL 错误: {data['errors']}")
                return []

            new_items = []
            edges = data.get("data", {}).get("search", {}).get("edges", [])

            for edge in edges:
                node = edge.get("node")
                if not node:
                    continue

                repo_url = node.get("url", "")
                item_id = self._generate_id(repo_url)

                if self.storage.is_sent(item_id):
                    continue

                owner_repo = node.get("nameWithOwner", "")
                description = node.get("description") or "(No description)"
                stars = node.get("stargazerCount", 0)
                language = node.get("primaryLanguage", {})
                lang_name = language.get("name", "Unknown") if language else "Unknown"
                created_at = node.get("createdAt", "")[:10]

                # 关键词过滤
                title = f"{owner_repo} - {description[:80]}"
                summary = f"Stars: {stars} | Lang: {lang_name} | {description}"
                if not self._should_include(title, summary, source_name):
                    continue

                item = {
                    'id': item_id,
                    'title': title,
                    'link': repo_url,
                    'summary': summary,
                    'published': created_at,
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

    def fetch_web_producthunt(self, max_items=5, max_days=2):
        """爬取 Product Hunt (每日热门产品)"""
        source_name = "Product Hunt"
        print(f"正在抓取 {source_name} ...")

        token = self._load_producthunt_token()

        # 策略1: 使用 GraphQL API (需要 token)
        if token:
            print(f"  使用 GraphQL API...")
            try:
                items = self._fetch_producthunt_api(token, max_items)
                if items:
                    return items
            except Exception as e:
                print(f"  API 失败: {e}, 尝试 Hydration 提取...")

        # 策略2: Next.js Hydration 提取 (无需 token)
        print(f"  使用 Hydration 提取...")
        return self._fetch_producthunt_hydration(max_items)

    def _fetch_producthunt_api(self, token, max_items):
        """Product Hunt GraphQL API"""
        query = """
        query {
          posts(first: %d, order: VOTES) {
            edges {
              node {
                name
                tagline
                url
                votesCount
                slug
                topics {
                  edges {
                    node {
                      name
                    }
                  }
                }
              }
            }
          }
        }
        """ % (max_items * 2)

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        resp = requests.post(
            "https://api.producthunt.com/v2/api/graphql",
            json={"query": query},
            headers=headers,
            timeout=15
        )

        data = resp.json()
        new_items = []

        if "data" in data and "posts" in data["data"]:
            for edge in data["data"]["posts"]["edges"]:
                node = edge["node"]
                slug = node.get("slug")
                ph_url = f"https://www.producthunt.com/posts/{slug}" if slug else node.get("url", "")

                item_id = self._generate_id(ph_url)
                if self.storage.is_sent(item_id):
                    continue

                name = node.get("name", "")
                tagline = node.get("tagline", "")
                votes = node.get("votesCount", 0)
                topics = [t["node"]["name"] for t in node.get("topics", {}).get("edges", [])][:3]

                title = f"{name} - {tagline}"
                summary = f"Votes: {votes} | Topics: {', '.join(topics) if topics else 'N/A'}"

                # 关键词过滤
                if not self._should_include(title, summary, "Product Hunt"):
                    continue

                item = {
                    'id': item_id,
                    'title': title,
                    'link': ph_url,
                    'summary': summary,
                    'published': datetime.now().strftime('%Y-%m-%d'),
                    'source': "Product Hunt"
                }

                new_items.append(item)
                if len(new_items) >= max_items:
                    break

        print(f"  找到 {len(new_items)} 条新内容")
        return new_items

    def _fetch_producthunt_hydration(self, max_items):
        """从 Product Hunt 首页提取 __NEXT_DATA__"""
        try:
            resp = requests.get(
                "https://www.producthunt.com/",
                headers=self.headers,
                timeout=15
            )

            # 检查是否被 Cloudflare 阻止
            if resp.status_code == 403:
                print(f"  被 Cloudflare 阻止 (403)，建议配置 PRODUCTHUNT_TOKEN")
                return []

            # 提取 __NEXT_DATA__
            match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>', resp.text)
            if not match:
                print(f"  未找到 __NEXT_DATA__，建议配置 PRODUCTHUNT_TOKEN")
                return []

            data = json.loads(match.group(1))
            apollo_state = data.get("props", {}).get("pageProps", {}).get("apolloState", {})

            # 提取 Post 对象
            all_posts = []
            for key, value in apollo_state.items():
                if key.startswith("Post:") and isinstance(value, dict):
                    if "name" in value and "votesCount" in value:
                        all_posts.append(value)

            # 按投票数排序
            all_posts.sort(key=lambda x: x.get("votesCount", 0), reverse=True)

            new_items = []
            for post in all_posts:
                slug = post.get("slug")
                ph_url = f"https://www.producthunt.com/posts/{slug}" if slug else ""

                if not ph_url:
                    continue

                item_id = self._generate_id(ph_url)
                if self.storage.is_sent(item_id):
                    continue

                name = post.get("name", "Unknown")
                tagline = post.get("tagline", "")
                votes = post.get("votesCount", 0)

                title = f"{name} - {tagline}"
                summary = f"Votes: {votes}"

                # 关键词过滤
                if not self._should_include(title, summary, "Product Hunt"):
                    continue

                item = {
                    'id': item_id,
                    'title': title,
                    'link': ph_url,
                    'summary': summary,
                    'published': datetime.now().strftime('%Y-%m-%d'),
                    'source': "Product Hunt"
                }

                new_items.append(item)
                if len(new_items) >= max_items:
                    break

            print(f"  找到 {len(new_items)} 条新内容")
            return new_items

        except Exception as e:
            print(f"  Hydration 提取失败: {e}")
            return []

    def fetch_web_hn_blogs(self, max_items=5, max_days=2):
        """爬取 HN Top Blogs (技术博客精选)"""
        source_name = "HN Blog"
        print(f"正在抓取 {source_name} (OPML) ...")

        # OPML 源
        opml_url = "https://gist.githubusercontent.com/emschwartz/e6d2bf860ccc367fe37ff953ba6de66b/raw/hn-popular-blogs-2025.opml"

        # Fallback 博客列表
        fallback_feeds = [
            {"title": "Simon Willison", "rss": "https://simonwillison.net/atom/everything/"},
            {"title": "Mitchell Hashimoto", "rss": "https://mitchellh.com/feed.xml"},
            {"title": "antirez", "rss": "http://antirez.com/rss"},
            {"title": "Paul Graham", "rss": "http://www.aaronsw.com/2002/feeds/pgessays.rss"},
            {"title": "Pluralistic", "rss": "https://pluralistic.net/feed/"},
        ]

        # 获取博客列表
        blogs = []
        try:
            resp = requests.get(opml_url, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                # 解析 OPML
                pattern = r'<outline[^>]+type="rss"[^>]*>'
                for match in re.finditer(pattern, resp.text):
                    outline = match.group(0)
                    text_match = re.search(r'text="([^"]+)"', outline)
                    xml_url_match = re.search(r'xmlUrl="([^"]+)"', outline)
                    if text_match and xml_url_match:
                        blogs.append({
                            "title": text_match.group(1),
                            "rss": xml_url_match.group(1)
                        })
                print(f"  从 OPML 获取 {len(blogs)} 个博客")
        except Exception as e:
            print(f"  OPML 获取失败: {e}")

        if not blogs:
            print(f"  使用 Fallback 博客列表")
            blogs = fallback_feeds

        # 抓取 RSS
        cutoff_date = datetime.now() - timedelta(days=max_days)
        new_items = []
        max_blogs = 15  # 限制抓取博客数量

        for blog in blogs[:max_blogs]:
            try:
                feed_resp = requests.get(blog["rss"], headers=self.headers, timeout=10)
                if feed_resp.status_code != 200:
                    continue

                # 解析 RSS/Atom
                articles = self._parse_blog_feed(feed_resp.text, blog["title"], cutoff_date)
                for article in articles[:2]:  # 每个博客最多2篇
                    item_id = self._generate_id(article['link'])
                    if self.storage.is_sent(item_id):
                        continue

                    # 关键词过滤
                    if not self._should_include(article['title'], article['summary'], f"HN Blog: {blog['title']}"):
                        continue

                    item = {
                        'id': item_id,
                        'title': article['title'],
                        'link': article['link'],
                        'summary': article['summary'][:500],
                        'published': article['published'],
                        'source': f"HN Blog: {blog['title']}"
                    }

                    new_items.append(item)
                    if len(new_items) >= max_items:
                        break

            except Exception:
                continue

            if len(new_items) >= max_items:
                break

        print(f"  找到 {len(new_items)} 条新内容")
        return new_items

    def _parse_blog_feed(self, feed_content, blog_title, cutoff_date):
        """解析 RSS/Atom feed"""
        articles = []
        try:
            root = ET.fromstring(feed_content)

            # Atom feed
            if 'atom' in root.tag.lower() or root.tag == '{http://www.w3.org/2005/Atom}feed':
                ns = {'atom': 'http://www.w3.org/2005/Atom'}
                entries = root.findall('.//atom:entry', ns) or root.findall('.//entry')
                for entry in entries[:5]:
                    title = entry.find('atom:title', ns) or entry.find('title')
                    link = entry.find('atom:link[@rel="alternate"]', ns) or entry.find('atom:link', ns) or entry.find('link')
                    published = entry.find('atom:published', ns) or entry.find('atom:updated', ns) or entry.find('published') or entry.find('updated')
                    summary = entry.find('atom:summary', ns) or entry.find('atom:content', ns) or entry.find('summary') or entry.find('content')

                    title_text = title.text if title is not None and title.text else "Untitled"
                    link_href = link.get('href', '') if link is not None else ""
                    pub_text = published.text[:10] if published is not None and published.text else ""
                    content_text = self._clean_html(summary.text) if summary is not None and summary.text else ""

                    # 日期过滤
                    if pub_text:
                        try:
                            pub_datetime = datetime.fromisoformat(pub_text.replace('Z', '+00:00').split('T')[0])
                            if pub_datetime < cutoff_date:
                                continue
                        except:
                            pass

                    if title_text and link_href:
                        articles.append({
                            'title': title_text,
                            'link': link_href,
                            'published': pub_text,
                            'summary': content_text or title_text
                        })

            # RSS 2.0
            else:
                items = root.findall('.//item')
                for item in items[:5]:
                    title = item.find('title')
                    link = item.find('link')
                    pub_date = item.find('pubDate')
                    description = item.find('description')

                    title_text = title.text if title is not None and title.text else "Untitled"
                    link_text = link.text if link is not None and link.text else ""
                    pub_text = ""
                    if pub_date is not None and pub_date.text:
                        # 解析 RFC 822 日期
                        try:
                            parsed = dateutil_parse(pub_date.text)
                            pub_text = parsed.strftime('%Y-%m-%d')
                            if parsed.replace(tzinfo=None) < cutoff_date:
                                continue
                        except:
                            pub_text = pub_date.text[:16]

                    content_text = self._clean_html(description.text) if description is not None and description.text else ""

                    if title_text and link_text:
                        articles.append({
                            'title': title_text,
                            'link': link_text,
                            'published': pub_text,
                            'summary': content_text or title_text
                        })

        except ET.ParseError:
            pass
        except Exception:
            pass

        return articles

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
                elif web_func == 'tmtpost':
                    items = self.fetch_web_tmtpost(max_items, max_days)
                elif web_func == 'xinzhiyuan':
                    items = self.fetch_web_xinzhiyuan(max_items, max_days)
                elif web_func == '36kr_ai':
                    items = self.fetch_web_36kr_ai(max_items, max_days)
                elif web_func == 'jiqizhixin':
                    items = self.fetch_web_jiqizhixin(max_items, max_days)
                elif web_func == 'github_trending':
                    items = self.fetch_web_github_trending(max_items, max_days)
                elif web_func == 'producthunt':
                    items = self.fetch_web_producthunt(max_items, max_days)
                elif web_func == 'hn_blogs':
                    items = self.fetch_web_hn_blogs(max_items, max_days)
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

    def _load_github_token(self):
        """加载 GitHub Token"""
        # 环境变量优先
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            return token

        # 尝试从 .env 文件加载
        env_paths = [
            os.path.join(os.path.dirname(__file__), "..", ".env"),
            os.path.join(os.getcwd(), ".env"),
        ]
        for env_path in env_paths:
            if os.path.exists(env_path):
                try:
                    with open(env_path, "r", encoding="utf-8-sig") as f:
                        for line in f:
                            line = line.strip()
                            if not line or line.startswith("#"):
                                continue
                            if "GITHUB_TOKEN=" in line:
                                return line.split("=", 1)[1].strip()
                            # 支持裸 token 格式
                            if line.startswith("ghp_") or line.startswith("github_pat_"):
                                return line
                except Exception:
                    pass
        return None

    def _load_producthunt_token(self):
        """加载 Product Hunt Token"""
        # 环境变量优先
        token = os.environ.get("PRODUCTHUNT_TOKEN")
        if token:
            return token

        # 尝试从 .env 文件加载
        env_paths = [
            os.path.join(os.path.dirname(__file__), "..", ".env"),
            os.path.join(os.getcwd(), ".env"),
        ]
        for env_path in env_paths:
            if os.path.exists(env_path):
                try:
                    with open(env_path, "r", encoding="utf-8-sig") as f:
                        for line in f:
                            if "PRODUCTHUNT_TOKEN" in line:
                                parts = line.strip().split("=", 1)
                                if len(parts) == 2:
                                    token = parts[1].strip().strip('"').strip("'")
                                    if token:
                                        return token
                except Exception:
                    pass
        return None

    def _generate_id(self, text):
        """生成唯一ID"""
        return hashlib.md5(text.encode()).hexdigest()
