"""跨源去重：同一事件被多个源报道时，合并为一条卡片。

抓取阶段（crawler）已经按 URL hash 做过精确去重；这里处理的是**同一事件的不同报道**：
- Google News 转载 AWS 官方 blog（URL 完全不同，标题一致）
- 多家媒体报道同一 IPO/融资/发布（标题近似）

去重后主 item 保留主源（权威性最高），其他源作为 `related_sources: [{name, url}]` 列表
挂在主 item 上，供 mailer 展示为来源徽章。
"""
import re
from collections import defaultdict


# 主源权威性排序（数字大 = 更权威 = 作为主卡片保留）
# 匹配是 substring 匹配，所以 "AWS Machine Learning Blog" 也会命中 "AWS Machine"
SOURCE_AUTHORITY = [
    ("AWS Machine Learning Blog", 100),
    ("AWS News Blog", 100),
    ("AWS AI Blog", 100),
    ("AWS Retail Blog", 100),
    ("Amazon Science", 100),
    ("AWS Blog España", 100),
    ("Shopify Engineering", 95),
    ("Amazon Science", 95),
    ("eBay Tech", 90),
    ("Etsy", 90),
    ("Walmart Tech", 90),
    ("Alibaba", 90),
    ("Pinterest", 85),
    ("Airbnb", 85),
    ("Netflix", 85),
    ("Spotify", 85),
    ("Instacart", 85),
    ("Anthropic News", 90),
    ("LangChain", 90),
    ("LlamaIndex", 90),
    # 行业媒体
    ("Digital Commerce 360", 70),
    ("Retail Dive", 70),
    ("Retail TouchPoints", 70),
    ("Chain Store Age", 65),
    ("Practical Ecommerce", 65),
    ("Ecommerce Times", 65),
    ("Internet Retailer", 65),
    ("TechCrunch", 60),
    ("VentureBeat", 60),
    ("36Kr", 60),
    ("InfoQ", 60),
    ("亿邦动力", 60),
    ("雨果跨境", 60),
    ("电商报", 60),
    # 聚合器（最低）
    ("Google News", 20),
    ("AWS What's New", 40),  # 官方但太宽泛，比 blog 权威性低
]


def source_score(source_name):
    """返回来源的权威性评分。匹配采用 substring；若无匹配返回 50（默认中等）"""
    for keyword, score in SOURCE_AUTHORITY:
        if keyword.lower() in (source_name or "").lower():
            return score
    return 50


# 标题里常见的"来源后缀"——通常由 Google News 转载时追加，例如：
#   "How Decathlon runs demand forecasting at scale with Chronos-2 - Amazon Web Services (AWS)"
# 去掉后缀能让主源和转载源匹配到同一个 key
_SUFFIX_STRIP_PATTERN = re.compile(
    r"\s*[-|–—]\s*("
    r"amazon web services.*|aws.*|"
    r"reuters|bloomberg\.?com|bloomberg|"
    r"the business of fashion|impakter|yahoo|"
    r"forbes|cnbc|financial times|ft\.com|wsj|"
    r"techcrunch|venturebeat|the verge|"
    r"engadget|wired|axios|"
    r".*news$|"
    r"digitalcommerce360|digital commerce 360|"
    r".*\.com"
    r")\s*$",
    flags=re.IGNORECASE,
)


def normalize_title(title):
    """标题标准化，用于跨源匹配

    规则：
    1. 剥掉常见"- Source Name"后缀（Google News 转载习惯）
    2. 剥掉标题里的 "TOP" 之类前缀（如果 caller 传入了 mailer 处理过的标题）
    3. 小写、去标点、压缩空白
    """
    if not title:
        return ""
    t = title.strip()
    # 反复剥离后缀，最多 2 次（应对 "Foo - Bar - AWS" 之类）
    for _ in range(2):
        new_t = _SUFFIX_STRIP_PATTERN.sub("", t).strip()
        if new_t == t:
            break
        t = new_t
    # 小写并去掉所有非字母数字字符（保留 CJK）
    t = t.lower()
    t = re.sub(r"[^\w一-鿿]+", "", t, flags=re.UNICODE)
    return t


def dedupe_cross_source(items):
    """跨源去重

    Args:
        items: crawler 抓取到的原始 items 列表

    Returns:
        去重后的 items 列表。每个 item 新增 `related_sources` 字段：
        [{"name": ..., "url": ...}, ...]，包含所有报道该事件的**其他**来源
        （不含主源本身）。
    """
    if not items:
        return items

    # 按标准化标题分组
    groups = defaultdict(list)
    for item in items:
        key = normalize_title(item.get("title", ""))
        if not key:
            # 标题标准化后为空——保留但不参与去重
            key = f"__unique__{id(item)}"
        groups[key].append(item)

    deduped = []
    merged_count = 0

    for key, group in groups.items():
        if len(group) == 1:
            group[0].setdefault("related_sources", [])
            deduped.append(group[0])
            continue

        # 选主源：权威性最高的；平手时保留最长的 summary
        def sort_key(it):
            return (
                source_score(it.get("source", "")),
                len(it.get("summary", "") or ""),
            )
        group.sort(key=sort_key, reverse=True)
        primary = group[0]
        others = group[1:]

        primary["related_sources"] = [
            {"name": o.get("source", ""), "url": o.get("link", "")}
            for o in others
            if o.get("source")
        ]
        deduped.append(primary)
        merged_count += len(others)

    if merged_count:
        print(f"  [跨源去重] 合并 {merged_count} 条重复报道 ({len(items)} → {len(deduped)})")

    return deduped


def dedupe_top_news(top_news):
    """TOP 榜内部去重——相同事件保留 score 更高的那条。

    Args:
        top_news: analyzer 输出的 top_news 列表（每项含 id / title / score...）

    Returns:
        去重后列表，顺序保持稳定（按输入的先后）。
    """
    if not top_news:
        return top_news

    best_by_key = {}
    order = []
    for item in top_news:
        key = normalize_title(item.get("title", ""))
        if not key:
            key = f"__unique__{id(item)}"
        score = item.get("score", item.get("ai_score", 0)) or 0
        prev = best_by_key.get(key)
        if prev is None or score > (prev.get("score", prev.get("ai_score", 0)) or 0):
            best_by_key[key] = item
            if key not in order:
                order.append(key)

    return [best_by_key[k] for k in order]
