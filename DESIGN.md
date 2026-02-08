# WhatsNew - Design Document

## Target User

**AWS Solutions Architect** specializing in **Agentic AI**

## Core Requirements

### 1. Content Focus

**Primary Focus: Agentic AI**
- Agent frameworks: LangChain, LlamaIndex, CrewAI, AutoGen, Semantic Kernel
- MCP (Model Context Protocol) ecosystem
- Multi-agent systems and orchestration
- Tool Use / Function Calling
- Agent safety and security
- RAG and knowledge retrieval
- Enterprise agent deployment

**Secondary Focus: Broader AI**
- LLM updates (Claude, GPT, etc.)
- AI infrastructure (Bedrock, SageMaker)
- Cloud AI services (AWS, GCP, Azure)
- AI research and trends

### 2. Content Sources

#### Agent-Specific Sources (Always Include)
| Source | Type | Notes |
|--------|------|-------|
| Anthropic News | Web Crawler | MCP, Claude Agent |
| LangChain Blog | Web Crawler | Agent framework |
| LlamaIndex Blog | Web Crawler | RAG, Agent tools |
| CrewAI Blog | RSS | Multi-agent |
| Semantic Kernel | RSS | Enterprise agent |
| Simon Willison | RSS | LLM/Agent tools |
| Latent Space | RSS | AI engineering |

#### General AI Sources (Keyword Filtered)
| Source | Type | Notes |
|--------|------|-------|
| OpenAI Blog | RSS | Filter by keywords |
| Google AI Blog | RSS | Filter by keywords |
| AWS AI/ML Blogs | RSS | Filter by keywords |
| TechCrunch AI | RSS | Filter by keywords |
| Hugging Face | RSS | Filter by keywords |

### 3. Filtering Strategy

#### Keyword Filter (for general sources)
```python
INCLUDE_KEYWORDS = [
    'agent', 'agentic', 'multi-agent', 'mcp',
    'tool use', 'function calling', 'langchain',
    'llamaindex', 'rag', 'retrieval', 'bedrock',
    'claude', 'llm', 'prompt', ...
]

EXCLUDE_KEYWORDS = [
    'appoints', 'appointed', 'hiring', 'office opening',
    'funding round', 'valuation', 'programming language',
    'compiler', 'game', 'gaming', ...
]
```

#### Source-Level Filtering
- **Agent-specific sources**: No keyword filter, but filter corporate news
- **General sources**: Apply keyword filter strictly
- **Newsletter deduplication**: Keep only latest from same source

### 4. AI Analysis (Agentic AI Focus)

#### Scoring Criteria (1-10)
| Score | Criteria |
|-------|----------|
| 9-10 | Agent framework major updates, MCP progress, Agent safety breakthroughs |
| 7-8 | RAG advances, Tool Use updates, Agent dev tools |
| 5-6 | General LLM updates, cloud service updates |
| 3-4 | Corporate news, policy, non-technical |
| 1-2 | Marketing, unrelated content |

**Key Requirement**: Scores must have variance (not all 5s)

#### Trend Identification
- Focus on Agentic AI trends only
- 2-4 trends per analysis
- Return empty array if no clear Agent trends

#### TOP Recommendations
- Must include scoring reason (15-30 chars)
- Explain why it's valuable for Agentic AI expert

### 5. Content Categories (by Type)

News is organized by **content type** rather than by source, optimized for Agentic AI Expert:

| Category | Icon | Description | Priority |
|----------|------|-------------|----------|
| **Agent 专项** | A | Agent 框架、MCP、Multi-Agent、Tool Use | 1 (Highest) |
| **技术深度** | T | LLM、RAG、模型优化、算法创新 | 2 |
| **AWS 聚焦** | W | Bedrock、SageMaker、AWS AI 服务 | 3 |
| **行业动态** | I | 企业落地、应用案例、市场趋势 | 4 (Lowest) |

