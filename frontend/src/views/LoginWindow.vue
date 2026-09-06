<template>
  <div class="login-wrap">
    <div class="login-card">
      <div class="brand">
        <div class="logo">🌙</div>
        <h1>Lunaris</h1>
        <p>AI 虚拟伴侣，随时陪伴</p>
      </div>
      <div class="switch">
        <button :class="{ active: mode === 'login' }" @click="mode = 'login'">登录</button>
        <button :class="{ active: mode === 'register' }" @click="mode = 'register'">注册</button>
      </div>
      <div class="form">
        <Login v-if="mode === 'login'" />
        <Register v-else />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import Login from '../components/auth/Login.vue'
import Register from '../components/auth/Register.vue'

const mode = ref<'login' | 'register'>('login')
</script>

<style scoped>
.login-wrap {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #07c160 0%, #0a8f4a 100%);
}
.login-card {
  width: 360px;
  background: #fff;
  border-radius: 12px;
  padding: 32px 28px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);
}
.brand { text-align: center; margin-bottom: 20px; }
.brand .logo { font-size: 40px; }
.brand h1 { margin: 8px 0 4px; color: #07c160; }
.brand p { margin: 0; color: #999; font-size: 13px; }
.switch { display: flex; margin-bottom: 20px; border-radius: 6px; overflow: hidden; }
.switch button {
  flex: 1; padding: 10px; border: none; background: #f2f2f2; cursor: pointer; font-size: 15px; color: #666;
}
.switch button.active { background: #07c160; color: #fff; }
</style>
