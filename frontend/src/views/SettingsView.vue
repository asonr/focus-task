<template>
  <div class="settings-page">
    <section class="settings-topbar">
      <div class="settings-heading">
        <span class="settings-eyebrow">设置</span>
        <h1>提醒与时间偏好</h1>
        <p>统一控制提醒节奏、轮询频率和新任务默认时间。</p>
      </div>
    </section>

    <section class="settings-grid">
      <article class="settings-card">
        <div class="card-head">
          <div>
            <span class="card-kicker">外观</span>
            <h2>主题模式</h2>
          </div>
        </div>

        <div class="field-block">
          <label>应用外观</label>
          <div class="segment-control">
            <button
              v-for="option in themeOptions"
              :key="option.value"
              class="segment-btn"
              :class="{ active: theme.mode.value === option.value }"
              @click="theme.setMode(option.value)"
            >
              {{ option.icon }} {{ option.label }}
            </button>
          </div>
          <p class="field-note">{{ themeHint }}</p>
        </div>
      </article>

      <article class="settings-card">
        <div class="card-head">
          <div>
            <span class="card-kicker">提醒策略</span>
            <h2>默认提醒时间</h2>
          </div>
        </div>

        <div class="field-block">
          <label>开始/截止提醒</label>
          <div class="segment-control">
            <button
              v-for="option in leadOptions"
              :key="option.value"
              class="segment-btn"
              :class="{ active: settings.state.reminderLeadMinutes === option.value }"
              @click="settings.update({ reminderLeadMinutes: option.value })"
            >
              {{ option.label }}
            </button>
          </div>
          <p class="field-note">当前：{{ settings.reminderLeadLabel }}</p>
        </div>

        <div class="field-block">
          <label>检查频率</label>
          <div class="segment-control narrow">
            <button
              v-for="option in intervalOptions"
              :key="option.value"
              class="segment-btn"
              :class="{ active: settings.state.notificationCheckIntervalSeconds === option.value }"
              @click="settings.update({ notificationCheckIntervalSeconds: option.value })"
            >
              {{ option.label }}
            </button>
          </div>
          <p class="field-note">应用运行期间按这个频率检查提醒。</p>
        </div>
      </article>

      <article class="settings-card">
        <div class="card-head">
          <div>
            <span class="card-kicker">默认值</span>
            <h2>新任务时间</h2>
          </div>
        </div>

        <div class="time-grid">
          <div class="field-block">
            <label>默认开始时间</label>
            <input
              type="time"
              :value="settings.state.defaultStartTime"
              @change="settings.update({ defaultStartTime: ($event.target as HTMLInputElement).value || '09:00' })"
            />
          </div>

          <div class="field-block">
            <label>默认截止时间</label>
            <input
              type="time"
              :value="settings.state.defaultDueTime"
              @change="settings.update({ defaultDueTime: ($event.target as HTMLInputElement).value || '18:00' })"
            />
          </div>
        </div>

        <p class="field-note">旧任务不会被强制改写，新的日期输入会优先用这里的默认时间。</p>
      </article>

      <article class="settings-card">
        <div class="card-head">
          <div>
            <span class="card-kicker">系统权限</span>
            <h2>通知权限</h2>
          </div>
          <span class="permission-badge" :class="settings.notificationPermission">
            {{ permissionLabel }}
          </span>
        </div>

          <div class="permission-panel">
          <p>{{ permissionHint }}</p>
          <div class="permission-actions">
            <button class="primary-btn" @click="handleNotificationAction">
              {{ settings.notificationActionLabel }}
            </button>
            <button class="secondary-btn" @click="sendTestNotification">发送测试通知</button>
            <button class="secondary-btn" @click="settings.refreshPermission()">刷新状态</button>
          </div>
        </div>
      </article>

      <article class="settings-card backup-card">
        <div class="card-head">
          <div>
            <span class="card-kicker">数据安全</span>
            <h2>备份与恢复</h2>
          </div>
          <span class="permission-badge granted">JSON v1</span>
        </div>

        <div class="backup-columns">
          <section class="backup-section">
            <div class="backup-section-head">
              <div>
                <strong>当前账号</strong>
                <p>导出或恢复 {{ auth.username }} 的全部任务。</p>
              </div>
            </div>
            <div class="permission-actions">
              <button class="primary-btn" :disabled="backupBusy" @click="exportCurrentUser">
                {{ backupBusy ? '处理中…' : '导出 JSON' }}
              </button>
              <button class="secondary-btn" :disabled="backupBusy" @click="userBackupInput?.click()">选择备份</button>
              <input ref="userBackupInput" class="hidden-file" type="file" accept="application/json,.json" @change="selectUserBackup" />
            </div>

            <div v-if="pendingUserBackup" class="restore-preview">
              <div>
                <strong>{{ pendingUserBackup.tasks.length }} 项任务</strong>
                <span>{{ pendingUserBackup.username }} · {{ formatDateTime(pendingUserBackup.exportedAt) }}</span>
              </div>
              <div class="permission-actions">
                <button class="primary-btn" :disabled="backupBusy" @click="restoreUserBackup('merge')">合并导入</button>
                <button class="secondary-btn danger-text" :disabled="backupBusy" @click="restoreUserBackup('replace')">覆盖当前账号</button>
                <button class="secondary-btn" :disabled="backupBusy" @click="pendingUserBackup = null">取消</button>
              </div>
            </div>
          </section>

          <section v-if="auth.isAdmin" class="backup-section server-backup-section">
            <div class="backup-section-head">
              <div>
                <strong>服务器快照</strong>
                <p>完整保存用户、密码哈希和任务数据库。</p>
              </div>
              <button class="secondary-btn" :disabled="serverBusy" @click="loadSnapshots">刷新</button>
            </div>
            <div class="permission-actions">
              <button class="primary-btn" :disabled="serverBusy" @click="createSnapshot">创建快照</button>
              <button class="secondary-btn danger-text" :disabled="serverBusy" @click="serverBackupInput?.click()">上传并恢复</button>
              <input ref="serverBackupInput" class="hidden-file" type="file" accept=".db,application/vnd.sqlite3" @change="restoreServerBackup" />
            </div>

            <div class="snapshot-list">
              <div v-if="snapshots.length === 0" class="snapshot-empty">暂无服务器快照</div>
              <div v-for="snapshot in snapshots" :key="snapshot.name" class="snapshot-row">
                <div>
                  <strong>{{ snapshot.name }}</strong>
                  <span>{{ formatBytes(snapshot.size) }} · {{ formatDateTime(snapshot.createdAt) }}</span>
                </div>
                <div class="snapshot-actions">
                  <template v-if="pendingDeleteSnapshotName === snapshot.name">
                    <button class="mini-btn" :disabled="serverBusy" @click="pendingDeleteSnapshotName = ''">取消</button>
                    <button class="mini-btn danger confirm-danger" :disabled="serverBusy" @click="confirmDeleteSnapshot(snapshot)">确认删除</button>
                  </template>
                  <template v-else>
                    <button class="mini-btn" :disabled="serverBusy" @click="downloadSnapshot(snapshot)">下载</button>
                    <button class="mini-btn danger" :disabled="serverBusy" @click="pendingDeleteSnapshotName = snapshot.name">删除</button>
                  </template>
                </div>
              </div>
            </div>
          </section>
        </div>

        <p v-if="backupError" class="settings-error">{{ backupError }}</p>
        <p v-if="backupMessage" class="settings-success">{{ backupMessage }}</p>
      </article>

      <article class="settings-card user-admin-card">
        <div class="card-head">
          <div>
            <span class="card-kicker">账号</span>
            <h2>用户管理</h2>
          </div>
          <button v-if="auth.isAdmin" class="secondary-btn" @click="loadUsers" :disabled="usersLoading">
            {{ usersLoading ? '刷新中…' : '刷新' }}
          </button>
        </div>

        <div v-if="!auth.isAdmin" class="permission-panel">
          <p>当前账号不是管理员，不能查看或维护其他用户。</p>
        </div>

        <div v-else class="user-admin-panel">
          <div class="user-admin-summary">
            <span>当前管理员：{{ auth.username }}</span>
            <span>{{ users.length }} 个账号</span>
          </div>

          <p v-if="usersError" class="settings-error">{{ usersError }}</p>
          <p v-if="usersMessage" class="settings-success">{{ usersMessage }}</p>

          <div class="user-table">
            <div class="user-row user-row-head">
              <span>用户</span>
              <span>权限</span>
              <span>状态</span>
              <span>任务</span>
              <span>操作</span>
            </div>

            <div v-for="user in users" :key="user.id" class="user-row">
              <div class="user-name-cell">
                <strong>{{ user.username }}</strong>
                <small>{{ formatDate(user.createdAt) }}</small>
              </div>
              <span class="user-badge" :class="{ admin: user.isAdmin }">
                {{ user.isAdmin ? '管理员' : '普通用户' }}
              </span>
              <span class="user-badge" :class="{ disabled: user.disabled, active: !user.disabled }">
                {{ user.disabled ? '已禁用' : '可登录' }}
              </span>
              <span class="task-count">{{ user.taskCount }}</span>
              <div class="user-actions">
                <button
                  class="mini-btn"
                  :disabled="isSelf(user.id) || actionBusy"
                  @click="toggleUserAdmin(user)"
                >
                  {{ user.isAdmin ? '取消管理员' : '设为管理员' }}
                </button>
                <button
                  class="mini-btn"
                  :disabled="isSelf(user.id) || actionBusy"
                  @click="toggleUserDisabled(user)"
                >
                  {{ user.disabled ? '启用' : '禁用' }}
                </button>
                <button class="mini-btn" :disabled="actionBusy" @click="startPasswordReset(user.id)">
                  重置密码
                </button>
                <button
                  class="mini-btn danger"
                  :disabled="isSelf(user.id) || actionBusy"
                  @click="removeUser(user)"
                >
                  删除
                </button>
              </div>

              <div v-if="resetUserId === user.id" class="password-reset-row">
                <input
                  v-model="resetPassword"
                  type="password"
                  placeholder="输入新密码，至少 8 位"
                  @keydown.enter="confirmPasswordReset(user)"
                  @keydown.escape="cancelPasswordReset"
                />
                <button class="primary-btn" :disabled="actionBusy" @click="confirmPasswordReset(user)">确认重置</button>
                <button class="secondary-btn" :disabled="actionBusy" @click="cancelPasswordReset">取消</button>
              </div>
            </div>
          </div>
        </div>
      </article>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { invoke } from '@tauri-apps/api/core'
