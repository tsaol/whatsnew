#!/usr/bin/env python3
"""Content Hub Web Console - FastAPI Application"""

import sys
import json
import hashlib
import secrets
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Query, HTTPException, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
import uvicorn

# 添加模块路径
sys.path.insert(0, str(Path(__file__).parent))
from src.config import Config
from src.storage import ContentStorage
from src.search import ContentSearch

# ============================================================
# 用户认证
# ============================================================

USERS_FILE = Path(__file__).parent / "users.json"

def hash_password(password: str, salt: str = "") -> str:
    """哈希密码 (SHA256 + salt)"""
    return hashlib.sha256((password + salt).encode()).hexdigest()

def load_users() -> dict:
    """加载用户配置"""
    if USERS_FILE.exists():
        with open(USERS_FILE) as f:
            return json.load(f)
    return {"users": {}, "session_secret": secrets.token_hex(32)}

def verify_user(username: str, password: str) -> Optional[dict]:
    """验证用户"""
    users_config = load_users()
    users = users_config.get("users", {})
    if username not in users:
        return None

    user_data = users[username]
    stored_password = user_data.get("password", "")

    # 支持哈希密码和明文密码（向后兼容）
    if user_data.get("hashed", False):
        # 哈希密码验证
        salt = user_data.get("salt", "")
        if hash_password(password, salt) == stored_password:
            return {"username": username, "name": user_data.get("name", username)}
    else:
        # 明文密码验证（兼容旧格式）
        if stored_password == password:
            return {"username": username, "name": user_data.get("name", username)}

    return None

def get_current_user(request: Request) -> Optional[dict]:
    """获取当前登录用户"""
    return request.session.get("user")

