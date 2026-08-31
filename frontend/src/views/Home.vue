<template>
  <div>
    <!-- 问候条 + 公告 -->
    <el-card class="greet-card" shadow="never">
      <div class="greet-row">
        <div class="greet-left">
          <span class="greet-hi">你好，{{ auth.user?.full_name }}</span>
          <span class="greet-sub">欢迎回到 gitcam</span>
        </div>
        <div class="greet-actions">
          <el-button size="small" type="primary" plain @click="$router.push('/projects/create')">
            <el-icon><Plus /></el-icon>创建项目
          </el-button>
          <el-button size="small" type="primary" @click="$router.push('/community/create')">
            <el-icon><EditPen /></el-icon>发帖
          </el-button>
        </div>
      </div>
      <el-alert
        v-if="announcement"
        type="info"
        :closable="false"
        show-icon
        class="announcement"
      >
        <template #title>
          <span class="announcement-text">公告：{{ announcement }}</span>
        </template>
      </el-alert>
    </el-card>

    <!-- 主区：社区帖子 + 右侧信息栏 -->
    <div class="home-layout">
      <div class="home-main">
        <el-card class="home-header">
          <template #header>
            <div class="home-header-row">
              <span class="home-header-title">社区论坛</span>
              <div class="home-header-actions">
                <el-radio-group v-model="category" size="small" @change="reload">
                  <el-radio-button value="all">全部</el-radio-button>
                  <el-radio-button value="question">问题求助</el-radio-button>
                  <el-radio-button value="share">经验分享</el-radio-button>
                  <el-radio-button value="review">代码评审</el-radio-button>
                </el-radio-group>
                <el-button size="small" type="primary" @click="$router.push('/community/create')">
                  <el-icon><Plus /></el-icon>发帖
                </el-button>
              </div>
            </div>
          </template>

          <div class="home-search">
            <el-input
              v-model="q"
              placeholder="搜索社区帖子（标题 / 内容）"
              clearable
              @keyup.enter="reload"
              @clear="reload"
            >
              <template #prefix><el-icon><Search /></el-icon></template>
            </el-input>
          </div>

          <el-empty v-if="!items.length && !loading" description="暂无帖子，来发第一帖吧" />
          <div v-for="p in items" :key="p.id" class="post-item" @click="$router.push(`/community/${p.id}`)">
            <div class="stats">
              <div class="stat">
                <div class="num">{{ p.vote_count }}</div>
                <div class="label">赞同</div>
              </div>
              <div class="stat" :class="{ answered: p.status === 'solved' }">
                <div class="num">{{ p.reply_count }}</div>
                <div class="label">回答</div>
              </div>
            </div>
            <div class="main">
              <div class="title-row">
                <span class="title">{{ p.title }}</span>
                <el-tag size="small" type="primary" effect="plain">{{ p.category_label }}</el-tag>
                <el-tag v-if="p.status === 'solved'" size="small" type="success">已解决</el-tag>
                <el-tag v-else-if="p.status === 'closed'" size="small" type="info">已关闭</el-tag>
              </div>
              <div class="meta">
                {{ p.author?.full_name }} · {{ formatTime(p.created_at) }}
              </div>
            </div>
          </div>
          <el-pagination
            v-if="total > perPage"
            layout="prev, pager, next"
            :total="total"
            :page-size="perPage"
            :current-page="page"
            @current-change="onPageChange"
            class="pagination"
          />
        </el-card>
      </div>

      <!-- 右侧信息栏 -->
      <div class="home-side">
        <!-- 最近提交的项目 -->
        <el-card class="side-card">
          <template #header>
            <div class="side-head">
              <span>最近提交的项目</span>
              <el-button size="small" text type="primary" @click="$router.push('/projects')">全部</el-button>
            </div>
          </template>
          <div v-loading="recentLoading">
            <el-empty v-if="!recentLoading && !recentProjects.length" description="暂无项目" :image-size="40">
              <el-button size="small" type="primary" @click="$router.push('/projects/create')">创建项目</el-button>
            </el-empty>
            <div
              v-for="p in recentProjects"
              :key="p.id"
              class="recent-item"
              @click="$router.push(`/projects/${p.slug}`)"
            >
              <div class="recent-head">
                <span class="recent-name">{{ p.name }}</span>
                <el-tag size="small" :type="p.visibility === 'public' ? 'success' : 'info'">
                  {{ p.visibility === 'public' ? '公开' : '私有' }}
                </el-tag>
              </div>
              <div v-if="p.description" class="recent-desc">{{ p.description }}</div>
              <div class="recent-meta">
                <span>{{ p.owner_name }}</span>
                <span>{{ p.member_count }} 成员</span>
                <span>{{ formatTime(p.updated_at) }}</span>
              </div>
            </div>
          </div>
        </el-card>

        <!-- 我的待办 -->
        <el-card class="side-card">
          <template #header>
            <div class="side-head">
              <span>我的待办</span>
              <el-button size="small" text type="primary" @click="$router.push('/projects')">全部项目</el-button>
            </div>
          </template>
          <div v-loading="todoLoading">
            <el-empty v-if="!todoLoading && !todos.length" description="暂无待办" :image-size="40" />
            <div
              v-for="t in todos"
              :key="t.id"
              class="todo-item"
              @click="$router.push(`/projects/${t.project_slug}/issues/${t.id}`)"
            >
              <div class="todo-head">
                <span class="todo-title">{{ t.title }}</span>
                <el-tag size="small" :type="t.status === 'in_progress' ? 'primary' : 'warning'" effect="plain">
                  {{ t.status_label }}
                </el-tag>
              </div>
              <div class="todo-meta">
                <span>{{ t.project_name }}</span>
                <span>{{ formatTime(t.updated_at) }}</span>
              </div>
            </div>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { communityApi, userApi, type CommunityPost, type RecentProject } from '@/api'
