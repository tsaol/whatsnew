"""配置管理模块"""
import yaml
from pathlib import Path


class Config:
    def __init__(self, config_path='config.yaml'):
        self.config_path = Path(config_path)
        self.config = self.load()

    def load(self):
        """加载配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def get(self, key, default=None):
        """获取配置项"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

    @property
    def email_config(self):
        return self.config.get('email', {})

    @property
    def sources(self):
        return [s for s in self.config.get('sources', []) if s.get('enabled', True)]

    @property
    def schedule_config(self):
        return self.config.get('schedule', {})
