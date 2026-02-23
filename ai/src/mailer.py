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

# 内容类型标签（用于标记而非过滤）
CONTENT_TYPE_BADGES = {
    "corporate": {"label": "企业", "color": "#9ca3af", "bg": "#f3f4f6"},  # 企业新闻
    "low_value": {"label": "引用", "color": "#9ca3af", "bg": "#f3f4f6"},  # 低价值内容
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
    """获取时效性标记 - McKinsey 风格"""
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
            # NEW - 金色背景，深蓝文字
            return '<span style="background: #FDB813; color: #00205B; padding: 1px 6px; font-size: 9px; font-weight: 700; margin-right: 4px;">NEW</span>'
        elif hours_ago < 24:
            # 今日 - 深蓝背景
            return '<span style="background: #00205B; color: white; padding: 1px 6px; font-size: 9px; font-weight: 700; margin-right: 4px;">今日</span>'
        elif hours_ago < 48:
            # 昨日 - 浅灰背景
            return '<span style="background: #e0e0e0; color: #666666; padding: 1px 6px; font-size: 9px; font-weight: 600; margin-right: 4px;">昨日</span>'
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

        # McKinsey 风格设计
        html = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{
                    font-family: Georgia, "Times New Roman", serif;
                    line-height: 1.6;
                    color: #333333;
                    background: #f5f5f5;
                    padding: 20px;
                    -webkit-font-smoothing: antialiased;
                }}

                .container {{
                    max-width: 680px;
                    margin: 0 auto;
                    background: #ffffff;
                    border: 1px solid #e0e0e0;
                }}

                /* 头部 - McKinsey 深蓝 */
                .header {{
                    background: #00205B;
                    color: white;
                    padding: 32px 40px;
                    border-bottom: 4px solid #FDB813;
                }}
                .header h1 {{
                    font-family: Georgia, serif;
                    font-size: 26px;
                    font-weight: 400;
                    letter-spacing: 1px;
                    margin-bottom: 8px;
                }}
                .header .subtitle {{
                    font-family: Arial, Helvetica, sans-serif;
                    font-size: 13px;
                    color: rgba(255,255,255,0.8);
                    font-weight: 400;
                    letter-spacing: 0.5px;
                    text-transform: uppercase;
                }}
                .header .date-line {{
                    font-family: Arial, Helvetica, sans-serif;
                    font-size: 12px;
                    color: rgba(255,255,255,0.6);
                    margin-top: 12px;
                }}
                .header .stats {{
                    display: flex;
                    gap: 32px;
                    margin-top: 20px;
                    padding-top: 16px;
                    border-top: 1px solid rgba(255,255,255,0.2);
                }}
                .header .stat-item {{
                    text-align: left;
                }}
                .header .stat-value {{
                    font-family: Georgia, serif;
                    font-size: 28px;
                    font-weight: 400;
                    color: #FDB813;
                }}
                .header .stat-label {{
                    font-family: Arial, Helvetica, sans-serif;
                    font-size: 10px;
                    color: rgba(255,255,255,0.7);
                    text-transform: uppercase;
                    letter-spacing: 1px;
                    margin-top: 2px;
                }}

                /* 区块标题 */
                .section-header {{
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    margin-bottom: 20px;
                    padding-bottom: 12px;
                    border-bottom: 2px solid #00205B;
                }}
                .section-badge {{
                    background: #00205B;
                    color: white;
                    font-family: Arial, Helvetica, sans-serif;
                    font-size: 10px;
                    font-weight: 700;
                    padding: 4px 10px;
                    letter-spacing: 1px;
                    text-transform: uppercase;
                }}
                .section-title {{
                    font-family: Georgia, serif;
                    font-size: 18px;
                    font-weight: 400;
                    color: #00205B;
                }}

                /* AI 分析区域 */
                .ai-section {{
                    padding: 32px 40px;
                    background: #ffffff;
                    border-bottom: 1px solid #e0e0e0;
                }}

                /* 今日聚焦 */
                .insight-card {{
                    background: #f8f8f8;
                    border-left: 3px solid #00205B;
                    padding: 20px 24px;
                    margin-bottom: 20px;
                }}
                .insight-card .label {{
                    font-family: Arial, Helvetica, sans-serif;
                    font-size: 11px;
                    font-weight: 700;
                    color: #00205B;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                    margin-bottom: 12px;
                }}
                .insight-list {{
                    list-style: none;
                    padding: 0;
                    margin: 0;
                }}
                .insight-list li {{
                    position: relative;
                    padding: 8px 0 8px 20px;
                    font-family: Georgia, serif;
                    font-size: 14px;
                    color: #333333;
                    line-height: 1.5;
                    border-bottom: 1px solid #e8e8e8;
                }}
                .insight-list li:last-child {{
                    border-bottom: none;
                }}
                .insight-list li::before {{
                    content: "—";
                    position: absolute;
                    left: 0;
                    color: #00205B;
                    font-weight: bold;
                }}

                /* 新闻列表区域 */
                .news-section {{
                    padding: 32px 40px;
                }}
                .news-section-title {{
                    font-family: Georgia, serif;
                    font-size: 18px;
                    font-weight: 400;
                    color: #00205B;
                    margin-bottom: 20px;
                    padding-bottom: 12px;
                    border-bottom: 2px solid #00205B;
                }}

                /* 页脚 */
                .footer {{
                    background: #00205B;
                    padding: 20px 40px;
                    text-align: center;
                }}
                .footer-text {{
                    font-family: Arial, Helvetica, sans-serif;
                    color: rgba(255,255,255,0.7);
                    font-size: 11px;
                    letter-spacing: 0.5px;
                }}

                /* 开篇评论 */
                .commentary-section {{
                    padding: 28px 40px;
                    background: #f8f8f8;
                    border-bottom: 1px solid #e0e0e0;
                }}
                .commentary-content {{
                    font-family: Georgia, serif;
                    font-size: 14px;
                    line-height: 1.7;
                    color: #333333;
                    padding: 16px 20px;
                    background: #ffffff;
                    border-left: 3px solid #FDB813;
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
                <!-- 头部 - McKinsey 风格 -->
                <div class="header">
                    <h1>AI DAILY BRIEFING</h1>
                    <div class="subtitle">Generative AI & Agent Technology Intelligence</div>
                    <div class="date-line">{beijing_now.strftime('%Y年%m月%d日')} · 北京时间</div>
                    <div class="stats">
                        <div class="stat-item">
                            <div class="stat-value">{len(items)}</div>
                            <div class="stat-label">Today's News</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value">{len([i for i in items if i.get('ai_score', 0) >= 7])}</div>
                            <div class="stat-label">Key Highlights</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value">{len(set(i.get('source', '') for i in items))}</div>
                            <div class="stat-label">Sources</div>
                        </div>
                    </div>
                </div>
        """

        # 开篇评论区域（最先显示）
        if ai_analysis and ai_analysis.get('commentary'):
            html += f"""
                <div id="commentary" class="commentary-section">
                    <div class="section-header">
                        <span class="section-badge">EXECUTIVE SUMMARY</span>
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
                        <span class="section-badge">KEY INSIGHTS</span>
                        <span class="section-title">今日聚焦</span>
                    </div>
            """

            # Bullet Points 总结
            if ai_analysis.get('summary'):
                summary_lines = [line.strip() for line in ai_analysis['summary'].split('\n') if line.strip()]
                html += """
                    <div class="insight-card">
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
                <div id="actions" style="padding: 28px 40px; background: #f8f8f8; border-bottom: 1px solid #e0e0e0;">
                    <div class="section-header">
                        <span class="section-badge">ACTION ITEMS</span>
                        <span class="section-title">行动建议</span>
                    </div>
            """
            priority_colors = {
                'high': '#00205B',
                'medium': '#FDB813',
                'low': '#666666'
            }
            for idx, action in enumerate(ai_analysis['action_items'][:5], 1):
                title = action.get('title', '')
                reason = action.get('reason', '')
                action_text = action.get('action', '')
                priority = action.get('priority', 'medium')
                priority_color = priority_colors.get(priority, '#666666')

                html += f"""
                        <div style="background: #ffffff; padding: 16px 20px; margin-bottom: 12px; border-left: 3px solid {priority_color};">
                            <div style="display: flex; align-items: baseline; gap: 12px; margin-bottom: 8px;">
                                <span style="font-family: Georgia, serif; font-size: 18px; color: #00205B; font-weight: 400;">{idx}.</span>
                                <span style="font-family: Arial, sans-serif; font-size: 14px; font-weight: 700; color: #333333;">{title}</span>
                            </div>
                            <div style="font-family: Georgia, serif; font-size: 13px; color: #666666; margin-bottom: 8px; padding-left: 28px;">{reason}</div>
                            <div style="font-family: Arial, sans-serif; font-size: 12px; color: #00205B; padding: 8px 12px; background: #f0f4f8; margin-left: 28px;">
                                <strong>Next Step:</strong> {action_text}
                            </div>
                        </div>
                """
            html += "</div>"

        # 论文精选区域
        if ai_analysis and ai_analysis.get('paper_analysis'):
            html += """
                <div id="papers" style="padding: 28px 40px; background: #ffffff; border-bottom: 1px solid #e0e0e0;">
                    <div class="section-header">
                        <span class="section-badge">RESEARCH</span>
                        <span class="section-title">论文精选</span>
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

                html += f"""
                    <div style="padding: 16px 0; border-bottom: 1px solid #e8e8e8;">
                        <div style="display: flex; gap: 8px; margin-bottom: 8px;">
                            <span style="font-family: Arial, sans-serif; background: #00205B; color: white; padding: 2px 8px; font-size: 10px; text-transform: uppercase;">{domain}</span>
                            <span style="font-family: Arial, sans-serif; background: #f0f0f0; color: #666666; padding: 2px 8px; font-size: 10px;">{difficulty}</span>
                        </div>
                        <div style="font-family: Georgia, serif; font-size: 14px; color: #00205B; margin-bottom: 6px;">
                            <a href="{link}" target="_blank" style="color: #00205B; text-decoration: none;">{title_zh or title}</a>
                        </div>
                        <div style="font-family: Georgia, serif; font-size: 13px; color: #666666; margin-bottom: 8px;">{contribution}</div>
                        <div style="font-family: Arial, sans-serif; font-size: 11px; color: #333333; padding: 8px 12px; background: #f8f8f8; border-left: 2px solid #FDB813;">
                            <strong>Takeaway:</strong> {takeaway}
                        </div>
                    </div>
                """
            html += "</div>"

        # 提取 GitHub Trending 和 Product Hunt 用于独立展示
        github_items = [item for item in items if item.get('source') == 'GitHub Trending']
        ph_items = [item for item in items if item.get('source') == 'Product Hunt']

        # 开源热门区域 - GitHub Trending
        if github_items:
            html += """
                <div id="github" style="padding: 28px 40px; background: #ffffff; border-bottom: 1px solid #e0e0e0;">
                    <div class="section-header">
                        <span class="section-badge">OPEN SOURCE</span>
                        <span class="section-title">GitHub Trending</span>
                    </div>
            """
            for item in github_items:
                title = item.get('title', '')
                title_zh = item.get('title_zh', '')
                link = item.get('link', '#')
                summary = item.get('summary', '')
                summary_zh = item.get('summary_zh', '')
                pub_date = format_date(item.get('published', ''))
                freshness = get_freshness_badge(item.get('published', ''))
                is_agent = item.get('is_agent_related', False)
                agent_html = '<span style="background: #00205B; color: white; padding: 2px 6px; font-size: 9px; font-weight: 700; margin-right: 6px;">AGENT</span>' if is_agent else ''

                html += f"""
                        <div style="padding: 14px 0; border-bottom: 1px solid #e8e8e8;">
                            <div style="margin-bottom: 6px;">
                                {freshness}{agent_html}
                                <a href="{link}" target="_blank" style="font-family: Georgia, serif; color: #00205B; text-decoration: none; font-size: 14px;">{title}</a>
                            </div>
                            {f'<div style="font-family: Arial, sans-serif; font-size: 12px; color: #666666; margin-bottom: 6px; padding-left: 12px; border-left: 2px solid #e0e0e0;">{title_zh}</div>' if title_zh else ''}
                            <div style="font-family: Georgia, serif; font-size: 12px; color: #666666; line-height: 1.5;">{summary}</div>
                            {f'<div style="font-family: Arial, sans-serif; font-size: 11px; color: #888888; margin-top: 4px;">{summary_zh}</div>' if summary_zh else ''}
                            <div style="font-family: Arial, sans-serif; font-size: 10px; color: #999999; margin-top: 6px;">{pub_date}</div>
                        </div>
                """
            html += "</div>"

        # 产品发现区域 - Product Hunt
        if ph_items:
            html += """
                <div id="producthunt" style="padding: 28px 40px; background: #f8f8f8; border-bottom: 1px solid #e0e0e0;">
                    <div class="section-header">
                        <span class="section-badge">PRODUCTS</span>
                        <span class="section-title">Product Hunt</span>
                    </div>
            """
            for item in ph_items:
                title = item.get('title', '')
                title_zh = item.get('title_zh', '')
                link = item.get('link', '#')
                summary = item.get('summary', '')
                summary_zh = item.get('summary_zh', '')
                pub_date = format_date(item.get('published', ''))
                is_agent = item.get('is_agent_related', False)
                agent_html = '<span style="background: #00205B; color: white; padding: 2px 6px; font-size: 9px; font-weight: 700; margin-right: 6px;">AGENT</span>' if is_agent else ''

                html += f"""
                        <div style="padding: 14px 0; border-bottom: 1px solid #e0e0e0;">
                            <div style="margin-bottom: 6px;">
                                {agent_html}
                                <a href="{link}" target="_blank" style="font-family: Georgia, serif; color: #00205B; text-decoration: none; font-size: 14px;">{title}</a>
                            </div>
                            {f'<div style="font-family: Arial, sans-serif; font-size: 12px; color: #666666; margin-bottom: 6px; padding-left: 12px; border-left: 2px solid #e0e0e0;">{title_zh}</div>' if title_zh else ''}
                            <div style="font-family: Georgia, serif; font-size: 12px; color: #666666; line-height: 1.5;">{summary}</div>
                            {f'<div style="font-family: Arial, sans-serif; font-size: 11px; color: #888888; margin-top: 4px;">{summary_zh}</div>' if summary_zh else ''}
                            <div style="font-family: Arial, sans-serif; font-size: 10px; color: #999999; margin-top: 6px;">{pub_date}</div>
                        </div>
                """
            html += "</div>"

        # 完整新闻 - 按具体来源分组（排除 GitHub Trending 和 Product Hunt）
        html += """
            <div id="newslist" class="news-section">
                <div class="section-header">
                    <span class="section-badge">NEWS BY SOURCE</span>
                    <span class="section-title">完整新闻列表</span>
                </div>
        """

        # 按具体来源分组（排除已单独展示的）
        excluded_sources = {'GitHub Trending', 'Product Hunt'}
        grouped_by_source = defaultdict(list)
        for item in items:
            source = item.get('source', '未知来源')
            if source not in excluded_sources:
                grouped_by_source[source].append(item)

        # 获取 TOP 新闻的 ID
        top_ids = set()
        if ai_analysis and ai_analysis.get('top_news'):
            for top_item in ai_analysis['top_news']:
                if 'id' in top_item:
                    top_ids.add(top_item['id'])

        # 来源排序：按新闻数量降序
        sorted_sources = sorted(grouped_by_source.keys(), key=lambda s: len(grouped_by_source[s]), reverse=True)

        for idx, source_name in enumerate(sorted_sources):
            source_items = grouped_by_source[source_name]

            # 分组内按评分排序
            source_items = sorted(source_items, key=lambda x: x.get('ai_score', 0), reverse=True)

            # 每个来源一个区块
            html += f"""
                <div style="margin-bottom: 24px;">
                    <div style="display: flex; align-items: center; justify-content: space-between; padding: 10px 0; border-bottom: 2px solid #00205B; margin-bottom: 12px;">
                        <span style="font-family: Arial, sans-serif; font-size: 12px; font-weight: 700; color: #00205B; text-transform: uppercase; letter-spacing: 1px;">{source_name}</span>
                        <span style="font-family: Arial, sans-serif; background: #00205B; color: white; padding: 2px 10px; font-size: 11px; font-weight: 600;">{len(source_items)}</span>
                    </div>
            """

            for item in source_items:
                is_top = item.get('id') in top_ids
                title = item.get('title', '')
                title_zh = item.get('title_zh', '')
                summary_zh = item.get('summary_zh', '')
                link = item.get('link', '#')
                pub_date = format_date(item.get('published', ''))
                freshness = get_freshness_badge(item.get('published', ''))

                # 标签 - McKinsey 风格
                badges = []
                # Freshness badge 放最前面
                if freshness:
                    badges.append(freshness)
                if is_top:
                    badges.append('<span style="background: #FDB813; color: #00205B; padding: 1px 6px; font-size: 9px; font-weight: 700; margin-right: 4px;">TOP</span>')
                if item.get('is_agent_related', False):
                    badges.append('<span style="background: #00205B; color: white; padding: 1px 6px; font-size: 9px; font-weight: 700; margin-right: 4px;">AGENT</span>')
                if item.get('is_corporate', False):
                    badges.append('<span style="background: #e0e0e0; color: #666666; padding: 1px 6px; font-size: 9px; font-weight: 600; margin-right: 4px;">企业</span>')
                if item.get('is_low_value', False):
                    badges.append('<span style="background: #e0e0e0; color: #666666; padding: 1px 6px; font-size: 9px; font-weight: 600; margin-right: 4px;">引用</span>')

                label = item.get('label', '')
                if label and label in NEWS_LABELS:
                    ls = NEWS_LABELS[label]
                    badges.append(f'<span style="background: {ls["bg"]}; color: {ls["color"]}; padding: 1px 6px; font-size: 9px; font-weight: 600; margin-right: 4px;">{label}</span>')

                badges_html = ''.join(badges)

                html += f"""
                    <div style="padding: 12px 0; border-bottom: 1px solid #e8e8e8;">
                        <div style="margin-bottom: 6px;">
                            {badges_html}
                            <a href="{link}" target="_blank" style="font-family: Georgia, serif; color: #00205B; text-decoration: none; font-size: 13px;">{title}</a>
                        </div>
                        {f'<div style="font-family: Arial, sans-serif; font-size: 12px; color: #666666; margin-bottom: 4px; padding-left: 12px; border-left: 2px solid #e0e0e0;">{title_zh}</div>' if title_zh else ''}
                        {f'<div style="font-family: Georgia, serif; font-size: 11px; color: #888888; margin-top: 4px;">{summary_zh[:100]}...</div>' if summary_zh else ''}
                        <div style="font-family: Arial, sans-serif; font-size: 10px; color: #999999; margin-top: 6px;">{pub_date}</div>
                    </div>
                """

            html += "</div>"

        html += "</div></div>"

        # 页脚 - McKinsey 风格
        source_count = len(grouped_by_source)
        html += f"""
                <div class="footer">
                    <div class="footer-text">
                        {source_count} Sources · {len(items)} Articles · AI Daily Briefing
                    </div>
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
