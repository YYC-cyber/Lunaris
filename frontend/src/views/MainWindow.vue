<template>
  <div class="main" :style="companionStyle">
    <!-- 左侧 tab 栏 -->
    <div class="sidebar" :style="companionStyle">
      <div class="avatar" @click="active = 'me'" title="我的信息">{{ avatarLetter }}</div>
      <!-- 北京时钟 -->
      <div class="beijing-clock">{{ currentTime }}</div>
      <div
        v-for="t in tabs"
        :key="t.key"
        class="tab"
        :class="{ active: active === t.key }"
        @click="switchTab(t.key)"
      >
        <span class="icon">{{ t.icon }}</span>
        <span class="label">{{ t.label }}</span>
      </div>
    </div>

    <!-- 内容区 -->
    <div class="content" :style="companionStyle">
      <!-- 聊天 -->
      <div v-if="active === 'chat'" class="chat-layout" :style="companionStyle">
        <FriendList />
        <ChatWindow />
      </div>

      <!-- 通讯录 -->
      <div v-else-if="active === 'contacts'" class="contacts-panel">
        <h3>AI 伴侣</h3>
        <div v-for="s in chat.souls" :key="s.id" class="row">
          <div class="avatar-sm">{{ s.display_name[0] }}</div>
          <div class="info"><div class="nm">{{ s.display_name }}</div><div class="sub">{{ s.gender === 'male' ? '男' : '女' }}</div></div>
          <el-button size="small" :type="s.is_default ? 'primary' : 'default'" @click="setPrimary(s)">设为伴侣</el-button>
          <el-button size="small" text type="danger" @click="removeSoul(s)">删除</el-button>
        </div>
        <el-button text type="primary" @click="showAvailable = true">＋ 添加角色</el-button>

        <h3 style="margin-top:20px">真人好友</h3>
        <div class="friend-search">
          <el-input v-model="lunarisId" placeholder="输入对方 lunaris_id" size="small" style="width: 220px" />
          <el-button size="small" @click="addFriend">添加</el-button>
        </div>
        <div v-for="f in friend.friends" :key="f.user_id" class="row">
          <div class="avatar-sm">👤</div>
          <div class="info"><div class="nm">{{ f.nickname || f.lunaris_id }}</div><div class="sub">{{ f.lunaris_id }}</div></div>
          <el-button size="small" text :type="isBlocked(f.user_id) ? 'success' : 'default'" @click="toggleBlock(f)">{{ isBlocked(f.user_id) ? '已屏蔽(点击解除)' : '屏蔽' }}</el-button>
          <el-button size="small" text type="danger" @click="removeFriend(f)">删除</el-button>
        </div>
        <div v-if="friend.requests.length">
          <h4>好友申请</h4>
          <div v-for="r in friend.requests" :key="r.user_id || r.requester_id" class="row">
            <div class="avatar-sm">👤</div>
            <div class="info"><div class="nm">{{ r.lunaris_id || r.requester_id }}</div></div>
            <el-button size="small" type="primary" @click="friend.handleRequest(r.user_id || r.requester_id, 'accept')">接受</el-button>
            <el-button size="small" @click="friend.handleRequest(r.user_id || r.requester_id, 'reject')">拒绝</el-button>
          </div>
        </div>
      </div>

      <!-- 群聊 -->
      <div v-else-if="active === 'groups'" class="groups-panel">
        <GroupChatWindow />
      </div>

      <!-- 发现（朋友圈） -->
      <div v-else-if="active === 'moments'" class="scroll-panel">
        <MomentTimeline />
      </div>

      <!-- 知识库（RAG 问答） -->
      <div v-else-if="active === 'knowledge'" class="knowledge-panel">
        <KnowledgePanel />
      </div>

      <!-- 我 -->
      <div v-else-if="active === 'me'" class="me-panel">
        <div class="profile">
          <div class="avatar-lg">{{ avatarLetter }}</div>
          <div>
            <div class="nm">{{ user.user?.nickname || user.user?.username }}</div>
            <div class="sub">lunaris_id：{{ user.user?.lunaris_id || '—' }}</div>
            <div class="sub" v-if="user.user?.remaining_days != null">平台 AI 剩余：{{ user.user.remaining_days }} 天</div>
          </div>
        </div>

        <h3>显示设置</h3>
        <ThemeToggle />
        <FontSizeSelector />

        <h3>API 配置（BYOK，支持任意 OpenAI 兼容服务）</h3>
        <ApiConfigPanel />

        <div class="section-heading">
          <h3>我的收藏</h3>
          <el-button size="small" text @click="loadFavorites">刷新</el-button>
        </div>
        <div v-if="favoritesLoading" class="empty">正在加载收藏…</div>
        <div v-else-if="!favorites.length" class="empty">还没有收藏消息</div>
        <div v-else class="favorites-list">
          <div v-for="item in favorites" :key="item.favorite_id" class="favorite-item">
            <div class="favorite-content">
              <div class="favorite-text">{{ item.content || '（媒体消息）' }}</div>
              <div class="favorite-meta">{{ item.category }} · {{ formatFavoriteTime(item.created_at) }}</div>
            </div>
            <el-button text type="danger" @click="removeFavorite(item.message_id)">取消收藏</el-button>
          </div>
        </div>

        <div class="section-heading" style="margin-top:16px;">
          <h3>账户与安全</h3>
        </div>
        <el-button style="margin-bottom:10px" @click="openEditProfile">✏️ 修改资料（昵称）</el-button>
        <el-button style="margin-bottom:10px" @click="showPwdDialog = true">🔑 修改密码</el-button>
        <el-button style="margin-bottom:10px" @click="openBlockDialog">🚫 屏蔽管理</el-button>
        <el-button style="margin-bottom:10px" @click="downloadMyData">⬇️ 导出数据</el-button>

        <div style="margin-top:24px; display: flex; gap: 12px;">
          <el-button type="danger" plain @click="logout">退出登录</el-button>
          <el-button type="danger" plain @click="showDeleteDialog = true">永久注销账号</el-button>
        </div>
        <div class="hint" style="margin-top:6px">⚠️ 注销将清除全部数据，操作不可逆</div>
      </div>
    </div>

    <!-- 添加角色对话框 -->
    <el-dialog v-model="showAvailable" title="添加 AI 伴侣" width="420px">
      <div v-for="s in available" :key="s.id" class="row">
        <div class="avatar-sm">{{ s.display_name[0] }}</div>
        <div class="info"><div class="nm">{{ s.display_name }}</div><div class="sub">{{ (s.tags || []).join(' · ') }}</div></div>
        <el-button size="small" type="primary" :loading="isAddingSoul" @click="addSoul(s)">添加</el-button>
      </div>
      <div v-if="!available.length" class="empty">暂无可添加的异性角色</div>
    </el-dialog>

    <!-- 修改资料（昵称） -->
    <el-dialog v-model="showProfileDialog" title="修改资料" width="380px">
      <div class="field">
        <div style="font-size:12px;color:var(--color-text-secondary);margin-bottom:6px">昵称</div>
        <el-input v-model="profileForm.nickname" placeholder="请输入昵称" maxlength="30" />
      </div>
      <template #footer>
        <el-button @click="showProfileDialog = false">取消</el-button>
        <el-button type="primary" :loading="savingProfile" @click="saveProfile">保存</el-button>
      </template>
    </el-dialog>

    <!-- 修改密码 -->
    <el-dialog v-model="showPwdDialog" title="修改密码" width="380px">
      <div class="field">
        <div style="font-size:12px;color:var(--color-text-secondary);margin-bottom:6px">原密码</div>
        <el-input v-model="pwdForm.old_password" type="password" show-password placeholder="请输入原密码" />
      </div>
      <div class="field">
        <div style="font-size:12px;color:var(--color-text-secondary);margin-bottom:6px">新密码</div>
        <el-input v-model="pwdForm.new_password" type="password" show-password placeholder="请输入新密码" />
      </div>
      <template #footer>
        <el-button @click="showPwdDialog = false">取消</el-button>
        <el-button type="primary" :loading="savingPwd" @click="savePassword">确认修改</el-button>
      </template>
    </el-dialog>

    <!-- 屏蔽管理 -->
    <el-dialog v-model="showBlockDialog" title="屏蔽管理" width="420px">
      <div v-if="!user.blocks.length" class="empty">暂未屏蔽任何人</div>
      <div v-for="b in user.blocks" :key="b.user_id ?? b.blocked_user_id ?? b.id" class="row">
        <div class="avatar-sm">🚫</div>
        <div class="info"><div class="nm">{{ b.nickname || b.username || b.lunaris_id || b.user_id || '已屏蔽用户' }}</div><div class="sub">{{ b.lunaris_id || 'ID 不可用' }}</div></div>
        <el-button size="small" @click="unblock(b)">解除屏蔽</el-button>
      </div>
      <template #footer>
        <el-button @click="showBlockDialog = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 永久注销 -->
    <el-dialog v-model="showDeleteDialog" title="永久注销账号" width="380px">
      <p style="line-height:1.8;color:var(--color-text-primary)">注销后，您的账户、聊天记录、朋友圈等内容将被<b>永久删除且无法恢复</b>。确定要继续吗？</p>
      <template #footer>
        <el-button @click="showDeleteDialog = false">取消</el-button>
        <el-button type="danger" :loading="deleting" @click="confirmDelete">确认注销</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../utils/api'
