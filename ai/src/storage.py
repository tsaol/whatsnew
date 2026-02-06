"""数据存储模块 - JSON文件存储 + S3归档"""
import json
import boto3
from pathlib import Path
from datetime import datetime, timedelta, timezone
from collections import Counter


class Storage:
    def __init__(self, data_file='data/sent_news.json'):
        self.data_file = Path(data_file)
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        self.sent_items = self.load()

    def load(self):
        """加载已发送记录"""
        if not self.data_file.exists():
            return {}

        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载数据文件失败: {e}")
            return {}

    def save(self):
        """保存记录到文件"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.sent_items, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存数据文件失败: {e}")

    def is_sent(self, item_id):
        """检查是否已发送"""
        return item_id in self.sent_items

    def mark_sent(self, item_id, title):
        """标记为已发送"""
        self.sent_items[item_id] = {
            'title': title,
            'sent_at': datetime.now().isoformat()
        }
        self.save()

    def get_stats(self):
        """获取统计信息"""
        return {
            'total_sent': len(self.sent_items),
            'data_file': str(self.data_file)
        }

    def get_week_news(self, days=7):
        """获取过去一周的新闻（用于周报）"""
        cutoff = datetime.now() - timedelta(days=days)
        week_news = []

        for item_id, item_data in self.sent_items.items():
            try:
                sent_at = datetime.fromisoformat(item_data.get('sent_at', ''))
                if sent_at >= cutoff:
                    week_news.append({
                        'id': item_id,
                        'title': item_data.get('title', ''),
                        'sent_at': sent_at,
                        **item_data
                    })
            except:
                continue

        # 按发送时间排序（最新的在前）
        week_news.sort(key=lambda x: x.get('sent_at', datetime.min), reverse=True)
        return week_news

    def save_weekly_summary(self, summary_data):
        """保存周报摘要"""
        weekly_file = self.data_file.parent / 'weekly_summaries.json'

        # 加载现有摘要
        summaries = []
        if weekly_file.exists():
            try:
                with open(weekly_file, 'r', encoding='utf-8') as f:
                    summaries = json.load(f)
            except:
                summaries = []

        # 添加新摘要
        summary_data['generated_at'] = datetime.now().isoformat()
        summaries.append(summary_data)

        # 只保留最近12周的摘要
        summaries = summaries[-12:]

        # 保存
        try:
            with open(weekly_file, 'w', encoding='utf-8') as f:
                json.dump(summaries, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存周报摘要失败: {e}")
            return False

    def get_weekly_summaries(self, count=4):
        """获取历史周报摘要"""
        weekly_file = self.data_file.parent / 'weekly_summaries.json'

        if not weekly_file.exists():
            return []

        try:
            with open(weekly_file, 'r', encoding='utf-8') as f:
                summaries = json.load(f)
            return summaries[-count:]
        except:
            return []

    def save_to_s3(self, html_content, items, ai_analysis, category='ai'):
        """保存日报到 S3

        Args:
            html_content: 邮件 HTML 内容
            items: 新闻列表
            ai_analysis: AI 分析结果
            category: 'ai' 或 'ecom'
        """
        bucket = 'cls-whatsnew'
        beijing_tz = timezone(timedelta(hours=8))
        date_str = datetime.now(beijing_tz).strftime('%Y-%m-%d')
        prefix = f'{category}/{date_str}'

        try:
            s3 = boto3.client('s3')

            # 上传 HTML
            s3.put_object(
                Bucket=bucket,
                Key=f'{prefix}.html',
                Body=html_content.encode('utf-8'),
                ContentType='text/html; charset=utf-8'
            )

            # 构建 JSON 数据
            json_data = {
                'date': date_str,
                'category': category,
                'stats': {
                    'total': len(items),
                    'by_category': dict(Counter(item.get('category', '未分类') for item in items)),
                    'by_source': dict(Counter(item.get('source', '未知') for item in items))
                },
                'items': [
                    {
                        'id': item.get('id'),
                        'title': item.get('title'),
                        'title_zh': item.get('title_zh'),
                        'source': item.get('source'),
                        'category': item.get('category'),
                        'link': item.get('link'),
                        'summary': item.get('summary', '')[:500],
                        'summary_zh': item.get('summary_zh', '')[:500] if item.get('summary_zh') else None,
                        'published': item.get('published'),
                        'ai_score': item.get('ai_score'),
                        'label': item.get('label'),
                        'oneliner': item.get('oneliner')
                    }
                    for item in items
                ],
                'ai_analysis': {
                    'summary': ai_analysis.get('summary') if ai_analysis else None,
                    'trends': ai_analysis.get('trends') if ai_analysis else None,
                    'top_news': [
                        {'title': t.get('title'), 'title_zh': t.get('title_zh'), 'reason': t.get('ai_reason')}
                        for t in (ai_analysis.get('top_news') or [])
                    ] if ai_analysis else None,
                    'hot_topics': ai_analysis.get('hot_topics') if ai_analysis else None,
                    'action_items': ai_analysis.get('action_items') if ai_analysis else None
                } if ai_analysis else None,
                'generated_at': datetime.now(beijing_tz).isoformat()
            }

            # 上传 JSON
            s3.put_object(
                Bucket=bucket,
                Key=f'{prefix}.json',
                Body=json.dumps(json_data, ensure_ascii=False, indent=2).encode('utf-8'),
                ContentType='application/json; charset=utf-8'
            )

            print(f"[S3] 已保存到 s3://{bucket}/{prefix}.html")
            print(f"[S3] 已保存到 s3://{bucket}/{prefix}.json")
            return True

        except Exception as e:
            print(f"[S3] 保存失败: {e}")
            return False
