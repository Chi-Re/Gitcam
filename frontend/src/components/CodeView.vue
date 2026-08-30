<template>
  <div class="code-view">
    <div class="code-header">
      <span>{{ filename }}</span>
      <span class="size">{{ formatSize(size) }}</span>
    </div>
    <pre><code class="hljs" v-html="highlighted"></code></pre>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import hljs from 'highlight.js'

const props = defineProps<{
  filename: string
  content: string
  size?: number | null
}>()

function detectLanguage(filename: string): string {
  const map: Record<string, string> = {
    '.py': 'python',
    '.js': 'javascript',
    '.ts': 'typescript',
    '.tsx': 'typescript',
    '.jsx': 'javascript',
    '.java': 'java',
    '.c': 'c',
    '.h': 'c',
    '.cpp': 'cpp',
    '.cc': 'cpp',
    '.go': 'go',
    '.rs': 'rust',
    '.rb': 'ruby',
    '.php': 'php',
    '.html': 'html',
    '.css': 'css',
    '.scss': 'scss',
    '.json': 'json',
    '.yml': 'yaml',
    '.yaml': 'yaml',
    '.xml': 'xml',
    '.sql': 'sql',
    '.sh': 'bash',
    '.bash': 'bash',
    '.md': 'markdown',
    '.vue': 'xml',
    '.ini': 'ini',
    '.toml': 'ini',
    '.dockerfile': 'dockerfile',
    'dockerfile': 'dockerfile',
  }
  const lower = filename.toLowerCase()
  for (const [ext, lang] of Object.entries(map)) {
    if (lower.endsWith(ext)) return lang
  }
  return 'plaintext'
}

const highlighted = computed(() => {
  try {
    return hljs.highlight(props.content || '', {
      language: detectLanguage(props.filename || ''),
    }).value
  } catch {
    return (props.content || '').replace(/</g, '&lt;')
  }
})

function formatSize(size?: number | null) {
  if (size == null) return ''
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(2)} MB`
}
</script>

<style scoped>
.code-view {
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  overflow: hidden;
}
.code-header {
  display: flex;
  justify-content: space-between;
  background: #f5f7fa;
  padding: 6px 14px;
  font-size: 13px;
  color: #606266;
  border-bottom: 1px solid #e4e7ed;
}
.code-view pre {
  margin: 0;
  padding: 14px;
  overflow-x: auto;
  font-size: 13px;
}
.code-view code {
  font-family: 'SFMono-Regular', Consolas, Menlo, monospace;
}
</style>
