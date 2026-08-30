<template>
  <el-card v-loading="loading">
    <template #header>
      <div class="head">
        <span>我的回复</span>
        <el-radio-group v-model="scope" size="small" @change="reload">
          <el-radio-button value="all">全部</el-radio-button>
          <el-radio-button value="project">项目论坛</el-radio-button>
          <el-radio-button value="community">社区论坛</el-radio-button>
        </el-radio-group>
      </div>
    </template>

    <el-empty v-if="!items.length && !loading" description="暂无回复记录" />
    <div
      v-for="r in items"
      :key="r.id"
      class="record"
      :class="{ deleted: !r.post_exists }"
      @click="open(r)"
    >
      <div class="record-main">
        <div class="title-row">
          <el-tag size="small" :type="r.scope === 'project' ? 'primary' : 'success'" effect="plain">
            {{ r.scope === 'project' ? '项目论坛' : '社区论坛' }}
          </el-tag>
          <span class="title" :class="{ deleted: !r.post_exists }">{{ r.post_title }}</span>
          <el-tag v-if="!r.post_exists" size="small" type="info">已删除</el-tag>
        </div>
        <div v-if="r.content_snippet" class="snippet">{{ r.content_snippet }}</div>
        <div class="meta">
          {{ formatTime(r.created_at) }}
          <template v-if="r.scope === 'project' && r.project_slug"> · {{ r.project_slug }}</template>
        </div>
      </div>
      <div v-if="!r.post_exists" class="deleted-hint">
        <el-icon><CircleClose /></el-icon> 原帖子已删除
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
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { userApi, type ReplyHistoryItem } from '@/api'

const router = useRouter()
const items = ref<ReplyHistoryItem[]>([])
const loading = ref(false)
const scope = ref('all')
const page = ref(1)
const perPage = 20
const total = ref(0)

async function load() {
  loading.value = true
  try {
    const data = await userApi.replyHistory({
      scope: scope.value,
      page: page.value,
      per_page: perPage,
    }) as { items: ReplyHistoryItem[]; total: number }
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

function open(r: ReplyHistoryItem) {
  if (!r.post_exists) {
    // 帖子已删除：不跳转
    ElMessage.info('原帖子已删除')
    return
  }
  if (r.scope === 'community') {
    router.push(`/community/${r.post_id}`)
  } else if (r.project_slug) {
    router.push(`/projects/${r.project_slug}/posts/${r.post_id}#reply-${r.reply_id}`)
  }
}

function formatTime(t: string) {
  return t ? new Date(t).toLocaleString('zh-CN') : '-'
}

onMounted(load)
</script>

<style scoped>
.head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.record {
  display: flex;
  gap: 12px;
  padding: 14px 8px;
  border-bottom: 1px solid #f0f2f5;
  cursor: pointer;
  align-items: center;
}
.record:hover {
  background: #fafbfc;
}
.record.deleted {
  cursor: not-allowed;
  background: #fafafa;
}
.record-main {
  flex: 1;
  min-width: 0;
}
.title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.title {
  font-weight: 600;
  font-size: 15px;
}
.title.deleted {
  color: #c0c4cc;
  text-decoration: line-through;
}
.snippet {
  color: #606266;
  font-size: 13px;
  margin-top: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.meta {
  color: #909399;
  font-size: 12px;
  margin-top: 4px;
}
.deleted-hint {
  color: #909399;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
}
.pagination {
  margin-top: 16px;
  justify-content: flex-end;
}
</style>
