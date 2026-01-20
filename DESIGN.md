# WhatsNew - Design Document

## 🎯 核心功能

### 1. AI 智能分析引擎 (LangGraph + Claude Sonnet 4.5)

**7 节点工作流**：
```
原始新闻
  → 分类 (Categorize)
  → 过滤 (Filter)
  → 评分 (Score)
  → 增强 (Enhance)
  → 翻译 (Translate)
  → 趋势 (Trends)
  → 总结 (Summarize)
```

#### 1.1 分类节点 (Categorize)
- **功能**：将新闻分类到预定义类别
- **类别**：AI Research, GenAI & LLM, AI Infrastructure, Developer Tools, Cloud Services, Industry & Business, Other
- **实现**：使用 Claude Sonnet 4.5 进行语义分类
- **输出**：`{"AI Research": ["0", "1"], "GenAI & LLM": ["2"], ...}`

#### 1.2 过滤节点 (Filter)
- **功能**：智能过滤非 AI 相关内容
- **聚焦**：GenAI/LLM/Agentic AI/云AI服务
- **策略**：
  - 技术社区来源（Hacker News, GitHub）：放宽标准
  - 其他来源：严格筛选 AI 相关性
- **过滤规则**：通用软件开发、硬件产品、营销内容、非技术新闻
- **输出**：过滤后的新闻列表

#### 1.3 评分节点 (Score)
- **功能**：评估新闻重要性（1-10 分）
- **评分标准**：
  - 9-10分：突破性技术、重大产品发布、行业变革
  - 7-8分：重要功能更新、有影响力的研究
  - 5-6分：常规更新、一般技术进展
  - 3-4分：营销内容、促销信息
  - 1-2分：低价值内容
- **输出**：每条新闻附带 `ai_score` 和 `ai_reason`

#### 1.4 增强节点 (Enhance)
- **功能**：为简短摘要生成详细描述
- **触发条件**：
  - 摘要长度 < 50 字符
  - 摘要与标题重复
  - 只有省略号
- **生成要求**：80-150 字，信息密度高，突出技术价值
- **输出**：增强后的 `summary` 字段

#### 1.5 翻译节点 (Translate)
- **功能**：英文新闻翻译成中文
- **检测**：英文字符占比 > 50%
- **批量处理**：10 条/批
- **要求**：
  - 保持技术术语准确性
  - 标题简洁有力
  - 摘要流畅自然
  - 使用书名号《》或单引号'，避免双引号"
- **输出**：`title_zh` 和 `summary_zh` 字段

#### 1.6 趋势节点 (Trends)
- **功能**：识别 3-5 个关键技术趋势
- **输入**：高分新闻（≥ 7 分）
- **要求**：8-15 字，聚焦技术方向
- **示例**：多模态模型实用化加速、开发工具AI化趋势明显
- **输出**：趋势列表

#### 1.7 总结节点 (Summarize)
- **功能**：生成精炼的 bullet points 总结
- **格式**：3-5 个要点，每个 20-35 字
- **选择 TOP 5**：按 `ai_score` 排序
- **输出**：
  - `summary`: 总结文本
  - `top_news`: TOP 5 新闻列表
  - `metadata`: 统计信息

### 2. 多源新闻聚合

**25+ AI 新闻源**：

#### AI 公司与研究机构
- OpenAI Blog
- Anthropic News
- Google AI Blog
- DeepMind Blog
- Hugging Face Blog
- Microsoft Research AI

#### 框架与工具
- LangChain Blog
- LlamaIndex Blog
- Replicate Blog

#### 云服务商
- AWS (8 个博客)：Machine Learning, AI, Compute, Big Data, Developer, Architecture, News, Startups
- GitHub Blog

#### 学术与技术媒体
- arXiv cs.AI
- TechCrunch AI
- VentureBeat AI
- MIT Tech Review AI

### 3. 智能内容过滤

#### 去重机制
- **ID 生成**：基于 URL 的 MD5 哈希
- **存储**：JSON 文件（`data/sent_news.json`）
- **检查**：发送前检查是否已存在

#### 时间过滤
- **默认**：只保留 48 小时内的新闻（2天）
- **配置**：`max_days: 2` （可调整）
- **实现**：解析 RSS `published_parsed` 字段
- **容错**：日期解析失败则保留新闻

#### AI 智能过滤
- **执行**：过滤节点
- **精度**：技术社区源放宽，其他严格筛选
- **输出**：显示过滤统计

### 4. 专业邮件推送

#### 邮件结构

**头部**
- 标题：WhatsNew 每日资讯
- 元信息：新闻数量、日期时间

**AI 分析区**（如果启用）
- 💡 今日聚焦：bullet points 总结
- 📊 关键趋势：趋势标签
- ⭐ TOP 新闻推荐：
  - 排名 + 评分
  - 标题（英文，可点击）
  - 来源标签
  - 标题翻译（中文）
  - 评分理由
  - **不显示摘要**（避免与完整列表重复）

**完整新闻列表**
- 按来源分组
- 每个新闻卡片：
  - 标题（英文，可点击）
  - 标题翻译（中文）
  - AI 评分徽章
  - TOP 徽章（如果是 TOP 新闻）
  - 发布时间
  - 摘要（英文）
  - 摘要翻译（中文）