import { useUserStore } from '../stores/user'
import { useChatStore } from '../stores/chat'
import { useMomentStore } from '../stores/moment'
import { useFriendStore } from '../stores/friend'
import { useGroupStore } from '../stores/group'
import { useWsStore } from '../stores/ws'
import { useUiStore } from '../stores/ui'
import FriendList from '../components/chat/FriendList.vue'
import ChatWindow from '../components/chat/ChatWindow.vue'
import GroupChatWindow from '../components/chat/GroupChatWindow.vue'
import MomentTimeline from '../components/moments/MomentTimeline.vue'
import ApiConfigPanel from '../components/settings/ApiConfigPanel.vue'
import ThemeToggle from '../components/common/ThemeToggle.vue'
import FontSizeSelector from '../components/common/FontSizeSelector.vue'
import KnowledgePanel from '../components/knowledge/KnowledgePanel.vue'

const router = useRouter()
const user = useUserStore()
const chat = useChatStore()
const moment = useMomentStore()
const friend = useFriendStore()
const group = useGroupStore()
const ws = useWsStore()
const ui = useUiStore()
const favorites = ref<any[]>([])
const favoritesLoading = ref(false)

const tabs = computed(() => {
  return [
    { key: 'chat', label: '聊天', icon: '💬' },
    { key: 'groups', label: '群聊', icon: '👥' },
    { key: 'contacts', label: '通讯录', icon: '📋' },
    { key: 'moments', label: '发现', icon: '🧭' },
    { key: 'knowledge', label: '知识库', icon: '📚' },
    { key: 'me', label: '我', icon: '👤' },
  ]
})
const active = ref('chat')
const currentTime = ref('00:00')

