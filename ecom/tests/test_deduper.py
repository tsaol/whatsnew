"""跨源去重单元测试

覆盖：
- normalize_title：Google News 后缀、Bloomberg/Reuters 后缀、CJK、空标题
- source_score：substring 匹配、默认值
- dedupe_cross_source：合并同一事件、保留最权威主源、related_sources 挂载
- dedupe_top_news：TOP 榜去重、score 更高的胜出
"""
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.deduper import (
    normalize_title,
    source_score,
    dedupe_cross_source,
    dedupe_top_news,
)


class TestNormalizeTitle(unittest.TestCase):

    def test_strips_aws_suffix(self):
        a = normalize_title("Build agentic creative workflows with Amazon Quick and fal - Amazon Web Services (AWS)")
        b = normalize_title("Build agentic creative workflows with Amazon Quick and fal")
        self.assertEqual(a, b)

    def test_strips_bloomberg_suffix(self):
        a = normalize_title("Shein's IPO Has Only One Winner - Bloomberg.com")
        b = normalize_title("Shein's IPO Has Only One Winner - Bloomberg")
        c = normalize_title("Shein's IPO Has Only One Winner")
        self.assertEqual(a, c)
        self.assertEqual(b, c)

    def test_strips_reuters_suffix(self):
        a = normalize_title("Why Shein went back to its Chinese roots to make an IPO work - Reuters")
        b = normalize_title("Why Shein went back to its Chinese roots to make an IPO work")
        self.assertEqual(a, b)

    def test_case_insensitive(self):
        self.assertEqual(normalize_title("Hello World"), normalize_title("HELLO WORLD"))
        self.assertEqual(normalize_title("Hello World"), normalize_title("hello world"))

    def test_cjk_preserved(self):
        a = normalize_title("迪卡侬借助Chronos-2实现大规模需求预测")
        # CJK 字符应保留
        self.assertIn("迪", a)
        self.assertIn("卡", a)

    def test_empty_title(self):
        self.assertEqual(normalize_title(""), "")
        self.assertEqual(normalize_title(None), "")

    def test_punctuation_normalized(self):
        self.assertEqual(normalize_title("Foo, bar."), normalize_title("foo bar"))
        self.assertEqual(normalize_title("A/B testing"), normalize_title("A B testing"))


class TestSourceScore(unittest.TestCase):

    def test_aws_blog_beats_google_news(self):
        self.assertGreater(
            source_score("AWS Machine Learning Blog"),
            source_score("Google News - Amazon AI"),
        )

    def test_official_beats_aggregator(self):
        self.assertGreater(
            source_score("Amazon Science"),
            source_score("Google News - AWS Spain"),
        )

    def test_industry_media_middle_tier(self):
        s = source_score("Digital Commerce 360")
        self.assertGreater(s, source_score("Google News"))
        self.assertLess(s, source_score("AWS News Blog"))

    def test_unknown_source_gets_default(self):
        # 50 是默认值；未知源不应意外高分
        self.assertEqual(source_score("Some Random Blog Nobody Knows"), 50)

    def test_none_source(self):
        self.assertEqual(source_score(None), 50)
        self.assertEqual(source_score(""), 50)


class TestDedupeCrossSource(unittest.TestCase):

    def test_merges_duplicates_keeping_authoritative_source(self):
        items = [
            {
                "id": "1",
                "title": "Build agentic creative workflows with Amazon Quick and fal - Amazon Web Services (AWS)",
                "link": "https://news.google.com/xxx",
                "summary": "Short.",
                "source": "Google News - Amazon AI",
            },
            {
                "id": "2",
                "title": "Build agentic creative workflows with Amazon Quick and fal",
                "link": "https://aws.amazon.com/blogs/machine-learning/build-agentic-...",
                "summary": "Long detailed summary here from the primary source, explaining the pipeline.",
                "source": "AWS Machine Learning Blog",
            },
        ]
        result = dedupe_cross_source(items)
        self.assertEqual(len(result), 1)
        primary = result[0]
        # AWS Blog 应作为主源（更权威）
        self.assertEqual(primary["source"], "AWS Machine Learning Blog")
        # related_sources 里应有 Google News
        self.assertEqual(len(primary["related_sources"]), 1)
        self.assertEqual(primary["related_sources"][0]["name"], "Google News - Amazon AI")

    def test_bloomberg_variants_merged(self):
        items = [
            {"id": "a", "title": "Shein's IPO Has Only One Winner - Bloomberg.com",
             "link": "https://bloomberg.com/xx", "summary": "Text",
             "source": "Google News - SHEIN"},
            {"id": "b", "title": "Opinion: Shein's IPO Has Only One Winner - The Business of Fashion",
             "link": "https://bof.com/yy", "summary": "Text",
             "source": "Google News - SHEIN"},
        ]
        # 标题不同（一个有 "Opinion:" 前缀），标准化后**不应**被合并——不同报道
        result = dedupe_cross_source(items)
        self.assertEqual(len(result), 2, "不同标题（Opinion: vs 无前缀）应保留为独立条目")

    def test_unique_items_pass_through(self):
        items = [
            {"id": "1", "title": "Foo", "link": "https://a", "summary": "s", "source": "A"},
            {"id": "2", "title": "Bar", "link": "https://b", "summary": "s", "source": "B"},
        ]
        result = dedupe_cross_source(items)
        self.assertEqual(len(result), 2)
        for r in result:
            self.assertEqual(r["related_sources"], [])

    def test_empty_input(self):
        self.assertEqual(dedupe_cross_source([]), [])

    def test_empty_titles_are_kept_separately(self):
        # 标准化后为空的标题不应被误合并
        items = [
            {"id": "1", "title": "!!!", "link": "https://a", "summary": "s", "source": "A"},
            {"id": "2", "title": "***", "link": "https://b", "summary": "s", "source": "B"},
        ]
        result = dedupe_cross_source(items)
        self.assertEqual(len(result), 2)


class TestDedupeTopNews(unittest.TestCase):

    def test_top_dedup_keeps_higher_score(self):
        top = [
            {"id": "1", "title": "Build agentic creative workflows with Amazon Quick and fal", "score": 9},
            {"id": "2", "title": "Build agentic creative workflows with Amazon Quick and fal - Amazon Web Services (AWS)", "score": 7},
        ]
        result = dedupe_top_news(top)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "1")

    def test_top_dedup_preserves_order(self):
        top = [
            {"id": "1", "title": "First News", "score": 8},
            {"id": "2", "title": "Second News", "score": 7},
            {"id": "3", "title": "First News - Reuters", "score": 6},  # dup of #1, lower score
        ]
        result = dedupe_top_news(top)
        self.assertEqual([r["id"] for r in result], ["1", "2"])

    def test_top_dedup_empty(self):
        self.assertEqual(dedupe_top_news([]), [])


if __name__ == "__main__":
    unittest.main()
