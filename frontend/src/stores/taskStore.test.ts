import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/api', () => ({
  reorderTasks: vi.fn(),
}))

import * as api from '@/api'
import { useTaskStore, type Task } from './taskStore'

function makeTask(clientId: string, sortOrder: number): Task {
  return {
    id: sortOrder + 1,
    clientId,
    quadrant: 1,
    title: clientId,
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
    sortOrder,
    doneAt: '',
    deleted: false,
    updatedAt: '2026-06-12T00:00:00.000Z',
    syncStatus: 'synced',
  }
}

describe('taskStore reorderTasks', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('persists sort order locally and marks tasks synced when API succeeds', async () => {
    vi.mocked(api.reorderTasks).mockResolvedValue(undefined)

    const store = useTaskStore()
    store.tasks = [makeTask('a', 0), makeTask('b', 1)]

    await store.reorderTasks([
      { clientId: 'b', sortOrder: 0 },
      { clientId: 'a', sortOrder: 1 },
    ])

    expect(api.reorderTasks).toHaveBeenCalledWith([
      { clientId: 'b', sortOrder: 0 },
      { clientId: 'a', sortOrder: 1 },
    ])
    expect(store.tasks.find(t => t.clientId === 'b')?.sortOrder).toBe(0)
    expect(store.tasks.find(t => t.clientId === 'a')?.sortOrder).toBe(1)
    expect(store.tasks.every(t => t.syncStatus === 'synced')).toBe(true)
  })

  it('keeps reordered tasks pending when API fails', async () => {
    vi.mocked(api.reorderTasks).mockRejectedValue(new Error('offline'))

    const store = useTaskStore()
    store.tasks = [makeTask('a', 0), makeTask('b', 1)]

    await store.reorderTasks([
      { clientId: 'b', sortOrder: 0 },
      { clientId: 'a', sortOrder: 1 },
    ])

    expect(store.tasks.find(t => t.clientId === 'b')?.sortOrder).toBe(0)
    expect(store.tasks.find(t => t.clientId === 'a')?.sortOrder).toBe(1)
    expect(store.tasks.every(t => t.syncStatus === 'pending')).toBe(true)
  })
})
