<template>
  <div v-loading="loading">
    <el-card v-if="post" class="post-card">
      <div class="post-header">
        <div class="title-row">
          <h2 class="title">{{ post.title }}</h2>
          <el-tag size="small" type="primary" effect="plain">{{ post.category_label }}</el-tag>
          <el-tag v-if="post.status === 'solved'" size="small" type="success">已解决</el-tag>
          <el-tag v-else-if="post.status === 'closed'" size="small" type="info">已关闭</el-tag>
          <el-tag v-else size="small" type="warning" effect="plain">待解决</el-tag>
        </div>
        <div class="meta">
          <el-avatar :size="24" :src="post.author?.avatar_url || undefined">
            {{ post.author?.full_name?.[0] }}
          </el-avatar>
          <span class="author">{{ post.author?.full_name }}</span>
          <span class="time">{{ formatTime(post.created_at) }}</span>
        </div>
      </div>

      <div class="post-body">
        <div class="vote-col">
          <el-button
            class="vote-btn"
            :type="post.my_vote ? 'primary' : 'default'"
            circle
            :disabled="!auth.isLoggedIn"
            @click="toggleVote"
          >
            <el-icon size="20"><Top /></el-icon>
          </el-button>
          <div class="vote-count" :class="{ active: post.my_vote }">{{ post.vote_count }}</div>
        </div>
        <div class="content-col">
          <div class="markdown-body" v-html="post.content_rendered" @click="onContentClick"></div>
        </div>
      </div>

      <div class="post-actions" v-if="canManage">
        <el-button v-if="post.status === 'open'" size="small" type="success" plain @click="setStatus('solved')">
          标记已解决
        </el-button>
        <el-button v-if="post.status !== 'closed'" size="small" type="info" plain @click="setStatus('closed')">
          关闭帖子
        </el-button>
        <el-button v-if="post.status === 'closed'" size="small" @click="setStatus('open')">
          重新打开
        </el-button>
        <el-button v-if="isAuthor" size="small" type="danger" plain @click="removePost">删除</el-button>
      </div>
    </el-card>

    <el-card v-if="post" class="replies-card">
      <template #header>
        <div class="replies-header">
          <span>{{ post.reply_count }} 条回答</span>
        </div>
      </template>

      <div v-for="r in sortedReplies" :key="r.id" class="reply" :id="`reply-${r.id}`">
        <div class="reply-head">
          <el-avatar :size="26" :src="r.author?.avatar_url || undefined">
            {{ r.author?.full_name?.[0] }}
          </el-avatar>
          <span class="author">{{ r.author?.full_name }}</span>
          <span class="time">{{ formatTime(r.created_at) }}</span>
          <el-tag v-if="r.is_accepted" size="small" type="success">
            <el-icon><Check /></el-icon> 已采纳
          </el-tag>
        </div>
        <div class="reply-body">
          <div class="markdown-body" v-html="r.content_rendered"></div>
        </div>
        <div class="reply-actions">
          <el-button size="small" text :disabled="!auth.isLoggedIn" @click="toggleReplyVote(r)">
            <el-icon :color="r.my_vote ? '#409eff' : ''"><Top /></el-icon>
            <span :class="{ voted: r.my_vote }">{{ r.vote_count }}</span>
          </el-button>
          <el-button
            v-if="canAccept && !r.is_accepted"
            size="small"
            type="success"
            text
            @click="accept(r)"
          >
            <el-icon><Select /></el-icon>采纳
          </el-button>
          <el-button v-if="isAuthor && !r.is_accepted" size="small" type="danger" text @click="removeReply(r)">
            删除
          </el-button>
        </div>
      </div>

      <el-divider v-if="post.status !== 'closed'" content-position="left">回复</el-divider>
      <div v-if="post.status !== 'closed'">
        <div v-if="auth.isLoggedIn" class="reply-editor">
          <PostEditor v-model="replyContent" community :slug="''" :rows="4" @snippet="onReplySnippet" />
          <el-button type="primary" size="small" class="reply-submit" :loading="replying" @click="submitReply">
            发表回复
          </el-button>
        </div>
        <el-alert v-else type="info" :closable="false" class="login-tip">
          <template #title>
            登录后可参与讨论
            <el-button size="small" type="primary" text @click="$router.push('/login')">去登录</el-button>
          </template>
        </el-alert>
      </div>
      <el-empty v-else description="帖子已关闭" :image-size="50" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { communityApi, type CommunityPost, type CommunityReply } from '@/api'
import { useAuthStore } from '@/stores/auth'
import PostEditor from '@/components/PostEditor.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const postId = Number(route.params.postId)
const loading = ref(false)
const post = ref<CommunityPost | null>(null)
const replyContent = ref('')
const replySnippets = ref<{ file_path: string; content: string; language: string; project_id?: number }[]>([])
const replying = ref(false)

