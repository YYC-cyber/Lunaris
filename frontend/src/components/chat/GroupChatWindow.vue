<template>
  <div class="group-chat-wrapper">
    <!-- 左侧：群列表 -->
    <div class="groups-list-panel" :style="{ width: `${leftPanelWidth}px` }">
      <div class="list-header">
        <h3>我的群聊</h3>
        <el-button
          circle
          type="primary"
          size="small"
          class="create-group-btn"
          aria-label="创建群聊"
          title="创建群聊"
          @click="creationModal?.open()"
        >
          <span class="create-group-plus">+</span>
        </el-button>
      </div>

      <!-- 群列表 -->
      <div class="groups-list">
        <div
          v-for="grp in groupStore.groups"
          :key="grp.id"
          :class="['group-item', { active: groupStore.currentGroupId === grp.id }]"
          @click="groupStore.selectGroup(grp.id)"
        >
          <div class="group-avatar">{{ grp.name[0] }}</div>
          <div class="group-info">
            <div class="group-name">{{ grp.name }}</div>
            <div class="group-type-badge">{{ getTypeLabel(grp.type) }}</div>
          </div>
        </div>

        <div v-if="groupStore.groups.length === 0" class="empty-groups">
          还没有群聊
        </div>
      </div>

      <!-- 待处理邀请 -->
      <div v-if="groupStore.pendingInvitations.length" class="invitations-section">
        <h4>待处理邀请</h4>
        <div
          v-for="inv in groupStore.pendingInvitations"
          :key="inv.id"
          class="invitation-item"
        >
          <div class="inv-title">{{ inv.group_name }}</div>
          <div class="inv-actions">
            <el-button
              size="small"
              type="primary"
              @click="groupStore.respondToInvitation(inv.id, true)"
            >
              接受
            </el-button>
            <el-button
              size="small"
              @click="groupStore.respondToInvitation(inv.id, false)"
            >
              拒绝
            </el-button>
          </div>
        </div>
      </div>
      <div class="panel-resizer left-resizer" @mousedown="startResize('left', $event)" />
    </div>

    <!-- 右侧：聊天窗口 -->
    <div class="messages-area">
      <div v-if="!currentGroup" class="empty-state">
        选择或创建一个群聊开始聊天
      </div>

      <template v-else>
        <!-- 消息列表 -->
        <div ref="messagesListRef" class="messages-list">
          <GroupMessageBubble
            v-for="(msg, index) in currentMessages"
            :key="msg.id"
            :message="msg"
            :show-time="shouldShowTime(index)"
          />
        </div>

        <!-- 输入框 -->
        <div class="input-area">
          <el-input
            v-model="inputText"
            placeholder="说点什么..."
            @keyup.enter="sendMessage"
            clearable
          />

          <el-button
            :type="recording ? 'danger' : 'default'"
            :loading="transcribingVoice"
            @click="toggleRecord"
          >
            {{ recording ? '停止录音' : '语音' }}
          </el-button>
          <el-button v-if="recordedVoiceBlob" type="success" @click="sendRecordedVoice">
            发送语音
          </el-button>
          <el-button v-if="recordedVoiceBlob" @click="cancelRecordedVoice">
            取消
          </el-button>

          <!-- @ 按钮 -->
          <el-popover
            placement="top"
            :width="250"
            trigger="click"
            v-model:visible="showMention"
          >
            <template #reference>
              <el-button icon="AtSymbol">@</el-button>
            </template>

            <!-- @ 成员列表 -->
            <div class="mention-list">
              <div
                v-for="member in currentGroup?.members || []"
                :key="member.id"
                @click="mentionMember(member)"
                class="mention-item"
              >
                <span>{{ member.name }}</span>
                <span class="member-type">{{ member.type === 'ai' ? '🤖' : '👤' }}</span>
              </div>
            </div>
          </el-popover>

          <!-- 发送按钮 -->
          <el-button type="primary" @click="sendMessage">发送</el-button>
        </div>
      </template>
    </div>

    <!-- 群信息面板 -->
    <aside v-if="showMemberSidebar" class="group-info-sidebar" :style="{ width: `${rightPanelWidth}px` }">
      <div v-if="currentGroup" class="group-header">
        <div>
          <h3>{{ currentGroup.name }}</h3>
          <span class="group-type">{{ getTypeLabel(currentGroup.type) }}</span>
        </div>
        <el-button text circle title="隐藏成员栏" aria-label="隐藏成员栏" @click="showMemberSidebar = false">×</el-button>
      </div>

      <!-- 成员列表 -->
      <div v-if="currentGroup" class="members-section">
        <div class="member-toolbar">
          <h4>成员 ({{ filteredMembers.length }})</h4>
          <div class="member-actions">
            <el-button text circle title="群管理" aria-label="群管理" @click="openGroupSettings">⚙</el-button>
            <el-button text circle title="添加成员" aria-label="添加成员" @click="openAddMember">+</el-button>
          </div>
        </div>
        <el-input v-model="memberSearch" size="small" clearable placeholder="搜索成员" />
        <div class="members-list">
          <div
            v-for="member in filteredMembers"
            :key="member.id"
            class="member-item"
          >
            <span class="member-icon">{{ member.type === 'ai' ? '🤖' : '👤' }}</span>
            <span class="member-name">{{ member.name }}</span>
            <span v-if="member.role === 'owner'" class="member-role">群主</span>
            <span v-else-if="member.role === 'admin'" class="member-role">管理员</span>
            <el-dropdown
              v-if="canManageMembers && member.role !== 'owner'"
              trigger="click"
              @command="(command: string) => handleMemberCommand(command, member)"
            >
              <el-button text circle class="member-more" aria-label="成员操作" title="成员操作">···</el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item
                    v-if="canManageRoles"
                    :command="member.role === 'admin' ? 'demote' : 'promote'"
                  >
                    {{ member.role === 'admin' ? '取消管理员' : '设为管理员' }}
                  </el-dropdown-item>
                  <el-dropdown-item
                    v-if="canManageRoles"
                    command="transfer"
                    divided
                  >转让群主</el-dropdown-item>
                  <el-dropdown-item
                    v-if="canManageMembers"
                    :command="isMuted(member) ? 'unmute' : 'mute'"
                  >
                    {{ isMuted(member) ? '解除禁言' : '禁言' }}
                  </el-dropdown-item>
                  <el-dropdown-item command="remove" divided>移出群聊</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </div>
      <p v-if="currentGroup?.announcement" class="group-announcement">
        {{ currentGroup.announcement }}
      </p>

      <!-- 邀请按钮 -->
      <el-button
        v-if="currentGroup && currentGroup.type !== 'ai_only'"
        @click="showInviteDialog = true"
        class="invite-btn"
      >
        + 邀请成员
      </el-button>
      <div class="panel-resizer right-resizer" @mousedown="startResize('right', $event)" />
    </aside>
    <el-button
      v-if="currentGroup && !showMemberSidebar"
      class="show-members-btn"
      circle
      title="显示成员栏"
      aria-label="显示成员栏"
      @click="showMemberSidebar = true"
    >☷</el-button>

    <!-- 邀请对话框 -->
    <el-dialog
      v-model="showInviteDialog"
      title="邀请成员"
      width="400px"
    >
      <div class="invite-form">
        <el-input
          v-model="inviteeId"
          placeholder="输入对方 lunaris_id"
          size="small"
        />
      </div>
      <template #footer>
        <el-button @click="showInviteDialog = false">取消</el-button>
        <el-button type="primary" @click="sendInvite">邀请</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showAddMemberDialog" title="添加群成员" width="420px">
      <el-radio-group v-model="addMemberType" class="member-type-tabs">
        <el-radio-button label="ai">AI 角色</el-radio-button>
        <el-radio-button label="human">真人用户</el-radio-button>
      </el-radio-group>
      <el-select v-if="addMemberType === 'ai'" v-model="selectedSoulId" placeholder="选择 AI 角色" style="width: 100%">
        <el-option v-for="soul in availableSouls" :key="soul.id" :label="soul.display_name" :value="soul.id" />
      </el-select>
      <el-input v-else v-model="addUserId" placeholder="输入用户 ID" />
      <template #footer>
        <el-button @click="showAddMemberDialog = false">取消</el-button>
        <el-button type="primary" @click="addMember">添加</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showGroupSettings" title="群管理" width="460px">
      <el-form label-width="82px">
        <el-form-item label="群聊名称">
          <el-input v-model="groupNameDraft" maxlength="100" show-word-limit />
        </el-form-item>
        <el-form-item label="群公告">
          <el-input v-model="announcementDraft" type="textarea" :rows="4" maxlength="500" show-word-limit />
        </el-form-item>
      </el-form>
      <div class="group-role-hint">
        群主可设置管理员；管理员可以协助邀请和移除成员。
      </div>
      <div class="group-admin-actions">
        <el-button size="small" @click="openAnnouncementManager">📢 公告管理</el-button>
        <el-button size="small" @click="openMemoryManager">🧠 群记忆</el-button>
        <el-button v-if="canManageRoles" size="small" @click="openPermissionManager">🛡 权限管理</el-button>
        <el-button size="small" type="danger" plain @click="handleLeaveGroup">🚪 退出群聊</el-button>
      </div>
      <template #footer>
        <el-button @click="showGroupSettings = false">取消</el-button>
        <el-button type="primary" @click="saveGroupSettings">保存</el-button>
      </template>
    </el-dialog>

    <!-- 公告管理对话框 -->
    <el-dialog v-model="showAnnouncementDialog" title="公告管理" width="460px">
      <div class="announcement-add">
        <el-input v-model="announcementDraft2" type="textarea" :rows="2" maxlength="500" show-word-limit placeholder="输入新公告内容" />
        <el-button type="primary" :disabled="!canManageRoles" @click="addAnnouncement">发布公告</el-button>
      </div>
      <div class="announcement-list">
        <div v-for="ann in announcements" :key="ann.id" class="ann-item">
          <span :class="['ann-pin', { pinned: ann.is_pinned }]">{{ ann.is_pinned ? '📌' : '' }}</span>
          <div class="ann-body">
            <div class="ann-content">{{ ann.content }}</div>
            <div class="ann-meta">{{ formatAnnTime(ann.created_at) }}</div>
          </div>
          <div class="ann-ops" v-if="canManageRoles || ann.created_by === userStore.user?.id">
            <el-button
              v-if="canManageRoles"
              size="small"
              text
              @click="toggleAnnPin(ann)"
            >{{ ann.is_pinned ? '取消置顶' : '置顶' }}</el-button>
            <el-button size="small" text type="danger" @click="removeAnnouncement(ann)">删除</el-button>
          </div>
        </div>
        <el-empty v-if="!announcements.length" description="暂无公告" :image-size="60" />
      </div>
    </el-dialog>

    <!-- 群记忆对话框 -->
    <el-dialog v-model="showMemoryDialog" title="群记忆" width="460px">
      <div class="memory-select">
        <span class="memory-label">AI 成员</span>
        <el-select v-model="memorySoulId" placeholder="选择 AI 成员" @change="loadMemories">
          <el-option v-for="ai in aiMembers" :key="ai.soul_id" :label="ai.name" :value="ai.soul_id" />
        </el-select>
      </div>
      <div v-if="memorySoulId" class="memory-add">
        <el-select v-model="memoryType" size="small" style="width: 128px">
          <el-option label="事件" value="event" />
          <el-option label="成员信息" value="member_info" />
          <el-option label="群规" value="group_rule" />
          <el-option label="话题" value="topic" />
        </el-select>
        <el-input v-model="memoryContent" size="small" placeholder="记忆内容" maxlength="500" />
        <el-button size="small" type="primary" @click="addMemory">添加</el-button>
      </div>
      <div class="memory-list">
        <div v-for="mem in memories" :key="mem.id" class="memory-item">
          <div class="memory-type">{{ mem.memory_type }}</div>
          <div class="memory-body">
            <div class="memory-content">{{ mem.content }}</div>
            <div class="memory-meta">{{ formatAnnTime(mem.created_at) }}</div>
          </div>
          <el-button v-if="canManageRoles" size="small" text type="danger" @click="removeMemory(mem)">删除</el-button>
        </div>
        <el-empty v-if="memorySoulId && !memories.length" description="暂无记忆" :image-size="60" />
      </div>
    </el-dialog>

    <!-- 权限管理对话框 -->
    <el-dialog v-model="showPermissionDialog" title="权限管理" width="480px">
      <div class="perm-role-tabs">
        <el-radio-group v-model="permissionRole" size="small">
          <el-radio-button label="admin">管理员</el-radio-button>
          <el-radio-button label="member">成员</el-radio-button>
          <el-radio-button label="guest">访客</el-radio-button>
        </el-radio-group>
      </div>
      <div class="perm-list" v-if="rolePermissions">
        <div v-for="perm in rolePermissions" :key="perm.key" class="perm-item">
          <span class="perm-name">{{ perm.label }}</span>
          <el-switch v-model="perm.value" :disabled="!canManageRoles" @change="onPermissionChange(perm.key, perm.value)" />
        </div>
      </div>
      <el-alert v-if="!canManageRoles" type="info" :closable="false" show-icon title="仅群主可修改权限" />
    </el-dialog>

    <!-- 禁言时长对话框 -->
    <el-dialog v-model="showMuteDialog" title="禁言成员" width="380px">
      <el-select v-model="muteMinutes" style="width: 100%">
        <el-option :label="'10 分钟'" :value="10" />
        <el-option :label="'30 分钟'" :value="30" />
        <el-option :label="'1 小时'" :value="60" />
        <el-option :label="'12 小时'" :value="720" />
        <el-option :label="'24 小时'" :value="1440" />
      </el-select>
      <template #footer>
        <el-button @click="showMuteDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmMute">确认禁言</el-button>
      </template>
    </el-dialog>

    <!-- 转让群主确认对话框 -->
    <el-dialog v-model="showTransferDialog" title="转让群主" width="380px">
      <p>确定将群主转让给 <b>{{ transferTarget?.name }}</b> 吗？转让后你将成为普通成员。</p>
      <template #footer>
        <el-button @click="showTransferDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmTransfer">确认转让</el-button>
      </template>
    </el-dialog>

    <!-- 创建群聊对话框 -->
    <GroupCreationModal ref="creationModal" @created="onGroupCreated" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useGroupStore } from '../../stores/group'
