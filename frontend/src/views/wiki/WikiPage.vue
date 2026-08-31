<template>
  <div class="wiki-layout" v-loading="loading">
    <div class="wiki-sidebar" v-if="!isMobile">
      <el-card class="sidebar-card">
        <template #header>
          <div class="sidebar-head">
            <span>Wiki 页面</span>
            <el-button v-if="myRole !== 'viewer'" size="small" type="primary" @click="startCreate">
              <el-icon><Plus /></el-icon>
            </el-button>
          </div>
        </template>
        <div
          v-for="p in sortedPages"
          :key="p.id"
          class="page-item"
          :class="{ active: current?.id === p.id }"
          :style="{ paddingLeft: 12 + p.depth * 18 + 'px' }"
          @click="openPage(p)"
        >
          <FileTypeIcon :name="p.title + '.md'" :size="14" />
          <span>{{ p.title }}</span>
        </div>
        <el-empty v-if="!pages.length" description="暂无页面" :image-size="50" />
      </el-card>
    </div>

    <div class="wiki-content">
      <el-card v-loading="pageLoading">
        <template #header>
          <div class="content-head" v-if="current">
            <div class="head-left">
              <el-button v-if="isMobile" size="small" text class="sidebar-toggle" @click="drawerOpen = true">
                <el-icon :size="16"><Menu /></el-icon>
              </el-button>
              <span class="page-title">{{ current.title }}</span>
              <el-tag size="small" effect="plain">v{{ current.version }}</el-tag>
            </div>
            <div class="head-actions">
              <el-button v-if="myRole !== 'viewer'" size="small" type="primary" plain @click="startEdit">
                <el-icon><Edit /></el-icon>编辑
              </el-button>
              <el-button size="small" @click="showVersions">
                <el-icon><Clock /></el-icon>历史版本
              </el-button>
              <el-button v-if="canDelete" size="small" type="danger" plain @click="removePage">删除</el-button>
            </div>
          </div>
        </template>

        <div v-if="editing">
          <div class="edit-tabs">
            <el-tabs v-model="editTab">
              <el-tab-pane label="编辑" name="edit">
                <el-input v-model="editContent" type="textarea" :rows="16" placeholder="支持 Markdown" />
              </el-tab-pane>
              <el-tab-pane label="预览" name="preview">
                <div class="markdown-body preview-box">
                  <MarkdownView :content="editContent" />
                </div>
              </el-tab-pane>
            </el-tabs>
          </div>
          <div class="edit-actions">
            <el-button type="primary" :loading="saving" @click="saveEdit">保存（生成新版本）</el-button>
            <el-button @click="cancelEdit">取消</el-button>
          </div>
        </div>

        <div v-else-if="current">
          <div class="markdown-body">
            <MarkdownView :content="current.content || ''" />
          </div>
          <div class="last-edited" v-if="current.editor">
            最后编辑：{{ current.editor.full_name }} · {{ formatTime(current.updated_at) }}
          </div>
        </div>
        <el-empty v-else description="从左侧选择一个页面，或创建第一个 Wiki 页面" />
      </el-card>
    </div>

    <el-dialog v-model="createOpen" title="创建 Wiki 页面" width="480px">
      <el-form label-width="70px">
        <el-form-item label="路径" required>
          <el-input v-model="createForm.path" placeholder="如：guide/start（字母/数字/中文/. / -）" />
        </el-form-item>
        <el-form-item label="标题" required>
          <el-input v-model="createForm.title" placeholder="页面标题" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createOpen = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="createPage">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="versionsOpen" title="历史版本" width="560px">
      <div v-loading="versionsLoading" class="version-list">
        <div
          v-for="v in versions"
          :key="v.version"
          class="version-item"
          :class="{ current: v.version === current?.version }"
        >
          <div class="version-head">
            <span class="v-label">v{{ v.version }}</span>
            <span class="v-editor">{{ v.editor?.full_name }}</span>
            <span class="v-time">{{ formatTime(v.created_at) }}</span>
            <el-button
              v-if="v.version !== current?.version && myRole !== 'viewer'"
              size="small"
              type="primary"
              plain
              @click="rollback(v)"
            >回滚到此版本</el-button>
            <el-tag v-if="v.version === current?.version" size="small" type="success">当前</el-tag>
          </div>
        </div>
        <el-empty v-if="!versions.length" description="暂无历史版本" :image-size="50" />
      </div>
    </el-dialog>

    <!-- 手机端：页面列表抽屉 -->
    <el-drawer v-model="drawerOpen" title="Wiki 页面" size="260px">
      <el-card class="sidebar-card" :body-style="{ padding: '0' }">
        <div
          v-for="p in sortedPages"
          :key="p.id"
          class="page-item"
          :class="{ active: current?.id === p.id }"
          :style="{ paddingLeft: 12 + p.depth * 18 + 'px' }"
          @click="openPage(p); drawerOpen = false"
        >
          <FileTypeIcon :name="p.title + '.md'" :size="14" />
          <span>{{ p.title }}</span>
        </div>
        <el-empty v-if="!pages.length" description="暂无页面" :image-size="50" />
      </el-card>
      <el-button
        v-if="myRole !== 'viewer'"
        type="primary"
        plain
        style="width: 100%; margin-top: 12px"
        @click="drawerOpen = false; startCreate()"
      >
        <el-icon><Plus /></el-icon>新建页面
      </el-button>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { projectApi, wikiApi, type Project, type WikiPage, type WikiVersion } from '@/api'
