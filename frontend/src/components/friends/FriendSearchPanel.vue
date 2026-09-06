<template>
  <div class="friend-search-panel">
    <div class="search-form">
      <div class="form-group">
        <label>关键词</label>
        <el-input v-model="filters.keyword" placeholder="输入用户名或ID…" clearable />
      </div>

      <div class="form-group">
        <label>性别</label>
        <el-select v-model="filters.gender" placeholder="选择性别" clearable>
          <el-option label="男" value="male" />
          <el-option label="女" value="female" />
        </el-select>
      </div>

      <div class="form-group">
        <label>排序方式</label>
        <el-select v-model="filters.sortBy" placeholder="选择排序方式" clearable>
          <el-option label="最近活跃" value="recent" />
          <el-option label="等级高低" value="level_desc" />
          <el-option label="等级低高" value="level_asc" />
        </el-select>
      </div>

      <div class="form-actions">
        <el-button type="primary" @click="handleSearch" :loading="loading">搜索</el-button>
        <el-button @click="handleReset">重置</el-button>
      </div>
    </div>

    <div class="results">
      <div v-if="results.length === 0 && searched" class="empty">暂无搜索结果</div>
      <div v-for="user in results" :key="user.user_id" class="result-item">
        <div class="user-avatar">{{ user.nickname?.[0] || user.lunaris_id?.[0] || '?' }}</div>
        <div class="user-info">
          <div class="user-name">{{ user.nickname || user.lunaris_id }}</div>
          <div class="user-meta">{{ user.lunaris_id }}</div>
        </div>
        <el-button size="small" type="primary" @click="addFriend(user)">添加</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useFriendStore } from '../../stores/friend'
import { ElMessage } from 'element-plus'

const friend = useFriendStore()

const filters = ref({
  keyword: '',
  gender: '',
  sortBy: 'recent',
})

const results = ref<any[]>([])
const loading = ref(false)
const searched = ref(false)

async function handleSearch() {
  if (!filters.value.keyword.trim()) {
    ElMessage.warning('请输入搜索关键词')
    return
  }

  loading.value = true
  try {
    const searchFilters: any = {
      keyword: filters.value.keyword,
    }
    if (filters.value.gender) searchFilters.gender = filters.value.gender
    if (filters.value.sortBy) searchFilters.sort_by = filters.value.sortBy

    results.value = await friend.advancedSearch(searchFilters)
    searched.value = true
  } catch (e) {
    ElMessage.error('搜索失败，请重试')
    results.value = []
  } finally {
    loading.value = false
  }
}

function handleReset() {
  filters.value = {
    keyword: '',
    gender: '',
    sortBy: 'recent',
  }
  results.value = []
  searched.value = false
}

async function addFriend(user: any) {
  try {
    await friend.sendRequest(user.lunaris_id)
    ElMessage.success('好友申请已发送')
  } catch (e) {
    ElMessage.error('发送申请失败，请重试')
  }
}
</script>

<style scoped>
.friend-search-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.3);
  backdrop-filter: blur(10px);
  border-radius: var(--radius-card);
  border: 1px solid rgba(212, 165, 212, 0.1);
}

.search-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-size: 12px;
  color: var(--color-text-primary);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.form-group :deep(.el-input__wrapper),
.form-group :deep(.el-select__wrapper) {
  border-radius: var(--radius-input);
  border: 1px solid rgba(212, 165, 212, 0.2);
}

.form-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.form-actions button {
  flex: 1;
}

.results {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 400px;
}

.empty {
  text-align: center;
  color: var(--color-text-light);
  padding: 20px;
  font-size: 13px;
}

.result-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  background: rgba(255, 255, 255, 0.3);
  border-radius: var(--radius-card);
  border: 1px solid rgba(212, 165, 212, 0.1);
  transition: all 0.2s ease;
}

.result-item:hover {
  background: rgba(255, 255, 255, 0.5);
  border-color: rgba(212, 165, 212, 0.2);
}

.user-avatar {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-card);
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-secondary) 100%);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
}

.user-info {
  flex: 1;
  min-width: 0;
}

.user-name {
  font-size: 13px;
  color: var(--color-text-primary);
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-meta {
  font-size: 11px;
  color: var(--color-text-light);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-top: 2px;
}
</style>
