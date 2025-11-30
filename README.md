# WhatsNew - AI/GenAI News Aggregator with Intelligent Analysis

An intelligent news aggregator **focused on AI, GenAI, and Agentic AI**, powered by AWS Bedrock Claude Sonnet 4.5 for smart analysis, translation, and curation.

## Core Focus

This tool is specifically designed for:
- **GenAI/LLM**: Large models, Prompt engineering, RAG, Fine-tuning
- **Agentic AI**: AI Agents, Multi-Agent systems, Agent frameworks (LangChain, AutoGPT)
- **AI Infrastructure**: Model training, deployment, MLOps, vector databases
- **Cloud AI Services**: AWS Bedrock, Azure OpenAI, GCP Vertex AI
- **AI Tooling**: Hugging Face, LangChain, LlamaIndex

## Key Features

### AI-Powered Analysis (Claude Sonnet 4.5)
- **7-Node Workflow**: Categorize → Filter → Score → Enhance → Translate → Find Trends → Summarize
- **Smart Filtering**: AI removes non-AI content automatically
- **Relevance Scoring**: Prioritizes breakthrough AI news (1-10 scale)
- **Summary Enhancement**: Generates detailed descriptions for sparse content
- **Bilingual Support**: Auto-translates English news to Chinese

### Professional Email Digest
- **Modern Design**: Card-based layout with unified purple theme
- **Bullet Points Summary**: Clear daily highlights
- **TOP News Picks**: AI-curated top 5 with full summaries
- **Source Grouping**: News organized by publication
- **Complete Translations**: Both titles and summaries in EN/CN

### Curated AI News Sources
- **AI Companies**: OpenAI, Anthropic, Google AI, DeepMind
- **AI Frameworks**: LangChain, LlamaIndex, Hugging Face
- **Cloud Providers**: AWS ML Blog, Azure AI, Google Cloud AI
- **Industry Analysis**: TechCrunch AI, VentureBeat AI, MIT Tech Review AI
- **Research**: arXiv cs.AI, Microsoft Research AI

## Project Structure

```
whatsnew/
 config.yaml              # Configuration (DO NOT commit!)
 requirements.txt         # Python dependencies
 main.py                  # Scheduled runner
 test_once.py            # One-time test
 preview_email.py        # Generate HTML preview
 src/
    config.py           # Configuration loader
    crawler.py          # RSS crawler with HTML cleanup
    analyzer.py         # AI analysis (7-node LangGraph workflow)
    mailer.py           # Email formatter with modern template
    storage.py          # Deduplication storage
 data/
     sent_news.json      # Sent news records
```

## Quick Start

### 1. Install Dependencies

**Option A: Using uv (Recommended - 10x faster)**

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv pip install -r requirements.txt
```

**Option B: Using pip**

```bash
pip install -r requirements.txt
```

**Required packages:**
- `feedparser` - RSS parsing
- `pyyaml` - Configuration
- `langchain-aws` - Bedrock integration
- `langgraph` - AI workflow orchestration

### 2. AWS Bedrock Setup

**Enable Claude Sonnet 4.5 in AWS Bedrock:**

1. Go to AWS Console → Bedrock → Model Access
2. Request access to: `Claude Sonnet 4.5 (global.anthropic.claude-sonnet-4-5-20250929-v1:0)`
3. Configure AWS credentials:

```bash
aws configure
# Or set environment variables:
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
export AWS_DEFAULT_REGION=us-west-2
```

### 3. Configure Email and News Sources

** Important: `config.yaml` contains secrets and is git-ignored!**

```bash
cp config.example.yaml config.yaml
# Edit config.yaml with your settings
```

**Minimal configuration:**

```yaml
email:
  smtp_server: smtp.126.com
  smtp_port: 465
  username: your-email@126.com
  password: YOUR_AUTH_CODE  # NOT your login password!
  to: recipient@example.com

ai:
  enabled: true
  aws_region: us-west-2
  model_id: global.anthropic.claude-sonnet-4-5-20250929-v1:0
  min_news_for_analysis: 5

max_items_per_source: 8
```

**Note**: For 126 email, get authorization code from: Settings → POP3/SMTP/IMAP

### 4. Test Run

**Preview without sending:**
```bash
python preview_email.py
# Opens email_preview.html in browser
```

**Send test email:**
```bash
python test_once.py
```

**Run continuously:**
```bash
python main.py
# Runs every hour (configurable)
# Press Ctrl+C to stop
```

## AI Analysis Workflow

The system uses a 7-node LangGraph workflow powered by Claude Sonnet 4.5:

```
1. Categorize    → Sort news into AI categories
2. Filter        → Remove non-AI content (games, general dev tools)
3. Score         → Rate importance (1-10 scale)
4. Enhance       → Generate detailed summaries for sparse content
5. Translate     → EN→CN translation with technical accuracy
6. Find Trends   → Identify 3-5 key trends
7. Summarize     → Generate bullet point highlights
```

**Filtering Criteria:**
-  **Keep**: GenAI, LLMs, AI Agents, MLOps, Cloud AI, AI research
-  **Remove**: General software dev, gaming, hardware, shopping deals

## News Sources (Enabled by Default)

### AI Companies & Research
- **OpenAI Blog** - GPT/ChatGPT updates
- **Anthropic News** - Claude releases
- **Google AI Blog** - Gemini/PaLM news
- **DeepMind Blog** - AlphaFold, AlphaZero research
- **Microsoft Research AI** - AI research papers

### AI Frameworks & Tools
- **Hugging Face Blog** - Open-source models
- **LangChain Blog** - Agent framework updates
- **LlamaIndex Blog** - RAG framework news

### Cloud AI Services
- **AWS Machine Learning Blog** - Bedrock, SageMaker
- **Google Cloud AI** - Vertex AI updates
- **Azure AI** - OpenAI Service news

### Industry Analysis
- **TechCrunch AI** - AI business news
- **VentureBeat AI** - AI trends
- **MIT Tech Review AI** - In-depth analysis

### Academic
- **arXiv cs.AI** - Latest AI papers

### Developer Community
- **GitHub Blog** - Copilot, AI security (filtered for AI content)

## Email Template Features

### Daily Highlights (Bullet Points)
```
 Today's Focus
