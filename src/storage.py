"""数据存储模块 - 简单的JSON文件存储"""
import json
from pathlib import Path
from datetime import datetime


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
