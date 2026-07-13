<template>
  <div class="list-view">
    <div class="list-header">
      <div class="list-header-left">
        <span class="list-eyebrow">记录</span>
        <div class="list-title-row">
          <svg class="list-icon" width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="oklch(52% 0.15 145)" stroke-width="1.5">
            <path d="M3 8.5L6.5 12L13 4.5" stroke-linecap="round" stroke-linejoin="round"/>
            <circle cx="8" cy="8" r="6.5"/>
          </svg>
          <h2>已完成</h2>
        </div>
      </div>
      <span class="count-badge">{{ store.doneTasks.length }} 项</span>
    </div>
    <div class="list-body">
      <TaskItem
        v-for="task in store.doneTasks"
        :key="task.clientId"
        :task="task"
        :quadrant="task.quadrant"
        compact
        :selected="task.clientId === store.selectedTaskId"
        @select="store.selectTask(task.clientId)"
        @toggle="store.toggleDone(task.clientId)"
      />
      <div v-if="store.doneTasks.length === 0" class="empty">
        <svg width="40" height="40" viewBox="0 0 48 48" fill="none" stroke="oklch(75% 0.02 240)" stroke-width="1.5">
          <rect x="8" y="6" width="32" height="36" rx="4"/>
          <line x1="14" y1="14" x2="34" y2="14"/>
          <line x1="14" y1="22" x2="28" y2="22"/>
          <line x1="14" y1="30" x2="22" y2="30"/>
        </svg>
        <p>还没有已完成的任务，开始行动吧</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useTaskStore } from '@/stores/taskStore'
import TaskItem from '@/components/TaskItem.vue'
const store = useTaskStore()
</script>

<style scoped>
.list-view { flex: 1; display: flex; flex-direction: column; overflow: hidden; }

.list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-subtle);
}

.list-header-left {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.list-eyebrow {
  font-size: 11px;
  font-weight: 500;
  color: var(--text-muted);
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.list-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.list-icon { flex-shrink: 0; }

.list-title-row h2 { font-size: 17px; font-weight: 600; }

.count-badge {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-muted);
  padding: 3px 10px;
  border-radius: 999px;
  background: oklch(96% 0.01 240);
}

.list-body { flex: 1; overflow-y: auto; padding: 12px 20px; }

.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 48px 0;
  color: var(--text-muted);
}

.empty p { font-size: 14px; }
</style>
