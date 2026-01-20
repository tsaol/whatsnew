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
        """构建 LangGraph 工作流"""
        workflow = StateGraph(AnalysisState)

        # 添加节点
        workflow.add_node("categorize", self._categorize_news)
        workflow.add_node("filter", self._filter_news)
        workflow.add_node("score", self._score_news)
        workflow.add_node("enhance", self._enhance_summary)
        workflow.add_node("translate", self._translate_news)
        workflow.add_node("find_trends", self._find_trends)
        workflow.add_node("summarize", self._summarize)

        # 定义边（流程）
        workflow.set_entry_point("categorize")
        workflow.add_edge("categorize", "filter")
        workflow.add_edge("filter", "score")
        workflow.add_edge("score", "enhance")
        workflow.add_edge("enhance", "translate")
        workflow.add_edge("translate", "find_trends")
        workflow.add_edge("find_trends", "summarize")
        workflow.add_edge("summarize", END)

        return workflow.compile()

    def _categorize_news(self, state: AnalysisState) -> Dict:
        """节点1: 分类新闻"""
        print("  [Agent] 正在分类新闻...")

        news_items = state["news_items"]

        # 准备新闻文本
        news_text = "\n\n".join([
            f"ID: {i}\n标题: {item['title']}\n来源: {item['source']}\n"
            f"摘要: {item['summary'][:200]}"
            for i, item in enumerate(news_items)
        ])

        # 调用 LLM 分类
        messages = [
            SystemMessage(content="""
你是AI/科技新闻分类专家。将新闻分类到以下类别：

核心类别：
- AI Research: 学术研究、论文、算法创新
- GenAI & LLM: 大模型、生成式AI应用、Prompt工程
- AI Infrastructure: ML平台、训练框架、模型部署
- Developer Tools: IDE、框架、库、开发工具
- Cloud Services: 云计算、AWS/Azure/GCP更新
- Industry & Business: 公司动态、融资、战略
- Other: 其他

返回 JSON 格式: {"AI Research": ["0", "1"], "GenAI & LLM": ["2"], ...}
只返回JSON，不要其他文字。
            """),
            HumanMessage(content=f"分类这些新闻:\n\n{news_text}")
        ]

        response = self.llm.invoke(messages)

        try:
            categorized = json.loads(response.content)
        except:
            # 如果解析失败，默认分类
            categorized = {"Other": [str(i) for i in range(len(news_items))]}

        return {"categorized": categorized}

    def _filter_news(self, state: AnalysisState) -> Dict:
        """节点2: 过滤新闻 - 只保留与 AI/计算机技术相关的内容"""
        print("  [Agent] 正在过滤新闻相关性...")

        news_items = state["news_items"]
        categorized = state.get("categorized", {})

        # 技术社区来源（放宽标准）
        tech_community_sources = {
            "Hacker News", "GitHub Trending", "GitHub Blog",
            "Dev.to", "Rust Blog", "Python Blog"
        }

        # 准备新闻文本（只过滤非技术社区来源）
        items_to_check = []
        tech_community_items = []

        for i, item in enumerate(news_items):
            if item['source'] in tech_community_sources:
                tech_community_items.append(i)
            else:
                items_to_check.append(i)

        if not items_to_check:
            print(f"    全部为技术社区来源，跳过过滤")
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
        keep_ids = set(tech_community_items) | relevant_ids
        filtered_items = [news_items[i] for i in sorted(keep_ids)]

        filtered_count = len(news_items) - len(filtered_items)
        print(f"    过滤掉 {filtered_count} 条不相关新闻，保留 {len(filtered_items)} 条")

        return {"news_items": filtered_items}

    def _score_news(self, state: AnalysisState) -> Dict:
        """节点3: 评估新闻重要性 - 聚焦 Agentic AI"""
        print("  [Agent] 正在评估新闻重要性...")

        news_items = state["news_items"]

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
- Claude/GPT 的 Agent 能力更新
- AWS Bedrock Agents 新功能
- 多 Agent 协作、Agent 安全的突破性研究

7-8分 [重要]：
- RAG 技术重要进展
- Tool Use / Function Calling 更新
- Agent 开发工具和框架更新
- LLM 推理优化（与 Agent 相关）
- 企业级 Agent 落地案例

5-6分 [一般]：
- 通用 LLM 模型更新（非 Agent 相关）
- 云服务常规更新
- 通用 AI 研究进展

3-4分 [低价值]：
- 公司新闻、人事变动、融资
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

            # 合并评分到原新闻
            scored_news = []
            for item in scored:
                news_id = int(item['id'])
                if news_id < len(news_items):
                    news_copy = news_items[news_id].copy()
                    news_copy['ai_score'] = item['score']
                    news_copy['ai_reason'] = item.get('reason', '')
                    scored_news.append(news_copy)

            # 验证评分分布，如果全是5分则警告
            scores = [n['ai_score'] for n in scored_news]
            if len(set(scores)) == 1:
                print(f"    [警告] 评分无区分度，全部为 {scores[0]} 分")

        except Exception as e:
            print(f"    评分解析失败: {e}")
            # 如果解析失败，默认评分
            scored_news = [
                {**item, 'ai_score': 5, 'ai_reason': ''}
                for item in news_items
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
            SystemMessage(content="""
你是 Agentic AI 趋势分析专家。基于今日新闻，识别 2-4 个与 Agent/Agentic AI 相关的趋势。

**聚焦方向**：
- Agent 框架演进（LangChain、LlamaIndex、CrewAI 等）
- Multi-Agent 协作和编排
- Agent 安全和可靠性
- Tool Use / MCP 生态
- RAG 和知识检索
- Agent 在企业的落地应用

**要求**：
- 每个趋势 8-15 字
- 必须与 Agent/Agentic AI 相关
- 具体、有洞察，不要泛泛而谈
- 如果今日新闻没有明显 Agent 趋势，返回空数组 []

示例：
["Agent安全沙箱机制成熟", "文档处理Agent能力提升", "MCP生态快速扩展"]

返回 JSON 格式: ["趋势1", "趋势2", ...]
只返回JSON数组，不要其他文字。如果没有明显趋势，返回 []。
            """),
            HumanMessage(content=f"基于这些新闻识别 Agentic AI 趋势:\n\n{news_text}")
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
            "metadata": {}
        }

        # 执行工作流
        result = self.workflow.invoke(initial_state)

        print("[NewsAnalyzerAgent] 分析完成！\n")

        return {
            "summary": result["summary"],
            "trends": result["trends"],
            "top_news": result["top_news"],
            "translated_items": result.get("scored", []),  # scored 包含翻译后的新闻
            "categorized": result["categorized"],
            "metadata": result["metadata"]
        }


# 简化的工厂函数
def create_analyzer(aws_region='us-west-2') -> NewsAnalyzerAgent:
    """创建分析器实例"""
    return NewsAnalyzerAgent(aws_region=aws_region)
