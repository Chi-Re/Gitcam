<template>
  <div class="file-tree">
    <div class="tree-toolbar">
      <el-select
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
      <div class="tree-actions">
        <el-tooltip content="展开全部" placement="top">
          <el-button size="small" text @click="expandAll">
            <el-icon><Expand /></el-icon>
          </el-button>
        </el-tooltip>
        <el-tooltip content="折叠全部" placement="top">
          <el-button size="small" text @click="collapseAll">
            <el-icon><Fold /></el-icon>
          </el-button>
        </el-tooltip>
      </div>
    </div>

    <!-- Go to file 搜索 -->
    <div class="tree-search">
      <el-input
        v-model="searchQuery"
        size="small"
        placeholder="搜索文件…"
        clearable
        @input="onSearchInput"
        @keyup.enter="onSearchEnter"
      >
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <div v-if="searchActive" class="search-hint">
        {{ searchResults.length }} 个匹配<template v-if="searchTruncated">（部分）</template>
      </div>
    </div>

    <!-- 搜索模式：扁平结果列表 -->
    <div v-if="searchActive" class="tree-body" v-loading="searchLoading">
      <div
        v-for="r in searchResults"
        :key="r.path"
        class="tree-row search-row"
        :class="{ 'row-active': r.path === currentPath }"
        @click="onSearchResultClick(r)"
      >
        <span class="search-icon">
          <FileTypeIcon :name="r.name" :type="r.isDir ? 'tree' : 'file'" :size="15" />
        </span>
        <span class="search-path">{{ r.path }}</span>
      </div>
      <el-empty v-if="!searchLoading && !searchResults.length" description="无匹配文件" :image-size="40" />
    </div>

    <!-- 树模式：懒加载目录树 -->
    <template v-else>
      <div class="tree-body" v-loading="loadingRoot">
        <el-empty
          v-if="!loadingRoot && !rootChildren.length"
          description="仓库为空"
          :image-size="40"
        />
        <div v-for="entry in rootChildren" :key="entry.path" class="tree-node" :class="{ 'node-open': isExpanded(entry.path) }">
          <TreeNode
            :entry="entry"
            :depth="0"
            :expanded="isExpanded(entry.path)"
            :active="entry.path === currentPath"
            :loaded="isLoaded(entry.path)"
            :loading="isLoading(entry.path)"
            :active-path="currentPath"
            @toggle="onToggle"
            @file-click="onFileClick"
          />
        </div>
      </div>

      <!-- 树底统计 -->
      <div class="tree-footer">
        <span v-if="statsLoaded">{{ statsDirs }} 个目录 · {{ statsFiles }} 个文件</span>
        <span v-else-if="statsLoading">统计中…</span>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { defineComponent, h, onMounted, ref, watch } from 'vue'
import { repoApi, type TreeEntry } from '@/api'
import FileTypeIcon from '@/components/FileTypeIcon.vue'

const props = defineProps<{
  slug: string
  branch: string
  branches: string[]
  /** 当前浏览路径（用于自动展开与高亮） */
  currentPath: string
}>()

const emit = defineEmits<{
  (e: 'branch-change', branch: string): void
  (e: 'file-click', entry: TreeEntry): void
}>()

const rootChildren = ref<TreeEntry[]>([])
const loadingRoot = ref(false)
// 路径 -> 子项缓存（懒加载）
const childrenCache = ref(new Map<string, TreeEntry[]>())
const expanded = ref(new Set<string>())
const loadingPaths = ref(new Set<string>())
// 搜索 + 统计
const searchQuery = ref('')
const searchActive = ref(false)
const searchLoading = ref(false)
const searchResults = ref<{ path: string; name: string; isDir: boolean }[]>([])
const searchTruncated = ref(false)
let searchPaths: string[] = []
let searchDirs = new Set<string>()
let indexLoaded = false
let indexLoading: Promise<void> | null = null
const statsLoaded = ref(false)
const statsLoading = ref(false)
const statsDirs = ref(0)
const statsFiles = ref(0)

async function loadIndex(): Promise<void> {
  if (indexLoaded) return
  if (indexLoading) return indexLoading
  indexLoading = (async () => {
    try {
      const data = await repoApi.treeIndex(props.slug, {
        branch: props.branch || undefined,
      }) as { paths: string[]; dirCount: number; fileCount: number; truncated: boolean }
      searchPaths = data.paths
      searchTruncated.value = data.truncated
      // 从文件路径推导目录集合（含空目录兜底：根目录为空时）
      searchDirs = new Set()
      for (const p of data.paths) {
        const seg = p.split('/')
        for (let i = 1; i < seg.length; i++) searchDirs.add(seg.slice(0, i).join('/'))
      }
      statsDirs.value = data.dirCount
      statsFiles.value = data.fileCount
      statsLoaded.value = true
      indexLoaded = true
    } finally {
      indexLoading = null
    }
  })()
  return indexLoading
}