import { useChatStore } from '../../stores/chat'
import { useUserStore } from '../../stores/user'
import { formatRelativeTime } from '../../utils/time'
import { ElMessage } from 'element-plus'
import api from '../../utils/api'
import { cleanVoiceText, getAudioExtension } from '../../utils/voice'
import GroupCreationModal from './GroupCreationModal.vue'
import GroupMessageBubble from './GroupMessageBubble.vue'

const groupStore = useGroupStore()
const chatStore = useChatStore()
const userStore = useUserStore()
const creationModal = ref<InstanceType<typeof GroupCreationModal> | null>(null)

const inputText = ref('')
const recording = ref(false)
const recordedVoiceBlob = ref<Blob | null>(null)
const transcribingVoice = ref(false)
const showMention = ref(false)
const showInviteDialog = ref(false)
const inviteeId = ref('')
const leftPanelWidth = ref(220)
const rightPanelWidth = ref(280)
const showMemberSidebar = ref(true)
const memberSearch = ref('')
const showAddMemberDialog = ref(false)
const showGroupSettings = ref(false)
const addMemberType = ref<'ai' | 'human'>('ai')
const selectedSoulId = ref<number>()
const addUserId = ref('')
const resizing = ref<'left' | 'right' | null>(null)
const availableSouls = computed(() => chatStore.souls || [])

