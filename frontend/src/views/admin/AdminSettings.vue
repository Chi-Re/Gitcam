<template>
  <el-card v-loading="loading">
    <template #header>系统设置</template>
    <el-form label-width="120px" style="max-width: 640px">
      <el-form-item label="站点公告">
        <el-input v-model="form.site_announcement" type="textarea" :rows="3" placeholder="显示在登录页与页头（可留空）" />
      </el-form-item>
      <el-form-item label="通知总开关">
        <el-switch v-model="form.notifications_enabled" />
        <span class="hint">关闭后系统不再产生任何站内通知</span>
      </el-form-item>
      <el-form-item label="存储配额 (MB)">
        <el-input-number v-model="form.storage_quota_mb" :min="1" :max="102400" />
        <span class="hint">Git 仓库与上传文件的配额上限</span>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="saving" @click="save">保存设置</el-button>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { adminApi } from '@/api'

interface Settings {
  site_announcement: string
  notifications_enabled: boolean
  storage_quota_mb: number
}

const loading = ref(false)
const saving = ref(false)
const form = reactive<Settings>({
  site_announcement: '',
  notifications_enabled: true,
  storage_quota_mb: 1024,
})

async function load() {
  loading.value = true
  try {
    const data = await adminApi.settings() as { settings: Settings }
    Object.assign(form, data.settings)
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  try {
    await adminApi.updateSettings({ ...form })
    ElMessage.success('设置已保存')
    load()
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.hint {
  margin-left: 12px;
  color: #909399;
  font-size: 12px;
}
</style>
