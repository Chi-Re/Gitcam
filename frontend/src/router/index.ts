import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/',
    name: 'landing',
    component: () => import('@/views/Landing.vue'),
    meta: { title: 'gitcam', public: true },
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/auth/Login.vue'),
    meta: { public: true, title: '登录' },
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('@/views/auth/Register.vue'),
    meta: { public: true, title: '注册' },
  },
  {
    path: '/',
    component: () => import('@/views/Layout.vue'),
    children: [
      {
        path: 'home',
        name: 'home',
        component: () => import('@/views/Home.vue'),
        meta: { title: '首页' },
      },
      {
        path: 'admin',
        component: () => import('@/views/admin/AdminLayout.vue'),
        meta: { title: '管理后台', adminOnly: true },
        children: [
          {
            path: 'users',
            name: 'admin-users',
            component: () => import('@/views/admin/AdminUsers.vue'),
            meta: { title: '用户管理', adminOnly: true },
          },
          {
            path: 'content',
            name: 'admin-content',
            component: () => import('@/views/admin/AdminContent.vue'),
            meta: { title: '内容管理', adminOnly: true },
          },
          {
            path: 'settings',
            name: 'admin-settings',
            component: () => import('@/views/admin/AdminSettings.vue'),
            meta: { title: '系统设置', adminOnly: true },
          },
          {
            path: 'logs',
            name: 'admin-logs',
            component: () => import('@/views/admin/AdminLogs.vue'),
            meta: { title: '日志审计', adminOnly: true },
          },
          { path: '', redirect: '/admin/users' },
        ],
      },
      {
        path: 'projects',
        name: 'projects',
        component: () => import('@/views/project/ProjectList.vue'),
        meta: { title: '项目' },
      },
      {
        path: 'projects/create',
        name: 'project-create',
        component: () => import('@/views/project/ProjectCreate.vue'),
        meta: { title: '创建项目' },
      },
      {
        path: 'projects/:slug',
        component: () => import('@/views/project/ProjectDetail.vue'),
        meta: { title: '项目详情' },
        children: [
          {
            path: '',
            name: 'project-overview',
            component: () => import('@/views/project/ProjectOverview.vue'),
          },
          {
            path: 'repo',
            name: 'repo-tree',
            component: () => import('@/views/repo/RepoTree.vue'),
          },
          {
            path: 'commits',
            name: 'repo-commits',
            component: () => import('@/views/repo/RepoCommits.vue'),
          },
          {
            path: 'commits/:sha',
            name: 'repo-commit-detail',
            component: () => import('@/views/repo/CommitDetail.vue'),
          },
          {
            path: 'branches',
            name: 'repo-branches',
            component: () => import('@/views/repo/RepoBranches.vue'),
          },
          {
            path: 'members',
            name: 'project-members',
            component: () => import('@/views/project/ProjectMembers.vue'),
          },
          {
            path: 'posts',
            name: 'project-posts',
            component: () => import('@/views/forum/PostList.vue'),
          },
          {
            path: 'posts/create',
            name: 'post-create',
            component: () => import('@/views/forum/PostCreate.vue'),
          },
          {
            path: 'posts/:postId',
            name: 'post-detail',
            component: () => import('@/views/forum/PostDetail.vue'),
          },
          {
            path: 'issues',
            name: 'project-issues',
            component: () => import('@/views/issue/IssueList.vue'),
          },
          {
            path: 'issues/create',
            name: 'issue-create',
            component: () => import('@/views/issue/IssueCreate.vue'),
          },
          {
            path: 'issues/:issueId',
            name: 'issue-detail',
            component: () => import('@/views/issue/IssueDetail.vue'),
          },
          {
            path: 'wiki',
            name: 'project-wiki',
            component: () => import('@/views/wiki/WikiPage.vue'),
          },
        ],
      },
      {
        path: 'profile',
        name: 'profile',
        component: () => import('@/views/Profile.vue'),
        meta: { title: '个人资料' },
      },
      {
        path: 'notifications',
        name: 'notifications',
        component: () => import('@/views/Notifications.vue'),
        meta: { title: '通知中心' },
      },
      {
        path: 'community',
        name: 'community',
        component: () => import('@/views/community/CommunityList.vue'),
        meta: { title: '社区论坛', public: true },
      },
      {
        path: 'community/create',
        name: 'community-create',
        component: () => import('@/views/community/CommunityCreate.vue'),
        meta: { title: '发布社区帖子' },
      },
      {
        path: 'community/:postId',
        name: 'community-detail',
        component: () => import('@/views/community/CommunityDetail.vue'),
        meta: { title: '社区帖子', public: true },
      },
      {
        path: 'reply-history',
        name: 'reply-history',
        component: () => import('@/views/ReplyHistory.vue'),
        meta: { title: '我的回复' },
      },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/projects' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.loaded && localStorage.getItem('gitcam_token')) {
    await auth.fetchMe()
  }
  // 已登录访问落地页 → 首页
  if (to.name === 'landing' && auth.isLoggedIn) {
    return { name: 'home' }
  }
  // 未登录访问首页 → 落地页
  if (to.name === 'home' && !auth.isLoggedIn) {
    return { name: 'landing' }
  }
  if (!to.meta.public && !auth.isLoggedIn) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.meta.adminOnly && !auth.isAdmin) {
    return { name: 'projects' }
  }
  document.title = `${(to.meta.title as string) || ''} - gitcam`
  return true
})

export default router