**页脚**
- 生成信息
- AI 提供商说明
- 统计数据

#### 样式设计
- **现代化**：圆角、渐变、阴影
- **响应式**：最大宽度 800px
- **交互**：悬停效果、平滑过渡
- **可读性**：清晰的层次结构、适当的间距

### 5. 配置管理

#### config.yaml 结构

```yaml
email:
  smtp_server: smtp.126.com
  smtp_port: 465
  username: your-email@126.com
  password: YOUR_AUTH_CODE
  to: recipient@example.com

sources:
  - name: OpenAI Blog
    type: rss
    url: https://openai.com/blog/rss.xml
    enabled: true

schedule:
  interval_hours: 1

ai:
  enabled: true
  aws_region: us-west-2
  model_id: global.anthropic.claude-sonnet-4-5-20250929-v1:0
  min_news_for_analysis: 5

max_items_per_source: 8
max_days: 2  # 48 hours
data_file: data/sent_news.json
```

## 🏗️ 技术架构

### 模块划分

```
src/
├── config.py       # 配置管理
├── crawler.py      # RSS 爬虫
├── storage.py      # 数据存储与去重
├── analyzer.py     # AI 分析引擎 (LangGraph)
└── mailer.py       # 邮件生成与发送
```

### 数据流

```
config.yaml
    ↓
爬虫抓取 (crawler.py)
    ↓
时间过滤 (max_days)
    ↓
去重检查 (storage.py)
    ↓
AI 分析 (analyzer.py)
    ├─ 分类
    ├─ 过滤
    ├─ 评分
    ├─ 增强
    ├─ 翻译
    ├─ 趋势
    └─ 总结
    ↓
邮件生成 (mailer.py)
    ↓
SMTP 发送
    ↓
标记已发送 (storage.py)
```

### 关键依赖

```
langchain-aws       # AWS Bedrock 集成
langgraph           # 工作流编排
feedparser          # RSS 解析
boto3               # AWS SDK
pyyaml              # 配置解析
schedule            # 任务调度
```

## 💰 成本优化

### Claude Sonnet 4.5 定价
- 输入：$3 / 百万 tokens
- 输出：$15 / 百万 tokens

### 估算（每天 1 次，40 条新闻）
- 分类：~5K tokens 输入, ~1K tokens 输出
- 过滤：~4K tokens 输入, ~500 tokens 输出
- 评分：~4K tokens 输入, ~1K tokens 输出
- 增强：~2K tokens 输入, ~3K tokens 输出
- 翻译：~8K tokens 输入, ~10K tokens 输出
- 趋势：~1K tokens 输入, ~200 tokens 输出
- 总结：~2K tokens 输入, ~300 tokens 输出

**总计**：~26K 输入, ~16K 输出
**每次成本**：$0.078 + $0.240 = $0.32
**月成本**：$0.32 × 30 = ~$10/月

### 优化策略
1. **批量处理**：翻译和增强使用批处理（10 条/批）
2. **条件触发**：`min_news_for_analysis: 5`
3. **缓存结果**：已翻译内容存储在 item 对象中
4. **智能过滤**：减少后续节点处理量

## 🚀 部署方式

### 1. 手动运行
```bash
python3 test_once.py
```

### 2. 定时任务（Cron）
```bash
0 22 * * * cd /path/to/whatsnew && python3 test_once.py >> cron.log 2>&1
```

### 3. 持续运行
```bash
python3 main.py  # 每天固定时间发送
```

## 🔧 扩展性

### 添加新闻源
1. 在 `config.yaml` 中添加源配置
2. 设置 `enabled: true`
3. 无需修改代码

### 调整分析策略
- 修改 `analyzer.py` 中各节点的 system message
- 调整评分标准、过滤规则、总结格式

### 支持其他 LLM
- 修改 `analyzer.py` 中的 `ChatBedrock` 初始化
- 可切换到 OpenAI, Anthropic API, Google Gemini

### 支持其他邮件服务
- 修改 `mailer.py` 中的 SMTP 配置
- 支持 Gmail, Outlook, SendGrid 等

## 📊 监控与日志

### 日志输出
- 抓取进度：每个源的新闻数量
- 过滤统计：过期新闻数量
- AI 分析进度：各节点状态
- 发送结果：成功/失败
- 累计统计：已发送总数

### 错误处理
- 网络错误：继续处理其他源
- AI 分析失败：降级到传统模式
- 邮件发送失败：记录错误信息
- 日期解析失败：保留新闻（容错）

## 🎯 设计原则

1. **简洁性**：模块化设计，职责清晰
2. **可靠性**：完善的错误处理和容错机制
3. **可扩展性**：配置驱动，易于添加功能
4. **用户友好**：清晰的日志输出，直观的邮件格式
5. **成本意识**：批量处理，条件触发，智能缓存

## 📝 待优化

- [ ] 支持 webhook 推送（Slack, Discord, 钉钉）
- [ ] 添加 Web 界面查看历史新闻
- [ ] 支持用户自定义过滤规则
- [ ] 增加更多中文 AI 新闻源
- [ ] 实现增量更新机制（避免重复分析）
- [ ] 添加 Docker 部署支持
- [ ] 实现邮件模板自定义
- [ ] 添加监控和告警功能
