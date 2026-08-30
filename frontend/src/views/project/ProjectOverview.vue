<template>
  <div class="overview" v-loading="loading">
    <el-card>
      <template #header>项目动态</template>
      <div class="filter">
        <el-radio-group v-model="typeFilter" @change="reload">
          <el-radio-button value="all">全部</el-radio-button>
          <el-radio-button value="commit">提交</el-radio-button>
          <el-radio-button value="member">成员</el-radio-button>
          <el-radio-button value="project">项目</el-radio-button>
        </el-radio-group>
      </div>
      <el-timeline v-if="events.length">
        <el-timeline-item
          v-for="ev in events"
          :key="ev.id"
          :timestamp="formatTime(ev.created_at)"
          :type="typeColor(ev.event_type)"
        >
          <div class="event-title">
            <router-link
              v-if="ev.commit_sha && ev.event_type === 'commit'"
              :to="`/projects/${slug}/commits/${ev.commit_sha}`"
              class="commit-link"
            >
              {{ ev.title }}
              <el-tag size="small" type="success" effect="plain">{{ ev.commit_sha?.slice(0, 8) }}</el-tag>
            </router-link>
            <template v-else>{{ ev.title }}</template>
          </div>
          <div class="event-actor" v-if="ev.actor">{{ ev.actor.full_name }} · {{ typeLabel(ev.event_type) }}</div>
        </el-timeline-item>
      </el-timeline>
      <el-empty v-else description="暂无动态，快去推送代码吧" />
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
import { projectApi, type ActivityItem } from '@/api'

const route = useRoute()
const slug = route.params.slug as string
const loading = ref(false)
const events = ref<ActivityItem[]>([])
const typeFilter = ref('all')
const page = ref(1)
const perPage = 30
const total = ref(0)

async function load() {
  loading.value = true
  try {
    const data = await projectApi.activities(slug, {
      type: typeFilter.value,
      page: page.value,
      per_page: perPage,
    }) as { items: ActivityItem[]; total: number }
    events.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function reload() {
  page.value = 1
  load()
}

function onPageChange(p: number) {
  page.value = p
  load()
}

function typeLabel(t: string) {
  const map: Record<string, string> = {
    commit: '代码提交',
    member: '成员变动',
    project: '项目事件',
    issue: 'Issue',
    post: '讨论帖',
    wiki: 'Wiki',
  }
  return map[t] || t
}

function typeColor(t: string) {
  const map: Record<string, 'primary' | 'success' | 'warning' | 'info'> = {
    commit: 'success',
    member: 'warning',
    project: 'primary',
  }
  return map[t] || 'info'
}

function formatTime(t: string) {
  return t ? new Date(t).toLocaleString('zh-CN') : '-'
}

onMounted(load)
</script>

<style scoped>
.filter {
  margin-bottom: 16px;
}
.event-title {
  font-weight: 500;
}
.commit-link {
  color: inherit;
  text-decoration: none;
}
.event-actor {
  color: #909399;
  font-size: 12px;
  margin-top: 4px;
}
.pagination {
  margin-top: 16px;
  justify-content: flex-end;
}
</style>