function onSearchInput() {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) {
    searchActive.value = false
    searchResults.value = []
    return
  }
  searchActive.value = true
  searchLoading.value = true
  loadIndex().finally(() => {
    const results: { path: string; name: string; isDir: boolean }[] = []
    // 匹配文件路径或其父目录路径（Go to file 语义：匹配文件名/路径片段）
    for (const p of searchPaths) {
      if (p.toLowerCase().includes(q)) {
        results.push({ path: p, name: p.split('/').pop() || p, isDir: false })
      }
    }
    for (const d of searchDirs) {
      if (d.toLowerCase().includes(q)) {
        results.push({ path: d, name: d.split('/').pop() || d, isDir: true })
      }
    }
    results.sort((a, b) => a.path.localeCompare(b.path))
    searchResults.value = results.slice(0, 200)
    searchLoading.value = false
  })
}

async function onSearchResultClick(r: { path: string; name: string; isDir: boolean }) {
  if (r.isDir) {
    // 目录：加载子项、展开祖先、保持搜索视图
    await loadChildren(r.path)
    expanded.value.add(r.path)
    expanded.value = new Set(expanded.value)
  } else {
    emit('file-click', { name: r.name, path: r.path, type: 'blob', size: null } as TreeEntry)
  }
}

async function onSearchEnter() {
  if (!searchResults.value.length) return
  await onSearchResultClick(searchResults.value[0])
}

async function loadStats() {
  statsLoading.value = true
  try {
    await loadIndex()
  } finally {
    statsLoading.value = false
  }
}

function isExpanded(path: string) {
  return expanded.value.has(path)
}

function isLoaded(path: string) {
  return childrenCache.value.has(path)
}

function isLoading(path: string) {
  return loadingPaths.value.has(path)
}

async function loadChildren(path: string): Promise<TreeEntry[]> {
  const cached = childrenCache.value.get(path)
  if (cached) return cached
  loadingPaths.value.add(path)
  try {
    const data = await repoApi.tree(props.slug, {
      path: path || undefined,
      branch: props.branch || undefined,
    }) as { entries: TreeEntry[] }
    childrenCache.value.set(path, data.entries)
    return data.entries
  } finally {
    loadingPaths.value.delete(path)
  }
}

async function onToggle(entry: TreeEntry) {
  const path = entry.path
  if (expanded.value.has(path)) {
    expanded.value.delete(path)
    expanded.value = new Set(expanded.value)
    return
  }
  await loadChildren(path)
  expanded.value.add(path)
  expanded.value = new Set(expanded.value)
}

function onFileClick(entry: TreeEntry) {
  emit('file-click', entry)
}

function onBranchChange(b: string) {
  // 分支切换：清空索引与统计缓存
  indexLoaded = false
  searchPaths = []
  searchDirs = new Set()
  statsLoaded.value = false
  searchActive.value = false
  searchQuery.value = ''
  emit('branch-change', b)
}

/** 展开全部：先按广度顺序加载整棵树（限制深度避免大仓库卡死） */
async function expandAll() {
  const root = await loadChildren('')
  const queue = [...root.filter((e) => e.type === 'tree')]
  const newExpanded = new Set(expanded.value)
  let guard = 0
  while (queue.length && guard < 2000) {
    const node = queue.shift()!
    guard++
    newExpanded.add(node.path)
    const children = await loadChildren(node.path)
    queue.push(...children.filter((c) => c.type === 'tree'))
  }
  expanded.value = newExpanded
}

function collapseAll() {
  expanded.value = new Set()
}

/** 当前路径变化：自动加载并展开祖先目录，高亮当前项 */
async function revealPath(path: string) {
  if (!path) return
  const parts = path.split('/')
  const dirs: string[] = []
  for (let i = 1; i < parts.length; i++) {
    dirs.push(parts.slice(0, i).join('/'))
  }
  const newExpanded = new Set(expanded.value)
  for (const dir of dirs) {
    await loadChildren(dir)
    newExpanded.add(dir)
  }
  expanded.value = newExpanded
  // 确保父目录已加载（高亮祖先链）
  for (let i = dirs.length - 1; i >= 0; i--) {
    await loadChildren(dirs[i])
  }
}

onMounted(async () => {
  loadingRoot.value = true
  try {
    rootChildren.value = await loadChildren('')
  } finally {
    loadingRoot.value = false
  }
  if (props.currentPath) revealPath(props.currentPath)
  loadStats()
})

