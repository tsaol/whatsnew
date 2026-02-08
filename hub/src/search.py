"""搜索接口 - 语义搜索 + 全文搜索"""
from typing import Optional


class ContentSearch:
    def __init__(self, storage):
        self.storage = storage
        self.client = storage.client
        self.index_name = storage.index_name

    def search(self, query: str, top_k: int = 10, filters: dict = None) -> list:
        """混合搜索: 向量相似度 + 过滤

        Args:
            query: 搜索查询
            top_k: 返回结果数量
            filters: 过滤条件 {source, category, date_from, date_to}

        Returns:
            list: 搜索结果列表
        """
        if not self.client:
            print("[Search] OpenSearch 客户端未初始化")
            return []

        try:
            # 生成查询向量
            query_embedding = self.storage._get_embedding(query)
            if not query_embedding:
                print("[Search] 无法生成查询向量，回退到全文搜索")
                return self.full_text_search(query, top_k, filters)

            # 构建 kNN 查询
            search_body = {
                "size": top_k,
                "query": {
                    "bool": {
                        "must": [
                            {
                                "knn": {
                                    "embedding": {
                                        "vector": query_embedding,
                                        "k": top_k
                                    }
                                }
                            }
                        ]
                    }
                },
                "_source": {
                    "excludes": ["embedding"]  # 不返回向量字段
                }
            }

            # 添加过滤条件
            filter_clauses = self._build_filters(filters)
            if filter_clauses:
                search_body["query"]["bool"]["filter"] = filter_clauses

            response = self.client.search(index=self.index_name, body=search_body)
            results = self._format_results(response)

            print(f"[Search] 语义搜索: '{query[:30]}...' 找到 {len(results)} 条结果")
            return results

        except Exception as e:
            print(f"[Search] 搜索失败: {e}")
            return []

    def full_text_search(self, query: str, top_k: int = 10, filters: dict = None) -> list:
        """纯全文搜索 (BM25)

        Args:
            query: 搜索查询
            top_k: 返回结果数量
            filters: 过滤条件

        Returns:
            list: 搜索结果列表
        """
        if not self.client:
            print("[Search] OpenSearch 客户端未初始化")
            return []

        try:
            search_body = {
                "size": top_k,
                "query": {
                    "bool": {
                        "must": [
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["title^3", "content"],
                                    "type": "best_fields",
                                    "fuzziness": "AUTO"
                                }
                            }
                        ]
                    }
                },
                "_source": {
                    "excludes": ["embedding"]
                }
            }

            # 添加过滤条件
            filter_clauses = self._build_filters(filters)
            if filter_clauses:
                search_body["query"]["bool"]["filter"] = filter_clauses

            response = self.client.search(index=self.index_name, body=search_body)
            results = self._format_results(response)

            print(f"[Search] 全文搜索: '{query[:30]}...' 找到 {len(results)} 条结果")
            return results

        except Exception as e:
            print(f"[Search] 全文搜索失败: {e}")
            return []

    def hybrid_search(self, query: str, top_k: int = 10, filters: dict = None,
                      semantic_weight: float = 0.7) -> list:
        """混合搜索: 向量 + BM25 加权融合

        Args:
            query: 搜索查询
            top_k: 返回结果数量
            filters: 过滤条件
            semantic_weight: 语义搜索权重 (0-1)

        Returns:
            list: 融合后的搜索结果
        """
        # 获取语义搜索结果
        semantic_results = self.search(query, top_k * 2, filters)

        # 获取全文搜索结果
        fulltext_results = self.full_text_search(query, top_k * 2, filters)

        # 简单的 RRF (Reciprocal Rank Fusion) 融合
        scores = {}

        for rank, result in enumerate(semantic_results):
            doc_id = result.get('url', result.get('id'))
            scores[doc_id] = scores.get(doc_id, 0) + semantic_weight / (rank + 1)
            if doc_id not in scores:
                scores[doc_id] = {'doc': result, 'score': 0}
            scores[doc_id] = {'doc': result, 'score': scores.get(doc_id, {}).get('score', 0) + semantic_weight / (rank + 1)}

        for rank, result in enumerate(fulltext_results):
            doc_id = result.get('url', result.get('id'))
            text_weight = 1 - semantic_weight
            if doc_id in scores:
                scores[doc_id]['score'] += text_weight / (rank + 1)
            else:
                scores[doc_id] = {'doc': result, 'score': text_weight / (rank + 1)}

        # 按分数排序
        sorted_results = sorted(scores.values(), key=lambda x: x['score'], reverse=True)

        return [item['doc'] for item in sorted_results[:top_k]]

    def list_sources(self) -> list:
        """列出所有来源"""
        if not self.client:
            return []

        try:
            response = self.client.search(
                index=self.index_name,
                body={
                    "size": 0,
                    "aggs": {
                        "sources": {
                            "terms": {"field": "source", "size": 100}
                        }
                    }
                }
            )
            buckets = response.get('aggregations', {}).get('sources', {}).get('buckets', [])
            return [{'source': b['key'], 'count': b['doc_count']} for b in buckets]
        except:
            return []

    def list_categories(self) -> list:
        """列出所有类别"""
        if not self.client:
            return []

        try:
            response = self.client.search(
                index=self.index_name,
                body={
                    "size": 0,
                    "aggs": {
                        "categories": {
                            "terms": {"field": "category", "size": 100}
                        }
                    }
                }
            )
            buckets = response.get('aggregations', {}).get('categories', {}).get('buckets', [])
            return [{'category': b['key'], 'count': b['doc_count']} for b in buckets]
        except:
            return []

    def _build_filters(self, filters: Optional[dict]) -> list:
        """构建过滤条件"""
        if not filters:
            return []

        filter_clauses = []

        if filters.get('source'):
            filter_clauses.append({"term": {"source": filters['source']}})

        if filters.get('category'):
            filter_clauses.append({"term": {"category": filters['category']}})

        if filters.get('date_from') or filters.get('date_to'):
            date_range = {}
            if filters.get('date_from'):
                date_range['gte'] = filters['date_from']
            if filters.get('date_to'):
                date_range['lte'] = filters['date_to']
            filter_clauses.append({"range": {"published_at": date_range}})

        return filter_clauses

    def _format_results(self, response: dict) -> list:
        """格式化搜索结果"""
        results = []
        for hit in response.get('hits', {}).get('hits', []):
            doc = hit['_source']
            doc['_score'] = hit.get('_score', 0)
            doc['_id'] = hit['_id']
            results.append(doc)
        return results
