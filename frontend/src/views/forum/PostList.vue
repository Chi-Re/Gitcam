<template>
  <div>
    <div class="toolbar">
      <el-radio-group v-model="category" @change="reload">
        <el-radio-button value="all">全部</el-radio-button>
        <el-radio-button value="question">问题求助</el-radio-button>
        <el-radio-button value="share">经验分享</el-radio-button>
        <el-radio-button value="review">代码评审</el-radio-button>
        <el-radio-button value="announce">公告</el-radio-button>
        <el-radio-button value="other">其他</el-radio-button>
      </el-radio-group>
      <el-input
        v-model="q"
        placeholder="搜索帖子"
        clearable
        style="width: 240px"
        @keyup.enter="reload"
        @clear="reload"
      >
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-select v-model="status" style="width: 110px" @change="reload">
        <el-option label="全部状态" value="all" />
        <el-option label="待解决" value="open" />
        <el-option label="已解决" value="solved" />
        <el-option label="已关闭" value="closed" />
      </el-select>
      <el-select v-model="sort" style="width: 120px" @change="reload">
        <el-option label="最新发布" value="latest" />
        <el-option label="最多赞同" value="votes" />
      </el-select>
      <el-button type="primary" @click="goCreate">
        <el-icon><Plus /></el-icon>发帖
      </el-button>
    </div>

    <el-card v-loading="loading">
      <el-empty v-if="!items.length && !loading" description="暂无帖子，来发第一帖吧" />
      <div v-for="p in items" :key="p.id" class="post-item" @click="$router.push(`/projects/${slug}/posts/${p.id}`)">
        <div class="stats">
          <div class="stat">
            <div class="num">{{ p.vote_count }}</div>
            <div class="label">赞同</div>
          </div>
          <div class="stat" :class="{ answered: p.status === 'solved' }">
            <div class="num">{{ p.reply_count }}</div>
            <div class="label">回答</div>
          </div>
        </div>
        <div class="main">
          <div class="title-row">
            <span class="title">{{ p.title }}</span>
            <el-tag size="small" type="primary" effect="plain">{{ p.category_label }}</el-tag>
            <el-tag v-if="p.status === 'solved'" size="small" type="success">已解决</el-tag>
            <el-tag v-else-if="p.status === 'closed'" size="small" type="info">已关闭</el-tag>
            <el-tag v-else size="small" type="warning" effect="plain">待解决</el-tag>
          </div>
          <div class="meta">
            {{ p.author?.full_name }} · {{ formatTime(p.created_at) }}
          </div>
        </div>
      </div>
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
import { useRoute, useRouter } from 'vue-router'
import { postsApi, type Post } from '@/api'

const route = useRoute()
const router = useRouter()
const slug = route.params.slug as string
const items = ref<Post[]>([])
const loading = ref(false)
const category = ref('all')
const status = ref('all')
const sort = ref('latest')
const q = ref('')
const page = ref(1)
const perPage = 20
const total = ref(0)

async function load() {
  loading.value = true
  try {
    const data = await postsApi.list(slug, {
      category: category.value,
      status: status.value,
      sort: sort.value,
      q: q.value || undefined,
      page: page.value,
      per_page: perPage,
    }) as { items: Post[]; total: number }
    items.value = data.items
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

function goCreate() {
  router.push(`/projects/${slug}/posts/create`)
}

function formatTime(t: string) {
  return t ? new Date(t).toLocaleString('zh-CN') : '-'
}

onMounted(load)
</script>

<style scoped>
.toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
  flex-wrap: wrap;
  align-items: center;
}
.post-item {
  display: flex;
  gap: 16px;
  padding: 14px 8px;
  border-bottom: 1px solid #f0f2f5;
  cursor: pointer;
}
.post-item:hover {
  background: #fafbfc;
}
.stats {
  display: flex;
  gap: 18px;
  min-width: 100px;
}
.stat {
  text-align: center;
}
.stat .num {
  font-weight: 600;
  font-size: 16px;
}
.stat .label {
  color: #909399;
  font-size: 12px;
}
.stat.answered .num {
  color: #67c23a;
}
.main {
  flex: 1;
}
.title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.title {
  font-weight: 600;
  font-size: 15px;
}
.meta {
  color: #909399;
  font-size: 12px;
  margin-top: 6px;
}
.pagination {
  margin-top: 16px;
  justify-content: flex-end;
}
</style>
