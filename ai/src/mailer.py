"""邮件发送模块 - 优化版"""
import smtplib
import re
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from dateutil import parser as date_parser


# 北京时区
BEIJING_TZ = timezone(timedelta(hours=8))

# 内容分类定义（按优先级排序）
CONTENT_CATEGORIES = [
    {"name": "Agent 专项", "icon": "A", "description": "Agent 框架、MCP、Multi-Agent、Tool Use", "color": "#6366f1", "bg": "#eef2ff"},
    {"name": "技术深度", "icon": "T", "description": "LLM、RAG、模型优化、算法创新", "color": "#0891b2", "bg": "#ecfeff"},
    {"name": "AWS 聚焦", "icon": "W", "description": "Bedrock、SageMaker、AWS AI 服务", "color": "#ea580c", "bg": "#fff7ed"},
    {"name": "行业动态", "icon": "I", "description": "企业落地、应用案例、市场趋势", "color": "#059669", "bg": "#ecfdf5"},
    {"name": "中文精选", "icon": "C", "description": "国内媒体、中文报道", "color": "#dc2626", "bg": "#fef2f2"},
    {"name": "论文精选", "icon": "P", "description": "arXiv、学术研究", "color": "#7c3aed", "bg": "#f5f3ff"},
]

# 新闻标签样式（精简为5种）
NEWS_LABELS = {
    "重磅": {"color": "#dc2626", "bg": "#fef2f2"},  # 重大事件、里程碑
    "融资": {"color": "#059669", "bg": "#ecfdf5"},  # 融资、估值、收购
    "发布": {"color": "#0891b2", "bg": "#ecfeff"},  # 新产品、新版本
    "开源": {"color": "#ea580c", "bg": "#fff7ed"},  # 开源项目
    "研究": {"color": "#6366f1", "bg": "#eef2ff"},  # 学术论文
}

# 来源类型分组（用于双栏布局）
SOURCE_TYPE_GROUPS = [
    {
        "name": "开源 & 工具",
        "icon": "🔧",
        "color": "#ea580c",
        "bg": "#fff7ed",
        "sources": ["GitHub Trending", "GitHub Blog", "HN Blog"]  # HN Blog 前缀匹配
    },
    {
        "name": "产品 & 应用",
        "icon": "🚀",
        "color": "#db2777",
        "bg": "#fdf2f8",
        "sources": ["Product Hunt"]
    },
    {
        "name": "技术博客",
        "icon": "📝",
        "color": "#0891b2",
        "bg": "#ecfeff",
        "sources": ["LlamaIndex", "LangChain", "Simon Willison", "Latent Space",
                    "Anthropic", "OpenAI", "DeepMind", "Google AI", "Meta AI",
                    "Hugging Face", "Ollama", "Replicate", "Together AI", "CrewAI"]
    },
    {
        "name": "行业新闻",
        "icon": "📰",
        "color": "#059669",
        "bg": "#ecfdf5",
        "sources": ["TechCrunch", "VentureBeat", "MIT Tech Review", "Hacker News",
                    "钛媒体", "36Kr", "机器之心", "新智元"]
    },
    {
        "name": "学术论文",
        "icon": "📚",
        "color": "#7c3aed",
        "bg": "#f5f3ff",
        "sources": ["arXiv"]  # 前缀匹配
    },
    {
        "name": "AWS & 云厂商",
        "icon": "☁️",
        "color": "#f59e0b",
        "bg": "#fffbeb",
        "sources": ["AWS", "Google Cloud", "Microsoft Research", "Semantic Kernel", "Azure"]
    },
]


def get_beijing_time():
    """获取北京时间"""
    return datetime.now(BEIJING_TZ)


def get_source_type_group(source_name):
    """根据来源名称获取所属的来源类型分组"""
    for group in SOURCE_TYPE_GROUPS:
        for src_pattern in group["sources"]:
            # 支持前缀匹配
            if source_name.startswith(src_pattern) or src_pattern in source_name:
                return group["name"]
    return "其他"  # 默认分组


def format_date(date_str):
    """统一格式化日期显示"""
    if not date_str:
        return ""

    try:
        dt = date_parser.parse(date_str)
        return dt.strftime('%Y-%m-%d')
    except:
        patterns = [
            r'(\d{4}-\d{2}-\d{2})',
            r'(\d{2}/\d{2}/\d{4})',
            r'(\w{3}\s+\d{1,2},?\s+\d{4})',
        ]
        for pattern in patterns:
            match = re.search(pattern, date_str)
            if match:
                try:
                    dt = date_parser.parse(match.group(1))
                    return dt.strftime('%Y-%m-%d')
                except:
                    pass
        return ""


def get_freshness_badge(date_str):
    """获取时效性标记"""
    if not date_str:
        return ""

    try:
        dt = date_parser.parse(date_str)
        now = datetime.now(BEIJING_TZ)
        # 确保 dt 有时区信息
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=BEIJING_TZ)

        hours_ago = (now - dt).total_seconds() / 3600

        if hours_ago < 6:
            return '<span style="background: #dc2626; color: white; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 600; margin-right: 6px;">NEW</span>'
        elif hours_ago < 24:
            return '<span style="background: #eab308; color: white; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 600; margin-right: 6px;">今日</span>'
        elif hours_ago < 48:
            return '<span style="background: #94a3b8; color: white; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 600; margin-right: 6px;">昨日</span>'
        else:
            return ""
    except:
        return ""


