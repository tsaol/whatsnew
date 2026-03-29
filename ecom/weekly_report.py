"""电商+AI 周报生成脚本
每周六北京时间 9:00 发送
"""
import sys
import json
import boto3
from pathlib import Path
from datetime import datetime, timedelta, timezone
from collections import Counter, defaultdict

from src.config import Config
from src.storage import Storage

# 北京时区
BEIJING_TZ = timezone(timedelta(hours=8))


def get_week_news_from_s3(days=7, bucket='cls-whatsnew', prefix='ecom'):
    """从 S3 日报归档获取一周新闻（包含完整元数据）"""
    s3 = boto3.client('s3')
    all_items = []
    now = datetime.now(BEIJING_TZ)

    for i in range(days):
        date = (now - timedelta(days=i)).strftime('%Y-%m-%d')
        key = f'{prefix}/{date}.json'

        try:
            obj = s3.get_object(Bucket=bucket, Key=key)
            data = json.loads(obj['Body'].read().decode('utf-8'))
            items = data.get('items', [])

            for item in items:
                item['report_date'] = date

            all_items.extend(items)
            print(f"[S3] 加载 {date}: {len(items)} 条")

        except s3.exceptions.NoSuchKey:
            print(f"[S3] {date} 无数据")
        except Exception as e:
            print(f"[S3] 加载 {date} 失败: {e}")

    return all_items


