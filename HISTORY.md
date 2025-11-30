# WhatsNew - Change History

## [2.0.0] - 2025-11-30

### 🎯 Major Focus Shift: AI/GenAI/Agentic AI
Completely refocused the project to be **AI-centric**, filtering out general tech news and focusing on:
- GenAI/LLM technologies (GPT, Claude, Gemini)
- Agentic AI and AI Agent frameworks (LangChain, AutoGPT)
- AI infrastructure and MLOps
- Cloud AI services (AWS Bedrock, Azure OpenAI, GCP Vertex AI)

### 🤖 AI-Powered Analysis (Claude Sonnet 4.5)
**Upgraded from Claude 3.5 Sonnet v2 to Claude Sonnet 4.5**
- Model ID: `global.anthropic.claude-sonnet-4-5-20250929-v1:0`
- Implemented **7-node LangGraph workflow**:
  1. **Categorize** - Sort news into AI categories
  2. **Filter** - AI-powered relevance filtering (removes non-AI content)
  3. **Score** - Rate news importance (1-10 scale)
  4. **Enhance** - Generate detailed summaries for sparse content
  5. **Translate** - English to Chinese translation
  6. **Find Trends** - Identify 3-5 key technology trends
  7. **Summarize** - Generate bullet point daily highlights

### 📰 News Source Reorganization
**Disabled general tech sources:**
- Hacker News (too broad)
- GitHub Trending (too general)
- Dev.to (not AI-focused)
- The Verge, Ars Technica (general tech)
- Rust Blog (programming language)
- 少数派, V2EX (Chinese general tech)

**Added AI-focused sources:**
- OpenAI Blog
- Anthropic News
- Google AI Blog
- DeepMind Blog
- Hugging Face Blog
- LangChain Blog
- LlamaIndex Blog
- TechCrunch AI
- VentureBeat AI
- MIT Tech Review AI
- Microsoft Research AI
- AWS Machine Learning Blog
- arXiv cs.AI