// 父级路径变化（面包屑/列表进入目录）→ 自动展开祖先并高亮
watch(
  () => props.currentPath,
  (path) => {
    if (path) revealPath(path)
  },
)

// 递归子节点组件
// 递归子节点组件（自引用，显式 any 类型）
const TreeNode: any = defineComponent({
  name: 'TreeItem',
  props: {
    entry: { type: Object, required: true },
    depth: { type: Number, required: true },
    expanded: Boolean,
    active: Boolean,
    loaded: Boolean,
    loading: Boolean,
    activePath: { type: String, default: '' },
  },
  emits: ['toggle', 'file-click'],
  setup(props, ctx) {
    return () => {
      const entry = props.entry as TreeEntry
      const isDir = entry.type === 'tree'
      return h('div', { class: 'tree-node' }, [
        h(
          'div',
          {
            class: ['tree-row', { 'row-active': props.active, 'row-dir': isDir }],
            style: { paddingLeft: 8 + props.depth * 16 + 'px' },
            onClick: () => {
              if (isDir) ctx.emit('toggle', entry)
              else ctx.emit('file-click', entry)
            },
          },
          [
            h('span', { class: 'tree-arrow' }, [
              isDir
                ? h(
                    'svg',
                    {
                      viewBox: '0 0 24 24',
                      width: '12',
                      height: '12',
                      class: ['arrow-icon', { 'arrow-open': props.expanded, 'arrow-loading': props.loading }],
                    },
                    h('path', {
                      d: 'M9 6l6 6-6 6',
                      fill: 'none',
                      stroke: 'currentColor',
                      'stroke-width': '2.4',
                      'stroke-linecap': 'round',
                      'stroke-linejoin': 'round',
                    }),
                  )
                : h('span', { class: 'arrow-placeholder' }),
            ]),
            h(
              FileTypeIcon,
              { name: entry.name, type: isDir ? (props.expanded ? 'tree-open' : 'tree') : 'file', size: 15 },
            ),
            h('span', { class: ['tree-name', { 'tree-name-dir': isDir }] }, entry.name),
            h('span', { class: 'tree-loading' }, props.loading ? '…' : ''),
          ],
        ),
        // 已展开目录的子节点
        props.expanded
          ? h(
              'div',
              { class: 'tree-children' },
              ((props.loaded ? (childrenCache.value.get(entry.path) || []) : []) as TreeEntry[]).map(
                (child) =>
                  h(TreeNode, {
                    key: child.path,
                    entry: child,
                    depth: props.depth + 1,
                    expanded: expanded.value.has(child.path),
                    active: child.path === props.activePath,
                    loaded: childrenCache.value.has(child.path),
                    loading: loadingPaths.value.has(child.path),
                    activePath: props.activePath,
                    onToggle: (e: TreeEntry) => onToggle(e),
                    'onFile-click': (e: TreeEntry) => onFileClick(e),
                  }),
              ),
            )
          : null,
      ])
    }
  },
})
</script>

<style scoped>
.file-tree {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}
.tree-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-bottom: 1px solid #f0f2f5;
}
.tree-actions {
  display: flex;
  gap: 2px;
}
.tree-search {
  padding: 8px 12px 4px;
}
.search-hint {
  color: #909399;
  font-size: 11px;
  margin-top: 4px;
}
.search-row {
  padding: 5px 12px;
}
.search-icon {
  display: inline-flex;
  flex-shrink: 0;
}
.search-path {
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 12.5px;
}
.tree-footer {
  border-top: 1px solid #f0f2f5;
  padding: 6px 12px;
  color: #909399;
  font-size: 12px;
  flex-shrink: 0;
}
.tree-body {
  flex: 1;
  overflow: auto;
  padding: 6px 0;
}
.tree-node {
  user-select: none;
}
.tree-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 8px;
  cursor: pointer;
  border-radius: 4px;
  font-size: 13.5px;
  white-space: nowrap;
}
.tree-row:hover {
  background: #f5f7fa;
}
.row-active {
  background: #ecf5ff;
  color: #409eff;
  font-weight: 500;
}
.tree-arrow {
  width: 12px;
  display: inline-flex;
  justify-content: center;
  flex-shrink: 0;
  color: #909399;
}
.arrow-icon {
  transition: transform 0.15s;
}
.arrow-open {
  transform: rotate(90deg);
}
.arrow-loading {
  animation: spin 0.8s linear infinite;
}
.arrow-placeholder {
  width: 12px;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
.tree-name {
  overflow: hidden;
  text-overflow: ellipsis;
}
.tree-name-dir {
  font-weight: 500;
}
.tree-loading {
  color: #c0c4cc;
}
</style>
