import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/api', () => ({
  syncPush: vi.fn(),
  syncPull: vi.fn(),
}))

import * as api from '@/api'
import { useAuthStore } from './authStore'
import { useSyncStore } from './syncStore'
import { useTaskStore } from './taskStore'

function resetStorage() {
  localStorage.clear()
}

describe('syncStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    resetStorage()
    vi.clearAllMocks()
  })

  it('pushes only pending tasks and marks them synced', async () => {
    const auth = useAuthStore()
    auth.token = 'token'
    auth.username = 'alice'
    auth.isLoggedIn = true
    auth.ready = true

    const taskStore = useTaskStore()
    taskStore.tasks = [
      {
        id: 1,
        clientId: 'pending-task',
        quadrant: 1,
        title: 'Pending',
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
        updatedAt: '2026-06-12T00:00:00.000Z',
        syncStatus: 'pending',
      },
      {
        id: 2,
        clientId: 'synced-task',
        quadrant: 2,
        title: 'Synced',
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
        updatedAt: '2026-06-11T00:00:00.000Z',
        syncStatus: 'synced',
      },
    ]

    vi.mocked(api.syncPush).mockResolvedValue([
      {
        ...taskStore.tasks[0],
        updatedAt: '2026-06-12T01:00:00.000Z',
      },
    ])
    vi.mocked(api.syncPull).mockResolvedValue([])

    const syncStore = useSyncStore()
    await syncStore.sync()

    expect(api.syncPush).toHaveBeenCalledTimes(1)
    expect(vi.mocked(api.syncPush).mock.calls[0][0]).toHaveLength(1)
    expect(vi.mocked(api.syncPush).mock.calls[0][0][0].clientId).toBe('pending-task')
    expect(taskStore.tasks[0].syncStatus).toBe('synced')
  })

  it('keeps local pending changes when pull returns an older server copy', async () => {
    const auth = useAuthStore()
    auth.token = 'token'
    auth.username = 'alice'
    auth.isLoggedIn = true
    auth.ready = true

    const taskStore = useTaskStore()
    taskStore.tasks = [
      {
        id: 1,
        clientId: 'task-1',
        quadrant: 1,
        title: 'Local title',
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
        updatedAt: '2026-06-12T02:00:00.000Z',
        syncStatus: 'pending',
      },
    ]

    vi.mocked(api.syncPush).mockResolvedValue([])
    vi.mocked(api.syncPull).mockResolvedValue([
      {
        ...taskStore.tasks[0],
        title: 'Server title',
        updatedAt: '2026-06-12T01:00:00.000Z',
      },
    ])

    const syncStore = useSyncStore()
    await syncStore.sync()

    expect(taskStore.tasks[0].title).toBe('Local title')
    expect(taskStore.tasks[0].syncStatus).toBe('pending')
  })

  it('marks conflicts when pull returns a newer server copy over local pending changes', async () => {
    const auth = useAuthStore()
    auth.token = 'token'
    auth.username = 'alice'
    auth.isLoggedIn = true
    auth.ready = true

    const taskStore = useTaskStore()
    taskStore.tasks = [
      {
        id: 1,
        clientId: 'task-1',
        quadrant: 1,
        title: 'Local title',
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
        updatedAt: '2026-06-12T01:00:00.000Z',
        syncStatus: 'pending',
      },
    ]

    vi.mocked(api.syncPush).mockResolvedValue([])
    vi.mocked(api.syncPull).mockResolvedValue([
      {
        ...taskStore.tasks[0],
        title: 'Server title',
        updatedAt: '2026-06-12T02:00:00.000Z',
      },
    ])

    const syncStore = useSyncStore()
    await syncStore.sync()

    expect(taskStore.tasks[0].title).toBe('Local title')
    expect(taskStore.tasks[0].syncStatus).toBe('conflict')
    expect(taskStore.tasks[0].conflictServer?.title).toBe('Server title')

    taskStore.resolveConflict('task-1', 'server')
    expect(taskStore.tasks[0].title).toBe('Server title')
    expect(taskStore.tasks[0].syncStatus).toBe('synced')
  })
})