const currentGroup = computed(() => groupStore.currentGroup)
const currentMessages = computed(() => groupStore.currentMessages)
const messagesListRef = ref<HTMLElement | null>(null)
const filteredMembers = computed(() => {
  const keyword = memberSearch.value.trim().toLowerCase()
  const members = currentGroup.value?.members || []
  return keyword ? members.filter(member => member.name.toLowerCase().includes(keyword)) : members
})
const canManageRoles = computed(() => currentGroup.value?.creator_id === userStore.user?.id)
const canManageMembers = computed(() => {
  const currentUserId = userStore.user?.id
  return currentGroup.value?.creator_id === currentUserId ||
    currentGroup.value?.members.some(member => member.user_id === currentUserId && member.role === 'admin')
})

// ================== 批次3：群聊高级能力 ==================
// 公告管理
const showAnnouncementDialog = ref(false)
const announcementDraft2 = ref('')
const announcements = ref<any[]>([])
// 群记忆
const showMemoryDialog = ref(false)
const memorySoulId = ref<number>()
const memoryType = ref('event')
const memoryContent = ref('')
const memories = ref<any[]>([])
// 权限管理
const showPermissionDialog = ref(false)
const permissionRole = ref('member')
const rolePermissions = ref<any[]>([])
const permissionRoleMap: Record<string, any> = {}
// 禁言
const showMuteDialog = ref(false)
const muteMinutes = ref(30)
const muteTarget = ref<any>(null)
const mutedUserIds = ref<string[]>([])
const isMuted = (member: any) => !!member.user_id && mutedUserIds.value.includes(String(member.user_id))
// 转让群主
const showTransferDialog = ref(false)
const transferTarget = ref<any>(null)

