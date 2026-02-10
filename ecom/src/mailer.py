"""邮件发送模块 - 优化版"""
import smtplib
import re
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
]


def get_beijing_time():
    """获取北京时间"""
    return datetime.now(BEIJING_TZ)


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


class Mailer:
    def __init__(self, config):
        self.smtp_server = config['smtp_server']
        self.smtp_port = config['smtp_port']
        self.username = config['username']
        self.password = config['password']
        # 解析收件人列表 (支持逗号分隔)
        to_raw = config['to']
        if isinstance(to_raw, list):
            self.to_emails = [e.strip() for e in to_raw]
        else:
            self.to_emails = [e.strip() for e in to_raw.split(',')]

    def send(self, subject, content):
        """发送邮件"""
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

            print(f"邮件发送成功: {subject}")
            return True

        except Exception as e:
            print(f"邮件发送失败: {e}")
            return False

    def format_news_email(self, items, ai_analysis=None):
        """格式化新闻邮件内容 - 现代化设计"""
        if not items:
            return None, None

        # 获取北京时间
        beijing_now = get_beijing_time()

        # 邮件主题
        ai_tag = " [AI]" if ai_analysis else ""
        subject = f"电商日报{ai_tag} - {len(items)} 条新内容 ({beijing_now.strftime('%Y-%m-%d %H:%M')})"

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
                    font-size: 15px;
                    color: rgba(255,255,255,0.8);
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
            </style>
        </head>
        <body>
            <div class="container">
                <!-- 头部 -->
                <div class="header">
                    <div class="header-content">
                        <h1>电商日报</h1>
                        <div class="subtitle">{beijing_now.strftime('%Y年%m月%d日 %H:%M')} 北京时间</div>
                        <div class="stats">
                            <div class="stat-item">
                                <div class="stat-value">{len(items)}</div>
                                <div class="stat-label">新内容</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-value">{len([c for c in CONTENT_CATEGORIES if any(i.get('category') == c['name'] for i in items)])}</div>
                                <div class="stat-label">内容类型</div>
                            </div>
                        </div>
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

            # 关键趋势
            if ai_analysis.get('trends'):
                html += """
                    <div class="trends-container">
                        <span class="trends-label">关键趋势</span>
                        <div class="trends-list">
                """
                for trend in ai_analysis['trends']:
                    html += f'<span class="trend-tag">{trend}</span>'
                html += """
                        </div>
                    </div>
                """

            # TOP 新闻
            if ai_analysis.get('top_news'):
                html += """
                    <div class="top-news">
                        <span class="top-news-label">TOP 新闻推荐</span>
                """
                for idx, top_item in enumerate(ai_analysis['top_news'][:5], 1):
                    score = top_item.get('ai_score', top_item.get('score', 'N/A'))
                    reason = top_item.get('ai_reason', top_item.get('reason', ''))
                    title = top_item.get('title', '')
                    title_zh = top_item.get('title_zh', '')
                    link = top_item.get('link', '#')
                    source = top_item.get('source', '未知来源')

                    html += f"""
                        <div class="top-item">
                            <div class="top-rank">{idx}</div>
                            <div class="top-content">
                                <a href="{link}" target="_blank" class="top-title">{title}</a>
                                <div class="top-meta">
                                    <span class="source-pill">{source}</span>
                                </div>
                                {f'<div class="translation">{title_zh}</div>' if title_zh else ''}
                                {f'<div class="top-reason">{reason}</div>' if reason else ''}
                            </div>
                        </div>
                    """
                html += "</div>"

            html += "</div>"

        # 完整新闻 - 按内容类型分组
        html += """
            <div class="news-section">
                <h2 class="news-section-title">完整新闻列表</h2>
        """

        # 按内容类型分组
        grouped_by_category = defaultdict(list)
        for item in items:
            category = item.get('category', '行业动态')
            grouped_by_category[category].append(item)

        # 获取 TOP 新闻的 ID
        top_ids = set()
        if ai_analysis and ai_analysis.get('top_news'):
            for top_item in ai_analysis['top_news']:
                if 'id' in top_item:
                    top_ids.add(top_item['id'])

        # 按类型优先级顺序显示新闻
        for cat_info in CONTENT_CATEGORIES:
            cat_name = cat_info["name"]
            cat_items = grouped_by_category.get(cat_name, [])

            if not cat_items:
                continue

            # 类型内按评分排序
            cat_items = sorted(cat_items, key=lambda x: x.get('ai_score', 0), reverse=True)

            html += f"""
                <div class="category-group">
                    <div class="category-header" style="background: {cat_info['bg']};">
                        <div class="category-left">
                            <span class="category-icon" style="background: {cat_info['color']};">{cat_info['icon']}</span>
                            <div>
                                <div class="category-name" style="color: {cat_info['color']};">{cat_name}</div>
                                <div class="category-desc">{cat_info['description']}</div>
                            </div>
                        </div>
                        <span class="category-count" style="color: {cat_info['color']};">{len(cat_items)} 条</span>
                    </div>
            """

            for item in cat_items:
                is_top = item.get('id') in top_ids
                card_class = "news-card is-top" if is_top else "news-card"

                # 构建 meta badges
                meta_html = ""
                if is_top:
                    meta_html += '<span class="meta-badge top">TOP</span>'
                source = item.get('source', '')
                if source:
                    meta_html += f'<span class="meta-badge source">{source}</span>'

                # 获取翻译
                title_zh = item.get('title_zh', '')
                summary_zh = item.get('summary_zh', '')
                summary_text = item['summary'][:250]

                # 检查摘要和翻译是否相同
                summary_same = summary_zh and summary_text.replace(' ', '')[:100] == summary_zh.replace(' ', '')[:100]

                # 格式化日期
                pub_date = format_date(item.get('published', ''))

                html += f"""
                    <div class="{card_class}">
                        <div class="news-title">
                            <a href="{item['link']}" target="_blank">{item['title']}</a>
                        </div>
                        {f'<div class="translation">{title_zh}</div>' if title_zh else ''}
                        <div class="news-meta">
                            {meta_html}
                            <span class="meta-date">{pub_date}</span>
                        </div>
                        <div class="news-summary">{summary_text}...</div>
                        {f'<div class="news-translation">{summary_zh[:200]}...</div>' if summary_zh and not summary_same else ''}
                    </div>
                """

            html += "</div>"

        html += "</div>"

        # 页脚
        category_count = len([cat for cat in CONTENT_CATEGORIES if grouped_by_category.get(cat["name"])])
        html += f"""
                <div class="footer">
                    <p class="footer-text">
                        共 {category_count} 个类型 · {len(items)} 条新闻
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

        return subject, html
