<template>
  <el-form @submit.prevent="submit">
    <el-form-item>
      <el-input v-model="username" placeholder="用户名" size="large" />
    </el-form-item>
    <el-form-item>
      <el-input v-model="password" type="password" placeholder="密码" size="large" show-password @keyup.enter="submit" />
    </el-form-item>
    <el-button type="primary" size="large" style="width: 100%" :loading="loading" @click="submit">登录</el-button>
  </el-form>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../../stores/user'

const router = useRouter()
const username = ref('')
const password = ref('')
const loading = ref(false)

async function submit() {
  if (!username.value || !password.value) { ElMessage.warning('请输入用户名和密码'); return }
  loading.value = true
  try {
    await useUserStore().login(username.value, password.value)
    router.push('/')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>