const aiMembers = computed(() => (currentGroup.value?.members || []).filter(m => m.type === 'ai'))
const isOwner = computed(() => currentGroup.value?.creator_id === userStore.user?.id)

const PERMISSION_LABELS: Record<string, string> = {
  can_invite: '邀请成员',
  can_kick: '移除成员',
  can_edit_info: '编辑群资料',
  can_delete_messages: '删除他人消息',
  can_pin: '置顶公告',
  can_manage_roles: '管理角色',
}

function formatAnnTime(iso: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

// ---- 公告 ----
async function openAnnouncementManager() {
  await loadAnnouncements()
  showAnnouncementDialog.value = true
}
async function loadAnnouncements() {
  if (!currentGroup.value) return
  announcements.value = await groupStore.listAnnouncements(currentGroup.value.id)
}
async function addAnnouncement() {
  if (!currentGroup.value || !announcementDraft2.value.trim()) return
  try {
    await groupStore.createAnnouncement(currentGroup.value.id, announcementDraft2.value.trim())
    announcementDraft2.value = ''
    await loadAnnouncements()
    ElMessage.success('公告已发布')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '发布公告失败')
  }
}
async function removeAnnouncement(ann: any) {
  if (!currentGroup.value) return
  try {
    await groupStore.deleteAnnouncement(currentGroup.value.id, ann.id)
    await loadAnnouncements()
    ElMessage.success('公告已删除')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '删除公告失败')
  }
}
async function toggleAnnPin(ann: any) {
  if (!currentGroup.value) return
  try {
    await groupStore.toggleAnnouncementPin(currentGroup.value.id, ann.id, !ann.is_pinned)
    await loadAnnouncements()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '置顶操作失败')
  }
}

// ---- 群记忆 ----
async function openMemoryManager() {
  memorySoulId.value = aiMembers.value[0]?.soul_id
  memoryType.value = 'event'
  memoryContent.value = ''
  memories.value = []
  if (memorySoulId.value) await loadMemories()
  showMemoryDialog.value = true
}
async function loadMemories() {
  if (!currentGroup.value || !memorySoulId.value) { memories.value = []; return }
  memories.value = await groupStore.listMemories(currentGroup.value.id, memorySoulId.value)
}
async function addMemory() {
  if (!currentGroup.value || !memorySoulId.value || !memoryContent.value.trim()) return
  try {
    await groupStore.addMemory(currentGroup.value.id, memorySoulId.value, memoryType.value, memoryContent.value.trim())
    memoryContent.value = ''
    await loadMemories()
    ElMessage.success('记忆已添加')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '添加记忆失败')
  }
}
async function removeMemory(mem: any) {
  if (!currentGroup.value || !memorySoulId.value) return
  try {
    await groupStore.deleteMemory(currentGroup.value.id, memorySoulId.value, mem.id)
    await loadMemories()
    ElMessage.success('记忆已删除')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '删除记忆失败')
  }
}