// 获取北京时间并更新时钟
function updateClock() {
  const formatter = new Intl.DateTimeFormat('zh-CN', {
    timeZone: 'Asia/Shanghai',
    hour: '2-digit',
    minute: '2-digit',
  })
  currentTime.value = formatter.format(new Date())
}

const avatarLetter = computed(() => {
  const name = user.user?.nickname || user.user?.username || 'L'
  return name[0]
})

const companionStyle = computed(() => {
  const name = chat.currentSoul?.name?.toLowerCase() || ''
  const themes: Record<string, { primary: string; secondary: string; surface: string; bubble: string; page: string }> = {
    diana: { primary: '#9274b4', secondary: '#caa5c8', surface: '#f0e7f2', bubble: '#ead9ed', page: '#f4eef5' },
    raven: { primary: '#637891', secondary: '#9baec3', surface: '#e5ebf0', bubble: '#d9e3ec', page: '#eef2f5' },
    luna: { primary: '#7f86b8', secondary: '#c0bce0', surface: '#e8e8f5', bubble: '#e0def2', page: '#f0f0f8' },
    elara: { primary: '#b07f78', secondary: '#d9ada0', surface: '#f3e8e2', bubble: '#f0ddd8', page: '#f7efeb' },
  }
  const theme = themes[name] || { primary: '#9b7ba9', secondary: '#d4a5d4', surface: '#f0e8f2', bubble: '#eadcf0', page: '#f7f3f7' }
  return {
    '--companion-primary': theme.primary,
    '--companion-secondary': theme.secondary,
    '--companion-surface': theme.surface,
    '--companion-bubble': theme.bubble,
    '--companion-page': theme.page,
  }
})

