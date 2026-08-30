import http from './http'

export interface User {
  id: number
  email: string
  student_id: string | null
  username: string
  full_name: string
  role: string
  college: string | null
  major_class: string | null
  bio: string | null
  avatar_url: string | null
  github_url: string | null
  gitee_url: string | null
  is_active: boolean
  created_at: string
}

export interface Project {
  id: number
  name: string
  slug: string
  description: string | null
  visibility: string
  template_type: string
  template_name: string
  default_branch: string
  language: string | null
  tags: string[]
  owner: User | null
  owner_id: number
  git_url: string
  created_at: string
  updated_at: string
  member_count: number
  members?: ProjectMember[]
  my_role?: string | null
  repo_size?: number | null
  commit_count?: number | null
}

export interface ProjectMember {
  id: number
  user_id: number
  username: string
  full_name: string
  avatar_url: string | null
  role: string
  created_at: string
}

export interface TreeEntry {
  name: string
  type: 'tree' | 'blob'
  path: string
  size: number | null
  last_commit_sha?: string | null
  last_commit_message?: string | null
  last_committed_at?: string | null
  last_author?: string | null
}

export interface CommitItem {
  sha: string
  short_sha: string
  message: string
  author_name: string
  author_email: string
  authored_at: string
  committed_at: string
  parents: string[]
  diff_stat?: { additions: number; deletions: number; files_changed: number }
  diff?: DiffFile[]
}

export interface DiffFile {
  old_path: string | null
  new_path: string | null
  change_type: string
  additions: number
  deletions: number
  patch: string
}

export interface Branch {
  name: string
  commit_sha: string
  commit_message: string
  author_name: string
  committed_at: string
  is_default: boolean
}

export interface ActivityItem {
  id: number
  project_id: number
  event_type: string
  action: string
  title: string
  ref_type: string | null
  ref_name: string | null
  commit_sha: string | null
  data: Record<string, unknown> | null
  actor: User | null
  created_at: string
}

export const authApi = {
  register: (data: Record<string, unknown>) => http.post('/auth/register', data),
  login: (data: Record<string, unknown>) => http.post('/auth/login', data),
  me: () => http.get('/auth/me'),
  updateProfile: (data: Record<string, unknown>) => http.put('/auth/profile', data),
}

export interface ReplyHistoryItem {
  id: number
  scope: 'project' | 'community'
  project_id: number | null
  project_slug: string | null
  post_id: number
  post_title: string
  reply_id: number
  content_snippet: string | null
  post_exists: boolean
  created_at: string
}

export const userApi = {
  publicProfile: (username: string) => http.get(`/users/${username}`),
  notifications: (params?: Record<string, unknown>) =>
    http.get('/users/me/notifications', { params }),
  readNotification: (data: Record<string, unknown>) =>
    http.post('/users/me/notifications/read', data),
  deleteNotification: (notificationId: number) =>
    http.delete(`/users/me/notifications/${notificationId}`),
  clearNotifications: () => http.delete('/users/me/notifications'),
  replyHistory: (params: Record<string, unknown>) =>
    http.get('/users/me/reply-history', { params }),
  prefs: () => http.get('/users/me/notification-prefs'),
  updatePrefs: (data: Record<string, unknown>) =>
    http.put('/users/me/notification-prefs', data),
}

export const projectApi = {
  templates: () => http.get('/projects/templates'),
  list: (params: Record<string, unknown>) => http.get('/projects', { params }),
  create: (data: Record<string, unknown>) => http.post('/projects', data),
  get: (slug: string) => http.get(`/projects/${slug}`),
  update: (slug: string, data: Record<string, unknown>) => http.put(`/projects/${slug}`, data),
  remove: (slug: string) => http.delete(`/projects/${slug}`),
  members: (slug: string) => http.get(`/projects/${slug}/members`),
  addMember: (slug: string, data: Record<string, unknown>) =>
    http.post(`/projects/${slug}/members`, data),
  updateMember: (slug: string, userId: number, data: Record<string, unknown>) =>
    http.put(`/projects/${slug}/members/${userId}`, data),
  removeMember: (slug: string, userId: number) =>
    http.delete(`/projects/${slug}/members/${userId}`),
  activities: (slug: string, params?: Record<string, unknown>) =>
    http.get(`/projects/${slug}/activities`, { params }),
}

export const repoApi = {
  tree: (slug: string, params: Record<string, unknown>) =>
    http.get(`/projects/${slug}/repo/tree`, { params }),
  treeIndex: (slug: string, params: Record<string, unknown>) =>
    http.get(`/projects/${slug}/repo/tree-index`, { params }),
  blob: (slug: string, params: Record<string, unknown>) =>
    http.get(`/projects/${slug}/repo/blob`, { params }),
  raw: (slug: string, params: Record<string, unknown>) =>
    http.get(`/projects/${slug}/repo/raw`, { params, responseType: 'blob' }),
  commits: (slug: string, params: Record<string, unknown>) =>
    http.get(`/projects/${slug}/repo/commits`, { params }),
  commitDetail: (slug: string, sha: string) =>
    http.get(`/projects/${slug}/repo/commits/${sha}`),
  diff: (slug: string, params: Record<string, unknown>) =>
    http.get(`/projects/${slug}/repo/diff`, { params }),
  branches: (slug: string) => http.get(`/projects/${slug}/repo/branches`),
  createBranch: (slug: string, data: Record<string, unknown>) =>
    http.post(`/projects/${slug}/repo/branches`, data),
  deleteBranch: (slug: string, name: string) =>
    http.delete(`/projects/${slug}/repo/branches/${name}`),
  tags: (slug: string) => http.get(`/projects/${slug}/repo/tags`),
}

