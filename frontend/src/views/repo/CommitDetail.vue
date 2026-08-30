<template>
  <div v-loading="loading">
    <el-card v-if="commit" class="commit-card">
      <template #header>
        <div class="commit-header">
          <span class="msg">{{ commit.message }}</span>
          <el-tag size="small" class="sha">{{ commit.short_sha }}</el-tag>
          <el-tag v-if="commit.parents.length === 0" size="small" type="success">初始提交</el-tag>
        </div>
      </template>
      <div class="commit-info">
        <div>
          作者：<span class="author">{{ commit.author_name }}</span>（{{ commit.author_email }}）
        </div>
        <div>提交时间：{{ formatTime(commit.committed_at) }}</div>
        <div v-if="commit.diff_stat" class="stat">
          共 {{ commit.diff_stat.files_changed }} 个文件变更，
          <span class="add">+{{ commit.diff_stat.additions }}</span>
          <span class="del">-{{ commit.diff_stat.deletions }}</span>
        </div>
        <el-button size="small" class="back-btn" @click="$router.back()">返回</el-button>
      </div>
    </el-card>

    <el-card v-if="commit" class="discuss-card">
      <template #header>
        <div class="discuss-header">
          <span>关联讨论</span>
          <el-button size="small" type="primary" plain @click="startDiscussion">
            <el-icon><ChatDotRound /></el-icon>针对此提交发起讨论
          </el-button>
        </div>
      </template>
      <el-empty v-if="!discussions.length && !loadingDiscussions" description="暂无关联讨论" :image-size="50" />
      <div
        v-for="d in discussions"
        :key="d.id"
        class="discuss-item"
        @click="$router.push(`/projects/${slug}/posts/${d.post_id}`)"
      >
        <el-icon color="#409eff"><ChatDotRound /></el-icon>
        <div class="discuss-body">
          <div class="discuss-title">{{ d.post?.title || d.post_title }}</div>
          <div class="discuss-meta">
            {{ d.post?.author?.full_name }} · {{ formatTime(d.created_at) }}
            <el-tag v-if="d.post?.status === 'solved'" size="small" type="success">已解决</el-tag>
            <el-tag v-else-if="d.post?.status === 'closed'" size="small" type="info">已关闭</el-tag>
            <el-tag v-else size="small" type="warning" effect="plain">讨论中</el-tag>
            <span v-if="d.file_path" class="file-path">{{ d.file_path }}{{ d.line_start ? `:${d.line_start}` : '' }}</span>
          </div>
        </div>
      </div>
    </el-card>

    <DiffView v-if="commit?.diff" :files="commit.diff" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { repoApi, discussionApi, type CommitItem, type DiscussionLinkItem } from '@/api'
import DiffView from '@/components/DiffView.vue'

const route = useRoute()
const router = useRouter()
const slug = route.params.slug as string
const sha = route.params.sha as string
const loading = ref(false)
const commit = ref<CommitItem | null>(null)
const discussions = ref<DiscussionLinkItem[]>([])
const loadingDiscussions = ref(false)

async function load() {
  loading.value = true
  try {
    commit.value = (await repoApi.commitDetail(slug, sha) as { commit: CommitItem }).commit
  } finally {
    loading.value = false
  }
}

async function loadDiscussions() {
  loadingDiscussions.value = true
  try {
    const data = await discussionApi.query(slug, { commit_sha: sha }) as { items: DiscussionLinkItem[] }
    discussions.value = data.items
  } finally {
    loadingDiscussions.value = false
  }
}

function startDiscussion() {
  router.push({
    path: `/projects/${slug}/posts/create`,
    query: { bind_commit: sha },
  })
}

function formatTime(t: string) {
  return t ? new Date(t).toLocaleString('zh-CN') : '-'
}

onMounted(() => {
  load()
  loadDiscussions()
})
</script>

<style scoped>
.commit-card {
  margin-bottom: 16px;
}
.commit-header {
  display: flex;
  align-items: center;
  gap: 10px;
}
.msg {
  font-weight: 600;
}
.commit-info {
  color: #606266;
  font-size: 13px;
  line-height: 2;
  display: flex;
  gap: 24px;
  align-items: center;
}
.author {
  font-weight: 500;
}
.add {
  color: #1a7f37;
}
.del {
  color: #cf222e;
}
.back-btn {
  margin-left: auto;
}
.discuss-card {
  margin-bottom: 16px;
}
.discuss-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.discuss-item {
  display: flex;
  gap: 10px;
  padding: 10px 6px;
  cursor: pointer;
  border-radius: 4px;
  align-items: flex-start;
}
.discuss-item:hover {
  background: #f5f7fa;
}
.discuss-body {
  flex: 1;
}
.discuss-title {
  font-weight: 500;
}
.discuss-meta {
  color: #909399;
  font-size: 12px;
  margin-top: 4px;
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.file-path {
  font-family: 'SFMono-Regular', Consolas, Menlo, monospace;
}
</style>