import * as api from '@/api'
import type { ServerSnapshot, UserAccount, UserBackup } from '@/api'
import { useAuthStore } from '@/stores/authStore'
import { useSettingsStore, type ReminderLeadMinutes } from '@/stores/settingsStore'
import { useTaskStore } from '@/stores/taskStore'
import { useTheme, type ThemeMode } from '@/composables/useTheme'

const settings = useSettingsStore()
const theme = useTheme()
const auth = useAuthStore()
const taskStore = useTaskStore()

const users = ref<UserAccount[]>([])
const usersLoading = ref(false)
const usersError = ref('')
const usersMessage = ref('')
const actionBusy = ref(false)
const resetUserId = ref<number | null>(null)
const resetPassword = ref('')
const backupBusy = ref(false)
const serverBusy = ref(false)
const backupError = ref('')
const backupMessage = ref('')
const pendingUserBackup = ref<UserBackup | null>(null)
const snapshots = ref<ServerSnapshot[]>([])
const userBackupInput = ref<HTMLInputElement | null>(null)
const serverBackupInput = ref<HTMLInputElement | null>(null)
const pendingDeleteSnapshotName = ref('')

const themeOptions: { label: string; icon: string; value: ThemeMode }[] = [
  { label: '亮色', icon: '☀️', value: 'light' },
  { label: '暗色', icon: '🌙', value: 'dark' },
  { label: '跟随系统', icon: '💻', value: 'system' },
]

