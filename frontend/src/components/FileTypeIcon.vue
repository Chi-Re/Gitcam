<template>
  <span class="file-type-icon" :style="{ width: size + 'px', height: size + 'px' }">
    <svg
      v-if="body"
      viewBox="0 0 24 24"
      :width="size"
      :height="size"
      xmlns="http://www.w3.org/2000/svg"
      v-html="body"
    />
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  FILE_ICONS,
  FILE_ICON_BY_FILENAME,
  FILE_ICON_BY_EXT,
  FOLDER_ICON,
  FOLDER_OPEN_ICON,
  DEFAULT_FILE_ICON,
} from '@/assets/fileIcons'

const props = withDefaults(
  defineProps<{
    /** 文件名（用于推断扩展名与特殊文件名） */
    name: string
    /** 目录标记：tree=目录（默认关闭态），tree-open=展开态 */
    type?: 'file' | 'tree' | 'tree-open'
    size?: number
  }>(),
  { type: 'file', size: 18 },
)

const body = computed(() => {
  if (props.type === 'tree') return FOLDER_ICON
  if (props.type === 'tree-open') return FOLDER_OPEN_ICON
  const lower = (props.name || '').toLowerCase()
  // 1. 特殊文件名（Dockerfile / .gitignore / package.json 等）
  const byName = FILE_ICON_BY_FILENAME[lower]
  if (byName && FILE_ICONS[byName]) return FILE_ICONS[byName]
  // 2. 扩展名（取最后一个点之后的完整后缀链，如 .d.ts 先试 d.ts 再试 ts）
  const ext = lower.includes('.') ? lower.slice(lower.lastIndexOf('.') + 1) : ''
  if (ext && FILE_ICON_BY_EXT[ext] && FILE_ICONS[FILE_ICON_BY_EXT[ext]]) {
    return FILE_ICONS[FILE_ICON_BY_EXT[ext]]
  }
  // 3. 复合扩展名（.d.ts → d.ts, .test.ts → test.ts）
  if (lower.includes('.')) {
    const parts = lower.split('.')
    for (let i = 1; i < parts.length - 1; i++) {
      const compound = parts.slice(i).join('.')
      if (FILE_ICON_BY_EXT[compound] && FILE_ICONS[FILE_ICON_BY_EXT[compound]]) {
        return FILE_ICONS[FILE_ICON_BY_EXT[compound]]
      }
    }
  }
  // 4. 未匹配 → 通用文件图标
  return DEFAULT_FILE_ICON
})
</script>

<style scoped>
.file-type-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  vertical-align: middle;
}
.file-type-icon svg {
  display: block;
}
</style>
