<template>
  <div class="win-controls">
    <button title="最小化" @click="minimize()">—</button>
    <button title="关闭到托盘" @click="closeToTray()">✕</button>
  </div>
</template>

<script setup lang="ts">
import { minimize, closeToTray } from '../../utils/electron'
</script>

<style scoped>
.win-controls { display: flex; gap: 4px; }
.win-controls button {
  width: 26px; height: 26px; border: none; border-radius: 4px;
  background: transparent; color: #999; cursor: pointer; font-size: 13px;
}
.win-controls button:hover { background: rgba(0, 0, 0, 0.08); }
</style>
