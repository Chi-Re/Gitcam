"""帖子服务：发帖/回帖/投票/采纳/状态/@提及/内容渲染"""

import re

from sqlalchemy import or_

from app.extensions import db
from app.models import Post, PostReply, PostVote, CodeSnippet, DiscussionLink, User

SNIPPET_RE = re.compile(r":::snippet:(\d+):::")
MENTION_RE = re.compile(r"@([A-Za-z0-9_.-]{2,32})")

# 支持的语言->文件后缀推断（与前端高亮映射保持一致）
LANG_EXTS = {
    "python": [".py", ".pyw"],
    "javascript": [".js", ".mjs"],
    "typescript": [".ts", ".tsx"],
    "java": [".java"],
    "c": [".c", ".h"],
    "cpp": [".cpp", ".cc", ".hpp"],
    "go": [".go"],
    "rust": [".rs"],
    "ruby": [".rb"],
    "php": [".php"],
    "html": [".html", ".htm"],
    "css": [".css", ".scss"],
    "json": [".json"],
    "yaml": [".yml", ".yaml"],
    "xml": [".xml", ".vue"],
    "sql": [".sql"],
    "bash": [".sh", ".bash"],
    "markdown": [".md", ".markdown"],
    "ini": [".ini", ".toml", ".cfg"],
    "dockerfile": ["dockerfile", ".dockerfile"],
}


def guess_language(filename):
    lower = (filename or "").lower()
    for lang, exts in LANG_EXTS.items():
        for ext in exts:
            if lower.endswith(ext):
                return lang
    return "plaintext"


def parse_mentions(content):
    """解析 @username 列表"""
    names = set(MENTION_RE.findall(content or ""))
    return [u for u in User.query.filter(User.username.in_(names)).all() if u]


def create_snippet(post_id, reply_id, project_id, file_path, language, start_line, end_line, content):
    snippet = CodeSnippet(
        post_id=post_id,
        reply_id=reply_id,
        project_id=project_id,
        file_path=file_path,
        language=language,
        start_line=start_line,
        end_line=end_line,
        content=content,
    )
    db.session.add(snippet)
    db.session.flush()
    return snippet


def render_post_content(obj, viewer_id=None):
    """将正文中的 :::snippet:id::: 占位符替换为渲染后的 HTML（含来源标注）"""
    content = obj.content or ""
    snippets = {s.id: s for s in obj.snippets}

    def replace(m):
        sid = int(m.group(1))
        s = snippets.get(sid)
        if not s:
            return ""
        header = ""
        if s.file_path:
            header = f'<div class="snippet-source">📄 {_esc(s.file_path)}'
            if s.start_line:
                header += f'（第 {s.start_line}-{s.end_line or s.start_line} 行）'
            header += "</div>"
        body = _esc(s.content).replace("\n", "<br>")
        return (
            f'<div class="post-snippet"><div class="snippet-lang">{_esc(s.language)}</div>'
            f"{header}<pre><code class=\"snippet-code\">{body}</code></pre></div>"
        )

    return SNIPPET_RE.sub(replace, _esc_with_mentions(content))


def _esc_with_mentions(content):
    """转义 HTML，同时将 @username 渲染为可跳转链接"""
    from markupsafe import escape

    content = escape(content)

    def mention_replace(m):
        return f'<a class="mention" href="#!user:{m.group(1)}">@{m.group(1)}</a>'

    return MENTION_RE.sub(mention_replace, content)


def _esc(text):
    from markupsafe import escape

    return escape(text or "")


# ---------- 投票 ----------

def toggle_vote(user_id, target_type, target_id):
    """投票 toggle；返回 (vote_count, voted_now)"""
    if target_type == "post":
        obj = Post.query.get(target_id)
    elif target_type == "reply":
        obj = PostReply.query.get(target_id)
    else:
        raise ValueError("投票目标类型不合法")

    vote = PostVote.query.filter_by(
        user_id=user_id, target_type=target_type, target_id=target_id
    ).first()
    if vote:
        db.session.delete(vote)
        obj.vote_count = max(0, obj.vote_count - 1)
        voted = False
    else:
        db.session.add(PostVote(user_id=user_id, target_type=target_type, target_id=target_id))
        obj.vote_count += 1
        voted = True
    return obj.vote_count, voted


# ---------- 采纳与状态 ----------

def can_manage_post(user, project, post):
    """提问者/教师/管理员/项目Owner 可管理帖子状态"""
    from app.utils.decorators import is_owner_or_admin

    if user is None:
        return False
    if user.role in ("teacher", "admin"):
        return True
    if post.author_id == user.id:
        return True
    if is_owner_or_admin(project, user):
        return True
    return False


def accept_reply(user, project, post, reply):
    """采纳回答：提问者/教师/管理员；采纳后帖子自动标记已解决"""
    if not can_manage_post(user, project, post):
        raise PermissionError("仅提问者或教师可以采纳回答")
    # 取消旧的采纳
    old = PostReply.query.filter_by(post_id=post.id, is_accepted=True).all()
    for r in old:
        r.is_accepted = False
    reply.is_accepted = True
    post.accepted_reply_id = reply.id
    post.status = "solved"
    db.session.add(reply)
    return True


def set_post_status(user, project, post, status):
    if not can_manage_post(user, project, post):
        raise PermissionError("仅提问者或教师可以修改状态")
    if status not in ("open", "solved", "closed"):
        raise ValueError("状态不合法")
    post.status = status
    return True


# ---------- 查询 ----------

def query_posts(project_id, category=None, status=None, q=None, sort="latest", page=1, per_page=20):
    query = Post.query.filter_by(project_id=project_id)
    if category and category != "all":
        query = query.filter_by(category=category)
    if status and status != "all":
        query = query.filter_by(status=status)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Post.title.like(like), Post.content.like(like)))
    total = query.count()
    if sort == "votes":
        query = query.order_by(Post.vote_count.desc(), Post.id.desc())
    else:
        query = query.order_by(Post.created_at.desc(), Post.id.desc())
    posts = query.offset((page - 1) * per_page).limit(per_page).all()
    return total, posts