class WeeklyAnalyzer:
    """电商+AI 周报分析器"""

    def __init__(self, aws_region='us-west-2'):
        from langchain_aws import ChatBedrock
        import boto3
        from botocore.config import Config as BotoConfig

        bedrock_config = BotoConfig(
            read_timeout=300,
            connect_timeout=60,
            retries={'max_attempts': 2}
        )

        bedrock_client = boto3.client(
            'bedrock-runtime',
            region_name=aws_region,
            config=bedrock_config
        )

        self.llm = ChatBedrock(
            model_id="us.anthropic.claude-opus-4-6-v1",
            region_name=aws_region,
            client=bedrock_client,
            model_kwargs={
                "temperature": 0.5,
                "max_tokens": 8192
            }
        )

    def analyze_week(self, news_items: list, stats: dict) -> dict:
        """生成电商+AI 周度分析"""

        news_summary = "\n".join([
            f"- [{item.get('source', '未知')}] {item.get('title', '')}"
            for item in news_items[:100]
        ])

        by_source = defaultdict(list)
        for item in news_items:
            source = item.get('source', '未知')
            by_source[source].append(item.get('title', ''))

        source_summary = ""
        for source, titles in sorted(by_source.items(), key=lambda x: -len(x[1]))[:15]:
            source_summary += f"\n## {source} ({len(titles)}条)\n"
            for t in titles[:5]:
                source_summary += f"- {t}\n"

        prompt = f"""你是一位资深电商行业分析师，专注于 AI 技术在电商领域的应用。请基于本周的电商+AI 新闻数据生成一份专业的周报分析。

## 本周数据概览
- 新闻总数: {stats['total']}
- 涉及来源: {stats['source_count']} 个
- 时间范围: {stats['date_range']}

## 按来源分布
{source_summary}

## 本周新闻列表
{news_summary}

---

请生成以下内容（使用中文，专业但易读）:

### 1. 本周概要 (executive_summary)
用 2-3 句话概括本周电商+AI 领域最重要的动态，突出关键主题和趋势。重点关注：AI 如何改变电商（搜索、推荐、客服、供应链、定价等）。

### 2. 热点趋势 (trends)
识别本周 3-5 个主要趋势或热点话题，每个用 1-2 句话说明：
- 趋势名称
- 具体表现
- 对电商从业者的影响

### 3. 本周 TOP 10 (top_news)
从新闻中选出最重要的 10 条，说明选择理由。优先选择对电商业务有直接影响的新闻。格式：
1. [来源] 标题 - 重要性说明

### 4. 技术应用 (tech_applications)
本周值得关注的电商 AI 技术应用：
- AI 搜索/推荐
- AI 客服/营销
- AI 供应链/物流
- AI 内容生成/商品描述
- 新工具/平台发布

### 5. 平台动态 (platform_moves)
电商平台层面的重要动态：
- 亚马逊/Shopify/阿里巴巴等平台的 AI 功能更新
- 新兴电商平台/模式
- 政策/监管变化

### 6. 值得关注 (watchlist)
本周值得持续关注的 3-5 个项目/技术/公司，说明关注理由。

### 7. 下周展望 (outlook)
基于本周动态，预测下周可能的发展方向或值得期待的事件。

请以 JSON 格式返回，确保内容专业、有洞察力：
```json
{{
  "executive_summary": "...",
  "trends": [
    {{"name": "...", "description": "...", "impact": "..."}}
  ],
  "top_news": [
    {{"rank": 1, "source": "...", "title": "...", "reason": "..."}}
  ],
  "tech_applications": [
    {{"title": "...", "description": "..."}}
  ],
  "platform_moves": [
    {{"platform": "...", "action": "...", "significance": "..."}}
  ],
  "watchlist": [
    {{"name": "...", "type": "项目/技术/公司", "reason": "..."}}
  ],
  "outlook": "..."
}}
```"""

        import re

        def try_parse_json(text):
            """Try to parse JSON with repair attempts"""
            # Try direct parse
            try:
                return json.loads(text)
            except json.JSONDecodeError as e:
                print(f"[Weekly] JSON parse error at pos {e.pos}: {repr(text[max(0,e.pos-20):e.pos+20])}")

            # Fix unescaped quotes inside JSON string values
            # Match content between key-value quotes and escape inner quotes
            def fix_inner_quotes(t):
                result = []
                i = 0
                in_string = False
                escaped = False
                while i < len(t):
                    ch = t[i]
                    if escaped:
                        result.append(ch)
                        escaped = False
                    elif ch == '\\':
                        result.append(ch)
                        escaped = True
                    elif ch == '"':
                        if not in_string:
                            in_string = True
                            result.append(ch)
                        else:
                            # Check if this quote ends the string value
                            rest = t[i+1:].lstrip()
                            if rest and rest[0] in ':,}]\n':
                                in_string = False
                                result.append(ch)
                            elif rest == '':
                                in_string = False
                                result.append(ch)
                            else:
                                # Inner quote - escape it
                                result.append('\\"')
                    else:
                        result.append(ch)
                    i += 1
                return ''.join(result)

            repaired = fix_inner_quotes(text)
            # Also remove trailing commas
            repaired = re.sub(r',\s*([}\]])', r'\1', repaired)
            try:
                return json.loads(repaired)
            except json.JSONDecodeError:
                pass
            # Try to fix truncated JSON by closing open brackets
            balanced = repaired.rstrip()
            balanced = re.sub(r',\s*$', '', balanced)
            open_braces = balanced.count('{') - balanced.count('}')
            open_brackets = balanced.count('[') - balanced.count(']')
            balanced += ']' * open_brackets + '}' * open_braces
            try:
                return json.loads(balanced)
            except json.JSONDecodeError as e:
                raise e

        for attempt in range(2):
            try:
                response = self.llm.invoke(prompt)
                content = response.content

                json_match = re.search(r'```json\s*([\s\S]*?)\s*```', content)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    json_str = content

                analysis = try_parse_json(json_str)
                return analysis

            except Exception as e:
                print(f"[Weekly] AI 分析尝试 {attempt+1} 失败: {e}")
                if attempt == 0:
                    print("[Weekly] 重试中...")
                    continue
                return {
                    "executive_summary": "本周电商+AI 领域持续活跃，多个重要动态值得关注。",
                    "trends": [],
                    "top_news": [],
                    "tech_applications": [],
                    "platform_moves": [],
                    "watchlist": [],
                    "outlook": "期待下周更多精彩内容。"
                }