const themeHint = computed(() => {
  if (theme.mode.value === 'light') return '始终使用亮色外观，不跟随系统设置。'
  if (theme.mode.value === 'dark') return '始终使用暗色外观，不跟随系统设置。'
  return '自动跟随 macOS 系统外观设置切换亮色/暗色模式。'
})

const leadOptions: { label: string; value: ReminderLeadMinutes }[] = [
  { label: '准点', value: 0 },
  { label: '提前 5 分', value: 5 },
  { label: '提前 10 分', value: 10 },
  { label: '提前 30 分', value: 30 },
]

const intervalOptions = [
  { label: '30 秒', value: 30 as const },
  { label: '60 秒', value: 60 as const },
]

const permissionLabel = computed(() => {
  if (settings.notificationPermission === 'granted') return '已允许'
  if (settings.notificationPermission === 'denied') return '已拒绝'
  return '未决定'
})

const permissionHint = computed(() => {
  if (settings.notificationPermission === 'granted') {
    return '系统通知已开启。应用运行时会按你设置的策略检查任务并发送提醒。'
  }
  if (settings.notificationPermission === 'denied') {
    return '通知权限已被系统拒绝。macOS 不会再次弹出授权框，需要到系统设置里手动重新允许。'
  }
  return '当前版本优先使用系统通知权限，必要时会回退到桌面原生通知。应用运行时会按你设置的策略检查任务。'
})

