<template>
  <el-dialog
    v-model="visible"
    title="创建群聊"
    width="500px"
    @close="resetForm"
  >
    <div class="creation-form">
      <!-- 群名称 -->
      <el-form-item label="群聊名称" required>
        <el-input
          v-model="form.groupName"
          placeholder="给你的群聊起个名字"
          size="small"
        />
      </el-form-item>

      <!-- 群类型 -->
      <el-form-item label="聊天类型" required>
        <el-select v-model="form.groupType" size="small">
          <el-option label="AI 多人聊天" value="ai_only" />
          <el-option label="真人群聊" value="human_only" />
          <el-option label="AI + 真人混合" value="mixed" />
        </el-select>
      </el-form-item>

      <!-- AI 成员选择 -->
      <div v-if="form.groupType !== 'human_only'" class="section">
        <h4>选择 AI 成员</h4>
        <div class="ai-members">
          <div
            v-for="soul in availableSouls"
            :key="soul.id"
            class="member-card"
            :class="{ selected: form.aiSoulIds.includes(soul.id) }"
            @click="toggleAISoul(soul.id)"
          >
            <div class="avatar">{{ soul.display_name[0] }}</div>
            <div class="name">{{ soul.display_name }}</div>
          </div>
        </div>
      </div>

      <!-- 真人成员邀请 -->
      <div v-if="form.groupType !== 'ai_only'" class="section">
        <h4>邀请真人好友</h4>
        <div class="human-members">
          <div
            v-for="friend in availableFriends"
            :key="friend.user_id"
            class="friend-card"
            :class="{ selected: form.humanUserIds.includes(friend.user_id) }"
            @click="toggleFriend(friend.user_id)"
          >
            <div class="avatar">👤</div>
            <div class="name">{{ friend.nickname || friend.lunaris_id }}</div>
          </div>
        </div>
      </div>

      <!-- 隐私设置（只有真人群才有） -->
      <div v-if="form.groupType !== 'ai_only'" class="section">
        <h4>隐私设置</h4>
        <el-form-item>
          <el-checkbox v-model="form.enableAutoDelete">
            自动删除消息（
            <el-input-number
              v-model="form.autoDeleteHours"
              :min="1"
              :max="720"
              size="small"
              style="width: 80px"
            />
            小时后）
          </el-checkbox>
        </el-form-item>
      </div>
    </div>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="isCreating" @click="createGroup">
        创建
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useGroupStore } from '../../stores/group'
import { useChatStore } from '../../stores/chat'
import { useFriendStore } from '../../stores/friend'

const emit = defineEmits<{
  created: [groupId: number]
}>()

const groupStore = useGroupStore()
const chatStore = useChatStore()
const friendStore = useFriendStore()

const visible = ref(false)
const isCreating = ref(false)

const form = ref({
  groupName: '',
  groupType: 'ai_only' as 'ai_only' | 'human_only' | 'mixed',
  aiSoulIds: [] as number[],
  humanUserIds: [] as string[],
  enableAutoDelete: false,
  autoDeleteHours: 24,
})

const availableSouls = computed(() => chatStore.souls || [])
const availableFriends = computed(() => friendStore.friends || [])

function toggleAISoul(soulId: number) {
  const index = form.value.aiSoulIds.indexOf(soulId)
  if (index > -1) {
    form.value.aiSoulIds.splice(index, 1)
  } else {
    form.value.aiSoulIds.push(soulId)
  }
}

function toggleFriend(userId: string) {
  const index = form.value.humanUserIds.indexOf(userId)
  if (index > -1) {
    form.value.humanUserIds.splice(index, 1)
  } else {
    form.value.humanUserIds.push(userId)
  }
}

async function createGroup() {
  if (!form.value.groupName.trim()) {
    ElMessage.warning('请输入群聊名称')
    return
  }

  if (
    form.value.groupType === 'ai_only' &&
    form.value.aiSoulIds.length === 0
  ) {
    ElMessage.warning('请至少选择一个 AI 成员')
    return
  }

  if (
    form.value.groupType === 'mixed' &&
    (form.value.aiSoulIds.length === 0 || form.value.humanUserIds.length === 0)
  ) {
    ElMessage.warning('混合群聊需要至少一个 AI 和一个真人')
    return
  }

  try {
    isCreating.value = true
    const res = await groupStore.createGroup(
      form.value.groupName,
      form.value.groupType,
      form.value.aiSoulIds.length > 0 ? form.value.aiSoulIds : undefined,
      form.value.humanUserIds.length > 0 ? form.value.humanUserIds : undefined,
      form.value.enableAutoDelete ? form.value.autoDeleteHours : undefined
    )
    ElMessage.success('群聊创建成功')
    emit('created', res.id)
    visible.value = false
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '创建失败，请稍后重试')
  } finally {
    isCreating.value = false
  }
}

function resetForm() {
  form.value = {
    groupName: '',
    groupType: 'ai_only',
    aiSoulIds: [],
    humanUserIds: [],
    enableAutoDelete: false,
    autoDeleteHours: 24,
  }
}

function open() {
  visible.value = true
}

defineExpose({ open })
</script>

<style scoped>
.creation-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.section {
  border-top: 1px solid rgba(212, 165, 212, 0.1);
  padding-top: 12px;
}

.section h4 {
  margin: 0 0 12px 0;
  font-size: 13px;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--color-text-light);
}

.ai-members,
.human-members {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 8px;
}

.member-card,
.friend-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 10px;
  border-radius: 8px;
  cursor: pointer;
  border: 2px solid transparent;
  transition: all 0.2s;
  background: rgba(212, 165, 212, 0.05);
}

.member-card:hover,
.friend-card:hover {
  background: rgba(212, 165, 212, 0.1);
  transform: scale(1.05);
}

.member-card.selected,
.friend-card.selected {
  background: rgba(212, 165, 212, 0.2);
  border-color: var(--color-primary);
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-secondary) 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: bold;
  font-size: 18px;
}

.name {
  font-size: 12px;
  text-align: center;
  word-break: break-all;
}
</style>
