# WhatsNew - 新闻爬虫聚合平台

[English](README.md) | 简体中文

简单的 Python 新闻聚合工具，定时抓取 RSS 新闻源并发送到邮箱。

## 功能特点

- RSS 订阅源爬取
- 自动去重（不重复发送已读新闻）
- HTML 格式邮件推送
- 定时调度执行
- 简单的配置文件

## 项目结构

```
whatsnew/
├── config.yaml              # 配置文件
├── requirements.txt         # 依赖包
├── main.py                  # 主程序
├── src/
│   ├── config.py           # 配置管理
│   ├── crawler.py          # 爬虫模块
│   ├── mailer.py           # 邮件发送
│   └── storage.py          # 数据存储
└── data/
    └── sent_news.json      # 已发送记录
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置邮箱和新闻源

**重要：配置文件包含敏感信息，请勿提交到 git！**

复制配置模板并编辑：

```bash
cp config.example.yaml config.yaml
# 然后编辑 config.yaml，填入你的邮箱信息
```

编辑 `config.yaml`:

```yaml
email:
  smtp_server: smtp.126.com       # SMTP 服务器
  smtp_port: 465                  # 端口
  username: your-email@126.com    # 发件邮箱
  password: your-auth-code        # 邮箱授权码（不是登录密码！）
  to: recipient@example.com       # 收件邮箱

sources:
  - name: Hacker News
    type: rss
    url: https://news.ycombinator.com/rss
    enabled: true

schedule:
  interval_hours: 1
```

**注意**：
- `config.yaml` 已添加到 `.gitignore`，不会被 git 跟踪
- 126 邮箱需要使用**授权码**，不是登录密码
- 获取授权码：登录 126 邮箱 → 设置 → POP3/SMTP/IMAP → 开启并生成授权码

### 3. 运行程序

```bash
python main.py
```

程序会：
1. 立即执行一次任务
2. 按配置的间隔定时执行
3. 按 `Ctrl+C` 停止

## 配置说明

### 邮箱配置

- `smtp_server`: SMTP 服务器地址
- `smtp_port`: SMTP 端口（126邮箱用465）
- `username`: 发件邮箱
- `password`: 邮箱密码或授权码
- `to`: 收件邮箱

### 新闻源配置

支持 RSS 格式的新闻源：

```yaml
sources:
  - name: 源名称
    type: rss
    url: RSS订阅地址
    enabled: true  # 是否启用
```

### 调度配置

- `interval_hours`: 执行间隔（小时）

## 常用 RSS 源

- Hacker News: https://news.ycombinator.com/rss
- Python News: https://www.python.org/feeds/community-events.rss.xml
- GitHub Trending: https://mshibanami.github.io/GitHubTrendingRSS/daily/all.xml

## 注意事项

1. 126 邮箱需要使用授权码，不是登录密码
2. 首次运行会发送所有新闻，之后只发送新内容
3. 数据保存在 `data/sent_news.json`

## License

MIT
