<template>
  <div class="card">
    <div class="head">
      <div class="avatar">
        {{ m.user_id ? (m.author_name?.[0] || '我') : getSoulEmoji(m.soul_id) }}
      </div>
      <div class="meta">
        <div class="name">{{ m.user_id ? m.author_name : (m.soul_name || 'AI 伴侣') }}</div>
        <div class="time">
          {{ (m.created_at || '').slice(0, 16).replace('T', ' ') }}
          <span v-if="getVisibilityIcon(m.visibility)" class="visibility-badge">
            {{ getVisibilityIcon(m.visibility) }}
          </span>
        </div>
      </div>
      <!-- 所有者菜单 -->
      <div v-if="m.is_mine" class="owner-menu">
        <button class="menu-trigger" aria-label="更多操作" :aria-expanded="showMenu" @click="showMenu = !showMenu">⋮</button>
        <div v-if="showMenu" class="menu-dropdown" role="menu" aria-label="动态操作菜单">
          <button class="menu-item" role="menuitem" @click="showVisibilityPicker = true; showMenu = false">
            编辑隐私
          </button>
          <button class="menu-item delete-item" role="menuitem" @click="confirmDelete">
            删除
          </button>
        </div>
      </div>
    </div>

    <!-- 隐私设置选择器 -->
    <div v-if="showVisibilityPicker" class="visibility-picker">
      <div class="picker-title">隐私设置</div>
      <label class="picker-option">
        <input
          type="radio"
          :value="'public'"
          :checked="visibility === 'public'"
          @change="updateVisibility('public')"
        />
        <span>🌍 公开</span>
      </label>
      <label class="picker-option">
        <input
          type="radio"
          :value="'friends'"
          :checked="visibility === 'friends'"
          @change="updateVisibility('friends')"
        />
        <span>👥 仅好友可见</span>
      </label>
      <label class="picker-option">
        <input
          type="radio"
          :value="'private'"
          :checked="visibility === 'private'"
          @change="updateVisibility('private')"
        />
        <span>🔒 仅自己可见</span>
      </label>
      <div class="picker-actions">
        <button class="btn-cancel" @click="showVisibilityPicker = false">取消</button>
        <button class="btn-ok" @click="showVisibilityPicker = false">确定</button>
      </div>
    </div>

    <div class="content">{{ m.content }}</div>
    <div v-if="m.images && m.images.length" class="images" :class="`count-${Math.min(m.images.length, 9)}`">
      <img v-for="img in m.images" :key="img" :src="img" alt="配图" />
    </div>
    <div v-if="m.topic_tags && m.topic_tags.length" class="tags">
      <span v-for="t in m.topic_tags" :key="t" class="tag">#{{ t }}</span>
    </div>
    <div class="actions">
      <button class="act" @click="moment.toggleLike(m)">
        {{ m.is_liked ? '❤️' : '🤍' }} {{ m.like_count || 0 }}
      </button>
      <button class="act" @click="showComment = !showComment">💬 评论</button>
    </div>
    <div v-if="m.comments && m.comments.length" class="comments">
      <div v-for="c in m.comments" :key="c.id" class="c">
        <b>{{ c.is_ai ? 'AI 回复' : '我' }}</b>：{{ c.content }}
      </div>
    </div>
    <div v-if="showComment" class="comment-box">
      <el-input v-model="text" size="small" placeholder="评论…" @keyup.enter="submit" />
      <el-button size="small" type="primary" @click="submit">发送</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { Moment } from '../../stores/moment'
import { useMomentStore } from '../../stores/moment'
import { useUserStore } from '../../stores/user'

const props = defineProps<{ m: Moment }>()
const moment = useMomentStore()
const user = useUserStore()
const showComment = ref(false)
const showMenu = ref(false)
const showVisibilityPicker = ref(false)
const text = ref('')
const visibility = ref(props.m.visibility || 'public')

// 根据 soul_id 返回对应的 emoji
function getSoulEmoji(soulId?: number | null): string {
  if (!soulId) return '🌙'
  const emojiMap: Record<number, string> = {
    1: '🌙', // Luna
    2: '🎵', // Aria
    3: '⭐', // Caelus
    4: '🐦', // Raven
    5: '💎', // Diana
    6: '💜', // Elara
  }
  return emojiMap[soulId] || '🌙'
}

function getVisibilityIcon(vis?: string): string {
  const iconMap: Record<string, string> = {
    'public': '🌍',
    'friends': '👥',
    'private': '🔒'
  }
  return iconMap[vis || 'public']
}

async function updateVisibility(newVis: 'public' | 'friends' | 'private') {
  visibility.value = newVis
  try {
    await moment.updateVisibility(props.m, newVis)
  } catch (err) {
    console.error('Failed to update visibility:', err)
  }
}

async function confirmDelete() {
  if (confirm('删除后无法恢复。确认删除这条动态吗？')) {
    try {
      await moment.deleteMoment(props.m)
      showMenu.value = false
    } catch (err) {
      console.error('Failed to delete moment:', err)
      alert('删除失败，请稍后重试')
    }
  }
}

async function submit() {
  const t = text.value.trim()
  if (!t) return
  await moment.comment(props.m, t)
  text.value = ''
  showComment.value = false
}
</script>

