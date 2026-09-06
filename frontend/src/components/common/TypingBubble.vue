<template>
  <div class="typing-bubble">
    <div class="typing-dot"></div>
    <div class="typing-dot"></div>
    <div class="typing-dot"></div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
.typing-bubble {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: var(--color-ai-gradient);
  color: var(--color-text-primary);
  padding: 10px 14px;
  border-radius: var(--radius-bubble);
  box-shadow: var(--shadow-soft);
  animation: slideInUp 0.3s ease-out;
}

.typing-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-text-primary);
  opacity: 0.4;
  animation: typingDot 1.4s infinite;
}

.typing-dot:nth-child(1) {
  animation-delay: 0s;
}

.typing-dot:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-dot:nth-child(3) {
  animation-delay: 0.4s;
}
</style>