def format_weekly_email(news_items: list, analysis: dict, stats: dict) -> str:
    """生成电商+AI 周报 HTML 邮件"""

    now = datetime.now(BEIJING_TZ)
    week_start = now - timedelta(days=7)

    # 电商主题配色
    PRIMARY = "#1a1a2e"   # Deep navy
    ACCENT = "#e94560"    # Commerce red
    SECONDARY = "#0f3460" # Blue accent

    # Build title -> link mapping for clickable news
    title_link_map = {}
    for item in news_items:
        link = item.get('link', '')
        if link:
            title_link_map[item.get('title', '')] = link
            title_link_map[item.get('title_zh', '')] = link

    def make_link(title, link=''):
        if not link:
            link = title_link_map.get(title, '')
        if link:
            return f'<a href="{link}" style="color: #1e293b; text-decoration: none; border-bottom: 1px solid #cbd5e1;" target="_blank">{title}</a>'
        return title

    # 趋势 HTML
    trends_html = ""
    for i, trend in enumerate(analysis.get('trends', [])[:5], 1):
        trends_html += f"""
        <div style="margin-bottom: 16px; padding: 16px; background: #fff5f7; border-left: 4px solid {ACCENT}; border-radius: 4px;">
            <div style="font-weight: 600; color: {PRIMARY}; margin-bottom: 8px;">
                {i}. {trend.get('name', '')}
            </div>
            <div style="color: #475569; font-size: 14px; line-height: 1.6;">
                {trend.get('description', '')}
            </div>
            <div style="color: #64748b; font-size: 13px; margin-top: 8px;">
                <strong>对电商的影响:</strong> {trend.get('impact', '')}
            </div>
        </div>
        """

    # TOP 10 HTML
    top_news_html = ""
    for item in analysis.get('top_news', [])[:10]:
        title = item.get('title', '')
        top_news_html += f"""
        <tr>
            <td style="padding: 12px 16px; border-bottom: 1px solid #e2e8f0;">
                <div style="font-weight: 600; color: {ACCENT};">#{item.get('rank', '')}</div>
            </td>
            <td style="padding: 12px 16px; border-bottom: 1px solid #e2e8f0;">
                <div style="color: #64748b; font-size: 12px;">{item.get('source', '')}</div>
                <div style="color: #1e293b; font-size: 14px; margin-top: 4px;">{make_link(title)}</div>
                <div style="color: #64748b; font-size: 13px; margin-top: 4px;">{item.get('reason', '')}</div>
            </td>
        </tr>
        """

    # 技术应用 HTML
    tech_html = ""
    for app in analysis.get('tech_applications', [])[:5]:
        tech_html += f"""
        <div style="margin-bottom: 12px; padding: 12px; background: #f0f9ff; border-radius: 6px;">
            <div style="font-weight: 600; color: #0369a1;">{app.get('title', '')}</div>
            <div style="color: #475569; font-size: 14px; margin-top: 6px;">{app.get('description', '')}</div>
        </div>
        """

    # 平台动态 HTML
    platform_html = ""
    for move in analysis.get('platform_moves', [])[:5]:
        platform_html += f"""
        <div style="margin-bottom: 12px; padding: 12px; background: #fef3c7; border-radius: 6px;">
            <div style="font-weight: 600; color: #92400e;">{move.get('platform', '')}</div>
            <div style="color: #78350f; font-size: 14px; margin-top: 4px;">{move.get('action', '')}</div>
            <div style="color: #a16207; font-size: 13px; margin-top: 4px;">{move.get('significance', '')}</div>
        </div>
        """

    # 关注清单 HTML
    watchlist_html = ""
    for item in analysis.get('watchlist', [])[:5]:
        type_colors = {
            "项目": "#059669",
            "技术": "#7c3aed",
            "公司": "#dc2626"
        }
        item_type = item.get('type', '项目')
        color = type_colors.get(item_type, "#64748b")
        watchlist_html += f"""
        <div style="margin-bottom: 12px; padding: 12px; border: 1px solid #e2e8f0; border-radius: 6px;">
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="background: {color}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">{item_type}</span>
                <span style="font-weight: 600; color: {PRIMARY};">{item.get('name', '')}</span>
            </div>
            <div style="color: #475569; font-size: 14px; margin-top: 8px;">{item.get('reason', '')}</div>
        </div>
        """

    # 来源统计
    source_stats = stats.get('by_source', {})
    source_stats_html = ""
    for source, count in sorted(source_stats.items(), key=lambda x: -x[1])[:10]:
        percentage = int(count / stats['total'] * 100) if stats['total'] > 0 else 0
        source_stats_html += f"""
        <div style="display: flex; align-items: center; margin-bottom: 8px;">
            <div style="width: 120px; font-size: 13px; color: #475569; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{source}</div>
            <div style="flex: 1; height: 20px; background: #e2e8f0; border-radius: 4px; margin: 0 12px; overflow: hidden;">
                <div style="width: {percentage}%; height: 100%; background: {ACCENT};"></div>
            </div>
            <div style="width: 50px; font-size: 13px; color: #64748b; text-align: right;">{count}</div>
        </div>
        """

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ecom+AI Weekly Report</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f1f5f9; font-family: 'Microsoft YaHei', 'Segoe UI', Arial, sans-serif;">
    <div style="max-width: 800px; margin: 0 auto; background: white;">

        <!-- Header -->
        <div style="background: {PRIMARY}; color: white; padding: 40px 32px; text-align: center;">
            <div style="font-size: 14px; letter-spacing: 2px; opacity: 0.8; margin-bottom: 8px;">WEEKLY INTELLIGENCE REPORT</div>
            <div style="font-size: 32px; font-weight: bold; margin-bottom: 8px;">电商+AI 周报</div>
            <div style="font-size: 16px; opacity: 0.9;">
                {week_start.strftime('%Y.%m.%d')} - {now.strftime('%Y.%m.%d')}
            </div>
        </div>

        <!-- Stats Bar -->
        <div style="background: {ACCENT}; color: white; padding: 16px 32px; display: flex; justify-content: space-around; text-align: center;">
            <div>
                <div style="font-size: 28px; font-weight: bold;">{stats['total']}</div>
                <div style="font-size: 13px;">新闻总数</div>
            </div>
            <div>
                <div style="font-size: 28px; font-weight: bold;">{stats['source_count']}</div>
                <div style="font-size: 13px;">信息来源</div>
            </div>
            <div>
                <div style="font-size: 28px; font-weight: bold;">7</div>
                <div style="font-size: 13px;">覆盖天数</div>
            </div>
        </div>

        <!-- Executive Summary -->
        <div style="padding: 32px;">
            <div style="font-size: 20px; font-weight: bold; color: {PRIMARY}; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 3px solid {ACCENT};">
                EXECUTIVE SUMMARY | 本周概要
            </div>
            <div style="font-size: 16px; line-height: 1.8; color: #334155; background: #f8fafc; padding: 20px; border-radius: 8px;">
                {analysis.get('executive_summary', '')}
            </div>
        </div>

        <!-- Trends -->
        <div style="padding: 0 32px 32px;">
            <div style="font-size: 20px; font-weight: bold; color: {PRIMARY}; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 3px solid {ACCENT};">
                KEY TRENDS | 热点趋势
            </div>
            {trends_html}
        </div>

        <!-- TOP 10 -->
        <div style="padding: 0 32px 32px;">
            <div style="font-size: 20px; font-weight: bold; color: {PRIMARY}; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 3px solid {ACCENT};">
                TOP 10 | 本周必读
            </div>
            <table style="width: 100%; border-collapse: collapse;">
                {top_news_html}
            </table>
        </div>

        <!-- Two Column Layout -->
        <div style="padding: 0 32px 32px;">
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="width: 50%; vertical-align: top; padding-right: 16px;">
                        <div style="font-size: 18px; font-weight: bold; color: {PRIMARY}; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 2px solid #0ea5e9;">
                            TECH APPLICATIONS | 技术应用
                        </div>
                        {tech_html}
                    </td>
                    <td style="width: 50%; vertical-align: top; padding-left: 16px;">
                        <div style="font-size: 18px; font-weight: bold; color: {PRIMARY}; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 2px solid #f59e0b;">
                            PLATFORM MOVES | 平台动态
                        </div>
                        {platform_html}
                    </td>
                </tr>
            </table>
        </div>

        <!-- Watchlist -->
        <div style="padding: 0 32px 32px;">
            <div style="font-size: 20px; font-weight: bold; color: {PRIMARY}; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 3px solid {ACCENT};">
                WATCHLIST | 值得关注
            </div>
            {watchlist_html}
        </div>

        <!-- Outlook -->
        <div style="padding: 0 32px 32px;">
            <div style="font-size: 20px; font-weight: bold; color: {PRIMARY}; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 3px solid {ACCENT};">
                OUTLOOK | 下周展望
            </div>
            <div style="font-size: 15px; line-height: 1.8; color: #334155; background: linear-gradient(135deg, #fff5f7 0%, #fee2e2 100%); padding: 20px; border-radius: 8px; border-left: 4px solid {ACCENT};">
                {analysis.get('outlook', '')}
            </div>
        </div>

        <!-- Source Distribution -->
        <div style="padding: 0 32px 32px;">
            <div style="font-size: 20px; font-weight: bold; color: {PRIMARY}; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 3px solid {ACCENT};">
                DATA SOURCE | 来源分布
            </div>
            <div style="padding: 16px; background: #f8fafc; border-radius: 8px;">
                {source_stats_html}
            </div>
        </div>

        <!-- Full News List -->
        <div style="padding: 0 32px 32px;">
            <div style="font-size: 20px; font-weight: bold; color: {PRIMARY}; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 3px solid {ACCENT};">
                ALL NEWS | 本周全部新闻 ({stats['total']})
            </div>
            <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                {''.join(f"""<tr>
                    <td style="padding: 8px 12px; border-bottom: 1px solid #f1f5f9; color: #64748b; white-space: nowrap; width: 100px;">{item.get('source', '')}</td>
                    <td style="padding: 8px 12px; border-bottom: 1px solid #f1f5f9;">
                        {'<a href="' + item.get('link', '') + '" style="color: #334155; text-decoration: none; border-bottom: 1px solid #e2e8f0;" target="_blank">' + (item.get('title_zh') or item.get('title', '')) + '</a>' if item.get('link') else (item.get('title_zh') or item.get('title', ''))}
                    </td>
                </tr>""" for item in sorted(news_items, key=lambda x: x.get('report_date', ''), reverse=True))}
            </table>
        </div>

        <!-- Footer -->
        <div style="background: {PRIMARY}; color: white; padding: 24px 32px; text-align: center;">
            <div style="font-size: 14px; opacity: 0.9; margin-bottom: 8px;">
                Ecom+AI Weekly Report | 每周六发送
            </div>
            <div style="font-size: 12px; opacity: 0.7;">
                Powered by WhatsNew | Generated at {now.strftime('%Y-%m-%d %H:%M')} (Beijing Time)
            </div>
        </div>

    </div>