// ---- 权限 ----
async function openPermissionManager() {
  if (!currentGroup.value) return
  await loadPermissions()
  showPermissionDialog.value = true
}
async function loadPermissions() {
  if (!currentGroup.value) return
  const perms: any[] = await groupStore.listPermissions(currentGroup.value.id)
  for (const p of perms) permissionRoleMap[p.role] = p
  await applyPermissionRole(permissionRole.value)
}
async function applyPermissionRole(role: string) {
  permissionRole.value = role
  const p = permissionRoleMap[role]
  rolePermissions.value = p ? [
    { key: 'can_invite', label: PERMISSION_LABELS.can_invite, value: p.can_invite },
    { key: 'can_kick', label: PERMISSION_LABELS.can_kick, value: p.can_kick },
    { key: 'can_edit_info', label: PERMISSION_LABELS.can_edit_info, value: p.can_edit_info },
    { key: 'can_delete_messages', label: PERMISSION_LABELS.can_delete_messages, value: p.can_delete_messages },
    { key: 'can_pin', label: PERMISSION_LABELS.can_pin, value: p.can_pin },
    { key: 'can_manage_roles', label: PERMISSION_LABELS.can_manage_roles, value: p.can_manage_roles },
  ] : []
}
async function onPermissionChange(key: string, value: boolean) {
  if (!currentGroup.value || !isOwner.value) return
  try {
    await groupStore.updateRolePermissions(currentGroup.value.id, permissionRole.value, { [key]: value })
    await loadPermissions()
  } catch (e: any) {
    await applyPermissionRole(permissionRole.value)
    ElMessage.error(e?.response?.data?.detail || '权限更新失败')
  }
}
watch(permissionRole, (role) => applyPermissionRole(role))

// ---- 退群 ----
async function handleLeaveGroup() {
  if (!currentGroup.value) return
  try {
    await groupStore.leaveGroup(currentGroup.value.id)
    showGroupSettings.value = false
    ElMessage.success('已退出群聊')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '退出群聊失败')
  }
}

// ---- 禁言 ----
async function refreshMutedUsers() {
  if (!currentGroup.value) return
  try {
    const users: any[] = await groupStore.listMutedUsers(currentGroup.value.id)
    mutedUserIds.value = users.map(u => String(u.user_id || u.id))
  } catch {
    mutedUserIds.value = []
  }
}
function toggleMute(member: any) {
  muteTarget.value = member
  muteMinutes.value = 30
  showMuteDialog.value = true
}
async function confirmMute() {
  if (!currentGroup.value || !muteTarget.value) return
  try {
    await groupStore.muteMember(currentGroup.value.id, muteTarget.value.user_id, muteMinutes.value)
    showMuteDialog.value = false
    await refreshMutedUsers()
    ElMessage.success('已禁言')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '禁言失败')
  }
}
async function confirmUnmute(member: any) {
  if (!currentGroup.value) return
  try {
    await groupStore.unmuteMember(currentGroup.value.id, member.user_id)
    await refreshMutedUsers()
    ElMessage.success('已解除禁言')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '解除禁言失败')
  }
}

// ---- 转让群主 ----
function transferOwner(member: any) {
  transferTarget.value = member
  showTransferDialog.value = true
}
async function confirmTransfer() {
  if (!currentGroup.value || !transferTarget.value) return
  try {
    await groupStore.transferOwner(currentGroup.value.id, transferTarget.value.id)
    showTransferDialog.value = false
    await groupStore.refreshGroup(currentGroup.value.id)
    ElMessage.success('群主已转让')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '转让失败')
  }
}

let mediaStream: MediaStream | null = null
let audioContext: AudioContext | null = null
let audioSource: MediaStreamAudioSourceNode | null = null
let audioProcessor: ScriptProcessorNode | null = null
let pcmChunks: Float32Array[] = []
let recordingSampleRate = 44100

function getTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    'ai_only': 'AI',
    'human_only': '真人',
    'mixed': '混合',
  }
  return labels[type] || type
}

function formatTime(isoString: string): string {
  return formatRelativeTime(isoString)
}

function shouldShowTime(index: number): boolean {
  if (index === 0) return true
  const current = currentMessages.value[index]
  const prev = currentMessages.value[index - 1]
  if (!current || !prev) return true
  const currentTime = new Date(current.created_at).getTime()
  const prevTime = new Date(prev.created_at).getTime()
  return (currentTime - prevTime) > 5 * 60 * 1000 // 5 分钟
}

async function sendMessage() {
  if (!inputText.value.trim() || !currentGroup.value) return

  try {
    const mentionedUserIds = extractMentions(inputText.value)
    await groupStore.sendMessageWithMentions(currentGroup.value.id, inputText.value, mentionedUserIds)
    inputText.value = ''
    scrollMessagesToBottom()
  } catch (e) {
    ElMessage.error('发送失败')
  }
}

async function toggleRecord() {
  if (recording.value) {
    recording.value = false
    audioProcessor?.disconnect()
    audioSource?.disconnect()
    mediaStream?.getTracks().forEach((track) => track.stop())
    audioProcessor = null
    audioSource = null
    audioContext?.close()
    audioContext = null
    await onRecordStop()
    return
  }

  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true })
    audioContext = new AudioContext()
    recordingSampleRate = audioContext.sampleRate
    audioSource = audioContext.createMediaStreamSource(mediaStream)
    audioProcessor = audioContext.createScriptProcessor(4096, 1, 1)
    pcmChunks = []
    audioProcessor.onaudioprocess = (event) => {
      pcmChunks.push(new Float32Array(event.inputBuffer.getChannelData(0)))
    }
    audioSource.connect(audioProcessor)
    audioProcessor.connect(audioContext.destination)
    recording.value = true
  } catch {
    mediaStream?.getTracks().forEach((track) => track.stop())
    audioContext?.close()
    mediaStream = null
    audioContext = null
    ElMessage.error('无法访问麦克风，请检查权限')
  }
}

