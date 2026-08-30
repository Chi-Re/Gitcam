<template>
  <el-card>
    <template #header>内容管理</template>
    <el-tabs v-model="tab">
      <!-- 项目 -->
      <el-tab-pane label="项目" name="projects">
        <div class="tab-bar">
          <el-input v-model="projectQ" placeholder="搜索项目名/标识" clearable size="small" style="width: 240px" @keyup.enter="loadProjects" @clear="loadProjects" />
        </div>
        <el-table v-loading="loading" :data="projects">
          <el-table-column label="ID" width="60" prop="id" />
          <el-table-column label="名称" min-width="160">
            <template #default="{ row }">{{ row.name }}</template>
          </el-table-column>
          <el-table-column label="标识" width="140" prop="slug" />
          <el-table-column label="创建者" width="100">
            <template #default="{ row }">{{ row.owner?.full_name }}</template>
          </el-table-column>
          <el-table-column label="可见性" width="80">
            <template #default="{ row }">
              <el-tag size="small" :type="row.visibility === 'public' ? 'success' : 'info'">
                {{ row.visibility === 'public' ? '公开' : '私有' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="90">
            <template #default="{ row }">
              <el-button size="small" type="danger" plain @click="removeProject(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- 帖子 -->
      <el-tab-pane label="帖子" name="posts">
        <div class="tab-bar">
          <el-input v-model="postQ" placeholder="搜索帖子标题" clearable size="small" style="width: 240px" @keyup.enter="loadPosts" @clear="loadPosts" />
        </div>
        <el-table v-loading="loading" :data="posts">
          <el-table-column label="ID" width="60" prop="id" />
          <el-table-column label="标题" min-width="200" prop="title" />
          <el-table-column label="分类" width="100">
            <template #default="{ row }">{{ row.category_label }}</template>
          </el-table-column>
          <el-table-column label="作者" width="100">
            <template #default="{ row }">{{ row.author?.full_name }}</template>
          </el-table-column>
          <el-table-column label="操作" width="90">
            <template #default="{ row }">
              <el-button size="small" type="danger" plain @click="removePost(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

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
import { ElMessage, ElMessageBox } from 'element-plus'
import { adminApi, type Post, type Project } from '@/api'

const tab = ref('projects')
const projects = ref<Project[]>([])
const posts = ref<Post[]>([])
const loading = ref(false)
const projectQ = ref('')
const postQ = ref('')
const page = ref(1)
const perPage = 20
const total = ref(0)

async function loadProjects() {
  loading.value = true
  try {
    const data = await adminApi.projects({
      q: projectQ.value || undefined,
      page: page.value,
      per_page: perPage,
    }) as { items: Project[]; total: number }
    projects.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function loadPosts() {
  loading.value = true
  try {
    const data = await adminApi.posts({
      q: postQ.value || undefined,
      page: page.value,
      per_page: perPage,
    }) as { items: Post[]; total: number }
    posts.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function load() {
  page.value = 1
  if (tab.value === 'projects') loadProjects()
  else loadPosts()
}

function onPageChange(p: number) {
  page.value = p
  if (tab.value === 'projects') loadProjects()
  else loadPosts()
}

async function removeProject(row: Project) {
  await ElMessageBox.confirm(`删除项目「${row.name}」将同时删除仓库与全部内容，确认？`, '删除项目', { type: 'warning' })
  await adminApi.deleteProject(row.slug)
  ElMessage.success('已删除')
  loadProjects()
}

async function removePost(row: Post) {
  await ElMessageBox.confirm(`删除帖子「${row.title}」？`, '删除', { type: 'warning' })
  await adminApi.deletePost(row.id)
  ElMessage.success('已删除')
  loadPosts()
}

onMounted(loadProjects)
</script>

<style scoped>
.tab-bar {
  margin-bottom: 12px;
}
.pagination {
  margin-top: 16px;
  justify-content: flex-end;
}
</style>
