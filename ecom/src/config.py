"""配置管理模块 - 支持 S3 和本地配置"""
import yaml
import boto3
from pathlib import Path


# S3 配置位置
S3_CONFIG_BUCKET = 'cls-whatsnew'
S3_CONFIG_KEY = 'config/ecom.yaml'


class Config:
    def __init__(self, config_path='config.yaml', use_s3=True):
        self.config_path = Path(config_path)
        self.use_s3 = use_s3
        self.config = self.load()

    def load(self):
        """加载配置文件，优先从 S3 加载"""
        if self.use_s3:
            try:
                s3 = boto3.client('s3')
                response = s3.get_object(Bucket=S3_CONFIG_BUCKET, Key=S3_CONFIG_KEY)
                content = response['Body'].read().decode('utf-8')
                print(f"[Config] 从 S3 加载: s3://{S3_CONFIG_BUCKET}/{S3_CONFIG_KEY}")
                return yaml.safe_load(content)
            except Exception as e:
                print(f"[Config] S3 加载失败: {e}, 使用本地配置")

        # 回退到本地文件
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            print(f"[Config] 从本地加载: {self.config_path}")
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
