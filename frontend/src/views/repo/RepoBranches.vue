<template>
  <el-card v-loading="loading">
    <template #header>
      <div class="header-row">
        <span>分支管理</span>
        <el-button type="primary" size="small" @click="showCreate = true">
          <el-icon><Plus /></el-icon>新建分支
        </el-button>
      </div>
    </template>

    <div class="table-wrap">
    <el-table :data="branches">
      <el-table-column label="分支" min-width="200">
        <template #default="{ row }">
          <div class="branch-name">
            <el-icon color="#409eff"><Share /></el-icon>
            <span class="name">{{ row.name }}</span>
            <el-tag v-if="row.is_default" size="small" type="danger" effect="plain">默认</el-tag>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="最新提交" min-width="280">
        <template #default="{ row }">
          <div class="commit-msg">{{ row.commit_message }}</div>
          <div class="commit-sha">{{ row.commit_sha.slice(0, 8) }} · {{ row.author_name }}</div>
        </template>
      </el-table-column>
      <el-table-column label="更新时间" width="170">
        <template #default="{ row }">{{ formatTime(row.committed_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button
            v-if="canWrite && !row.is_default"
            size="small"
            type="danger"
            plain
            @click="removeBranch(row)"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    </div>

    <el-divider v-if="tags.length" content-position="left">标签</el-divider>
    <div v-if="tags.length" class="tag-list">
      <el-tag
        v-for="t in tags"
        :key="t.name"
        size="large"
        effect="plain"
        class="tag-item"
        @click="$router.push(`/projects/${slug}/commits/${t.commit_sha}`)"
      >
        <el-icon style="margin-right: 4px"><PriceTag /></el-icon>
        {{ t.name }} <span class="tag-sha">{{ t.commit_sha.slice(0, 8) }}</span>
      </el-tag>
    </div>

    <el-dialog v-model="showCreate" title="新建分支" width="420px">
      <el-form label-width="80px">
        <el-form-item label="分支名" required>
          <el-input v-model="createForm.name" placeholder="如：feature/login" />
        </el-form-item>
        <el-form-item label="来源分支">
          <el-select v-model="createForm.source" style="width: 100%">
            <el-option v-for="b in branches" :key="b.name" :label="b.name" :value="b.name" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="createBranch">创建</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { projectApi, repoApi, type Branch, type Project } from '@/api'

const route = useRoute()
const slug = route.params.slug as string
const branches = ref<Branch[]>([])
const tags = ref<{ name: string; commit_sha: string }[]>([])
const loading = ref(false)
const showCreate = ref(false)
const submitting = ref(false)
const myRole = ref<string | null>(null)
const canWrite = computed(() => myRole.value === 'owner' || myRole.value === 'developer')
const createForm = reactive({ name: '', source: '' })

async function load() {
  loading.value = true
  try {
    const [bd, td, pd] = await Promise.all([
      repoApi.branches(slug),
      repoApi.tags(slug),
      projectApi.get(slug),
    ])
    branches.value = (bd as { branches: Branch[] }).branches
    tags.value = (td as { tags: { name: string; commit_sha: string }[] }).tags
    myRole.value = (pd as { project: Project }).project.my_role ?? null
  } finally {
    loading.value = false
  }
}

async function createBranch() {
  if (!createForm.name) {
    ElMessage.warning('请输入分支名')
    return
  }
  submitting.value = true
  try {
    await repoApi.createBranch(slug, {
      name: createForm.name,
      source: createForm.source || undefined,
    })
    ElMessage.success('分支已创建')
    showCreate.value = false
    createForm.name = ''
    load()
  } finally {
    submitting.value = false
  }
}

async function removeBranch(row: Branch) {
  await ElMessageBox.confirm(`确定删除分支 ${row.name} 吗？`, '提示', { type: 'warning' })
  await repoApi.deleteBranch(slug, row.name)
  ElMessage.success('分支已删除')
  load()
}

function formatTime(t: string) {
  return t ? new Date(t).toLocaleString('zh-CN') : '-'
}

onMounted(load)
</script>

<style scoped>
.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.branch-name {
  display: flex;
  align-items: center;
  gap: 8px;
}
.name {
  font-weight: 600;
}
.commit-msg {
  font-weight: 500;
}
.commit-sha {
  color: #909399;
  font-size: 12px;
}
.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.tag-item {
  cursor: pointer;
}
.tag-sha {
  color: #909399;
  font-size: 12px;
}
</style>
