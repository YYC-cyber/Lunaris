<template>
  <div class="beijing-clock">
    <span class="clock-icon">🕐</span>
    <span class="time-text">{{ currentTime }}</span>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { formatBeijingClock } from '../../utils/time'

const currentTime = ref('00:00')
let timer: ReturnType<typeof setInterval> | null = null

function updateTime() {
  currentTime.value = formatBeijingClock()
}

onMounted(() => {
  updateTime()
  timer = setInterval(updateTime, 60000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.beijing-clock {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #666;
  padding: 8px 12px;
  background: #f5f5f5;
  border-radius: 4px;
  margin: 8px 0;
}

.clock-icon {
  font-size: 14px;
}

.time-text {
  font-family: 'Courier New', monospace;
  font-weight: 500;
}
</style>
