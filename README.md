# WhatsNew - News Aggregator

English | [简体中文](README_zh.md)

A simple Python-based news aggregator that crawls RSS feeds and sends updates to your email.

## Features

- RSS feed crawling from multiple sources
- Automatic deduplication (no duplicate news)
- HTML formatted email notifications
- Scheduled execution
- Simple YAML configuration

## Project Structure

```
whatsnew/
├── config.yaml              # Configuration file
├── requirements.txt         # Python dependencies
├── main.py                  # Main program
├── src/
│   ├── config.py           # Configuration management
│   ├── crawler.py          # Crawler module
│   ├── mailer.py           # Email sender
│   └── storage.py          # Data storage
└── data/
    └── sent_news.json      # Sent news records
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Email and News Sources

**Important: The configuration file contains sensitive information. Do NOT commit it to git!**

Copy the configuration template and edit it:

```bash
cp config.example.yaml config.yaml
# Then edit config.yaml and fill in your email credentials
```

Edit `config.yaml`:

```yaml
email:
  smtp_server: smtp.126.com       # SMTP server
  smtp_port: 465                  # SMTP port
  username: your-email@126.com    # Sender email
  password: your-auth-code        # Email authorization code (NOT login password!)
  to: recipient@example.com       # Recipient email

sources:
  - name: Hacker News
    type: rss
    url: https://news.ycombinator.com/rss
    enabled: true

schedule:
  interval_hours: 1               # Check interval in hours
```

**Notes**:
- `config.yaml` is added to `.gitignore` and will not be tracked by git
- For 126 email, you need to use an **authorization code**, not your login password
- To get authorization code: Login to 126 email → Settings → POP3/SMTP/IMAP → Enable and generate code

### 3. Run the Program

**Test once:**
```bash
python test_once.py
```

**Run continuously:**
```bash
python main.py
```

The program will:
1. Execute immediately once
2. Run periodically based on configured interval
3. Press `Ctrl+C` to stop

## Configuration

### Email Settings

- `smtp_server`: SMTP server address
- `smtp_port`: SMTP port (465 for 126 email with SSL)
- `username`: Sender email address
- `password`: Email password or authorization code
- `to`: Recipient email address

### News Sources

Supports RSS format news sources:

```yaml
sources:
  - name: Source Name
    type: rss
    url: RSS feed URL
    enabled: true  # Enable or disable
```

### Schedule Configuration

- `interval_hours`: Execution interval in hours
- `max_items_per_source`: Maximum items to fetch per source

## Built-in AI/Tech News Sources

The project comes with 20+ high-quality RSS feeds:

### AI & Research
- OpenAI Blog, Google AI Blog, Microsoft Research AI
- Hugging Face Blog, VentureBeat AI, MIT Tech Review AI
- Replicate Blog, arXiv cs.AI

### Developer Resources
- Hacker News, GitHub Trending, Dev.to
- TechCrunch, The Verge, Ars Technica

### Cloud AI Services
- AWS Machine Learning Blog

### Chinese Tech News
- 少数派 (sspai.com), V2EX

See `config.example.yaml` for the complete list.

## Popular RSS Feeds

You can add more RSS feeds to `config.yaml`:

- **Hacker News**: https://news.ycombinator.com/rss
- **GitHub Trending**: https://mshibanami.github.io/GitHubTrendingRSS/daily/all.xml
- **Python News**: https://www.python.org/feeds/community-events.rss.xml
- **Reddit Programming**: https://www.reddit.com/r/programming/.rss

## Important Notes

1. **For 126 email users**: Use authorization code, not login password
2. **First run**: Will send all news. Subsequent runs only send new content
3. **Data storage**: Sent news records are saved in `data/sent_news.json`
4. **Security**: Never commit `config.yaml` to version control

## How It Works

1. **Crawl**: Fetches RSS feeds from configured sources
2. **Parse**: Extracts title, link, summary, and publish date
3. **Deduplicate**: Checks against local database to avoid duplicates
4. **Format**: Creates HTML formatted email with all news items
5. **Send**: Sends email via SMTP
6. **Record**: Saves sent items to prevent future duplicates

## Troubleshooting

### Email not sending
- Check SMTP credentials are correct
- Ensure you're using authorization code (not password) for 126 email
- Verify SMTP server and port settings

### No new content found
- Check if RSS feeds are accessible
- Some feeds update infrequently
- Verify `enabled: true` for desired sources

### RSS parsing warnings
- Some RSS feeds may have format issues
- You can disable problematic sources by setting `enabled: false`

## Deployment

### Run as systemd service (Linux)

Create `/etc/systemd/system/whatsnew.service`:

```ini
[Unit]
Description=WhatsNew News Aggregator
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/whatsnew
ExecStart=/usr/bin/python3 /path/to/whatsnew/main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable whatsnew
sudo systemctl start whatsnew
```

### Run with Docker (optional)

Create a `Dockerfile`:

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

Build and run:
```bash
docker build -t whatsnew .
docker run -d --name whatsnew -v $(pwd)/config.yaml:/app/config.yaml whatsnew
```

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

If you find this project helpful, please give it a ⭐️ on GitHub!
