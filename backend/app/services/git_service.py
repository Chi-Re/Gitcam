"""Git 操作统一封装（基于 GitPython），向上提供仓库管理能力。

每个项目对应一个 bare 仓库，路径为 REPO_ROOT/{project_id}.git
"""

import os
import re
from datetime import datetime, timezone

import git
from flask import current_app

from app.models.activity import ActivityEvent

DEFAULT_BRANCH = "main"


class GitServiceError(Exception):
    pass


class GitService:
    def __init__(self, repo_path):
        self.repo_path = repo_path
        self._repo = None

    @property
    def repo(self):
        if self._repo is None:
            self._repo = git.Repo(self.repo_path)
        return self._repo

    # ---------- 仓库生命周期 ----------

    @classmethod
    def create_bare(cls, project_id, default_branch=DEFAULT_BRANCH):
        """创建 bare 仓库并初始化默认分支的初始提交（含模板 README）"""
        repo_root = current_app.config["REPO_ROOT"]
        os.makedirs(repo_root, exist_ok=True)
        repo_path = os.path.join(repo_root, f"{project_id}.git")
        if os.path.exists(repo_path):
            raise GitServiceError("仓库已存在")
        repo = git.Repo.init(repo_path, bare=True)
        # 设置默认分支 HEAD
        head_file = os.path.join(repo_path, "HEAD")
        with open(head_file, "w", encoding="utf-8") as f:
            f.write(f"ref: refs/heads/{default_branch}\n")
        repo.git.config("core.bare", "true")
        repo.git.config("http.receivepack", "true")
        return cls(repo_path)

    @classmethod
    def open(cls, project_id):
        repo_path = os.path.join(current_app.config["REPO_ROOT"], f"{project_id}.git")
        if not os.path.isdir(repo_path):
            raise GitServiceError("仓库不存在")
        return cls(repo_path)

    @classmethod
    def exists(cls, project_id):
        repo_path = os.path.join(current_app.config["REPO_ROOT"], f"{project_id}.git")
        return os.path.isdir(repo_path)

    def ensure_initial_commit(self, files, message, author_name, author_email):
        """向新仓库写入初始提交（模板文件），返回 commit sha"""
        if not self.repo.head.is_valid() and not self.repo.branches:
            init_dir = f"{self.repo_path}_work"
            os.makedirs(init_dir, exist_ok=True)
            for path, content in files.items():
                full = os.path.join(init_dir, path)
                os.makedirs(os.path.dirname(full) or init_dir, exist_ok=True)
                if content is not None:
                    with open(full, "w", encoding="utf-8") as f:
                        f.write(content)
            work_repo = git.Repo.init(init_dir)
            work_repo.index.add(list(files.keys()))
            work_repo.index.commit(
                message, author=git.Actor(author_name, author_email), committer=git.Actor(author_name, author_email)
            )
            # bare 仓库接收 push
            self.repo.git.config("receive.denyCurrentBranch", "ignore")
            work_repo.git.push(self.repo_path, f"HEAD:refs/heads/{DEFAULT_BRANCH}")
            sha = work_repo.head.commit.hexsha
            import shutil
            shutil.rmtree(init_dir, ignore_errors=True)
            return sha
        return None

    # ---------- 分支与标签 ----------

    def list_branches(self):
        branches = []
        for b in self.repo.branches:
            branches.append(
                {
                    "name": b.name,
                    "commit_sha": b.commit.hexsha,
                    "commit_message": b.commit.message.strip().split("\n")[0],
                    "author_name": b.commit.author.name,
                    "committed_at": _iso(b.commit.committed_datetime),
                    "is_default": b.name == (self.repo.active_branch.name if not self.repo.head.is_detached and self.repo.active_branch else DEFAULT_BRANCH),
                }
            )
        branches.sort(key=lambda x: x["committed_at"], reverse=True)
        return branches

    def default_branch(self):
        try:
            if self.repo.head.is_valid() and not self.repo.head.is_detached:
                return self.repo.active_branch.name
        except Exception:
            pass
        try:
            for b in self.repo.branches:
                return b.name
        except Exception:
            return DEFAULT_BRANCH

    def list_tags(self):
        tags = []
        for t in self.repo.tags:
            commit = t.commit
            tags.append(
                {
                    "name": t.name,
                    "commit_sha": commit.hexsha,
                    "commit_message": commit.message.strip().split("\n")[0],
                    "committed_at": _iso(commit.committed_datetime),
                }
            )
        tags.sort(key=lambda x: x["committed_at"], reverse=True)
        return tags

    def create_branch(self, name, source_branch=None, actor=None):
        if not re.fullmatch(r"[\w./-]+", name or ""):
            raise GitServiceError("分支名不合法")
        try:
            if source_branch:
                ref = self.repo.refs[source_branch]
                self.repo.create_head(name, ref.commit)
            else:
                self.repo.create_head(name)
        except git.GitCommandError as e:
            raise GitServiceError(str(e))
        return {"name": name}

    def delete_branch(self, name):
        if name == self.default_branch():
            raise GitServiceError("不能删除默认分支")
        try:
            head = self.repo.heads[name]
            head.delete(self.repo, head)
        except (IndexError, git.GitCommandError) as e:
            raise GitServiceError(str(e))
        return True

    # ---------- 提交历史 ----------

    def commit_log(self, branch=None, path=None, page=1, per_page=50, keyword=None):
        kwargs = {"max_count": per_page, "skip": (page - 1) * per_page}
        if branch and branch != "all":
            kwargs["rev"] = branch
        if path:
            kwargs["paths"] = path
        commits = list(self.repo.iter_commits(**kwargs))
        result = []
        for c in commits:
            if keyword and keyword.lower() not in (c.message or "").lower():
                continue
            result.append(self._commit_dict(c))
        return result

    def commit_detail(self, sha):
        try:
            c = self.repo.commit(sha)
        except (git.BadName, ValueError) as e:
            raise GitServiceError("提交不存在")
        return self._commit_dict(c, detail=True)

    def _commit_dict(self, c, detail=False):
        data = {
            "sha": c.hexsha,
            "short_sha": c.hexsha[:8],
            "message": c.message.strip(),
            "author_name": c.author.name,
            "author_email": c.author.email,
            "authored_at": _iso(c.authored_datetime),
            "committed_at": _iso(c.committed_datetime),
            "parents": [p.hexsha for p in c.parents],
        }
        if detail:
            diff = self.diff_commit(c)
            data["diff_stat"] = diff["stat"]
            data["diff"] = diff["files"]
        return data

    # ---------- Diff ----------

    def diff_commit(self, commit):
        """提交与其父提交的 diff（文件级，parent→commit 方向）"""
        if len(commit.parents) == 0:
            diff_index = commit.diff(git.NULL_TREE, create_patch=True)
        else:
            diff_index = commit.parents[0].diff(commit, create_patch=True)
        return self._diff_to_dict(diff_index, commit.hexsha)

    def diff_commits(self, sha_a, sha_b):
        """两个提交/分支之间的 diff"""
        try:
            commit_a = self.repo.commit(sha_a)
            commit_b = self.repo.commit(sha_b)
        except (git.BadName, ValueError) as e:
            raise GitServiceError("提交不存在")
        diff_index = commit_a.diff(commit_b, create_patch=True)
        return self._diff_to_dict(diff_index, sha_b)

    def _diff_to_dict(self, diff_index, target_sha):
        stat = {"additions": 0, "deletions": 0, "files_changed": 0}
        files = []
        for d in diff_index:
            old_path = d.a_path or (d.a_blob.path if d.a_blob else None)
            new_path = d.b_path or (d.b_blob.path if d.b_blob else None)
            if d.change_type == "R":
                old_path = d.rename_from if hasattr(d, "rename_from") and d.rename_from else old_path
                new_path = d.rename_to if hasattr(d, "rename_to") and d.rename_to else new_path
            change_type = d.change_type or (
                "A" if (d.b_blob and not d.a_blob) else ("D" if (d.a_blob and not d.b_blob) else "M")
            )
            try:
                patch = d.diff.decode("utf-8", errors="replace") if isinstance(d.diff, bytes) else str(d.diff or "")
            except Exception:
                patch = ""
            additions = len([l for l in patch.splitlines() if l.startswith("+") and not l.startswith("+++")])
            deletions = len([l for l in patch.splitlines() if l.startswith("-") and not l.startswith("---")])
            stat["additions"] += additions
            stat["deletions"] += deletions
            stat["files_changed"] += 1
            files.append(
                {
                    "old_path": old_path,
                    "new_path": new_path,
                    "change_type": change_type,
                    "additions": additions,
                    "deletions": deletions,
                    "patch": patch,
                }
            )
        return {"stat": stat, "files": files}

    # ---------- 文件树 ----------

    def file_tree(self, branch=None, path="", ref=None):
        """返回目录条目列表；path 为空返回根目录"""
        commit = self._resolve_commit(branch, ref)
        path = path.strip("/")
        try:
            tree = commit.tree / path if path else commit.tree
        except KeyError:
            raise GitServiceError("路径不存在")
        entries = []
        for item in tree:
            entry = {
                "name": item.name,
                "type": "tree" if item.type == "tree" else "blob",
                "path": item.path,
                "size": None,
            }
            if item.type == "blob":
                entry["size"] = item.size
                last = self._last_commit_for_path(commit, item.path)
                if last:
                    entry["last_commit_sha"] = last.hexsha[:8]
                    entry["last_commit_message"] = last.message.strip().split("\n")[0]
                    entry["last_committed_at"] = _iso(last.committed_datetime)
                    entry["last_author"] = last.author.name
            entries.append(entry)
        entries.sort(key=lambda x: (x["type"] != "tree", x["name"].lower()))
        return entries

    def blob_content(self, path, branch=None, ref=None):
        commit = self._resolve_commit(branch, ref)
        path = path.strip("/")
        try:
            blob = commit.tree / path
        except KeyError:
            raise GitServiceError("路径不存在")
        if blob.type != "blob":
            raise GitServiceError("路径不是文件")
        return blob.data_stream.read(), blob.size

    def _resolve_commit(self, branch=None, ref=None):
        rev = ref or branch or self.default_branch()
        try:
            return self.repo.commit(rev)
        except (git.BadName, ValueError, IndexError):
            raise GitServiceError("分支或引用不存在")

    def _last_commit_for_path(self, commit, path):
        """路径最后修改提交（git log -1 -- path）"""
        try:
            log = self.repo.git.log("-1", "--format=%H", commit.hexsha, "--", path)
            sha = log.strip()
            return self.repo.commit(sha) if sha else None
        except git.GitCommandError:
            return None

    # ---------- 归档/统计 ----------

    def repo_size(self):
        total = 0
        for dirpath, _, filenames in os.walk(self.repo_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if os.path.exists(fp):
                    total += os.path.getsize(fp)
        return total

    def total_commits(self):
        try:
            return len(list(self.repo.iter_commits("--all")))
        except Exception:
            return 0


def _iso(dt):
    """datetime -> ISO 字符串；git 返回 naive datetime 时补 UTC"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()
