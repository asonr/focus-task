import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as api from '@/api'
import { normalizeDateTimeLocal } from '@/utils/dateTime'
import { useSettingsStore } from '@/stores/settingsStore'

export interface Task {
  id?: number
  clientId: string
  quadrant: number
  title: string
  notes: string
  done: boolean
  startAt: string
  due: string
  tag: string
  repeat: string
  notifyOnStart: boolean
  notifyOnDue: boolean
  notifyOnOverdue: boolean
  showInFocus: boolean
  sortOrder: number
  doneAt: string
  deleted: boolean
  createdAt?: string
  updatedAt?: string
  syncStatus?: 'synced' | 'pending' | 'conflict'
  lastSyncedAt?: string
  conflictServer?: Task
}

const LOCAL_KEY_PREFIX = 'focus-task-local-cache'

function normalizeOwner(username: string) {
  return username.trim().toLowerCase() || 'anonymous'
}

function ownerFromBrowserStorage() {
  return normalizeOwner(localStorage.getItem('focus-task-username') || '')
}

function localKeyFor(owner: string) {
  return `${LOCAL_KEY_PREFIX}:${encodeURIComponent(owner)}`
}

export const useTaskStore = defineStore('tasks', () => {
  const settings = useSettingsStore()
  // ─── State ───
  const localOwner = ref(ownerFromBrowserStorage())
  const tasks = ref<Task[]>(loadLocal())
  const selectedTaskId = ref<string | null>(null)
  const currentView = ref<'matrix' | 'today' | 'done' | 'reports' | 'summary'>('matrix')
  const searchQuery = ref('')
  const filterQuadrant = ref<number | null>(null)
  const loading = ref(false)

  // ─── Local cache for offline ───
  function loadLocal(owner = localOwner.value): Task[] {
    try {
      const raw = localStorage.getItem(localKeyFor(owner))
      const data = raw ? JSON.parse(raw) : []
      return data.map(normalizeTask)
    } catch { return [] }
  }

  function normalizeTask(task: Task): Task {
    return {
      ...task,
      startAt: normalizeDateTimeLocal(task.startAt || '', settings.state.defaultStartTime || '09:00'),
      due: normalizeDateTimeLocal(task.due || '', settings.state.defaultDueTime || '18:00'),
      notifyOnStart: task.notifyOnStart ?? true,
      notifyOnDue: task.notifyOnDue ?? true,
      notifyOnOverdue: task.notifyOnOverdue ?? true,
    }
  }

  function saveLocal() {
    localStorage.setItem(localKeyFor(localOwner.value), JSON.stringify(tasks.value))
  }

  function useUser(username: string) {
    const nextOwner = normalizeOwner(username)
    if (localOwner.value === nextOwner) return

    localOwner.value = nextOwner
    tasks.value = loadLocal(nextOwner)
    selectedTaskId.value = null
    searchQuery.value = ''
    filterQuadrant.value = null
  }

  function markPending(task: Task, updatedAt = new Date().toISOString()) {
    task.updatedAt = updatedAt
    task.syncStatus = 'pending'
  }

  function markSynced(task: Task) {
    task.syncStatus = 'synced'
    task.lastSyncedAt = task.updatedAt || new Date().toISOString()
  }

  function markOrderPending(items: { clientId: string; sortOrder: number }[]) {
    const now = new Date().toISOString()
    for (const item of items) {
      const task = tasks.value.find(t => t.clientId === item.clientId)
      if (!task) continue
      task.sortOrder = item.sortOrder
      markPending(task, now)
    }
    saveLocal()
  }

  async function reorderTasks(items: { clientId: string; sortOrder: number }[]) {
    if (items.length === 0) return

    markOrderPending(items)

    try {
      await api.reorderTasks(items)
      for (const item of items) {
        const task = tasks.value.find(t => t.clientId === item.clientId)
        if (task) markSynced(task)
      }
      saveLocal()
    } catch {
      // Offline - dirty sort orders will be pushed by the sync loop later.
    }
  }

  function mergeServerTasks(serverTasks: Task[]) {
    const localMap = new Map(tasks.value.map(t => [t.clientId, t]))

    for (const serverTask of serverTasks) {
      const local = localMap.get(serverTask.clientId)
      const normalizedServer: Task = {
        ...normalizeTask(serverTask),
        syncStatus: 'synced',
        lastSyncedAt: serverTask.updatedAt || new Date().toISOString(),
      }

      if (!local) {
        tasks.value.push(normalizedServer)
        continue
      }

      if (local.syncStatus === 'pending') {
        const localUpdated = local.updatedAt ? new Date(local.updatedAt).getTime() : 0
        const serverUpdated = serverTask.updatedAt ? new Date(serverTask.updatedAt).getTime() : 0
        if (serverUpdated > localUpdated) {
          local.syncStatus = 'conflict'
          local.conflictServer = normalizedServer
        }
        continue
      }

      Object.assign(local, normalizedServer)
    }
  }

  const conflictTasks = computed(() => tasks.value.filter(t => t.syncStatus === 'conflict'))

  function pendingTasks() {
    return tasks.value.filter(t => t.syncStatus === 'pending')
  }

  function pruneSyncedDeleted() {
    tasks.value = tasks.value.filter(t => !(t.deleted && t.syncStatus === 'synced'))
  }

  function resolveConflict(clientId: string, strategy: 'local' | 'server') {
    const task = tasks.value.find(t => t.clientId === clientId)
    if (!task || task.syncStatus !== 'conflict') return

    if (strategy === 'server' && task.conflictServer) {
      Object.assign(task, {
        ...task.conflictServer,
        syncStatus: 'synced',
        lastSyncedAt: task.conflictServer.updatedAt || new Date().toISOString(),
        conflictServer: undefined,
      })
      saveLocal()
      return
    }

    task.conflictServer = undefined
    markPending(task)
    saveLocal()
  }

  // ─── Getters ───
  const activeTasks = computed(() => tasks.value.filter(t => !t.deleted))

  const selectedTask = computed(() =>
    activeTasks.value.find(t => t.clientId === selectedTaskId.value) || null
  )

  function quadrantTasks(q: number) {
    return activeTasks.value
      .filter(t => t.quadrant === q)
      .sort((a, b) => a.sortOrder - b.sortOrder || (b.createdAt || '').localeCompare(a.createdAt || ''))
  }

  const todayTasks = computed(() => {
    const today = new Date().toISOString().slice(0, 10)
    return activeTasks.value.filter(t => t.due.slice(0, 10) === today && !t.done)
  })

  const doneTasks = computed(() =>
    activeTasks.value.filter(t => t.done).sort((a, b) => (b.doneAt || '').localeCompare(a.doneAt || ''))
  )

  // ─── Actions ───
  async function fetchTasks() {
    loading.value = true
    try {
      const serverTasks = await api.listTasks(true)
      mergeServerTasks(serverTasks)
      pruneSyncedDeleted()
      saveLocal()
    } catch {
      // Offline — use local cache
      console.log('Using local cache (offline)')
    } finally {
      loading.value = false
    }
  }

  async function addTask(quadrant: number, title: string) {
    const clientId = crypto.randomUUID()
    const now = new Date().toISOString()
    const task: Task = {
      clientId,
      quadrant,
      title,
      notes: '',
      done: false,
      startAt: '',
      due: '',
      tag: '',
      repeat: 'none',
      notifyOnStart: true,
      notifyOnDue: true,
      notifyOnOverdue: true,
      showInFocus: false,
      sortOrder: 0,
      doneAt: '',
      deleted: false,
      createdAt: now,
      updatedAt: now,
      syncStatus: 'pending',
    }

    // Optimistic update
    tasks.value.unshift(task)
    selectedTaskId.value = clientId
    saveLocal()

    // Try API
    try {
      const serverTask = await api.createTask({
        clientId,
        quadrant,
        title,
        notes: '',
        done: false,
        startAt: '',
        due: '',
        tag: '',
        repeat: 'none',
        notifyOnStart: true,
        notifyOnDue: true,
        notifyOnOverdue: true,
        showInFocus: false,
        sortOrder: 0,
        doneAt: '',
      })
      Object.assign(task, serverTask)
      markSynced(task)
      saveLocal()
    } catch {
      // Offline — will sync later
    }

    return task
  }

  async function updateTask(clientId: string, updates: Partial<Task>) {
    const task = tasks.value.find(t => t.clientId === clientId)
    if (!task) return

    // Optimistic update
    Object.assign(task, updates)
    markPending(task)
    saveLocal()

    // Try API
    try {
      if (task.id) {
        const updated = await api.updateTask(task.id, updates)
        Object.assign(task, updated)
        markSynced(task)
        saveLocal()
      }
    } catch {
      // Offline — will sync later
    }
  }

  async function toggleDone(clientId: string) {
    const task = tasks.value.find(t => t.clientId === clientId)
    if (!task) return

    const done = !task.done
    const doneAt = done ? new Date().toISOString() : ''

    // Optimistic update
    Object.assign(task, { done, doneAt })
    markPending(task)
    saveLocal()

    // Try API
    try {
      if (task.id) {
        const updated = await api.updateTask(task.id, { done, doneAt })
        Object.assign(task, updated)
        markSynced(task)
        saveLocal()
      }
    } catch {
      // Offline — will sync later
    }
  }

  async function removeTask(clientId: string) {
    const task = tasks.value.find(t => t.clientId === clientId)
    if (!task) return

    if (!task.id) {
      tasks.value = tasks.value.filter(t => t.clientId !== clientId)
      if (selectedTaskId.value === clientId) selectedTaskId.value = null
      saveLocal()
      return
    }

    // Optimistic update
    task.deleted = true
    markPending(task)
    if (selectedTaskId.value === clientId) selectedTaskId.value = null
    saveLocal()

    // Try API
    try {
      if (task.id) {
        await api.deleteTask(task.id)
      }
      markSynced(task)
      tasks.value = tasks.value.filter(t => t.clientId !== clientId)
      saveLocal()
    } catch {
      // Offline — will sync later
    }
  }

  function selectTask(clientId: string | null) {
    selectedTaskId.value = clientId
  }

  function setView(view: 'matrix' | 'today' | 'done' | 'reports' | 'summary') {
    currentView.value = view
  }

  return {
    tasks,
    selectedTaskId,
    currentView,
    searchQuery,
    loading,
    activeTasks,
    selectedTask,
    quadrantTasks,
    todayTasks,
    doneTasks,
    conflictTasks,
    filterQuadrant,
    localOwner,
    useUser,
    mergeServerTasks,
    pendingTasks,
    markSynced,
    pruneSyncedDeleted,
    resolveConflict,
    reorderTasks,
    fetchTasks,
    addTask,
    updateTask,
    toggleDone,
    removeTask,
    selectTask,
    setView,
    saveLocal,
  }
})
