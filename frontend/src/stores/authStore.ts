import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as api from '@/api'
import { clearAuthState, loadAuthState, saveAuthState } from '@/utils/secureStorage'
import { useTaskStore } from './taskStore'

export const useAuthStore = defineStore('auth', () => {
  const token = ref('')
  const username = ref('')
  const userId = ref<number | null>(null)
  const isAdmin = ref(false)
  const isLoggedIn = ref(!!token.value)
  const ready = ref(false)

  async function init() {
    const state = await loadAuthState()
    token.value = state.token
    username.value = state.username
    isLoggedIn.value = !!state.token
    useTaskStore().useUser(state.username)
    if (state.token) {
      try {
        const me = await api.getMe()
        userId.value = me.id
        username.value = me.username
        isAdmin.value = !!me.isAdmin
        useTaskStore().useUser(me.username)
      } catch {
        await logout()
      }
    }
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
    const me = await api.getMe()
    userId.value = me.id
    username.value = me.username
    isAdmin.value = !!me.isAdmin
    await saveAuthState({ token: res.accessToken, username: me.username })
    useTaskStore().useUser(me.username)
  }

  async function logout() {
    token.value = ''
    username.value = ''
    userId.value = null
    isAdmin.value = false
    isLoggedIn.value = false
    await clearAuthState()
    useTaskStore().useUser('')
  }

  return { token, username, userId, isAdmin, isLoggedIn, ready, init, register, login, logout }
})
