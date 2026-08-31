<template>
  <el-container class="layout">
    <el-aside v-if="!isMobile" :width="collapsed ? '64px' : '220px'" class="aside">
      <div class="logo" @click="$router.push('/home')">
        <span class="logo-icon">&#128187;</span>
        <span v-show="!collapsed" class="logo-text">gitcam</span>
      </div>
      <el-menu :default-active="$route.path" router class="menu" :collapse="collapsed" :collapse-transition="false">
        <el-menu-item-group title="导航">
          <el-menu-item index="/home">
            <el-icon><HomeFilled /></el-icon>
            <template #title>首页</template>
          </el-menu-item>
          <el-menu-item index="/community">
            <el-icon><ChatDotRound /></el-icon>
            <template #title>社区论坛</template>
          </el-menu-item>
        </el-menu-item-group>

        <el-menu-item-group title="项目">
          <el-menu-item index="/projects">
            <el-icon><Folder /></el-icon>
            <template #title>项目</template>
          </el-menu-item>
          <el-menu-item index="/projects/create">
            <el-icon><Plus /></el-icon>
            <template #title>创建项目</template>
          </el-menu-item>
        </el-menu-item-group>

        <el-menu-item-group title="个人">
          <el-menu-item index="/notifications">
            <el-icon><Bell /></el-icon>
            <template #title>通知中心</template>
          </el-menu-item>
          <el-menu-item index="/reply-history">
            <el-icon><ChatLineRound /></el-icon>
            <template #title>我的回复</template>
          </el-menu-item>
          <el-menu-item index="/profile">
            <el-icon><User /></el-icon>
            <template #title>个人资料</template>
          </el-menu-item>
          <el-menu-item v-if="auth.isAdmin" index="/admin/users">
            <el-icon><Setting /></el-icon>
            <template #title>管理后台</template>
          </el-menu-item>
        </el-menu-item-group>
      </el-menu>
    </el-aside>

    <!-- 手机端：抽屉菜单 -->
    <el-drawer
      v-model="drawerOpen"
      direction="ltr"
      size="230px"
      :with-header="false"
      class="drawer-side"
    >
      <div class="drawer-logo" @click="$router.push('/home'); drawerOpen = false">
        <span class="logo-icon">&#128187;</span>
        gitcam
      </div>
      <el-menu :default-active="$route.path" router class="menu drawer-menu" @select="drawerOpen = false">
        <el-menu-item-group title="导航">
          <el-menu-item index="/home">
            <el-icon><HomeFilled /></el-icon>
            <template #title>首页</template>
          </el-menu-item>
          <el-menu-item index="/community">
            <el-icon><ChatDotRound /></el-icon>
            <template #title>社区论坛</template>
          </el-menu-item>
        </el-menu-item-group>
        <el-menu-item-group title="项目">
          <el-menu-item index="/projects">
            <el-icon><Folder /></el-icon>
            <template #title>项目</template>
          </el-menu-item>
          <el-menu-item index="/projects/create">
            <el-icon><Plus /></el-icon>
            <template #title>创建项目</template>
          </el-menu-item>
        </el-menu-item-group>
        <el-menu-item-group title="个人">
          <el-menu-item index="/notifications">
            <el-icon><Bell /></el-icon>
            <template #title>通知中心</template>
          </el-menu-item>
          <el-menu-item index="/reply-history">
            <el-icon><ChatLineRound /></el-icon>
            <template #title>我的回复</template>
          </el-menu-item>
          <el-menu-item index="/profile">
            <el-icon><User /></el-icon>
            <template #title>个人资料</template>
          </el-menu-item>
          <el-menu-item v-if="auth.isAdmin" index="/admin/users">
            <el-icon><Setting /></el-icon>
            <template #title>管理后台</template>
          </el-menu-item>
        </el-menu-item-group>
      </el-menu>
    </el-drawer>

    <el-container>
      <el-header class="header">
        <div class="header-left">
          <el-button v-if="isMobile" text class="collapse-btn" @click="drawerOpen = true">
            <el-icon :size="20"><Menu /></el-icon>
          </el-button>
          <el-button v-else text class="collapse-btn" @click="toggleSidebar">
            <el-icon :size="18">
              <Expand v-if="collapsed" />
              <Fold v-else />
            </el-icon>
          </el-button>
          <div class="header-title">{{ $route.meta.title || 'gitcam' }}</div>
        </div>
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
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const collapsed = ref(localStorage.getItem('gitcam_sidebar_collapsed') === '1')
const drawerOpen = ref(false)
const isMobile = ref(window.innerWidth < 768)

function onResize() {
  isMobile.value = window.innerWidth < 768
  if (!isMobile.value) drawerOpen.value = false
}

function toggleSidebar() {
  collapsed.value = !collapsed.value
  localStorage.setItem('gitcam_sidebar_collapsed', collapsed.value ? '1' : '0')
}

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
  window.addEventListener('resize', onResize)
  if (!auth.user) auth.fetchMe()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
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
  transition: width 0.25s ease;
  overflow: hidden;
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
  white-space: nowrap;
}
.logo-icon {
  margin-right: 6px;
  flex-shrink: 0;
}
.logo-text {
  overflow: hidden;
}
.menu {
  border-right: none;
  background: transparent;
  --el-menu-text-color: #c0c4cc;
  --el-menu-hover-bg-color: #263445;
  --el-menu-active-color: #409eff;
  --el-menu-item-height: 44px;
}
.menu:not(.el-menu--collapse) {
  width: 220px;
}
/* 收起态兜底：强制隐藏组标题与残留文字，仅保留图标 */
.menu.el-menu--collapse .el-menu-item-group__title {
  display: none !important;
}
.menu.el-menu--collapse .el-menu-item {
  justify-content: center;
  padding: 0 10px !important;
}
.menu.el-menu--collapse .el-menu-item .el-menu-tooltip__trigger {
  justify-content: center;
  padding: 0;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.collapse-btn {
  color: #606266;
  padding: 6px;
}
.collapse-btn:hover {
  background: #f0f2f5;
}
.drawer-logo {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 19px;
  font-weight: 700;
  color: #1f2d3d;
  padding: 4px 12px 18px;
  cursor: pointer;
}
.drawer-menu {
  background: transparent;
}
.header-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.name {
  max-width: 80px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
@media (max-width: 767px) {
  .header {
    height: 52px !important;
    padding: 0 12px !important;
  }
  .main {
    padding: 12px !important;
  }
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