import { useAuthStore } from '@/stores/auth'

interface IssueTodo {
  id: number
  title: string
  status: string
  status_label: string
  priority: string
  project_id: number
  project_name: string
  project_slug: string | null
  updated_at: string
}

const router = useRouter()
const auth = useAuthStore()

const items = ref<CommunityPost[]>([])
const loading = ref(false)
const category = ref('all')
const q = ref('')
const page = ref(1)
const perPage = 10
const total = ref(0)
const recentProjects = ref<RecentProject[]>([])
const recentLoading = ref(false)
const todos = ref<IssueTodo[]>([])
const todoLoading = ref(false)
const announcement = ref('')

async function load() {
  loading.value = true
  try {
    const data = await communityApi.list({
      category: category.value,
      q: q.value || undefined,
      page: page.value,
      per_page: perPage,
    }) as { items: CommunityPost[]; total: number }
    items.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function reload() {
  page.value = 1
  load()
}

function onPageChange(p: number) {
  page.value = p
  load()
}

async function loadRecent() {
  recentLoading.value = true
  try {
    const data = await userApi.recentProjects() as { projects: RecentProject[] }
    recentProjects.value = data.projects
  } finally {
    recentLoading.value = false
  }
}

async function loadTodos() {
  todoLoading.value = true
  try {
    const data = await userApi.issueTodos() as { items: IssueTodo[] }
    todos.value = data.items
  } finally {
    todoLoading.value = false
  }
}

async function loadAnnouncement() {
  try {
    const data = await communityApi.announcement() as { announcement: string | null }
    announcement.value = data.announcement || ''
  } catch {
    announcement.value = ''
  }
}

function formatTime(t: string) {
  if (!t) return '-'
  const d = new Date(t)
  const diff = Date.now() - d.getTime()
  if (diff < 60 * 60 * 1000) return `${Math.max(1, Math.floor(diff / 60000))} 分钟前`
  if (diff < 24 * 60 * 60 * 1000) return `${Math.floor(diff / 3600000)} 小时前`
  if (diff < 7 * 24 * 60 * 60 * 1000) return `${Math.floor(diff / 86400000)} 天前`
  return d.toLocaleDateString('zh-CN')
}

onMounted(() => {
  load()
  loadRecent()
  loadTodos()
  loadAnnouncement()
})
</script>

<style scoped>
.greet-card {
  margin-bottom: 16px;
}
.greet-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}
.greet-left {
  display: flex;
  align-items: baseline;
  gap: 10px;
}
.greet-hi {
  font-size: 18px;
  font-weight: 700;
}
.greet-sub {
  color: #909399;
  font-size: 13px;
}
.greet-actions {
  display: flex;
  gap: 8px;
}
.announcement {
  margin-top: 12px;
}
.announcement-text {
  font-size: 13px;
}
.home-layout {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}
.home-main {
  flex: 1;
  min-width: 0;
}
.home-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.home-header-title {
  font-weight: 600;
  font-size: 15px;
}
.home-header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.home-search {
  margin-bottom: 12px;
}
.post-item {
  display: flex;
  gap: 16px;
  padding: 14px 8px;
  border-bottom: 1px solid #f0f2f5;
  cursor: pointer;
}
.post-item:hover {
  background: #fafbfc;
}
.stats {
  display: flex;
  gap: 18px;
  min-width: 100px;
}
.stat {
  text-align: center;
}
.stat .num {
  font-weight: 600;
  font-size: 16px;
}
.stat .label {
  color: #909399;
  font-size: 12px;
}
.stat.answered .num {
  color: #67c23a;
}
.main {
  flex: 1;
}
.title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.title {
  font-weight: 600;
  font-size: 15px;
}
.meta {
  color: #909399;
  font-size: 12px;
  margin-top: 6px;
}
.pagination {
  margin-top: 16px;
  justify-content: flex-end;
}
.home-side {
  width: 280px;
  flex-shrink: 0;
  position: sticky;
  top: 0;
}
@media (min-width: 768px) and (max-width: 991px) {
  .home-side {
    width: 240px;
  }
}
@media (max-width: 767px) {
  .home-layout {
    flex-direction: column;
  }
  .home-side {
    width: 100%;
    position: static;
  }
  .greet-title {
    font-size: 16px;
  }
}
.side-card {
  margin-bottom: 16px;
}
.side-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.recent-item,
.todo-item {
  padding: 10px 4px;
  border-bottom: 1px solid #f0f2f5;
  cursor: pointer;
  border-radius: 4px;
}
.recent-item:hover,
.todo-item:hover {
  background: #f5f7fa;
}
.recent-head,
.todo-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}
.recent-name,
.todo-title {
  font-weight: 600;
  font-size: 13.5px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.recent-desc {
  color: #909399;
  font-size: 12px;
  margin-top: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.recent-meta,
.todo-meta {
  color: #c0c4cc;
  font-size: 11.5px;
  margin-top: 4px;
  display: flex;
  gap: 10px;
}
</style>
