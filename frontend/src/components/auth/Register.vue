<template>
  <el-form @submit.prevent="submit">
    <el-form-item>
      <el-input v-model="username" placeholder="用户名（3-50 位）" size="large" />
    </el-form-item>
    <el-form-item>
      <el-input v-model="password" type="password" placeholder="密码（至少 6 位）" size="large" show-password />
    </el-form-item>
    <el-form-item>
      <el-input v-model="nickname" placeholder="昵称（可选）" size="large" />
    </el-form-item>
    <el-form-item>
      <el-radio-group v-model="gender">
        <el-radio value="male">男</el-radio>
        <el-radio value="female">女</el-radio>
      </el-radio-group>
    </el-form-item>
    <el-button type="primary" size="large" style="width: 100%" :loading="loading" @click="submit">注册并进入</el-button>
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
const nickname = ref('')
const gender = ref('female')
const loading = ref(false)

async function submit() {
  if (!username.value || !password.value) { ElMessage.warning('请输入用户名和密码'); return }
  if (password.value.length < 6) { ElMessage.warning('密码至少 6 位'); return }
  loading.value = true
  try {
    await useUserStore().register({
      username: username.value,
      password: password.value,
      gender: gender.value,
      nickname: nickname.value || undefined,
    })
    ElMessage.success('注册成功，已自动配对 AI 伴侣')
    router.push('/')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '注册失败')
  } finally {
    loading.value = false
  }
}
</script>
