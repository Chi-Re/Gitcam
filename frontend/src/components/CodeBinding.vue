<template>
  <div class="code-binding">
    <div class="binding-head">
      <el-tag size="small" :type="tagType" effect="plain">{{ kindLabel }}</el-tag>
      <span class="binding-path">{{ pathLabel }}</span>
      <span v-if="props.link.line_start" class="binding-lines">第 {{ props.link.line_start }}{{ props.link.line_end && props.link.line_end !== props.link.line_start ? ' - ' + props.link.line_end : '' }} 行</span>
      <el-button size="small" text type="primary" class="jump-btn" @click="jump">
        <el-icon><Position /></el-icon>{{ jumpLabel }}
      </el-button>
    </div>
    <div v-if="props.link.context?.code" class="binding-code">
      <pre><code>{{ props.link.context.code }}</code></pre>
    </div>
    <div v-else-if="props.link.context?.commit" class="binding-commit">
      <span class="commit-msg">{{ props.link.context.commit.message }}</span>
      <span class="commit-meta">{{ props.link.context.commit.author_name }} · {{ props.link.context.commit.short_sha }}</span>
    </div>
    <div v-else-if="props.link.context?.sha" class="binding-commit">
      <span class="commit-msg">{{ props.link.context.sha }}</span>
    </div>
    <div v-else-if="!props.link.context?.code" class="binding-empty">（代码内容不可用）</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import type { DiscussionLinkItem } from '@/api'

const props = defineProps<{
  link: DiscussionLinkItem
  slug: string
}>()

const router = useRouter()

const kindLabel = computed(() => {
  const kind = props.link.context?.kind
  if (kind === 'commit') return '提交绑定'
  if (kind === 'file') return '文件绑定'
  if (kind === 'commit_file') return '提交文件行级'
  if (props.link.commit_sha) return '提交绑定'
  return '文件绑定'
})

const tagType = computed(() => {
  const kind = props.link.context?.kind
  if (kind === 'commit') return 'warning'
  if (kind === 'file') return 'primary'
  return 'danger'
})

const pathLabel = computed(() => {
  const ctx = props.link.context
  if (ctx?.file_path) return ctx.file_path
  if (props.link.file_path) return props.link.file_path
  if (ctx?.commit) return ctx.commit.short_sha
  return props.link.commit_sha?.slice(0, 8) || ''
})

const jumpLabel = computed(() => {
  const kind = props.link.context?.kind
  if (kind === 'commit') return '查看提交'
  return '查看代码'
})

function jump() {
  const ctx = props.link.context
  if (ctx?.kind === 'commit' && ctx.commit) {
    router.push(`/projects/${props.slug}/commits/${ctx.commit.sha}`)
    return
  }
  if (ctx?.file_path || props.link.file_path) {
    const path = ctx?.file_path || props.link.file_path
    router.push({
      path: `/projects/${props.slug}/repo`,
      query: { path: path as string },
    })
  }
}
</script>

<style scoped>
.code-binding {
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  overflow: hidden;
}
.binding-head {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #f5f7fa;
  padding: 8px 12px;
  font-size: 13px;
}
.binding-path {
  font-weight: 600;
}
.binding-lines {
  color: #909399;
  font-size: 12px;
}
.jump-btn {
  margin-left: auto;
}
.binding-code {
  background: #fafbfc;
  padding: 10px 14px;
  overflow-x: auto;
  max-height: 200px;
  overflow-y: auto;
}
.binding-code pre {
  margin: 0;
  font-size: 12.5px;
  font-family: 'SFMono-Regular', Consolas, Menlo, monospace;
  white-space: pre;
}
.binding-commit {
  padding: 10px 14px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.commit-msg {
  font-weight: 500;
}
.commit-meta {
  color: #909399;
  font-size: 12px;
}
.binding-empty {
  padding: 10px 14px;
  color: #909399;
  font-size: 13px;
}
</style>
