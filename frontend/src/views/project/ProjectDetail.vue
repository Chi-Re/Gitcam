<template>
  <div v-loading="loading">
    <template v-if="project">
      <div class="project-head">
        <div class="title-row">
          <h2>{{ project.name }}</h2>
          <el-tag size="small" :type="project.visibility === 'public' ? 'success' : 'info'">
            {{ project.visibility === 'public' ? '公开' : '私有' }}
          </el-tag>
          <el-tag size="small" type="warning" effect="plain">{{ project.template_name }}</el-tag>
        </div>
        <p class="desc">{{ project.description || '暂无简介' }}</p>
        <div class="meta">
          <span>创建者：{{ project.owner?.full_name }}</span>
          <span>默认分支：{{ project.default_branch }}</span>
          <span>提交数：{{ project.commit_count ?? '-' }}</span>
          <span>成员：{{ project.member_count }}</span>
        </div>
        <div class="git-url">
          <span class="label">git clone 地址：</span>
          <el-input :model-value="project.git_url" readonly size="small" style="width: 340px">
            <template #append>
              <el-button @click="copyGitUrl">复制</el-button>
            </template>
          </el-input>
        </div>
      </div>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="概览" name="overview" />
        <el-tab-pane label="代码" name="repo" />
        <el-tab-pane label="提交历史" name="commits" />
        <el-tab-pane label="分支" name="branches" />
        <el-tab-pane label="Issue" name="issues" />
        <el-tab-pane label="Wiki" name="wiki" />
        <el-tab-pane label="论坛" name="posts" />
        <el-tab-pane label="成员" name="members" />
      </el-tabs>

      <router-view />
    </template>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { projectApi, type Project } from '@/api'

const route = useRoute()
const router = useRouter()
const slug = route.params.slug as string
const loading = ref(false)
const project = ref<Project | null>(null)
const activeTab = ref('overview')

const tabMap: Record<string, string> = {
  '': 'overview',
  repo: 'repo',
  commits: 'commits',
  'commits/:sha': 'commits',
  branches: 'branches',
  posts: 'posts',
  'posts/create': 'posts',
  'posts/:postId': 'posts',
  issues: 'issues',
  'issues/create': 'issues',
  'issues/:issueId': 'issues',
  wiki: 'wiki',
  members: 'members',
}

watch(
  () => route.path,
  (p) => {
    for (const [key, val] of Object.entries(tabMap)) {
      if (p.endsWith(`/${key}`) || p.endsWith(`/${key}/`)) {
        activeTab.value = val
        return
      }
    }
  },
  { immediate: true },
)

watch(activeTab, (tab) => {
  if (tab === 'overview') router.replace(`/projects/${slug}`)
  else router.push(`/projects/${slug}/${tab}`)
})

async function load() {
  loading.value = true
  try {
    project.value = (await projectApi.get(slug) as { project: Project }).project
  } finally {
    loading.value = false
  }
}

function copyGitUrl() {
  if (project.value) {
    navigator.clipboard.writeText(project.value.git_url)
    ElMessage.success('已复制 git clone 地址')
  }
}

onMounted(load)
</script>

<style scoped>
.project-head {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 16px;
}
.title-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.title-row h2 {
  margin: 0;
}
.desc {
  color: #606266;
  margin: 8px 0;
}
.meta {
  display: flex;
  gap: 20px;
  color: #909399;
  font-size: 13px;
}
.git-url {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}
.label {
  color: #606266;
  white-space: nowrap;
}
</style>