import MarkdownView from '@/components/MarkdownView.vue'
import FileTypeIcon from '@/components/FileTypeIcon.vue'

interface PageNode extends WikiPage {
  depth: number
}

const route = useRoute()
const router = useRouter()
const slug = route.params.slug as string
const drawerOpen = ref(false)
const isMobile = ref(window.innerWidth < 768)
const loading = ref(false)
const pageLoading = ref(false)
const pages = ref<PageNode[]>([])
const current = ref<WikiPage | null>(null)
const myRole = ref<string | null>(null)
const editing = ref(false)
const editTab = ref('edit')
const editContent = ref('')
const saving = ref(false)
const createOpen = ref(false)
const creating = ref(false)
const createForm = reactive({ path: '', title: '' })
const versionsOpen = ref(false)
const versionsLoading = ref(false)
const versions = ref<WikiVersion[]>([])

const sortedPages = computed(() => {
  const map: Record<string, number> = {}
  return [...pages.value].sort((a, b) => {
    const keyA = a.path.split('/')
    const keyB = b.path.split('/')
    for (let i = 0; i < Math.min(keyA.length, keyB.length); i++) {
      if (keyA[i] !== keyB[i]) {
        const da = map[keyA[i]] ?? (map[keyA[i]] = pages.value.length)
        const db = map[keyB[i]] ?? (map[keyB[i]] = pages.value.length)
        return da - db
      }
    }
    return keyA.length - keyB.length
  })
})

const canDelete = computed(() => {
  if (!current.value) return false
  const me = undefined // 简化：服务端校验，前端隐藏对 viewer
  return myRole.value !== 'viewer'
})

async function loadTree() {
  loading.value = true
  try {
    const [treeData, projectData] = await Promise.all([
      wikiApi.tree(slug),
      projectApi.get(slug),
    ])
    pages.value = (treeData as { pages: WikiPage[] }).pages.map((p) => ({
      ...p,
      depth: p.path.split('/').length - 1,
    }))
    myRole.value = (projectData as { project: Project }).project.my_role ?? null
  } finally {
    loading.value = false
  }
}

async function openPage(p: PageNode) {
  pageLoading.value = true
  try {
    current.value = (await wikiApi.get(slug, p.id) as { page: WikiPage }).page
    editing.value = false
  } finally {
    pageLoading.value = false
  }
}

function startCreate() {
  createForm.path = ''
  createForm.title = ''
  createOpen.value = true
}