async function handleNotificationAction() {
  if (settings.notificationPermission === 'denied') {
    await settings.openNotificationSettings()
    return
  }
  await settings.requestNotificationPermission()
}

async function sendTestNotification() {
  await settings.sendTestNotification()
}

function formatDate(value: string) {
  return value ? new Date(value).toLocaleDateString() : ''
}

function formatDateTime(value: string) {
  return value ? new Date(value).toLocaleString() : ''
}

function formatBytes(bytes: number) {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

function isTauriRuntime() {
  return '__TAURI_INTERNALS__' in window || '__TAURI__' in window
}

async function saveJsonFile(filename: string, content: string): Promise<boolean> {
  if (isTauriRuntime()) {
    return invoke<boolean>('save_text_file', { filename, content })
  }
  downloadBlob(new Blob([content], { type: 'application/json' }), filename)
  return true
}

function showBackupMessage(message: string) {
  backupMessage.value = message
  window.setTimeout(() => {
    if (backupMessage.value === message) backupMessage.value = ''
  }, 4000)
}

async function exportCurrentUser() {
  backupBusy.value = true
  backupError.value = ''
  try {
    const backup = await api.exportUserBackup()
    const date = new Date().toISOString().slice(0, 10)
    const saved = await saveJsonFile(
      `focus-task-${auth.username}-${date}.json`,
      JSON.stringify(backup, null, 2),
    )
    if (saved) showBackupMessage(`已导出 ${backup.tasks.length} 项任务`)
  } catch (e: any) {
    backupError.value = e?.message || '数据导出失败'
  } finally {
    backupBusy.value = false
  }
}

async function selectUserBackup(event: Event) {
  backupError.value = ''
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  try {
    const parsed = JSON.parse(await file.text()) as UserBackup
    if (parsed.format !== 'focus-task-backup' || parsed.version !== 1 || !Array.isArray(parsed.tasks)) {
      throw new Error('备份格式或版本不受支持')
    }
    pendingUserBackup.value = parsed
  } catch (e: any) {
    backupError.value = e?.message || '无法读取备份文件'
  }
}

async function restoreUserBackup(mode: 'merge' | 'replace') {
  if (!pendingUserBackup.value) return
  if (mode === 'replace' && !window.confirm('覆盖恢复会删除当前账号已有任务，然后导入备份。确定继续？')) return
  backupBusy.value = true
  backupError.value = ''
  try {
    const result = await api.importUserBackup(pendingUserBackup.value, mode)
    await taskStore.reloadTasks()
    pendingUserBackup.value = null
    showBackupMessage(`恢复完成：新增 ${result.created}，更新 ${result.updated}，跳过 ${result.skipped}`)
  } catch (e: any) {
    backupError.value = e?.message || '数据恢复失败'
  } finally {
    backupBusy.value = false
  }
}

async function loadSnapshots() {
  if (!auth.isAdmin) return
  serverBusy.value = true
  backupError.value = ''
  try {
    snapshots.value = await api.listServerSnapshots()
  } catch (e: any) {
    backupError.value = e?.message || '快照列表加载失败'
  } finally {
    serverBusy.value = false
  }
}

async function createSnapshot() {
  serverBusy.value = true
  backupError.value = ''
  try {
    const snapshot = await api.createServerSnapshot()
    snapshots.value = [snapshot, ...snapshots.value.filter(item => item.name !== snapshot.name)]
    showBackupMessage(`服务器快照已创建：${snapshot.name}`)
  } catch (e: any) {
    backupError.value = e?.message || '创建服务器快照失败'
  } finally {
    serverBusy.value = false
  }
}

async function downloadSnapshot(snapshot: ServerSnapshot) {
  serverBusy.value = true
  backupError.value = ''
  try {
    downloadBlob(await api.downloadServerSnapshot(snapshot.name), snapshot.name)
  } catch (e: any) {
    backupError.value = e?.message || '快照下载失败'
  } finally {
    serverBusy.value = false
  }
}

async function confirmDeleteSnapshot(snapshot: ServerSnapshot) {
  serverBusy.value = true
  backupError.value = ''
  try {
    await api.deleteServerSnapshot(snapshot.name)
    snapshots.value = snapshots.value.filter(item => item.name !== snapshot.name)
    pendingDeleteSnapshotName.value = ''
    showBackupMessage('服务器快照已删除')
  } catch (e: any) {
    backupError.value = e?.message || '快照删除失败'
  } finally {
    serverBusy.value = false
  }
}

async function restoreServerBackup(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file || !window.confirm(`从 ${file.name} 恢复整个服务器数据库？系统会先自动创建当前数据快照。`)) return
  serverBusy.value = true
  backupError.value = ''
  try {
    const result = await api.restoreServerSnapshot(file)
    showBackupMessage(`服务器已恢复，恢复前快照：${result.safetySnapshot}`)
    await loadSnapshots()
    await taskStore.reloadTasks()
  } catch (e: any) {
    backupError.value = e?.message || '服务器恢复失败'
  } finally {
    serverBusy.value = false
  }
}

