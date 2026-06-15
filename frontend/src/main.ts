import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { useAuthStore } from './stores/authStore'
import { useSettingsStore } from './stores/settingsStore'
import { useTaskStore } from './stores/taskStore'
import { startTaskNotifications } from './utils/notifications'

const app = createApp(App)
const pinia = createPinia()

async function bootstrap() {
  app.use(pinia)

  const auth = useAuthStore(pinia)
  await auth.init()
  const settingsStore = useSettingsStore(pinia)
  settingsStore.refreshPermission()
  const taskStore = useTaskStore(pinia)
  startTaskNotifications(() => taskStore.activeTasks)

  app.use(router)
  await router.isReady()
  app.mount('#app')
}

bootstrap()
