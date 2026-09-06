<template>
  <div class="moments-page">
    <section class="moments-hero">
      <div>
        <p class="eyebrow">朋友圈</p>
        <h2>今天的片刻</h2>
        <p class="hero-copy">记录和角色、好友一起经过的小事。</p>
      </div>
      <div class="hero-orbit">
        <span>月</span>
      </div>
    </section>

    <div class="timeline-shell">
      <MomentCompose />

      <div v-if="!moment.timeline.length" class="empty">
        <div class="empty-mark">·</div>
        <div>还没有动态</div>
        <p>写下第一条近况，让这里慢慢热闹起来。</p>
      </div>
      <MomentCard v-for="m in moment.timeline" :key="m.id" :m="m" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useMomentStore } from '../../stores/moment'
import MomentCard from './MomentCard.vue'
import MomentCompose from './MomentCompose.vue'

const moment = useMomentStore()
onMounted(() => moment.loadTimeline())
</script>

<style scoped>
.moments-page {
  min-height: 100%;
  padding: 28px 18px 44px;
  background:
    radial-gradient(circle at 12% 0%, color-mix(in srgb, var(--companion-secondary, #b8a5bd) 18%, transparent), transparent 28%),
    linear-gradient(180deg, color-mix(in srgb, var(--companion-page, #eef0f4) 92%, #fff 8%) 0%, var(--companion-page, #f3f5f7) 100%);
}

.moments-hero {
  max-width: 720px;
  min-height: 124px;
  margin: 0 auto 18px;
  padding: 22px 26px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background:
    linear-gradient(135deg, rgba(76, 58, 89, 0.92), rgba(125, 99, 128, 0.88)),
    url("https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1200&q=70") center/cover;
  background-blend-mode: multiply;
  border-radius: 8px;
  color: #fff;
  box-shadow: 0 16px 34px rgba(67, 48, 71, 0.2);
}

.eyebrow {
  margin: 0 0 6px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.72);
}

.moments-hero h2 {
  margin: 0;
  font-size: 26px;
  font-weight: 700;
  letter-spacing: 0;
}

.hero-copy {
  margin: 8px 0 0;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.78);
}

.hero-orbit {
  width: 56px;
  height: 56px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  background: rgba(255, 255, 255, 0.16);
  border: 1px solid rgba(255, 255, 255, 0.22);
  color: rgba(255, 255, 255, 0.92);
  font-size: 22px;
  font-weight: 700;
  flex: 0 0 auto;
}

.timeline-shell {
  max-width: 720px;
  margin: 0 auto;
}

.empty {
  min-height: 220px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #8c858d;
  background: rgba(255, 252, 246, 0.72);
  border: 1px solid rgba(88, 71, 91, 0.08);
  border-radius: 8px;
  box-shadow: 0 10px 28px rgba(66, 52, 70, 0.08);
}

.empty-mark {
  width: 38px;
  height: 38px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  margin-bottom: 10px;
  background: #ded2de;
  color: #6b5570;
  font-size: 28px;
}

.empty p {
  margin: 8px 0 0;
  font-size: 13px;
  color: #aaa1a8;
}

:global(:root.dark) .moments-page {
  background:
    radial-gradient(circle at 12% 0%, color-mix(in srgb, var(--companion-secondary, #8b7892) 16%, transparent), transparent 30%),
    linear-gradient(180deg, #1e1b20 0%, #252127 48%, #1c1a1e 100%);
}

:global(:root.dark) .empty {
  background: rgba(44, 38, 48, 0.72);
  border-color: rgba(255, 255, 255, 0.08);
}

@media (max-width: 720px) {
  .moments-page {
    padding: 18px 12px 32px;
  }

  .moments-hero {
    min-height: 112px;
    padding: 18px;
  }

  .moments-hero h2 {
    font-size: 22px;
  }
}
</style>
