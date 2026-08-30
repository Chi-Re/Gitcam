<template>
  <el-card v-loading="loading">
    <template #header>
      <div class="card-header">
        <span>创建项目</span>
        <span class="sub">项目创建后将自动初始化 Git 仓库与项目空间</span>
      </div>
    </template>

    <el-form :model="form" label-width="90px" style="max-width: 560px">
      <el-form-item label="项目名称" required>
        <el-input v-model="form.name" placeholder="如：计网课程作业" />
      </el-form-item>
      <el-form-item label="项目标识" required>
        <el-input v-model="form.slug" placeholder="用于 git clone 地址，留空自动生成">
          <template #append>{{ form.slug ? '.git' : '' }}</template>
        </el-input>
      </el-form-item>
      <el-form-item label="项目简介">
        <el-input v-model="form.description" type="textarea" :rows="3" placeholder="一句话介绍项目" />
      </el-form-item>
      <el-form-item label="可见性">
        <el-radio-group v-model="form.visibility">
          <el-radio value="private">私有（仅成员可见）</el-radio>
          <el-radio value="public">公开（所有人可浏览）</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="项目模板">
        <el-radio-group v-model="form.template_type" class="template-group">
          <el-card
            v-for="t in templates"
            :key="t.type"
            class="template-card"
            :class="{ selected: form.template_type === t.type }"
            @click="form.template_type = t.type"
          >
            <div class="template-name">{{ t.name }}</div>
            <div class="template-desc">{{ t.description }}</div>
            <div class="template-files">{{ t.files.join(' / ') }}</div>
          </el-card>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="标签">
        <el-select
          v-model="form.tags"
          multiple
          filterable
          allow-create
          default-first-option
          placeholder="添加标签，如：Python"
          style="width: 100%"
        />
      </el-form-item>
      <el-form-item label="主要语言">
        <el-select v-model="form.language" filterable allow-create clearable placeholder="选择语言" style="width: 100%">
          <el-option
            v-for="lang in languages"
            :key="lang"
            :label="lang"
            :value="lang"
          />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="submitting" @click="onSubmit">创建项目</el-button>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { projectApi } from '@/api'

interface Template {
  type: string
  name: string
  description: string
  files: string[]
}

const router = useRouter()
const loading = ref(false)
const submitting = ref(false)
const templates = ref<Template[]>([])
const languages = [
  'Python', 'JavaScript', 'TypeScript', 'Java', 'C', 'C++', 'C#', 'Go',
  'Rust', 'PHP', 'Ruby', 'HTML', 'CSS', 'SQL', 'Shell', 'Vue', 'React', '其他',
]

const form = reactive({
  name: '',
  slug: '',
  description: '',
  visibility: 'private',
  template_type: 'blank',
  tags: [] as string[],
  language: '',
})

async function onSubmit() {
  if (!form.name) {
    ElMessage.warning('请填写项目名称')
    return
  }
  submitting.value = true
  try {
    const data = await projectApi.create({
      ...form,
      slug: form.slug || undefined,
      language: form.language || undefined,
    }) as { project: { slug: string } }
    ElMessage.success('项目创建成功')
    router.push(`/projects/${data.project.slug}`)
  } catch {
    // 错误信息已由拦截器提示
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  loading.value = true
  try {
    templates.value = (await projectApi.templates() as { templates: Template[] }).templates
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.card-header {
  display: flex;
  align-items: baseline;
  gap: 12px;
}
.sub {
  font-size: 12px;
  color: #909399;
  font-weight: normal;
}
.template-group {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  width: 100%;
}
.template-card {
  cursor: pointer;
  margin: 0;
  border: 2px solid #e4e7ed;
  transition: border-color 0.2s;
}
.template-card.selected {
  border-color: #409eff;
}
.template-name {
  font-weight: 600;
}
.template-desc {
  font-size: 12px;
  color: #909399;
  margin: 4px 0;
}
.template-files {
  font-size: 11px;
  color: #c0c4cc;
}
</style>
