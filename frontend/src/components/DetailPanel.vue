<template>
  <div class="detail-panel">
    <div class="detail-header">
      <div class="detail-heading">
        <span class="detail-title">任务详情</span>
        <div v-if="task" class="detail-status-row">
          <span class="detail-chip">Q{{ task.quadrant }}</span>
          <span v-if="task.syncStatus === 'pending'" class="detail-chip detail-chip-pending">待同步</span>
          <span v-else-if="task.syncStatus === 'conflict'" class="detail-chip detail-chip-conflict">有冲突</span>
          <span v-else class="detail-chip detail-chip-synced">已同步</span>
        </div>
      </div>
      <button class="close-btn" @click="store.selectTask(null)">
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" width="14" height="14">
          <path d="M4 4L12 12M12 4L4 12"/>
        </svg>
      </button>
    </div>
    <div v-if="task" class="detail-body">
      <div class="detail-meta-card">
        <div class="detail-meta-item">
          <span class="detail-meta-label">创建于</span>
          <span class="detail-meta-value">{{ formatCreatedAt }}</span>
        </div>
        <div class="detail-meta-item">
          <span class="detail-meta-label">最近变更</span>
          <span class="detail-meta-value">{{ formatUpdatedAt }}</span>
        </div>
      </div>
      <div v-if="serverConflict" class="conflict-box">
        <div class="conflict-copy">
          <strong>检测到同步冲突</strong>
          <span>服务端版本更新于 {{ formatConflictUpdatedAt }}，标题为“{{ serverConflict.title || '未命名任务' }}”。</span>
        </div>
        <div class="conflict-actions">
          <button type="button" @click="resolveConflict('local')">保留本地</button>
          <button type="button" class="primary" @click="resolveConflict('server')">使用服务端</button>
        </div>
      </div>
      <div class="detail-field">
        <label>标题</label>
        <input type="text" :value="task.title" @input="updateField('title', ($event.target as HTMLInputElement).value)" placeholder="任务标题" />
      </div>
      <div class="detail-field">
        <label>备注</label>
        <textarea :value="task.notes" @input="updateField('notes', ($event.target as HTMLTextAreaElement).value)" placeholder="添加备注…"></textarea>
      </div>
      <div class="detail-field">
        <label>象限</label>
        <select :value="task.quadrant" @change="updateField('quadrant', +($event.target as HTMLSelectElement).value)">
          <option value="1">重要 · 紧急（立即做）</option>
          <option value="2">重要 · 不紧急（计划）</option>
          <option value="3">紧急 · 不重要（委托）</option>
          <option value="4">不重要 · 不紧急（删除）</option>
        </select>
      </div>
      <div class="detail-field">
        <label>标签</label>
        <input type="text" :value="task.tag" @input="updateField('tag', ($event.target as HTMLInputElement).value)" placeholder="标签" />
      </div>
      <div class="detail-field">
        <label>开始日期</label>
        <input type="datetime-local" :value="task.startAt" @change="updateField('startAt', ($event.target as HTMLInputElement).value)" />
      </div>
      <div class="detail-field">
        <label>截止日期</label>
        <input type="datetime-local" :value="task.due" @change="updateField('due', ($event.target as HTMLInputElement).value)" />
      </div>
      <div class="detail-field">
        <label>提醒</label>
        <div class="detail-notification-grid">
          <label class="detail-check">
            <input type="checkbox" :checked="task.notifyOnStart" @change="updateField('notifyOnStart', ($event.target as HTMLInputElement).checked)" />
            <span>开始时</span>
          </label>
          <label class="detail-check">
            <input type="checkbox" :checked="task.notifyOnDue" @change="updateField('notifyOnDue', ($event.target as HTMLInputElement).checked)" />
            <span>截止时</span>
          </label>
          <label class="detail-check">
            <input type="checkbox" :checked="task.notifyOnOverdue" @change="updateField('notifyOnOverdue', ($event.target as HTMLInputElement).checked)" />
            <span>过期后</span>
          </label>
        </div>
      </div>
      <div class="detail-field">
        <label>重复</label>
        <select :value="task.repeat" @change="updateField('repeat', ($event.target as HTMLSelectElement).value)">
          <option value="none">不重复</option>
          <option value="daily">每天</option>
          <option value="weekly">每周</option>
          <option value="monthly">每月</option>
        </select>
      </div>
    </div>
    <div v-else class="detail-body">
      <p class="detail-empty">从象限中选一个任务，这里会展开它的内容、状态和节奏。</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useTaskStore } from '@/stores/taskStore'
import { formatDateTimeLocal } from '@/utils/dateTime'

const store = useTaskStore()
const task = computed(() => store.selectedTask)
const serverConflict = computed(() => task.value?.conflictServer || null)