const isAuthor = computed(() => post.value?.author?.id === auth.user?.id)
const canAccept = computed(() => {
  if (!post.value) return false
  const me = auth.user
  if (!me) return false
  if (me.role === 'teacher' || me.role === 'admin') return true
  return post.value.author?.id === me.id
})
const canManage = computed(() => isAuthor.value || auth.isTeacher || auth.isAdmin)

const sortedReplies = computed(() => {
  const replies = [...(post.value?.replies ?? [])]
  const accepted = replies.find((r) => r.is_accepted)
  const rest = replies.filter((r) => !r.is_accepted)
  return accepted ? [accepted, ...rest] : replies
})

async function load() {
  loading.value = true
  try {
    post.value = (await communityApi.get(postId) as { post: CommunityPost }).post
  } finally {
    loading.value = false
  }
}

async function toggleVote() {
  if (!post.value) return
  const data = await communityApi.vote(post.value.id) as { vote_count: number; voted: boolean }
  post.value.vote_count = data.vote_count
  post.value.my_vote = data.voted
}

async function toggleReplyVote(r: CommunityReply) {
  const data = await communityApi.voteReply(postId, r.id) as { vote_count: number; voted: boolean }
  r.vote_count = data.vote_count
  r.my_vote = data.voted
}

async function accept(r: CommunityReply) {
  await ElMessageBox.confirm(`采纳 ${r.author?.full_name} 的回答？帖子将标记为已解决`, '采纳回答', {
    type: 'success',
  })
  const data = await communityApi.acceptReply(postId, r.id) as { post: CommunityPost }
  post.value = data.post
  ElMessage.success('已采纳')
}

async function setStatus(status: string) {
  const data = await communityApi.changeStatus(postId, status) as { post: CommunityPost }
  post.value = data.post
  ElMessage.success('状态已更新')
}

async function removePost() {
  await ElMessageBox.confirm('确定删除该帖子？', '删除', { type: 'warning' })
  await communityApi.remove(postId)
  ElMessage.success('已删除')
  router.push('/community')
}

async function removeReply(r: CommunityReply) {
  await ElMessageBox.confirm('确定删除该回复？', '删除', { type: 'warning' })
  await communityApi.deleteReply(postId, r.id)
  await load()
}

function onReplySnippet(sn: { file_path: string; content: string; language: string; project_id?: number }) {
  replySnippets.value.push(sn)
}

async function submitReply() {
  if (!replyContent.value.trim()) {
    ElMessage.warning('回复内容不能为空')
    return
  }
  replying.value = true
  try {
    await communityApi.createReply(postId, {
      content: replyContent.value,
      snippets: replySnippets.value,
    })
    ElMessage.success('回复成功')
    replyContent.value = ''
    replySnippets.value = []
    await load()
  } finally {
    replying.value = false
  }
}

function formatTime(t: string) {
  return t ? new Date(t).toLocaleString('zh-CN') : '-'
}

function onContentClick(e: MouseEvent) {
  const target = (e.target as HTMLElement).closest('a')
  if (!target) return
  const href = target.getAttribute('href') || ''
  // 来源仓库链接：#!repo:<slug>:path:<file_path>
  if (href.startsWith('#!repo:')) {
    e.preventDefault()
    const rest = href.slice('#!repo:'.length)
    const slug = rest.split(':path:')[0]
    const filePath = rest.split(':path:')[1] || ''
    if (slug) {
      router.push({
        path: `/projects/${slug}/repo`,
        query: { path: filePath },
      })
    }
  }
}

onMounted(load)
</script>

<style scoped>
.post-card {
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
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  color: #909399;
  font-size: 13px;
}
.author {
  color: #606266;
  font-weight: 500;
}
.post-body {
  display: flex;
  gap: 20px;
  margin-top: 16px;
}
.vote-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  min-width: 48px;
}
.vote-count {
  font-weight: 600;
  color: #606266;
}
.vote-count.active {
  color: #409eff;
}
.content-col {
  flex: 1;
  min-width: 0;
}
.post-actions {
  margin-top: 16px;
  border-top: 1px solid #f0f2f5;
  padding-top: 12px;
}
.replies-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.reply {
  border-bottom: 1px solid #f0f2f5;
  padding: 14px 0;
}
.reply-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.reply-head .time {
  color: #909399;
  font-size: 12px;
}
.reply-body {
  margin-left: 34px;
}
.reply-actions {
  margin-left: 34px;
  margin-top: 8px;
}
.voted {
  color: #409eff;
}
.reply-editor {
  margin-top: 8px;
}
.reply-submit {
  margin-top: 8px;
  float: right;
}
.login-tip {
  margin-top: 8px;
}
</style>
