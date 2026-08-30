<template>
  <div v-loading="loading">
    <el-card v-if="issue" class="issue-card">
      <div class="issue-head">
        <div class="title-row">
          <h2 class="title">#{{ issue.number }} {{ issue.title }}</h2>
          <el-tag v-for="l in issue.labels" :key="l" size="small" :type="labelType(l)" effect="plain">{{ l }}</el-tag>
        </div>
        <div class="meta">
          {{ issue.creator?.full_name }} 创建于 {{ formatTime(issue.created_at) }} ·
          {{ issue.status_label }} · {{ issue.priority_label }}优先级
          <template v-if="issue.milestone"> · 里程碑：{{ issue.milestone }}</template>
          <template v-if="issue.closed_at"> · 关闭于 {{ formatTime(issue.closed_at) }}</template>
        </div>
        <div class="assignee" v-if="issue.assignee">
          指派人：
          <el-tag size="small" type="primary" effect="plain">{{ issue.assignee.full_name }}</el-tag>
        </div>

        <div class="status-actions">
          <el-button
            v-for="(label, st) in nextStatuses"
            :key="st"
            size="small"
            :type="st === 'closed' ? 'danger' : st === 'resolved' ? 'success' : 'primary'"
            plain
            @click="changeStatus(st)"
          >
            {{ label }}
          </el-button>
          <el-button v-if="canEdit" size="small" type="danger" plain @click="removeIssue">删除</el-button>
        </div>
      </div>

      <el-divider />
      <div class="markdown-body" v-if="issue.description">
        <MarkdownView :content="issue.description" />
      </div>
      <div v-else class="no-desc">（暂无描述）</div>

      <div v-if="issue.commits?.length" class="commits-section">
        <div class="section-title">关联提交（提交信息含 fix #{{ issue.number }} 自动关联）</div>
        <div
          v-for="c in issue.commits"
          :key="c.id"
          class="commit-item"
          @click="$router.push(`/projects/${slug}/commits/${c.commit_sha}`)"
        >
          <el-icon color="#409eff"><Connection /></el-icon>
          <span class="sha">{{ c.commit_sha.slice(0, 8) }}</span>
          <span class="by">{{ c.linked_by || '未知' }}</span>
          <span class="time">{{ formatTime(c.created_at) }}</span>
        </div>
      </div>
    </el-card>

    <el-card v-if="issue" class="comments-card">
      <template #header>{{ issue.comment_count }} 条评论</template>
      <div v-for="c in issue.comments" :key="c.id" class="comment">
        <div class="comment-head">
          <el-avatar :size="24" :src="c.author?.avatar_url || undefined">{{ c.author?.full_name?.[0] }}</el-avatar>
          <span class="author">{{ c.author?.full_name }}</span>
          <span class="time">{{ formatTime(c.created_at) }}</span>
          <el-button
            v-if="c.author?.id === auth.user?.id"
            size="small"
            text
            type="danger"
            @click="removeComment(c)"
          >删除</el-button>
        </div>
        <div class="markdown-body comment-body">
          <MarkdownView :content="c.content" />
        </div>
      </div>
      <el-empty v-if="!issue.comments?.length" description="暂无评论" :image-size="50" />
      <el-divider content-position="left">评论</el-divider>
      <div class="comment-editor">
        <el-input v-model="commentText" type="textarea" :rows="3" placeholder="支持 Markdown；回复时可在开头 @指派人" />
        <el-button type="primary" size="small" class="submit-btn" :loading="commenting" @click="submitComment">
          发表评论
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { issuesApi, type Issue, type IssueComment } from '@/api'
import { useAuthStore } from '@/stores/auth'
import MarkdownView from '@/components/MarkdownView.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const slug = route.params.slug as string
const issueId = Number(route.params.issueId)
const loading = ref(false)
const issue = ref<Issue | null>(null)
const commentText = ref('')
const commenting = ref(false)

const nextStatuses = computed(() => {
  const map: Record<string, [string, string][]> = {
    open: [['in_progress', '开始处理'], ['resolved', '标记已解决'], ['closed', '关闭']],
    in_progress: [['open', '重新打开'], ['resolved', '标记已解决'], ['closed', '关闭']],
    resolved: [['open', '重新打开'], ['closed', '关闭']],
    closed: [['open', '重新打开']],
  }
  const arr = map[issue.value?.status || 'open'] || []
  const obj: Record<string, string> = {}
  for (const [st, label] of arr) obj[st] = label
  return obj
})

const canEdit = computed(() => {
  const me = auth.user
  if (!me || !issue.value) return false
  if (me.role === 'teacher' || me.role === 'admin') return true
  return issue.value.creator?.id === me.id || issue.value.assignee?.id === me.id
})

async function load() {
  loading.value = true
  try {
    issue.value = (await issuesApi.get(slug, issueId) as { issue: Issue }).issue
  } finally {
    loading.value = false
  }
}

async function changeStatus(st: string) {
  const data = await issuesApi.changeStatus(slug, issueId, st) as { issue: Issue }
  issue.value = data.issue
  ElMessage.success('状态已更新')
}

async function removeIssue() {
  await ElMessageBox.confirm('确定删除该 Issue？', '删除', { type: 'warning' })
  await issuesApi.remove(slug, issueId)
  ElMessage.success('已删除')
  router.push(`/projects/${slug}/issues`)
}

async function submitComment() {
  if (!commentText.value.trim()) {
    ElMessage.warning('评论不能为空')
    return
  }
  commenting.value = true
  try {
    await issuesApi.createComment(slug, issueId, { content: commentText.value })
    commentText.value = ''
    await load()
  } finally {
    commenting.value = false
  }
}

async function removeComment(c: IssueComment) {
  await ElMessageBox.confirm('确定删除该评论？', '删除', { type: 'warning' })
  await issuesApi.deleteComment(slug, issueId, c.id)
  await load()
}

function labelType(l: string) {
  const map: Record<string, 'danger' | 'success' | 'warning' | 'primary' | 'info'> = {
    bug: 'danger',
    feature: 'success',
    question: 'warning',
    enhancement: 'primary',
  }
  return map[l] || 'info'
}

function formatTime(t: string) {
  return t ? new Date(t).toLocaleString('zh-CN') : '-'
}

onMounted(load)
</script>

<style scoped>
.issue-card {
  margin-bottom: 16px;
}
.title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.title {
  margin: 0;
}
.meta {
  color: #909399;
  font-size: 13px;
  margin-top: 8px;
}
.assignee {
  margin-top: 8px;
  color: #606266;
  font-size: 13px;
}
.status-actions {
  margin-top: 14px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.no-desc {
  color: #c0c4cc;
}
.commits-section {
  margin-top: 20px;
  border-top: 1px solid #f0f2f5;
  padding-top: 12px;
}
.section-title {
  font-weight: 600;
  color: #606266;
  margin-bottom: 10px;
}
.commit-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 4px;
  cursor: pointer;
  border-radius: 4px;
  font-family: 'SFMono-Regular', Consolas, Menlo, monospace;
  font-size: 13px;
}
.commit-item:hover {
  background: #f5f7fa;
}
.commit-item .sha {
  font-weight: 600;
}
.commit-item .by,
.commit-item .time {
  color: #909399;
  font-size: 12px;
}
.comment {
  padding: 12px 0;
  border-bottom: 1px solid #f0f2f5;
}
.comment-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.comment-head .author {
  font-weight: 500;
}
.comment-head .time {
  color: #909399;
  font-size: 12px;
}
.comment-body {
  margin-left: 32px;
}
.comment-editor {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.submit-btn {
  align-self: flex-end;
}
</style>
