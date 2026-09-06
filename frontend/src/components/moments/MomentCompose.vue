<template>
  <div class="moment-compose-card">
    <div class="compose-header">
      <div class="compose-avatar">我</div>
      <div>
        <h3>发布动态</h3>
        <p>分享此刻的心情、画面和想法。</p>
      </div>
    </div>

    <div class="compose-body">
      <!-- 文本输入 -->
      <textarea
        v-model="content"
        class="content-input"
        placeholder="说点什么..."
        maxlength="2000"
      />
      <div class="char-count">{{ content.length }} / 2000</div>

      <!-- 图片预览 -->
      <div class="images-section">
        <div class="images-preview">
          <div v-for="(img, i) in images" :key="i" class="image-item">
            <img :src="img" :alt="`Image ${i + 1}`" />
            <button class="remove-btn" @click="removeImage(i)">✕</button>
          </div>
          <button
            v-if="images.length < 9"
            class="add-image-btn"
            @click="triggerImageUpload"
          >
            <span>+</span>
            <small>图片</small>
          </button>
        </div>
        <input
          ref="imageInput"
          type="file"
          multiple
          accept="image/*"
          style="display: none"
          @change="handleImageUpload"
        />
      </div>

      <!-- 隐私设置 -->
      <div class="visibility-section">
        <label class="visibility-label">谁可以看</label>
        <div class="visibility-options">
          <label class="radio-option">
            <input
              v-model="visibility"
              type="radio"
              value="public"
            />
            <span class="radio-text">
              <span class="icon">🌍</span> 公开
            </span>
          </label>
          <label class="radio-option">
            <input
              v-model="visibility"
              type="radio"
              value="friends"
            />
            <span class="radio-text">
              <span class="icon">👥</span> 仅好友可见
            </span>
          </label>
          <label class="radio-option">
            <input
              v-model="visibility"
              type="radio"
              value="private"
            />
            <span class="radio-text">
              <span class="icon">🔒</span> 仅自己可见
            </span>
          </label>
          <label class="radio-option">
            <input
              v-model="visibility"
              type="radio"
              value="groups"
            />
            <span class="radio-text">
              <span class="icon">👫</span> 分组可见
            </span>
          </label>
        </div>

        <!-- Group selection when "分组可见" is selected -->
        <div v-if="visibility === 'groups'" class="group-selection">
          <label class="checkbox-option">
            <input
              v-model="visibleGroups"
              type="checkbox"
              value="close_friends"
            />
            <span>密友</span>
          </label>
          <label class="checkbox-option">
            <input
              v-model="visibleGroups"
              type="checkbox"
              value="family"
            />
            <span>家人</span>
          </label>
          <label class="checkbox-option">
            <input
              v-model="visibleGroups"
              type="checkbox"
              value="work"
            />
            <span>工作</span>
          </label>
          <label class="checkbox-option">
            <input
              v-model="visibleGroups"
              type="checkbox"
              value="acquaintance"
            />
            <span>普通熟人</span>
          </label>
        </div>
      </div>

      <!-- 错误提示 -->
      <div v-if="error" class="error-message">
        {{ error }}
      </div>

      <!-- 发布按钮 -->
      <button
        class="publish-btn"
        :disabled="!content.trim() || loading"
        @click="publish"
      >
        <span v-if="!loading">发布</span>
        <span v-else>发布中...</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useMomentStore } from '../../stores/moment'
import api from '../../utils/api'

const momentStore = useMomentStore()
const imageInput = ref<HTMLInputElement | null>(null)

const content = ref('')
const images = ref<string[]>([])
const visibility = ref('public')
const visibleGroups = ref<string[]>([])
const loading = ref(false)
const error = ref('')

async function triggerImageUpload() {
  imageInput.value?.click()
}

async function handleImageUpload(event: Event) {
  const target = event.target as HTMLInputElement
  const files = target.files

  if (!files) return

  loading.value = true
  error.value = ''

  try {
    for (let i = 0; i < Math.min(files.length, 9 - images.value.length); i++) {
      const file = files[i]
      const formData = new FormData()
      formData.append('file', file)

      const response = await api.post('/api/upload/image', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })

      if (response.data?.data?.url) {
        images.value.push(response.data.data.url)
      }
    }
  } catch (err: any) {
    error.value = err.response?.data?.message || '图片上传失败'
  } finally {
    loading.value = false
    // 重置 input，允许重新选择同一个文件
    target.value = ''
  }
}

function removeImage(index: number) {
  images.value.splice(index, 1)
}