async function createPage() {
  if (!createForm.path.trim() || !createForm.title.trim()) {
    ElMessage.warning('请填写路径和标题')
    return
  }
  creating.value = true
  try {
    const data = await wikiApi.create(slug, {
      path: createForm.path.trim(),
      title: createForm.title.trim(),
      content: '',
    }) as { page: WikiPage }
    createOpen.value = false
    await loadTree()
    openPage({ ...data.page, depth: data.page.path.split('/').length - 1 })
  } finally {
    creating.value = false
  }
}

function startEdit() {
  if (!current.value) return
  editing.value = true
  editTab.value = 'edit'
  editContent.value = current.value.content || ''
}

function cancelEdit() {
  editing.value = false
}

async function saveEdit() {
  if (!current.value) return
  saving.value = true
  try {
    const data = await wikiApi.update(slug, current.value.id, {
      content: editContent.value,
      title: current.value.title,
    }) as { page: WikiPage }
    current.value = data.page
    editing.value = false
    ElMessage.success(`已保存（v${data.page.version}）`)
    loadTree()
  } finally {
    saving.value = false
  }
}

async function removePage() {
  if (!current.value) return
  await ElMessageBox.confirm(`确定删除页面「${current.value.title}」？历史版本将一并删除`, '删除', {
    type: 'warning',
  })
  await wikiApi.remove(slug, current.value.id)
  current.value = null
  ElMessage.success('已删除')
  loadTree()
}

async function showVersions() {
  if (!current.value) return
  versionsOpen.value = true
  versionsLoading.value = true
  try {
    versions.value = (await wikiApi.versions(slug, current.value.id) as { versions: WikiVersion[] }).versions
  } finally {
    versionsLoading.value = false
  }
}

async function rollback(v: WikiVersion) {
  if (!current.value) return
  await ElMessageBox.confirm(`确定回滚到 v${v.version}？当前内容将保留为新版本快照`, '回滚', { type: 'warning' })
  const data = await wikiApi.rollback(slug, current.value.id, v.version) as { page: WikiPage }
  current.value = data.page
  versionsOpen.value = false
  ElMessage.success(`已回滚到 v${v.version}（当前为 v${data.page.version}）`)
  loadTree()
}

function formatTime(t: string) {
  return t ? new Date(t).toLocaleString('zh-CN') : '-'
}

onMounted(async () => {
  window.addEventListener('resize', onResize)
  await loadTree()
  const first = pages.value[0]
  if (first) openPage(first)
})

function onResize() {
  isMobile.value = window.innerWidth < 768
  if (!isMobile.value) drawerOpen.value = false
}

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
})
</script>

<style scoped>
.wiki-layout {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}
@media (max-width: 767px) {
  .wiki-layout {
    flex-direction: column;
  }
  .sidebar-toggle {
    padding: 4px;
  }
}
.wiki-sidebar {
  width: 260px;
  flex-shrink: 0;
}
.sidebar-card {
  position: sticky;
  top: 0;
}
.sidebar-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.page-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  cursor: pointer;
  border-radius: 4px;
  font-size: 13.5px;
}
.page-item:hover {
  background: #f5f7fa;
}
.page-item.active {
  background: #ecf5ff;
  color: #409eff;
  font-weight: 500;
}
.wiki-content {
  flex: 1;
  min-width: 0;
}
.content-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}
.head-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.page-title {
  font-weight: 600;
  font-size: 16px;
}
.head-actions {
  display: flex;
  gap: 6px;
}
.edit-actions {
  margin-top: 10px;
  display: flex;
  gap: 8px;
}
.preview-box {
  min-height: 200px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 12px;
}
.last-edited {
  margin-top: 20px;
  color: #909399;
  font-size: 12px;
  border-top: 1px solid #f0f2f5;
  padding-top: 10px;
}
.version-list {
  max-height: 400px;
  overflow: auto;
}
.version-item {
  padding: 10px 6px;
  border-bottom: 1px solid #f0f2f5;
}
.version-head {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
}
.v-label {
  font-weight: 600;
}
.v-editor {
  color: #606266;
}
.v-time {
  color: #909399;
  font-size: 12px;
}
</style>
