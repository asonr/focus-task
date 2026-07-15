<template>
  <aside class="sidebar" role="navigation" aria-label="侧边栏导航">
    <div class="sidebar-section-label">视图</div>
    <div
      v-for="item in viewItems"
      :key="item.key"
      class="sidebar-item"
      role="button"
      tabindex="0"
      :aria-label="item.label"
      :class="{ active: !isSettingsRoute && store.currentView === item.key && !store.filterQuadrant }"
      @click="clickView(item.key)"
      @keydown.enter="clickView(item.key)"
    >
      <svg class="sidebar-icon" width="14" height="14" viewBox="0 0 16 16" fill="none" :stroke="item.color" stroke-width="1.5">
        <component :is="item.icon" />
      </svg>
      <span>{{ item.label }}</span>
      <span class="sidebar-badge">{{ item.badge || '' }}</span>
    </div>

    <div class="sidebar-section-label">象限</div>
    <div
      v-for="q in quadrants"
      :key="q.id"
      class="sidebar-item"
      role="button"
      tabindex="0"
      :aria-label="q.label"
      :class="{ active: !isSettingsRoute && store.filterQuadrant === q.id }"
      @click="clickQuadrant(q.id)"
      @keydown.enter="clickQuadrant(q.id)"
    >
      <div class="sidebar-dot" :style="{ background: q.color }"></div>
      <span>{{ q.label }}</span>
      <span class="sidebar-badge">{{ q.badge || '' }}</span>
    </div>

    <div class="sidebar-section-label">统计</div>
    <div
      class="sidebar-item"
      role="button"
      tabindex="0"
      aria-label="总结"
      :class="{ active: !isSettingsRoute && store.currentView === 'summary' }"
      @click="openSummary"
      @keydown.enter="openSummary"
    >
      <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="oklch(55% 0.12 240)" stroke-width="1.5" style="flex-shrink:0">
        <path d="M3 13V5M7 13V8M11 13V3" stroke-linecap="round"/>
        <circle cx="3" cy="4" r="1" fill="oklch(55% 0.12 240)" stroke="none"/>
        <circle cx="7" cy="7" r="1" fill="oklch(55% 0.12 240)" stroke="none"/>
        <circle cx="11" cy="2" r="1" fill="oklch(55% 0.12 240)" stroke="none"/>
      </svg>
      <span>总结</span>
    </div>
    <div
      class="sidebar-item"
      role="button"
      tabindex="0"
      aria-label="报告"
      :class="{ active: !isSettingsRoute && store.currentView === 'reports' }"
      @click="openReports"
      @keydown.enter="openReports"
    >
      <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="oklch(55% 0.12 240)" stroke-width="1.5" style="flex-shrink:0">
        <rect x="2" y="2" width="5" height="12" rx="1"/><rect x="9" y="6" width="5" height="8" rx="1"/>
      </svg>
      <span>报告</span>
    </div>

    <div class="sidebar-section-label">偏好</div>
    <div
      class="sidebar-item"
      role="button"
      tabindex="0"
      aria-label="设置"
      :class="{ active: route.path === '/settings' }"
      @click="router.push('/settings')"
      @keydown.enter="router.push('/settings')"
    >
      <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="oklch(56% 0.11 240)" stroke-width="1.5" style="flex-shrink:0">
        <circle cx="8" cy="8" r="2.5"/><path d="M8 1.5v2M8 12.5v2M14.5 8h-2M3.5 8h-2M12.95 3.05l-1.4 1.4M4.45 11.55l-1.4 1.4M12.95 12.95l-1.4-1.4M4.45 4.45l-1.4-1.4"/>
      </svg>
      <span>设置</span>
    </div>

    <div class="sidebar-account">
      <div class="account-main">
        <div class="account-avatar">{{ accountInitial }}</div>
        <div class="account-copy">
          <strong>{{ auth.username || '未登录' }}</strong>
          <span>{{ auth.isAdmin ? '管理员' : '普通用户' }}</span>
        </div>
      </div>
      <button class="logout-btn" type="button" @click="logout">
        退出登录
      </button>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed, h } from 'vue'
import { useTaskStore } from '@/stores/taskStore'
import { useAuthStore } from '@/stores/authStore'
import { toDateKey } from '@/utils/dateTime'
import { useRoute, useRouter } from 'vue-router'

const store = useTaskStore()
const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const isSettingsRoute = computed(() => route.path === '/settings')
const accountInitial = computed(() => (auth.username || '?').slice(0, 1).toUpperCase())

const today = new Date().toISOString().slice(0, 10)

