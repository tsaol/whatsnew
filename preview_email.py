"""生成邮件 HTML 预览"""
from src.config import Config
from src.storage import Storage
from src.crawler import Crawler
from src.mailer import Mailer
from src.analyzer import create_analyzer

print("生成邮件预览...")
print("="*50)

# 加载配置
config = Config('config.yaml')

# 初始化模块
storage = Storage(config.get('data_file', 'data/sent_news.json'))
crawler = Crawler(storage)
mailer = Mailer(config.email_config)

# 抓取新闻用于预览（使用所有启用的源，每个源限制3条）
sources = config.sources  # 使用所有启用的源
max_items = 3  # 每个源最多3条，避免预览过长
max_days = config.get('max_days', 2)  # 默认2天（48小时）
new_items = crawler.fetch_all(sources, max_items=max_items, max_days=max_days)

print(f"\n抓取到 {len(new_items)} 条新闻")

# AI 分析
ai_analysis = None
ai_enabled = config.get('ai.enabled', False)

if new_items and ai_enabled and len(new_items) >= 5:
    try:
        print(f"\n🤖 正在进行 AI 分析...")
        aws_region = config.get('ai.aws_region', 'us-west-2')
        analyzer = create_analyzer(aws_region=aws_region)
        ai_analysis = analyzer.analyze(new_items)
        print(f"✅ AI 分析完成")

        # 如果有翻译后的数据，使用翻译后的数据替换原始数据
        if ai_analysis and ai_analysis.get('translated_items'):
            new_items = ai_analysis['translated_items']
            print(f"✅ 使用翻译后的新闻数据")
    except Exception as e:
        print(f"⚠️  AI 分析失败: {e}")
        ai_analysis = None

# 生成邮件内容
print(f"\n生成邮件 HTML...")
subject, html_content = mailer.format_news_email(new_items, ai_analysis=ai_analysis)

# 保存到文件
output_file = "email_preview.html"
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"\n✅ 邮件预览已生成")
print(f"📁 文件位置: {output_file}")
print(f"📧 邮件主题: {subject}")
print(f"\n打开文件查看效果:")
print(f"   file://{output_file}")
print("="*50)
