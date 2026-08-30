"""摘要补齐：当 RSS 里的 summary 为空或过短时，用 trafilatura 抓取正文首段。

设计考虑：
- 只对确实短的（<80 字）尝试补齐，避免无谓的 HTTP 请求
- 每条设 8 秒 timeout；有的站会 403（openai.com, ft.com），fallback 保留原摘要
- 用 ThreadPoolExecutor 并发，避免串行 40 条 × 8 秒 = 5 分钟
- 抓不到就用 title 兜底（当前 crawler 已有此逻辑），不 raise
"""
import concurrent.futures
import requests

# trafilatura 是重量级依赖；lazy import 避免测试环境未安装时炸
def _get_trafilatura():
    try:
        import trafilatura
        return trafilatura
    except ImportError:
        return None


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}

MIN_SUMMARY_LEN = 80
MAX_SUMMARY_LEN = 500
FETCH_TIMEOUT = 8
MAX_WORKERS = 8


def _needs_backfill(item):
    """是否需要抓正文补齐？"""
    summary = (item.get("summary") or "").strip()
    title = (item.get("title") or "").strip()
    if len(summary) >= MIN_SUMMARY_LEN and summary != title:
        return False
    # 无 link 抓不动
    if not item.get("link"):
        return False
    return True


def _fetch_one(url):
    """抓单条正文首段"""
    trafilatura = _get_trafilatura()
    if trafilatura is None:
        return None
    try:
        resp = requests.get(url, headers=HEADERS, timeout=FETCH_TIMEOUT)
        if resp.status_code != 200 or not resp.text:
            return None
        text = trafilatura.extract(resp.text, include_comments=False, include_tables=False)
        if not text:
            return None
        # 只取前 MAX_SUMMARY_LEN 字，且去除首行的多余空白
        cleaned = " ".join(text.split())
        return cleaned[:MAX_SUMMARY_LEN]
    except Exception:
        return None


def backfill_summaries(items):
    """对短摘要的条目并发补齐正文首段。

    Args:
        items: item 列表，会**原地修改** summary 字段（保持向后兼容）

    Returns:
        补齐了几条（int）
    """
    targets = [it for it in items if _needs_backfill(it)]
    if not targets:
        return 0

    print(f"  [摘要补齐] 检测到 {len(targets)} 条摘要过短，尝试抓取正文...")

    filled = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(_fetch_one, it["link"]): it for it in targets}
        for future in concurrent.futures.as_completed(futures):
            item = futures[future]
            try:
                text = future.result()
            except Exception:
                text = None
            if text and len(text) >= MIN_SUMMARY_LEN:
                item["summary"] = text
                filled += 1

    print(f"  [摘要补齐] 成功补齐 {filled}/{len(targets)} 条")
    return filled
