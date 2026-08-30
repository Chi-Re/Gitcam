# gitcam 校园代码托管分享交流平台

> 基于 Python Flask + Vue 3 的校园代码托管与社区讨论平台（已完成第 2 阶段 MVP + 第 3 阶段论坛）
> 核心理念：**"代码即讨论上下文，讨论即代码注解"**

## 功能范围（已实现）

| 模块 | 功能 |
|---|---|
| 用户系统 | 注册（邮箱/学号/角色）、登录（JWT）、个人资料、角色权限（学生/教师/管理员） |
| 项目管理 | 5 种项目模板、公开/私有可见性、成员管理（Owner/Developer/Viewer）、标签/语言、搜索 |
| 代码仓库 | Git 裸仓库托管、**真实 git clone/push（smart HTTP）**、**GitHub 风格侧边栏文件树（"文件树"按钮唤出、默认收起、懒加载展开/折叠、Go to file 文件名搜索、目录/文件统计、当前路径高亮、分支联动、移动端抽屉）** + 右侧文件列表/README/内嵌文件预览（vscode-icons 彩色图标、行级讨论标记）、提交历史、提交级 Diff、分支/标签管理、提交对比 |
| 动态聚合 | 项目动态流（提交/成员/项目/帖子事件，可筛选类型） |
| **论坛（第 3 阶段核心）** | 发帖/回帖（Markdown）、分类标签、@提及（触发通知）、投票、问题采纳（自动标记已解决）、帖子状态流转 |
| **代码片段** | 编辑器内从仓库文件树选文件一键插入高亮代码块（自动识别语言、记录行号），支持图片插入（MinIO 直传） |
| **讨论绑定（双向可达）** | 帖子/回帖可绑定 Commit / 文件 / 具体行；仓库 blob 预览页显示行级讨论标记、提交详情页显示关联讨论，双向跳转 |
| **社区论坛（全站板块）** | 独立社区板块（浏览公开、操作需登录）：发帖/回帖、分类、搜索（标题+内容）、投票、采纳、@提及通知、图片上传；**代码引用仅限公共仓库**（含来源仓库跳转链接，私有仓库接口级拦截） |
| **Issue 系统** | 创建/编辑/关闭、状态流转（Open→In Progress→Resolved→Closed，支持 reopen）、优先级/标签/指派人/里程碑、评论讨论、**提交信息 "fix #N" 自动关联并自动解决** |
| **Wiki** | 多页面树导航、Markdown 编辑/预览、**每次编辑保留版本快照、可回滚** |
| 通知 | 站内收件箱（被评论/@提及/Issue 变更/仓库动态/Wiki 更新，全事件源接入）+ 偏好配置 + 站点通知总开关 + 可配置 SMTP 邮件（未配置自动降级） |
| 对象存储 | MinIO 预签名 URL 上传/下载（图片/大文件） |
| **管理员后台** | 用户管理（搜索/改角色/封禁）、内容管理（删违规项目/帖子/评论）、系统配置（公告/通知开关/存储配额）、日志审计（登录日志+敏感操作日志） |
| 部署 | **Docker 一键部署**（web-nginx / backend-gunicorn / MySQL / MinIO，`scripts/deploy.sh`） |

## 技术栈

- 前端：Vue 3 + TypeScript + Vite + Element Plus + Pinia + Vue Router + highlight.js + marked
- 后端：Python Flask + Flask-SQLAlchemy + flask-jwt-extended + GitPython + MinIO SDK
- 存储：MySQL 8（结构化数据）、Git 裸仓库（本地磁盘）、MinIO（二进制/大文件）
- 部署：Docker Compose（MySQL + MinIO）

## 目录结构

```
├── docker-compose.yml        # MySQL 8 + MinIO
├── backend/                  # Flask API
│   ├── app/
│   │   ├── models/           # 数据模型
│   │   ├── services/         # git_service / storage / mail / notification / activity
│   │   ├── api/              # auth / users / projects / repos / git_http / storage_api
│   │   └── config.py         # 环境变量配置
│   └── run.py
├── frontend/                 # Vue 3 SPA
│   └── src/
│       ├── router/           # 路由 + 守卫
│       ├── stores/           # Pinia
│       ├── api/              # 接口封装
│       └── views/            # 页面
└── scripts/                  # 启动与验证脚本
```

## 快速启动

```bash
# 1. 一键启动（Docker 基础设施 + 后端 + 前端）
bash scripts/start_all.sh

# 2. 手动分步启动
docker-compose up -d                                  # MySQL + MinIO
bash scripts/start_backend.sh                         # Flask API :5000
cd frontend && npm install && npm run dev             # Vite :5173
```

- 前端：http://127.0.0.1:5173
- 后端：http://127.0.0.1:5000
- MinIO 控制台：http://127.0.0.1:9001（`gitcam_minio` / `gitcam_minio_dev`）
- 默认管理员：`admin` / `admin123`（生产环境务必修改）

## 端到端验证

```bash
bash scripts/e2e_test.sh
```

验证链路：注册 → 登录 → 创建项目（自动初始化仓库）→ 真实 `git clone` → 修改 → `git commit` → `git push` → 平台可见提交/Diff/动态流 → 越权访问 401/403。

## 文件类型图标

- 使用 VS Code 官方图标集（`@iconify-json/vscode-icons`，网络下载安装）。
- 由 `scripts/generate_file_icons.mjs` 提取 **78 个常用类型图标**（代码/文档/图片/音频/视频/压缩包/配置文件等 + 特殊文件名如 Dockerfile/.gitignore）生成 `frontend/src/assets/fileIcons.ts`，构建时内联打包、运行时完全离线。
- 应用于：仓库文件树、帖子代码片段选择器、提交 Diff 文件列表、Wiki 页面列表。
- 新增类型后重新运行 `node scripts/generate_file_icons.mjs` 并补充映射即可。

## Git 使用示例

```bash
git clone http://<服务器>:5000/git/<项目标识>.git
# 或通过前端代理
git clone http://<服务器>:5173/git/<项目标识>.git
cd <项目标识>
# 修改文件...
git add -A
git commit -m "完成实验一"
git push
```

账号密码即平台注册账号（用户名/邮箱/学号 + 密码）。写权限需为项目 Developer/Owner。

## 邮件通知配置

后端启动前设置环境变量（见 `backend/.env.example`）：

```
MAIL_ENABLED=true
MAIL_SMTP_HOST=smtp.xxx.edu.cn
MAIL_SMTP_PORT=465
MAIL_SMTP_USER=your_account
MAIL_SMTP_PASSWORD=your_password
```

未配置时通知自动降级为仅站内收件箱。

## 默认分支与模板

- 新项目默认分支为 `main`，创建时按模板自动生成初始提交（README 等）。
- 模板：课程作业 / 毕业设计 / 创新创业 / 兴趣小组 / 空项目。

## 后续阶段规划（按《项目开发计划_提示词》）

第 3 阶段已完成（论坛 / Issue / Wiki / 动态流全量接入）。
第 4 阶段已完成（通知全量接入 / 管理员后台 / 性能优化与压测 / Docker 一键部署）。
第 5-6 阶段：试点部署、教学评议、正式文档（《系统设计说明书》《结题报告》）。
