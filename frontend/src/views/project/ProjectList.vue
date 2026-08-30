<template>
  <div>
    <div class="toolbar">
      <el-input
        v-model="query"
        placeholder="搜索项目名称 / 标签 / 简介"
        clearable
        style="width: 320px"
        @keyup.enter="search"
        @clear="search"
      >
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-select v-model="visibility" placeholder="可见性" clearable style="width: 130px" @change="search">
        <el-option label="公开" value="public" />
        <el-option label="私有" value="private" />
      </el-select>
      <el-button type="primary" @click="$router.push('/projects/create')">
        <el-icon><Plus /></el-icon>创建项目
      </el-button>
    </div>

    <el-table v-loading="loading" :data="projects" class="project-table">
      <el-table-column label="项目" min-width="280">
        <template #default="{ row }">
          <div class="project-name" @click="$router.push(`/projects/${row.slug}`)">
            {{ row.name }}
            <el-tag size="small" :type="row.visibility === 'public' ? 'success' : 'info'" class="vis-tag">
              {{ row.visibility === 'public' ? '公开' : '私有' }}
            </el-tag>
          </div>
          <div class="project-desc">{{ row.description || '暂无简介' }}</div>
          <div class="project-meta">
            <el-tag
              v-for="tag in row.tags"
              :key="tag"
              size="small"
              type="primary"
              effect="plain"
              class="tag-item"
              @click="setTag(tag)"
            >
              {{ tag }}
            </el-tag>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="模板" width="130">
        <template #default="{ row }">{{ row.template_name }}</template>
      </el-table-column>
      <el-table-column label="创建者" width="120">
        <template #default="{ row }">{{ row.owner?.full_name }}</template>
      </el-table-column>
      <el-table-column label="成员" width="80" align="center">
        <template #default="{ row }">{{ row.member_count }}</template>
      </el-table-column>
      <el-table-column label="更新时间" width="170">
        <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-if="total > perPage"
      layout="prev, pager, next"
      :total="total"
      :page-size="perPage"
      :current-page="page"
      @current-change="onPageChange"
      class="pagination"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { projectApi, type Project } from '@/api'

const router = useRouter()
const projects = ref<Project[]>([])
const loading = ref(false)
const query = ref('')
const visibility = ref('')
const page = ref(1)
const perPage = 20
const total = ref(0)

async function load() {
  loading.value = true
  try {
    const data = await projectApi.list({
      q: query.value || undefined,
      visibility: visibility.value || undefined,
      page: page.value,
      per_page: perPage,
    }) as { items: Project[]; total: number }
    projects.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function search() {
  page.value = 1
  load()
}

function setTag(tag: string) {
  query.value = tag
  search()
}

function onPageChange(p: number) {
  page.value = p
  load()
}

function formatTime(t: string) {
  return t ? new Date(t).toLocaleString('zh-CN') : '-'
}

onMounted(load)
</script>

<style scoped>
.toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  align-items: center;
}
.project-name {
  font-weight: 600;
  color: #409eff;
  cursor: pointer;
  font-size: 15px;
}
.vis-tag {
  margin-left: 8px;
}
.project-desc {
  color: #909399;
  font-size: 13px;
  margin: 4px 0;
}
.tag-item {
  margin-right: 6px;
  cursor: pointer;
}
.pagination {
  margin-top: 16px;
  justify-content: flex-end;
}
</style>
