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
            @click="toggleVote"
          >
            <el-icon size="20"><Top /></el-icon>
          </el-button>
          <div class="vote-count" :class="{ active: post.my_vote }">{{ post.vote_count }}</div>
        </div>
        <div class="content-col">
          <div class="markdown-body" v-html="post.content_rendered"></div>

          <div v-if="post.discussion_links?.length" class="links-section">
            <div class="section-title">关联代码</div>
            <div
              v-for="link in post.discussion_links"
              :key="link.id"
              class="link-item"
            >
              <CodeBinding :link="link" :slug="slug" />
            </div>
          </div>
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

    <!-- 回帖 -->
    <el-card v-if="post" class="replies-card">
      <template #header>
        <div class="replies-header">
          <span>{{ post.reply_count }} 条回答</span>
          <el-radio-group v-model="replySort" size="small">
            <el-radio-button value="default">默认</el-radio-button>
            <el-radio-button value="votes">按赞同</el-radio-button>
          </el-radio-group>
        </div>
      </template>

      <div v-for="r in sortedReplies" :key="r.id" class="reply" :id="`reply-${r.id}`">
        <div class="reply-head">
          <el-avatar :size="26" :src="r.author?.avatar_url || undefined">
            {{ r.author?.full_name?.[0] }}
          </el-avatar>
          <span class="author">{{ r.author?.full_name }}</span>
          <span class="time">{{ formatTime(r.created_at) }}</span>
          <el-tag v-if="r.is_accepted" size="small" type="success" class="accepted-tag">
            <el-icon><Check /></el-icon> 已采纳
          </el-tag>
        </div>
        <div class="reply-body">
          <div class="markdown-body" v-html="r.content_rendered"></div>
          <div v-if="r.discussion_links.length" class="links-section">
            <div v-for="link in r.discussion_links" :key="link.id" class="link-item">
              <CodeBinding :link="link" :slug="slug" />
            </div>
          </div>
        </div>
        <div class="reply-actions">
          <el-button size="small" text @click="toggleReplyVote(r)">
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
      <div v-if="post.status !== 'closed'" class="reply-editor">
        <PostEditor v-model="replyContent" :slug="slug" :rows="4" @snippet="onReplySnippet" />
        <div class="reply-editor-actions">
          <el-select
            v-model="replyBinding.commit_sha"
            filterable
            placeholder="绑定 Commit SHA（可选）"
            clearable
            size="small"
            style="width: 220px"
          />
          <el-input
            v-model="replyBinding.file_path"
            placeholder="绑定文件路径（可选）"
            clearable
            size="small"
            style="width: 220px"
          />
          <el-button type="primary" size="small" :loading="replying" @click="submitReply">
            发表回复
          </el-button>
        </div>
      </div>
      <el-empty v-else description="帖子已关闭" :image-size="50" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { postsApi, type Post, type PostReply } from '@/api'
import { useAuthStore } from '@/stores/auth'
import PostEditor from '@/components/PostEditor.vue'
import CodeBinding from '@/components/CodeBinding.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const slug = route.params.slug as string
const postId = Number(route.params.postId)
const loading = ref(false)
const post = ref<Post | null>(null)
const replyContent = ref('')
const replySnippets = ref<{ file_path: string; content: string; language: string }[]>([])
const replying = ref(false)
const replySort = ref('default')
const replyBinding = reactive({ commit_sha: '', file_path: '' })

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
  const replies = post.value?.replies ?? []
  const list = [...replies]
  if (replySort.value === 'votes') {
    list.sort((a, b) => b.vote_count - a.vote_count)
  }
  // 采纳的回答置顶
  const accepted = list.find((r) => r.is_accepted)
  const rest = list.filter((r) => !r.is_accepted)
  return accepted ? [accepted, ...rest] : list
})

async function load() {
  loading.value = true
  try {
    post.value = (await postsApi.get(slug, postId) as { post: Post }).post
  } finally {
    loading.value = false
  }
}

async function toggleVote() {
  if (!post.value) return
  const data = await postsApi.vote(slug, post.value.id) as { vote_count: number; voted: boolean }
  post.value.vote_count = data.vote_count
  post.value.my_vote = data.voted
}

async function toggleReplyVote(r: PostReply) {
  const data = await postsApi.voteReply(slug, postId, r.id) as { vote_count: number; voted: boolean }
  r.vote_count = data.vote_count
  r.my_vote = data.voted
}

async function accept(r: PostReply) {
  await ElMessageBox.confirm(`采纳 ${r.author?.full_name} 的回答？帖子将标记为已解决`, '采纳回答', {
    type: 'success',
  })
  const data = await postsApi.acceptReply(slug, postId, r.id) as { post: Post }
  post.value = data.post
  ElMessage.success('已采纳')
}

async function setStatus(status: string) {
  const data = await postsApi.changeStatus(slug, postId, status) as { post: Post }
  post.value = data.post
  ElMessage.success('状态已更新')
}

async function removePost() {
  await ElMessageBox.confirm('确定删除该帖子？', '删除', { type: 'warning' })
  await postsApi.remove(slug, postId)
  ElMessage.success('已删除')
  router.push(`/projects/${slug}/posts`)
}

async function removeReply(r: PostReply) {
  await ElMessageBox.confirm('确定删除该回复？', '删除', { type: 'warning' })
  await postsApi.deleteReply(slug, postId, r.id)
  await load()
}

function onReplySnippet(sn: { file_path: string; content: string; language: string }) {
  replySnippets.value.push(sn)
}

async function submitReply() {
  if (!replyContent.value.trim()) {
    ElMessage.warning('回复内容不能为空')
    return
  }
  replying.value = true
  try {
    const bindings = []
    if (replyBinding.commit_sha || replyBinding.file_path) {
      bindings.push({ ...replyBinding })
    }
    await postsApi.createReply(slug, postId, {
      content: replyContent.value,
      snippets: replySnippets.value,
      bindings,
    })
    ElMessage.success('回复成功')
    replyContent.value = ''
    replySnippets.value = []
    replyBinding.commit_sha = ''
    replyBinding.file_path = ''
    await load()
  } finally {
    replying.value = false
  }
}

function formatTime(t: string) {
  return t ? new Date(t).toLocaleString('zh-CN') : '-'
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
.links-section {
  margin-top: 20px;
  border-top: 1px solid #f0f2f5;
  padding-top: 12px;
}
.section-title {
  font-weight: 600;
  color: #606266;
  margin-bottom: 10px;
}
.link-item {
  margin-bottom: 10px;
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
.accepted-tag {
  margin-left: 8px;
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
.reply-editor-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
  align-items: center;
}
</style>
