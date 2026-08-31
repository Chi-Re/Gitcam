<template>
  <div class="admin-layout">
    <el-card v-if="!isMobile" class="admin-nav">
      <el-menu :default-active="$route.path" router>
        <el-menu-item index="/admin/users">
          <el-icon><User /></el-icon>
          <span>用户管理</span>
        </el-menu-item>
        <el-menu-item index="/admin/content">
          <el-icon><FolderOpened /></el-icon>
          <span>内容管理</span>
        </el-menu-item>
        <el-menu-item index="/admin/settings">
          <el-icon><Setting /></el-icon>
          <span>系统设置</span>
        </el-menu-item>
        <el-menu-item index="/admin/logs">
          <el-icon><List /></el-icon>
          <span>日志审计</span>
        </el-menu-item>
      </el-menu>
    </el-card>

    <div class="admin-content">
      <el-button v-if="isMobile" size="small" class="admin-toggle" @click="drawerOpen = true">
        <el-icon><Menu /></el-icon>后台菜单
      </el-button>
      <router-view />
    </div>

    <el-drawer v-model="drawerOpen" title="管理后台" size="220px">
      <el-menu :default-active="$route.path" router @select="drawerOpen = false">
        <el-menu-item index="/admin/users">
          <el-icon><User /></el-icon>
          <span>用户管理</span>
        </el-menu-item>
        <el-menu-item index="/admin/content">
          <el-icon><FolderOpened /></el-icon>
          <span>内容管理</span>
        </el-menu-item>
        <el-menu-item index="/admin/settings">
          <el-icon><Setting /></el-icon>
          <span>系统设置</span>
        </el-menu-item>
        <el-menu-item index="/admin/logs">
          <el-icon><List /></el-icon>
          <span>日志审计</span>
        </el-menu-item>
      </el-menu>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

const drawerOpen = ref(false)
const isMobile = ref(window.innerWidth < 768)

function onResize() {
  isMobile.value = window.innerWidth < 768
  if (!isMobile.value) drawerOpen.value = false
}

onMounted(() => window.addEventListener('resize', onResize))
onBeforeUnmount(() => window.removeEventListener('resize', onResize))
</script>

<style scoped>
.admin-layout {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}
.admin-nav {
  width: 200px;
  flex-shrink: 0;
}
.admin-nav .el-menu {
  border-right: none;
}
.admin-content {
  flex: 1;
  min-width: 0;
}
.admin-toggle {
  margin-bottom: 10px;
}
@media (max-width: 767px) {
  .admin-layout {
    flex-direction: column;
  }
}
</style>
