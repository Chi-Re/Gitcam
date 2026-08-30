<template>
  <div>
    <div class="repo-layout">
      <!-- 左侧文件树（桌面端，默认收起，按钮唤出） -->
      <div class="repo-side" v-if="isDesktop && treeOpen">
        <el-card class="side-card" :body-style="{ padding: '0' }">
          <div class="side-head">
            <span class="side-title">{{ project?.name || '仓库文件' }}</span>
          </div>
          <div class="side-body">
            <RepoFileTree
              :key="`${branch}-${slug}`"
              :slug="slug"
              :branch="branch"
              :branches="branches"
              :current-path="path"
              @branch-change="onBranchChange"
              @file-click="openBlob"
            />
          </div>
        </el-card>
      </div>

      <!-- 右侧主区 -->
      <div class="repo-main">
        <div class="toolbar">
          <el-button v-if="isDesktop" size="small" :type="treeOpen ? 'primary' : 'default'" @click="treeOpen = !treeOpen">
            <el-icon><FolderOpened /></el-icon>文件树
          </el-button>
          <el-button v-if="!isDesktop" size="small" @click="drawerOpen = true">
            <el-icon><FolderOpened /></el-icon>文件
          </el-button>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item>
              <span class="crumb-link" @click="goPath('')">{{ project?.name || '仓库' }}</span>
            </el-breadcrumb-item>
            <el-breadcrumb-item v-for="(part, i) in parts" :key="i">
              <span class="crumb-link" @click="goPath(parts.slice(0, i + 1).join('/'))">{{ part }}</span>
            </el-breadcrumb-item>
          </el-breadcrumb>
          <el-select
            v-if="!isDesktop"
            :model-value="branch"
            size="small"
            style="width: 130px"
            @change="onBranchChange"
          >
            <el-option v-for="b in branches" :key="b" :label="b" :value="b">
              <el-icon><Share /></el-icon>
              {{ b }}
            </el-option>
          </el-select>
          <el-button
            v-if="viewMode === 'preview'"
            size="small"
            class="back-btn"
            @click="backToList"
          >
            <el-icon><Back /></el-icon>返回列表
          </el-button>
        </div>

        <!-- 列表模式：文件列表 + README -->
        <template v-if="viewMode === 'list'">
          <el-card v-loading="loading" class="tree-card">
            <template v-if="entries.length">
              <div
                v-for="entry in entries"
                :key="entry.path"
                class="entry"
                @click="onEntryClick(entry)"
              >
                <FileTypeIcon :name="entry.name" :type="entry.type === 'tree' ? 'tree' : 'file'" class="entry-icon" />
                <span class="entry-name">{{ entry.name }}</span>
                <span class="entry-meta" v-if="entry.last_commit_message">
                  {{ entry.last_commit_message }}
                </span>
                <span class="entry-size" v-if="entry.type === 'blob'">{{ formatSize(entry.size) }}</span>
              </div>
            </template>
            <el-empty v-else-if="!loading" description="仓库为空" />
          </el-card>

          <el-card v-if="readme" class="readme-card">
            <template #header>README</template>
            <MarkdownView :content="readmeContent" />
          </el-card>
        </template>

        <!-- 预览模式：内嵌文件内容面板 -->
        <el-card v-else-if="viewMode === 'preview'" class="preview-card" v-loading="blobLoading">
          <template #header>
            <div class="preview-head">
              <FileTypeIcon :name="blobPath" :size="16" />
              <span class="preview-path">{{ blobPath }}</span>
              <div class="preview-actions">
                <el-button v-if="fileDiscussions.length" size="small" type="primary" plain @click="openFileDiscussions">
                  <el-icon><ChatDotRound /></el-icon>{{ fileDiscussions.length }} 条讨论
                </el-button>
                <el-button size="small" @click="downloadRaw">下载</el-button>
              </div>
            </div>
          </template>
          <div>
            <MarkdownView v-if="isMarkdown(blobPath)" :content="blobContent" class="blob-body" />
            <div v-else class="blob-body">
              <!-- 有行级讨论时逐行渲染带标记 -->
              <div v-if="lineDiscussions.size" class="line-file">
                <div
                  v-for="(line, idx) in blobLines"
                  :key="idx"
                  class="line-row"
                  :class="{ 'has-discussion': lineDiscussions.has(idx + 1) }"
                >
                  <span class="line-num">{{ idx + 1 }}</span>
                  <span class="line-text">{{ line }}</span>
                  <el-popover
                    v-if="lineDiscussions.has(idx + 1)"
                    :width="280"
                    trigger="click"
                    :teleported="true"
                  >
                    <template #reference>
                      <el-badge :value="lineDiscussions.get(idx + 1)!.length" class="line-badge">
                        <el-button size="small" circle type="warning" plain class="line-marker">
                          <el-icon size="12"><ChatDotRound /></el-icon>
                        </el-button>
                      </el-badge>
                    </template>
                    <div class="marker-pop">
                      <div
                        v-for="d in lineDiscussions.get(idx + 1)"
                        :key="d.id"
                        class="marker-item"
                        @click="jumpToPost(d)"
                      >
                        <div class="marker-title">{{ d.post?.title }}</div>
                        <div class="marker-meta">
                          {{ d.post?.author?.full_name }} · {{ d.post?.status === 'solved' ? '已解决' : d.post?.status === 'closed' ? '已关闭' : '讨论中' }}
                        </div>
                      </div>
                    </div>
                  </el-popover>
                </div>
              </div>
              <CodeView v-else :filename="blobPath" :content="blobContent" :size="blobSize" />
            </div>
            <el-empty v-if="!blobLoading && blobTruncated" description="文件过大，仅显示前 1MB" />
          </div>
        </el-card>
      </div>
    </div>

    <!-- 移动端：文件树抽屉 -->
    <el-drawer v-model="drawerOpen" :title="project?.name || '仓库文件'" size="300px">
      <RepoFileTree
        :key="`drawer-${branch}-${slug}`"
        :slug="slug"
        :branch="branch"
        :branches="branches"
        :current-path="path"
        @branch-change="onBranchChange"
        @file-click="onDrawerFileClick"
      />
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { repoApi, projectApi, discussionApi, type DiscussionLinkItem, type Project, type TreeEntry } from '@/api'
import MarkdownView from '@/components/MarkdownView.vue'
import CodeView from '@/components/CodeView.vue'
import FileTypeIcon from '@/components/FileTypeIcon.vue'
import RepoFileTree from '@/components/RepoFileTree.vue'