const formatCreatedAt = computed(() => {
  if (!task.value?.createdAt) return '—'
  return formatDateTimeLocal(task.value.createdAt)
})

const formatUpdatedAt = computed(() => {
  if (!task.value?.updatedAt) return '—'
  return formatDateTimeLocal(task.value.updatedAt)
})

const formatConflictUpdatedAt = computed(() => {
  if (!serverConflict.value?.updatedAt) return '—'
  return formatDateTimeLocal(serverConflict.value.updatedAt)
})

function updateField(field: string, value: any) {
  if (!task.value) return
  store.updateTask(task.value.clientId, { [field]: value })
}

function resolveConflict(strategy: 'local' | 'server') {
  if (!task.value) return
  store.resolveConflict(task.value.clientId, strategy)
}
</script>

<style scoped>
.detail-panel {
  width: 260px;
  min-width: 0;
  background: var(--surface);
  border-left: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: opacity 180ms cubic-bezier(0.2, 0, 0, 1);
}
.detail-header {
  padding: 12px 14px 10px;
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}
.detail-heading {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.detail-title {
  font-size: 13px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
}
.detail-status-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.detail-chip {
  border-radius: 999px;
  padding: 2px 7px;
  background: var(--surface-mid);
  font-size: 10px;
  font-weight: 700;
  color: var(--text-secondary);
}
.detail-chip-pending {
  background: oklch(96% 0.018 240);
  color: oklch(47% 0.11 240);
}
.detail-chip-conflict {
  background: oklch(96% 0.03 25);
  color: oklch(52% 0.16 25);
}
.detail-chip-synced {
  background: oklch(96% 0.018 145);
  color: oklch(45% 0.1 145);
}
.close-btn {
  width: 28px; height: 28px; border-radius: var(--radius-sm);
  border: none; background: transparent; cursor: pointer;
  display: grid; place-items: center; color: var(--text-secondary);
  transition: background var(--transition), color var(--transition);
}
.close-btn:hover { background: var(--surface-mid); color: var(--text-primary); }

.detail-body {
  flex: 1;
  overflow-y: auto;
  padding: 12px 14px 92px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  scroll-padding-bottom: 92px;
}
.detail-meta-card {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 10px;
  border: 1px solid var(--border-subtle);
  background: linear-gradient(180deg, oklch(99% 0.003 240), var(--surface));
  border-radius: var(--radius-md);
  padding: 8px 10px;
}
.detail-meta-item {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}
.detail-meta-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-muted);
}
.detail-meta-value {
  font-size: 11px;
  color: var(--text-primary);
  line-height: 1.25;
  white-space: nowrap;
}
.detail-empty {
  font-size: 14px;
  color: var(--text-muted);
  text-align: left;
  line-height: 1.6;
  padding: 8px 4px;
}
.conflict-box {
  display: flex;
  flex-direction: column;
  gap: 8px;
  border: 1px solid oklch(74% 0.12 42);
  background: oklch(98% 0.025 72);
  border-radius: var(--radius-md);
  padding: 9px 10px;
}
.conflict-copy {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}
.conflict-copy strong {
  font-size: 12px;
  color: oklch(43% 0.12 42);
}
.conflict-copy span {
  font-size: 12px;
  line-height: 1.45;
  color: oklch(38% 0.04 72);
}
.conflict-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px;
}
.conflict-actions button {
  border: 1px solid oklch(82% 0.04 72);
  background: var(--surface);
  border-radius: var(--radius-sm);
  padding: 6px 8px;
  font-size: 12px;
  font-weight: 700;
  color: var(--text-secondary);
  cursor: pointer;
}
.conflict-actions button.primary {
  border-color: oklch(58% 0.12 240);
  background: oklch(96% 0.018 240);
  color: oklch(43% 0.13 240);
}
.detail-field label {
  display: block;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  margin-bottom: 3px;
}
.detail-field input,
.detail-field textarea,
.detail-field select {
  width: 100%;
  background: var(--surface-mid);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 6px 8px;
  font: inherit;
  font-size: 13px;
  color: var(--text-primary);
  outline: none;
  transition: border-color var(--transition), box-shadow var(--transition);
  resize: vertical;
}
.detail-field input:focus,
.detail-field textarea:focus,
.detail-field select:focus {
  border-color: oklch(60% 0.12 240);
  box-shadow: 0 0 0 3px oklch(60% 0.12 240 / 0.12);
}
.detail-field textarea { min-height: 54px; }
.detail-notification-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 6px;
  padding: 6px 8px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  background: var(--surface-mid);
}
.detail-check {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 11px;
  white-space: nowrap;
  color: var(--text-secondary);
}
.detail-check input {
  width: 13px;
  height: 13px;
  accent-color: oklch(60% 0.12 240);
}
</style>
