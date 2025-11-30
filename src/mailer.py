"""邮件发送模块"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


class Mailer:
    def __init__(self, config):
        self.smtp_server = config['smtp_server']
        self.smtp_port = config['smtp_port']
        self.username = config['username']
        self.password = config['password']
        self.to_email = config['to']

    def send(self, subject, content):
        """发送邮件"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.username
            msg['To'] = self.to_email
            msg['Subject'] = subject

            msg.attach(MIMEText(content, 'html', 'utf-8'))

            # 连接SMTP服务器（126邮箱使用SSL）
            server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            server.login(self.username, self.password)
            server.send_message(msg)
            server.quit()

            print(f"邮件发送成功: {subject}")
            return True

        except Exception as e:
            print(f"邮件发送失败: {e}")
            return False

    def format_news_email(self, items):
        """格式化新闻邮件内容"""
        if not items:
            return None, None

        subject = f"WhatsNew - {len(items)} 条新内容 ({datetime.now().strftime('%Y-%m-%d %H:%M')})"

        # HTML邮件内容
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                h2 {{ color: #2c3e50; }}
                .item {{ margin-bottom: 30px; padding: 15px; border-left: 4px solid #3498db; background: #f9f9f9; }}
                .source {{ color: #7f8c8d; font-size: 0.9em; }}
                .title {{ font-size: 1.2em; font-weight: bold; margin: 10px 0; }}
                .title a {{ color: #2980b9; text-decoration: none; }}
                .title a:hover {{ text-decoration: underline; }}
                .summary {{ color: #555; margin-top: 10px; }}
                .published {{ color: #95a5a6; font-size: 0.85em; margin-top: 5px; }}
            </style>
        </head>
        <body>
            <h2>最新资讯</h2>
        """

        for item in items:
            html += f"""
            <div class="item">
                <div class="source">[{item['source']}]</div>
                <div class="title"><a href="{item['link']}" target="_blank">{item['title']}</a></div>
                <div class="summary">{item['summary'][:200]}...</div>
                <div class="published">{item['published']}</div>
            </div>
            """

        html += """
        </body>
        </html>
        """

        return subject, html
