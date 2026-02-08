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

    def mark_sent(self, item_id, title, link=None, source=None, category=None):
        """标记为已发送"""
        self.sent_items[item_id] = {
            'title': title,
            'link': link,
            'source': source,
            'category': category,
            'sent_at': datetime.now().isoformat()
        }
        self.save()

    def get_stats(self):
        """获取统计信息"""
        return {
            'total_sent': len(self.sent_items),
            'data_file': str(self.data_file)
        }

    def save_to_s3(self, html_content, items, ai_analysis, s3_config):
        """保存日报到 S3

        Args:
            html_content: 邮件 HTML 内容
            items: 新闻列表
            ai_analysis: AI 分析结果
            s3_config: S3 配置 {enabled, bucket, prefix}
        """
        if not s3_config or not s3_config.get('enabled', False):
            print("[S3] 存储已禁用")
            return False

        bucket = s3_config.get('bucket', 'cls-whatsnew')
        category = s3_config.get('prefix', 'ecom')
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
                    'by_source': dict(Counter(item.get('source', '未知') for item in items)),
                    'key_company_count': sum(1 for item in items if item.get('is_key_company', False))
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
                        'is_key_company': item.get('is_key_company', False),
                        'matched_company': item.get('matched_company')
                    }
                    for item in items
                ],
                'ai_analysis': {
                    'summary': ai_analysis.get('summary') if ai_analysis else None,
                    'trends': ai_analysis.get('trends') if ai_analysis else None,
                    'top_news': [
                        {'title': t.get('title'), 'title_zh': t.get('title_zh'), 'reason': t.get('ai_reason')}
                        for t in (ai_analysis.get('top_news') or [])
                    ] if ai_analysis else None
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
