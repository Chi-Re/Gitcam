<template>
  <div>
    <el-card v-loading="loading">
      <template #header>
        <div class="header-row">
          <span>通知中心</span>
          <div>
            <el-button size="small" @click="load">刷新</el-button>
            <el-button size="small" type="danger" plain :disabled="!items.length" @click="clearAll">
              清空
            </el-button>
            <el-button size="small" type="primary" plain @click="readAll">全部已读</el-button>
          </div>
        </div>
      </template>
      <el-empty v-if="!items.length && !loading" description="暂无通知" />
      <div v-for="n in items" :key="n.id" class="notice" @click="open(n)">
        <el-badge is-dot :hidden="n.is_read" class="dot">
          <el-icon :color="n.is_read ? '#c0c4cc' : '#409eff'" :size="20">
            <component :is="typeIcon(n.type)" />
          </el-icon>
        </el-badge>
        <div class="notice-body">
          <div class="notice-title" :class="{ unread: !n.is_read }">{{ n.title }}</div>
          <div v-if="n.content" class="notice-content">{{ n.content }}</div>
          <div class="notice-time">
            {{ formatTime(n.created_at) }}
            <el-tag v-if="n.email_sent" size="small" type="success" effect="plain" class="mail-tag">邮件已发送</el-tag>
          </div>
        </div>
        <el-button
          size="small"
          text
          type="danger"
          class="delete-btn"
          @click.stop="removeOne(n)"
        >
          <el-icon><Delete /></el-icon>
        </el-button>
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

    <el-card class="pref-card">
      <template #header>通知设置</template>
      <el-form label-width="110px">
        <el-form-item label="通知类型">
          <div class="pref-checks">
            <el-checkbox v-model="prefs.comment">被评论</el-checkbox>
            <el-checkbox v-model="prefs.mention">@提及</el-checkbox>
            <el-checkbox v-model="prefs.issue">Issue 变更</el-checkbox>
            <el-checkbox v-model="prefs.repo">仓库动态</el-checkbox>
            <el-checkbox v-model="prefs.wiki">Wiki 更新</el-checkbox>
          </div>
        </el-form-item>
        <el-form-item label="邮件提醒">
          <el-switch v-model="prefs.email_enabled" />
          <span class="hint">未配置 SMTP 时仅站内通知</span>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="small" :loading="savingPrefs" @click="savePrefs">保存设置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { userApi } from '@/api'

interface Notice {
  id: number
  type: string
  title: string
  content: string | null
  url: string | null
  is_read: boolean
  email_sent: boolean
  created_at: string
}

const items = ref<Notice[]>([])
const loading = ref(false)
const page = ref(1)
const perPage = 15
const total = ref(0)
const savingPrefs = ref(false)
const prefs = reactive({
  comment: true,
  mention: true,
  issue: true,
  repo: true,
  wiki: true,
  email_enabled: true,
})

async function load() {
  loading.value = true
  try {
    const data = await userApi.notifications({ page: page.value, per_page: perPage }) as {
      items: Notice[]
      total: number
    }
    items.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function open(n: Notice) {
  if (!n.is_read) {
    await userApi.readNotification({ id: n.id })
    n.is_read = true
  }
  if (n.url) {
    window.location.href = n.url
  }
}

async function readAll() {
  await userApi.readNotification({ all: true })
  items.value.forEach((n) => (n.is_read = true))
  ElMessage.success('已全部标记为已读')
}

async function removeOne(n: Notice) {
  await ElMessageBox.confirm('删除这条通知？', '删除', { type: 'warning' })
  await userApi.deleteNotification(n.id)
  items.value = items.value.filter((x) => x.id !== n.id)
  ElMessage.success('已删除')
}

async function clearAll() {
  await ElMessageBox.confirm('清空全部通知？', '清空', { type: 'warning' })
  await userApi.clearNotifications()
  items.value = []
  ElMessage.success('已清空')
}

async function loadPrefs() {
  const data = await userApi.prefs() as { prefs: typeof prefs }
  Object.assign(prefs, data.prefs)
}

async function savePrefs() {
  savingPrefs.value = true
  try {
    await userApi.updatePrefs(prefs)
    ElMessage.success('通知设置已保存')
  } finally {
    savingPrefs.value = false
  }
}

function onPageChange(p: number) {
  page.value = p
  load()
}

function typeIcon(type: string) {
  const map: Record<string, string> = {
    comment: 'ChatDotRound',
    mention: 'Mention',
    issue: 'Warning',
    repo: 'FolderOpened',
    wiki: 'Document',
  }
  return map[type] || 'Bell'
}

function formatTime(t: string) {
  return t ? new Date(t).toLocaleString('zh-CN') : '-'
}

onMounted(() => {
  load()
  loadPrefs()
})
</script>

<style scoped>
.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.notice {
  display: flex;
  gap: 12px;
  padding: 12px;
  border-radius: 6px;
  cursor: pointer;
  align-items: flex-start;
}
.notice:hover {
  background: #f5f7fa;
}
.delete-btn {
  opacity: 0;
  transition: opacity 0.2s;
}
.notice:hover .delete-btn {
  opacity: 1;
}
.notice-body {
  flex: 1;
}
.notice-title {
  font-weight: 500;
}
.notice-title.unread {
  color: #409eff;
  font-weight: 600;
}
.notice-content {
  color: #909399;
  font-size: 13px;
  margin-top: 2px;
}
.notice-time {
  color: #c0c4cc;
  font-size: 12px;
  margin-top: 4px;
}
.mail-tag {
  margin-left: 8px;
}
.pagination {
  margin-top: 16px;
  justify-content: flex-end;
}
.pref-card {
  margin-top: 16px;
}
.pref-checks {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}
.hint {
  margin-left: 12px;
  color: #909399;
  font-size: 12px;
}
</style>