function getTimeBasedGradient(): string {
  return 'linear-gradient(135deg, #eef0f4 0%, #f7f8fa 100%)'
}

function switchTab(key: string) {
  active.value = key
  if (key === 'contacts') { friend.loadFriends(); friend.loadRequests(); loadAvailable(); user.fetchBlocks() }
  if (key === 'moments') moment.loadTimeline()
  if (key === 'groups') { group.loadGroups(); group.loadPendingInvitations() }
  if (key === 'me') loadFavorites()
}

async function loadFavorites() {
  favoritesLoading.value = true
  try {
    const res: any = await api.get('/v1/chat/message/favorites', { params: { limit: 50 } })
    favorites.value = res?.items ?? res?.data?.items ?? []
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '收藏加载失败')
  } finally {
    favoritesLoading.value = false
  }
}

async function removeFavorite(messageId: number) {
  try {
    await api.delete(`/v1/chat/message/${messageId}/favorite`)
    favorites.value = favorites.value.filter((item) => item.message_id !== messageId)
    ElMessage.success('已取消收藏')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '取消收藏失败')
  }
}

function formatFavoriteTime(value?: string) {
  if (!value) return ''
  return new Date(value).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

const available = ref<any[]>([])
const showAvailable = ref(false)
const isAddingSoul = ref(false)

async function loadAvailable() {
  const res: any = await api.get('/api/souls/available')
  available.value = Array.isArray(res) ? res : (res?.data || [])
}
async function addSoul(s: any) {
  if (isAddingSoul.value) return
  isAddingSoul.value = true
  try {
    await api.post(`/api/souls/${s.id}/add`)
    ElMessage.success('已添加，去聊天吧')
    await chat.loadSouls()
    await loadAvailable()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '添加失败')
  } finally {
    isAddingSoul.value = false
  }
}
async function setPrimary(s: any) {
  await api.put(`/api/souls/${s.id}/primary`)
  ElMessage.success('已设为默认伴侣')
  await chat.loadSouls()
  chat.selectSoul(s.id)
}
async function removeSoul(s: any) {
  await api.delete(`/api/souls/${s.id}/remove`)
  await chat.loadSouls()
  if (chat.currentSoulId === s.id) {
    chat.currentSoulId = null
    const nextSoul = chat.souls.find((soul) => soul.is_default) || chat.souls[0]
    if (nextSoul) chat.selectSoul(nextSoul.id)
  }
}

const lunarisId = ref('')
async function addFriend() {
  if (!lunarisId.value) return
  try {
    await friend.sendRequest(lunarisId.value)
    ElMessage.success('申请已发送')
    lunarisId.value = ''
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '添加失败')
  }
}
async function removeFriend(f: any) {
  await friend.removeFriend(f.user_id)
}

function logout() {
  user.logoutServer()
  ws.disconnect()
  router.push('/login')
}

// ==================== 账户与安全（C 类接线） ====================
const showProfileDialog = ref(false)
const profileForm = ref({ nickname: '' })
const savingProfile = ref(false)
const showPwdDialog = ref(false)
const pwdForm = ref({ old_password: '', new_password: '' })
const savingPwd = ref(false)
const showBlockDialog = ref(false)
const showDeleteDialog = ref(false)
const deleting = ref(false)

