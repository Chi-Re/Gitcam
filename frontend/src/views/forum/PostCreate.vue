<template>
  <el-card v-loading="loading">
    <template #header>发布帖子</template>

    <el-form label-width="80px" style="max-width: 900px">
      <el-form-item label="标题" required>
        <el-input v-model="title" placeholder="一句话说明问题或主题" maxlength="255" />
      </el-form-item>
      <el-form-item label="分类" required>
        <el-select v-model="category" style="width: 200px">
          <el-option label="问题求助" value="question" />
          <el-option label="经验分享" value="share" />
          <el-option label="代码评审" value="review" />
          <el-option label="公告" value="announce" />
          <el-option label="其他" value="other" />
        </el-select>
      </el-form-item>
      <el-form-item label="内容" required>
        <PostEditor v-model="content" :slug="slug" @snippet="onSnippet" />
      </el-form-item>
      <el-form-item label="关联代码">
        <div class="binding-box">
          <div v-if="bindings.length" class="binding-list">
            <el-tag
              v-for="(b, i) in bindings"
              :key="i"
              closable
              @close="bindings.splice(i, 1)"
              class="binding-tag"
            >
              {{ bindingLabel(b) }}
            </el-tag>
          </div>
          <div class="binding-actions">
            <el-select
              v-model="binding.commit_sha"
              filterable
              placeholder="绑定 Commit SHA（可选）"
              clearable
              style="width: 260px"
            />
            <el-input
              v-model="binding.file_path"
              placeholder="绑定文件路径（可选）"
              clearable
              style="width: 260px"
            />
            <el-input-number v-model="binding.line_start" :min="1" placeholder="起始行" style="width: 110px" />
            <span>~</span>
            <el-input-number v-model="binding.line_end" :min="1" placeholder="结束行" style="width: 110px" />
            <el-button size="small" type="primary" plain @click="addBinding">添加绑定</el-button>
          </div>
          <div class="binding-hint">绑定后，浏览对应代码/提交时可看到本讨论入口（双向可达）</div>
        </div>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="submitting" @click="submit">发布</el-button>
        <el-button @click="$router.back()">取消</el-button>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { postsApi } from '@/api'
import PostEditor from '@/components/PostEditor.vue'

interface SnippetPayload {
  file_path: string
  content: string
  language: string
}

interface Binding {
  commit_sha: string
  file_path: string
  line_start: number | undefined
  line_end: number | undefined
}

const route = useRoute()
const router = useRouter()
const slug = route.params.slug as string
const loading = ref(false)
const submitting = ref(false)
const title = ref('')
const category = ref('question')
const content = ref('')
const snippets = ref<SnippetPayload[]>([])
const bindings = ref<Binding[]>([])

const binding = reactive<Binding>({
  commit_sha: '',
  file_path: '',
  line_start: undefined,
  line_end: undefined,
})

function onSnippet(sn: SnippetPayload) {
  snippets.value.push(sn)
}

function bindingLabel(b: Binding) {
  const parts = []
  if (b.commit_sha) parts.push(`commit ${b.commit_sha.slice(0, 8)}`)
  if (b.file_path) {
    parts.push(b.file_path)
    if (b.line_start) parts.push(`第 ${b.line_start}${b.line_end && b.line_end !== b.line_start ? '-' + b.line_end : ''} 行`)
  }
  return parts.join(' · ') || '绑定'
}

function addBinding() {
  if (!binding.commit_sha && !binding.file_path) {
    ElMessage.warning('请填写 Commit SHA 或文件路径')
    return
  }
  bindings.value.push({ ...binding })
  binding.commit_sha = ''
  binding.file_path = ''
  binding.line_start = undefined
  binding.line_end = undefined
}

async function submit() {
  if (!title.value.trim()) {
    ElMessage.warning('请填写标题')
    return
  }
  if (!content.value.trim()) {
    ElMessage.warning('请填写内容')
    return
  }
  submitting.value = true
  try {
    const data = await postsApi.create(slug, {
      title: title.value.trim(),
      category: category.value,
      content: content.value,
      snippets: snippets.value,
      bindings: bindings.value,
    }) as { post: { id: number } }
    ElMessage.success('发布成功')
    router.push(`/projects/${slug}/posts/${data.post.id}`)
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  // 支持从仓库页/提交页携带上下文进入发帖
  const q = route.query
  const commit = (q.bind_commit as string) || ''
  const file = (q.bind_file as string) || ''
  const lineStart = q.bind_line_start ? Number(q.bind_line_start) : undefined
  const lineEnd = q.bind_line_end ? Number(q.bind_line_end) : undefined
  if (commit || file) {
    bindings.value.push({ commit_sha: commit, file_path: file, line_start: lineStart, line_end: lineEnd })
  }
})
</script>

<style scoped>
.binding-box {
  width: 100%;
}
.binding-list {
  margin-bottom: 8px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.binding-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.binding-hint {
  color: #909399;
  font-size: 12px;
  margin-top: 6px;
}
</style>