async function publish() {
  if (!content.value.trim()) {
    error.value = '请输入内容'
    return
  }

  loading.value = true
  error.value = ''

  try {
    const publishData: any = {
      content: content.value,
      images: images.value,
      visibility: visibility.value,
    }
    if (visibility.value === 'groups' && visibleGroups.value.length > 0) {
      publishData.visible_groups = visibleGroups.value
    }

    await momentStore.publish(publishData.content, publishData.images, publishData.visibility, publishData.visible_groups)

    // Reset form
    content.value = ''
    images.value = []
    visibility.value = 'public'
    visibleGroups.value = []
  } catch (err: any) {
    error.value = err.response?.data?.detail || 'Failed to publish, please try again'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.moment-compose-card {
  background: rgba(255, 252, 246, 0.9);
  border-radius: 8px;
  border: 1px solid rgba(89, 70, 91, 0.1);
  box-shadow: 0 12px 26px rgba(66, 52, 70, 0.1);
  overflow: hidden;
  margin-bottom: 14px;
  backdrop-filter: blur(14px);
}

.compose-header {
  padding: 16px 18px;
  display: flex;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid rgba(89, 70, 91, 0.08);
  background: rgba(246, 239, 231, 0.68);
}

.compose-avatar {
  width: 42px;
  height: 42px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #a979ad, #ceb1cf);
  color: #fff;
  font-weight: 700;
}

.compose-header h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #46324f;
}

.compose-header p {
  margin: 4px 0 0;
  font-size: 12px;
  color: #8d828c;
}

.compose-body {
  padding: 16px 18px 18px;
}

.content-input {
  width: 100%;
  min-height: 96px;
  padding: 0;
  border: 0;
  background: transparent;
  font-family: inherit;
  font-size: 15px;
  resize: vertical;
  color: #392b3f;
  line-height: 1.7;
}

.content-input:focus {
  outline: none;
}

.content-input::placeholder {
  color: #b4aab2;
}

.char-count {
  text-align: right;
  font-size: 12px;
  color: #aaa0a8;
  margin: 6px 0 14px 0;
}

.images-section {
  margin-bottom: 16px;
}

.images-preview {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(78px, 78px));
  gap: 8px;
  margin-bottom: 12px;
}

.image-item {
  position: relative;
  width: 80px;
  height: 80px;
  background: #eee8e0;
  border-radius: 6px;
  overflow: hidden;
}

.image-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.remove-btn {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 24px;
  height: 24px;
  padding: 0;
  background: rgba(35, 26, 38, 0.68);
  border: 0;
  border-radius: 6px;
  cursor: pointer;
  font-size: 16px;
  color: #fff;
  transition: all 0.2s;
}

.remove-btn:hover {
  background: #9f4f60;
  color: #fff;
}

.add-image-btn {
  width: 80px;
  height: 80px;
  padding: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(239, 233, 224, 0.8);
  border: 1px dashed rgba(89, 70, 91, 0.2);
  border-radius: 6px;
  cursor: pointer;
  color: #7b687f;
  transition: all 0.2s;
}

.add-image-btn:hover {
  border-color: #9a76a0;
  color: #5f4566;
  background: #e9dfe8;
}

.add-image-btn span {
  font-size: 24px;
  line-height: 1;
}

.add-image-btn small {
  margin-top: 4px;
  font-size: 12px;
}

.visibility-section {
  margin-bottom: 16px;
  padding: 12px;
  background: rgba(244, 238, 230, 0.74);
  border-radius: 8px;
}

.visibility-label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #4a384f;
  margin-bottom: 8px;
}

.visibility-options {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.radio-option {
  display: flex;
  align-items: center;
  cursor: pointer;
  user-select: none;
  padding: 7px 10px;
  border-radius: 6px;
  background: rgba(255, 252, 247, 0.72);
  border: 1px solid rgba(89, 70, 91, 0.08);
}

.radio-option input[type="radio"] {
  margin-right: 8px;
  cursor: pointer;
}

.radio-text {
  display: flex;
  align-items: center;
  font-size: 14px;
  color: #6b5d69;
}

.icon {
  margin-right: 6px;
  font-size: 16px;
}

.group-selection {
  margin-top: 12px;
  padding: 12px;
  background: white;
  border-radius: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.checkbox-option {
  display: flex;
  align-items: center;
  cursor: pointer;
  user-select: none;
  font-size: 14px;
}

.checkbox-option input[type="checkbox"] {
  margin-right: 8px;
  cursor: pointer;
  accent-color: #1890ff;
}

.error-message {
  padding: 8px 12px;
  margin-bottom: 12px;
  background: #fff1f0;
  border: 1px solid #ffccc7;
  border-radius: 4px;
  color: #ff4d4f;
  font-size: 14px;
}

.publish-btn {
  width: 100%;
  padding: 10px 16px;
  background: #1890ff;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.publish-btn:hover:not(:disabled) {
  background: #0050b3;
}

.publish-btn:disabled {
  background: #bfbfbf;
  cursor: not-allowed;
}
</style>