#### Category Assignment Rules
1. **Agent 专项** (highest priority): Any news mentioning Agent/Agentic AI frameworks, MCP, Tool Use
2. **AWS 聚焦**: AWS-related content prioritized for AWS SA audience
3. **技术深度**: Deep technical content (LLM, RAG, algorithms)
4. **行业动态**: Everything else (enterprise cases, market news)

#### Email Display Order
- TOP 新闻推荐 (sorted by score)
- Agent 专项 (most relevant to user)
- 技术深度 (technical depth)
- AWS 聚焦 (AWS SA focus)
- 行业动态 (general news)

### 6. Output Requirements

#### Email Format
- No emojis (user preference)
- Unified date format: YYYY-MM-DD
- Chinese translations for titles and summaries
- Clear score differentiation
- TOP recommendations with reasons
- **Content grouped by category** (not by source)

#### Quality Metrics
- High relevance to Agentic AI (>70% of content)
- Score variance (not uniform scores)
- Actionable trends
- Enhanced summaries (80-150 chars, technical depth)

---

## Technical Architecture

### Module Structure
```
whatsnew/
├── ai/                     # AI 日报实例
│   ├── src/
│   │   ├── config.py       # Configuration management
│   │   ├── crawler.py      # RSS + Web crawlers with keyword filter
│   │   ├── storage.py      # Deduplication and persistence
│   │   ├── analyzer.py     # LangGraph AI analysis (Agentic AI focus)
│   │   └── mailer.py       # Email generation with date formatting
│   └── data/
├── ecom/                   # 电商+AI 日报实例
│   ├── src/
│   └── data/
└── hub/                    # Content Hub (全文存储 + 语义搜索)
    ├── src/
    │   ├── config.py       # S3 + 本地配置加载
    │   ├── fetcher.py      # 全文抓取 (trafilatura)
    │   ├── storage.py      # OpenSearch Serverless 存储
    │   └── search.py       # 语义 + 全文搜索
    └── main.py             # CLI 入口
```

### Data Flow
```
Config
  → Crawl (RSS + Web)
  → Time Filter (max_days)
  → Keyword Filter (agent-related)
  → Deduplication
  → AI Analysis
    ├─ Categorize
    ├─ Filter (AI relevance)
    ├─ Score (Agentic AI focus)
    ├─ Enhance (summaries)
    ├─ Translate
    ├─ Trends (Agentic AI only)
    └─ Summarize
  → Email Generation
  → Send
  → Mark Sent
  → S3 Archive (HTML + JSON)
  → Content Hub Index (hook)
```

### Content Hub Data Flow
```
Daily Report Sent
  → Hook: index_to_hub()
  → For each news item:
      ├─ Fetch full content (trafilatura)
      ├─ Generate embedding (Cohere Multilingual v3)
      └─ Index to OpenSearch Serverless
```

### Web Crawlers

#### Anthropic News
- URL: https://www.anthropic.com/news
- Extract: og:title, og:description, article content
- Filter: Corporate news (appointments, office openings)

#### LangChain Blog
- URL: https://blog.langchain.dev/
- Extract: Article links and titles

#### LlamaIndex Blog
- URL: https://www.llamaindex.ai/blog
- Extract: Article links and titles

---

## Content Hub

### Purpose
存储新闻全文并提供语义搜索能力，支持后续的知识检索和问答。

### Storage
- **OpenSearch Serverless** (VECTORSEARCH 类型)
- Collection: `whatsnew-hub`
- VPC 内访问 (非公网)

### Embedding
- **Cohere Multilingual v3** (1024 维)
- 中英文混合内容优化
- Token 限制: 2048

### Index Schema
```json
{
  "mappings": {
    "properties": {
      "article_id": {"type": "keyword"},
      "title": {"type": "text"},
      "content": {"type": "text"},
      "embedding": {"type": "knn_vector", "dimension": 1024},
      "source": {"type": "keyword"},
      "category": {"type": "keyword"},
      "published_at": {"type": "date"},
      "url": {"type": "keyword"},
      "indexed_at": {"type": "date"},
      "folder_name": {"type": "keyword"},
      "screenshot_s3": {"type": "keyword"},
      "html_s3": {"type": "keyword"},
      "images_s3": {"type": "keyword"}
    }
  }
}
```

