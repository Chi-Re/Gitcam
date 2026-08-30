<template>
  <el-container class="layout">
    <el-aside width="220px" class="aside">
      <div class="logo" @click="$router.push('/projects')">
        <span class="logo-icon">&#128187;</span>
        gitcam
      </div>
      <el-menu :default-active="$route.path" router class="menu">
        <el-menu-item index="/projects">
          <el-icon><Folder /></el-icon>
          <span>项目</span>
        </el-menu-item>
        <el-menu-item index="/community">
          <el-icon><ChatDotRound /></el-icon>
          <span>社区论坛</span>
        </el-menu-item>
        <el-menu-item index="/projects/create">
          <el-icon><Plus /></el-icon>
          <span>创建项目</span>
        </el-menu-item>
        <el-menu-item index="/notifications">
          <el-icon><Bell /></el-icon>
          <span>通知中心</span>
        </el-menu-item>
        <el-menu-item index="/reply-history">
          <el-icon><ChatLineRound /></el-icon>
          <span>我的回复</span>
        </el-menu-item>
        <el-menu-item index="/profile">
          <el-icon><User /></el-icon>
          <span>个人资料</span>
        </el-menu-item>
        <el-menu-item v-if="auth.isAdmin" index="/admin/users">
          <el-icon><Setting /></el-icon>
          <span>管理后台</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-title">{{ $route.meta.title || 'gitcam' }}</div>
        <el-dropdown v-if="auth.user" @command="onCommand">
          <span class="user-info">
            <el-avatar :size="30" :src="auth.user.avatar_url || undefined">
              {{ auth.user.full_name?.[0] || '?' }}
            </el-avatar>
            <span class="name">{{ auth.user.full_name }}</span>
            <el-tag size="small" :type="roleTagType" class="role-tag">{{ roleLabel }}</el-tag>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile">个人资料</el-dropdown-item>
              <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>

      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

const roleLabel = computed(() => {
  const map: Record<string, string> = { student: '学生', teacher: '教师', admin: '管理员' }
  return map[auth.user?.role || ''] || ''
})
const roleTagType = computed(() => {
  const map: Record<string, 'primary' | 'success' | 'danger'> = {
    student: 'primary',
    teacher: 'success',
    admin: 'danger',
  }
  return map[auth.user?.role || ''] || 'info'
})

onMounted(() => {
  if (!auth.user) auth.fetchMe()
})

function onCommand(cmd: string) {
  if (cmd === 'logout') {
    auth.logout()
    router.push('/login')
  } else if (cmd === 'profile') {
    router.push('/profile')
  }
}
</script>

<style scoped>
.layout {
  min-height: 100vh;
}
.aside {
  background: #1f2d3d;
  color: #fff;
}
.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  font-weight: 700;
  color: #fff;
  cursor: pointer;
  letter-spacing: 1px;
}
.logo-icon {
  margin-right: 6px;
}
.menu {
  border-right: none;
  background: transparent;
  --el-menu-text-color: #c0c4cc;
  --el-menu-hover-bg-color: #263445;
  --el-menu-active-color: #409eff;
}
.header {
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 60px;
}
.header-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}
.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  outline: none;
}
.main {
  padding: 20px;
  max-width: 1200px;
  width: 100%;
  margin: 0 auto;
}
</style>
