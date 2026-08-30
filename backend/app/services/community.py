"""社区论坛服务：渲染（含来源公共仓库链接）/投票/采纳/@提及/片段"""

import re

from sqlalchemy import or_
from markupsafe import escape

from app.extensions import db
from app.models import (
    CommunityPost,
    CommunityReply,
    CommunityVote,
    CommunitySnippet,
    User,
    Project,
)

SNIPPET_RE = re.compile(r":::snippet:(\d+):::")
MENTION_RE = re.compile(r"@([A-Za-z0-9_.-]{2,32})")

# 语言推断（与项目论坛一致）
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
    names = set(MENTION_RE.findall(content or ""))
    return [u for u in User.query.filter(User.username.in_(names)).all() if u]


def render_post_content(obj):
    """渲染正文：占位符→高亮代码块+来源公共仓库标注与链接"""
    content = obj.content or ""
    snippets = {s.id: s for s in obj.snippets}

    def replace(m):
        s = snippets.get(int(m.group(1)))
        if not s:
            return ""
        header = ""
        if s.file_path:
            header = f'<div class="snippet-source">📄 {escape(s.file_path)}'
            if s.start_line:
                header += f'（第 {s.start_line}-{s.end_line or s.start_line} 行）'
            if s.project:
                header += (
                    f' · 来源仓库：<a class="snippet-repo" '
                    f'href="#!repo:{escape(s.project.slug)}:path:{escape(s.file_path)}">'
                    f"{escape(s.project.name)}</a>"
                )
            header += "</div>"
        body = escape(s.content).replace("\n", "<br>")
        return (
            f'<div class="post-snippet"><div class="snippet-lang">{escape(s.language)}</div>'
            f"{header}<pre><code class=\"snippet-code\">{body}</code></pre></div>"
        )

    return SNIPPET_RE.sub(replace, _esc_with_mentions(content))


def _esc_with_mentions(content):
    content = escape(content)
    return MENTION_RE.sub(lambda m: f'<a class="mention" href="#!user:{m.group(1)}">@{m.group(1)}</a>', content)


# ---------- 公共仓库校验 ----------

def public_project_or_none(project_id):
    """仅允许引用公共仓库；私有仓库返回 None"""
    if not project_id:
        return None
    project = Project.query.get(project_id)
    if project is None or project.visibility != "public":
        return None
    return project


# ---------- 投票 / 采纳 ----------

def toggle_vote(user_id, target_type, target_id):
    if target_type == "post":
        obj = CommunityPost.query.get(target_id)
    elif target_type == "reply":
        obj = CommunityReply.query.get(target_id)
    else:
        raise ValueError("投票目标类型不合法")
    vote = CommunityVote.query.filter_by(
        user_id=user_id, target_type=target_type, target_id=target_id
    ).first()
    if vote:
        db.session.delete(vote)
        obj.vote_count = max(0, obj.vote_count - 1)
        voted = False
    else:
        db.session.add(CommunityVote(user_id=user_id, target_type=target_type, target_id=target_id))
        obj.vote_count += 1
        voted = True
    return obj.vote_count, voted


def can_manage_post(user, post):
    """作者/教师/管理员 可采纳与改状态"""
    if user is None:
        return False
    if user.role in ("teacher", "admin"):
        return True
    return post.author_id == user.id


def accept_reply(user, post, reply):
    if not can_manage_post(user, post):
        raise PermissionError("仅作者或教师可以采纳回答")
    for r in CommunityReply.query.filter_by(post_id=post.id, is_accepted=True).all():
        r.is_accepted = False
    reply.is_accepted = True
    post.accepted_reply_id = reply.id
    post.status = "solved"
    return True


def set_post_status(user, post, status):
    if status not in ("open", "solved", "closed"):
        raise ValueError("状态不合法")
    if not can_manage_post(user, post):
        raise PermissionError("仅作者或教师可以修改状态")
    post.status = status
    return True


# ---------- 查询 ----------

def query_posts(category=None, status=None, q=None, sort="latest", page=1, per_page=20):
    query = CommunityPost.query
    if category and category != "all":
        query = query.filter_by(category=category)
    if status and status != "all":
        query = query.filter_by(status=status)
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(CommunityPost.title.like(like), CommunityPost.content.like(like))
        )
    total = query.count()
    if sort == "votes":
        query = query.order_by(CommunityPost.vote_count.desc(), CommunityPost.id.desc())
    else:
        query = query.order_by(CommunityPost.created_at.desc(), CommunityPost.id.desc())
    posts = query.offset((page - 1) * per_page).limit(per_page).all()
    return total, posts


def batch_my_votes(user_id, post_ids):
    """批量查询当前用户对帖子列表的投票状态"""
    if not user_id or not post_ids:
        return set()
    return {
        v.target_id
        for v in CommunityVote.query.filter(
            CommunityVote.user_id == user_id,
            CommunityVote.target_type == "post",
            CommunityVote.target_id.in_(post_ids),
        ).all()
    }
