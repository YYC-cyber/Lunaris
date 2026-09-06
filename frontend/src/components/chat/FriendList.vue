<template>
  <div class="friend-list">
    <div class="search">
      <el-input v-model="keyword" placeholder="搜索" size="small" clearable />
    </div>
    <div class="list">
      <!-- AI 伴侣（可收缩） -->
      <div class="section-header">
        <span class="section">AI 伴侣</span>
        <button class="collapse-btn" @click="toggleSoulsCollapsed" :title="soulsCollapsed ? '展开' : '收缩'">
          {{ soulsCollapsed ? '▶' : '▼' }}
        </button>
      </div>
      <div v-if="!soulsCollapsed">
        <div
          v-for="s in filteredSouls"
          :key="s.id"
          class="item"
          :class="{ active: s.id === chat.currentSoulId }"
          @click="chat.selectSoul(s.id)"
        >
          <div class="avatar">{{ s.display_name[0] }}</div>
          <div class="info">
            <div class="name">{{ s.display_name }}</div>
            <!-- 当日心语 -->
            <div class="daily-motto">{{ getDailyMotto(s.id) }}</div>
            <!-- 最近消息预览 -->
            <div class="last-message">{{ getLastMessage(s.id) }}</div>
            <!-- 亲密度进度条 -->
            <div class="intimacy-bar">
              <div class="intimacy-fill" :style="{ width: `${getIntimacy(s.id)}%` }"></div>
            </div>
          </div>
          <div v-if="chat.unread[s.id]" class="badge">{{ chat.unread[s.id] }}</div>
        </div>
      </div>

      <!-- 真人好友（可收缩） -->
      <div class="section-header">
        <span class="section">真人好友</span>
        <button class="collapse-btn" @click="toggleFriendsCollapsed" :title="friendsCollapsed ? '展开' : '收缩'">
          {{ friendsCollapsed ? '▶' : '▼' }}
        </button>
      </div>
      <div v-if="!friendsCollapsed">
        <div
          v-for="f in chat.friends"
          :key="f.user_id"
          class="item"
          :class="{ active: f.user_id === chat.currentFriendId }"
          @click="chat.selectFriend(f)"
        >
          <div class="avatar-wrapper">
            <div class="avatar person">👤</div>
            <div class="online-status" :class="{ online: isUserOnline(f.user_id) }" :title="isUserOnline(f.user_id) ? '在线' : `最后活动于 ${getLastActivityTime(f.user_id)}`"></div>
          </div>
          <div class="info">
            <div class="name">{{ f.nickname || f.lunaris_id }}</div>
            <div class="tags">{{ f.lunaris_id }}</div>
            <div class="activity" v-if="!isUserOnline(f.user_id)">最后活动于 {{ getLastActivityTime(f.user_id) }}</div>
          </div>
        </div>
      </div>

      <div v-if="!filteredSouls.length && !chat.friends.length" class="empty">暂无聊天对象</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useChatStore } from '../../stores/chat'
import { useUserStore } from '../../stores/user'
import { wsClient } from '../../utils/ws'
import api from '../../utils/api'

const chat = useChatStore()
const user = useUserStore()
const keyword = ref('')
const friendshipData = ref<Record<number, any>>({})
const soulsCollapsed = ref(false)
const friendsCollapsed = ref(false)
const userLastActivity = ref<Record<string, number>>({})

const filteredSouls = computed(() => {
  if (!keyword.value) return chat.souls
  return chat.souls.filter((s) => s.display_name.includes(keyword.value))
})

function getIntimacy(soulId: number): number {
  return friendshipData.value[soulId]?.intimacy_level || 0
}

function getDailyMotto(soulId: number): string {
  return friendshipData.value[soulId]?.daily_motto || "今天也要开心呀！"
}

function getLastMessage(soulId: number): string {
  const preview = friendshipData.value[soulId]?.last_message_preview
  if (!preview) return ""
  return preview.length > 20 ? preview.substring(0, 20) + "..." : preview
}

function toggleSoulsCollapsed() {
  soulsCollapsed.value = !soulsCollapsed.value
}

function toggleFriendsCollapsed() {
  friendsCollapsed.value = !friendsCollapsed.value
}

function isUserOnline(userId: string): boolean {
  return user.onlineUsers.has(userId)
}

