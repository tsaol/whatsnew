"""AWS 西班牙 region 采集逻辑的单元测试

覆盖:
- SPAIN_REGION_KEYWORDS 命中/未命中
- _should_include() 对 Spain 内容的强制放行
- source_tag='aws_spain' 场景下对非西班牙内容的强制过滤
- Spain 检测优先于 key_company / 电商+AI 关键词过滤
"""
import unittest
from unittest.mock import MagicMock

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.crawler import Crawler


def _mk_crawler(keyword_filter='ecommerce', key_companies=None):
    storage = MagicMock()
    storage.is_sent.return_value = False
    return Crawler(
        storage=storage,
        keyword_filter=keyword_filter,
        key_companies=key_companies or ['SHEIN', 'Amazon'],
    )


class TestSpainRegionDetection(unittest.TestCase):
    """_is_spain_region_news 关键词匹配"""

    def setUp(self):
        self.crawler = _mk_crawler()

    def test_matches_eu_south_2(self):
        self.assertTrue(
            self.crawler._is_spain_region_news(
                "Amazon Bedrock now available in eu-south-2",
                "The AI service is generally available in the Spain region."
            )
        )

    def test_matches_zaragoza(self):
        self.assertTrue(
            self.crawler._is_spain_region_news(
                "New AWS local zone in Zaragoza",
                "AWS expands infrastructure in Spain."
            )
        )

    def test_matches_europe_spain_wording(self):
        self.assertTrue(
            self.crawler._is_spain_region_news(
                "SageMaker now available in the AWS Europe (Spain) Region",
                "General availability."
            )
        )

    def test_matches_chinese_keyword(self):
        self.assertTrue(
            self.crawler._is_spain_region_news(
                "AWS 西班牙 region 新增服务", "萨拉戈萨数据中心扩容"
            )
        )

    def test_no_match_for_unrelated_aws_news(self):
        self.assertFalse(
            self.crawler._is_spain_region_news(
                "AWS re:Invent 2026 keynote highlights",
                "New services launched in us-east-1."
            )
        )

    def test_no_match_for_pure_ecommerce(self):
        self.assertFalse(
            self.crawler._is_spain_region_news(
                "SHEIN launches new AI shopping assistant",
                "Fast-fashion retailer adopts recommendation model."
            )
        )

    def test_ambiguous_spain_without_aws_context_still_matches(self):
        # 设计权衡：只要出现 "spain region"，即便非 AWS 上下文也放行——
        # 因为专用源 (aws_spain tag) 已限定了源头，误报概率低。
        self.assertTrue(
            self.crawler._is_spain_region_news(
                "Spain region economic outlook 2026", "GDP growth."
            )
        )


class TestShouldIncludeSpainOverride(unittest.TestCase):
    """_should_include 的 Spain 逻辑：优先级、tag 过滤"""

    def setUp(self):
        self.crawler = _mk_crawler(keyword_filter='ecommerce')

    def test_spain_content_bypasses_ecommerce_filter(self):
        # 纯 AWS region 上线新闻，没有 e-commerce/AI 关键词，标准过滤会丢弃
        include, is_key, is_spain = self.crawler._should_include(
            "Bedrock now available in eu-south-2",
            "General availability announced today.",
            "AWS What's New",
        )
        self.assertTrue(include)
        self.assertTrue(is_spain)
        self.assertFalse(is_key)

    def test_spain_content_beats_key_company(self):
        # Amazon 相关 + Spain 相关：Spain 优先，不再标 is_key_company
        include, is_key, is_spain = self.crawler._should_include(
            "Amazon EC2 launches in Zaragoza",
            "AWS Spain region welcomes Amazon EC2 instances.",
            "AWS Blog",
        )
        self.assertTrue(include)
        self.assertTrue(is_spain)
        self.assertFalse(is_key, "Spain 检测应优先于 key_company")

    def test_aws_spain_tag_filters_non_spain_content(self):
        # AWS What's New 里的一条与西班牙无关的通用更新——tag='aws_spain' 时应丢弃
        include, is_key, is_spain = self.crawler._should_include(
            "New Amazon RDS feature in us-east-1",
            "Provisioned IOPS improvements.",
            "AWS What's New",
            source_tag='aws_spain',
        )
        self.assertFalse(include)
        self.assertFalse(is_spain)

    def test_aws_spain_tag_still_lets_spain_content_through(self):
        include, is_key, is_spain = self.crawler._should_include(
            "Amazon EKS available in eu-south-2",
            "General availability in the AWS Europe (Spain) Region.",
            "AWS What's New",
            source_tag='aws_spain',
        )
        self.assertTrue(include)
        self.assertTrue(is_spain)

    def test_non_spain_ecommerce_still_works(self):
        # 回归测试：Spain 改动不能破坏原有的 e-commerce+AI 过滤
        include, is_key, is_spain = self.crawler._should_include(
            "Shopify launches AI-powered product recommendations",
            "Machine learning improves conversion.",
            "Shopify Engineering",
        )
        self.assertTrue(include)
        self.assertFalse(is_spain)

    def test_non_spain_non_ecommerce_still_rejected(self):
        include, is_key, is_spain = self.crawler._should_include(
            "New JavaScript framework released",
            "A minimalist alternative to React.",
            "Hacker News",
        )
        self.assertFalse(include)
        self.assertFalse(is_spain)


class TestExcludeKeywordsInteraction(unittest.TestCase):
    """确保 Spain 检测发生在 EXCLUDE_KEYWORDS 之前——公司人事新闻仍能被 Spain 兜底"""

    def setUp(self):
        self.crawler = _mk_crawler()

    def test_hiring_news_mentioning_spain_still_included(self):
        # 边界：如果公司在 eu-south-2 招聘，应保留（region 扩张的信号）
        # 当前实现：Spain 检查最优先，所以会通过
        include, is_key, is_spain = self.crawler._should_include(
            "AWS hires local team in Zaragoza for eu-south-2 expansion",
            "Regional presence grows.",
            "Google News - AWS Spain",
        )
        self.assertTrue(include)
        self.assertTrue(is_spain)


if __name__ == '__main__':
    unittest.main()