### 🎨 Email Template Redesign
**Complete UI/UX overhaul:**
- Modern card-based design with unified purple theme (#667eea)
- Responsive hover effects throughout
- Source-grouped news organization
- Bullet points for daily highlights (was paragraph format)
- TOP news with full summaries and translations
- Professional typography and spacing

### ✨ New Features

#### 🔍 Smart Content Filtering
- AI-powered relevance detection
- Strict filtering criteria for AI/GenAI/Agentic AI content
- Technical community sources (GitHub, etc.) preserved but filtered
- Removes: games, general dev tools, shopping, non-tech content

#### 📝 Summary Enhancement
- Detects sparse summaries (< 50 chars, duplicate titles)
- AI generates detailed 80-150 word descriptions
- Specialized for: GitHub projects, tech blogs, news reports
- Technical focus with high information density

#### 🌐 Bilingual Translation
- Automatic EN→CN translation for all English news
- Technical term preservation (AI, API, LLM stay in English)
- Batch processing (10 items per batch)
- JSON-safe output (replaces double quotes with single quotes)
- Title + summary translation

#### 💡 Bullet Points Summary
- Changed from paragraph to bullet list format
- 3-5 key highlights per day
- 20-35 characters per point
- Focuses on specific events and technical value

#### ⭐ Enhanced TOP News
- AI-curated top 5 news
- Full English summary (200 chars)
- Chinese translation (150 chars)
- Source attribution badges
- AI recommendation reasoning

### 🔧 Technical Improvements

#### Crawler Enhancements
- HTML tag cleanup and entity decoding
- Intelligent summary extraction
- Fallback to title for sparse content
- Handles "Comments" and similar edge cases

#### Email Template
- Unified CSS with consistent styling
- Translation styling (italic, gray, indented)
- TOP badge and score badge system
- Source grouping with item counts
- Mobile-friendly layout

#### AI Workflow
- LangGraph state management
- Proper error handling and fallbacks
- Batch processing for scalability
- Token optimization

### 📊 Statistics
**Filtering effectiveness:**
- Before: 24 news → 16 after filtering (67% kept)
- After: 24 news → 20 after filtering (83% kept) ← More relevant sources

**AI processing:**
- ~10 summaries enhanced per run
- ~20 items translated per run
- ~500k tokens/day (input) + ~100k tokens/day (output)
- Estimated cost: ~$3/day with hourly checks

---

## [1.0.0] - 2025-11-28

### 🎉 Initial Release

#### Core Features
- RSS feed crawling from 20+ sources
- Email notifications via SMTP
- MD5-based deduplication
- Basic HTML email template
- Scheduled execution support

#### Supported Sources
- Hacker News
- TechCrunch
- The Verge
- Ars Technica
- GitHub Trending
- Dev.to
- GitHub Blog
- Python/Rust Blogs
- Chinese tech sites (少数派, V2EX)

#### Configuration
- YAML-based configuration
- Email settings (SMTP)
- News source management
- Schedule configuration

#### Security
- `.gitignore` for `config.yaml`
- `config.example.yaml` template
- Email authorization code support

---

## Upgrade Path

### From 1.0.0 to 2.0.0

**Required Actions:**

1. **Update Dependencies:**
   ```bash
   pip install -r requirements.txt
   # New: langchain-aws, langgraph
   ```

2. **AWS Bedrock Setup:**
   - Enable Claude Sonnet 4.5 in AWS Console
   - Configure AWS credentials
   - Update `config.yaml`:
   ```yaml
   ai:
     enabled: true
     aws_region: us-west-2
     model_id: global.anthropic.claude-sonnet-4-5-20250929-v1:0
     min_news_for_analysis: 5
   ```

3. **Update News Sources:**
   - Review `config.yaml` source list
   - Disable non-AI sources if desired
   - Add new AI-focused sources from template

4. **Test:**
   ```bash
   python preview_email.py  # Generate HTML preview
   python test_once.py      # Send test email
   ```

**Breaking Changes:**
- ❌ No breaking changes - all 1.0.0 functionality preserved
- ✅ AI features are optional (`ai.enabled: false` for 1.0.0 behavior)
- ✅ Existing configurations work without modification

**Behavioral Changes:**
- Email template appearance completely redesigned
- Non-AI news filtered out by default when AI enabled
- Translation adds ~30% to email length
- Increased API costs (~$3/day) if AI analysis enabled

---

## Future Roadmap

### Planned Features
- [ ] Web UI for configuration management
- [ ] Slack/Discord notification support
- [ ] Multi-language support (beyond EN/CN)
- [ ] Custom LLM provider support (OpenAI, Anthropic Direct)
- [ ] Mobile-optimized email templates
- [ ] Webhook integrations
- [ ] RSS feed health monitoring
- [ ] Advanced filtering rules (keywords, regex)
- [ ] Read/unread tracking
- [ ] Favorites and bookmarking

### Under Consideration
- [ ] Browser extension for quick subscriptions
- [ ] Newsletter-style weekly summaries
- [ ] Audio podcast generation from news
- [ ] Social media cross-posting
- [ ] Team collaboration features
- [ ] Analytics dashboard

---

## Contributing

We welcome contributions! Priority areas:
1. **New AI news sources** - Help us find quality AI/ML RSS feeds
2. **Translation improvements** - Better technical term handling
3. **Email templates** - Mobile optimization, dark mode
4. **Documentation** - Tutorials, guides, best practices
5. **Testing** - Unit tests, integration tests

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## Acknowledgments

### v2.0.0 Contributors
- **Claude Sonnet 4.5** - AI analysis and workflow orchestration
- **AWS Bedrock** - Reliable LLM API
- **LangChain/LangGraph** - Agent framework
- Community feedback on AI focus and email design

### v1.0.0 Contributors
- Initial project concept and implementation
- RSS feed research and curation
- Email template design

---

**Project Repository:** https://github.com/tsaol/whatsnew
**License:** MIT
**Maintained by:** [@tsaol](https://github.com/tsaol)
