<template>
  <div class="search-view">
    <div class="search-panel">
      <div class="search-header">
        <h2>消息搜索</h2>
        <el-button text @click="$router.back()">✕</el-button>
      </div>

      <div class="search-form">
        <!-- Keyword input -->
        <div class="form-group">
          <label>关键词 (至少2个字符)</label>
          <el-input
            v-model="keyword"
            placeholder="输入关键词…"
            clearable
            @keyup.enter="search"
          />
        </div>

        <!-- Date range picker -->
        <div class="form-group">
          <label>日期范围 (可选)</label>
          <div class="date-range">
            <el-date-picker
              v-model="fromDate"
              type="date"
              placeholder="开始日期"
              style="width: 100%"
            />
            <span class="separator">至</span>
            <el-date-picker
              v-model="toDate"
              type="date"
              placeholder="结束日期"
              style="width: 100%"
            />
          </div>
        </div>

        <!-- Sender filter -->
        <div class="form-group">
          <label>发送人 (可选)</label>
          <el-select v-model="senderId" placeholder="选择发送人" clearable filterable>
            <el-option
              v-for="f in chat.friends"
              :key="f.user_id"
              :label="f.nickname || f.lunaris_id"
              :value="f.user_id"
            />
          </el-select>
        </div>

        <el-button type="primary" @click="search" :loading="loading">搜索</el-button>
      </div>

      <!-- Results -->
      <div class="results-section">
        <div v-if="!searched && results.length === 0" class="empty-state">
          输入关键词开始搜索
        </div>

        <div v-else-if="searched && results.length === 0" class="empty-state">
          没有找到相关消息
        </div>

        <div v-else class="results-list">
          <div
            v-for="(result, idx) in results"
            :key="idx"
            class="result-item"
            @click="jumpToMessage(result)"
          >
            <div class="result-header">
              <div class="sender-info">
                <span class="sender-name">{{ result.sender_name || 'Unknown' }}</span>
                <span class="conversation-name">{{ result.conversation_name }}</span>
              </div>
              <span class="time">{{ formatTime(result.created_at) }}</span>
            </div>
            <div class="result-content">{{ result.content }}</div>
          </div>

          <!-- Pagination -->
          <div class="pagination">
            <el-button
              :disabled="offset === 0"
              @click="previousPage"
            >
              上一页
            </el-button>
            <span class="page-info">第 {{ currentPage }} 页</span>
            <el-button
              :disabled="results.length < limit"
              @click="nextPage"
            >
              下一页
            </el-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useChatStore } from '../stores/chat'
import { useRouter } from 'vue-router'

const router = useRouter()
const chat = useChatStore()

const keyword = ref('')
const fromDate = ref<any>(null)
const toDate = ref<any>(null)
const senderId = ref<string>('')
const results = ref<any[]>([])
const loading = ref(false)
const searched = ref(false)
const offset = ref(0)
const limit = 20
const currentPage = ref(1)

async function search() {
  if (keyword.value.trim().length < 2) {
    ElMessage.warning('关键词至少2个字符')
    return
  }

  offset.value = 0
  currentPage.value = 1
  await performSearch()
}

async function performSearch() {
  loading.value = true
  try {
    const startDateStr = fromDate.value ? new Date(fromDate.value).toISOString().split('T')[0] : undefined
    const endDateStr = toDate.value ? new Date(toDate.value).toISOString().split('T')[0] : undefined

    const result = await chat.searchMessages(
      keyword.value,
      startDateStr,
      endDateStr,
      senderId.value || undefined,
      currentPage.value,
      limit
    )
    results.value = result.items || []
    searched.value = true
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '搜索失败')
    results.value = []
  } finally {
    loading.value = false
  }
}

function nextPage() {
  offset.value += limit
  currentPage.value += 1
  performSearch()
}

function previousPage() {
  offset.value = Math.max(0, offset.value - limit)
  currentPage.value = Math.max(1, currentPage.value - 1)
  performSearch()
}

function formatTime(dateStr: string): string {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function jumpToMessage(result: any) {
  ElMessage.info('跳转到消息：' + result.id)
  // TODO: Implement actual navigation to message
  // This would require passing conversation/group ID and scrolling to message
  router.back()
}
</script>

<style scoped>
.search-view {
  flex: 1;
  display: flex;
  background: var(--color-bg-gradient);
  overflow: hidden;
}

.search-panel {
  width: 100%;
  max-width: 600px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  padding: 20px;
}

.search-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  gap: 12px;
}

.search-header h2 {
  margin: 0;
  color: var(--color-text-primary);
  font-size: 18px;
}

.search-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 20px;
  background: rgba(255, 255, 255, 0.3);
  backdrop-filter: blur(10px);
  border-radius: var(--radius-card);
  padding: 16px;
  border: 1px solid rgba(212, 165, 212, 0.1);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-size: 13px;
  color: var(--color-text-primary);
  font-weight: 600;
}

.form-group :deep(.el-input),
.form-group :deep(.el-select) {
  width: 100%;
}

.date-range {
  display: flex;
  align-items: center;
  gap: 8px;
}

.date-range > :first-child,
.date-range > :last-child {
  flex: 1;
}

.separator {
  color: var(--color-text-light);
  padding: 0 4px;
}

.results-section {
  flex: 1;
  overflow-y: auto;
}

.empty-state {
  text-align: center;
  color: var(--color-text-light);
  padding: 40px 20px;
  font-size: 14px;
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.result-item {
  background: rgba(255, 255, 255, 0.3);
  backdrop-filter: blur(10px);
  border-radius: var(--radius-card);
  border: 1px solid rgba(212, 165, 212, 0.1);
  padding: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.result-item:hover {
  background: rgba(255, 255, 255, 0.5);
  border-color: rgba(212, 165, 212, 0.2);
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
  gap: 8px;
}

.sender-info {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.sender-name {
  color: var(--color-primary);
  font-weight: 600;
  font-size: 13px;
}

.conversation-name {
  color: var(--color-text-light);
  font-size: 12px;
  white-space: nowrap;
}

.time {
  color: var(--color-text-light);
  font-size: 12px;
  white-space: nowrap;
}

.result-content {
  color: var(--color-text-primary);
  font-size: 14px;
  line-height: 1.5;
  word-break: break-word;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 12px;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid rgba(212, 165, 212, 0.1);
}

.page-info {
  color: var(--color-text-secondary);
  font-size: 13px;
  min-width: 60px;
  text-align: center;
}
</style>