</body>
</html>
"""
    return html


def send_weekly_email(html_content: str, config: Config) -> bool:
    """发送周报邮件"""
    import requests

    email_config = config.get('email', {})
    if not email_config.get('enabled', False):
        print("[Weekly] 邮件发送已禁用")
        return False

    now = datetime.now(BEIJING_TZ)
    week_start = now - timedelta(days=7)
    subject = f"电商+AI 周报 | {week_start.strftime('%m.%d')}-{now.strftime('%m.%d')} Ecom Weekly Intelligence"

    api_key = email_config.get('resend_api_key')
    from_email = email_config.get('from_email', 'weekly@xcaoliu.com')
    to_emails = email_config.get('to', '').split(',')
    to_emails = [e.strip() for e in to_emails if e.strip()]

    if not api_key or not to_emails:
        print("[Weekly] 邮件配置不完整")
        return False

    try:
        response = requests.post(
            'https://api.resend.com/emails',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            },
            json={
                'from': f'Ecom+AI Weekly <{from_email}>',
                'to': to_emails,
                'subject': subject,
                'html': html_content
            }
        )

        if response.status_code == 200:
            result = response.json()
            print(f"[Weekly] 邮件发送成功: {result.get('id')}")
            print(f"[Weekly] 收件人: {', '.join(to_emails)}")
            return True
        else:
            print(f"[Weekly] 邮件发送失败: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print(f"[Weekly] 邮件发送异常: {e}")
        return False


def save_weekly_to_s3(html_content: str, analysis: dict, stats: dict, config: Config) -> bool:
    """保存周报到 S3"""
    s3_config = config.get('s3', {})
    if not s3_config.get('enabled', False):
        print("[Weekly] S3 存储已禁用")
        return False

    bucket = s3_config.get('bucket', 'cls-whatsnew')
    now = datetime.now(BEIJING_TZ)
    week_start = now - timedelta(days=7)

    prefix = f"weekly-ecom/{week_start.strftime('%Y-%m-%d')}_{now.strftime('%Y-%m-%d')}"

    try:
        s3 = boto3.client('s3')

        s3.put_object(
            Bucket=bucket,
            Key=f'{prefix}.html',
            Body=html_content.encode('utf-8'),
            ContentType='text/html; charset=utf-8'
        )

        json_data = {
            'week_start': week_start.isoformat(),
            'week_end': now.isoformat(),
            'stats': stats,
            'analysis': analysis,
            'generated_at': now.isoformat()
        }

        s3.put_object(
            Bucket=bucket,
            Key=f'{prefix}.json',
            Body=json.dumps(json_data, ensure_ascii=False, indent=2).encode('utf-8'),
            ContentType='application/json; charset=utf-8'
        )

        print(f"[Weekly] 已保存到 s3://{bucket}/{prefix}.html")
        print(f"[Weekly] 已保存到 s3://{bucket}/{prefix}.json")
        return True

    except Exception as e:
        print(f"[Weekly] S3 保存失败: {e}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("电商+AI 周报生成")
    print("=" * 60)

    config = Config()

    data_file = config.get('data_file', 'data/sent_news.json')
    storage = Storage(data_file)

    lookback_days = config.get('weekly.lookback_days', 7)
    s3_bucket = config.get('s3.bucket', 'cls-whatsnew')
    s3_prefix = config.get('s3.prefix', 'ecom')

    print(f"\n[Weekly] 从 S3 加载过去 {lookback_days} 天的日报...")
    week_news = get_week_news_from_s3(days=lookback_days, bucket=s3_bucket, prefix=s3_prefix)

    print(f"[Weekly] 共获取 {len(week_news)} 条新闻")

    if not week_news:
        print("[Weekly] 本周没有新闻数据，跳过周报生成")
        return

    by_source = Counter(item.get('source', '未知') for item in week_news)
    by_category = Counter(item.get('category', '未分类') for item in week_news)

    dates = set()
    for item in week_news:
        report_date = item.get('report_date')
        if report_date:
            dates.add(report_date)
        else:
            published = item.get('published')
            if published:
                try:
                    if isinstance(published, str):
                        dt = datetime.fromisoformat(published.replace('Z', '+00:00'))
                        dates.add(dt.strftime('%Y-%m-%d'))
                except:
                    pass

    if dates:
        sorted_dates = sorted(dates)
        date_range = f"{sorted_dates[0]} ~ {sorted_dates[-1]}"
    else:
        date_range = "N/A"

    stats = {
        'total': len(week_news),
        'source_count': len(by_source),
        'category_count': len(by_category),
        'by_source': dict(by_source),
        'by_category': dict(by_category),
        'date_range': date_range
    }

    print(f"[Weekly] 来源数: {stats['source_count']}")
    print(f"[Weekly] 日期范围: {date_range}")

    print("\n[Weekly] 开始 AI 分析...")
    analyzer = WeeklyAnalyzer(aws_region=config.get('ai.aws_region', 'us-west-2'))
    analysis = analyzer.analyze_week(week_news, stats)
    print("[Weekly] AI 分析完成")

    print("\n[Weekly] 生成周报 HTML...")
    html_content = format_weekly_email(week_news, analysis, stats)

    print("\n[Weekly] 发送邮件...")
    email_sent = send_weekly_email(html_content, config)

    print("\n[Weekly] 保存到 S3...")
    s3_saved = save_weekly_to_s3(html_content, analysis, stats, config)

    print("\n" + "=" * 60)
    print("电商+AI 周报生成完成")
    print(f"  - 新闻数量: {stats['total']}")
    print(f"  - 邮件发送: {'成功' if email_sent else '失败'}")
    print(f"  - S3 保存: {'成功' if s3_saved else '失败'}")
    print("=" * 60)


if __name__ == '__main__':
    main()