function getLastActivityTime(userId: string): string {
  const timestamp = userLastActivity.value[userId]
  if (!timestamp) return '未知'
  const minutes = Math.floor((Date.now() - timestamp) / 60000)
  if (minutes === 0) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}小时前`
  const days = Math.floor(hours / 24)
  return `${days}天前`
}

async function loadFriendshipData() {
  try {
    const res: any = await api.get('/v1/chat/friendships')
    const data = Array.isArray(res) ? res : (res?.data ?? [])
    data.forEach((item: any) => {
      friendshipData.value[item.soul_id] = item
    })
  } catch (e) {
    console.error('加载关系数据失败:', e)
  }
}

function setupWebSocketListeners() {
  wsClient.on('user_online', (e) => {
    const userId = e?.data?.user_id
    if (userId) {
      user.updateUserStatus(userId, true)
      userLastActivity.value[userId] = Date.now()
    }
  })

  wsClient.on('user_offline', (e) => {
    const userId = e?.data?.user_id
    if (userId) {
      user.updateUserStatus(userId, false)
      userLastActivity.value[userId] = Date.now()
    }
  })
}

onMounted(async () => {
  await loadFriendshipData()
  await user.fetchOnlineUsers()

  for (const friend of chat.friends) {
    userLastActivity.value[friend.user_id] = Date.now()
  }

  setupWebSocketListeners()
})
</script>

<style scoped>
.friend-list {
  width: 260px;
  background: color-mix(in srgb, var(--companion-surface, #fff) 62%, transparent);
  backdrop-filter: blur(10px);
  border-right: 1px solid rgba(212, 165, 212, 0.15);
  display: flex;
  flex-direction: column;
  box-shadow: inset -1px 0 4px rgba(0, 0, 0, 0.02);
}

.search {
  padding: 12px;
}

.search :deep(.el-input__wrapper) {
  border-radius: var(--radius-input);
  background: color-mix(in srgb, var(--companion-surface, #fff) 72%, white 28%);
  border: 1px solid color-mix(in srgb, var(--companion-primary, #d4a5d4) 24%, transparent);
  transition: all 0.2s ease;
}

.search :deep(.el-input__wrapper:hover) {
  border-color: color-mix(in srgb, var(--companion-primary, #d4a5d4) 48%, transparent);
  background: color-mix(in srgb, var(--companion-surface, #fff) 84%, white 16%);
}

.list {
  flex: 1;
  overflow-y: auto;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px 6px 16px;
}

.section {
  font-size: 11px;
  color: var(--color-text-light);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.collapse-btn {
  background: none;
  border: none;
  color: var(--color-text-light);
  cursor: pointer;
  font-size: 10px;
  padding: 2px 4px;
  transition: color 0.2s ease;
  opacity: 0.6;
}

.collapse-btn:hover {
  opacity: 1;
  color: var(--color-primary);
}

.item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  margin: 0 8px;
  cursor: pointer;
  position: relative;
  border-radius: var(--radius-card);
  transition: all 0.2s ease;
}

.item:hover {
  background: color-mix(in srgb, var(--companion-secondary, #d4a5d4) 14%, transparent);
}

.item.active {
  background: color-mix(in srgb, var(--companion-secondary, #d4a5d4) 28%, transparent);
  box-shadow: inset 3px 0 0 var(--companion-primary, #d4a5d4);
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-card);
  background: linear-gradient(135deg, var(--companion-primary, var(--color-primary)) 0%, var(--companion-secondary, var(--color-secondary)) 100%);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 17px;
  flex-shrink: 0;
  font-weight: 600;
  box-shadow: var(--shadow-soft);
}

.avatar.person {
  background: linear-gradient(135deg, #7B68BE 0%, #5B4FB1 100%);
  position: relative;
}

.avatar-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.online-status {
  position: absolute;
  bottom: -2px;
  right: -2px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #888888;
  border: 2px solid var(--color-bg-main);
  box-shadow: var(--shadow-soft);
  transition: background 0.3s ease;
}

.online-status.online {
  background: #07c160;
}

.activity {
  font-size: 10px;
  color: var(--color-text-light);
  margin-top: 2px;
}

.info {
  flex: 1;
  min-width: 0;
}

.name {
  font-size: 14px;
  color: var(--color-text-primary);
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 当日心语 */
.daily-motto {
  font-size: 10px;
  color: var(--color-primary);
  font-style: italic;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-top: 1px;
  opacity: 0.8;
}

/* 最近消息预览 */
.last-message {
  font-size: 11px;
  color: var(--color-text-light);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-top: 2px;
  margin-bottom: 4px;
}

.tags {
  font-size: 11px;
  color: var(--color-text-light);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-top: 2px;
  margin-bottom: 4px;
}

/* 亲密度进度条 */
.intimacy-bar {
  width: 100%;
  height: 4px;
  background: rgba(212, 165, 212, 0.1);
  border-radius: 2px;
  overflow: hidden;
}

.intimacy-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary) 0%, var(--color-secondary) 100%);
  border-radius: 2px;
  transition: width 0.3s ease;
}

.badge {
  background: linear-gradient(135deg, #E85D75 0%, #D64560 100%);
  color: #fff;
  border-radius: 10px;
  padding: 2px 7px;
  font-size: 11px;
  font-weight: 600;
  box-shadow: var(--shadow-soft);
}

.empty {
  text-align: center;
  color: var(--color-text-light);
  margin-top: 40px;
  font-size: 13px;
}
</style>
