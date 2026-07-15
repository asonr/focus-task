import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as api from '@/api'
import { useTaskStore } from './taskStore'
import { useAuthStore } from './authStore'

const LAST_SYNC_KEY_PREFIX = 'focus-task-last-sync'

function normalizeOwner(username: string) {
  return username.trim().toLowerCase() || 'anonymous'
}

function lastSyncKeyFor(username: string) {
  return `${LAST_SYNC_KEY_PREFIX}:${encodeURIComponent(normalizeOwner(username))}`
}

export const useSyncStore = defineStore('sync', () => {
  const lastSyncAt = ref('')
  const syncing = ref(false)
  const syncError = ref('')
  const online = ref(navigator.onLine)

  // Track online status
  if (typeof window !== 'undefined') {
    window.addEventListener('online', () => { online.value = true })
    window.addEventListener('offline', () => { online.value = false })
  }

  async function sync() {
    const auth = useAuthStore()
    if (!auth.isLoggedIn || !online.value) return

    syncing.value = true
    syncError.value = ''
    try {
      const taskStore = useTaskStore()
      lastSyncAt.value = localStorage.getItem(lastSyncKeyFor(auth.username)) || ''

      // 1. Push only locally dirty tasks. Server returns canonical timestamps/ids.
      const dirtyTasks = taskStore.pendingTasks()
      let pushedTasks: typeof dirtyTasks = []
      if (dirtyTasks.length > 0) {
        const pushed = await api.syncPush(dirtyTasks)
        pushedTasks = pushed
        for (const serverTask of pushed) {
          const local = taskStore.tasks.find(t => t.clientId === serverTask.clientId)
          if (local) {
            Object.assign(local, serverTask)
            taskStore.markSynced(local)
          }
        }
      }

      // 2. Pull server changes since the previous successful sync.
      const serverTasks = await api.syncPull(lastSyncAt.value || undefined)
      taskStore.mergeServerTasks(serverTasks)

      // 3. Advance sync cursor from observed server timestamps.
      const observedTimestamps = [...serverTasks, ...pushedTasks]
        .map(t => t.updatedAt)
        .filter((value): value is string => !!value)
      if (observedTimestamps.length > 0) {
        const sortedTimestamps = observedTimestamps.sort()
        lastSyncAt.value = sortedTimestamps[sortedTimestamps.length - 1] || lastSyncAt.value
      } else {
        lastSyncAt.value = new Date().toISOString()
      }
      localStorage.setItem(lastSyncKeyFor(auth.username), lastSyncAt.value)

      // 4. Remove tombstones after the server has acknowledged them.
      taskStore.pruneSyncedDeleted()
    } catch (e: any) {
      syncError.value = e.message || '同步失败'
      console.error('Sync failed:', e)
    } finally {
      syncing.value = false
    }
  }

  // Auto-sync every 30 seconds when online
  let syncTimer: ReturnType<typeof setInterval> | null = null
  function startAutoSync(intervalMs = 30000) {
    const auth = useAuthStore()
    lastSyncAt.value = auth.isLoggedIn ? localStorage.getItem(lastSyncKeyFor(auth.username)) || '' : ''
    stopAutoSync()
    sync() // Initial sync
    syncTimer = setInterval(() => {
      if (online.value) sync()
    }, intervalMs)
  }

  function stopAutoSync() {
    if (syncTimer) {
      clearInterval(syncTimer)
      syncTimer = null
    }
  }

  return {
    lastSyncAt,
    syncing,
    syncError,
    online,
    sync,
    startAutoSync,
    stopAutoSync,
  }
})
