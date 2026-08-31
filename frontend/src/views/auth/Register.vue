<template>
  <div class="auth-page">
    <el-card class="auth-card">
      <div class="auth-logo">
        <span class="logo-icon">&#128187;</span>
        <h2>注册 gitcam</h2>
        <p>加入校园代码托管分享交流平台</p>
      </div>
      <el-form :model="form" label-position="top">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="姓名" required>
              <el-input v-model="form.full_name" placeholder="真实姓名" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="角色" required>
              <el-select v-model="form.role" style="width: 100%">
                <el-option label="学生" value="student" />
                <el-option label="教师" value="teacher" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="用户名" required>
              <el-input v-model="form.username" placeholder="登录用户名" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="学号 / 工号">
              <el-input v-model="form.student_id" placeholder="选填" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="邮箱" required>
          <el-input v-model="form.email" placeholder="用于登录与通知" />
        </el-form-item>
        <el-form-item label="密码" required>
          <el-input v-model="form.password" type="password" placeholder="至少 6 位" show-password />
        </el-form-item>
        <el-form-item label="学院">
          <el-input v-model="form.college" placeholder="选填" />
        </el-form-item>
        <el-form-item label="专业班级">
          <el-input v-model="form.major_class" placeholder="如：计科2401" />
        </el-form-item>
        <el-button
          type="primary"
          size="large"
          class="submit-btn"
          :loading="loading"
          @click="onSubmit"
        >
          注 册
        </el-button>
      </el-form>
      <div class="auth-footer">
        已有账号？
        <router-link to="/login" class="link">去登录</router-link>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { authApi, type User } from '@/api'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const loading = ref(false)
const form = reactive({
  full_name: '',
  role: 'student',
  username: '',
  student_id: '',
  email: '',
  password: '',
  college: '',
  major_class: '',
})

async function onSubmit() {
  if (!form.full_name || !form.username || !form.email || !form.password) {
    ElMessage.warning('请填写必填项')
    return
  }
  loading.value = true
  try {
    const data = await authApi.register({ ...form }) as { token: string; user: User }
    auth.token = data.token
    auth.user = data.user
    localStorage.setItem('gitcam_token', data.token)
    ElMessage.success('注册成功，欢迎加入 gitcam')
    router.push('/home')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1f2d3d 0%, #2c3e50 100%);
  padding: 30px 0;
}
.auth-card {
  width: 460px;
  padding: 12px 8px;
}
.auth-logo {
  text-align: center;
  margin-bottom: 16px;
}
.auth-logo h2 {
  margin: 8px 0 4px;
  color: #1f2d3d;
}
.auth-logo p {
  margin: 0;
  color: #909399;
  font-size: 13px;
}
.submit-btn {
  width: 100%;
}
.auth-footer {
  text-align: center;
  margin-top: 16px;
  color: #606266;
  font-size: 14px;
}
.link {
  color: #409eff;
  text-decoration: none;
}
</style>
