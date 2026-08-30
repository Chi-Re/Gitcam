<template>
  <div class="auth-page">
    <el-card class="auth-card">
      <div class="auth-logo">
        <span class="logo-icon">&#128187;</span>
        <h2>gitcam</h2>
        <p>校园代码托管分享交流平台</p>
      </div>
      <el-form :model="form" @keyup.enter="onSubmit">
        <el-form-item>
          <el-input v-model="form.account" placeholder="用户名 / 邮箱 / 学号" size="large">
            <template #prefix><el-icon><User /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            size="large"
            show-password
          >
            <template #prefix><el-icon><Lock /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="form.remember">记住登录状态</el-checkbox>
        </el-form-item>
        <el-button
          type="primary"
          size="large"
          class="submit-btn"
          :loading="loading"
          @click="onSubmit"
        >
          登 录
        </el-button>
      </el-form>
      <div class="auth-footer">
        还没有账号？
        <router-link to="/register" class="link">立即注册</router-link>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const loading = ref(false)
const form = reactive({ account: '', password: '', remember: false })

async function onSubmit() {
  if (!form.account || !form.password) {
    ElMessage.warning('请输入账号和密码')
    return
  }
  loading.value = true
  try {
    await auth.login(form.account, form.password)
    ElMessage.success('登录成功')
    router.push((route.query.redirect as string) || '/projects')
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
}
.auth-card {
  width: 380px;
  padding: 12px 8px;
}
.auth-logo {
  text-align: center;
  margin-bottom: 20px;
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
