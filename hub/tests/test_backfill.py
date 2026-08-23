"""backfill.py 的回归测试

重点覆盖两个真实 bug：
1. save_to_s3 被 add_article 的返回值挡住，导致索引失败时丢掉已抓到的正文
2. S3 归档目录用 datetime.now()，回填历史日期会把旧文章归到今天
"""
import sys
from pathlib import Path

import pytest

HUB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HUB))

import backfill as bf


class FakeStorage:
    """记录调用顺序和参数，模拟 AOSS 403 的情况"""

    def __init__(self, index_ok=True, archive_ok=True):
        self.index_ok = index_ok
        self.archive_ok = archive_ok
        self.archived = []
        self.indexed = []

    def save_to_s3(self, article, archive_date=None):
        self.archived.append((article["id"], archive_date))
        return self.archive_ok

    def add_article(self, article):
        self.indexed.append(article["id"])
        return self.index_ok


class FakeFetcher:
    def __init__(self, fail_urls=()):
        self.fail_urls = set(fail_urls)
        self.calls = []

    def fetch_full_content(self, url, metadata=None):
        self.calls.append(url)
        if url in self.fail_urls:
            return None
        return {"id": "id-" + url[-1], "url": url, "title": "t", "content": "body"}


class FakeS3:
    def __init__(self, items):
        self._items = items

    def get_object(self, Bucket=None, Key=None):
        import io, json

        return {"Body": io.BytesIO(json.dumps({"items": self._items}).encode())}


def items(n):
    return [{"link": f"http://example.com/{i}", "title": f"t{i}"} for i in range(n)]


class TestArchiveNotGatedOnIndex:
    def test_archives_even_when_indexing_fails(self):
        # 这是主 bug：AOSS 返回 403 时，正文必须仍然落到 S3
        st = FakeStorage(index_ok=False)
        ok, skip, fail, idx_fail = bf.backfill_date(
            None, FakeFetcher(), st, FakeS3(items(3)), "2026-07-07"
        )
        assert len(st.archived) == 3
        assert ok == 3
        assert fail == 0
        assert idx_fail == 3

    def test_counts_success_when_both_work(self):
        st = FakeStorage()
        ok, skip, fail, idx_fail = bf.backfill_date(
            None, FakeFetcher(), st, FakeS3(items(2)), "2026-07-07"
        )
        assert ok == 2 and idx_fail == 0 and fail == 0

    def test_archive_failure_counts_as_failure(self):
        st = FakeStorage(archive_ok=False)
        ok, skip, fail, idx_fail = bf.backfill_date(
            None, FakeFetcher(), st, FakeS3(items(2)), "2026-07-07"
        )
        assert ok == 0 and fail == 2


class TestArchiveDate:
    def test_stamps_the_backfilled_date_not_today(self):
        # 第二个 bug：回填 7/7 必须写成 2026-07-07，不能写成今天
        st = FakeStorage()
        bf.backfill_date(None, FakeFetcher(), st, FakeS3(items(2)), "2026-07-07")
        assert {d for _, d in st.archived} == {"2026-07-07"}

    def test_each_date_gets_its_own_stamp(self):
        st = FakeStorage()
        bf.backfill_date(None, FakeFetcher(), st, FakeS3(items(1)), "2026-07-07")
        bf.backfill_date(None, FakeFetcher(), st, FakeS3(items(1)), "2026-07-08")
        assert [d for _, d in st.archived] == ["2026-07-07", "2026-07-08"]


class TestSkipExisting:
    def test_skips_already_archived(self):
        import hashlib

        url = "http://example.com/0"
        short = hashlib.md5(url.encode()).hexdigest()[:8]
        ft = FakeFetcher()
        st = FakeStorage()
        ok, skip, fail, _ = bf.backfill_date(
            None, ft, st, FakeS3(items(2)), "2026-07-07", existing={short}
        )
        # 已归档的那条不该再发网络请求
        assert url not in ft.calls
        assert skip == 1 and ok == 1

    def test_skips_items_without_link(self):
        st = FakeStorage()
        ok, skip, fail, _ = bf.backfill_date(
            None, FakeFetcher(), st, FakeS3([{"title": "no link"}]), "2026-07-07"
        )
        assert skip == 1 and ok == 0


class TestFetchFailures:
    def test_fetch_failure_does_not_archive(self):
        ft = FakeFetcher(fail_urls={"http://example.com/0"})
        st = FakeStorage()
        ok, skip, fail, _ = bf.backfill_date(
            None, ft, st, FakeS3(items(2)), "2026-07-07"
        )
        assert fail == 1 and ok == 1
        assert len(st.archived) == 1


class TestMissingDay:
    def test_missing_daily_file_returns_four_zeros(self):
        class Dead:
            def get_object(self, **kw):
                raise RuntimeError("NoSuchKey")

        # 返回值必须是 4 元组，否则 main() 解包会崩
        assert bf.backfill_date(None, FakeFetcher(), FakeStorage(), Dead(), "2026-07-07") == (0, 0, 0, 0)


class TestDryRun:
    def test_dry_run_makes_no_network_or_s3_calls(self):
        ft = FakeFetcher()
        st = FakeStorage()
        ok, skip, fail, _ = bf.backfill_date(
            None, ft, st, FakeS3(items(3)), "2026-07-07", dry_run=True
        )
        assert ft.calls == [] and st.archived == [] and ok == 3


class TestListArchivedIds:
    def test_extracts_short_id_from_folder_name(self):
        class Pager:
            def paginate(self, **kw):
                return [{"CommonPrefixes": [
                    {"Prefix": "hub/2026-08-23_Some-Title_5f9a84d7/"},
                    {"Prefix": "hub/2026-07-04_Other_abc12345/"},
                ]}]

        class S3:
            def get_paginator(self, name):
                return Pager()

        assert bf.list_archived_ids(S3(), "b") == {"5f9a84d7", "abc12345"}

    def test_ignores_folders_without_underscore(self):
        class Pager:
            def paginate(self, **kw):
                return [{"CommonPrefixes": [{"Prefix": "hub/screenshots/"}]}]

        class S3:
            def get_paginator(self, name):
                return Pager()

        assert bf.list_archived_ids(S3(), "b") == set()


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
