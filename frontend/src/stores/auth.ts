import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, type User } from '@/api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string>(localStorage.getItem('gitcam_token') || '')
  const user = ref<User | null>(null)
  const loaded = ref(false)

  const isLoggedIn = computed(() => !!token.value && !!user.value)
  const isTeacher = computed(() => user.value?.role === 'teacher' || user.value?.role === 'admin')
  const isAdmin = computed(() => user.value?.role === 'admin')

  async function fetchMe() {
    try {
      user.value = (await authApi.me() as { user: User }).user
    } catch {
      user.value = null
      token.value = ''
      localStorage.removeItem('gitcam_token')
    } finally {
      loaded.value = true
    }
  }

  async function login(account: string, password: string) {
    const data = await authApi.login({ account, password }) as { token: string; user: User }
    token.value = data.token
    user.value = data.user
    localStorage.setItem('gitcam_token', data.token)
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('gitcam_token')
  }

  return { token, user, loaded, isLoggedIn, isTeacher, isAdmin, login, logout, fetchMe }
})
