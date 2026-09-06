<template>
  <div v-if="Array.from(typingUsers.values()).length > 0" class="typing-indicator">
    <div class="typing-text">
      {{ typingText }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { wsClient } from '../../utils/ws'

interface TypingUser {
  user_id: string
  username: string
}

const typingUsers = ref<Map<string, TypingUser>>(new Map())
const timeouts = ref<Map<string, number>>(new Map())

wsClient.on('typing_start', (e: any) => {
  const data = e?.data || {}
  const userId = data.user_id
  const username = data.username

  if (!userId) return

  // Clear existing timeout for this user
  const existingTimeout = timeouts.value.get(userId)
  if (existingTimeout) clearTimeout(existingTimeout)

  // Add or update user
  typingUsers.value.set(userId, { user_id: userId, username: username || 'Unknown' })

  // Set timeout to auto-remove after 5 seconds
  const newTimeout = window.setTimeout(() => {
    typingUsers.value.delete(userId)
    timeouts.value.delete(userId)
  }, 5000)

  timeouts.value.set(userId, newTimeout)
})

wsClient.on('typing_stop', (e: any) => {
  const data = e?.data || {}
  const userId = data.user_id

  if (!userId) return

  // Clear timeout and remove user
  const timeout = timeouts.value.get(userId)
  if (timeout) clearTimeout(timeout)

  typingUsers.value.delete(userId)
  timeouts.value.delete(userId)
})

const typingText = computed(() => {
  const users = Array.from(typingUsers.value.values())
  if (users.length === 0) return ''
  if (users.length === 1) return `${users[0].username} 正在输入...`
  if (users.length === 2) return `${users[0].username} 和 ${users[1].username} 正在输入...`
  return `${users.length} 人正在输入...`
})
</script>

<style scoped>
.typing-indicator {
  padding: 8px 12px;
  margin: 8px 0;
}

.typing-text {
  font-size: 12px;
  color: var(--color-text-light);
  font-style: italic;
}
</style>
