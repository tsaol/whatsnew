"""浏览器全文抓取器 - 使用 Playwright 渲染 JS 并保存完整内容"""
import hashlib
import json
import base64
import boto3
from datetime import datetime, timezone, timedelta
from typing import Optional
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


class BrowserFetcher:
    """基于 Playwright 的全文抓取器，支持 JS 渲染和图片保存"""

    def __init__(self, config):
        self.config = config
        self.s3_config = config.get('s3', {})
        self.bucket = self.s3_config.get('bucket', 'cls-whatsnew')
        self.prefix = self.s3_config.get('prefix', 'hub')
        self.s3 = boto3.client('s3', region_name=config.get('aws_region', 'us-west-2'))

        # 本地备份目录
        self.local_dir = Path(__file__).parent.parent / 'data' / 'captures'
        self.local_dir.mkdir(parents=True, exist_ok=True)

        # 北京时区
        self.beijing_tz = timezone(timedelta(hours=8))

    def capture(self, url: str, metadata: dict = None,
                save_screenshot: bool = True,
                save_html: bool = True,
                save_images: bool = True,
                save_to_s3: bool = True) -> Optional[dict]:
        """
        抓取完整网页内容

        Args:
            url: 目标 URL
            metadata: 可选元数据 (title, source, category)
            save_screenshot: 是否保存全页截图
            save_html: 是否保存完整 HTML
            save_images: 是否下载保存图片
            save_to_s3: 是否上传到 S3

        Returns:
            dict: {id, url, title, text, html_key, screenshot_key, images, ...}
        """
        if sync_playwright is None:
            print("[BrowserFetcher] playwright 未安装")
            return None

        article_id = self._generate_id(url)
        result = {
            'id': article_id,
            'url': url,
            'source': (metadata or {}).get('source', ''),
            'category': (metadata or {}).get('category', ''),
            'captured_at': datetime.now(self.beijing_tz).isoformat()
        }

        # 图片保存目录
        images_dir = self.local_dir / article_id
        if save_images:
            images_dir.mkdir(parents=True, exist_ok=True)

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={'width': 1280, 'height': 800},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                )
                page = context.new_page()

                # 收集并保存图片
                images = []
                image_index = [0]  # 用列表以便在闭包中修改

                def handle_response(response):
                    if response.request.resource_type == 'image':
                        try:
                            img_url = response.url
                            status = response.status

                            # 跳过追踪像素和小图标
                            if any(x in img_url for x in ['px.ads', 'track', '.gif?', 'pixel', 'beacon']):
                                return

                            img_info = {
                                'url': img_url,
                                'status': status,
                                'index': image_index[0]
                            }

                            # 下载图片内容
                            if save_images and status == 200:
                                try:
                                    body = response.body()
                                    if len(body) > 1000:  # 跳过太小的图片（可能是图标）
                                        # 确定文件扩展名
                                        ext = self._get_image_ext(img_url, response.headers.get('content-type', ''))
                                        filename = f"{image_index[0]:03d}{ext}"
                                        filepath = images_dir / filename

                                        filepath.write_bytes(body)
                                        img_info['local_path'] = str(filepath)
                                        img_info['size'] = len(body)
                                        image_index[0] += 1
                                except Exception as e:
                                    img_info['error'] = str(e)

                            images.append(img_info)
                        except:
                            pass

                page.on('response', handle_response)

                # 加载页面
                print(f"[BrowserFetcher] 加载: {url}")
                page.goto(url, wait_until='networkidle', timeout=60000)

                # 等待额外时间让懒加载图片加载
                page.wait_for_timeout(2000)

                # 滚动到底部触发懒加载
                page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                page.wait_for_timeout(1000)

                # 获取标题
                title = (metadata or {}).get('title') or page.title()
                result['title'] = title

                # 生成可读的文件夹名
                folder_name = self._generate_folder_name(title, article_id)
                result['folder_name'] = folder_name

                # 获取正文
                text = page.evaluate('() => document.body.innerText')
                result['text'] = text
                result['text_length'] = len(text)

                # 保存截图
                if save_screenshot:
                    screenshot = page.screenshot(full_page=True, type='png')
                    screenshot_key = f"{self.prefix}/{folder_name}/screenshot.png"

                    # 本地保存
                    local_path = self.local_dir / folder_name / "screenshot.png"
                    local_path.parent.mkdir(parents=True, exist_ok=True)
                    local_path.write_bytes(screenshot)
                    result['screenshot_local'] = str(local_path)

                    # S3 上传
                    if save_to_s3:
                        self.s3.put_object(
                            Bucket=self.bucket,
                            Key=screenshot_key,
                            Body=screenshot,
                            ContentType='image/png'
                        )
                        result['screenshot_s3'] = f"s3://{self.bucket}/{screenshot_key}"
                        print(f"[BrowserFetcher] 截图已保存: {screenshot_key}")

                # 保存 HTML (含内联资源)
                if save_html:
                    # 获取完整 HTML
                    html = page.content()
                    html_key = f"{self.prefix}/{folder_name}/page.html"

                    # 本地保存
                    local_html = self.local_dir / folder_name / "page.html"
                    local_html.parent.mkdir(parents=True, exist_ok=True)
                    local_html.write_text(html, encoding='utf-8')
                    result['html_local'] = str(local_html)

                    # S3 上传
                    if save_to_s3:
                        self.s3.put_object(
                            Bucket=self.bucket,
                            Key=html_key,
                            Body=html.encode('utf-8'),
                            ContentType='text/html; charset=utf-8'
                        )
                        result['html_s3'] = f"s3://{self.bucket}/{html_key}"
                        print(f"[BrowserFetcher] HTML 已保存: {html_key}")

                # 图片信息
                saved_images = [img for img in images if img.get('local_path')]
                result['images'] = images
                result['image_count'] = len(images)
                result['saved_image_count'] = len(saved_images)

                # 上传图片到 S3
                if save_images and save_to_s3 and saved_images:
                    result['images_s3'] = []
                    for img in saved_images:
                        if img.get('local_path'):
                            local_path = Path(img['local_path'])
                            s3_key = f"{self.prefix}/{folder_name}/images/{local_path.name}"
                            self.s3.put_object(
                                Bucket=self.bucket,
                                Key=s3_key,
                                Body=local_path.read_bytes(),
                                ContentType=self._get_content_type(local_path.suffix)
                            )
                            img['s3_path'] = f"s3://{self.bucket}/{s3_key}"
                            result['images_s3'].append(img['s3_path'])
                    print(f"[BrowserFetcher] 图片已上传: {len(result['images_s3'])} 张")

                browser.close()

                # 保存元数据
                meta_key = f"{self.prefix}/{folder_name}/meta.json"
                if save_to_s3:
                    self.s3.put_object(
                        Bucket=self.bucket,
                        Key=meta_key,
                        Body=json.dumps(result, ensure_ascii=False, indent=2),
                        ContentType='application/json'
                    )

                print(f"[BrowserFetcher] 完成: {title[:50]}... ({len(text)} 字符, {len(images)} 图片)")
                return result

        except Exception as e:
            print(f"[BrowserFetcher] 抓取失败 {url}: {e}")
            return None

    def capture_batch(self, items: list, **kwargs) -> list:
        """批量抓取"""
        results = []
        for item in items:
            url = item.get('link') or item.get('url')
            if not url:
                continue

            metadata = {
                'title': item.get('title'),
                'source': item.get('source'),
                'category': item.get('category')
            }

            result = self.capture(url, metadata, **kwargs)
            if result:
                results.append(result)

        print(f"[BrowserFetcher] 批量完成: {len(results)}/{len(items)}")
        return results

    def _generate_id(self, url: str) -> str:
        """生成文章唯一 ID"""
        return hashlib.md5(url.encode()).hexdigest()

    def _get_image_ext(self, url: str, content_type: str) -> str:
        """根据 URL 或 Content-Type 确定图片扩展名"""
        # 从 content-type 推断
        type_map = {
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'image/webp': '.webp',
            'image/svg+xml': '.svg',
            'image/avif': '.avif'
        }
        for ct, ext in type_map.items():
            if ct in content_type:
                return ext

        # 从 URL 推断
        url_lower = url.lower().split('?')[0]
        for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.avif']:
            if url_lower.endswith(ext):
                return ext if ext != '.jpeg' else '.jpg'

        return '.jpg'  # 默认

    def _get_content_type(self, ext: str) -> str:
        """根据扩展名返回 Content-Type"""
        return {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.svg': 'image/svg+xml',
            '.avif': 'image/avif'
        }.get(ext.lower(), 'image/jpeg')

    def _generate_folder_name(self, title: str, article_id: str) -> str:
        """生成可读的文件夹名: {date}_{title}_{short_id}

        例如: 2026-02-08_LangChain-Templates_0d2526c2
        """
        import re

        # 日期
        date_str = datetime.now(self.beijing_tz).strftime('%Y-%m-%d')

        # 标题转 slug (只保留字母数字，用横杠连接)
        if title:
            # 移除特殊字符，保留字母数字空格
            slug = re.sub(r'[^\w\s-]', '', title)
            # 空格转横杠
            slug = re.sub(r'[\s_]+', '-', slug)
            # 截断到 50 字符
            slug = slug[:50].strip('-')
        else:
            slug = 'untitled'

        # 短 ID (前 8 位)
        short_id = article_id[:8]

        return f"{date_str}_{slug}_{short_id}"
