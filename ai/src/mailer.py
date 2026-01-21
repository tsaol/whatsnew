"""邮件发送模块"""
import smtplib
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from collections import defaultdict
from dateutil import parser as date_parser


# 内容分类定义（按优先级排序）
CONTENT_CATEGORIES = [
    {"name": "Agent 专项", "icon": "A", "description": "Agent 框架、MCP、Multi-Agent、Tool Use", "color": "#667eea"},
    {"name": "技术深度", "icon": "T", "description": "LLM、RAG、模型优化、算法创新", "color": "#3498db"},
    {"name": "AWS 聚焦", "icon": "W", "description": "Bedrock、SageMaker、AWS AI 服务", "color": "#ff9500"},
    {"name": "行业动态", "icon": "I", "description": "企业落地、应用案例、市场趋势", "color": "#27ae60"},
]


def format_date(date_str):
    """统一格式化日期显示"""
    if not date_str:
        return ""

    try:
        # 尝试解析各种日期格式
        dt = date_parser.parse(date_str)
        # 统一输出格式：2026-01-20
        return dt.strftime('%Y-%m-%d')
    except:
        # 如果解析失败，尝试提取日期部分
        # 匹配常见日期格式
        patterns = [
            r'(\d{4}-\d{2}-\d{2})',  # 2026-01-20
            r'(\d{2}/\d{2}/\d{4})',  # 01/20/2026
            r'(\w{3}\s+\d{1,2},?\s+\d{4})',  # Jan 20, 2026
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
        self.to_email = config['to']

    def send(self, subject, content):
        """发送邮件"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.username
            msg['To'] = self.to_email
            msg['Subject'] = subject

            msg.attach(MIMEText(content, 'html', 'utf-8'))

            # 连接SMTP服务器（126邮箱使用SSL）
            server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            server.login(self.username, self.password)
            server.send_message(msg)
            server.quit()

            print(f"邮件发送成功: {subject}")
            return True

        except Exception as e:
            print(f"邮件发送失败: {e}")
            return False

    def format_news_email(self, items, ai_analysis=None):
        """格式化新闻邮件内容 - 全新设计"""
        if not items:
            return None, None

        # 邮件主题
        ai_tag = " [AI]" if ai_analysis else ""
        subject = f"WhatsNew{ai_tag} - {len(items)} 条新内容 ({datetime.now().strftime('%Y-%m-%d %H:%M')})"

        # 统一样式设计
        html = f"""
        <html>
        <head>
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    background: #f5f7fa;
                    padding: 20px;
                }}
                .container {{
                    max-width: 800px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 12px;
                    overflow: hidden;
                    box-shadow: 0 2px 12px rgba(0,0,0,0.08);
                }}

                /* 统一卡片样式 */
                .card {{
                    background: white;
                    border-radius: 8px;
                    padding: 20px;
                    margin-bottom: 16px;
                    border: 1px solid #e1e8ed;
                    transition: all 0.2s;
                }}
                .card:hover {{
                    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                    transform: translateY(-2px);
                }}

                /* 头部 */
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                }}
                .header h1 {{
                    font-size: 1.8em;
                    margin-bottom: 10px;
                }}
                .header .meta {{
                    opacity: 0.9;
                    font-size: 0.9em;
                }}

                /* AI 分析区域 */
                .ai-section {{
                    padding: 30px;
                    background: #f8f9ff;
                }}
                .section-title {{
                    font-size: 1.3em;
                    color: #667eea;
                    margin-bottom: 20px;
                    display: flex;
                    align-items: center;
                }}
                .section-title:before {{
                    content: "[AI]";
                    margin-right: 10px;
                    font-size: 1.2em;
                }}

                .ai-insight {{
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    border-left: 4px solid #667eea;
                    margin-bottom: 20px;
                    font-size: 1.05em;
                    line-height: 1.8;
                }}

                /* 趋势标签 */
                .trends {{
                    margin: 20px 0;
                }}
                .trends .label {{
                    font-weight: 600;
                    color: #667eea;
                    margin-bottom: 10px;
                    display: block;
                }}
                .trend-tag {{
                    display: inline-block;
                    background: #667eea;
                    color: white;
                    padding: 6px 14px;
                    border-radius: 20px;
                    margin: 4px 6px 4px 0;
                    font-size: 0.85em;
                }}

                /* TOP 新闻 - 可点击卡片 */
                .top-news {{
                    margin-top: 24px;
                }}
                .top-news-item {{
                    background: white;
                    padding: 16px;
                    border-radius: 8px;
                    margin-bottom: 12px;
                    border: 1px solid #e1e8ed;
                    transition: all 0.2s;
                }}
                .top-news-item:hover {{
                    border-color: #667eea;
                    box-shadow: 0 2px 8px rgba(102,126,234,0.15);
                }}
                .top-news-item .rank {{
                    display: inline-block;
                    background: #ffd700;
                    color: #333;
                    font-weight: bold;
                    padding: 4px 10px;
                    border-radius: 4px;
                    margin-right: 10px;
                    font-size: 0.9em;
                }}
                .top-news-item .source-badge {{
                    display: inline-block;
                    background: #f0f0f0;
                    color: #666;
                    padding: 2px 8px;
                    border-radius: 3px;
                    font-size: 0.75em;
                    margin-left: 8px;
                }}
                .top-news-item a {{
                    color: #2c3e50;
                    text-decoration: none;
                    font-weight: 600;
                    font-size: 1.05em;
                }}
                .top-news-item a:hover {{
                    color: #667eea;
                }}
                .top-news-item .reason {{
                    color: #666;
                    font-size: 0.9em;
                    margin-top: 8px;
                    padding-left: 45px;
                }}

                /* 翻译样式 */
                .translation {{
                    color: #666;
                    font-size: 0.95em;
                    margin-top: 6px;
                    padding-left: 4px;
                    border-left: 3px solid #e1e8ed;
                    padding-left: 12px;
                    font-style: italic;
                }}
                .top-news-item .translation {{
                    padding-left: 45px;
                    border-left: none;
                    font-style: italic;
                }}

                /* 完整新闻 - 按内容类型分组 */
                .news-section {{
                    padding: 30px;
                }}
                .category-group {{
                    margin-bottom: 32px;
                }}
                .category-header {{
                    font-size: 1.2em;
                    color: #2c3e50;
                    margin-bottom: 16px;
                    padding-bottom: 8px;
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                }}
                .category-icon {{
                    display: inline-block;
                    width: 28px;
                    height: 28px;
                    line-height: 28px;
                    text-align: center;
                    border-radius: 6px;
                    color: white;
                    font-weight: bold;
                    margin-right: 10px;
                }}
                .category-header .count {{
                    font-size: 0.85em;
                    color: #999;
                    font-weight: normal;
                }}
                .category-desc {{
                    font-size: 0.85em;
                    color: #666;
                    margin-left: 38px;
                    margin-bottom: 12px;
                }}

                /* 新闻卡片 */
                .news-card {{
                    background: white;
                    padding: 18px;
                    border-radius: 8px;
                    margin-bottom: 12px;
                    border: 1px solid #e1e8ed;
                    transition: all 0.2s;
                }}
                .news-card:hover {{
                    border-color: #667eea;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                }}
                .news-card.top-item {{
                    border-left: 4px solid #ffd700;
                    background: #fffef8;
                }}
                .news-card .title {{
                    font-size: 1.1em;
                    font-weight: 600;
                    margin-bottom: 10px;
                }}
                .news-card .title a {{
                    color: #2c3e50;
                    text-decoration: none;
                }}
                .news-card .title a:hover {{
                    color: #667eea;
                }}
                .news-card .meta {{
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    margin-bottom: 10px;
                    font-size: 0.85em;
                    color: #999;
                }}
                .news-card .score-badge {{
                    background: #667eea;
                    color: white;
                    padding: 2px 8px;
                    border-radius: 3px;
                    font-weight: 600;
                }}
                .news-card .top-badge {{
                    background: #ffd700;
                    color: #333;
                    padding: 2px 8px;
                    border-radius: 3px;
                    font-weight: 600;
                }}
                .news-card .summary {{
                    color: #555;
                    line-height: 1.6;
                }}

                /* 页脚 */
                .footer {{
                    background: #f8f9fa;
                    padding: 20px;
                    text-align: center;
                    color: #999;
                    font-size: 0.85em;
                    border-top: 1px solid #e1e8ed;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <!-- 头部 -->
                <div class="header">
                    <h1>WhatsNew 每日资讯</h1>
                    <div class="meta">
                        {len(items)} 条新内容 | {datetime.now().strftime('%Y年%m月%d日 %H:%M')}
                    </div>
                </div>
        """

        # AI 分析区域
        if ai_analysis:
            html += """
                <div class="ai-section">
                    <div class="section-title">AI 智能分析</div>
            """

            # Bullet Points 总结
            if ai_analysis.get('summary'):
                # 处理总结，转换为列表格式
                summary_lines = [line.strip() for line in ai_analysis['summary'].split('\n') if line.strip()]
                summary_html = '<ul style="margin:10px 0; padding-left:20px; line-height:1.8;">'
                for line in summary_lines:
                    # 移除开头的 "- " 如果有的话
                    clean_line = line.lstrip('- ').strip()
                    if clean_line:
                        summary_html += f'<li style="margin:5px 0;">{clean_line}</li>'
                summary_html += '</ul>'

                html += f"""
                    <div class="ai-insight">
                        <strong>今日聚焦</strong>
                        {summary_html}
                    </div>
                """

            # 关键趋势
            if ai_analysis.get('trends'):
                html += """
                    <div class="trends">
                        <span class="label">关键趋势</span>
                """
                for trend in ai_analysis['trends']:
                    html += f'<span class="trend-tag">{trend}</span>'
                html += "</div>"

            # TOP 新闻 - 可点击，显示来源
            if ai_analysis.get('top_news'):
                html += """
                    <div class="top-news">
                        <span class="label" style="display:block; font-weight:600; color:#667eea; margin-bottom:12px;">TOP 新闻推荐</span>
                """
                for idx, top_item in enumerate(ai_analysis['top_news'][:5], 1):
                    score = top_item.get('ai_score', top_item.get('score', 'N/A'))
                    reason = top_item.get('ai_reason', top_item.get('reason', ''))
                    title = top_item.get('title', '')
                    title_zh = top_item.get('title_zh', '')
                    link = top_item.get('link', '#')
                    source = top_item.get('source', '未知来源')

                    html += f"""
                        <div class="top-news-item">
                            <span class="rank">#{idx} {score}分</span>
                            <a href="{link}" target="_blank">{title}</a>
                            <span class="source-badge">{source}</span>
                            {f'<div class="translation">{title_zh}</div>' if title_zh else ''}
                            {f'<div class="reason" style="margin-top:8px; padding-top:6px; border-top:1px solid #f0f0f0;">{reason}</div>' if reason else ''}
                        </div>
                    """
                html += "</div>"

            html += "</div>"

        # 完整新闻 - 按内容类型分组
        html += '<div class="news-section">'
        html += '<h2 style="margin-bottom:24px; color:#2c3e50;">完整新闻列表</h2>'

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
                    <div class="category-header" style="border-bottom: 2px solid {cat_info['color']};">
                        <span>
                            <span class="category-icon" style="background: {cat_info['color']};">{cat_info['icon']}</span>
                            {cat_name}
                        </span>
                        <span class="count">{len(cat_items)} 条</span>
                    </div>
                    <div class="category-desc">{cat_info['description']}</div>
            """

            for item in cat_items:
                is_top = item.get('id') in top_ids
                card_class = "news-card top-item" if is_top else "news-card"

                meta_badges = []
                if item.get('ai_score'):
                    meta_badges.append(f'<span class="score-badge">AI评分 {item["ai_score"]}</span>')
                if is_top:
                    meta_badges.append('<span class="top-badge">TOP</span>')
                # 添加来源标签
                source = item.get('source', '')
                if source:
                    meta_badges.append(f'<span style="background:#f0f0f0; color:#666; padding:2px 8px; border-radius:3px; font-size:0.85em;">{source}</span>')

                meta_html = ''.join(meta_badges) if meta_badges else ''

                # 获取翻译
                title_zh = item.get('title_zh', '')
                summary_zh = item.get('summary_zh', '')
                summary_text = item['summary'][:250]

                # 检查摘要和翻译是否相同（避免重复显示）
                summary_same = summary_zh and summary_text.replace(' ', '')[:100] == summary_zh.replace(' ', '')[:100]

                # 格式化日期
                pub_date = format_date(item.get('published', ''))

                html += f"""
                    <div class="{card_class}">
                        <div class="title">
                            <a href="{item['link']}" target="_blank">{item['title']}</a>
                        </div>
                        {f'<div class="translation">{title_zh}</div>' if title_zh else ''}
                        <div class="meta">
                            {meta_html}
                            <span>{pub_date}</span>
                        </div>
                        <div class="summary">{summary_text}...</div>
                        {f'<div class="translation">{summary_zh[:200]}...</div>' if summary_zh and not summary_same else ''}
                    </div>
                """

            html += "</div>"

        html += "</div>"

        # 页脚 - 统计类型数量
        category_count = len([cat for cat in CONTENT_CATEGORIES if grouped_by_category.get(cat["name"])])
        html += f"""
                <div class="footer">
                    <p>本邮件由 WhatsNew 自动生成</p>
                    {'<p>AI 分析由 AWS Bedrock Claude Sonnet 4.5 提供</p>' if ai_analysis else ''}
                    <p style="margin-top:8px; font-size:0.9em;">
                        共 {category_count} 个类型 · {len(items)} 条新闻
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

        return subject, html
