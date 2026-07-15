import { invoke } from '@tauri-apps/api/core'

const TOKEN_KEY = 'focus-task-token'
const USERNAME_KEY = 'focus-task-username'
const REMEMBERED_USERNAME_KEY = 'focus-task-remembered-username'

interface AuthState {
  token: string
  username: string
}

function hasWindow(name: string): boolean {
  return typeof window !== 'undefined' && name in window
}

function isTauriRuntime(): boolean {
  return hasWindow('__TAURI_INTERNALS__') || hasWindow('__TAURI__')
}

function loadBrowserAuthState(): AuthState {
  return {
    token: localStorage.getItem(TOKEN_KEY) || '',
    username: localStorage.getItem(USERNAME_KEY) || '',
  }
}

function saveBrowserAuthState(state: AuthState) {
  localStorage.setItem(TOKEN_KEY, state.token)
  localStorage.setItem(USERNAME_KEY, state.username)
}

function clearBrowserAuthState() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USERNAME_KEY)
}

export async function loadAuthState(): Promise<AuthState> {
  if (!isTauriRuntime()) return loadBrowserAuthState()

  try {
    const state = await invoke<AuthState | null>('load_auth_state')
    if (!state?.token) return loadBrowserAuthState()
    return state
  } catch {
    return loadBrowserAuthState()
  }
}

export async function saveAuthState(state: AuthState): Promise<void> {
  saveBrowserAuthState(state)
  if (!isTauriRuntime()) return

  try {
    await invoke('save_auth_state', { state })
  } catch {
    // Keep browser storage as fallback in dev/browser mode.
  }
}

export async function clearAuthState(): Promise<void> {
  clearBrowserAuthState()
  if (!isTauriRuntime()) return

  try {
    await invoke('clear_auth_state')
  } catch {
    // Browser storage is already cleared.
  }
}

export function loadRememberedUsername(): string {
  return localStorage.getItem(REMEMBERED_USERNAME_KEY) || ''
}

export function saveRememberedUsername(username: string) {
  localStorage.setItem(REMEMBERED_USERNAME_KEY, username)
}

export function clearRememberedUsername() {
  localStorage.removeItem(REMEMBERED_USERNAME_KEY)
}
