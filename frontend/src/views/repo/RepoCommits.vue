<template>
  <div>
    <div class="toolbar">
      <el-input
        v-model="keyword"
        placeholder="搜索提交信息"
        clearable
        style="width: 260px"
        @keyup.enter="reload"
        @clear="reload"
      >
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-select v-model="branch" placeholder="分支" clearable style="width: 150px" @change="reload">
        <el-option v-for="b in branches" :key="b.name" :label="b.name" :value="b.name" />
      </el-select>
      <el-button size="small" @click="showDiffCompare = !showDiffCompare">提交对比</el-button>
    </div>

    <el-card v-if="showDiffCompare" class="compare-card">
      <div class="compare-row">
        <span>比较</span>
        <el-input v-model="compareFrom" placeholder="from sha/分支" size="small" style="width: 180px" />
        <span>到</span>
        <el-input v-model="compareTo" placeholder="to sha/分支" size="small" style="width: 180px" />
        <el-button type="primary" size="small" @click="doCompare">比较</el-button>
      </div>
      <DiffView v-if="compareFiles" :files="compareFiles" class="compare-result" />
    </el-card>

    <el-card v-loading="loading">
      <el-timeline v-if="commits.length">
        <el-timeline-item
          v-for="c in commits"
          :key="c.sha"
          :timestamp="formatTime(c.committed_at)"
          placement="top"
          :type="c.parents.length === 0 ? 'success' : 'primary'"
        >
          <div class="commit-item" @click="$router.push(`/projects/${slug}/commits/${c.sha}`)">
            <div class="commit-msg">{{ c.message }}</div>
            <div class="commit-meta">
              <span class="author">{{ c.author_name }}</span>
              <el-tag size="small" class="sha">{{ c.short_sha }}</el-tag>
              <el-tag v-if="c.parents.length === 0" size="small" type="success">初始提交</el-tag>
            </div>
          </div>
        </el-timeline-item>
      </el-timeline>
      <el-empty v-else-if="!loading" description="暂无提交" />
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
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { repoApi, type Branch, type CommitItem, type DiffFile } from '@/api'
import DiffView from '@/components/DiffView.vue'

const route = useRoute()
const slug = route.params.slug as string
const commits = ref<CommitItem[]>([])
const branches = ref<Branch[]>([])
const branch = ref('')
const keyword = ref('')
const page = ref(1)
const perPage = 20
const total = ref(0)
const loading = ref(false)
const showDiffCompare = ref(false)
const compareFrom = ref('')
const compareTo = ref('')
const compareFiles = ref<DiffFile[] | null>(null)

async function load() {
  loading.value = true
  try {
    const data = await repoApi.commits(slug, {
      branch: branch.value || undefined,
      q: keyword.value || undefined,
      page: page.value,
      per_page: perPage,
    }) as { commits: CommitItem[]; total?: number }
    commits.value = data.commits
    if (data.total) total.value = data.total
    else total.value = data.commits.length < perPage ? (page.value - 1) * perPage + data.commits.length : page.value * perPage + 1
  } finally {
    loading.value = false
  }
}

async function reload() {
  page.value = 1
  load()
}

function onPageChange(p: number) {
  page.value = p
  load()
}

async function doCompare() {
  if (!compareFrom.value || !compareTo.value) return
  compareFiles.value = null
  const data = await repoApi.diff(slug, { from: compareFrom.value, to: compareTo.value }) as { files: DiffFile[] }
  compareFiles.value = data.files
}

function formatTime(t: string) {
  return t ? new Date(t).toLocaleString('zh-CN') : '-'
}

onMounted(async () => {
  const bd = await repoApi.branches(slug) as { branches: Branch[] }
  branches.value = bd.branches
  load()
})
</script>

<style scoped>
.toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
}
.compare-card {
  margin-bottom: 12px;
}
.compare-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}
.commit-item {
  cursor: pointer;
}
.commit-msg {
  font-weight: 500;
}
.commit-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
  color: #909399;
  font-size: 12px;
}
.author {
  font-weight: 500;
  color: #606266;
}
.pagination {
  margin-top: 16px;
  justify-content: flex-end;
}
</style>
