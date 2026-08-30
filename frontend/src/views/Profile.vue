<template>
  <el-card v-if="auth.user" style="max-width: 640px">
    <template #header>个人资料</template>
    <div class="profile-row">
      <el-avatar :size="64" :src="form.avatar_url || undefined" class="avatar">
        {{ auth.user.full_name?.[0] }}
      </el-avatar>
      <div>
        <div class="name">{{ form.full_name }}</div>
        <div class="username">@{{ auth.user.username }} · {{ roleLabel }}</div>
      </div>
    </div>

    <el-form :model="form" label-width="100px">
      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="姓名">
            <el-input v-model="form.full_name" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="学号">
            <el-input :model-value="auth.user.student_id || ''" disabled />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="学院">
        <el-input v-model="form.college" />
      </el-form-item>
      <el-form-item label="专业班级">
        <el-input v-model="form.major_class" />
      </el-form-item>
      <el-form-item label="个人简介">
        <el-input v-model="form.bio" type="textarea" :rows="3" maxlength="500" show-word-limit />
      </el-form-item>
      <el-form-item label="头像 URL">
        <el-input v-model="form.avatar_url" placeholder="https://..." />
      </el-form-item>
      <el-form-item label="GitHub 主页">
        <el-input v-model="form.github_url" placeholder="https://github.com/..." />
      </el-form-item>
      <el-form-item label="Gitee 主页">
        <el-input v-model="form.gitee_url" placeholder="https://gitee.com/..." />
      </el-form-item>

      <el-divider content-position="left">修改密码（选填）</el-divider>
      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="原密码">
            <el-input v-model="pwd.old_password" type="password" show-password />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="新密码">
            <el-input v-model="pwd.password" type="password" show-password />
          </el-form-item>
        </el-col>
      </el-row>

      <el-form-item>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { authApi } from '@/api'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const saving = ref(false)
const form = reactive({
  full_name: '',
  college: '',
  major_class: '',
  bio: '',
  avatar_url: '',
  github_url: '',
  gitee_url: '',
})
const pwd = reactive({ old_password: '', password: '' })

const roleLabel = computed(() => {
  const map: Record<string, string> = { student: '学生', teacher: '教师', admin: '管理员' }
  return map[auth.user?.role || ''] || ''
})

onMounted(() => {
  if (auth.user) {
    form.full_name = auth.user.full_name
    form.college = auth.user.college || ''
    form.major_class = auth.user.major_class || ''
    form.bio = auth.user.bio || ''
    form.avatar_url = auth.user.avatar_url || ''
    form.github_url = auth.user.github_url || ''
    form.gitee_url = auth.user.gitee_url || ''
  }
})

async function save() {
  saving.value = true
  try {
    const data = await authApi.updateProfile({ ...form, ...pwd }) as { user: typeof auth.user }
    auth.user = data.user
    ElMessage.success('保存成功')
    pwd.old_password = ''
    pwd.password = ''
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.profile-row {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}
.name {
  font-size: 18px;
  font-weight: 600;
}
.username {
  color: #909399;
}
</style>