async function onRecordStop() {
  if (!pcmChunks.length) return
  const blob = encodeWav(pcmChunks, recordingSampleRate)
  try {
    transcribingVoice.value = true
    const form = new FormData()
    form.append('file', blob, 'voice.wav')
    const response: any = await api.post('/api/voice/transcribe', form)
    const transcribedText = cleanVoiceText(response?.text)
    if (!transcribedText) {
      ElMessage.warning('未识别到内容')
      recordedVoiceBlob.value = null
      return
    }
    inputText.value = transcribedText
    recordedVoiceBlob.value = blob
    ElMessage.success(`识别成功：${transcribedText}`)
  } catch (error: any) {
    recordedVoiceBlob.value = null
    ElMessage.error(error?.response?.data?.detail || '语音转写失败')
  } finally {
    transcribingVoice.value = false
  }
}

function encodeWav(chunks: Float32Array[], sampleRate: number): Blob {
  const sampleCount = chunks.reduce((total, chunk) => total + chunk.length, 0)
  const buffer = new ArrayBuffer(44 + sampleCount * 2)
  const view = new DataView(buffer)
  const writeString = (offset: number, value: string) => {
    for (let index = 0; index < value.length; index++) view.setUint8(offset + index, value.charCodeAt(index))
  }
  writeString(0, 'RIFF')
  view.setUint32(4, 36 + sampleCount * 2, true)
  writeString(8, 'WAVE')
  writeString(12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, 1, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * 2, true)
  view.setUint16(32, 2, true)
  view.setUint16(34, 16, true)
  writeString(36, 'data')
  view.setUint32(40, sampleCount * 2, true)
  let offset = 44
  for (const chunk of chunks) {
    for (const sample of chunk) {
      const clamped = Math.max(-1, Math.min(1, sample))
      view.setInt16(offset, clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff, true)
      offset += 2
    }
  }
  return new Blob([buffer], { type: 'audio/wav' })
}

function cancelRecordedVoice() {
  recordedVoiceBlob.value = null
  inputText.value = ''
}

async function sendRecordedVoice() {
  if (!currentGroup.value || !recordedVoiceBlob.value || !inputText.value.trim()) {
    ElMessage.warning('内容不能为空')
    return
  }
  try {
    const form = new FormData()
    form.append('file', recordedVoiceBlob.value, `voice.${getAudioExtension(recordedVoiceBlob.value)}`)
    const uploadResponse: any = await api.post('/api/upload/voice', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    const voiceUrl = uploadResponse?.data?.url || uploadResponse?.url
    if (!voiceUrl) throw new Error('语音上传失败')

    const mentionedUserIds = extractMentions(inputText.value)
    await groupStore.sendMessageWithMentions(
      currentGroup.value.id,
      inputText.value,
      mentionedUserIds,
      voiceUrl,
    )
    inputText.value = ''
    recordedVoiceBlob.value = null
    scrollMessagesToBottom()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '发送语音失败')
  }
}

function scrollMessagesToBottom() {
  nextTick(() => {
    const container = messagesListRef.value
    if (container) container.scrollTop = container.scrollHeight
  })
}

watch(
  () => [groupStore.currentGroupId, currentMessages.value.length],
  () => scrollMessagesToBottom(),
  { flush: 'post' },
)

watch(
  () => groupStore.currentGroupId,
  () => refreshMutedUsers(),
)

function extractMentions(content: string): string[] {
  const matches = content.match(/@([^\s@]+)/g) || []
  return matches.map((m) => {
    const mentioned = currentGroup.value?.members?.find((member) => member.name === m.slice(1))
    const mentionedId = mentioned?.type === 'ai'
      ? mentioned.soul_id
      : mentioned?.user_id
    return mentionedId?.toString() || m.slice(1)
  }).filter(Boolean)
}

function mentionMember(member: any) {
  inputText.value += `@${member.name} `
  showMention.value = false
}

async function sendInvite() {
  if (!inviteeId.value.trim() || !currentGroup.value) return

  try {
    await groupStore.inviteMember(currentGroup.value.id, inviteeId.value)
    ElMessage.success('邀请已发送')
    showInviteDialog.value = false
    inviteeId.value = ''
  } catch (e) {
    ElMessage.error('邀请失败')
  }
}

function onGroupCreated(groupId: number) {
  groupStore.selectGroup(groupId)
}

function startResize(panel: 'left' | 'right', event: MouseEvent) {
  resizing.value = panel
  document.body.style.userSelect = 'none'
  window.addEventListener('mousemove', resizePanel)
  window.addEventListener('mouseup', stopResize)
  event.preventDefault()
}

function resizePanel(event: MouseEvent) {
  if (resizing.value === 'left') leftPanelWidth.value = Math.min(360, Math.max(180, event.clientX - 136))
  if (resizing.value === 'right') rightPanelWidth.value = Math.min(420, Math.max(220, window.innerWidth - event.clientX))
}

function stopResize() {
  resizing.value = null
  document.body.style.userSelect = ''
  window.removeEventListener('mousemove', resizePanel)
  window.removeEventListener('mouseup', stopResize)
}

function openAddMember() {
  showAddMemberDialog.value = true
}

const groupNameDraft = ref('')
const announcementDraft = ref('')

function openGroupSettings() {
  if (!currentGroup.value) return
  groupNameDraft.value = currentGroup.value.name
  announcementDraft.value = currentGroup.value.announcement || ''
  showGroupSettings.value = true
}

