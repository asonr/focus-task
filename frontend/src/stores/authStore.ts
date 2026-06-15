import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as api from '@/api'
import { clearAuthState, loadAuthState, saveAuthState } from '@/utils/secureStorage'

export const useAuthStore = defineStore('auth', () => {
  const token = ref('')
  const username = ref('')
  const isLoggedIn = ref(!!token.value)
  const ready = ref(false)

  async function init() {
    const state = await loadAuthState()
    token.value = state.token
    username.value = state.username
    isLoggedIn.value = !!state.token
    ready.value = true
  }

  async function register(user: string, password: string) {
    const res = await api.register(user, password)
    await login(user, password)
    return res
  }

  async function login(user: string, password: string) {
    const res = await api.login(user, password)
    token.value = res.accessToken
    username.value = user
    isLoggedIn.value = true
    await saveAuthState({ token: res.accessToken, username: user })
  }

  async function logout() {
    token.value = ''
    username.value = ''
    isLoggedIn.value = false
    await clearAuthState()
  }

  return { token, username, isLoggedIn, ready, init, register, login, logout }
})
