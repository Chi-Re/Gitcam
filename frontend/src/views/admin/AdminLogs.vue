<template>
  <el-card>
    <template #header>
      <div class="head">
        <span>日志审计</span>
        <el-radio-group v-model="kind" size="small" @change="reload">
          <el-radio-button value="login">登录日志</el-radio-button>
          <el-radio-button value="audit">操作日志</el-radio-button>
        </el-radio-group>
      </div>
    </template>

    <el-table v-loading="loading" :data="items">
      <template v-if="kind === 'login'">
        <el-table-column label="ID" width="70" prop="id" />
        <el-table-column label="用户" width="130" prop="user" />
        <el-table-column label="IP" width="140" prop="ip" />
        <el-table-column label="结果" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="row.success ? 'success' : 'danger'">
              {{ row.success ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="User-Agent" min-width="200" prop="user_agent" show-overflow-tooltip />
      </template>
      <template v-else>
        <el-table-column label="ID" width="70" prop="id" />
        <el-table-column label="操作者" width="110" prop="actor" />
        <el-table-column label="操作" width="150" prop="action" />
        <el-table-column label="目标" width="130">
          <template #default="{ row }">{{ row.target_type }} #{{ row.target_id }}</template>
        </el-table-column>
        <el-table-column label="详情" min-width="200" prop="detail" show-overflow-tooltip />
        <el-table-column label="IP" width="140" prop="ip" />
        <el-table-column label="时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
      </template>
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
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { adminApi } from '@/api'

interface LogItem {
  id: number
  user?: string | null
  actor?: string | null
  action?: string
  target_type?: string | null
  target_id?: string | null
  detail?: string | null
  ip?: string | null
  success?: boolean
  user_agent?: string | null
  created_at: string
}

const kind = ref('login')
const items = ref<LogItem[]>([])
const loading = ref(false)
const page = ref(1)
const perPage = 20
const total = ref(0)

async function load() {
  loading.value = true
  try {
    const data = await adminApi.logs({
      type: kind.value,
      page: page.value,
      per_page: perPage,
    }) as { items: LogItem[]; total: number }
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

function formatTime(t: string) {
  return t ? new Date(t).toLocaleString('zh-CN') : '-'
}

onMounted(load)
</script>

<style scoped>
.head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.pagination {
  margin-top: 16px;
  justify-content: flex-end;
}
</style>