<style scoped>
.card {
  background: rgba(255, 252, 246, 0.88);
  border-radius: 8px;
  padding: 16px 18px 14px;
  margin-bottom: 12px;
  position: relative;
  border: 1px solid rgba(89, 70, 91, 0.1);
  box-shadow: 0 10px 24px rgba(66, 52, 70, 0.09);
  backdrop-filter: blur(12px);
}

.head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.avatar {
  width: 42px;
  height: 42px;
  border-radius: 6px;
  background: linear-gradient(135deg, #b08bb7 0%, #d9c1d8 100%);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 17px;
  font-weight: 700;
  box-shadow: 0 8px 18px rgba(112, 87, 119, 0.18);
}

.meta {
  flex: 1;
  min-width: 0;
}

.name {
  font-size: 15px;
  font-weight: 700;
  color: #51405a;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.time {
  font-size: 12px;
  color: #9c939b;
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 3px;
}

.visibility-badge {
  font-size: 12px;
  color: #666;
}

/* 所有者菜单 */
.owner-menu {
  position: relative;
}

.menu-trigger {
  width: 30px;
  height: 30px;
  background: rgba(237, 228, 236, 0.8);
  border: none;
  padding: 0;
  cursor: pointer;
  font-size: 18px;
  color: #7d6e7f;
  border-radius: 6px;
  transition: background 0.2s;
}

.menu-trigger:hover {
  background: #e4d8e5;
}

.menu-dropdown {
  position: absolute;
  right: 0;
  top: 100%;
  background: #fffaf4;
  border: 1px solid rgba(89, 70, 91, 0.14);
  border-radius: 8px;
  box-shadow: 0 12px 26px rgba(55, 42, 58, 0.16);
  min-width: 120px;
  z-index: 1000;
}

.menu-item {
  display: block;
  width: 100%;
  padding: 8px 16px;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  color: #4a384f;
  text-align: left;
  transition: background 0.2s;
}

.menu-item:hover {
  background: #f1e9f0;
}

.delete-item {
  color: #ff4d4f;
  border-top: 1px solid #f0f0f0;
}

.delete-item:hover {
  background: #fff1f0;
}

/* 隐私设置选择器 */
.visibility-picker {
  background: rgba(244, 238, 230, 0.78);
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;
}

.picker-title {
  font-size: 12px;
  font-weight: 600;
  color: #4a384f;
  margin-bottom: 8px;
}

.picker-option {
  display: flex;
  align-items: center;
  padding: 6px 0;
  cursor: pointer;
  font-size: 13px;
  color: #6b5d69;
}

.picker-option input {
  margin-right: 8px;
  cursor: pointer;
}

.picker-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid rgba(89, 70, 91, 0.1);
}

.btn-cancel,
.btn-ok {
  flex: 1;
  padding: 6px 12px;
  border: 1px solid rgba(89, 70, 91, 0.15);
  background: #fffaf4;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
}

.btn-cancel:hover {
  border-color: #b3b3b3;
}

.btn-ok {
  background: #7f5c87;
  color: white;
  border-color: #7f5c87;
}

.btn-ok:hover {
  background: #66466e;
  border-color: #66466e;
}

.content {
  font-size: 15px;
  line-height: 1.75;
  margin-bottom: 12px;
  color: #372a3d;
  white-space: pre-wrap;
}

.images {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 7px;
  margin-bottom: 12px;
  max-width: 420px;
}

.images.count-1 {
  grid-template-columns: minmax(160px, 260px);
}

.images.count-2,
.images.count-4 {
  grid-template-columns: repeat(2, minmax(120px, 1fr));
  max-width: 360px;
}

.images img {
  width: 100%;
  aspect-ratio: 1;
  height: auto;
  object-fit: cover;
  border-radius: 6px;
  display: block;
  box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.04);
}

.images.count-1 img {
  aspect-ratio: 4 / 3;
}

.tags {
  margin-bottom: 10px;
}

.tag {
  display: inline-flex;
  align-items: center;
  padding: 3px 8px;
  border-radius: 6px;
  background: rgba(219, 207, 220, 0.54);
  color: #6d5273;
  font-size: 13px;
  margin: 0 6px 6px 0;
}

.actions {
  display: flex;
  gap: 8px;
  border-top: 1px solid rgba(89, 70, 91, 0.08);
  padding-top: 10px;
}

.act {
  border: none;
  background: rgba(237, 228, 236, 0.72);
  cursor: pointer;
  color: #6f6170;
  font-size: 13px;
  padding: 6px 10px;
  border-radius: 6px;
  transition: color 0.2s;
}

.act:hover {
  color: #4f3857;
  background: #e2d5e2;
}

.comments {
  background: rgba(244, 238, 230, 0.82);
  border-radius: 8px;
  padding: 10px 12px;
  margin-top: 10px;
  font-size: 13px;
  color: #4b3d50;
}

.c {
  margin-bottom: 6px;
  line-height: 1.55;
}

.c:last-child {
  margin-bottom: 0;
}

.comment-box {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}

:global(:root.dark) .card,
:global(:root.dark) .menu-dropdown {
  background: rgba(43, 37, 47, 0.88);
  border-color: rgba(255, 255, 255, 0.08);
}

:global(:root.dark) .name,
:global(:root.dark) .content,
:global(:root.dark) .comments {
  color: #ece7ee;
}

:global(:root.dark) .time {
  color: #aaa1aa;
}

@media (max-width: 560px) {
  .card {
    padding: 14px;
  }

  .images {
    max-width: 100%;
  }

  .actions {
    flex-wrap: wrap;
  }
}
</style>
