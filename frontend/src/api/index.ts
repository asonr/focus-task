/**
 * API client for Focus Task backend.
 * Handles snake_case ↔ camelCase conversion transparently.
 */
import type { Task } from '@/stores/taskStore'
import { loadAuthState } from '@/utils/secureStorage'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8765'
const LOCAL_BACKEND = /^http:\/\/(127\.0\.0\.1|localhost):8765$/.test(API_BASE)
const STARTUP_RETRY_DELAYS = [150, 250, 400, 650, 1000, 1500]

// ─── Case conversion ───
function toSnake(obj: any): any {
  if (Array.isArray(obj)) return obj.map(toSnake)
  if (obj && typeof obj === 'object') {
    const out: any = {}
    for (const key of Object.keys(obj)) {
      const snake = key.replace(/[A-Z]/g, m => '_' + m.toLowerCase())
      out[snake] = toSnake(obj[key])
    }
    return out
  }
  return obj
}

function toCamel(obj: any): any {
  if (Array.isArray(obj)) return obj.map(toCamel)
  if (obj && typeof obj === 'object') {
    const out: any = {}
    for (const key of Object.keys(obj)) {
      const camel = key.replace(/_([a-z])/g, (_, c) => c.toUpperCase())
      out[camel] = toCamel(obj[key])
    }
    return out
  }
  return obj
}

function formatApiError(err: any): string {
  const detail = err?.detail
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0]
    const field = Array.isArray(first?.loc) ? first.loc[first.loc.length - 1] : ''
    const message = typeof first?.msg === 'string' ? first.msg : ''

    if (field === 'password' && message.includes('at least')) {
      const minLengthMatch = message.match(/at least (\d+)/)
      const minLength = minLengthMatch?.[1]
      return minLength ? `密码至少需要 ${minLength} 个字符` : '密码长度不符合要求'
    }

    if (field === 'username' && message.includes('at least')) {
      return '用户名至少需要 2 个字符'
    }

    return message || '请求参数不正确'
  }

  if (typeof detail === 'string' && detail.trim()) {
    return detail
  }

  return err?.message || '请求失败'
}

// ─── HTTP helpers ───
function sleep(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

async function fetchWithStartupRetry(url: string, options: RequestInit): Promise<Response> {
  let lastError: unknown
  const delays = LOCAL_BACKEND ? STARTUP_RETRY_DELAYS : []

  for (let attempt = 0; attempt <= delays.length; attempt += 1) {
    try {
      return await fetch(url, options)
    } catch (err) {
      lastError = err
      if (attempt === delays.length) break
      await sleep(delays[attempt])
    }
  }

  throw lastError
}

async function request(method: string, path: string, body?: any): Promise<any> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  const token = (await loadAuthState()).token
  if (token) headers['Authorization'] = `Bearer ${token}`

  let res: Response
  try {
    res = await fetchWithStartupRetry(`${API_BASE}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(toSnake(body)) : undefined,
    })
  } catch {
    throw new Error(`无法连接 Focus Task 后端服务（${API_BASE}）。如果刚打开 App，请稍等几秒后重试；也请检查本机端口是否被其它应用占用。`)
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(formatApiError(err) || res.statusText)
  }
  const data = await res.json()
  return toCamel(data)
}

// ─── Auth API ───
export async function register(username: string, password: string) {
  return request('POST', '/api/auth/register', { username, password })
}

export async function login(username: string, password: string): Promise<{ accessToken: string }> {
  return request('POST', '/api/auth/login', { username, password })
}

export async function getMe() {
  return request('GET', '/api/auth/me')
}

// ─── Task API ───
export async function listTasks(includeDeleted = false): Promise<Task[]> {
  return request('GET', `/api/tasks?include_deleted=${includeDeleted}`)
}

export async function createTask(task: Partial<Task> & { clientId: string }): Promise<Task> {
  return request('POST', '/api/tasks', task)
}

export async function getTask(taskId: number): Promise<Task> {
  return request('GET', `/api/tasks/${taskId}`)
}

export async function updateTask(taskId: number, updates: Partial<Task>): Promise<Task> {
  return request('PATCH', `/api/tasks/${taskId}`, updates)
}

export async function deleteTask(taskId: number): Promise<void> {
  return request('DELETE', `/api/tasks/${taskId}`)
}

export async function reorderTasks(items: { clientId: string; sortOrder: number }[]): Promise<void> {
  return request('POST', '/api/tasks/reorder', { items })
}

// ─── Sync API ───
export async function syncPush(tasks: Partial<Task>[]): Promise<Task[]> {
  return request('POST', '/api/tasks/sync/push', { tasks })
}

export async function syncPull(since?: string): Promise<Task[]> {
  return request('POST', '/api/tasks/sync/pull', { since })
}
