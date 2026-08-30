<template>
  <el-card>
    <template #header>
      <div class="head">
        <span>用户管理</span>
        <div class="filters">
          <el-input v-model="q" placeholder="用户名/邮箱/姓名/学号" clearable style="width: 220px" @keyup.enter="reload" @clear="reload" />
          <el-select v-model="role" clearable placeholder="角色" style="width: 110px" @change="reload">
            <el-option label="学生" value="student" />
            <el-option label="教师" value="teacher" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </div>
      </div>
    </template>
    <el-table v-loading="loading" :data="items">
      <el-table-column label="ID" width="60" prop="id" />
      <el-table-column label="用户名" width="130" prop="username" />
      <el-table-column label="姓名" width="120" prop="full_name" />
      <el-table-column label="邮箱" min-width="180" prop="email" />
      <el-table-column label="学号" width="110" prop="student_id" />
      <el-table-column label="角色" width="130">
        <template #default="{ row }">
          <el-select
            :model-value="row.role"
            size="small"
            :disabled="row.id === auth.user?.id"
            style="width: 100px"
            @change="(r: string) => changeRole(row, r)"
          >
            <el-option label="学生" value="student" />
            <el-option label="教师" value="teacher" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
            {{ row.is_active ? '正常' : '已封禁' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="注册时间" width="160">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="110">
        <template #default="{ row }">
          <el-button
            v-if="row.id !== auth.user?.id"
            size="small"
            :type="row.is_active ? 'danger' : 'success'"
            plain
            @click="toggleActive(row)"
          >
            {{ row.is_active ? '封禁' : '解封' }}
          </el-button>
        </template>
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
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { adminApi, type User } from '@/api'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const items = ref<User[]>([])
const loading = ref(false)
const q = ref('')
const role = ref('')
const page = ref(1)
const perPage = 20
const total = ref(0)

async function load() {
  loading.value = true
  try {
    const data = await adminApi.users({
      q: q.value || undefined,
      role: role.value || undefined,
      page: page.value,
      per_page: perPage,
    }) as { items: User[]; total: number }
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

async function changeRole(row: User, r: string) {
  if (r === row.role) return
  await ElMessageBox.confirm(`将 ${row.username} 的角色改为「${r}」？`, '变更角色', { type: 'warning' })
  await adminApi.updateUser(row.id, { role: r })
  ElMessage.success('角色已更新')
  load()
}

async function toggleActive(row: User) {
  const action = row.is_active ? '封禁' : '解封'
  await ElMessageBox.confirm(`确定${action}用户 ${row.full_name}（${row.username}）？`, action, {
    type: 'warning',
  })
  await adminApi.updateUser(row.id, { is_active: !row.is_active })
  ElMessage.success(`已${action}`)
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
.filters {
  display: flex;
  gap: 8px;
}
.pagination {
  margin-top: 16px;
  justify-content: flex-end;
}
</style>
