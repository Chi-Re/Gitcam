<template>
  <el-card>
    <template #header>新建 Issue</template>
    <el-form :model="form" label-width="90px" style="max-width: 700px">
      <el-form-item label="标题" required>
        <el-input v-model="form.title" placeholder="简要描述问题或需求" maxlength="255" />
      </el-form-item>
      <el-form-item label="描述">
        <div style="width: 100%">
          <el-tabs v-model="tab">
            <el-tab-pane label="编辑" name="edit">
              <el-input v-model="form.description" type="textarea" :rows="8" placeholder="支持 Markdown，可补充复现步骤等" />
            </el-tab-pane>
            <el-tab-pane label="预览" name="preview">
              <div class="markdown-body preview-box">
                <MarkdownView :content="form.description || ''" />
              </div>
            </el-tab-pane>
          </el-tabs>
        </div>
      </el-form-item>
      <el-form-item label="优先级">
        <el-radio-group v-model="form.priority">
          <el-radio-button value="urgent">紧急</el-radio-button>
          <el-radio-button value="high">高</el-radio-button>
          <el-radio-button value="medium">中</el-radio-button>
          <el-radio-button value="low">低</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="指派人">
        <el-select v-model="form.assignee_id" filterable clearable placeholder="选择成员" style="width: 220px">
          <el-option v-for="m in members" :key="m.user_id" :label="m.full_name" :value="m.user_id" />
        </el-select>
      </el-form-item>
      <el-form-item label="里程碑">
        <el-input v-model="form.milestone" placeholder="如：实验二" style="width: 220px" />
      </el-form-item>
      <el-form-item label="标签">
        <el-select v-model="form.labels" multiple filterable allow-create default-first-option style="width: 100%">
          <el-option label="bug" value="bug" />
          <el-option label="feature" value="feature" />
          <el-option label="question" value="question" />
          <el-option label="enhancement" value="enhancement" />
          <el-option label="documentation" value="documentation" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="submitting" @click="submit">创建</el-button>
        <el-button @click="$router.back()">取消</el-button>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { issuesApi, projectApi, type ProjectMember } from '@/api'
import MarkdownView from '@/components/MarkdownView.vue'

const route = useRoute()
const router = useRouter()
const slug = route.params.slug as string
const members = ref<ProjectMember[]>([])
const submitting = ref(false)
const tab = ref('edit')

const form = reactive({
  title: '',
  description: '',
  priority: 'medium',
  assignee_id: undefined as number | undefined,
  milestone: '',
  labels: [] as string[],
})

async function submit() {
  if (!form.title.trim()) {
    ElMessage.warning('请填写标题')
    return
  }
  submitting.value = true
  try {
    const data = await issuesApi.create(slug, {
      ...form,
      description: form.description || undefined,
      milestone: form.milestone || undefined,
      assignee_id: form.assignee_id,
    }) as { issue: { id: number } }
    ElMessage.success('Issue 已创建')
    router.push(`/projects/${slug}/issues/${data.issue.id}`)
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  const data = await projectApi.members(slug) as { members: ProjectMember[] }
  members.value = data.members
})
</script>

<style scoped>
.preview-box {
  min-height: 120px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 12px;
}
</style>