function isSelf(userId: number) {
  return auth.userId === userId
}

function showUserMessage(message: string) {
  usersMessage.value = message
  window.setTimeout(() => {
    if (usersMessage.value === message) usersMessage.value = ''
  }, 2400)
}

async function loadUsers() {
  if (!auth.isAdmin) return
  usersLoading.value = true
  usersError.value = ''
  try {
    users.value = await api.listUsers()
  } catch (e: any) {
    usersError.value = e?.message || '用户列表加载失败'
  } finally {
    usersLoading.value = false
  }
}

async function updateUserFlags(user: UserAccount, updates: { isAdmin?: boolean; disabled?: boolean }, message: string) {
  actionBusy.value = true
  usersError.value = ''
  try {
    const updated = await api.updateUser(user.id, updates)
    users.value = users.value.map(item => item.id === user.id ? updated : item)
    showUserMessage(message)
  } catch (e: any) {
    usersError.value = e?.message || '用户更新失败'
  } finally {
    actionBusy.value = false
  }
}

function toggleUserAdmin(user: UserAccount) {
  updateUserFlags(user, { isAdmin: !user.isAdmin }, user.isAdmin ? '已取消管理员权限' : '已设为管理员')
}

function toggleUserDisabled(user: UserAccount) {
  updateUserFlags(user, { disabled: !user.disabled }, user.disabled ? '账号已启用' : '账号已禁用')
}

function startPasswordReset(userId: number) {
  resetUserId.value = userId
  resetPassword.value = ''
  usersError.value = ''
}

function cancelPasswordReset() {
  resetUserId.value = null
  resetPassword.value = ''
}

