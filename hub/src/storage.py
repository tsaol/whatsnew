"""OpenSearch Serverless 存储模块"""
import json
import boto3
from datetime import datetime, timezone, timedelta
from typing import Optional

try:
    from opensearchpy import OpenSearch, RequestsHttpConnection
    from requests_aws4auth import AWS4Auth
except ImportError:
    OpenSearch = None
    RequestsHttpConnection = None
    AWS4Auth = None


class ContentStorage:
    def __init__(self, config):
        self.config = config
        self.os_config = config.opensearch_config
        self.embed_config = config.embeddings_config
        self.s3_config = config.s3_config

        self.endpoint = self.os_config.get('endpoint', '')
        self.index_name = self.os_config.get('index', 'whatsnew-articles')
        self.region = self.os_config.get('region', 'us-west-2')

        self.client = None
        self.bedrock = None

        if self.endpoint:
            self.client = self._create_client()
            self._ensure_index()
        else:
            print("[Storage] OpenSearch endpoint 未配置，跳过初始化")

    def _create_client(self):
        """创建 OpenSearch Serverless 客户端"""
        if OpenSearch is None:
            print("[Storage] opensearch-py 未安装，请运行 pip install opensearch-py requests-aws4auth")
            return None

        try:
            credentials = boto3.Session().get_credentials()
            awsauth = AWS4Auth(
                credentials.access_key,
                credentials.secret_key,
                self.region,
                'aoss',  # OpenSearch Serverless service
                session_token=credentials.token
            )

            # 解析 endpoint (移除 https:// 前缀)
            host = self.endpoint.replace('https://', '').replace('http://', '')

            client = OpenSearch(
                hosts=[{'host': host, 'port': 443}],
                http_auth=awsauth,
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection,
                timeout=30
            )

            print(f"[Storage] OpenSearch 客户端已创建: {host}")
            return client

        except Exception as e:
            print(f"[Storage] 创建 OpenSearch 客户端失败: {e}")
            return None

    def _ensure_index(self):
        """确保索引存在，带向量字段映射"""
        if not self.client:
            return

        try:
            if not self.client.indices.exists(index=self.index_name):
                self.client.indices.create(
                    index=self.index_name,
                    body={
                        "settings": {
                            "index.knn": True
                        },
                        "mappings": {
                            "properties": {
                                "title": {"type": "text", "analyzer": "standard"},
                                "content": {"type": "text", "analyzer": "standard"},
                                "embedding": {
                                    "type": "knn_vector",
                                    "dimension": 1024,  # Titan v2 维度
                                    "method": {
                                        "name": "hnsw",
                                        "space_type": "cosinesimil",
                                        "engine": "faiss",
                                        "parameters": {
                                            "ef_construction": 128,
                                            "m": 16
                                        }
                                    }
                                },
                                "source": {"type": "keyword"},
                                "category": {"type": "keyword"},
                                "author": {"type": "keyword"},
                                "published_at": {"type": "date"},
                                "fetched_at": {"type": "date"},
                                "url": {"type": "keyword"},
                                "content_length": {"type": "integer"}
                            }
                        }
                    }
                )
                print(f"[Storage] 索引已创建: {self.index_name}")
            else:
                print(f"[Storage] 索引已存在: {self.index_name}")

        except Exception as e:
            print(f"[Storage] 创建索引失败: {e}")

    def add_article(self, article: dict) -> bool:
        """添加文章到 OpenSearch

        Args:
            article: {id, url, title, content, source, category, ...}

        Returns:
            bool: 是否成功
        """
        if not self.client:
            print("[Storage] OpenSearch 客户端未初始化")
            return False

        try:
            # 生成 embedding
            embedding = self._get_embedding(article['content'])
            if not embedding:
                print(f"[Storage] 无法生成 embedding: {article.get('title', '')[:30]}")
                return False

            # 构建文档
            doc = {
                "title": article.get('title', ''),
                "content": article.get('content', ''),
                "embedding": embedding,
                "source": article.get('source', ''),
                "category": article.get('category', ''),
                "author": article.get('author'),
                "published_at": article.get('published_at'),
                "fetched_at": article.get('fetched_at'),
                "url": article.get('url', ''),
                "content_length": article.get('content_length', 0)
            }

            # 索引文档 (OpenSearch Serverless 不支持自定义 ID)
            doc['article_id'] = article['id']  # 保存原始 ID 作为字段
            self.client.index(
                index=self.index_name,
                body=doc
            )

            print(f"[Storage] 已索引: {article.get('title', '')[:50]}")
            return True

        except Exception as e:
            print(f"[Storage] 索引文章失败: {e}")
            return False

    def add_batch(self, articles: list) -> tuple:
        """批量添加文章

        Returns:
            tuple: (成功数, 失败数)
        """
        success = 0
        failed = 0

        for article in articles:
            if self.add_article(article):
                success += 1
            else:
                failed += 1

        print(f"[Storage] 批量索引完成: {success} 成功, {failed} 失败")
        return success, failed

    def exists(self, article_id: str) -> bool:
        """检查文章是否已存在"""
        if not self.client:
            return False

        try:
            return self.client.exists(index=self.index_name, id=article_id)
        except:
            return False

    def get_article(self, article_id: str) -> Optional[dict]:
        """获取文章"""
        if not self.client:
            return None

        try:
            response = self.client.get(index=self.index_name, id=article_id)
            return response['_source']
        except:
            return None

    def _get_embedding(self, text: str) -> Optional[list]:
        """调用 Bedrock Embeddings 生成向量 (支持 Titan 和 Cohere)"""
        if not text:
            return None

        try:
            if not self.bedrock:
                self.bedrock = boto3.client(
                    'bedrock-runtime',
                    region_name=self.embed_config.get('region', 'us-west-2')
                )

            model_id = self.embed_config.get('model_id', 'amazon.titan-embed-text-v2:0')

            # 截断文本
            truncated_text = text[:8000]

            # 根据模型构建不同的请求体
            if 'cohere' in model_id:
                # Cohere API 格式
                request_body = {
                    "texts": [truncated_text],
                    "input_type": "search_document"
                }
            else:
                # Titan API 格式
                request_body = {"inputText": truncated_text}

            response = self.bedrock.invoke_model(
                modelId=model_id,
                body=json.dumps(request_body)
            )

            result = json.loads(response['body'].read())

            # 根据模型解析不同的响应格式
            if 'cohere' in model_id:
                return result.get('embeddings', [[]])[0]
            else:
                return result.get('embedding')

        except Exception as e:
            print(f"[Storage] 生成 embedding 失败: {e}")
            return None

    def save_to_s3(self, article: dict) -> bool:
        """保存文章到 S3 备份

        Args:
            article: 文章数据

        Returns:
            bool: 是否成功
        """
        if not self.s3_config.get('enabled', False):
            return False

        try:
            s3 = boto3.client('s3')
            bucket = self.s3_config.get('bucket', 'cls-whatsnew')
            prefix = self.s3_config.get('prefix', 'hub')

            beijing_tz = timezone(timedelta(hours=8))
            date_str = datetime.now(beijing_tz).strftime('%Y-%m-%d')

            key = f"{prefix}/articles/{date_str}/{article['id']}.json"

            s3.put_object(
                Bucket=bucket,
                Key=key,
                Body=json.dumps(article, ensure_ascii=False, indent=2).encode('utf-8'),
                ContentType='application/json; charset=utf-8'
            )

            print(f"[S3] 已备份: s3://{bucket}/{key}")
            return True

        except Exception as e:
            print(f"[S3] 备份失败: {e}")
            return False

    def get_stats(self) -> dict:
        """获取索引统计信息"""
        if not self.client:
            return {'status': 'not_initialized'}

        try:
            stats = self.client.indices.stats(index=self.index_name)
            return {
                'status': 'ok',
                'index': self.index_name,
                'doc_count': stats['indices'][self.index_name]['primaries']['docs']['count'],
                'size_bytes': stats['indices'][self.index_name]['primaries']['store']['size_in_bytes']
            }
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