def require_login(request: Request):
    """登录检查依赖"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user

# ============================================================
# 应用初始化
# ============================================================

# 全局服务实例
config: Config = None
storage: ContentStorage = None
search: ContentSearch = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global config, storage, search
    print("[Web] 初始化 Content Hub...")
    config = Config()
    storage = ContentStorage(config)
    search = ContentSearch(storage)
    print("[Web] 初始化完成")
    yield
    print("[Web] 应用关闭")


app = FastAPI(
    title="Content Hub",
    description="WhatsNew 内容中心 - 文章浏览与搜索",
    version="1.0.0",
    lifespan=lifespan
)

# 添加 Session 中间件 (安全加固)
users_config = load_users()
app.add_middleware(
    SessionMiddleware,
    secret_key=users_config.get("session_secret", "default-secret-key"),
    max_age=86400 * 7,  # 7 天有效期
    same_site="lax",    # 防止 CSRF
    https_only=True     # 仅 HTTPS 传输 (生产环境)
)

# 模板和静态文件
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")


# ============================================================
# 辅助函数
# ============================================================

def build_filters(source: Optional[str], category: Optional[str],
                  date_from: Optional[str], date_to: Optional[str]) -> list:
    """构建 OpenSearch 过滤条件"""
    filters = []
    if source:
        filters.append({"term": {"source": source}})
    if category:
        filters.append({"term": {"category": category}})
    if date_from or date_to:
        date_range = {}
        if date_from:
            date_range["gte"] = date_from
        if date_to:
            date_range["lte"] = date_to
        filters.append({"range": {"published_at": date_range}})
    return filters


def truncate_content(content: str, max_length: int = 150) -> str:
    """截取内容作为摘要"""
    if not content:
        return ""
    # 移除多余空白
    content = ' '.join(content.split())
    if len(content) <= max_length:
        return content
    # 截取并添加省略号
    return content[:max_length].rsplit(' ', 1)[0] + "..."


def query_articles(page: int, size: int, source: Optional[str] = None,
                   category: Optional[str] = None, date_from: Optional[str] = None,
                   date_to: Optional[str] = None, sort: str = "published_at:desc") -> dict:
    """查询文章列表"""
    offset = (page - 1) * size

    # 解析排序
    sort_field, sort_order = sort.split(":") if ":" in sort else (sort, "desc")

    # 构建查询体 - 包含 content 用于生成摘要，包含 fetched_at 用于显示收录日期
    query_body = {
        "size": size,
        "from": offset,
        "sort": [{sort_field: {"order": sort_order}}],
        "_source": {"excludes": ["embedding"]}  # 只排除向量字段
    }

    # 添加过滤条件
    filters = build_filters(source, category, date_from, date_to)
    if filters:
        query_body["query"] = {"bool": {"filter": filters}}
    else:
        query_body["query"] = {"match_all": {}}

    # 执行查询
    response = storage.client.search(index=storage.index_name, body=query_body)

    total = response['hits']['total']['value']
    articles = []
    for hit in response['hits']['hits']:
        doc = hit['_source']
        doc['_id'] = hit['_id']
        # 生成摘要
        if 'content' in doc:
            doc['summary'] = truncate_content(doc['content'], 150)
            del doc['content']  # 删除完整内容，只保留摘要
        articles.append(doc)

    return {
        "data": articles,
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size if total > 0 else 1
    }


def get_article_by_id(doc_id: str) -> Optional[dict]:
    """根据文档 ID 获取文章"""
    try:
        response = storage.client.get(index=storage.index_name, id=doc_id)
        doc = response['_source']
        doc['_id'] = response['_id']
        # 移除 embedding 字段
        doc.pop('embedding', None)
        return doc
    except Exception as e:
        print(f"[Web] 获取文章失败: {e}")
        return None


def execute_search(q: str, mode: str, page: int, size: int,
                   source: Optional[str], category: Optional[str]) -> dict:
    """执行搜索"""
    # 构建过滤条件
    filters = {}
    if source:
        filters['source'] = source
    if category:
        filters['category'] = category

    # 计算需要的总数量 (用于分页)
    top_k = page * size

    # 根据模式选择搜索方法
    if mode == "fulltext":
        results = search.full_text_search(q, top_k, filters or None)
    elif mode == "hybrid":
        results = search.hybrid_search(q, top_k, filters or None)
    else:  # semantic
        results = search.search(q, top_k, filters or None)

    # 手动分页
    start = (page - 1) * size
    end = start + size
    paged_results = results[start:end]

    return {
        "data": paged_results,
        "total": len(results),
        "page": page,
        "size": size,
        "pages": (len(results) + size - 1) // size if results else 1,
        "query": q,
        "mode": mode
    }


# ============================================================
# 登录路由
# ============================================================

@app.get("/login", response_class=HTMLResponse)
async def page_login(request: Request, error: Optional[str] = None):
    """登录页面"""
    # 如果已登录，重定向到首页
    if get_current_user(request):
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": error
    })


@app.post("/login")
async def do_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    """处理登录"""
    user = verify_user(username, password)
    if user:
        request.session["user"] = user
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": "用户名或密码错误"
    })


@app.get("/logout")
async def do_logout(request: Request):
    """退出登录"""
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


# ============================================================
# 页面路由 (HTML) - 需要登录
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def page_index(
    request: Request,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    source: Optional[str] = None,
    category: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
):
    """文章列表首页"""
    # 检查登录
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    articles = query_articles(page, size, source, category, date_from, date_to)
    sources = search.list_sources()
    categories = search.list_categories()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "user": user,
        "articles": articles,
        "sources": sources,
        "categories": categories,
        "page": page,
        "size": size,
        "current_source": source,
        "current_category": category,
        "date_from": date_from,
        "date_to": date_to
    })


@app.get("/article/{doc_id}", response_class=HTMLResponse)
async def page_article(request: Request, doc_id: str):
    """文章详情页"""
    # 检查登录
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    article = get_article_by_id(doc_id)
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    return templates.TemplateResponse("article.html", {
        "request": request,
        "user": user,
        "article": article
    })


@app.get("/search", response_class=HTMLResponse)
async def page_search(
    request: Request,
    q: str = "",
    mode: str = Query("semantic", pattern="^(semantic|fulltext|hybrid)$"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    source: Optional[str] = None,
    category: Optional[str] = None
):
    """搜索结果页"""
    # 检查登录
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    results = {"items": [], "total": 0, "page": 1, "size": size, "pages": 1, "query": q, "mode": mode}

    if q:
        results = execute_search(q, mode, page, size, source, category)

    sources = search.list_sources()
    categories = search.list_categories()

    return templates.TemplateResponse("search.html", {
        "request": request,
        "user": user,
        "results": results,
        "sources": sources,
        "categories": categories,
        "query": q,
        "mode": mode,
        "page": page,
        "size": size,
        "current_source": source,
        "current_category": category
    })


# ============================================================
# API 路由 (JSON) - 需要登录
# ============================================================

def api_auth(request: Request):
    """API 认证检查"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="未授权，请先登录")
    return user


@app.get("/api/articles")
async def api_list_articles(
    request: Request,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    source: Optional[str] = None,
    category: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    sort: str = Query("published_at:desc")
):
    """文章列表 API"""
    api_auth(request)
    return query_articles(page, size, source, category, date_from, date_to, sort)


@app.get("/api/articles/{doc_id}")
async def api_get_article(request: Request, doc_id: str):
    """获取单篇文章 API"""
    api_auth(request)
    article = get_article_by_id(doc_id)
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    return article


@app.get("/api/search")
async def api_search(
    request: Request,
    q: str,
    mode: str = Query("semantic", pattern="^(semantic|fulltext|hybrid)$"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    source: Optional[str] = None,
    category: Optional[str] = None
):
    """搜索 API"""
    api_auth(request)
    return execute_search(q, mode, page, size, source, category)


@app.get("/api/stats")
async def api_stats(request: Request):
    """统计信息 API"""
    api_auth(request)
    return storage.get_stats()


@app.get("/api/filters")
async def api_filters(request: Request):
    """获取过滤选项 API"""
    api_auth(request)
    return {
        "sources": search.list_sources(),
        "categories": search.list_categories()
    }


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    uvicorn.run(
        "web:app",
        host="0.0.0.0",
        port=8080,
        reload=False,
        access_log=True
    )