function openEditProfile() {
  profileForm.value.nickname = user.user?.nickname || ''
  showProfileDialog.value = true
}
async function saveProfile() {
  savingProfile.value = true
  try {
    await user.updateProfile({ nickname: profileForm.value.nickname })
    ElMessage.success('资料已更新')
    showProfileDialog.value = false
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '资料更新失败')
  } finally {
    savingProfile.value = false
  }
}
async function savePassword() {
  if (!pwdForm.value.old_password || !pwdForm.value.new_password) {
    ElMessage.warning('请填写完整')
    return
  }
  savingPwd.value = true
  try {
    await user.changePassword(pwdForm.value.old_password, pwdForm.value.new_password)
    ElMessage.success('密码已修改，请重新登录')
    pwdForm.value = { old_password: '', new_password: '' }
    showPwdDialog.value = false
    logout()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '密码修改失败')
  } finally {
    savingPwd.value = false
  }
}
function isBlocked(userId: string) {
  return user.blocks.some((b: any) => (b.user_id ?? b.blocked_user_id) === userId)
}
async function toggleBlock(f: any) {
  try {
    if (isBlocked(f.user_id)) {
      await user.unblockUser(f.user_id)
      ElMessage.success('已解除屏蔽')
    } else {
      await user.blockUser(f.user_id)
      ElMessage.success('已屏蔽该用户')
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  }
}
async function openBlockDialog() {
  await user.fetchBlocks()
  showBlockDialog.value = true
}
async function unblock(b: any) {
  await user.unblockUser(b.user_id ?? b.blocked_user_id)
  ElMessage.success('已解除屏蔽')
}
async function downloadMyData() {
  try {
    const data = await user.exportData()
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = 'lunaris_my_data.json'
    a.click()
    URL.revokeObjectURL(a.href)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '数据导出失败')
  }
}
async function confirmDelete() {
  deleting.value = true
  try {
    await user.deleteAccount()
    ElMessage.success('账号已注销')
    ws.disconnect()
    router.push('/login')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '注销失败')
  } finally {
    deleting.value = false
  }
}

onMounted(async () => {
  // Initialize UI preferences
  ui.init()

  // Initialize clock
  updateClock()
  // Update clock every 60 seconds
  setInterval(() => updateClock(), 60000)

  await user.fetchMe()
  await user.fetchOnlineUsers()
  await chat.loadSouls()
  chat.loadFriends()
  loadFavorites()
  ws.connect(user.token)
  chat.initWs()
  group.initWs()
  moment.initWs()
})
</script>

