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

### 5. Output Requirements

#### Email Format
- No emojis (user preference)
- Unified date format: YYYY-MM-DD
- Chinese translations for titles and summaries
- Clear score differentiation
- TOP recommendations with reasons

#### Quality Metrics
- High relevance to Agentic AI (>70% of content)
- Score variance (not uniform scores)
- Actionable trends
- Enhanced summaries (80-150 chars, technical depth)

---

## Technical Architecture

### Module Structure
```
src/
├── config.py       # Configuration management
├── crawler.py      # RSS + Web crawlers with keyword filter
├── storage.py      # Deduplication and persistence
├── analyzer.py     # LangGraph AI analysis (Agentic AI focus)
└── mailer.py       # Email generation with date formatting
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
- [ ] Filter corporate news from agent-specific sources
- [ ] Filter pure quotes/references from Simon Willison

### P2 - Nice to Have
- [x] Unified date format (YYYY-MM-DD)
- [x] TOP recommendations with reasons
- [x] Remove emojis
- [ ] Content type grouping (deep tech vs news)
- [ ] Twitter/X integration for AI KOLs

### Future
- [ ] Webhook notifications (Slack, Discord)
- [ ] Web UI for history
- [ ] Custom filter rules
- [ ] Docker deployment
- [ ] Monitoring and alerts

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
