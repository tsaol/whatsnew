"""AI 新闻分析模块 - 使用 LangGraph + Bedrock Claude 4.5"""
import json
from typing import List, Dict, TypedDict
from datetime import datetime

from langchain_aws import ChatBedrock
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage


class AnalysisState(TypedDict):
    """分析状态定义"""
    news_items: List[Dict]                          # 原始新闻列表
    categorized: Dict                               # 分类后的新闻 {category: [news]}
    scored: List[Dict]                              # 评分后的新闻
    trends: List[str]                               # 识别的趋势
    top_news: List[Dict]                            # TOP 新闻
    summary: str                                     # 最终总结
    metadata: Dict                                   # 元数据
    commentary: str                                  # 开篇评论
    clusters: List[Dict]                            # 热点聚类
    extracted_data: List[Dict]                      # 提取的关键数据
    # 新增字段
    news_labels: Dict[str, str]                     # 新闻标签 {news_id: "重磅"|"独家"|"融资"...}
    paper_analysis: List[Dict]                      # 论文深度分析
    spotlight: Dict                                  # 深度专题
    market_pulse: Dict                              # 市场脉搏（情绪+数据）
    weekly_outlook: str                             # 下周展望
    one_liners: Dict[str, str]                      # 一句话速读 {news_id: "精华"}
    action_items: List[Dict]                        # 行动建议