export interface DiscussionLinkItem {
  id: number
  project_id: number
  post_id: number
  post_title: string | null
  reply_id: number | null
  commit_sha: string | null
  file_path: string | null
  line_start: number | null
  line_end: number | null
  created_at: string
  post?: {
    id: number
    title: string
    category: string
    author: User | null
    created_at: string
    status: string
  }
  context?: {
    kind: string | null
    commit?: CommitItem | null
    sha?: string
    file_path?: string | null
    line_start?: number | null
    line_end?: number | null
    code?: string | null
    total_lines?: number
  }
}

export interface Post {
  id: number
  project_id: number
  title: string
  category: string
  category_label: string
  status: string
  accepted_reply_id: number | null
  vote_count: number
  reply_count: number
  my_vote: boolean
  author: User | null
  created_at: string
  updated_at: string
  content?: string
  content_rendered?: string
  snippets?: CodeSnippet[]
  discussion_links?: DiscussionLinkItem[]
  replies?: PostReply[]
}

export interface PostReply {
  id: number
  post_id: number
  content: string
  content_rendered: string
  is_accepted: boolean
  vote_count: number
  my_vote: boolean
  author: User | null
  created_at: string
  discussion_links: DiscussionLinkItem[]
}

export interface CodeSnippet {
  id: number
  post_id: number | null
  reply_id: number | null
  project_id: number
  file_path: string | null
  language: string
  start_line: number | null
  end_line: number | null
  content: string
}

export const postsApi = {
  list: (slug: string, params: Record<string, unknown>) =>
    http.get(`/projects/${slug}/posts`, { params }),
  create: (slug: string, data: Record<string, unknown>) =>
    http.post(`/projects/${slug}/posts`, data),
  get: (slug: string, postId: number) => http.get(`/projects/${slug}/posts/${postId}`),
  update: (slug: string, postId: number, data: Record<string, unknown>) =>
    http.put(`/projects/${slug}/posts/${postId}`, data),
  remove: (slug: string, postId: number) => http.delete(`/projects/${slug}/posts/${postId}`),
  vote: (slug: string, postId: number) => http.post(`/projects/${slug}/posts/${postId}/vote`),
  changeStatus: (slug: string, postId: number, status: string) =>
    http.post(`/projects/${slug}/posts/${postId}/status`, { status }),
  createReply: (slug: string, postId: number, data: Record<string, unknown>) =>
    http.post(`/projects/${slug}/posts/${postId}/replies`, data),
  updateReply: (slug: string, postId: number, replyId: number, data: Record<string, unknown>) =>
    http.put(`/projects/${slug}/posts/${postId}/replies/${replyId}`, data),
  deleteReply: (slug: string, postId: number, replyId: number) =>
    http.delete(`/projects/${slug}/posts/${postId}/replies/${replyId}`),
  voteReply: (slug: string, postId: number, replyId: number) =>
    http.post(`/projects/${slug}/posts/${postId}/replies/${replyId}/vote`),
  acceptReply: (slug: string, postId: number, replyId: number) =>
    http.post(`/projects/${slug}/posts/${postId}/replies/${replyId}/accept`),
}

export const discussionApi = {
  query: (slug: string, params: Record<string, unknown>) =>
    http.get(`/projects/${slug}/discussion-links`, { params }),
}

export interface Issue {
  id: number
  number: number
  project_id: number
  title: string
  status: string
  status_label: string
  priority: string
  priority_label: string
  labels: string[]
  assignee: User | null
  milestone: string | null
  creator: User | null
  comment_count: number
  created_at: string
  updated_at: string
  closed_at: string | null
  description?: string | null
  comments?: IssueComment[]
  commits?: IssueCommitLink[]
}

export interface IssueComment {
  id: number
  issue_id: number
  content: string
  author: User | null
  created_at: string
}

export interface IssueCommitLink {
  id: number
  issue_id: number
  commit_sha: string
  linked_by: string | null
  created_at: string
}

export interface WikiPage {
  id: number
  project_id: number
  path: string
  title: string
  version: number
  editor: User | null
  created_at: string
  updated_at: string
  content?: string
}

export interface WikiVersion {
  id: number
  page_id: number
  version: number
  content: string
  editor: User | null
  created_at: string
}