async function confirmPasswordReset(user: UserAccount) {
  if (resetPassword.value.length < 8) {
    usersError.value = '新密码至少需要 8 位'
    return
  }
  actionBusy.value = true
  usersError.value = ''
  try {
    await api.resetUserPassword(user.id, resetPassword.value)
    cancelPasswordReset()
    showUserMessage(`已重置 ${user.username} 的密码`)
  } catch (e: any) {
    usersError.value = e?.message || '密码重置失败'
  } finally {
    actionBusy.value = false
  }
}

async function removeUser(user: UserAccount) {
  if (!window.confirm(`删除账号 ${user.username}？该用户的任务也会被删除。`)) return
  actionBusy.value = true
  usersError.value = ''
  try {
    await api.deleteUser(user.id)
    users.value = users.value.filter(item => item.id !== user.id)
    showUserMessage(`已删除 ${user.username}`)
  } catch (e: any) {
    usersError.value = e?.message || '删除用户失败'
  } finally {
    actionBusy.value = false
  }
}

onMounted(() => {
  loadUsers()
  loadSnapshots()
})
</script>

<style scoped>
.settings-page {
  height: 100%;
  overflow-y: auto;
  padding: 18px 20px 28px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  background: linear-gradient(180deg, oklch(98.8% 0.003 240), oklch(97.8% 0.004 240));
}

.settings-topbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

