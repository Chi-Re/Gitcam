<template>
  <el-card>
    <template #header>发布社区帖子</template>
    <el-form label-width="80px" style="max-width: 900px">
      <el-form-item label="标题" required>
        <el-input v-model="title" placeholder="一句话说明主题" maxlength="255" />
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
        <PostEditor v-model="content" community :slug="''" @snippet="onSnippet" />
        <div class="hint">代码引用仅限公共仓库；也可手动粘贴代码块（Markdown ``` 语法）</div>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="submitting" @click="submit">发布</el-button>
        <el-button @click="$router.back()">取消</el-button>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { communityApi } from '@/api'
import PostEditor from '@/components/PostEditor.vue'

interface SnippetPayload {
  file_path: string
  content: string
  language: string
  project_id?: number
}

const router = useRouter()
const submitting = ref(false)
const title = ref('')
const category = ref('question')
const content = ref('')
const snippets = ref<SnippetPayload[]>([])

function onSnippet(sn: SnippetPayload) {
  snippets.value.push(sn)
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
    const data = await communityApi.create({
      title: title.value.trim(),
      category: category.value,
      content: content.value,
      snippets: snippets.value,
    }) as { post: { id: number } }
    ElMessage.success('发布成功')
    router.push(`/community/${data.post.id}`)
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.hint {
  color: #909399;
  font-size: 12px;
  margin-top: 4px;
}
</style>
