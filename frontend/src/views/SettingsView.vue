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
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useSettingsStore, type ReminderLeadMinutes } from '@/stores/settingsStore'

const settings = useSettingsStore()

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
  font-weight: 650;
  color: var(--text-primary);
}

.settings-heading p {
  font-size: 14px;
  line-height: 1.5;
  color: var(--text-secondary);
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
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

.card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.card-head h2 {
  margin-top: 3px;
  font-size: 18px;
  font-weight: 650;
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

.segment-control {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  padding: 4px;
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  background: var(--surface);
}

.segment-control.narrow {
  width: fit-content;
}

.segment-btn {
  min-width: 68px;
  height: 30px;
  padding: 0 10px;
  border: none;
  border-radius: 8px;
  background: transparent;
  font: inherit;
  font-size: 12px;
  color: var(--text-secondary);
  cursor: pointer;
}

.segment-btn.active {
  background: oklch(95% 0.015 240);
  color: oklch(35% 0.1 240);
  font-weight: 600;
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

@media (max-width: 1180px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }

  .time-grid {
    grid-template-columns: 1fr;
  }
}
</style>