### Search Types
- **语义搜索**: kNN 向量相似度
- **全文搜索**: BM25 关键词匹配
- **混合搜索**: 向量 + 全文组合

### CLI Usage
```bash
python hub/main.py search "Claude Agent"     # 语义搜索
python hub/main.py search "MCP" --fulltext   # 全文搜索
python hub/main.py index --url https://...   # 手动索引
python hub/main.py stats                      # 统计信息
```

### Content Fetchers

| Fetcher | 技术 | 用途 | 输出 |
|---------|------|------|------|
| `fetcher.py` | trafilatura | 快速纯文本提取 | 正文文本 |
| `browser_fetcher.py` | Playwright | 完整页面抓取 | 截图 + HTML + 图片 |

**BrowserFetcher 功能:**
- JS 渲染: 支持 SPA 动态页面
- 全页截图: PNG 格式完整页面
- HTML 存档: 保留样式和结构
- 图片下载: 自动保存内容图片到 S3
- 懒加载: 滚动触发延迟加载图片

**S3 存储结构:**
```
s3://cls-whatsnew/hub/
└── {date}_{title}_{short_id}/    # 可读的文章目录名
    ├── screenshot.png             # 全页截图
    ├── page.html                  # 完整 HTML
    ├── article.json               # 文章文本内容
    ├── meta.json                  # 抓取元数据
    └── images/                    # 文章图片
        ├── 000.png
        └── ...

示例: hub/2026-02-08_LangGraph-Cloud_d77d3855/
```

---

## Configuration

### config.yaml
```yaml
# Target user profile
profile:
  role: AWS SA
  focus: Agentic AI Expert

# Filtering
filter:
  keyword_filter: agent  # null | 'agent'
  newsletter_dedup: true
  filter_corporate_news: true

# Sources
sources:
  # Agent-specific (type: web for crawlers)
  - name: Anthropic News
    type: web
    web_func: anthropic
    enabled: true

  # General (type: rss with keyword filter)
  - name: OpenAI Blog
    type: rss
    url: https://openai.com/blog/rss.xml
    enabled: true

# AI Analysis
ai:
  enabled: true
  model_id: claude-sonnet-4.5
  scoring_focus: agentic_ai
  min_news_for_analysis: 5

# Schedule
schedule:
  daily_time: "06:00"  # Beijing time

max_items_per_source: 8
max_days: 3
```

---

## Pending Improvements

### P0 - Critical
- [x] Fix Anthropic crawler title parsing
- [x] Add keyword filtering for agent-related content
- [x] Improve AI scoring variance
- [ ] Newsletter deduplication (same source, keep latest)

### P1 - Important
- [x] Web crawlers for sites without RSS
- [x] Enhanced summaries (80-150 chars)
- [x] Content Hub for full-text storage and semantic search
- [x] S3 daily report archiving (HTML + JSON)
- [ ] Filter corporate news from agent-specific sources
- [ ] Filter pure quotes/references from Simon Willison

### P2 - Nice to Have
- [x] Unified date format (YYYY-MM-DD)
- [x] TOP recommendations with reasons
- [x] Remove emojis
- [x] Content type grouping (Agent专项/技术深度/AWS聚焦/行业动态)
- [ ] Twitter/X integration for AI KOLs

### Future
- [ ] Webhook notifications (Slack, Discord)
- [ ] Web UI for history
- [ ] Custom filter rules
- [ ] Docker deployment
- [ ] Monitoring and alerts
- [ ] Content Hub web search interface

---

## Success Metrics

1. **Relevance**: >70% content directly related to Agentic AI
2. **Quality**: TOP 5 news are actionable for AWS SA
3. **Efficiency**: <20 news items per day (quality over quantity)
4. **Accuracy**: Correct titles, summaries, and translations
5. **Timeliness**: Fresh content (within 3 days)

---

## Cost Estimate

- Claude Sonnet 4.5: ~$0.30/analysis
- ~$10/month for daily analysis
- Optimization: batch processing, conditional triggers
