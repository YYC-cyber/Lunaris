<template>
  <div class="font-size-selector">
    <div class="label">字体大小</div>
    <div class="options">
      <label v-for="size in sizes" :key="size.key" class="radio-option">
        <input
          type="radio"
          :value="size.key"
          :checked="ui.fontSize === size.key"
          @change="ui.setFontSize(size.key)"
        />
        <span class="radio-text" :style="{ fontSize: size.preview }">{{ size.label }}</span>
      </label>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useUiStore } from '../../stores/ui'

const ui = useUiStore()

const sizes = [
  { key: 'small' as const, label: '小', preview: '12px' },
  { key: 'normal' as const, label: '正常', preview: '14px' },
  { key: 'large' as const, label: '大', preview: '16px' },
  { key: 'xlarge' as const, label: '特大', preview: '18px' },
]
</script>

<style scoped>
.font-size-selector {
  padding: 12px 0;
}

.label {
  font-size: 13px;
  color: var(--color-text-primary);
  font-weight: 600;
  margin-bottom: 8px;
}

.options {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.radio-option {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}

.radio-option input {
  cursor: pointer;
  accent-color: var(--color-primary);
}

.radio-text {
  color: var(--color-text-primary);
  user-select: none;
}

.radio-option input:checked + .radio-text {
  color: var(--color-primary);
  font-weight: 600;
}
</style>