async function saveGroupSettings() {
  if (!currentGroup.value) return
  try {
    await groupStore.updateGroupSettings(currentGroup.value.id, {
      groupName: groupNameDraft.value,
      announcement: announcementDraft.value,
    })
    ElMessage.success('群资料已更新')
    showGroupSettings.value = false
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '群资料更新失败')
  }
}

async function addMember() {
  if (!currentGroup.value) return
  try {
    await groupStore.addMember(currentGroup.value.id, addMemberType.value, {
      soulId: selectedSoulId.value,
      userId: addUserId.value.trim() || undefined,
    })
    ElMessage.success('成员已添加')
    showAddMemberDialog.value = false
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '添加成员失败')
  }
}

async function handleMemberCommand(command: string, member: any) {
  if (!currentGroup.value) return
  if (command === 'remove') {
    try {
      await groupStore.removeMember(currentGroup.value.id, member.id)
      ElMessage.success('成员已移除')
    } catch (error: any) {
      ElMessage.error(error?.response?.data?.detail || '移除成员失败')
    }
  } else if (command === 'promote' || command === 'demote') {
    try {
      await groupStore.updateMember(
        currentGroup.value.id,
        member.id,
        command === 'promote' ? 'admin' : 'member',
      )
      ElMessage.success(command === 'promote' ? '已设为管理员' : '已取消管理员')
    } catch (error: any) {
      ElMessage.error(error?.response?.data?.detail || '管理员设置失败')
    }
  } else if (command === 'transfer') {
    transferOwner(member)
  } else if (command === 'mute') {
    toggleMute(member)
  } else if (command === 'unmute') {
    confirmUnmute(member)
  }
}

onMounted(() => {
  groupStore.loadGroups()
  groupStore.loadPendingInvitations()
})

onUnmounted(() => {
  stopResize()
  mediaStream?.getTracks().forEach((track) => track.stop())
  audioProcessor?.disconnect()
  audioSource?.disconnect()
  audioContext?.close()
})
</script>

<style scoped>
.group-chat-wrapper {
  display: flex;
  height: 100%;
  gap: 12px;
  min-width: 0;
  position: relative;
}

.groups-list-panel {
  position: relative;
  flex: 0 0 auto;
  background: rgba(255, 255, 255, 0.3);
  border-radius: var(--radius-card);
  padding: 12px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(212, 165, 212, 0.1);
}

.list-header h3 {
  margin: 0;
  font-size: 16px;
}

.create-group-btn {
  width: 34px;
  height: 34px;
  padding: 0;
  border: 0;
  box-shadow: 0 6px 14px rgba(112, 78, 160, 0.2);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.create-group-btn:hover {
  transform: rotate(90deg) scale(1.08);
  box-shadow: 0 8px 18px rgba(112, 78, 160, 0.3);
}

.create-group-plus {
  display: block;
  font-size: 24px;
  font-weight: 300;
  line-height: 1;
  transition: transform 0.2s ease;
}

.groups-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 200px;
}

.group-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  background: rgba(212, 165, 212, 0.05);
}

.group-item:hover {
  background: rgba(212, 165, 212, 0.1);
}

.group-item.active {
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-secondary) 100%);
  color: white;
}

.group-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: rgba(212, 165, 212, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 16px;
  flex-shrink: 0;
}

.group-item.active .group-avatar {
  background: rgba(255, 255, 255, 0.3);
}

.group-info {
  flex: 1;
  min-width: 0;
}

.group-name {
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.group-type-badge {
  font-size: 10px;
  color: var(--color-text-light);
  margin-top: 2px;
}

.empty-groups {
  text-align: center;
  color: var(--color-text-light);
  font-size: 12px;
  padding: 20px;
}

.invitations-section {
  border-top: 1px solid rgba(212, 165, 212, 0.1);
  padding-top: 12px;
}

.invitations-section h4 {
  margin: 0 0 8px 0;
  font-size: 12px;
  color: var(--color-text-light);
  text-transform: uppercase;
}

.invitation-item {
  background: rgba(255, 200, 124, 0.1);
  border: 1px solid rgba(255, 200, 124, 0.2);
  padding: 8px;
  border-radius: 6px;
  margin-bottom: 6px;
}

.inv-title {
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 6px;
}

.inv-actions {
  display: flex;
  gap: 6px;
}

.inv-actions :deep(.el-button) {
  flex: 1;
}

.messages-area {
  flex: 1;
  min-width: 320px;
  display: flex;
  flex-direction: column;
  background: rgba(255, 255, 255, 0.3);
  border-radius: var(--radius-card);
  overflow: hidden;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--color-text-light);
  font-size: 14px;
}

.messages-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.msg-item {
  display: flex;
  gap: 8px;
  padding: 8px;
  border-radius: var(--radius-card);
  background: rgba(255, 255, 255, 0.5);
}

.msg-item.user {
  justify-content: flex-end;
  background: rgba(212, 165, 212, 0.1);
}

.msg-item.ai {
  justify-content: flex-start;
}

.sender-info {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--color-text-secondary);
  min-width: 100px;
}

.sender-name {
  font-weight: 600;
}

.sender-type {
  font-size: 14px;
}

.msg-content {
  flex: 1;
  max-width: 60%;
}

.voice-bubble {
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-secondary) 100%);
  border-radius: var(--radius-bubble);
  padding: 8px;
  color: white;
}

