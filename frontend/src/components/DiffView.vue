<template>
  <div>
    <div v-for="file in files" :key="file.old_path + '->' + file.new_path" class="diff-file">
      <div class="diff-file-header">
        <FileTypeIcon :name="file.new_path || file.old_path || ''" :size="16" />
        <el-tag size="small" :type="tagType(file.change_type)" class="ct">{{ file.change_type }}</el-tag>
        <span class="path">{{ file.new_path || file.old_path }}</span>
        <span class="counts">
          <span class="add">+{{ file.additions }}</span>
          <span class="del">-{{ file.deletions }}</span>
        </span>
      </div>
      <div class="diff-view">
        <table>
          <tbody>
            <tr v-for="(line, idx) in parsedLines(file.patch)" :key="idx" :class="lineClass(line)">
              <td class="line-num">{{ line.oldNum }}</td>
              <td class="line-num">{{ line.newNum }}</td>
              <td>{{ line.text }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <el-empty v-if="!files.length" description="无文件变更" :image-size="60" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { DiffFile } from '@/api'
import FileTypeIcon from '@/components/FileTypeIcon.vue'

const props = defineProps<{ files: DiffFile[] }>()

interface DiffLine {
  text: string
  oldNum: number | null
  newNum: number | null
  type: 'add' | 'del' | 'ctx' | 'meta'
}

function parsedLines(patch: string): DiffLine[] {
  const lines: DiffLine[] = []
  let oldNum = 0
  let newNum = 0
  for (const raw of (patch || '').split('\n')) {
    if (raw.startsWith('@@')) {
      const m = raw.match(/@@ -(\d+)(?:,\d+)? \+(\d+)/)
      if (m) {
        oldNum = parseInt(m[1]) - 1
        newNum = parseInt(m[2]) - 1
      }
      lines.push({ text: raw, oldNum: null, newNum: null, type: 'meta' })
      continue
    }
    if (raw.startsWith('\\')) {
      lines.push({ text: raw, oldNum: null, newNum: null, type: 'meta' })
      continue
    }
    if (raw.startsWith('+')) {
      newNum++
      lines.push({ text: raw, oldNum: null, newNum, type: 'add' })
    } else if (raw.startsWith('-')) {
      oldNum++
      lines.push({ text: raw, oldNum, newNum: null, type: 'del' })
    } else {
      oldNum++
      newNum++
      lines.push({ text: raw, oldNum, newNum, type: 'ctx' })
    }
  }
  return lines
}

function lineClass(line: DiffLine) {
  return line.type === 'add' || line.type === 'del' ? line.type : ''
}

function tagType(ct: string) {
  const map: Record<string, 'success' | 'danger' | 'warning' | 'primary'> = {
    A: 'success',
    D: 'danger',
    M: 'primary',
    R: 'warning',
  }
  return map[ct] || 'info'
}
</script>

<style scoped>
.diff-file {
  margin-bottom: 16px;
}
.diff-file-header {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #f5f7fa;
  padding: 8px 12px;
  border: 1px solid #e4e7ed;
  border-bottom: none;
  border-radius: 6px 6px 0 0;
  font-size: 13px;
}
.path {
  font-weight: 600;
}
.counts {
  margin-left: auto;
  font-size: 12px;
}
.add {
  color: #1a7f37;
}
.del {
  color: #cf222e;
}
</style>