// SVG icon components for sidebar items
const MatrixIcon = h('path', { d: 'M2 2h5v5H2zM9 2h5v5H9zM2 9h5v5H2zM9 9h5v5H9zM2 2h5v5H2zM9 2h5v5H9zM2 9h5v5H2zM9 9h5v5H9z', 'stroke-linecap': 'round', 'stroke-linejoin': 'round' })
const TodayIcon = h('path', { d: 'M2 2h12v12H2zM2 6h12M6 2v4M8 9l2 2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round' })
const DoneIcon = h('path', { d: 'M3 8.5L6.5 12L13 4.5M8 2a6 6 0 1 0 0 12a6 6 0 0 0 0-12z', 'stroke-linecap': 'round', 'stroke-linejoin': 'round' })

const viewItems = computed(() => [
  { key: 'matrix' as const, label: '四象限矩阵', color: 'oklch(55% 0.12 240)', icon: MatrixIcon, badge: store.activeTasks.length },
  { key: 'today' as const, label: '今日任务', color: 'oklch(62% 0.14 4)', icon: TodayIcon, badge: store.activeTasks.filter(t => toDateKey(t.due) === today && !t.done).length },
  { key: 'done' as const, label: '已完成', color: 'oklch(52% 0.15 145)', icon: DoneIcon, badge: store.doneTasks.length },
])

const quadrants = computed(() => [
  { id: 1, label: '重要且紧急', color: 'oklch(62% 0.14 4)', badge: store.quadrantTasks(1).filter(t => !t.done).length },
  { id: 2, label: '重要不紧急', color: 'oklch(54% 0.13 138)', badge: store.quadrantTasks(2).filter(t => !t.done).length },
  { id: 3, label: '紧急不重要', color: 'oklch(56% 0.12 205)', badge: store.quadrantTasks(3).filter(t => !t.done).length },
  { id: 4, label: '不重要不紧急', color: 'oklch(54% 0.01 0)', badge: store.quadrantTasks(4).filter(t => !t.done).length },
])

function clickView(key: 'matrix' | 'today' | 'done' | 'reports' | 'summary') {
  store.filterQuadrant = null
  store.setView(key)
  if (route.path === '/settings') {
    router.push('/')
  }
}

function clickQuadrant(q: number) {
  store.filterQuadrant = store.filterQuadrant === q ? null : q
  store.setView('matrix')
  if (route.path === '/settings') {
    router.push('/')
  }
}

function openReports() {
  store.filterQuadrant = null
  store.setView('reports')
  if (route.path === '/settings') {
    router.push('/')
  }
}

function openSummary() {
  store.filterQuadrant = null
  store.setView('summary')
  if (route.path === '/settings') {
    router.push('/')
  }
}

async function logout() {
  await auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.sidebar {
  background: var(--surface);
  border-right: 1px solid var(--border-subtle);
  padding: 16px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow-y: auto;
}
.sidebar-section-label {
  padding: 6px 8px 2px;
  font-size: 11px;
  font-weight: 500;
  color: var(--text-muted);
  margin-top: 8px;
}
.sidebar-section-label:first-child { margin-top: 0; }
.sidebar-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 14px;
  color: var(--text-secondary);
  font-weight: 500;
  transition: background var(--transition), color var(--transition);
  user-select: none;
}
.sidebar-item:hover { background: var(--surface-mid); color: var(--text-primary); }
.sidebar-item.active { background: oklch(95% 0.015 240); color: oklch(35% 0.1 240); font-weight: 500; }
.sidebar-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.sidebar-icon { flex-shrink: 0; }
.sidebar-badge {
  margin-left: auto;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-muted);
  background: var(--surface-mid);
  border-radius: 20px;
  padding: 0 6px;
  min-width: 18px;
  text-align: center;
  line-height: 18px;
}
.sidebar-item.active .sidebar-badge {
  background: oklch(88% 0.04 240);
  color: oklch(35% 0.1 240);
}

.sidebar-account {
  margin-top: auto;
  padding-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  border-top: 1px solid var(--border-subtle);
}

.account-main {
  display: flex;
  align-items: center;
  gap: 9px;
  min-width: 0;
}

.account-avatar {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  flex-shrink: 0;
  background: oklch(95% 0.018 240);
  color: oklch(38% 0.11 240);
  font-size: 13px;
  font-weight: 700;
}

.account-copy {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.account-copy strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-primary);
  font-size: 13px;
  line-height: 1.25;
}

.account-copy span {
  color: var(--text-muted);
  font-size: 11px;
  line-height: 1.25;
}

.logout-btn {
  height: 30px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  background: var(--surface);
  color: oklch(50% 0.15 25);
  font: inherit;
  font-size: 13px;
  cursor: pointer;
  transition: background var(--transition), border-color var(--transition);
}

.logout-btn:hover {
  background: oklch(96% 0.025 25);
  border-color: oklch(88% 0.04 25);
}
</style>
