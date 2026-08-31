<template>
  <el-card>
    <template #header>
      <div class="header-row">
        <span>成员管理</span>
        <el-button
          v-if="canManage"
          type="primary"
          size="small"
          @click="showAdd = true"
        >
          <el-icon><Plus /></el-icon>添加成员
        </el-button>
      </div>
    </template>

    <div class="table-wrap">
    <el-table :data="members">
      <el-table-column label="成员" min-width="200">
        <template #default="{ row }">
          <div class="member-cell">
            <el-avatar :size="28" :src="row.avatar_url || undefined">{{ row.full_name?.[0] }}</el-avatar>
            <div>
              <div>{{ row.full_name }}</div>
              <div class="username">@{{ row.username }}</div>
            </div>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="项目角色" width="180">
        <template #default="{ row }">
          <el-tag v-if="row.role === 'owner'" type="danger" size="small">Owner</el-tag>
          <el-tag v-else-if="row.role === 'developer'" type="primary" size="small">Developer</el-tag>
          <el-tag v-else type="info" size="small">Viewer</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="加入时间" width="170">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="220">
        <template #default="{ row }">
          <template v-if="canManage && row.role !== 'owner'">
            <el-select
              :model-value="row.role"
              size="small"
              style="width: 110px; margin-right: 8px"
              @change="(role: string) => changeRole(row, role)"
            >
              <el-option label="Developer" value="developer" />
              <el-option label="Viewer" value="viewer" />
            </el-select>
            <el-button size="small" type="danger" plain @click="removeMember(row)">移除</el-button>
          </template>
        </template>
      </el-table-column>
    </el-table>
    </div>

    <el-dialog v-model="showAdd" title="添加成员" width="420px">
      <el-form label-width="90px">
        <el-form-item label="账号">
          <el-input v-model="addForm.account" placeholder="用户名 / 邮箱 / 学号" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="addForm.role" style="width: 100%">
            <el-option label="Developer（可读写代码）" value="developer" />
            <el-option label="Viewer（只读）" value="viewer" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAdd = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="addMember">添加</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { projectApi, type Project, type ProjectMember } from '@/api'

const route = useRoute()
const slug = route.params.slug as string
const members = ref<ProjectMember[]>([])
const showAdd = ref(false)
const submitting = ref(false)
const myRole = ref<string | null>(null)

const addForm = reactive({ account: '', role: 'developer' })
const canManage = computed(() => myRole.value === 'owner')

async function load() {
  const [memberData, projectData] = await Promise.all([
    projectApi.members(slug),
    projectApi.get(slug),
  ])
  members.value = (memberData as { members: ProjectMember[] }).members
  myRole.value = (projectData as { project: Project }).project.my_role ?? null
}

async function addMember() {
  if (!addForm.account) {
    ElMessage.warning('请输入账号')
    return
  }
  submitting.value = true
  try {
    const data = await projectApi.addMember(slug, addForm) as { members: ProjectMember[] }
    members.value = data.members
    showAdd.value = false
    addForm.account = ''
    ElMessage.success('已添加成员')
  } finally {
    submitting.value = false
  }
}

async function changeRole(row: ProjectMember, role: string) {
  const data = await projectApi.updateMember(slug, row.user_id, { role }) as { members: ProjectMember[] }
  members.value = data.members
  ElMessage.success('角色已更新')
}

async function removeMember(row: ProjectMember) {
  await ElMessageBox.confirm(`确定移除成员 ${row.full_name} 吗？`, '提示', { type: 'warning' })
  const data = await projectApi.removeMember(slug, row.user_id) as { members: ProjectMember[] }
  members.value = data.members
  ElMessage.success('已移除')
}

function formatTime(t: string) {
  return t ? new Date(t).toLocaleString('zh-CN') : '-'
}

onMounted(load)
</script>

<style scoped>
.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.member-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}
.username {
  font-size: 12px;
  color: #909399;
}
</style>