class Mailer:
    def __init__(self, config):
        self.provider = config.get('provider', 'smtp')
        # 解析收件人列表 (支持逗号分隔)
        to_raw = config['to']
        if isinstance(to_raw, list):
            self.to_emails = [e.strip() for e in to_raw]
        else:
            self.to_emails = [e.strip() for e in to_raw.split(',')]

        if self.provider == 'resend':
            self.resend_api_key = config.get('resend_api_key')
            self.from_email = config.get('from_email')
        else:
            self.smtp_server = config['smtp_server']
            self.smtp_port = config['smtp_port']
            self.username = config['username']
            self.password = config['password']

    def send(self, subject, content):
        """发送邮件"""
        if self.provider == 'resend':
            return self._send_resend(subject, content)
        else:
            return self._send_smtp(subject, content)

    def _send_resend(self, subject, content):
        """使用 Resend API 发送邮件"""
        try:
            response = requests.post(
                'https://api.resend.com/emails',
                headers={
                    'Authorization': f'Bearer {self.resend_api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'from': self.from_email,
                    'to': self.to_emails,
                    'subject': subject,
                    'html': content
                },
                timeout=30
            )

            if response.status_code == 200:
                print(f"邮件发送成功 (Resend): {subject}")
                return True
            else:
                print(f"邮件发送失败 (Resend): {response.status_code} - {response.text}")
                return False

        except Exception as e:
            print(f"邮件发送失败 (Resend): {e}")
            return False

    def _send_smtp(self, subject, content):
        """使用 SMTP 发送邮件"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.username
            msg['To'] = ', '.join(self.to_emails)
            msg['Subject'] = subject

            msg.attach(MIMEText(content, 'html', 'utf-8'))

            server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            server.login(self.username, self.password)
            server.sendmail(self.username, self.to_emails, msg.as_string())
            server.quit()

            print(f"邮件发送成功 (SMTP): {subject}")
            return True

        except Exception as e:
            print(f"邮件发送失败 (SMTP): {e}")
            return False

    def format_news_email(self, items, ai_analysis=None):
        """格式化新闻邮件内容 - 现代化设计"""
        if not items:
            return None, None

        # 获取北京时间
        beijing_now = get_beijing_time()

        # 邮件主题 - 专业品牌化
        subject = f"AI Daily | 生成式AI日报 - {beijing_now.strftime('%Y年%m月%d日')}"

        # 现代化样式设计
        html = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, "SF Pro SC", "SF Pro Text", "Helvetica Neue", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
                    line-height: 1.7;
                    color: #1a1a2e;
                    background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
                    padding: 24px;
                    -webkit-font-smoothing: antialiased;
                }}

                .container {{
                    max-width: 720px;
                    margin: 0 auto;
                    background: #ffffff;
                    border-radius: 16px;
                    overflow: hidden;
                    box-shadow: 0 4px 24px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.04);
                }}

                /* 头部设计 - 大胆渐变 */
                .header {{
                    background: linear-gradient(135deg, #1e293b 0%, #334155 50%, #475569 100%);
                    color: white;
                    padding: 40px 32px;
                    position: relative;
                    overflow: hidden;
                }}
                .header::before {{
                    content: "";
                    position: absolute;
                    top: -50%;
                    right: -20%;
                    width: 300px;
                    height: 300px;
                    background: radial-gradient(circle, rgba(99,102,241,0.3) 0%, transparent 70%);
                    border-radius: 50%;
                }}
                .header::after {{
                    content: "";
                    position: absolute;
                    bottom: -30%;
                    left: -10%;
                    width: 200px;
                    height: 200px;
                    background: radial-gradient(circle, rgba(234,88,12,0.2) 0%, transparent 70%);
                    border-radius: 50%;
                }}
                .header-content {{
                    position: relative;
                    z-index: 1;
                }}
                .header h1 {{
                    font-size: 28px;
                    font-weight: 700;
                    letter-spacing: -0.5px;
                    margin-bottom: 8px;
                }}
                .header .subtitle {{
                    font-size: 16px;
                    color: rgba(255,255,255,0.9);
                    font-weight: 500;
                    margin-bottom: 4px;
                }}
                .header .date-line {{
                    font-size: 13px;
                    color: rgba(255,255,255,0.7);
                    font-weight: 400;
                }}
                .header .stats {{
                    display: flex;
                    gap: 24px;
                    margin-top: 20px;
                }}
                .header .stat-item {{
                    background: rgba(255,255,255,0.1);
                    backdrop-filter: blur(10px);
                    padding: 12px 20px;
                    border-radius: 10px;
                    border: 1px solid rgba(255,255,255,0.1);
                }}
                .header .stat-value {{
                    font-size: 24px;
                    font-weight: 700;
                    color: #fff;
                }}
                .header .stat-label {{
                    font-size: 12px;
                    color: rgba(255,255,255,0.7);
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }}

                /* AI 分析区域 */
                .ai-section {{
                    padding: 32px;
                    background: linear-gradient(180deg, #fafafa 0%, #ffffff 100%);
                    border-bottom: 1px solid #e5e7eb;
                }}
                .section-header {{
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    margin-bottom: 24px;
                }}
                .section-badge {{
                    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
                    color: white;
                    font-size: 11px;
                    font-weight: 600;
                    padding: 6px 12px;
                    border-radius: 6px;
                    letter-spacing: 0.5px;
                    text-transform: uppercase;
                }}
                .section-title {{
                    font-size: 20px;
                    font-weight: 700;
                    color: #1e293b;
                }}

                /* 今日聚焦卡片 */
                .insight-card {{
                    background: #ffffff;
                    border: 1px solid #e5e7eb;
                    border-radius: 12px;
                    padding: 24px;
                    margin-bottom: 24px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
                }}
                .insight-card .label {{
                    font-size: 13px;
                    font-weight: 600;
                    color: #6366f1;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                    margin-bottom: 16px;
                }}
                .insight-list {{
                    list-style: none;
                    padding: 0;
                    margin: 0;
                }}
                .insight-list li {{
                    position: relative;
                    padding: 10px 0 10px 24px;
                    border-bottom: 1px solid #f1f5f9;
                    font-size: 15px;
                    color: #334155;
                    line-height: 1.6;
                }}
                .insight-list li:last-child {{
                    border-bottom: none;
                }}
                .insight-list li::before {{
                    content: "";
                    position: absolute;
                    left: 0;
                    top: 18px;
                    width: 8px;
                    height: 8px;
                    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
                    border-radius: 50%;
                }}

                /* 趋势标签 */
                .trends-container {{
                    margin-bottom: 24px;
                }}
                .trends-label {{
                    font-size: 13px;
                    font-weight: 600;
                    color: #64748b;
                    margin-bottom: 12px;
                    display: block;
                }}
                .trends-list {{
                    display: flex;
                    flex-wrap: wrap;
                    gap: 8px;
                }}
                .trend-tag {{
                    background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
                    color: #fff;
                    padding: 8px 16px;
                    border-radius: 20px;
                    font-size: 13px;
                    font-weight: 500;
                }}

                /* TOP 新闻 - 编号卡片 */
                .top-news {{
                    margin-top: 8px;
                }}
                .top-news-label {{
                    font-size: 13px;
                    font-weight: 600;
                    color: #64748b;
                    margin-bottom: 16px;
                    display: block;
                }}
                .top-item {{
                    display: flex;
                    gap: 16px;
                    padding: 16px;
                    background: #ffffff;
                    border: 1px solid #e5e7eb;
                    border-radius: 12px;
                    margin-bottom: 12px;
                    transition: all 0.2s ease;
                }}
                .top-item:hover {{
                    border-color: #6366f1;
                    box-shadow: 0 4px 12px rgba(99,102,241,0.1);
                }}
                .top-rank {{
                    flex-shrink: 0;
                    width: 44px;
                    height: 44px;
                    background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
                    border-radius: 10px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 18px;
                    font-weight: 700;
                    color: #1e293b;
                }}
                .top-content {{
                    flex: 1;
                    min-width: 0;
                }}
                .top-title {{
                    font-size: 15px;
                    font-weight: 600;
                    color: #1e293b;
                    text-decoration: none;
                    line-height: 1.4;
                    display: block;
                    margin-bottom: 6px;
                }}
                .top-title:hover {{
                    color: #6366f1;
                }}
                .top-meta {{
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    flex-wrap: wrap;
                }}
                .score-pill {{
                    background: #6366f1;
                    color: white;
                    font-size: 11px;
                    font-weight: 600;
                    padding: 3px 8px;
                    border-radius: 4px;
                }}
                .source-pill {{
                    background: #f1f5f9;
                    color: #64748b;
                    font-size: 11px;
                    font-weight: 500;
                    padding: 3px 8px;
                    border-radius: 4px;
                }}
                /* 翻译样式 - 移除斜体 */
                .translation {{
                    color: #64748b;
                    font-size: 14px;
                    font-weight: 400;
                    margin-top: 8px;
                    padding-left: 16px;
                    border-left: 3px solid #e2e8f0;
                    line-height: 1.6;
                }}
                .top-reason {{
                    color: #64748b;
                    font-size: 13px;
                    margin-top: 10px;
                    padding-top: 10px;
                    border-top: 1px dashed #e5e7eb;
                    line-height: 1.5;
                }}

                /* 新闻列表区域 */
                .news-section {{
                    padding: 32px;
                }}
                .news-section-title {{
                    font-size: 20px;
                    font-weight: 700;
                    color: #1e293b;
                    margin-bottom: 24px;
                }}

                /* 分类组 */
                .category-group {{
                    margin-bottom: 32px;
                }}
                .category-header {{
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: 16px 20px;
                    border-radius: 12px;
                    margin-bottom: 16px;
                }}
                .category-left {{
                    display: flex;
                    align-items: center;
                    gap: 12px;
                }}
                .category-icon {{
                    width: 36px;
                    height: 36px;
                    border-radius: 8px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 16px;
                    font-weight: 700;
                    color: white;
                }}
                .category-name {{
                    font-size: 17px;
                    font-weight: 700;
                }}
                .category-desc {{
                    font-size: 13px;
                    color: #64748b;
                    margin-top: 2px;
                }}
                .category-count {{
                    background: rgba(0,0,0,0.08);
                    padding: 4px 12px;
                    border-radius: 20px;
                    font-size: 13px;
                    font-weight: 600;
                }}

                /* 新闻卡片 */
                .news-card {{
                    background: #ffffff;
                    border: 1px solid #e5e7eb;
                    border-radius: 12px;
                    padding: 20px;
                    margin-bottom: 12px;
                    transition: all 0.2s ease;
                }}
                .news-card:hover {{
                    border-color: #cbd5e1;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
                }}
                .news-card.is-top {{
                    border-left: 4px solid #fbbf24;
                    background: linear-gradient(135deg, #fffbeb 0%, #ffffff 100%);
                }}
                .news-title {{
                    font-size: 16px;
                    font-weight: 600;
                    line-height: 1.5;
                    margin-bottom: 8px;
                }}
                .news-title a {{
                    color: #1e293b;
                    text-decoration: none;
                }}
                .news-title a:hover {{
                    color: #6366f1;
                }}
                .news-meta {{
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    flex-wrap: wrap;
                    margin-bottom: 12px;
                }}
                .meta-badge {{
                    font-size: 11px;
                    font-weight: 600;
                    padding: 3px 8px;
                    border-radius: 4px;
                }}
                .meta-badge.score {{
                    background: #6366f1;
                    color: white;
                }}
                .meta-badge.top {{
                    background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
                    color: #1e293b;
                }}
                .meta-badge.source {{
                    background: #f1f5f9;
                    color: #64748b;
                }}
                .meta-date {{
                    color: #94a3b8;
                    font-size: 12px;
                }}
                .news-summary {{
                    color: #475569;
                    font-size: 14px;
                    line-height: 1.7;
                }}
                .news-translation {{
                    color: #64748b;
                    font-size: 14px;
                    margin-top: 10px;
                    padding: 12px 16px;
                    background: #f8fafc;
                    border-radius: 8px;
                    border-left: 3px solid #e2e8f0;
                    line-height: 1.6;
                }}

                /* 页脚 */
                .footer {{
                    background: #f8fafc;
                    padding: 24px 32px;
                    text-align: center;
                    border-top: 1px solid #e5e7eb;
                }}
                .footer-text {{
                    color: #94a3b8;
                    font-size: 13px;
                    line-height: 1.8;
                }}
                .footer-highlight {{
                    color: #6366f1;
                    font-weight: 500;
                }}

                /* 开篇评论区域 */
                .commentary-section {{
                    padding: 28px 32px;
                    background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
                    border-bottom: 1px solid #bae6fd;
                }}
                .commentary-content {{
                    font-size: 15px;
                    line-height: 1.8;
                    color: #0c4a6e;
                    padding: 20px 24px;
                    background: rgba(255,255,255,0.7);
                    border-radius: 12px;
                    border-left: 4px solid #0284c7;
                }}

                /* 热点专题区域 */
                .clusters-section {{
                    padding: 28px 32px;
                    background: #fefce8;
                    border-bottom: 1px solid #fde047;
                }}
                .cluster-card {{
                    background: #ffffff;
                    border: 1px solid #fde047;
                    border-radius: 12px;
                    padding: 20px;
                    margin-bottom: 16px;
                }}
                .cluster-topic {{
                    font-size: 16px;
                    font-weight: 700;
                    color: #854d0e;
                    margin-bottom: 8px;
                }}
                .cluster-summary {{
                    font-size: 14px;
                    color: #a16207;
                    margin-bottom: 12px;
                }}
                .cluster-news-list {{
                    list-style: none;
                    padding: 0;
                    margin: 0;
                }}
                .cluster-news-item {{
                    padding: 8px 0;
                    border-top: 1px solid #fef3c7;
                }}
                .cluster-news-item:first-child {{
                    border-top: none;
                }}
                .cluster-news-item a {{
                    color: #78350f;
                    text-decoration: none;
                    font-size: 14px;
                }}
                .cluster-news-item a:hover {{
                    color: #d97706;
                }}
                .cluster-source {{
                    font-size: 12px;
                    color: #a16207;
                    margin-left: 8px;
                }}

                /* 数据统计表 */
                .data-section {{
                    padding: 28px 32px;
                    background: #f0fdf4;
                    border-bottom: 1px solid #86efac;
                }}
                .data-table {{
                    width: 100%;
                    border-collapse: collapse;
                    background: #ffffff;
                    border-radius: 12px;
                    overflow: hidden;
                }}
                .data-table th {{
                    background: #166534;
                    color: white;
                    padding: 12px 16px;
                    text-align: left;
                    font-size: 13px;
                    font-weight: 600;
                }}
                .data-table td {{
                    padding: 12px 16px;
                    border-bottom: 1px solid #dcfce7;
                    font-size: 14px;
                    color: #14532d;
                }}
                .data-table tr:last-child td {{
                    border-bottom: none;
                }}
                .data-type {{
                    display: inline-block;
                    padding: 2px 8px;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: 600;
                }}
                .data-type.funding {{ background: #fef3c7; color: #92400e; }}
                .data-type.valuation {{ background: #ede9fe; color: #5b21b6; }}
                .data-type.users {{ background: #dbeafe; color: #1e40af; }}
                .data-type.performance {{ background: #d1fae5; color: #065f46; }}
                .data-type.model {{ background: #fce7f3; color: #9d174d; }}
            </style>
        </head>
        <body>
            <div class="container">
                <!-- 头部 - 品牌化设计 -->
                <div class="header">
                    <div class="header-content">
                        <h1>AI Daily</h1>
                        <div class="subtitle">生成式AI与智能体技术日报</div>
                        <div class="date-line">{beijing_now.strftime('%Y年%m月%d日')} · 北京时间</div>
                        <div class="stats">
                            <div class="stat-item">
                                <div class="stat-value">{len(items)}</div>
                                <div class="stat-label">今日新闻</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-value">{len([i for i in items if i.get('ai_score', 0) >= 7])}</div>
                                <div class="stat-label">重点推荐</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-value">{len(ai_analysis.get('trends', [])) if ai_analysis else 0}</div>
                                <div class="stat-label">关键趋势</div>
                            </div>
                        </div>
                    </div>
                </div>
        """

        # 本周新星区域 - 展示 GitHub Trending 和 Product Hunt
        github_items = [item for item in items if item.get('source') == 'GitHub Trending'][:3]
        ph_items = [item for item in items if item.get('source') == 'Product Hunt'][:3]

        if github_items or ph_items:
            html += """
                <div id="discoveries" style="padding: 24px 32px; background: linear-gradient(135deg, #fdf2f8 0%, #fce7f3 100%); border-bottom: 1px solid #f9a8d4;">
                    <div class="section-header">
                        <span class="section-badge" style="background: linear-gradient(135deg, #db2777 0%, #be185d 100%);">🔥 本周新星</span>
                        <span class="section-title">开源项目 & 新产品发现</span>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 16px;">
            """

            # GitHub Trending 列
            if github_items:
                html += """
                        <div style="background: white; border-radius: 12px; padding: 16px; border: 1px solid #f9a8d4;">
                            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
                                <span style="font-size: 18px;">⭐</span>
                                <span style="font-weight: 700; color: #831843;">开源热门</span>
                            </div>
                """
                for item in github_items:
                    title = item.get('title', '')[:50]
                    link = item.get('link', '#')
                    summary = item.get('summary', '')[:60]
                    html += f"""
                            <div style="padding: 10px 0; border-bottom: 1px solid #fce7f3;">
                                <a href="{link}" target="_blank" style="color: #be185d; text-decoration: none; font-weight: 600; font-size: 13px; display: block; margin-bottom: 4px;">{title}</a>
                                <div style="font-size: 11px; color: #9d174d;">{summary}</div>
                            </div>
                    """
                html += """
                        </div>
                """

            # Product Hunt 列
            if ph_items:
                html += """
                        <div style="background: white; border-radius: 12px; padding: 16px; border: 1px solid #f9a8d4;">
                            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
                                <span style="font-size: 18px;">🚀</span>
                                <span style="font-weight: 700; color: #831843;">产品发现</span>
                            </div>
                """
                for item in ph_items:
                    title = item.get('title', '')[:50]
                    link = item.get('link', '#')
                    summary = item.get('summary', '')[:60]
                    html += f"""
                            <div style="padding: 10px 0; border-bottom: 1px solid #fce7f3;">
                                <a href="{link}" target="_blank" style="color: #be185d; text-decoration: none; font-weight: 600; font-size: 13px; display: block; margin-bottom: 4px;">{title}</a>
                                <div style="font-size: 11px; color: #9d174d;">{summary}</div>
                            </div>
                    """
                html += """
                        </div>
                """

            html += """
                    </div>
                </div>
            """

        # 开篇评论区域（在 AI 分析前显示）
        if ai_analysis and ai_analysis.get('commentary'):
            html += f"""
                <div id="commentary" class="commentary-section">
                    <div class="section-header">
                        <span class="section-badge" style="background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);">开篇评论</span>
                    </div>
                    <div class="commentary-content">
                        {ai_analysis['commentary']}
                    </div>
                </div>
            """

        # AI 分析区域
        if ai_analysis:
            html += """
                <div class="ai-section">
                    <div class="section-header">
                        <span class="section-badge">AI 分析</span>
                        <span class="section-title">智能洞察</span>
                    </div>
            """

            # Bullet Points 总结
            if ai_analysis.get('summary'):
                summary_lines = [line.strip() for line in ai_analysis['summary'].split('\n') if line.strip()]
                html += """
                    <div class="insight-card">
                        <div class="label">今日聚焦</div>
                        <ul class="insight-list">
                """
                for line in summary_lines:
                    clean_line = line.lstrip('- ').strip()
                    if clean_line:
                        html += f'<li>{clean_line}</li>'
                html += """
                        </ul>
                    </div>
                """

            html += "</div>"

        # 行动建议区域
        if ai_analysis and ai_analysis.get('action_items'):
            html += """
                <div id="actions" style="padding: 28px 32px; background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%); border-bottom: 1px solid #6ee7b7;">
                    <div class="section-header">
                        <span class="section-badge" style="background: linear-gradient(135deg, #059669 0%, #047857 100%);">行动建议</span>
                        <span class="section-title">技术决策者必读</span>
                    </div>
                    <div style="display: grid; gap: 12px; margin-top: 16px;">
            """
            priority_colors = {
                'high': '#dc2626',
                'medium': '#d97706',
                'low': '#6b7280'
            }
            for action in ai_analysis['action_items'][:5]:
                action_type = action.get('type', '关注')
                title = action.get('title', '')
                reason = action.get('reason', '')
                action_text = action.get('action', '')
                priority = action.get('priority', 'medium')
                priority_color = priority_colors.get(priority, '#6b7280')

                html += f"""
                        <div style="background: #ffffff; border-radius: 12px; padding: 16px 20px; border-left: 4px solid {priority_color}; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                                <span style="font-size: 15px; font-weight: 700; color: #065f46;">{title}</span>
                                <span style="background: {priority_color}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: 600; margin-left: auto;">{priority.upper()}</span>
                            </div>
                            <div style="font-size: 13px; color: #047857; margin-bottom: 8px;">{reason}</div>
                            <div style="font-size: 13px; color: #065f46; font-weight: 500; padding: 8px 12px; background: #ecfdf5; border-radius: 6px;">
                                →{action_text}
                            </div>
                        </div>
                """
            html += """
                    </div>
                </div>
            """

        # 论文精选区域（新版：显示领域、难度、可操作建议）
        if ai_analysis and ai_analysis.get('paper_analysis'):
            # 难度对应颜色
            difficulty_colors = {
                '入门': {'bg': '#d1fae5', 'color': '#065f46'},
                '进阶': {'bg': '#fef3c7', 'color': '#92400e'},
                '专家': {'bg': '#fee2e2', 'color': '#991b1b'}
            }
            html += """
                <div id="papers" class="papers-section" style="padding: 28px 32px; background: #f5f3ff; border-bottom: 1px solid #c4b5fd;">
                    <div class="section-header">
                        <span class="section-badge" style="background: linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%);">论文精选</span>
                        <span class="section-title">本期学术亮点</span>
                    </div>
            """
            for paper in ai_analysis['paper_analysis'][:6]:
                original = paper.get('original', {})
                link = original.get('link', '#')
                title = original.get('title', '')
                title_zh = paper.get('title_zh', '')
                contribution = paper.get('contribution', '')
                domain = paper.get('domain', '')
                difficulty = paper.get('difficulty', '进阶')
                takeaway = paper.get('takeaway', '')
                diff_style = difficulty_colors.get(difficulty, difficulty_colors['进阶'])

                html += f"""
                    <div style="background: #ffffff; border: 1px solid #ddd6fe; border-radius: 12px; padding: 20px; margin-bottom: 12px;">
                        <div style="display: flex; gap: 8px; margin-bottom: 10px;">
                            <span style="background: #ede9fe; color: #6d28d9; padding: 2px 8px; border-radius: 4px; font-size: 11px;">{domain}</span>
                            <span style="background: {diff_style['bg']}; color: {diff_style['color']}; padding: 2px 8px; border-radius: 4px; font-size: 11px;">{difficulty}</span>
                        </div>
                        <div style="font-size: 14px; font-weight: 600; color: #5b21b6; margin-bottom: 6px;">
                            <a href="{link}" target="_blank" style="color: #5b21b6; text-decoration: none;">{title_zh or title}</a>
                        </div>
                        <div style="font-size: 13px; color: #4c1d95; margin-bottom: 10px;">{contribution}</div>
                        <div style="font-size: 12px; color: #065f46; background: #ecfdf5; padding: 8px 12px; border-radius: 6px;">
                            <strong>工程师可做：</strong>{takeaway}
                        </div>
                    </div>
                """
            html += "</div>"

        # 完整新闻 - 按具体来源分组（多栏布局）
        html += """
            <div id="newslist" class="news-section">
                <h2 class="news-section-title">完整新闻列表</h2>
        """

        # 按具体来源分组
        grouped_by_source = defaultdict(list)
        for item in items:
            source = item.get('source', '未知来源')
            grouped_by_source[source].append(item)

        # 获取 TOP 新闻的 ID
        top_ids = set()
        if ai_analysis and ai_analysis.get('top_news'):
            for top_item in ai_analysis['top_news']:
                if 'id' in top_item:
                    top_ids.add(top_item['id'])

        # 来源排序：按新闻数量降序，确保内容多的来源优先显示
        sorted_sources = sorted(grouped_by_source.keys(), key=lambda s: len(grouped_by_source[s]), reverse=True)

        # 为每个来源分配颜色（循环使用）
        source_colors = [
            {"color": "#6366f1", "bg": "#eef2ff"},  # 紫色
            {"color": "#0891b2", "bg": "#ecfeff"},  # 青色
            {"color": "#ea580c", "bg": "#fff7ed"},  # 橙色
            {"color": "#059669", "bg": "#ecfdf5"},  # 绿色
            {"color": "#dc2626", "bg": "#fef2f2"},  # 红色
            {"color": "#7c3aed", "bg": "#f5f3ff"},  # 紫罗兰
            {"color": "#0284c7", "bg": "#e0f2fe"},  # 蓝色
            {"color": "#be185d", "bg": "#fce7f3"},  # 粉色
        ]

        # 来源图标映射
        source_icons = {
            "GitHub Trending": "⭐", "GitHub Blog": "🐙", "Product Hunt": "🚀",
            "LangChain": "🦜", "LlamaIndex": "🦙", "OpenAI": "🤖", "Anthropic": "🧠",
            "Google AI": "🔍", "DeepMind": "🧬", "Meta AI": "👁️", "Hugging Face": "🤗",
            "TechCrunch": "📰", "VentureBeat": "📊", "Hacker News": "🔶",
            "arXiv": "📚", "AWS": "☁️", "Simon Willison": "✍️", "Latent Space": "🎙️",
            "CrewAI": "👥", "钛媒体": "📱", "36Kr": "💰", "机器之心": "🤖", "新智元": "🧠",
        }

        # 多栏布局
        html += '<div style="display: flex; flex-wrap: wrap; gap: 12px; margin-top: 16px;">'

        for idx, source_name in enumerate(sorted_sources):
            source_items = grouped_by_source[source_name]
            color_info = source_colors[idx % len(source_colors)]

            # 分组内按评分排序
            source_items = sorted(source_items, key=lambda x: x.get('ai_score', 0), reverse=True)

            # 获取来源图标
            icon = "📄"
            for key, val in source_icons.items():
                if key in source_name:
                    icon = val
                    break

            # 每个来源占满一行
            html += f"""
                <div style="flex: 1 1 100%; background: {color_info['bg']}; border-radius: 12px; padding: 14px; margin-bottom: 8px; border: 1px solid {color_info['color']}20;">
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 10px; padding-bottom: 10px; border-bottom: 1px solid {color_info['color']}30;">
                        <span style="font-size: 18px;">{icon}</span>
                        <span style="font-weight: 700; color: {color_info['color']}; font-size: 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{source_name}</span>
                        <span style="margin-left: auto; background: {color_info['color']}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600;">{len(source_items)}</span>
                    </div>
            """

            for item in source_items:
                is_top = item.get('id') in top_ids
                title = item.get('title', '')[:70]
                title_zh = item.get('title_zh', '')
                link = item.get('link', '#')
                pub_date = format_date(item.get('published', ''))
                freshness = get_freshness_badge(item.get('published', ''))

                # 标签
                label = item.get('label', '')
                label_html = ''
                if label and label in NEWS_LABELS:
                    ls = NEWS_LABELS[label]
                    label_html = f'<span style="background: {ls["bg"]}; color: {ls["color"]}; padding: 1px 6px; border-radius: 3px; font-size: 10px; font-weight: 600; margin-right: 4px;">{label}</span>'

                # TOP 标记
                top_html = '<span style="background: #dc2626; color: white; padding: 1px 4px; border-radius: 3px; font-size: 9px; font-weight: 700; margin-right: 4px;">TOP</span>' if is_top else ''

                # Agent 标记
                is_agent = item.get('is_agent_related', False)
                agent_html = '<span style="background: #6366f1; color: white; padding: 1px 4px; border-radius: 3px; font-size: 9px; font-weight: 700; margin-right: 4px;">Agent</span>' if is_agent else ''

                html += f"""
                    <div style="padding: 8px 0; border-bottom: 1px solid {color_info['color']}15;">
                        <div style="margin-bottom: 4px;">
                            {freshness}{top_html}{agent_html}{label_html}
                            <a href="{link}" target="_blank" style="color: #1e293b; text-decoration: none; font-weight: 600; font-size: 12px; line-height: 1.4;">{title}</a>
                        </div>
                        {f'<div style="font-size: 11px; color: #64748b; margin-bottom: 4px;">{title_zh[:50]}...</div>' if title_zh else ''}
                        <div style="font-size: 10px; color: #94a3b8;">{pub_date}</div>
                    </div>
                """

            html += "</div>"

        html += "</div></div>"

        # 页脚
        source_count = len(grouped_by_source)
        html += f"""
                <div class="footer">
                    <p class="footer-text">
                        共 {source_count} 个来源 · {len(items)} 条新闻
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

        return subject, html

    def format_weekly_email(self, analysis, week_start, week_end):
        """格式化周报邮件内容"""
        if not analysis:
            return None, None

        # 获取北京时间
        beijing_now = get_beijing_time()

        # 邮件主题
        subject = f"AI 周报 - {week_start.strftime('%m/%d')} ~ {week_end.strftime('%m/%d')} ({beijing_now.strftime('%Y-%m-%d')})"

        # 周报 HTML
        html = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, "SF Pro SC", "SF Pro Text", "Helvetica Neue", "PingFang SC", sans-serif;
                    line-height: 1.7;
                    color: #1a1a2e;
                    background: linear-gradient(135deg, #fdf4ff 0%, #f5f3ff 100%);
                    padding: 24px;
                }}
                .container {{
                    max-width: 720px;
                    margin: 0 auto;
                    background: #ffffff;
                    border-radius: 16px;
                    overflow: hidden;
                    box-shadow: 0 4px 24px rgba(0,0,0,0.08);
                }}
                .header {{
                    background: linear-gradient(135deg, #7c3aed 0%, #a855f7 50%, #c084fc 100%);
                    color: white;
                    padding: 40px 32px;
                    position: relative;
                }}
                .header h1 {{
                    font-size: 32px;
                    font-weight: 700;
                    margin-bottom: 8px;
                }}
                .header .period {{
                    font-size: 16px;
                    color: rgba(255,255,255,0.9);
                }}
                .header .stats {{
                    display: flex;
                    gap: 24px;
                    margin-top: 20px;
                }}
                .header .stat-item {{
                    background: rgba(255,255,255,0.15);
                    padding: 12px 20px;
                    border-radius: 10px;
                }}
                .header .stat-value {{
                    font-size: 28px;
                    font-weight: 700;
                }}
                .header .stat-label {{
                    font-size: 12px;
                    color: rgba(255,255,255,0.8);
                }}
                .section {{
                    padding: 32px;
                    border-bottom: 1px solid #e5e7eb;
                }}
                .section-title {{
                    font-size: 20px;
                    font-weight: 700;
                    color: #1e293b;
                    margin-bottom: 20px;
                    display: flex;
                    align-items: center;
                    gap: 12px;
                }}
                .section-badge {{
                    background: linear-gradient(135deg, #7c3aed 0%, #a855f7 100%);
                    color: white;
                    font-size: 11px;
                    padding: 6px 12px;
                    border-radius: 6px;
                    font-weight: 600;
                }}
                .summary-box {{
                    background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
                    padding: 24px;
                    border-radius: 12px;
                    font-size: 15px;
                    line-height: 1.8;
                    color: #4c1d95;
                    border-left: 4px solid #7c3aed;
                }}
                .trends-list {{
                    display: flex;
                    flex-wrap: wrap;
                    gap: 10px;
                }}
                .trend-tag {{
                    background: linear-gradient(135deg, #7c3aed 0%, #a855f7 100%);
                    color: white;
                    padding: 10px 18px;
                    border-radius: 25px;
                    font-size: 14px;
                    font-weight: 500;
                }}
                .highlight-card {{
                    background: #fffbeb;
                    border: 1px solid #fde047;
                    border-radius: 12px;
                    padding: 20px;
                    margin-bottom: 12px;
                }}
                .highlight-title {{
                    font-size: 16px;
                    font-weight: 700;
                    color: #854d0e;
                    margin-bottom: 8px;
                }}
                .highlight-impact {{
                    font-size: 14px;
                    color: #a16207;
                }}
                .top-news-card {{
                    display: flex;
                    gap: 16px;
                    padding: 20px;
                    background: #ffffff;
                    border: 1px solid #e5e7eb;
                    border-radius: 12px;
                    margin-bottom: 12px;
                }}
                .top-news-card:hover {{
                    border-color: #7c3aed;
                    box-shadow: 0 4px 12px rgba(124,58,237,0.1);
                }}
                .top-rank {{
                    width: 48px;
                    height: 48px;
                    background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
                    border-radius: 12px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 20px;
                    font-weight: 700;
                    color: #1e293b;
                    flex-shrink: 0;
                }}
                .top-content {{
                    flex: 1;
                }}
                .top-title {{
                    font-size: 16px;
                    font-weight: 600;
                    color: #1e293b;
                    text-decoration: none;
                    display: block;
                    margin-bottom: 8px;
                }}
                .top-title:hover {{
                    color: #7c3aed;
                }}
                .top-reason {{
                    font-size: 14px;
                    color: #64748b;
                    line-height: 1.5;
                }}
                .top-source {{
                    font-size: 12px;
                    color: #94a3b8;
                    margin-top: 8px;
                }}
                .outlook-box {{
                    background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
                    padding: 24px;
                    border-radius: 12px;
                    font-size: 15px;
                    line-height: 1.8;
                    color: #065f46;
                    border-left: 4px solid #10b981;
                }}
                .footer {{
                    background: #f8fafc;
                    padding: 24px 32px;
                    text-align: center;
                }}
                .footer-text {{
                    color: #94a3b8;
                    font-size: 13px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>AI 周报</h1>
                    <div class="period">{week_start.strftime('%Y年%m月%d日')} - {week_end.strftime('%Y年%m月%d日')}</div>
                    <div class="stats">
                        <div class="stat-item">
                            <div class="stat-value">{analysis.get('weekly_stats', {}).get('total_news', 0)}</div>
                            <div class="stat-label">本周新闻总数</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value">{len(analysis.get('top_news', []))}</div>
                            <div class="stat-label">精选推荐</div>
                        </div>
                    </div>
                </div>
        """

        # 本周综述
        if analysis.get('summary'):
            html += f"""
                <div class="section">
                    <div class="section-title">
                        <span class="section-badge">综述</span>
                        本周概览
                    </div>
                    <div class="summary-box">
                        {analysis['summary']}
                    </div>
                </div>
            """

        # 关键趋势
        if analysis.get('trends'):
            html += """
                <div class="section">
                    <div class="section-title">
                        <span class="section-badge">趋势</span>
                        本周关键趋势
                    </div>
                    <div class="trends-list">
            """
            for trend in analysis['trends']:
                html += f'<span class="trend-tag">{trend}</span>'
            html += """
                    </div>
                </div>
            """

        # 重点事件
        if analysis.get('highlights'):
            html += """
                <div class="section">
                    <div class="section-title">
                        <span class="section-badge">聚焦</span>
                        重点事件
                    </div>
            """
            for highlight in analysis['highlights']:
                html += f"""
                    <div class="highlight-card">
                        <div class="highlight-title">{highlight.get('title', '')}</div>
                        <div class="highlight-impact">{highlight.get('impact', '')}</div>
                    </div>
                """
            html += "</div>"

        # TOP 新闻
        if analysis.get('top_news'):
            html += """
                <div class="section">
                    <div class="section-title">
                        <span class="section-badge">精选</span>
                        本周 TOP 新闻
                    </div>
            """
            for idx, news in enumerate(analysis['top_news'], 1):
                title = news.get('title_zh') or news.get('title', '')
                link = news.get('link', '#')
                source = news.get('source', '')
                reason = news.get('weekly_reason', '')

                html += f"""
                    <div class="top-news-card">
                        <div class="top-rank">{idx}</div>
                        <div class="top-content">
                            <a href="{link}" target="_blank" class="top-title">{title}</a>
                            {f'<div class="top-reason">{reason}</div>' if reason else ''}
                            <div class="top-source">{source}</div>
                        </div>
                    </div>
                """
            html += "</div>"

        # 下周展望
        if analysis.get('outlook'):
            html += f"""
                <div class="section">
                    <div class="section-title">
                        <span class="section-badge">展望</span>
                        下周看点
                    </div>
                    <div class="outlook-box">
                        {analysis['outlook']}
                    </div>
                </div>
            """

        # 页脚
        html += f"""
                <div class="footer">
                    <p class="footer-text">
                        AI 周报 · {week_start.strftime('%Y年%m月%d日')} - {week_end.strftime('%Y年%m月%d日')}
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

        return subject, html