class NewsAnalyzerAgent:
    """基于 LangGraph 的新闻分析 Agent"""

    def __init__(self, aws_region='us-west-2'):
        """初始化"""
        self.aws_region = aws_region

        # 初始化 Claude Sonnet 4.5
        self.llm = ChatBedrock(
            model_id="global.anthropic.claude-sonnet-4-5-20250929-v1:0",
            region_name=aws_region,
            model_kwargs={
                "temperature": 0.3,
                "max_tokens": 4096
            }
        )

        # 构建工作流
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """构建 LangGraph 工作流 - 优化版 (12节点)"""
        workflow = StateGraph(AnalysisState)

        # 添加节点 (优化: 删除 market_pulse, extract_data; 合并 label_news + one_liners)
        workflow.add_node("categorize", self._categorize_news)
        workflow.add_node("filter", self._filter_news)
        workflow.add_node("score", self._score_news)
        workflow.add_node("enhance_translate", self._enhance_and_translate)  # 合并节点
        workflow.add_node("label_and_oneliner", self._label_and_oneliner)    # 合并节点
        workflow.add_node("find_trends", self._find_trends)
        workflow.add_node("cluster_news", self._cluster_news)
        workflow.add_node("analyze_papers", self._analyze_papers)
        workflow.add_node("summarize", self._summarize)
        workflow.add_node("spotlight", self._generate_spotlight)
        workflow.add_node("action_items", self._generate_action_items)
        workflow.add_node("commentary", self._generate_commentary)

        # 定义边（流程）- 12节点工作流
        workflow.set_entry_point("categorize")
        workflow.add_edge("categorize", "filter")
        workflow.add_edge("filter", "score")
        workflow.add_edge("score", "enhance_translate")
        workflow.add_edge("enhance_translate", "label_and_oneliner")
        workflow.add_edge("label_and_oneliner", "find_trends")
        workflow.add_edge("find_trends", "cluster_news")
        workflow.add_edge("cluster_news", "analyze_papers")
        workflow.add_edge("analyze_papers", "summarize")
        workflow.add_edge("summarize", "spotlight")
        workflow.add_edge("spotlight", "action_items")
        workflow.add_edge("action_items", "commentary")
        workflow.add_edge("commentary", END)

        return workflow.compile()

    # 内容分类定义（为 Agentic AI 专家优化）
    CONTENT_CATEGORIES = {
        "Agent 专项": {
            "icon": "A",
            "description": "Agent 框架、MCP、Multi-Agent、Tool Use",
            "priority": 1
        },
        "技术深度": {
            "icon": "T",
            "description": "LLM、RAG、模型优化、算法创新",
            "priority": 2
        },
        "AWS 聚焦": {
            "icon": "W",
            "description": "Bedrock、SageMaker、AWS AI 服务",
            "priority": 3
        },
        "行业动态": {
            "icon": "I",
            "description": "企业落地、应用案例、市场趋势",
            "priority": 4
        }
    }

    def _categorize_news(self, state: AnalysisState) -> Dict:
        """节点1: 分类新闻 - 为 Agentic AI 专家优化"""
        print("  [Agent] 正在分类新闻...")

        news_items = state["news_items"]

        # 准备新闻文本
        news_text = "\n\n".join([
            f"ID: {i}\n标题: {item['title']}\n来源: {item['source']}\n"
            f"摘要: {item['summary'][:200]}"
            for i, item in enumerate(news_items)
        ])

        # 调用 LLM 分类 - 使用新的分类体系
        messages = [
            SystemMessage(content="""
你是 Agentic AI 领域专家。将新闻分类到以下 4 个类别（每条新闻只能属于一个类别）：

**Agent 专项**（最高优先级）:
- Agent/Agentic AI 框架更新（LangChain、LlamaIndex、CrewAI、AutoGen）
- MCP (Model Context Protocol) 相关
- Multi-Agent 系统、Agent 编排
- Tool Use / Function Calling
- Agent 安全、可观测性
- 自主代理、Agent 工作流

**技术深度**:
- LLM 模型更新、推理优化
- RAG 技术、向量数据库
- 文档处理、数据解析
- Prompt 工程、Fine-tuning
- 算法研究、论文解读

**AWS 聚焦**:
- 来源为 AWS 博客的所有内容（AWS News Blog、AWS AI Blog、AWS ML Blog 等）
- Amazon Bedrock、Bedrock Agents、SageMaker
- AWS 服务更新、AWS Weekly Roundup

**行业动态**:
- 企业 AI 落地案例
- 产品发布、市场趋势
- 其他 AI 相关新闻

**分类原则**（严格按顺序判断）：
1. **来源是 AWS 的** → 归 "AWS 聚焦"（最高优先，无论内容是什么）
2. 涉及 Agent/Agentic/MCP/Tool Use → 归 "Agent 专项"
3. 技术性强（LLM/RAG/算法） → 归 "技术深度"
4. 其余 → 归 "行业动态"

返回 JSON 格式: {"Agent 专项": ["0", "2"], "技术深度": ["1", "3"], ...}
只返回JSON，不要其他文字。
            """),
            HumanMessage(content=f"分类这些新闻:\n\n{news_text}")
        ]

        response = self.llm.invoke(messages)

        try:
            content = response.content.strip()
            start_idx = content.find('{')
            end_idx = content.rfind('}')
            if start_idx != -1 and end_idx != -1:
                json_str = content[start_idx:end_idx+1]
                categorized = json.loads(json_str)
            else:
                raise ValueError("未找到 JSON")
        except:
            # 如果解析失败，默认分类
            categorized = {"行业动态": [str(i) for i in range(len(news_items))]}

        return {"categorized": categorized}

    def _filter_news(self, state: AnalysisState) -> Dict:
        """节点2: 过滤新闻 - 只保留与 AI/计算机技术相关的内容"""
        print("  [Agent] 正在过滤新闻相关性...")

        news_items = state["news_items"]
        categorized = state.get("categorized", {})

        # 受保护的来源（不过滤，直接保留）
        protected_sources = {
            # 技术社区
            "Hacker News", "GitHub Trending", "GitHub Blog",
            "Dev.to", "Rust Blog", "Python Blog",
            # AWS 来源（对 AWS SA 必看）
            "AWS News Blog", "AWS AI Blog", "AWS Machine Learning Blog",
            "AWS Compute Blog", "AWS Developer Blog",
            # Agent 框架（核心内容）
            "LangChain Blog", "LlamaIndex Blog", "CrewAI Blog",
            "Semantic Kernel Blog", "Anthropic News",
        }

        # 准备新闻文本（只过滤非受保护来源）
        items_to_check = []
        protected_items = []

        for i, item in enumerate(news_items):
            if item['source'] in protected_sources:
                protected_items.append(i)
            else:
                items_to_check.append(i)

        if not items_to_check:
            print(f"    全部为受保护来源，跳过过滤")
            return {"news_items": news_items}

        # 准备需要检查的新闻
        news_text = "\n\n".join([
            f"ID: {i}\n标题: {news_items[i]['title']}\n来源: {news_items[i]['source']}\n"
            f"摘要: {news_items[i]['summary'][:150]}"
            for i in items_to_check
        ])

        # 调用 LLM 判断相关性
        messages = [
            SystemMessage(content="""
你是 AI/GenAI/Agentic AI 新闻过滤专家。严格筛选与这些核心主题相关的内容。

**必须保留的内容**：
- GenAI/LLM：大模型、Prompt工程、RAG、Fine-tuning、模型推理
- Agentic AI：AI Agent、自主代理、Multi-Agent、Agent框架（LangChain、AutoGPT等）
- AI 基础设施：模型训练、部署、MLOps、向量数据库
- 云服务 AI：AWS Bedrock、Azure OpenAI、GCP Vertex AI
- AI 工具链：Hugging Face、LangChain、LlamaIndex、Agent开发工具
- AI 研究：最新论文、算法创新、模型架构

**严格过滤的内容**：
- 通用软件开发（与AI无关的编程）
- 纯前端/后端技术（无AI组件）
- 游戏开发（除非涉及AI技术）
- 硬件产品、消费电子
- 购物促销、营销内容
- 非技术新闻

**判断标准**：如果新闻不明确涉及 AI、GenAI、Agent 或云AI服务，则过滤掉。

返回 JSON 格式：{"relevant_ids": ["0", "2", "5"], "filtered_ids": ["1", "3", "4"]}
只返回JSON，不要其他文字。
            """),
            HumanMessage(content=f"过滤这些新闻:\n\n{news_text}")
        ]

        try:
            response = self.llm.invoke(messages)

            # 提取 JSON
            content = response.content.strip()
            start_idx = content.find('{')
            end_idx = content.rfind('}')

            if start_idx != -1 and end_idx != -1:
                json_str = content[start_idx:end_idx+1]
                filter_result = json.loads(json_str)
                relevant_ids = set(int(id) for id in filter_result.get('relevant_ids', []))
            else:
                # 如果解析失败，保留所有
                relevant_ids = set(items_to_check)

        except Exception as e:
            print(f"    过滤失败: {e}，保留所有新闻")
            relevant_ids = set(items_to_check)

        # 合并技术社区新闻 + 相关新闻
        keep_ids = set(protected_items) | relevant_ids
        filtered_items = [news_items[i] for i in sorted(keep_ids)]

        filtered_count = len(news_items) - len(filtered_items)
        print(f"    过滤掉 {filtered_count} 条不相关新闻，保留 {len(filtered_items)} 条")

        return {"news_items": filtered_items}

    # 来源到分类的强制映射（仅对明确的来源强制分类）
    SOURCE_CATEGORY_MAP = {
        # AWS 来源 → AWS 聚焦（强制）
        'AWS News Blog': 'AWS 聚焦',
        'AWS AI Blog': 'AWS 聚焦',
        'AWS Machine Learning Blog': 'AWS 聚焦',
        'AWS Compute Blog': 'AWS 聚焦',
        'AWS Developer Blog': 'AWS 聚焦',
        # 纯 Agent 框架来源 → Agent 专项（强制）
        'CrewAI Blog': 'Agent 专项',
        'Semantic Kernel Blog': 'Agent 专项',
        # Anthropic (MCP 相关) → Agent 专项（强制）
        'Anthropic News': 'Agent 专项',
        # 注意：LangChain/LlamaIndex 不强制，让 AI 根据内容判断
        # 因为它们有 Agent 内容也有 RAG/技术深度内容
    }

    # 基于标题关键词的分类规则（用于非强制来源）
    TITLE_CATEGORY_KEYWORDS = {
        'Agent 专项': ['agent', 'agentic', 'multi-agent', 'mcp', 'tool use', 'function call'],
        '技术深度': ['rag', 'retrieval', 'embedding', 'vector', 'llm', 'fine-tun', 'prompt', 'ocr', 'parse', 'extract'],
        'AWS 聚焦': ['aws', 'bedrock', 'sagemaker', 'amazon'],
    }

    def _score_news(self, state: AnalysisState) -> Dict:
        """节点3: 评估新闻重要性 - 聚焦 Agentic AI，并分配内容类型"""
        print("  [Agent] 正在评估新闻重要性...")

        news_items = state["news_items"]
        categorized = state.get("categorized", {})

        # 构建 ID -> category 映射（结合 AI 分类和强制映射）
        id_to_category = {}
        for category, ids in categorized.items():
            for id_str in ids:
                id_to_category[int(id_str)] = category

        # 对特定来源强制覆盖分类，或基于标题关键词分类
        for i, item in enumerate(news_items):
            source = item.get('source', '')
            title_lower = item.get('title', '').lower()

            # 1. 先检查强制来源映射
            if source in self.SOURCE_CATEGORY_MAP:
                id_to_category[i] = self.SOURCE_CATEGORY_MAP[source]
            else:
                # 2. 基于标题关键词分类（按优先级：Agent > 技术深度 > AWS）
                matched_category = None
                for category in ['Agent 专项', '技术深度', 'AWS 聚焦']:
                    keywords = self.TITLE_CATEGORY_KEYWORDS.get(category, [])
                    if any(kw in title_lower for kw in keywords):
                        matched_category = category
                        break

                if matched_category:
                    id_to_category[i] = matched_category
                # 否则保留 AI 的分类结果

        # 准备新闻文本
        news_text = "\n\n".join([
            f"ID: {i}\n标题: {item['title']}\n来源: {item['source']}\n"
            f"摘要: {item['summary'][:200]}"
            for i, item in enumerate(news_items)
        ])

        # 调用 LLM 评分 - 优化为更有区分度的评分标准
        messages = [
            SystemMessage(content="""
你是 Agentic AI 领域专家，为 AWS SA 评估新闻价值。严格按以下标准评分（1-10分）。

**评分标准（必须严格区分，不要都评5分）**：

9-10分 [必看]：
- Agent/Agentic AI 框架重大更新（LangChain、LlamaIndex、CrewAI、AutoGen）
- MCP (Model Context Protocol) 相关进展
- Claude/GPT 的 Agent 能力重大更新
- AWS Bedrock Agents 新功能
- 重大融资（>$500M）或重要公司收购

7-8分 [重要]：
- RAG 技术重要进展
- Tool Use / Function Calling 更新
- Agent 开发工具和框架更新
- LLM 推理优化、新模型发布
- 企业级 Agent 落地案例
- 大额融资（$100M-$500M）

5-6分 [一般]：
- 通用 LLM 模型更新
- 云服务常规更新
- 通用 AI 研究进展
- 中等融资（$20M-$100M）

3-4分 [低价值]：
- 人事变动、小额融资（<$20M）
- 非技术内容
- 过于宽泛的综述

1-2分 [不相关]：
- 与 AI/Agent 无关的内容
- 营销促销内容

**重要**：评分要有区分度！如果10条新闻，应该有2-3条高分(7+)，3-4条中分(5-6)，其余低分。

返回 JSON: [{"id": "0", "score": 8, "reason": "LangChain Agent重大更新，提升多Agent协作能力"}, ...]
reason 字段必填，说明评分理由（15-30字）。
只返回JSON数组。
            """),
            HumanMessage(content=f"严格评估这些新闻（注意区分度）:\n\n{news_text}")
        ]

        response = self.llm.invoke(messages)

        try:
            # 尝试提取 JSON
            content = response.content.strip()
            start_idx = content.find('[')
            end_idx = content.rfind(']')

            if start_idx != -1 and end_idx != -1:
                json_str = content[start_idx:end_idx+1]
                scored = json.loads(json_str)
            else:
                raise ValueError("未找到有效 JSON")

            # 合并评分到原新闻，并附上 category
            scored_news = []
            for item in scored:
                news_id = int(item['id'])
                if news_id < len(news_items):
                    news_copy = news_items[news_id].copy()
                    news_copy['ai_score'] = item['score']
                    news_copy['ai_reason'] = item.get('reason', '')
                    # 附上内容类型
                    news_copy['category'] = id_to_category.get(news_id, '行业动态')
                    scored_news.append(news_copy)

            # 验证评分分布，如果全是5分则警告
            scores = [n['ai_score'] for n in scored_news]
            if len(set(scores)) == 1:
                print(f"    [警告] 评分无区分度，全部为 {scores[0]} 分")

        except Exception as e:
            print(f"    评分解析失败: {e}")
            # 如果解析失败，默认评分
            scored_news = [
                {**item, 'ai_score': 5, 'ai_reason': '', 'category': id_to_category.get(i, '行业动态')}
                for i, item in enumerate(news_items)
            ]

        return {"scored": scored_news}

    def _enhance_summary(self, state: AnalysisState) -> Dict:
        """节点4: 增强摘要 - 为简单的摘要生成更详细的描述"""
        print("  [Agent] 正在增强简单摘要...")

        scored = state.get("scored", [])

        # 识别需要增强的新闻（摘要太简单或重复标题）
        to_enhance = []
        for idx, item in enumerate(scored):
            summary = item.get('summary', '')
            title = item.get('title', '')

            # 判断是否需要增强
            needs_enhance = (
                len(summary) < 50 or  # 太短
                summary == title or  # 重复标题
                summary.startswith(title[:20]) or  # 摘要就是标题的开头
                '...' == summary.strip()  # 只有省略号
            )

            if needs_enhance:
                to_enhance.append({
                    'idx': idx,
                    'title': title,
                    'source': item.get('source', ''),
                    'link': item.get('link', '')
                })

        if not to_enhance:
            print("    所有摘要都足够详细，跳过增强")
            return {"scored": scored}

        print(f"    需要增强 {len(to_enhance)} 条摘要")

        # 批量增强
        batch_size = 10
        enhanced_news = scored.copy()

        for batch_start in range(0, len(to_enhance), batch_size):
            batch = to_enhance[batch_start:batch_start + batch_size]
            print(f"    正在增强第 {batch_start+1}-{batch_start+len(batch)} 条...")

            enhancement_text = "\n\n".join([
                f"ID: {item['idx']}\n标题: {item['title']}\n来源: {item['source']}\nURL: {item['link']}"
                for item in batch
            ])

            messages = [
                SystemMessage(content="""
你是AI/科技新闻摘要生成专家。为每条新闻生成简洁、信息丰富的描述（80-150字）。

针对不同类型：
- GitHub 项目：描述项目功能、技术栈、应用场景
- 技术博客：概括核心观点、技术要点、适用场景
- 新闻报道：说明事件背景、影响、技术细节

要求：
- 具体、信息密度高，避免泛泛而谈
- 突出技术价值和创新点
- 面向技术读者，使用专业术语
- 80-150字长度

返回 JSON 格式：[{"id": "0", "enhanced_summary": "项目描述..."}, ...]
只返回JSON数组，不要其他文字。
                """),
                HumanMessage(content=f"为这些新闻生成摘要:\n\n{enhancement_text}")
            ]

            try:
                response = self.llm.invoke(messages)

                # 提取 JSON
                content = response.content.strip()
                content = content.replace('\u201c', '"').replace('\u201d', '"')
                content = content.replace('\u2018', "'").replace('\u2019', "'")

                start_idx = content.find('[')
                end_idx = content.rfind(']')

                if start_idx != -1 and end_idx != -1:
                    json_str = content[start_idx:end_idx+1]
                    enhancements = json.loads(json_str)

                    # 合并增强结果
                    for enh in enhancements:
                        idx = int(enh['id'])
                        if idx < len(enhanced_news):
                            enhanced_news[idx]['summary'] = enh.get('enhanced_summary', enhanced_news[idx]['summary'])

                    print(f"      成功增强 {len(enhancements)} 条")
                else:
                    print(f"      批次增强失败: 未找到有效JSON")

            except Exception as e:
                print(f"      批次增强失败: {e}")
                continue

        return {"scored": enhanced_news}

    def _translate_news(self, state: AnalysisState) -> Dict:
        """节点5: 翻译英文新闻"""
        print("  [Agent] 正在翻译英文新闻...")

        scored = state.get("scored", [])

        # 检测哪些需要翻译（简单检测：是否包含大量英文字符）
        def needs_translation(text):
            if not text:
                return False
            # 统计英文字符占比
            english_chars = sum(1 for c in text if c.isascii() and c.isalpha())
            total_chars = len([c for c in text if c.isalpha()])
            return total_chars > 0 and english_chars / total_chars > 0.5

        # 收集需要翻译的新闻（分开检测标题和摘要）
        to_translate = []
        for idx, item in enumerate(scored):
            title_needs = needs_translation(item['title'])
            summary_needs = needs_translation(item['summary'])

            if title_needs or summary_needs:
                to_translate.append({
                    'idx': idx,
                    'title': item['title'] if title_needs else None,
                    'summary': item['summary'][:300] if summary_needs else None,
                    'title_needs': title_needs,
                    'summary_needs': summary_needs
                })
                # 如果摘要已经是中文，直接复制到 summary_zh
                if not summary_needs and item['summary']:
                    scored[idx]['summary_zh'] = item['summary']
                # 如果标题已经是中文，直接复制到 title_zh
                if not title_needs and item['title']:
                    scored[idx]['title_zh'] = item['title']

        if not to_translate:
            print("    无需翻译，全部为中文")
            return {"scored": scored}

        # 统计需要翻译的标题和摘要数量
        titles_to_trans = sum(1 for item in to_translate if item['title'])
        summaries_to_trans = sum(1 for item in to_translate if item['summary'])
        print(f"    需要翻译 {len(to_translate)} 条新闻 (标题: {titles_to_trans}, 摘要: {summaries_to_trans})")

        # 分批翻译所有新闻
        batch_size = 10
        translated_news = scored.copy()

        for batch_start in range(0, len(to_translate), batch_size):
            batch = to_translate[batch_start:batch_start + batch_size]
            print(f"    正在翻译第 {batch_start+1}-{batch_start+len(batch)} 条...")

            # 只发送需要翻译的内容
            translation_text = "\n\n".join([
                f"ID: {item['idx']}" +
                (f"\n标题: {item['title']}" if item['title'] else "") +
                (f"\n摘要: {item['summary']}" if item['summary'] else "")
                for item in batch
            ])

            messages = [
                SystemMessage(content="""
你是专业的科技新闻翻译专家。将英文新闻翻译成简洁、准确的中文。

要求：
- 保持技术术语的准确性（如AI、API、LLM等可保留英文）
- 标题翻译要简洁有力
- 摘要翻译要流畅自然
- **重要：翻译中如需引用词语，使用书名号《》或单引号'，不要使用双引号"**
- 返回 JSON 格式：[{"id": "0", "title_zh": "翻译后的标题", "summary_zh": "翻译后的摘要"}, ...]
- 如果某条新闻只有标题或只有摘要，只返回对应的翻译字段
- 确保 JSON 格式正确，所有字符串都用双引号包围

只返回有效的JSON数组，不要其他文字。

示例：
- 正确：使用工程抗体的临床试验显示'功能性治愈'可能指日可待
- 错误：使用工程抗体的临床试验显示"功能性治愈"可能指日可待
                """),
                HumanMessage(content=f"翻译这些新闻:\n\n{translation_text}")
            ]

            try:
                response = self.llm.invoke(messages)

                # 尝试提取 JSON（有时 LLM 会在前后添加文字）
                content = response.content.strip()

                # 替换中文引号为英文引号（LLM 有时会在翻译中使用中文引号）
                # 使用 Unicode 码点明确指定
                content = content.replace('\u201c', '"').replace('\u201d', '"')  # " "
                content = content.replace('\u2018', "'").replace('\u2019', "'")  # ' '

                # 查找 JSON 数组
                start_idx = content.find('[')
                end_idx = content.rfind(']')

                if start_idx != -1 and end_idx != -1:
                    json_str = content[start_idx:end_idx+1]
                    translations = json.loads(json_str)
                else:
                    raise ValueError("未找到有效的 JSON 数组")

                # 合并翻译结果到当前批次（只更新 LLM 返回的字段）
                for trans in translations:
                    idx = int(trans['id'])
                    if idx < len(translated_news):
                        if 'title_zh' in trans and trans['title_zh']:
                            translated_news[idx]['title_zh'] = trans['title_zh']
                        if 'summary_zh' in trans and trans['summary_zh']:
                            translated_news[idx]['summary_zh'] = trans['summary_zh']

                print(f"      成功翻译 {len(translations)} 条")

            except Exception as e:
                print(f"      批次翻译失败: {e}")
                continue

        return {"scored": translated_news}

    def _enhance_and_translate(self, state: AnalysisState) -> Dict:
        """合并节点: 增强摘要 + 翻译（减少 LLM 调用）"""
        print("  [Agent] 正在增强摘要并翻译...")

        scored = state.get("scored", [])
        if not scored:
            return {"scored": []}

        # 检测是否需要翻译
        def needs_translation(text):
            if not text:
                return False
            english_chars = sum(1 for c in text if c.isascii() and c.isalpha())
            total_chars = len([c for c in text if c.isalpha()])
            return total_chars > 0 and english_chars / total_chars > 0.5

        # 准备待处理的新闻
        to_process = []
        for idx, item in enumerate(scored):
            summary = item.get('summary', '')
            title = item.get('title', '')
            title_needs_trans = needs_translation(title)
            summary_needs_trans = needs_translation(summary)
            needs_enhance = len(summary) < 50 or summary == title

            to_process.append({
                'idx': idx,
                'title': title,
                'summary': summary[:300],
                'source': item.get('source', ''),
                'title_needs_trans': title_needs_trans,
                'summary_needs_trans': summary_needs_trans,
                'needs_enhance': needs_enhance
            })

        # 分批处理
        batch_size = 10
        processed_news = [item.copy() for item in scored]

        for batch_start in range(0, len(to_process), batch_size):
            batch = to_process[batch_start:batch_start + batch_size]
            print(f"    处理第 {batch_start+1}-{batch_start+len(batch)} 条...")

            news_text = "\n\n".join([
                f"ID: {item['idx']}\n标题: {item['title']}\n摘要: {item['summary']}\n来源: {item['source']}"
                for item in batch
            ])

            messages = [
                SystemMessage(content="""你是科技新闻翻译专家。对每条新闻翻译标题和摘要。

**术语处理规则**：
- 保留英文: LangChain, Claude, GPT, Gemini, Bedrock, RAG, MCP, API, SDK
- 翻译为中文: Agent→智能体, Prompt→提示词, Fine-tune→微调, Embedding→嵌入
- 公司名保留英文: OpenAI, Anthropic, Google, Meta, AWS

**摘要要求**：
- 50-80字，信息密集
- 如果原摘要太短或重复标题，基于标题扩写

返回 JSON 数组:
[{"id": "0", "title_zh": "中文标题", "summary_zh": "中文摘要"}, ...]
只返回JSON数组。"""),
                HumanMessage(content=f"处理这些新闻:\n\n{news_text}")
            ]

            try:
                response = self.llm.invoke(messages)
                content = response.content.strip()
                start_idx = content.find('[')
                end_idx = content.rfind(']')

                if start_idx != -1 and end_idx != -1:
                    results = json.loads(content[start_idx:end_idx+1])
                    for item in results:
                        idx = int(item['id'])
                        if idx < len(processed_news):
                            if item.get('title_zh'):
                                processed_news[idx]['title_zh'] = item['title_zh']
                            if item.get('summary_zh'):
                                processed_news[idx]['summary_zh'] = item['summary_zh']
                                # 如果原摘要太短，也更新原摘要
                                if len(processed_news[idx].get('summary', '')) < 50:
                                    processed_news[idx]['summary'] = item['summary_zh']
                    print(f"      成功处理 {len(results)} 条")
            except Exception as e:
                print(f"      批次处理失败: {e}")
                continue

        return {"scored": processed_news}

    def _label_and_oneliner(self, state: AnalysisState) -> Dict:
        """合并节点: 打标签 + 生成一句话速读"""
        print("  [Agent] 正在打标签并生成速读...")

        scored = state.get("scored", [])
        if not scored:
            return {"news_labels": {}, "one_liners": {}}

        # 准备新闻文本
        news_text = "\n".join([
            f"ID: {i} | {item.get('title_zh', item['title'])} | 来源: {item.get('source', '')} | 评分: {item.get('ai_score', 5)}"
            for i, item in enumerate(scored[:30])
        ])

        messages = [
            SystemMessage(content="""你是新闻编辑专家。为每条新闻完成两个任务：

**任务1: 打标签**（只给20-30%的重要新闻打标签，宁缺毋滥）
可用标签(仅5种):
- 重磅: 重大事件、里程碑发布、行业变革
- 融资: 融资、估值、收购（金额>$50M才标）
- 发布: 新产品、新版本、新功能
- 开源: 开源项目、代码发布
- 研究: 学术论文、技术研究

**任务2: 一句话速读**（必须，每条都要）
- 12-20字，必须包含具体的产品/项目/公司名称
- 有数据就必须体现（版本号、star数、性能提升%、融资金额）
- 格式: [主体名称] + [做了什么] + [关键数据/亮点]
- 禁止: 空洞描述如"性能提升"、"全面升级"、"重大突破"

正确示例:
- "Claude Opus 4.6发布，推理准确率提升23%"
- "LangChain 0.3支持多Agent编排"
- "ClawWork开源3天获2.5k stars"
- "Anthropic融资$2B估值$60B"

错误示例（禁止）:
- "Agent开发效率提升" ❌ 缺少主体
- "性能全面提升" ❌ 太空洞
- "重大突破" ❌ 没有具体信息

返回 JSON:
{
  "labels": {"0": "重磅", "5": "融资"},
  "oneliners": {"0": "一句话速读", "1": "一句话速读", ...}
}
只返回JSON。"""),
            HumanMessage(content=f"处理这些新闻:\n\n{news_text}")
        ]

        try:
            response = self.llm.invoke(messages)
            content = response.content.strip()
            start_idx = content.find('{')
            end_idx = content.rfind('}')

            if start_idx != -1 and end_idx != -1:
                result = json.loads(content[start_idx:end_idx+1])
                news_labels = result.get('labels', {})
                one_liners = result.get('oneliners', {})
            else:
                news_labels, one_liners = {}, {}
        except Exception as e:
            print(f"    处理失败: {e}")
            news_labels, one_liners = {}, {}

        print(f"    标记 {len(news_labels)} 条，生成 {len(one_liners)} 条速读")
        return {"news_labels": news_labels, "one_liners": one_liners}

    def _find_trends(self, state: AnalysisState) -> Dict:
        """节点6: 识别趋势 - 聚焦 Agentic AI"""
        print("  [Agent] 正在识别趋势...")

        scored = state.get("scored", [])

        # 使用所有新闻（不仅是高分），让 LLM 自己判断趋势
        if not scored:
            return {"trends": []}

        news_text = "\n".join([
            f"- {item['title']} (评分: {item.get('ai_score', 'N/A')}, 来源: {item.get('source', '')})"
            for item in scored[:15]
        ])

        # 调用 LLM 识别趋势
        messages = [
            SystemMessage(content="""你是 AI 行业趋势分析专家。基于今日新闻，识别 2-4 个值得关注的趋势。

**可关注方向**（不限于此）：
- Agent/Agentic AI: 框架、Multi-Agent、MCP、Tool Use
- LLM 进展: 新模型、推理优化、长上下文
- 多模态: 图像、视频、语音
- AI 基础设施: 云服务、部署、MLOps
- 行业应用: 代码生成、企业落地

**要求**：
- 每个趋势 10-18 字，具体有洞察
- 至少返回 2 个趋势（即使不明显也要提炼）
- 优先 Agent 相关，但不强制

示例：
["MCP协议获主流框架支持", "多模态Agent进入实用阶段", "代码生成工具竞争白热化"]

返回 JSON 格式: ["趋势1", "趋势2", ...]
只返回JSON数组。"""),
            HumanMessage(content=f"基于这些新闻识别 AI 趋势:\n\n{news_text}")
        ]

        response = self.llm.invoke(messages)

        try:
            content = response.content.strip()
            start_idx = content.find('[')
            end_idx = content.rfind(']')

            if start_idx != -1 and end_idx != -1:
                json_str = content[start_idx:end_idx+1]
                trends = json.loads(json_str)
            else:
                trends = []
        except:
            trends = []

        return {"trends": trends}

    def _summarize(self, state: AnalysisState) -> Dict:
        """节点7: 生成总结"""
        print("  [Agent] 正在生成总结...")

        scored = state.get("scored", [])
        trends = state.get("trends", [])
        categorized = state.get("categorized", {})

        # 选出 TOP 5 新闻
        sorted_news = sorted(scored, key=lambda x: x.get('ai_score', 0), reverse=True)
        top_news = sorted_news[:5]

        # 准备上下文
        context = f"""
总计新闻: {len(scored)} 条
分类分布: {json.dumps(categorized, ensure_ascii=False)}

识别的趋势:
{chr(10).join(f'- {t}' for t in trends)}

TOP 5 新闻:
{chr(10).join(f'{i+1}. {n["title"]} (评分: {n.get("ai_score", "N/A")})' for i, n in enumerate(top_news))}
        """

        # 调用 LLM 生成总结
        messages = [
            SystemMessage(content="""
你是AI/科技领域资深分析师。基于今日新闻分析，生成精炼的 bullet points 总结。

格式要求：
- 生成 3-5 个要点
- 每个要点一句话（20-35字）
- 突出技术价值和创新点
- 使用 "- " 开头（破折号+空格）

写作要求：
- 专业、精准、高信息密度
- 避免废话和套话
- 聚焦技术本质和具体事件
- 面向AI/开发者受众

示例：
- Google发布Gemini Pro视觉API，支持图文混合推理，性能超越GPT-4V
- LangChain 0.1重构Agent架构，简化复杂工作流开发
- AWS推出Bedrock Agents托管服务，降低企业AI应用门槛
- GitHub引入AI代码审查功能，自动检测安全漏洞和性能问题

直接输出要点列表，不要其他文字。
            """),
            HumanMessage(content=f"基于以下分析生成总结:\n\n{context}")
        ]

        response = self.llm.invoke(messages)
        summary = response.content.strip()

        return {
            "top_news": top_news,
            "summary": summary,
            "metadata": {
                "total_news": len(scored),
                "analyzed_at": datetime.now().isoformat(),
                "avg_score": sum(n.get('ai_score', 0) for n in scored) / len(scored) if scored else 0
            }
        }

    def _label_news(self, state: AnalysisState) -> Dict:
        """节点: 为新闻打标签（重磅/独家/融资等）"""
        print("  [Agent] 正在为新闻打标签...")

        scored = state.get("scored", [])
        if not scored:
            return {"news_labels": {}}

        # 准备新闻文本
        news_text = "\n".join([
            f"ID: {i} | 标题: {item['title']} | 来源: {item.get('source', '')} | 评分: {item.get('ai_score', 5)}"
            for i, item in enumerate(scored[:30])
        ])

        messages = [
            SystemMessage(content="""
你是新闻编辑专家，为新闻打上醒目标签。

**可用标签**（只能选一个）：
- 重磅: 行业重大事件、里程碑式发布、影响深远
- 独家: 首发消息、独特视角、稀缺信息
- 融资: 融资、估值、收购、IPO相关
- 发布: 新产品、新版本、新功能发布
- 开源: 开源项目、代码发布
- 研究: 学术论文、研究报告
- 警示: 安全问题、风险警告
- 趋势: 行业趋势、市场变化

**规则**：
- 只给最值得标注的新闻打标签（约30-50%）
- 评分7+的新闻优先考虑"重磅"或"独家"
- 不是每条都需要标签

返回 JSON: {"0": "重磅", "3": "融资", "5": "开源", ...}
只返回JSON，没有标签的新闻不要包含。
            """),
            HumanMessage(content=f"为这些新闻打标签:\n\n{news_text}")
        ]

        try:
            response = self.llm.invoke(messages)
            content = response.content.strip()
            start_idx = content.find('{')
            end_idx = content.rfind('}')
            if start_idx != -1 and end_idx != -1:
                news_labels = json.loads(content[start_idx:end_idx+1])
            else:
                news_labels = {}
        except Exception as e:
            print(f"    标签生成失败: {e}")
            news_labels = {}

        print(f"    标记 {len(news_labels)} 条新闻")
        return {"news_labels": news_labels}

    def _analyze_papers(self, state: AnalysisState) -> Dict:
        """节点: 深度分析学术论文"""
        print("  [Agent] 正在分析学术论文...")

        scored = state.get("scored", [])
        # 筛选论文（来源包含 arXiv 或标题包含论文特征）
        papers = [item for item in scored if
                  'arxiv' in item.get('source', '').lower() or
                  'arxiv' in item.get('link', '').lower() or
                  'paper' in item.get('title', '').lower()]

        if not papers:
            print("    未发现论文")
            return {"paper_analysis": []}

        # 准备论文文本
        paper_text = "\n\n".join([
            f"ID: {i}\n标题: {p['title']}\n摘要: {p.get('summary', '')[:300]}\n链接: {p.get('link', '')}"
            for i, p in enumerate(papers[:10])
        ])

        messages = [
            SystemMessage(content="""你是AI研究专家，为工程师解读学术论文。

为每篇论文生成：
1. title_zh: 中文标题
2. domain: 领域(Agent/RAG/LLM/多模态/安全/其他)
3. difficulty: 难度(入门/进阶/专家)
4. contribution: 核心贡献（1句话，25字内）
5. takeaway: 工程师可以做什么（具体行动，如"可用于优化RAG召回"）

返回 JSON 数组:
[
  {
    "id": "0",
    "title_zh": "中文标题",
    "domain": "Agent",
    "difficulty": "进阶",
    "contribution": "提出了XXX方法解决YYY问题",
    "takeaway": "可用于优化多Agent协作的通信效率"
  }
]
只返回JSON数组。"""),
            HumanMessage(content=f"分析这些论文:\n\n{paper_text}")
        ]

        try:
            response = self.llm.invoke(messages)
            content = response.content.strip()
            start_idx = content.find('[')
            end_idx = content.rfind(']')
            if start_idx != -1 and end_idx != -1:
                analysis = json.loads(content[start_idx:end_idx+1])
                # 合并原始论文数据
                for item in analysis:
                    idx = int(item['id'])
                    if idx < len(papers):
                        item['original'] = papers[idx]
            else:
                analysis = []
        except Exception as e:
            print(f"    论文分析失败: {e}")
            analysis = []

        print(f"    分析 {len(analysis)} 篇论文")
        return {"paper_analysis": analysis}

    def _generate_spotlight(self, state: AnalysisState) -> Dict:
        """节点: 生成深度专题报道"""
        print("  [Agent] 正在生成深度专题...")

        clusters = state.get("clusters", [])
        top_news = state.get("top_news", [])
        scored = state.get("scored", [])

        if not clusters and not top_news:
            return {"spotlight": {}}

        # 选择最热门的主题作为专题
        context = ""
        if clusters:
            top_cluster = clusters[0]
            context = f"热点专题: {top_cluster.get('topic', '')}\n相关新闻: {len(top_cluster.get('news', []))}条"
        if top_news:
            context += f"\n\nTOP新闻:\n" + "\n".join([
                f"- {n['title']}" for n in top_news[:3]
            ])

        messages = [
            SystemMessage(content="""你是深度报道专家，为本期最热门话题生成专题报道。

返回 JSON:
{
  "title": "专题标题（15-25字，有吸引力）",
  "summary": "核心内容概述（80-120字，说明是什么、为什么重要、有什么影响）",
  "key_points": ["要点1（15-20字）", "要点2", "要点3"]
}
只返回JSON。"""),
            HumanMessage(content=f"基于以下内容生成深度专题:\n\n{context}")
        ]

        try:
            response = self.llm.invoke(messages)
            content = response.content.strip()
            start_idx = content.find('{')
            end_idx = content.rfind('}')
            if start_idx != -1 and end_idx != -1:
                spotlight = json.loads(content[start_idx:end_idx+1])
            else:
                spotlight = {}
        except Exception as e:
            print(f"    专题生成失败: {e}")
            spotlight = {}

        return {"spotlight": spotlight}

    def _analyze_market_pulse(self, state: AnalysisState) -> Dict:
        """节点: 分析市场脉搏（情绪+关键数据）"""
        print("  [Agent] 正在分析市场脉搏...")

        scored = state.get("scored", [])
        extracted_data = state.get("extracted_data", [])
        trends = state.get("trends", [])

        context = f"""
新闻数量: {len(scored)}
识别趋势: {', '.join(trends) if trends else '无'}
提取数据: {len(extracted_data)}条
"""
        # 添加新闻标题
        if scored:
            context += "\n主要新闻:\n" + "\n".join([
                f"- {item['title']}" for item in scored[:15]
            ])

        messages = [
            SystemMessage(content="""
你是市场分析专家，分析AI行业的市场脉搏。

**分析维度**：
1. 市场情绪（乐观/中性/谨慎/悲观）+ 情绪指数(0-100)
2. 热度领域Top3
3. 关键信号（2-3个值得关注的信号）
4. 风险提示（如果有的话）

返回 JSON:
{
  "sentiment": "乐观",
  "sentiment_score": 75,
  "sentiment_reason": "原因说明(20-30字)",
  "hot_areas": ["领域1", "领域2", "领域3"],
  "key_signals": [
    {"signal": "信号描述", "type": "positive|negative|neutral"}
  ],
  "risk_alerts": ["风险1"]
}
只返回JSON。
            """),
            HumanMessage(content=f"分析市场脉搏:\n\n{context}")
        ]

        try:
            response = self.llm.invoke(messages)
            content = response.content.strip()
            start_idx = content.find('{')
            end_idx = content.rfind('}')
            if start_idx != -1 and end_idx != -1:
                market_pulse = json.loads(content[start_idx:end_idx+1])
            else:
                market_pulse = {}
        except Exception as e:
            print(f"    市场分析失败: {e}")
            market_pulse = {}

        return {"market_pulse": market_pulse}

    def _generate_one_liners(self, state: AnalysisState) -> Dict:
        """节点: 生成一句话速读"""
        print("  [Agent] 正在生成一句话速读...")

        scored = state.get("scored", [])
        if not scored:
            return {"one_liners": {}}

        # 准备新闻文本
        news_text = "\n".join([
            f"ID: {i} | {item['title']}"
            for i, item in enumerate(scored[:30])
        ])

        messages = [
            SystemMessage(content="""
你是新闻精华提炼专家。为每条新闻生成一句话速读。

**要求**：
- 每条精华控制在10-15个中文字符
- 提炼核心价值/影响/结论
- 使用动词开头，有冲击力
- 不要重复标题，要提炼本质

**示例**：
- "OpenAI发布Codex桌面版" → "编程Agent进入桌面时代"
- "Anthropic估值3500亿" → "超OpenAI成最贵AI独角兽"
- "LangChain 0.3发布" → "Agent开发体验大幅提升"
- "Claude支持MCP协议" → "工具调用标准化迈出关键步"

返回 JSON: {"0": "一句话精华", "1": "一句话精华", ...}
为所有新闻生成精华，只返回JSON。
            """),
            HumanMessage(content=f"为这些新闻生成一句话速读:\n\n{news_text}")
        ]

        try:
            response = self.llm.invoke(messages)
            content = response.content.strip()
            start_idx = content.find('{')
            end_idx = content.rfind('}')
            if start_idx != -1 and end_idx != -1:
                one_liners = json.loads(content[start_idx:end_idx+1])
            else:
                one_liners = {}
        except Exception as e:
            print(f"    一句话速读生成失败: {e}")
            one_liners = {}

        print(f"    生成 {len(one_liners)} 条速读")
        return {"one_liners": one_liners}

    def _generate_action_items(self, state: AnalysisState) -> Dict:
        """节点: 生成行动建议"""
        print("  [Agent] 正在生成行动建议...")

        top_news = state.get("top_news", [])
        trends = state.get("trends", [])
        scored = state.get("scored", [])

        if not top_news and not scored:
            return {"action_items": []}

        # 准备上下文
        context = f"""
今日趋势: {', '.join(trends) if trends else '无明显趋势'}

TOP 新闻:
{chr(10).join([f'- {n["title"]}' for n in top_news[:10]])}

其他重要新闻:
{chr(10).join([f'- {n["title"]}' for n in scored[:10] if n.get('ai_score', 0) >= 6])}
        """

        messages = [
            SystemMessage(content="""你是技术战略顾问，为技术决策者生成可执行的行动建议。

**建议类型**：
- 试用: 值得动手试用的工具/产品
- 评估: 需要团队评估的技术方案
- 关注: 值得持续跟踪的趋势
- 学习: 值得深入学习的技术概念

**要求**：
- 生成 3-4 条建议，必须具体可执行
- action 字段要包含具体动作，如"pip install xxx"、"阅读官方文档"、"在测试环境部署"

**示例**：
{"type": "试用", "title": "体验 Claude MCP 协议", "reason": "Anthropic 开放工具调用标准，可能成为行业规范", "action": "安装 claude-mcp-sdk，跑通官方 demo", "priority": "high"}
{"type": "评估", "title": "评估 LangGraph 替代方案", "reason": "新版重构了状态管理，可能简化现有架构", "action": "在 staging 环境对比测试，产出评估报告", "priority": "medium"}

返回 JSON 数组，只返回JSON。"""),
            HumanMessage(content=f"基于以下内容生成行动建议:\n\n{context}")
        ]

        try:
            response = self.llm.invoke(messages)
            content = response.content.strip()
            start_idx = content.find('[')
            end_idx = content.rfind(']')
            if start_idx != -1 and end_idx != -1:
                action_items = json.loads(content[start_idx:end_idx+1])
            else:
                action_items = []
        except Exception as e:
            print(f"    行动建议生成失败: {e}")
            action_items = []

        print(f"    生成 {len(action_items)} 条行动建议")
        return {"action_items": action_items}

    def _generate_commentary(self, state: AnalysisState) -> Dict:
        """节点8: 生成开篇评论 - 趋势解读"""
        print("  [Agent] 正在生成开篇评论...")

        top_news = state.get("top_news", [])
        trends = state.get("trends", [])
        summary = state.get("summary", "")

        if not top_news:
            return {"commentary": ""}

        # 准备上下文
        context = f"""
今日趋势:
{chr(10).join(f'- {t}' for t in trends) if trends else '无明显趋势'}

TOP 新闻:
{chr(10).join(f'{i+1}. {n["title"]}' for i, n in enumerate(top_news[:5]))}

要点总结:
{summary}
        """

        # 调用 LLM 生成评论
        messages = [
            SystemMessage(content="""
你是资深 AI 行业分析师，为技术专家撰写每日新闻开篇评论。

**写作要求**：
- 150-250 字
- 专业、有洞见、不废话
- 突出最重要的 1-2 个事件或趋势
- 给出技术或战略层面的解读
- 面向技术决策者，语气专业但不枯燥
- 可以适当加入对未来影响的判断

**格式**：
直接输出评论文本，不需要标题或开头语。

示例风格：
"本周最值得关注的是 LangChain 0.2 的发布，这次更新彻底重构了 Agent 执行引擎，
将 Tool 调用延迟降低了 40%。更重要的是，新增的 Agent Memory 系统支持跨会话持久化，
这解决了长期困扰开发者的状态管理难题。结合 Anthropic 同期发布的 Claude 3.5 Opus，
我们可以预见企业级 Agent 应用将在今年下半年迎来一波部署高峰。"
            """),
            HumanMessage(content=f"基于以下分析生成开篇评论:\n\n{context}")
        ]

        try:
            response = self.llm.invoke(messages)
            commentary = response.content.strip()
        except Exception as e:
            print(f"    评论生成失败: {e}")
            commentary = ""

        return {"commentary": commentary}

    def _cluster_news(self, state: AnalysisState) -> Dict:
        """节点: 热点聚类 - 识别相关新闻组"""
        print("  [Agent] 正在进行热点聚类...")

        scored = state.get("scored", [])

        if len(scored) < 3:
            return {"clusters": []}

        # 准备新闻列表
        news_text = "\n".join([
            f"ID: {i} | {item['title']} | {item.get('source', '')}"
            for i, item in enumerate(scored[:20])
        ])

        # 调用 LLM 进行聚类
        messages = [
            SystemMessage(content="""
你是新闻聚类专家。将相关新闻分组，识别 2-5 个热点专题。

**聚类原则**：
- 同一事件的不同报道归为一组
- 同一技术主题的多篇内容归为一组
- 每个专题至少包含 2 条新闻
- 专题名称 8-15 字，概括核心主题
- 如果新闻关联性不强，可以返回较少或空的聚类

**返回格式** (JSON):
[
  {
    "topic": "专题名称",
    "news_ids": ["0", "3", "5"],
    "summary": "一句话描述这个专题的核心内容(20-30字)"
  }
]

只返回JSON数组。如果没有明显的聚类，返回 []。
            """),
            HumanMessage(content=f"对这些新闻进行热点聚类:\n\n{news_text}")
        ]

        try:
            response = self.llm.invoke(messages)

            content = response.content.strip()
            start_idx = content.find('[')
            end_idx = content.rfind(']')

            if start_idx != -1 and end_idx != -1:
                json_str = content[start_idx:end_idx+1]
                clusters = json.loads(json_str)

                # 丰富聚类数据，添加新闻详情
                for cluster in clusters:
                    cluster['news'] = []
                    for news_id in cluster.get('news_ids', []):
                        idx = int(news_id)
                        if idx < len(scored):
                            cluster['news'].append({
                                'title': scored[idx].get('title', ''),
                                'title_zh': scored[idx].get('title_zh', ''),
                                'link': scored[idx].get('link', ''),
                                'source': scored[idx].get('source', '')
                            })
            else:
                clusters = []

        except Exception as e:
            print(f"    聚类失败: {e}")
            clusters = []

        print(f"    识别 {len(clusters)} 个热点专题")
        return {"clusters": clusters}

    def _extract_data(self, state: AnalysisState) -> Dict:
        """节点: 提取关键数据 - 融资金额、估值、用户数等"""
        print("  [Agent] 正在提取关键数据...")

        scored = state.get("scored", [])

        if not scored:
            return {"extracted_data": []}

        # 准备新闻文本
        news_text = "\n\n".join([
            f"ID: {i}\n标题: {item['title']}\n摘要: {item['summary'][:200]}"
            for i, item in enumerate(scored[:15])
        ])

        # 调用 LLM 提取数据
        messages = [
            SystemMessage(content="""
你是数据提取专家。从新闻中提取关键数据指标。

**提取类型**：
- 融资金额 (funding): "$100M", "1亿美元"
- 估值 (valuation): "$10B", "100亿估值"
- 用户/客户数 (users): "100万用户", "500家企业客户"
- 性能指标 (performance): "提升50%", "延迟降低3x"
- 模型参数 (model): "70B参数", "128K上下文"

**返回格式** (JSON):
[
  {
    "news_id": "0",
    "company": "公司/产品名",
    "metric_type": "funding|valuation|users|performance|model",
    "value": "具体数值",
    "context": "简短说明(10-20字)"
  }
]

只提取有明确数值的数据，不要推测。如果没有数据，返回 []。
只返回JSON数组。
            """),
            HumanMessage(content=f"从这些新闻中提取关键数据:\n\n{news_text}")
        ]

        try:
            response = self.llm.invoke(messages)

            content = response.content.strip()
            start_idx = content.find('[')
            end_idx = content.rfind(']')

            if start_idx != -1 and end_idx != -1:
                json_str = content[start_idx:end_idx+1]
                extracted_data = json.loads(json_str)
            else:
                extracted_data = []

        except Exception as e:
            print(f"    数据提取失败: {e}")
            extracted_data = []

        print(f"    提取 {len(extracted_data)} 条关键数据")
        return {"extracted_data": extracted_data}

    def analyze(self, news_items: List[Dict]) -> Dict:
        """执行完整的分析流程"""
        print(f"\n[NewsAnalyzerAgent] 开始分析 {len(news_items)} 条新闻...")

        # 初始化状态
        initial_state = {
            "news_items": news_items,
            "categorized": {},
            "scored": [],
            "trends": [],
            "top_news": [],
            "summary": "",
            "metadata": {},
            "commentary": "",
            "clusters": [],
            "extracted_data": [],
            "news_labels": {},
            "paper_analysis": [],
            "spotlight": {},
            "market_pulse": {},
            "weekly_outlook": "",
            "one_liners": {},
            "action_items": []
        }

        # 执行工作流
        result = self.workflow.invoke(initial_state)

        print("[NewsAnalyzerAgent] 分析完成！\n")

        # 将标签和一句话速读合并到新闻数据中
        scored_with_labels = result.get("scored", [])
        news_labels = result.get("news_labels", {})
        one_liners = result.get("one_liners", {})
        for i, item in enumerate(scored_with_labels):
            if str(i) in news_labels:
                item['label'] = news_labels[str(i)]
            if str(i) in one_liners:
                item['one_liner'] = one_liners[str(i)]

        return {
            "summary": result["summary"],
            "trends": result["trends"],
            "top_news": result["top_news"],
            "translated_items": scored_with_labels,
            "categorized": result["categorized"],
            "metadata": result["metadata"],
            "commentary": result.get("commentary", ""),
            "clusters": result.get("clusters", []),
            "extracted_data": result.get("extracted_data", []),
            "news_labels": news_labels,
            "paper_analysis": result.get("paper_analysis", []),
            "spotlight": result.get("spotlight", {}),
            "market_pulse": result.get("market_pulse", {}),
            "one_liners": one_liners,
            "action_items": result.get("action_items", [])
        }


    def analyze_weekly(self, news_items: List[Dict], top_n: int = 10) -> Dict:
        """执行周报分析流程"""
        print(f"\n[NewsAnalyzerAgent] 开始周报分析 {len(news_items)} 条新闻...")

        if not news_items:
            return {
                "summary": "",
                "trends": [],
                "top_news": [],
                "highlights": [],
                "weekly_stats": {}
            }

        # 准备周报新闻文本
        news_text = "\n\n".join([
            f"ID: {i}\n标题: {item.get('title', '')}\n来源: {item.get('source', '')}"
            for i, item in enumerate(news_items[:50])  # 最多50条
        ])

        # 调用 LLM 生成周报分析
        messages = [
            SystemMessage(content=f"""
你是资深 AI 行业分析师，为技术专家撰写周报。

**任务**：基于本周新闻，生成周报分析。

**返回 JSON 格式**:
{{
  "weekly_summary": "本周综述（150-250字，概括本周最重要的趋势和事件）",
  "top_news_ids": ["0", "3", "5"],  // 本周最值得关注的 {top_n} 条新闻 ID
  "top_reasons": ["理由1", "理由2", "理由3"],  // 对应的推荐理由
  "trends": ["趋势1", "趋势2", "趋势3"],  // 本周 3-5 个关键趋势
  "highlights": [
    {{"title": "重点事件1", "impact": "影响说明"}},
    {{"title": "重点事件2", "impact": "影响说明"}}
  ],  // 2-4 个重点事件及其影响
  "outlook": "下周展望（50-80字，预测下周可能的发展方向）"
}}

只返回 JSON，不要其他文字。
            """),
            HumanMessage(content=f"分析这些本周新闻并生成周报:\n\n{news_text}")
        ]

        try:
            response = self.llm.invoke(messages)

            content = response.content.strip()
            start_idx = content.find('{')
            end_idx = content.rfind('}')

            if start_idx != -1 and end_idx != -1:
                json_str = content[start_idx:end_idx+1]
                analysis = json.loads(json_str)
            else:
                raise ValueError("未找到有效 JSON")

            # 构建 top_news 列表
            top_news = []
            top_ids = analysis.get('top_news_ids', [])
            top_reasons = analysis.get('top_reasons', [])
            for i, news_id in enumerate(top_ids[:top_n]):
                idx = int(news_id)
                if idx < len(news_items):
                    news_copy = news_items[idx].copy()
                    if i < len(top_reasons):
                        news_copy['weekly_reason'] = top_reasons[i]
                    top_news.append(news_copy)

            result = {
                "summary": analysis.get('weekly_summary', ''),
                "trends": analysis.get('trends', []),
                "top_news": top_news,
                "highlights": analysis.get('highlights', []),
                "outlook": analysis.get('outlook', ''),
                "weekly_stats": {
                    "total_news": len(news_items),
                    "analyzed_at": datetime.now().isoformat()
                }
            }

        except Exception as e:
            print(f"    周报分析失败: {e}")
            result = {
                "summary": "",
                "trends": [],
                "top_news": news_items[:top_n],
                "highlights": [],
                "weekly_stats": {"total_news": len(news_items)}
            }

        print("[NewsAnalyzerAgent] 周报分析完成！\n")
        return result


# 简化的工厂函数
def create_analyzer(aws_region='us-west-2') -> NewsAnalyzerAgent:
    """创建分析器实例"""
    return NewsAnalyzerAgent(aws_region=aws_region)
