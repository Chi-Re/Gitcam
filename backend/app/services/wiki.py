"""Wiki 服务：页面树/编辑快照/回滚"""

from app.extensions import db
from app.models import WikiPage, WikiVersion


def build_page_tree(pages):
    """按 path 构建分层树：pages 为 WikiPage 列表"""
    root = []
    for page in pages:
        parts = page.path.split("/")
        root.append(
            {
                "id": page.id,
                "path": page.path,
                "title": page.title,
                "version": page.version,
                "depth": len(parts) - 1,
                "segments": parts,
            }
        )
    return sorted(root, key=lambda p: (p["path"].lower(), p["id"]))


def save_page_edit(page, content, title, editor_id):
    """保存编辑：写入版本快照并 version+1"""
    db.session.add(
        WikiVersion(
            page_id=page.id,
            version=page.version,
            content=page.content,
            editor_id=page.editor_id,
        )
    )
    page.content = content
    page.title = title
    page.editor_id = editor_id
    page.version += 1
    return page


def rollback_page(page, target_version, editor_id):
    """回滚到指定版本：目标版本内容写入当前页，并生成新版本快照"""
    target = WikiVersion.query.filter_by(page_id=page.id, version=target_version).first()
    if target is None:
        raise ValueError("版本不存在")
    save_page_edit(page, target.content, page.title, editor_id)
    return page
