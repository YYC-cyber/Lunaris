<template>
  <div class="knowledge-panel">
    <!-- 上传区 -->
    <div class="upload-card">
      <h3>📚 知识库（文档问答 RAG）</h3>
      <p class="hint">上传文档后，可基于文档内容向你提问。支持 txt / md / pdf / docx。</p>
      <div class="upload-row">
        <el-upload
          :auto-upload="false"
          :show-file-list="false"
          :on-change="handleFileChange"
          accept=".txt,.md,.pdf,.docx"
        >
          <el-button type="primary" :disabled="uploading">📤 选择文档</el-button>
        </el-upload>
        <el-button v-if="!!selectedFile" :loading="uploading" @click="doUpload">
          {{ uploadedName }}
        </el-button>
      </div>
    </div>

    <!-- 文档列表 -->
    <div class="doc-section">
      <h3>我的文档（{{ knowledge.documents.length }}）</h3>
      <div v-if="knowledge.loading" class="empty">正在加载…</div>
      <div v-else-if="!knowledge.documents.length" class="empty">还没有上传文档</div>
      <div v-else class="doc-list">
        <div v-for="d in knowledge.documents" :key="d.id" class="doc-item">
          <div class="doc-icon">{{ d.file_type === 'pdf' ? '📄' : d.file_type === 'docx' ? '📘' : '📝' }}</div>
          <div class="doc-info">
            <div class="doc-name">{{ d.file_name }}</div>
            <div class="doc-meta">
              <el-tag :type="statusType(d.status)" size="small">{{ statusText(d.status) }}</el-tag>
              <span v-if="d.status === 'ready'">{{ d.chunk_count }} 分块 · {{ formatSize(d.file_size) }}</span>
            </div>
          </div>
          <el-button v-if="d.file_url" size="small" text @click="openFile(d.file_url)">下载</el-button>
          <el-button size="small" text type="danger" @click="removeDoc(d)">删除</el-button>
        </div>
      </div>
    </div>

    <!-- RAG 问答 -->
    <div class="qa-section">
      <h3>🤖 基于文档问答</h3>
      <div class="ask-row">
        <el-input v-model="query" placeholder="例如：帮我总结文档中的重点内容" @keyup.enter="ask" />
        <el-button type="primary" :loading="knowledge.asking" @click="ask">提问</el-button>
      </div>
      <div v-if="knowledge.answer" class="answer">
        <div class="answer-text">{{ knowledge.answer }}</div>
      </div>
      <div v-if="knowledge.results.length" class="sources">
        <div class="source-title">参考资料</div>
        <div v-for="(s, i) in knowledge.results" :key="i" class="source-item">{{ s.content }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useKnowledgeStore } from '../../stores/knowledge'

const knowledge = useKnowledgeStore()
const selectedFile = ref<File | null>(null)
const uploading = ref(false)
const query = ref('')

const uploadedName = () => (selectedFile.value ? `⬆️ 上传 ${selectedFile.value.name}` : '')

function handleFileChange(file: any) {
  selectedFile.value = file?.raw || null
}

async function doUpload() {
  if (!selectedFile.value) return
  uploading.value = true
  try {
    await knowledge.upload(selectedFile.value)
    ElMessage.success('文档已上传，处理中或已完成')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '上传失败')
  } finally {
    uploading.value = false
    selectedFile.value = null
  }
}

function statusType(s: string) {
  return s === 'ready' ? 'success' : s === 'failed' ? 'danger' : 'warning'
}
function statusText(s: string) {
  return s === 'ready' ? '已完成' : s === 'failed' ? '处理失败' : '处理中'
}
function formatSize(s?: number) {
  if (!s) return ''
  return s > 1024 * 1024 ? `${(s / 1024 / 1024).toFixed(1)}MB` : `${(s / 1024).toFixed(0)}KB`
}
function openFile(url: string) {
  window.open(url, '_blank')
}

async function removeDoc(d: any) {
  await knowledge.remove(d.id)
  ElMessage.success('已删除')
}

async function ask() {
  if (!query.value.trim()) return
  await knowledge.ask(query.value)
}

onMounted(knowledge.loadDocuments)
</script>

<style scoped>
.knowledge-panel {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
  background: radial-gradient(
      circle at 85% 0%,
      color-mix(in srgb, var(--companion-secondary, #cbd1dc) 12%, transparent),
      transparent 28%
    ),
    var(--companion-page, #f3f5f7);
}
.upload-card { max-width: 640px; }
.hint { color: var(--color-text-secondary); font-size: 12px; }
.upload-row { display: flex; align-items: center; gap: 10px; margin-top: 10px; }
.doc-section, .qa-section { margin-top: 22px; max-width: 640px; }
h3 { margin: 8px 0; color: var(--color-text-primary); font-weight: 600; }
.empty { color: var(--color-text-light); padding: 16px 0; font-size: 13px; }
.doc-list { border-top: 1px solid color-mix(in srgb, var(--companion-primary, #cbd1dc) 12%, transparent); }
.doc-item {
  display: flex; align-items: center; gap: 10px; padding: 10px 0;
  border-bottom: 1px solid color-mix(in srgb, var(--companion-primary, #cbd1dc) 12%, transparent);
}
.doc-icon { font-size: 22px; }
.doc-info { flex: 1; min-width: 0; }
.doc-name {
  color: var(--color-text-primary); font-weight: 600; overflow-wrap: anywhere;
}
.doc-meta { display: flex; align-items: center; gap: 8px; margin-top: 4px; font-size: 12px; color: var(--color-text-secondary); }
.ask-row { display: flex; gap: 8px; }
.answer {
  margin-top: 12px; background: rgba(255, 255, 255, 0.55);
  backdrop-filter: blur(10px); border-radius: var(--radius-card); padding: 14px;
  border: 1px solid color-mix(in srgb, var(--companion-secondary, #d4a5d4) 14%, transparent);
}
.answer-text { font-size: 14px; line-height: 1.7; white-space: pre-wrap; overflow-wrap: anywhere; }
.sources { margin-top: 14px; }
.source-title { font-size: 12px; color: var(--color-text-secondary); margin-bottom: 6px; }
.source-item {
  background: color-mix(in srgb, var(--companion-secondary, #cbd1dc) 10%, transparent);
  border-radius: var(--radius-card); padding: 8px 10px; margin-bottom: 6px;
  font-size: 13px; color: var(--color-text-primary); overflow-wrap: anywhere;
  max-height: 90px; overflow-y: auto;
}
</style>