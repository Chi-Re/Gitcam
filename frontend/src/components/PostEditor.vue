<template>
  <div class="post-editor">
    <el-tabs v-model="tab">
      <el-tab-pane label="编辑" name="edit">
        <el-input
          v-model="text"
          type="textarea"
          :rows="rows"
          placeholder="支持 Markdown；插入代码块请用上方工具栏按钮，@用户名 可提及成员"
          resize="vertical"
        />
      </el-tab-pane>
      <el-tab-pane label="预览" name="preview">
        <div class="preview-box markdown-body">
          <MarkdownView :content="previewContent" />
        </div>
      </el-tab-pane>
    </el-tabs>

    <div class="editor-toolbar">
      <el-button size="small" @click="openFilePicker">
        <el-icon><FolderOpened /></el-icon>插入仓库代码
      </el-button>
      <el-button size="small" @click="uploadImage">
        <el-icon><Picture /></el-icon>插入图片
      </el-button>
    </div>

    <el-dialog v-model="pickerOpen" :title="props.community ? '从公共仓库选择文件' : '从仓库选择文件'" width="640px" top="8vh">
      <div class="picker">
        <div v-if="props.community" class="picker-repo">
          <el-select
            v-model="pickerProjectId"
            filterable
            placeholder="选择公共仓库（仅公开项目可选）"
            style="width: 100%"
            @change="onPickerProjectChange"
          >
            <el-option
              v-for="p in publicProjects"
              :key="p.id"
              :label="p.name"
              :value="p.id"
            >
              <span>{{ p.name }}</span>
              <span class="picker-repo-slug">@{{ p.slug }}</span>
            </el-option>
          </el-select>
        </div>
        <div class="picker-path">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item>
              <span class="crumb" @click="pickerPath = ''">仓库根目录</span>
            </el-breadcrumb-item>
            <el-breadcrumb-item v-for="(p, i) in pickerParts" :key="i">
              <span class="crumb" @click="pickerPath = pickerParts.slice(0, i + 1).join('/')">
                {{ p }}
              </span>
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div v-loading="pickerLoading" class="picker-list">
          <div
            v-for="e in pickerEntries"
            :key="e.path"
            class="picker-item"
            @click="onPickerClick(e)"
          >
            <FileTypeIcon :name="e.name" :type="e.type === 'tree' ? 'tree' : 'file'" :size="16" />
            <span>{{ e.name }}</span>
            <span v-if="e.type === 'blob'" class="picker-size">{{ formatSize(e.size) }}</span>
          </div>
          <el-empty v-if="!pickerEntries.length && !pickerLoading" description="仓库为空" />
        </div>
      </div>
      <template #footer>
        <el-button @click="pickerOpen = false">取消</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { repoApi, communityApi, storageApi, type TreeEntry } from '@/api'
import MarkdownView from '@/components/MarkdownView.vue'
import FileTypeIcon from '@/components/FileTypeIcon.vue'

const props = defineProps<{
  slug: string
  modelValue: string
  rows?: number
  community?: boolean
}>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: string): void
  (e: 'snippet', snippet: { file_path: string; content: string; language: string; project_id?: number }): void
}>()

const text = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})
const tab = ref('edit')
const pickerOpen = ref(false)
const pickerLoading = ref(false)
const pickerPath = ref('')
const pickerEntries = ref<TreeEntry[]>([])
const publicProjects = ref<{ id: number; slug: string; name: string }[]>([])
const pickerProjectId = ref<number | null>(null)

const pickerParts = computed(() => (pickerPath.value ? pickerPath.value.split('/') : []))

const pickerSlug = computed(() => {
  if (!props.community) return props.slug
  const p = publicProjects.value.find((x) => x.id === pickerProjectId.value)
  return p?.slug || ''
})

const previewContent = computed(() => {
  // 预览时保留占位符文本
  return text.value
})

async function openFilePicker() {
  pickerOpen.value = true
  pickerPath.value = ''
  if (props.community) {
    const data = await communityApi.publicProjects() as { projects: { id: number; slug: string; name: string }[] }
    publicProjects.value = data.projects
    if (!data.projects.length) {
      ElMessage.warning('暂无公共仓库可供引用')
      pickerOpen.value = false
      return
    }
    if (!pickerProjectId.value) {
      pickerProjectId.value = data.projects[0].id
    }
    await loadPicker()
  } else {
    await loadPicker()
  }
}

async function onPickerProjectChange() {
  pickerPath.value = ''
  await loadPicker()
}

async function loadPicker() {
  if (!pickerSlug.value) {
    pickerEntries.value = []
    return
  }
  pickerLoading.value = true
  try {
    const data = await repoApi.tree(pickerSlug.value, {
      path: pickerPath.value || undefined,
    }) as { entries: TreeEntry[] }
    pickerEntries.value = data.entries
  } finally {
    pickerLoading.value = false
  }
}

async function onPickerClick(entry: TreeEntry) {
  if (entry.type === 'tree') {
    pickerPath.value = entry.path
    await loadPicker()
    return
  }
  // 读取文件并插入片段
  const data = await repoApi.blob(pickerSlug.value, { path: entry.path }) as {
    content: string
    size: number
    truncated: boolean
  }
  if (data.truncated) {
    ElMessage.warning('文件过大，请手动粘贴代码')
    pickerOpen.value = false
    return
  }
  const idx = nextSnippetIndex.value
  nextSnippetIndex.value = idx + 1
  emit('snippet', {
    file_path: entry.path,
    content: data.content,
    language: '',
    project_id: props.community ? (pickerProjectId.value || undefined) : undefined,
  })
  appendText(`\n:::snippet:${idx}:::\n`)
  pickerOpen.value = false
  tab.value = 'edit'
}

const nextSnippetIndex = ref(0)

function appendText(addition: string) {
  const current = text.value
  text.value = current ? (current.endsWith('\n') ? current + addition : current + '\n' + addition) : addition
}

async function uploadImage() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = 'image/*'
  input.onchange = async () => {
    const file = input.files?.[0]
    if (!file) return
    try {
      const data = await storageApi.uploadUrl({
        filename: file.name,
        content_type: file.type || 'application/octet-stream',
      }) as { upload_url: string; download_url: string }
      await fetch(data.upload_url, { method: 'PUT', body: file })
      appendText(`\n![${file.name}](${data.download_url})\n`)
      ElMessage.success('图片已插入')
    } catch {
      ElMessage.error('图片上传失败')
    }
  }
  input.click()
}

function formatSize(size?: number | null) {
  if (size == null) return ''
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(2)} MB`
}
</script>

<style scoped>
.editor-toolbar {
  margin-top: 8px;
}
.preview-box {
  min-height: 120px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 12px;
}
.picker-repo {
  margin-bottom: 10px;
}
.picker-path {
  margin-bottom: 10px;
}
.picker-repo-slug {
  margin-left: 8px;
  color: #909399;
  font-size: 12px;
}
.crumb {
  cursor: pointer;
  color: #409eff;
}
.picker-list {
  max-height: 320px;
  overflow: auto;
}
.picker-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  cursor: pointer;
  border-radius: 4px;
}
.picker-item:hover {
  background: #f5f7fa;
}
.picker-size {
  margin-left: auto;
  color: #c0c4cc;
  font-size: 12px;
}
</style>
