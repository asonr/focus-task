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
import * as api from '@/api'
import type { UserAccount } from '@/api'
import { useAuthStore } from '@/stores/authStore'
import { useSettingsStore, type ReminderLeadMinutes } from '@/stores/settingsStore'
import { useTheme, type ThemeMode } from '@/composables/useTheme'

const settings = useSettingsStore()
const theme = useTheme()
const auth = useAuthStore()

const users = ref<UserAccount[]>([])
const usersLoading = ref(false)
const usersError = ref('')
const usersMessage = ref('')
const actionBusy = ref(false)
const resetUserId = ref<number | null>(null)
const resetPassword = ref('')

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
