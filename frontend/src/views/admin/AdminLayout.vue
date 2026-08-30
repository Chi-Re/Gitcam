<template>
  <div class="admin-layout">
    <el-card class="admin-nav">
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
      <router-view />
    </div>
  </div>
</template>

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
</style>