export const issuesApi = {
  list: (slug: string, params: Record<string, unknown>) =>
    http.get(`/projects/${slug}/issues`, { params }),
  create: (slug: string, data: Record<string, unknown>) =>
    http.post(`/projects/${slug}/issues`, data),
  get: (slug: string, issueId: number) => http.get(`/projects/${slug}/issues/${issueId}`),
  update: (slug: string, issueId: number, data: Record<string, unknown>) =>
    http.put(`/projects/${slug}/issues/${issueId}`, data),
  remove: (slug: string, issueId: number) => http.delete(`/projects/${slug}/issues/${issueId}`),
  changeStatus: (slug: string, issueId: number, status: string) =>
    http.post(`/projects/${slug}/issues/${issueId}/status`, { status }),
  createComment: (slug: string, issueId: number, data: Record<string, unknown>) =>
    http.post(`/projects/${slug}/issues/${issueId}/comments`, data),
  deleteComment: (slug: string, issueId: number, commentId: number) =>
    http.delete(`/projects/${slug}/issues/${issueId}/comments/${commentId}`),
}

export const wikiApi = {
  tree: (slug: string) => http.get(`/projects/${slug}/wiki/tree`),
  get: (slug: string, pageId: number) => http.get(`/projects/${slug}/wiki/pages/${pageId}`),
  create: (slug: string, data: Record<string, unknown>) => http.post(`/projects/${slug}/wiki`, data),
  update: (slug: string, pageId: number, data: Record<string, unknown>) =>
    http.put(`/projects/${slug}/wiki/pages/${pageId}`, data),
  remove: (slug: string, pageId: number) => http.delete(`/projects/${slug}/wiki/pages/${pageId}`),
  versions: (slug: string, pageId: number) =>
    http.get(`/projects/${slug}/wiki/pages/${pageId}/versions`),
  rollback: (slug: string, pageId: number, version: number) =>
    http.post(`/projects/${slug}/wiki/pages/${pageId}/rollback`, { version }),
}

export const adminApi = {
  users: (params: Record<string, unknown>) => http.get('/admin/users', { params }),
  updateUser: (userId: number, data: Record<string, unknown>) =>
    http.put(`/admin/users/${userId}`, data),
  projects: (params: Record<string, unknown>) => http.get('/admin/projects', { params }),
  deleteProject: (slug: string) => http.delete(`/admin/projects/${slug}`),
  posts: (params: Record<string, unknown>) => http.get('/admin/posts', { params }),
  deletePost: (postId: number) => http.delete(`/admin/posts/${postId}`),
  deleteReply: (postId: number, replyId: number) =>
    http.delete(`/admin/posts/${postId}/replies/${replyId}`),
  deleteIssueComment: (issueId: number, commentId: number) =>
    http.delete(`/admin/issues/${issueId}/comments/${commentId}`),
  settings: () => http.get('/admin/settings'),
  updateSettings: (data: Record<string, unknown>) => http.put('/admin/settings', data),
  logs: (params: Record<string, unknown>) => http.get('/admin/logs', { params }),
}

export interface CommunityPost {
  id: number
  title: string
  category: string
  category_label: string
  status: string
  accepted_reply_id: number | null
  vote_count: number
  reply_count: number
  my_vote: boolean
  author: User | null
  created_at: string
  updated_at: string
  content?: string
  content_rendered?: string
  snippets?: CommunitySnippet[]
  replies?: CommunityReply[]
}

export interface CommunityReply {
  id: number
  post_id: number
  content: string
  content_rendered: string
  is_accepted: boolean
  vote_count: number
  my_vote: boolean
  author: User | null
  created_at: string
}

export interface CommunitySnippet {
  id: number
  post_id: number | null
  reply_id: number | null
  project_id: number
  project_slug: string | null
  project_name: string | null
  file_path: string | null
  language: string
  start_line: number | null
  end_line: number | null
  content: string
}

export interface PublicProject {
  id: number
  slug: string
  name: string
  description: string | null
}

export const communityApi = {
  list: (params: Record<string, unknown>) => http.get('/community/posts', { params }),
  create: (data: Record<string, unknown>) => http.post('/community/posts', data),
  get: (postId: number) => http.get(`/community/posts/${postId}`),
  update: (postId: number, data: Record<string, unknown>) =>
    http.put(`/community/posts/${postId}`, data),
  remove: (postId: number) => http.delete(`/community/posts/${postId}`),
  vote: (postId: number) => http.post(`/community/posts/${postId}/vote`),
  changeStatus: (postId: number, status: string) =>
    http.post(`/community/posts/${postId}/status`, { status }),
  createReply: (postId: number, data: Record<string, unknown>) =>
    http.post(`/community/posts/${postId}/replies`, data),
  deleteReply: (postId: number, replyId: number) =>
    http.delete(`/community/posts/${postId}/replies/${replyId}`),
  voteReply: (postId: number, replyId: number) =>
    http.post(`/community/posts/${postId}/replies/${replyId}/vote`),
  acceptReply: (postId: number, replyId: number) =>
    http.post(`/community/posts/${postId}/replies/${replyId}/accept`),
  publicProjects: () => http.get('/community/public-projects'),
}

export const storageApi = {
  uploadUrl: (data: Record<string, unknown>) => http.post('/storage/upload-url', data),
}
