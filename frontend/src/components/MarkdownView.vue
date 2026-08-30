<template>
  <div class="markdown-body" v-html="html"></div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js'

const renderer = new marked.Renderer()
renderer.code = ({ text, lang }: { text: string; lang?: string }) => {
  const language = lang && hljs.getLanguage(lang) ? lang : 'plaintext'
  try {
    const highlighted = hljs.highlight(text, { language }).value
    return `<pre><code class="hljs language-${language}">${highlighted}</code></pre>`
  } catch {
    return `<pre><code>${text.replace(/</g, '&lt;')}</code></pre>`
  }
}

marked.use({
  renderer,
  breaks: true,
  gfm: true,
})

const props = defineProps<{ content: string }>()

const html = computed(() => marked.parse(props.content || '') as string)
</script>
