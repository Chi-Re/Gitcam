<template>
  <div>
    <div class="toolbar">
      <el-radio-group v-model="status" @change="reload">
        <el-radio-button value="all">全部</el-radio-button>
        <el-radio-button value="open">待处理</el-radio-button>
        <el-radio-button value="in_progress">处理中</el-radio-button>
        <el-radio-button value="resolved">已解决</el-radio-button>
        <el-radio-button value="closed">已关闭</el-radio-button>
      </el-radio-group>
      <el-select v-model="priority" clearable placeholder="优先级" style="width: 110px" @change="reload">
        <el-option label="紧急" value="urgent" />
        <el-option label="高" value="high" />
        <el-option label="中" value="medium" />
        <el-option label="低" value="low" />
      </el-select>
      <el-select v-model="label" filterable clearable placeholder="标签" style="width: 130px" @change="reload">
        <el-option label="bug" value="bug" />
        <el-option label="feature" value="feature" />
        <el-option label="question" value="question" />
        <el-option label="enhancement" value="enhancement" />
        <el-option label="documentation" value="documentation" />
      </el-select>
      <el-input v-model="milestone" placeholder="里程碑" clearable style="width: 140px" @keyup.enter="reload" @clear="reload" />
      <el-button type="primary" @click="$router.push(`/projects/${slug}/issues/create`)">
        <el-icon><Plus /></el-icon>新建 Issue
      </el-button>
    </div>

    <el-card v-loading="loading">
      <el-empty v-if="!items.length && !loading" description="暂无 Issue" />
      <div v-for="i in items" :key="i.id" class="issue-item" @click="$router.push(`/projects/${slug}/issues/${i.id}`)">
        <div class="issue-main">
          <div class="title-row">
            <el-icon :color="statusColor(i.status)" size="16" class="status-icon">
              <Warning v-if="i.status === 'open'" />
              <Loading v-else-if="i.status === 'in_progress'" />
              <CircleCheck v-else-if="i.status === 'resolved'" />
              <CircleClose v-else />
            </el-icon>
            <span class="title">{{ i.title }}</span>
            <el-tag v-for="l in i.labels" :key="l" size="small" :type="labelType(l)" effect="plain">{{ l }}</el-tag>
          </div>
          <div class="meta">
            #{{ i.number }} · {{ i.status_label }} · {{ i.priority_label }}优先级
            <template v-if="i.milestone"> · 里程碑：{{ i.milestone }}</template>
            <template v-if="i.assignee"> · 指派：{{ i.assignee.full_name }}</template>
            · {{ i.creator?.full_name }} 创建于 {{ formatTime(i.created_at) }}
          </div>
        </div>
        <div class="issue-side">
          <span v-if="i.comment_count" class="comments">
            <el-icon><ChatDotRound /></el-icon> {{ i.comment_count }}
          </span>
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
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { issuesApi, type Issue } from '@/api'

const route = useRoute()
const router = useRouter()
const slug = route.params.slug as string
const items = ref<Issue[]>([])
const loading = ref(false)
const status = ref('all')
const priority = ref('')
const label = ref('')
const milestone = ref('')
const page = ref(1)
const perPage = 20
const total = ref(0)

async function load() {
  loading.value = true
  try {
    const data = await issuesApi.list(slug, {
      status: status.value,
      priority: priority.value || undefined,
      label: label.value || undefined,
      milestone: milestone.value || undefined,
      page: page.value,
      per_page: perPage,
    }) as { items: Issue[]; total: number }
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

function statusColor(s: string) {
  const map: Record<string, string> = {
    open: '#e6a23c',
    in_progress: '#409eff',
    resolved: '#67c23a',
    closed: '#909399',
  }
  return map[s] || '#909399'
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
.toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
  flex-wrap: wrap;
  align-items: center;
}
.issue-item {
  display: flex;
  gap: 12px;
  padding: 14px 8px;
  border-bottom: 1px solid #f0f2f5;
  cursor: pointer;
  align-items: center;
}
.issue-item:hover {
  background: #fafbfc;
}
.issue-main {
  flex: 1;
}
.title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.status-icon {
  flex-shrink: 0;
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
.issue-side {
  color: #909399;
  display: flex;
  align-items: center;
  gap: 6px;
}
.pagination {
  margin-top: 16px;
  justify-content: flex-end;
}
</style>
