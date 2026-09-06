<template>
  <div class="api-panel">
    <el-radio-group v-model="service" class="svc-tabs">
      <el-radio-button v-for="s in services" :key="s.key" :value="s.key">{{ s.label }}</el-radio-button>
    </el-radio-group>

    <el-form label-width="88px" style="max-width: 520px; margin-top: 12px">
      <el-form-item label="API Key">
        <el-input
          v-model="form.api_key"
          :type="showKey ? 'text' : 'password'"
          :placeholder="cur && cur.is_configured ? '已保存（留空则不修改）' : 'sk-...'"
        />
        <el-button text @click="showKey = !showKey">{{ showKey ? '隐藏' : '显示' }}</el-button>
      </el-form-item>
      <el-form-item label="Base URL">
        <el-input v-model="form.base_url" :placeholder="curSvc.defaultBase || 'OpenAI 兼容地址'" />
      </el-form-item>
      <el-form-item label="模型名">
        <el-input v-model="form.model" :placeholder="curSvc.placeholder || 'deepseek-v4-flash'" />
        <div class="tip">{{ curSvc.hint }}</div>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
        <el-button :loading="testing" @click="test">测试连接</el-button>
        <el-button @click="load">刷新</el-button>
      </el-form-item>
    </el-form>

    <div v-if="testResult" class="test-result" :class="testResult.success ? 'ok' : 'fail'">
      {{ testResult.success ? '✅ ' + testResult.note : '❌ ' + testResult.error }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../utils/api'

const services = [
  { key: 'llm', label: '对话 LLM', defaultBase: 'https://api.deepseek.com/v1', placeholder: 'deepseek-v4-flash', hint: '任何 OpenAI 兼容模型均可，如 deepseek-v4-flash / gpt-4o / qwen 等' },
  { key: 'vision', label: '视觉', defaultBase: 'https://api.deepseek.com/v1', placeholder: '如 qwen-vl-plus', hint: '图片分析用（当前未启用，配好备用）' },
  { key: 'whisper', label: '语音识别', defaultBase: '', placeholder: '如 whisper-1', hint: '留空则用本地 whisper.cpp（免 key）' },
  { key: 'tts', label: '语音合成', defaultBase: '', placeholder: '留空用 Edge TTS', hint: '留空则用免费 Edge TTS（免 key）' },
  { key: 'image', label: '图片生成', defaultBase: '', placeholder: '留空用免费兜底', hint: '留空则用免费 Pollinations 兜底' },
]

const service = ref('llm')
const form = ref({ api_key: '', base_url: '', model: '' })
const configs = ref<Record<string, any>>({})
const saving = ref(false)
const testing = ref(false)
const testResult = ref<any>(null)
const showKey = ref(false)

const cur = computed(() => configs.value[service.value])
const curSvc = computed(() => services.find((s) => s.key === service.value)!)

async function load() {
  const res: any = await api.get('/api/settings/api-config')
  configs.value = res?.data ?? {}
  applyCurrent()
}
function applyCurrent() {
  const c = cur.value
  form.value = {
    api_key: '',
    base_url: c?.base_url || curSvc.value.defaultBase || '',
    model: c?.model || curSvc.value.placeholder || '',
  }
  testResult.value = null
}
watch(service, applyCurrent)
onMounted(load)

async function save() {
  saving.value = true
  try {
    await api.put('/api/settings/api-config', {
      service: service.value,
      api_key: form.value.api_key || undefined,
      base_url: form.value.base_url || undefined,
      model: form.value.model || undefined,
    })
    ElMessage.success('已保存')
    await load()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function test() {
  testing.value = true
  testResult.value = null
  try {
    const res: any = await api.post('/api/settings/api-config/test', {
      service: service.value,
      api_key: form.value.api_key || undefined,
      base_url: form.value.base_url || undefined,
      model: form.value.model || undefined,
    })
    testResult.value = res
  } catch (e: any) {
    testResult.value = { success: false, error: e?.response?.data?.detail || '测试请求失败' }
  } finally {
    testing.value = false
  }
}
</script>

<style scoped>
.svc-tabs { display: flex; flex-wrap: wrap; }
.tip { font-size: 12px; color: #999; line-height: 1.5; }
.test-result { margin-top: 4px; font-size: 13px; padding: 8px 10px; border-radius: 4px; }
.test-result.ok { background: #f0f9eb; color: #529b2e; }
.test-result.fail { background: #fef0f0; color: #f56c6c; }
</style>