const route = useRoute()
const router = useRouter()
const slug = route.params.slug as string

const project = ref<Project | null>(null)
const entries = ref<TreeEntry[]>([])
const branches = ref<string[]>([])
const branch = ref('')
const path = ref('')
const readme = ref('')
const readmeContent = ref('')
const loading = ref(false)
const viewMode = ref<'list' | 'preview'>('list')
const blobLoading = ref(false)
const blobContent = ref('')
const blobSize = ref<number | null>(null)
const blobTruncated = ref(false)
const blobPath = ref('')
const fileDiscussions = ref<DiscussionLinkItem[]>([])
const lineDiscussions = ref(new Map<number, DiscussionLinkItem[]>())
const drawerOpen = ref(false)
const treeOpen = ref(false)
const isDesktop = ref(window.innerWidth >= 992)

const blobLines = computed(() => blobContent.value.split('\n'))

const parts = computed(() => (path.value ? path.value.split('/') : []))

function onResize() {
  isDesktop.value = window.innerWidth >= 992
  if (isDesktop.value) drawerOpen.value = false
}

onMounted(() => {
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
})

watch(
  () => route.query,
  () => {
    path.value = (route.query.path as string) || ''
    if (route.query.path) {
      // 若带 path 查询，直接加载该路径的树
      loadTree()
    }
  },
)

async function loadTree() {
  loading.value = true
  try {
    const data = await repoApi.tree(slug, {
      path: path.value || undefined,
      branch: branch.value || undefined,
    }) as { entries: TreeEntry[]; branch: string; readme: string | null }
    entries.value = data.entries
    readme.value = data.readme || ''
    if (data.branch) branch.value = data.branch
    if (readme.value) {
      const blob = await repoApi.blob(slug, { path: readme.value, branch: branch.value }) as {
        content: string
      }
      readmeContent.value = blob.content
    } else {
      readmeContent.value = ''
    }
  } finally {
    loading.value = false
  }
}

function goPath(p: string) {
  path.value = p
  router.replace({
    path: `/projects/${slug}/repo`,
    query: p ? { path: p, branch: branch.value || undefined } : { branch: branch.value || undefined },
  })
  loadTree()
}

function onEntryClick(entry: TreeEntry) {
  if (entry.type === 'tree') {
    goPath(entry.path)
  } else {
    openBlob(entry)
  }
}

async function openBlob(entry: TreeEntry) {
  viewMode.value = 'preview'
  drawerOpen.value = false
  blobLoading.value = true
  blobPath.value = entry.path
  try {
    const data = await repoApi.blob(slug, {
      path: entry.path,
      branch: branch.value || undefined,
    }) as { content: string; size: number; truncated: boolean }
    blobContent.value = data.content
    blobSize.value = data.size
    blobTruncated.value = data.truncated
    await loadFileDiscussions()
  } finally {
    blobLoading.value = false
  }
}

