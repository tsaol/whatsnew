# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **McKinsey Style Email Design** (#48): Complete redesign with consulting report aesthetics
  - Primary color: McKinsey Blue `#00205B`, Accent: Gold `#FDB813`
  - Typography: Georgia (headers) + Arial (body)
  - Clean layout with generous whitespace and 2px section borders
  - Chinese translations displayed below English content
- **Label Mode for Content Filtering** (#44, #47): Filters converted to labeling system
  - Agent keyword filter → `[AGENT]` badge (purple → blue)
  - Corporate news filter → `[企业]` badge (gray)
  - Low-value content filter → `[引用]` badge (gray)
  - No content filtered out, all items shown with appropriate labels
- **Separate GitHub & Product Hunt Sections** (#46): Dedicated full-display sections
  - `OPEN SOURCE | GitHub Trending` - full item display with translations
  - `PRODUCTS | Product Hunt` - full item display with translations
  - Excluded from main news list to avoid duplication

### Changed
- **Email Layout Simplified** (#41): Removed redundant sections
  - Removed: 快速导航, 30秒速读, 关键趋势, 本日要闻 Top 10, 热点专题, 深度专题
  - Focus on: Executive Summary, Key Insights, Action Items, Research, News by Source
- **Full-Width Source Rows** (#37): Each news source occupies full row width
- **Re-enabled Data Sources** (#39): The Batch, Azure AI Blog, InfoQ AI (English)

### Fixed
- **Content Hub Indexing** (#34): Fixed missing index_to_hub() call in test_once.py
- **Hub Module Import Conflict** (#35): Use importlib.util for explicit path loading

### Added (previous)
- **New Data Sources**: GitHub Trending, Product Hunt, HN Top Blogs (#27)
  - GitHub Trending: GraphQL API, requires `GITHUB_TOKEN`
  - Product Hunt: GraphQL API with Hydration fallback
  - HN Top Blogs: OPML feed aggregation with 5 fallback blogs
  - Hacker News RSS enabled with keyword filtering
- **"This Week's Discoveries" Section**: New email section for GitHub Trending & Product Hunt (#28)
  - Two-column layout: ⭐ Open Source + 🚀 Product Discoveries
  - Placed after "30-second Quick Read" section
  - Auto-hides when no new content available
- **Per-Source max_items Config**: Individual sources can now override global max_items (#28)
  - Example: `max_items: 4` for arXiv sources to reduce paper ratio
- **Content Hub Module**: New `hub/` directory for full-text storage and semantic search
  - OpenSearch Serverless for vector + full-text search
  - Cohere Multilingual v3 embedding (optimized for Chinese + English)
  - Auto-index after daily report sent
  - CLI: `python hub/main.py search "query"` for semantic search
- **Browser Fetcher**: Playwright-based full page capture with image download
  - Full-page screenshot (PNG)
  - Complete HTML with styles preserved
  - Image download and S3 upload
  - JavaScript rendering for SPA pages
  - Lazy-load image handling
- **S3 Folder Reorganization**: Content organized by article with readable names
  - Format: `hub/{date}_{title}_{short_id}/`
  - Example: `hub/2026-02-08_LangGraph-Cloud_d77d3855/`
  - Each folder contains: screenshot.png, page.html, article.json, meta.json, images/
- **OpenSearch Snapshot Paths**: S3 paths stored in search index
  - `folder_name`: Readable folder name for S3 path
  - `screenshot_s3`: Direct link to full-page screenshot
  - `html_s3`: Direct link to archived HTML
  - `images_s3`: List of article image paths
- **S3 Daily Report Archiving**: Daily reports now saved to S3
  - HTML: `s3://cls-whatsnew/{ai|ecom}/{date}.html`
  - JSON: `s3://cls-whatsnew/{ai|ecom}/{date}.json`
- **Enhanced sent_news.json**: Now saves URL, source, and category for each news item
- **E-commerce + AI Focus Mode**: New `ecom/` directory with dedicated config for e-commerce + AI content
- **Key Companies Tracking**: Track specific companies (SHEIN, Amazon) across all news sources
- **Company Aliases**: Broader matching with aliases (Amazon → aws, alexa, kindle, prime, etc.)
- **Dual Instance Setup**: Separate `ai/` and `ecom/` directories with independent configs and data
- **Google News RSS Sources**: Added Google News search for key companies as supplemental source
- **E-commerce Content Categories**: 关键企业/电商+AI/技术深度/行业动态 for ecom emails
- **30+ E-commerce Sources**: Shopify, eBay, Etsy, Walmart, Alibaba, Netflix, Spotify, etc.

### Changed
- Project restructured into `ai/` (original) and `ecom/` (new) directories
- Crontab now runs both instances: ai at 06:00, ecom at 06:30 Beijing time
- E-commerce filter requires BOTH ecommerce AND AI keywords (intersection, not union)
- Email subject format: `WhatsNew [Ecom] [AI] - N 条新内容`

### Fixed
- **30秒速读质量改进** (#31): One-liner now extracts specific data from summaries
  - Pass `summary_zh` to AI prompt for data extraction
  - Fix field name mismatch: `one_liner` → `oneliner`
  - Improved prompt with examples for name + data format
- **Published Date Display** (#25): Articles now show original publication date in email
  - RSS feeds: Extract from `published_parsed` / `updated_parsed` (YYYY-MM-DD format)
  - Web scrapers: Default to current date for sources without date info
  - Content Hub: Pass `published` field in metadata for indexing
- **Anthropic Crawler Date Filtering** (#24): Fix old articles being included
- **Email Recipients Parsing** (#21): Fix Resend API error with comma-separated recipients
- **Key Company Filter Bug**: Google News results now require actual company mention in content
- Previously, news from "Google News - Amazon AI" auto-passed without checking content
- Now filters like "The best free AI courses..." are correctly excluded

---

## [1.2.0] - 2026-01-21

### Added
- **Content Categories Display**: News grouped by type (Agent专项/技术深度/AWS聚焦/行业动态)
- **Source-based Forced Classification**: AWS sources → AWS聚焦, Agent frameworks → Agent专项
- **Protected Sources**: Core sources (AWS, LangChain, LlamaIndex) skip AI filtering
- **Title-based Classification**: Keywords in title determine category for non-forced sources
- **Email Enable/Disable Config**: `email.enabled` flag to disable sending on test machines
- **Agentic AI Focus**: Optimized for AWS SA / Agentic AI Expert
- **Web Crawlers**: Support for sites without RSS (Anthropic, LangChain, LlamaIndex)
- **Keyword Filtering**: Agent-related content filter (agent, mcp, tool use, rag, etc.)
- **Newsletter Deduplication**: Same source newsletters keep only the latest
- **Corporate News Filter**: Auto-remove HR, funding, policy news
- **Low-value Content Filter**: Remove pure quotes, bare links
- **Unified Date Format**: All dates show as YYYY-MM-DD
- **TOP Recommendations with Reasons**: Each recommendation includes scoring reason

### Changed
- Email template now groups by content category instead of source
- Category icons with colors (A=purple, T=blue, W=orange, I=green)
- AI scoring focused on Agentic AI relevance (9-10 for Agent frameworks, MCP)
- Trend identification focused on Agentic AI only
- Removed all emojis from code and email templates
- Anthropic crawler extracts og:title and og:description properly
- Default `max_days` changed to 3 days (for keyword filtering)
- DESIGN.md rewritten with user requirements and target profile

### Fixed
- LlamaIndex crawler now extracts date from URL/title for proper filtering
- AWS content no longer filtered out by AI (protected source)
- Anthropic News title parsing (was mixing date/category in title)
- AI scoring variance (was all 5s, now properly distributed)
- Trend identification returning "no trends" issue
- Empty or incorrect date display in emails

## [1.1.0] - 2026-01-20

### Added
- 48-hour time filter for news (only fetch news from last 2 days)
- Email duplicate content fix (TOP news no longer shows summaries)
- DESIGN.md with comprehensive architecture documentation
- CHANGELOG.md following standard format

### Changed
- TOP news section now only shows title + translation + scoring reason
- Full news list maintains complete bilingual information

### Fixed
- Duplicate Chinese content in email body
- TOP news and full list showing identical translations

## [1.0.0] - 2025-12-03

### Added
- 🤖 **AI-Powered Analysis Engine**
  - 7-node LangGraph workflow (categorize, filter, score, enhance, translate, trends, summarize)
  - Claude Sonnet 4.5 integration via AWS Bedrock
  - Intelligent content filtering focused on GenAI/LLM/Agentic AI
  - Automatic English-to-Chinese translation
  - TOP news selection (top 5 scored news)
  - Trend identification (3-5 key technology trends)

- 📰 **Multi-Source News Aggregation**
  - 25+ AI-focused RSS sources
  - OpenAI, Anthropic, Google AI, DeepMind, Hugging Face
  - AWS blogs (8 channels): ML, AI, Compute, Big Data, Developer, Architecture, News, Startups
  - GitHub Blog, LangChain, LlamaIndex, Replicate
  - Academic: arXiv cs.AI, MIT Tech Review
  - Tech media: TechCrunch AI, VentureBeat AI

- 📧 **Professional HTML Email**
  - Modern responsive design
  - AI insights section with bullet points summary
  - Trend tags
  - TOP news recommendations
  - Grouped by source in full news list
  - Bilingual display (English + Chinese)

- ⚙️ **Configuration Management**
  - YAML-based configuration
  - Per-source enable/disable control
  - Customizable AI analysis parameters
  - Flexible email scheduling

- 🔄 **Smart Deduplication**
  - MD5-based unique ID generation
  - JSON storage for sent news tracking
  - Cross-session duplicate prevention

### Technical Details
- **Framework**: LangGraph for workflow orchestration
- **LLM**: Claude Sonnet 4.5 (global.anthropic.claude-sonnet-4-5-20250929-v1:0)
- **Region**: AWS us-west-2
- **Cost**: ~$10/month (1 run/day, ~40 news items)
- **Dependencies**: langchain-aws, langgraph, feedparser, boto3, pyyaml, schedule

### Cost Optimization
- Batch processing for translation and enhancement (10 items/batch)
- Conditional AI analysis (`min_news_for_analysis: 5`)
- Intelligent filtering reduces downstream processing
- Result caching in item objects

## [0.5.0] - 2025-11-30

### Added
- Initial project structure
- Basic RSS crawler
- Simple email formatting
- Storage module with deduplication

### Features
- RSS feed parsing
- HTML email generation
- SMTP sending via 126.com
- Manual scheduling support

---

## Version History

### Latest (Unreleased)
- ✅ Fixed duplicate content issue
- ✅ Added 48-hour time filter
- ✅ Comprehensive documentation

### v1.0.0 (2025-12-03)
- 🚀 AI-powered intelligent analysis
- 🌐 25+ AI-focused sources
- 📧 Professional email design
- 🎯 7-node workflow engine

### v0.5.0 (2025-11-30)
- 🔧 Basic crawler and mailer
- 💾 Simple deduplication
- 📮 Email scheduling

---

## Migration Guide

### From v0.5.0 to v1.0.0

**New Dependencies**:
```bash
pip install langchain-aws langgraph boto3
```

**Configuration Changes**:
```yaml
# Add AI configuration
ai:
  enabled: true
  aws_region: us-west-2
  model_id: global.anthropic.claude-sonnet-4-5-20250929-v1:0
  min_news_for_analysis: 5
```

**AWS Setup**:
1. AWS Console → Bedrock → Model Access
2. Request access to Claude Sonnet 4.5
3. Configure credentials: `aws configure`

### From v1.0.0 to Unreleased

**Configuration Changes**:
```yaml
# Add time filter (optional)
max_days: 2  # Only fetch news from last 48 hours
```

**No Breaking Changes** - backward compatible

---

## Roadmap

### Short-term
- [ ] Webhook integration (Slack, Discord, DingTalk)
- [ ] Web interface for viewing history
- [ ] User-customizable filter rules
- [ ] More Chinese AI news sources

### Long-term
- [ ] Docker deployment support
- [ ] Custom email templates
- [ ] Monitoring and alerting
- [ ] Multi-user support
- [ ] API endpoints
- [ ] Mobile app

---

## Contributing

Please read [DESIGN.md](DESIGN.md) for architecture details before contributing.

## License

MIT License - see [LICENSE](LICENSE) for details.