.text-bubble {
  background: rgba(212, 165, 212, 0.15);
  border: 1px solid rgba(212, 165, 212, 0.2);
  border-radius: var(--radius-bubble);
  padding: 10px 14px;
  word-wrap: break-word;
  line-height: 1.4;
}

.msg-time {
  font-size: 11px;
  color: var(--color-text-light);
  white-space: nowrap;
}

.input-area {
  display: flex;
  gap: 8px;
  padding: 12px;
  border-top: 1px solid rgba(212, 165, 212, 0.1);
}

.input-area :deep(.el-input) {
  flex: 1;
}

.mention-list {
  max-height: 300px;
  overflow-y: auto;
}

.mention-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px;
  cursor: pointer;
  border-radius: 4px;
  transition: background 0.2s;
}

.mention-item:hover {
  background: rgba(212, 165, 212, 0.1);
}

.member-type {
  font-size: 12px;
  color: var(--color-text-light);
}

.group-info-sidebar {
  position: relative;
  flex: 0 0 auto;
  background: rgba(255, 255, 255, 0.3);
  border-radius: var(--radius-card);
  padding: 16px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.group-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  border-bottom: 1px solid rgba(212, 165, 212, 0.1);
  padding-bottom: 12px;
}

.group-header h3 {
  margin: 0 0 4px 0;
  font-size: 16px;
}

.group-type {
  font-size: 12px;
  color: var(--color-primary);
}

.members-section h4 {
  margin: 0;
  font-size: 13px;
  text-transform: uppercase;
  color: var(--color-text-light);
}

.member-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.member-actions {
  display: flex;
  gap: 2px;
}

.member-item {
  min-height: 34px;
}

.member-more {
  opacity: 0;
  transition: opacity 0.15s ease;
}

.member-item:hover .member-more {
  opacity: 1;
}

.panel-resizer {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 8px;
  cursor: col-resize;
  z-index: 3;
}

.panel-resizer::after {
  content: '';
  position: absolute;
  top: 40%;
  bottom: 40%;
  left: 3px;
  width: 2px;
  border-radius: 2px;
  background: rgba(112, 78, 160, 0.18);
  transition: background 0.15s ease, transform 0.15s ease;
}

.panel-resizer:hover::after {
  background: var(--color-primary);
  transform: scaleY(1.4);
}

.left-resizer {
  right: -10px;
}

.right-resizer {
  left: -10px;
}

.show-members-btn {
  position: absolute;
  right: 12px;
  top: 12px;
  z-index: 4;
}

.member-type-tabs {
  display: flex;
  margin-bottom: 16px;
}

.members-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.member-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px;
  border-radius: 4px;
  font-size: 13px;
  background: rgba(212, 165, 212, 0.05);
}

.member-icon {
  font-size: 16px;
}

.member-name {
  flex: 1;
}

.member-role {
  flex: 0 0 auto;
  color: var(--color-primary);
  font-size: 11px;
}

.group-announcement {
  margin: -4px 0 0;
  padding: 10px;
  border-left: 3px solid var(--color-primary);
  background: rgba(212, 165, 212, 0.08);
  color: var(--color-text-secondary);
  font-size: 12px;
  line-height: 1.5;
}

.invite-btn {
  width: 100%;
}

.invite-form :deep(.el-input) {
  margin-bottom: 12px;
}

/* ================== 批次3：群聊高级能力样式 ================== */

.group-admin-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(212, 165, 212, 0.12);
}

/* 公告 */
.announcement-add {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.announcement-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 320px;
  overflow-y: auto;
}

.ann-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px;
  background: rgba(212, 165, 212, 0.06);
  border-radius: 6px;
  border: 1px solid transparent;
}

.ann-item:has(.ann-pin.pinned) {
  border-color: rgba(212, 165, 212, 0.35);
}

.ann-pin {
  width: 18px;
  flex: 0 0 auto;
  font-size: 14px;
}

.ann-body {
  flex: 1;
  min-width: 0;
}

.ann-content {
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

.ann-meta {
  font-size: 11px;
  color: var(--color-text-light);
  margin-top: 4px;
}

.ann-ops {
  display: flex;
  flex-direction: column;
  flex: 0 0 auto;
  gap: 2px;
}

/* 群记忆 */
.memory-select {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.memory-label {
  font-size: 13px;
  color: var(--color-text-secondary);
  flex: 0 0 auto;
}

.memory-select :deep(.el-select) {
  flex: 1;
}

.memory-add {
  display: flex;
  gap: 6px;
  margin-bottom: 12px;
}

.memory-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 280px;
  overflow-y: auto;
}

.memory-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px;
  background: rgba(212, 165, 212, 0.06);
  border-radius: 6px;
}

.memory-type {
  flex: 0 0 auto;
  font-size: 11px;
  color: var(--color-primary);
  background: color-mix(in srgb, var(--color-primary) 14%, transparent);
  padding: 2px 8px;
  border-radius: 10px;
}

.memory-body {
  flex: 1;
  min-width: 0;
}

.memory-content {
  font-size: 13px;
  line-height: 1.5;
  word-break: break-word;
}

.memory-meta {
  font-size: 11px;
  color: var(--color-text-light);
  margin-top: 4px;
}

/* 权限 */
.perm-role-tabs {
  margin-bottom: 14px;
}

.perm-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.perm-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  background: rgba(212, 165, 212, 0.06);
  border-radius: 6px;
}

.perm-name {
  font-size: 13px;
}
</style>
