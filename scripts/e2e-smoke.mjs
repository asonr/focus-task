import { spawn } from 'node:child_process'
import { mkdtemp } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const backendDir = path.join(root, 'backend')
const port = Number(process.env.FOCUS_TASK_E2E_PORT || 8899)
const baseUrl = `http://127.0.0.1:${port}`
const python = process.env.FOCUS_TASK_PYTHON || '/Library/Frameworks/Python.framework/Versions/3.14/bin/python3.14'
const useSourceBackend = process.env.FOCUS_TASK_E2E_SOURCE === '1'
const backendBinary = path.join(backendDir, 'dist', 'focus-task-backend')
const tempDir = await mkdtemp(path.join(tmpdir(), 'focus-task-e2e-'))
const dbPath = path.join(tempDir, 'todo.db')

const command = useSourceBackend
  ? python
  : backendBinary
const args = useSourceBackend
  ? ['-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', String(port)]
  : []

const child = spawn(command, args, {
  cwd: backendDir,
  env: {
    ...process.env,
    FOCUS_TASK_BACKEND_PORT: String(port),
    FOCUS_TASK_DATABASE_URL: `sqlite:///${dbPath}`,
    FOCUS_TASK_SECRET_KEY: 'focus-task-e2e-secret',
    FOCUS_TASK_BACKEND_LOG_LEVEL: 'warning',
  },
  stdio: ['ignore', 'pipe', 'pipe'],
})

let output = ''
let exited = false
child.stdout.on('data', chunk => {
  output += chunk.toString()
})
child.stderr.on('data', chunk => {
  output += chunk.toString()
})
const childExit = new Promise(resolve => {
  child.once('exit', (code, signal) => {
    exited = true
    resolve({ code, signal })
  })
})

async function waitForHealth() {
  for (let i = 0; i < 150; i += 1) {
    if (exited) {
      throw new Error(`backend exited before health check passed\n${output}`)
    }
    try {
      const res = await fetch(`${baseUrl}/api/health`)
      const body = await res.json()
      if (res.ok && body.status === 'ok') return
    } catch {
      // backend is still starting
    }
    await new Promise(resolve => setTimeout(resolve, 200))
  }
  throw new Error(`backend health check timed out\n${output}`)
}

async function request(method, route, body, token) {
  const res = await fetch(`${baseUrl}${route}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    throw new Error(`${method} ${route} failed: ${res.status} ${JSON.stringify(data)}`)
  }
  return data
}

try {
  await waitForHealth()

  const username = `e2e_${Date.now()}`
  const password = 'password123'
  await request('POST', '/api/auth/register', { username, password })
  const login = await request('POST', '/api/auth/login', { username, password })
  const token = login.access_token

  const created = await request(
    'POST',
    '/api/tasks',
    {
      client_id: crypto.randomUUID(),
      quadrant: 1,
      title: 'E2E smoke task',
      notes: '',
      done: false,
      start_at: '',
      due: '',
      tag: 'e2e',
      repeat: 'none',
      notify_on_start: true,
      notify_on_due: true,
      notify_on_overdue: true,
      show_in_focus: false,
      sort_order: 0,
      done_at: '',
    },
    token,
  )

  const tasks = await request('GET', '/api/tasks?include_deleted=true', undefined, token)
  if (!tasks.some(task => task.client_id === created.client_id)) {
    throw new Error('created task was not returned by list API')
  }

  console.log('E2E smoke passed')
} finally {
  if (!exited) {
    child.kill('SIGINT')
    await Promise.race([
      childExit,
      new Promise(resolve => setTimeout(resolve, 3000)),
    ])
  }
}