<style scoped>
.main {
  display: flex;
  height: 100%;
  --bg-gradient: linear-gradient(135deg, #eef0f4 0%, #f7f8fa 100%);
}

.sidebar {
  width: 64px;
  background:
    linear-gradient(
      180deg,
      color-mix(in srgb, var(--companion-primary, #4a3658) 82%, #241c2c),
      color-mix(in srgb, var(--companion-primary, #4a3658) 58%, #241c2c)
    );
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 16px;
  gap: 6px;
  box-shadow: 2px 0 16px color-mix(in srgb, var(--companion-primary, #4a3658) 25%, transparent);
  transition: background 0.45s ease, box-shadow 0.45s ease;
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-btn);
  background: linear-gradient(
    135deg,
    var(--companion-secondary, var(--color-primary)) 0%,
    var(--companion-primary, var(--color-secondary)) 100%
  );
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  margin-bottom: 12px;
  box-shadow: var(--shadow-soft);
  transition: all 0.3s ease;
  font-weight: 600;
  font-size: 18px;
}

.avatar:hover {
  transform: scale(1.08);
  box-shadow: var(--shadow-medium);
}

.beijing-clock {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
  font-weight: 600;
  text-align: center;
  width: 100%;
  padding: 4px 0;
  margin-bottom: 8px;
  font-variant-numeric: tabular-nums;
}

.tab {
  width: 56px;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px 0;
  color: color-mix(in srgb, var(--companion-secondary, #d4a5d4) 70%, white 30%);
  cursor: pointer;
  border-radius: var(--radius-btn);
  transition: all 0.2s ease;
}

.tab .icon { font-size: 20px; }
.tab .label { font-size: 11px; margin-top: 2px; }

.tab:hover {
  color: #fff;
  background: color-mix(in srgb, var(--companion-secondary, #d4a5d4) 28%, transparent);
}

.tab.active {
  color: #fff;
  background: color-mix(in srgb, var(--companion-secondary, #d4a5d4) 38%, transparent);
  box-shadow: inset 3px 0 0 var(--companion-secondary, #d4a5d4);
}

.content {
  flex: 1;
  display: flex;
  overflow: hidden;
  background:
    radial-gradient(circle at 82% 0%, color-mix(in srgb, var(--companion-secondary, #cbd1dc) 14%, transparent), transparent 30%),
    var(--companion-page, #f3f5f7);
  transition: background 0.45s ease;
}

.chat-layout {
  flex: 1;
  display: flex;
  background: var(--companion-page, var(--bg-gradient));
  transition: background 0.45s ease;
}
.scroll-panel {
  flex: 1;
  overflow-y: auto;
  background:
    radial-gradient(circle at 82% 0%, color-mix(in srgb, var(--companion-secondary, #cbd1dc) 12%, transparent), transparent 28%),
    var(--companion-page, #f3f5f7);
  transition: background 0.45s ease;
}

.contacts-panel, .me-panel {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
  background:
    radial-gradient(circle at 85% 0%, color-mix(in srgb, var(--companion-secondary, #cbd1dc) 12%, transparent), transparent 28%),
    var(--companion-page, #f3f5f7);
  transition: background 0.45s ease;
}

.row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid color-mix(in srgb, var(--companion-primary, #cbd1dc) 12%, transparent);
  transition: all 0.2s ease;
}

.row:hover {
  background: color-mix(in srgb, var(--companion-secondary, #cbd1dc) 8%, transparent);
  border-radius: var(--radius-card);
  padding: 10px 8px;
}

.avatar-sm {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-card);
  background: linear-gradient(135deg, var(--companion-primary, var(--color-primary)) 0%, var(--companion-secondary, var(--color-secondary)) 100%);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-weight: 600;
  box-shadow: var(--shadow-soft);
}

.avatar-lg {
  width: 60px;
  height: 60px;
  border-radius: var(--radius-card);
  background: linear-gradient(135deg, var(--companion-primary, var(--color-primary)) 0%, var(--companion-secondary, var(--color-secondary)) 100%);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
  font-weight: 600;
  box-shadow: var(--shadow-medium);
}

.info { flex: 1; min-width: 0; }
.nm { font-size: 15px; color: var(--color-text-primary); font-weight: 600; }
.sub { font-size: 12px; color: var(--color-text-secondary); }
.friend-search { display: flex; gap: 8px; margin-bottom: 8px; }
.ask-box { display: flex; gap: 8px; margin-top: 12px; max-width: 480px; }
.answer {
  margin-top: 10px;
  background: rgba(255, 255, 255, 0.5);
  backdrop-filter: blur(10px);
  border-radius: var(--radius-card);
  padding: 12px;
  font-size: 14px;
  line-height: 1.6;
  max-width: 480px;
  border: 1px solid rgba(212, 165, 212, 0.1);
}

.section-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  max-width: 560px;
}

.favorites-list {
  max-width: 560px;
  border-top: 1px solid color-mix(in srgb, var(--companion-primary, #cbd1dc) 12%, transparent);
}

.favorite-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid color-mix(in srgb, var(--companion-primary, #cbd1dc) 12%, transparent);
}

.favorite-content {
  flex: 1;
  min-width: 0;
}

.favorite-text {
  color: var(--color-text-primary);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.favorite-meta {
  margin-top: 4px;
  color: var(--color-text-secondary);
  font-size: 12px;
}

.hint { color: var(--color-text-secondary); font-size: 12px; margin-left: 8px; }
.empty { color: var(--color-text-light); text-align: center; padding: 20px 0; font-size: 13px; }
.profile { display: flex; align-items: center; gap: 14px; margin-bottom: 16px; }
h3 { margin: 12px 0; color: var(--color-text-primary); font-weight: 600; }
h4 { margin: 10px 0; color: var(--color-text-secondary); }
</style>