• GitHub releases AI Agent security framework
• Claude 3.5 Sonnet announces new capabilities
• Research reveals AI model bias challenges
```

### TOP News (AI-Curated)
```
#1 9  Achieving lasting remission for HIV  [Ars Technica]
        HIV

        Promising trials using engineered antibodies...
        ''...

         Major medical breakthrough using AI
```

### Complete News List (Grouped by Source)
- Source-organized sections
- AI scores and TOP badges
- Full EN/CN translations
- Clean, scannable layout

## Configuration

### AI Analysis Settings

```yaml
ai:
  enabled: true                    # Enable AI analysis
  aws_region: us-west-2           # AWS region for Bedrock
  model_id: global.anthropic.claude-sonnet-4-5-20250929-v1:0
  min_news_for_analysis: 5        # Minimum news items to trigger analysis
```

### News Source Management

Enable/disable sources in `config.yaml`:

```yaml
sources:
  - name: OpenAI Blog
    type: rss
    url: https://openai.com/blog/rss.xml
    enabled: true

  - name: Hacker News
    type: rss
    url: https://news.ycombinator.com/rss
    enabled: false  # Too broad, disabled for AI focus
```

### Schedule Configuration

```yaml
schedule:
  interval_hours: 1              # Check every hour

max_items_per_source: 8          # Max items per source
data_file: data/sent_news.json   # Deduplication database
```

## Troubleshooting

### AWS Bedrock Access Denied
- Ensure you've requested model access in AWS Console → Bedrock
- Check AWS credentials: `aws sts get-caller-identity`
- Verify region supports Claude Sonnet 4.5 (us-west-2 recommended)

### Email Not Sending
- For 126.com: Use **authorization code**, not login password
- Check SMTP settings: `smtp_server`, `smtp_port` (465 for SSL)
- Test with: `python test_once.py`

### No AI Analysis
- Ensure `ai.enabled: true` in config
- Verify AWS Bedrock credentials
- Check minimum news threshold: `min_news_for_analysis`

### Translation Failures
- AI removes double quotes in translations to prevent JSON errors
- Uses single quotes '…' or guillemets … instead
- Retries with smaller batches if timeout

## Deployment

### Run as systemd service (Linux)

Create `/etc/systemd/system/whatsnew.service`:

```ini
[Unit]
Description=WhatsNew AI News Aggregator
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/whatsnew
Environment="AWS_ACCESS_KEY_ID=your-key"
Environment="AWS_SECRET_ACCESS_KEY=your-secret"
Environment="AWS_DEFAULT_REGION=us-west-2"
ExecStart=/usr/bin/python3 /path/to/whatsnew/main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable whatsnew
sudo systemctl start whatsnew
sudo systemctl status whatsnew
```

### Docker Deployment

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

Build and run:
```bash
docker build -t whatsnew .
docker run -d \
  --name whatsnew \
  -e AWS_ACCESS_KEY_ID=your-key \
  -e AWS_SECRET_ACCESS_KEY=your-secret \
  -e AWS_DEFAULT_REGION=us-west-2 \
  -v $(pwd)/config.yaml:/app/config.yaml \
  -v $(pwd)/data:/app/data \
  whatsnew
```

## Security Best Practices

1. **Never commit** `config.yaml` (git-ignored by default)
2. **Use AWS IAM roles** instead of access keys when possible
3. **Rotate credentials** regularly
4. **Limit Bedrock permissions** to only required models
5. **Use email app passwords**, not account passwords

## Cost Estimation (AWS Bedrock)

**Claude Sonnet 4.5 pricing** (us-west-2):
- Input: $3 per million tokens
- Output: $15 per million tokens

**Typical daily usage** (1 check/hour, 20 news items):
- ~24 API calls/day
- ~500k tokens/day input + 100k tokens/day output
- **~$3/day or $90/month**

**Cost optimization:**
- Reduce `max_items_per_source` (fewer news = fewer tokens)
- Increase `interval_hours` (check less frequently)
- Disable translation if not needed
- Use fewer news sources

## Contributing

Contributions welcome! Areas for improvement:

- [ ] Add more AI-focused news sources
- [ ] Support other LLM providers (OpenAI, Anthropic Direct)
- [ ] Implement web UI for configuration
- [ ] Add Slack/Discord notifications
- [ ] Create mobile-optimized email template

## License

MIT License - feel free to use and modify!

## Acknowledgments

- **AWS Bedrock** - Claude Sonnet 4.5 API
- **LangChain/LangGraph** - AI workflow orchestration
- **Anthropic** - Claude model
- All the excellent AI news sources

## Support

If you find this project helpful, please:
- Give it a star on GitHub
- Share with your AI/ML community
- Report issues or suggest features

---

**Built with  for the AI community**
