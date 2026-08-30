# WhatsNew

AI-focused news aggregator with intelligent analysis powered by AWS Bedrock Claude Sonnet 4.5.

## Features

- **AI Analysis**: 12-node LangGraph workflow for intelligent news processing
- **Smart Filtering**: Auto-removes non-AI content, focuses on GenAI/LLM/Agentic AI
- **Bilingual**: English to Chinese translation for all news
- **Professional Email**: Modern HTML digest with TOP news picks and category grouping
- **35+ AI Sources**: OpenAI, Anthropic, Google AI, DeepMind, Hugging Face, AWS blogs, etc.
- **Content Hub**: Full-text storage with semantic search (OpenSearch + Cohere Embedding)
- **Browser Capture**: Playwright-based full page capture with screenshots and image download
- **S3 Archiving**: Daily reports archived to S3 (HTML + JSON)
- **Weekly Reports**: AI and Ecommerce weekly intelligence reports with clickable links
  - AI Weekly: Saturday 12:00 PM Beijing time
  - Ecom Weekly: Saturday 9:00 AM Beijing time

## Quick Start

### 1. Install

```bash
# Using uv (recommended - 10x faster)
curl -LsSf https://astral.sh/uv/install.sh | sh
uv pip install -r requirements.txt

# Or using pip
pip install -r requirements.txt
```

### 2. Configure

```bash
cp config.example.yaml config.yaml
# Edit config.yaml with your settings
```

**Minimal config:**

```yaml
email:
  smtp_server: smtp.126.com
  smtp_port: 465
  username: your-email@126.com
  password: YOUR_AUTH_CODE
  to: recipient@example.com

ai:
  enabled: true
  aws_region: us-west-2
  model_id: global.anthropic.claude-sonnet-4-5-20250929-v1:0
```

**AWS Bedrock Setup:**
1. AWS Console → Bedrock → Model Access
2. Request access to Claude Sonnet 4.5
3. Configure credentials: `aws configure`

### 3. Run

```bash
# Test preview (no email sent)
python3 preview_email.py

# Send test email
python3 test_once.py

# Run continuously (every hour)
python3 main.py
```

### 4. Deploy

**Crontab schedule (北京时间):**

```bash
# AI 日报: 每天 06:00 BJT (= 22:00 UTC 前一天)
0 22 * * *       cd /path/to/whatsnew/ai   && python3 test_once.py >> cron.log 2>&1

# Ecom 日报: 每周一/三/五 06:30 BJT (= 22:30 UTC 周日/二/四)
30 22 * * 0,2,4  cd /path/to/whatsnew/ecom && python3 test_once.py >> cron.log 2>&1

# Ecom 周报: 每周六 01:00 BJT (= 17:00 UTC 周五)
0  17 * * 5      cd /path/to/whatsnew/ecom && python3 weekly_report.py >> cron.log 2>&1
```

> BJT 星期 X 早上 → UTC 星期 X-1 晚上，所以 cron 的 day-of-week 是**前一天**：
> 周一 → 0, 周三 → 2, 周五 → 4, 周六 → 5

## Cost

**Claude Sonnet 4.5 pricing:**
- Input: $3 per million tokens
- Output: $15 per million tokens

**Estimated cost (1 run/day, 40 news items):**
- ~$3-5/month

## Documentation

- [HISTORY.md](HISTORY.md) - Detailed changelog and features

## License

MIT License

---

**Repository:** https://github.com/tsaol/whatsnew
