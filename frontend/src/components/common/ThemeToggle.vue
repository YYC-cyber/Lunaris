<template>
  <el-button text @click="toggleTheme" :title="currentTheme === 'light' ? '深色模式' : '浅色模式'">
    <span class="theme-icon">{{ currentTheme === 'light' ? '🌙' : '☀️' }}</span>
  </el-button>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useUiStore } from '../../stores/ui'

const ui = useUiStore()

const currentTheme = computed(() => ui.theme)

function toggleTheme() {
  const newTheme = ui.theme === 'light' ? 'dark' : 'light'
  ui.setTheme(newTheme)
}
</script>

<style scoped>
.theme-icon {
  font-size: 18px;
  display: inline-block;
}
</style>