function onDrawerFileClick(entry: TreeEntry) {
  openBlob(entry)
}

function backToList() {
  viewMode.value = 'list'
}

async function loadFileDiscussions() {
  fileDiscussions.value = []
  lineDiscussions.value = new Map()
  if (!blobPath.value) return
  const data = await discussionApi.query(slug, { file_path: blobPath.value }) as { items: DiscussionLinkItem[] }
  fileDiscussions.value = data.items
  const map = new Map<number, DiscussionLinkItem[]>()
  for (const item of data.items) {
    if (item.line_start) {
      const list = map.get(item.line_start) || []
      list.push(item)
      map.set(item.line_start, list)
    }
  }
  lineDiscussions.value = map
}

function jumpToPost(d: DiscussionLinkItem) {
  router.push(`/projects/${slug}/posts/${d.post_id}`)
}

function openFileDiscussions() {
  router.push({
    path: `/projects/${slug}/posts/create`,
    query: { bind_file: blobPath.value },
  })
}

async function downloadRaw() {
  const resp = await repoApi.raw(slug, { path: blobPath.value, branch: branch.value || undefined })
  const url = URL.createObjectURL(resp as unknown as Blob)
  const a = document.createElement('a')
  a.href = url
  a.download = blobPath.value.split('/').pop() || 'file'
  a.click()
  URL.revokeObjectURL(url)
}

function isMarkdown(name: string) {
  return /\.(md|markdown)$/i.test(name)
}

function formatSize(size?: number | null) {
  if (size == null) return ''
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(2)} MB`
}

function onBranchChange(b: string) {
  branch.value = b
  goPath(path.value)
}

onMounted(async () => {
  project.value = (await projectApi.get(slug) as { project: Project }).project
  const bd = await repoApi.branches(slug) as { branches: { name: string }[] }
  branches.value = bd.branches.map((b) => b.name)
  loadTree()
})
</script>

<style scoped>
.repo-layout {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}
.repo-side {
  width: 280px;
  flex-shrink: 0;
  position: sticky;
  top: 0;
}
.side-card {
  margin-bottom: 0;
}
.side-head {
  padding: 10px 14px;
  border-bottom: 1px solid #f0f2f5;
}
.side-title {
  font-weight: 600;
  font-size: 14px;
}
.side-body {
  height: calc(100vh - 200px);
  min-height: 320px;
}
.repo-main {
  flex: 1;
  min-width: 0;
}
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  gap: 8px;
  flex-wrap: wrap;
}
.back-btn {
  margin-left: auto;
}
.crumb-link {
  cursor: pointer;
  color: #409eff;
}
.tree-card {
  margin-bottom: 16px;
}
.entry {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  cursor: pointer;
  border-radius: 4px;
}
.entry:hover {
  background: #f5f7fa;
}
.entry-icon {
  font-size: 18px;
  line-height: 1;
}
.entry-name {
  font-weight: 500;
}
.entry-meta {
  color: #909399;
  font-size: 12px;
  margin-left: 12px;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.entry-size {
  color: #c0c4cc;
  font-size: 12px;
}
.preview-card {
  margin-bottom: 16px;
}
.preview-head {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}
.preview-path {
  font-weight: 600;
  font-family: 'SFMono-Regular', Consolas, Menlo, monospace;
  font-size: 13.5px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.preview-actions {
  margin-left: auto;
  display: flex;
  gap: 8px;
}
.blob-body {
  max-height: 70vh;
  overflow: auto;
}
.line-file {
  font-family: 'SFMono-Regular', Consolas, Menlo, monospace;
  font-size: 12.5px;
  line-height: 1.7;
}
.line-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 10px;
}
.line-row:hover {
  background: #f5f7fa;
}
.line-row.has-discussion {
  background: #fdf6ec;
}
.line-num {
  color: #c0c4cc;
  min-width: 34px;
  text-align: right;
  user-select: none;
}
.line-text {
  white-space: pre;
  flex: 1;
  overflow-x: auto;
}
.line-badge {
  flex-shrink: 0;
}
.line-marker {
  width: 22px;
  height: 22px;
  padding: 0;
}
.marker-pop {
  max-height: 200px;
  overflow: auto;
}
.marker-item {
  padding: 6px 4px;
  cursor: pointer;
  border-radius: 4px;
}
.marker-item:hover {
  background: #f5f7fa;
}
.marker-title {
  font-weight: 500;
  font-size: 13px;
}
.marker-meta {
  color: #909399;
  font-size: 12px;
}
</style>