.settings-heading {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.settings-eyebrow,
.card-kicker {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.settings-heading h1 {
  font-size: 28px;
  line-height: 1.1;
  font-weight: 600;
  color: var(--text-primary);
}

.settings-heading p {
  font-size: 14px;
  line-height: 1.5;
  color: var(--text-secondary);
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.settings-card {
  background: oklch(99.5% 0.002 240 / 0.96);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  box-shadow: 0 12px 28px oklch(0% 0 0 / 0.03);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.user-admin-card {
  grid-column: 1 / -1;
}

.backup-card {
  grid-column: 1 / -1;
}

.backup-columns {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.backup-section {
  min-width: 0;
  padding: 14px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--surface);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.backup-section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.backup-section-head strong,
.restore-preview strong,
.snapshot-row strong {
  color: var(--text-primary);
  font-size: 13px;
}

.snapshot-actions {
  flex-shrink: 0;
  display: flex;
  gap: 6px;
}

.backup-section-head p {
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.45;
}

.hidden-file {
  display: none;
}

.restore-preview {
  padding: 10px;
  border: 1px solid oklch(58% 0.11 240 / 0.28);
  border-radius: 8px;
  background: oklch(97% 0.012 240);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.restore-preview > div:first-child,
.snapshot-row > div {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.restore-preview span,
.snapshot-row span {
  color: var(--text-muted);
  font-size: 11px;
}

.danger-text {
  color: oklch(50% 0.17 25);
}

.snapshot-list {
  max-height: 190px;
  overflow-y: auto;
  border-top: 1px solid var(--border-subtle);
}

.snapshot-row {
  min-height: 48px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  border-bottom: 1px solid var(--border-subtle);
}

.snapshot-row strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.snapshot-empty {
  padding: 16px 0;
  text-align: center;
  color: var(--text-muted);
  font-size: 12px;
}

.card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.card-head h2 {
  margin-top: 3px;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.field-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.field-block label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
}

.field-note {
  font-size: 12px;
  line-height: 1.45;
  color: var(--text-muted);
}

.time-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.time-grid input {
  width: 100%;
  height: 38px;
  padding: 0 10px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--surface-mid);
  color: var(--text-primary);
  font: inherit;
  font-size: 14px;
  outline: none;
}

.time-grid input:focus {
  border-color: oklch(58% 0.11 240);
  box-shadow: 0 0 0 3px oklch(58% 0.11 240 / 0.12);
}

.permission-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.permission-panel p {
  font-size: 13px;
  line-height: 1.5;
  color: var(--text-secondary);
}

.permission-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.primary-btn,
.secondary-btn {
  height: 34px;
  padding: 0 12px;
  border-radius: 8px;
  font: inherit;
  font-size: 13px;
  cursor: pointer;
}

.primary-btn {
  border: none;
  background: oklch(58% 0.11 240);
  color: white;
}

.secondary-btn {
  border: 1px solid var(--border-subtle);
  background: var(--surface);
  color: var(--text-primary);
}

.primary-btn:disabled,
.secondary-btn:disabled,
.mini-btn:disabled {
  opacity: 0.48;
  cursor: not-allowed;
}

.permission-badge {
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}

.permission-badge.granted {
  background: oklch(96% 0.018 145);
  color: oklch(45% 0.1 145);
}

.permission-badge.denied {
  background: oklch(96% 0.03 25);
  color: oklch(52% 0.16 25);
}

.permission-badge.default {
  background: var(--surface-mid);
  color: var(--text-secondary);
}

.user-admin-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.user-admin-summary {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: var(--text-muted);
  font-size: 12px;
}

.settings-error,
.settings-success {
  margin: 0;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 12px;
  line-height: 1.4;
}

.settings-error {
  background: oklch(96% 0.03 25);
  color: oklch(50% 0.16 25);
}

.settings-success {
  background: oklch(96% 0.018 145);
  color: oklch(43% 0.1 145);
}

.user-table {
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  overflow: hidden;
  background: var(--surface);
}

.user-row {
  display: grid;
  grid-template-columns: minmax(160px, 1.2fr) 96px 82px 58px minmax(360px, 1.8fr);
  gap: 10px;
  align-items: center;
  padding: 10px 12px;
  border-top: 1px solid var(--border-subtle);
}

.user-row:first-child {
  border-top: 0;
}

.user-row-head {
  min-height: 34px;
  padding-top: 8px;
  padding-bottom: 8px;
  background: oklch(98% 0.004 240);
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.user-name-cell {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.user-name-cell strong {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-primary);
  font-size: 14px;
}

.user-name-cell small {
  color: var(--text-muted);
  font-size: 11px;
}

.user-badge {
  width: fit-content;
  border-radius: 999px;
  padding: 3px 8px;
  background: var(--surface-mid);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}

.user-badge.admin {
  background: oklch(95% 0.025 240);
  color: oklch(44% 0.12 240);
}

.user-badge.active {
  background: oklch(96% 0.018 145);
  color: oklch(43% 0.1 145);
}

.user-badge.disabled {
  background: oklch(96% 0.03 25);
  color: oklch(50% 0.16 25);
}

.task-count {
  font-size: 13px;
  color: var(--text-secondary);
}

.user-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.mini-btn {
  height: 28px;
  padding: 0 9px;
  border: 1px solid var(--border-subtle);
  border-radius: 7px;
  background: var(--surface);
  color: var(--text-primary);
  font: inherit;
  font-size: 12px;
  cursor: pointer;
}

.mini-btn:hover:not(:disabled),
.secondary-btn:hover:not(:disabled) {
  background: var(--surface-mid);
}

.mini-btn.danger {
  color: oklch(50% 0.17 25);
}

.mini-btn.danger:hover:not(:disabled) {
  background: oklch(96% 0.025 25);
}

.password-reset-row {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: minmax(220px, 1fr) auto auto;
  gap: 8px;
  align-items: center;
  padding-top: 2px;
}

.password-reset-row input {
  height: 34px;
  min-width: 0;
  padding: 0 10px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--surface-mid);
  color: var(--text-primary);
  font: inherit;
  font-size: 13px;
  outline: none;
}

.password-reset-row input:focus {
  border-color: oklch(58% 0.11 240);
  box-shadow: 0 0 0 3px oklch(58% 0.11 240 / 0.12);
}

@media (max-width: 1180px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }

  .time-grid {
    grid-template-columns: 1fr;
  }

  .backup-columns {
    grid-template-columns: 1fr;
  }

  .user-row,
  .user-row-head {
    grid-template-columns: minmax(140px, 1fr) 90px 80px 48px;
  }

  .user-row > .user-actions,
  .user-row-head > span:last-child {
    grid-column: 1 / -1;
  }
}

@media (max-width: 720px) {
  .user-row,
  .user-row-head {
    grid-template-columns: 1fr 1fr;
  }

  .password-reset-row {
    grid-template-columns: 1fr;
  }
}
</style>
