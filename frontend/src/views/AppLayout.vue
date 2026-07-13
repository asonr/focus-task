<template>
  <div class="app">
    <!-- Header: data-tauri-drag-region + JS startDragging for macOS -->
    <header class="header" id="app-header" data-tauri-drag-region>
      <!-- Traffic light spacer: leaves room for macOS close/minimize/zoom buttons -->
      <div class="traffic-light-spacer" data-tauri-drag-region></div>
      <div class="header-logo" data-tauri-drag-region>
        <svg viewBox="0 0 24 24" width="22" height="22" fill="none">
          <rect x="2" y="2" width="9" height="9" rx="2.5" fill="oklch(55% 0.18 25)"/>
          <rect x="13" y="2" width="9" height="9" rx="2.5" fill="oklch(62% 0.13 145)"/>
          <rect x="2" y="13" width="9" height="9" rx="2.5" fill="oklch(62% 0.14 250)"/>
          <rect x="13" y="13" width="9" height="9" rx="2.5" fill="oklch(68% 0.04 0)"/>
        </svg>
      </div>
      <div class="header-divider" data-tauri-drag-region></div>
      <div class="header-brand" data-tauri-drag-region>
        <span class="header-title">Focus Task</span>
        <span class="header-subtitle">聚焦任务桌面台</span>
      </div>
      <div class="header-spacer" data-tauri-drag-region></div>
      <div v-if="showTaskChrome" class="header-actions">
        <div class="search-bar">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" width="14" height="14">
            <circle cx="6.5" cy="6.5" r="4.5"/><path d="M10 10L14 14"/>
          </svg>
          <input type="text" v-model="store.searchQuery" placeholder="搜索任务…" />
        </div>
        <button class="btn-icon" @click="panelOpen = !panelOpen" title="详情面板">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" width="18" height="18">
            <rect x="2" y="2" width="12" height="12" rx="2"/><line x1="10" y1="2" x2="10" y2="14"/>
          </svg>
        </button>
        <button class="btn-icon btn-danger" @click="clearDone" title="清除已完成">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" width="20" height="20">
            <path d="M3 4h10M6 4V2.5a.5.5 0 0 1 .5-.5h3a.5.5 0 0 1 .5.5V4M5 4l.5 8.5h5L11 4"/>
          </svg>
        </button>
      </div>
    </header>

    <!-- Sidebar -->
    <Sidebar />

    <!-- Main Content -->
    <div class="main" :class="{ 'panel-hidden': !panelOpen, 'reports-active': isFullView }">
      <SettingsView v-if="isSettingsRoute" />

      <!-- Matrix View -->
      <div v-else-if="!isFullView" class="matrix-area">
        <!-- Stats Bar -->
        <div class="stats-bar">
          <div class="stats-kicker">
            <span class="stats-kicker-label">今日焦点</span>
            <strong>{{ focusSummary }}</strong>
          </div>
          <div class="stat-item">
            <div class="stat-dot" style="background:oklch(55% 0.12 240)"></div>
            <span>共 <strong>{{ allVisible.length }}</strong> 项</span>
          </div>
          <div class="stat-item">
            <div class="stat-dot" style="background:oklch(54% 0.13 138)"></div>
            <span>已完成 <strong>{{ doneVisible.length }}</strong> 项</span>
          </div>
          <div class="progress-bar-wrap">
            <div class="progress-bar-fill" :style="{ width: progressPct + '%' }"></div>
          </div>
          <div class="stat-item">
            <strong>{{ progressPct }}%</strong>
          </div>
        </div>

        <!-- Matrix: flexbox-based for reliable equal-height rows -->
        <div class="axis-container">
          <!-- Top axis label -->
          <div class="axis-row-top">
            <div class="axis-vlabel"><span>重要 →</span></div>
            <div class="axis-sublabel-row">
              <span>紧急 ↑</span>
              <span>↓ 不紧急</span>
            </div>
          </div>
          <!-- Top row: Q1 + Q2 -->
          <div class="matrix-row">
            <div class="axis-vlabel-spacer"></div>
            <QuadrantCard :quadrant="1" />
            <QuadrantCard :quadrant="2" />
          </div>
          <!-- Bottom row: Q3 + Q4 -->
          <div class="matrix-row">
            <div class="axis-vlabel-spacer"><span>← 不重要</span></div>
            <QuadrantCard :quadrant="3" />
            <QuadrantCard :quadrant="4" />
          </div>
        </div>
      </div>

      <!-- Reports View -->
      <ReportsView v-else-if="isReportsView" />

      <!-- Summary View -->
      <SummaryView v-else-if="isSummaryView" />

      <!-- Detail Panel -->
      <Transition name="panel">
        <DetailPanel v-if="panelOpen && !isFullView && !isSettingsRoute" />
      </Transition>
    </div>

    <!-- Context Menu -->
    <div v-if="contextMenu.visible" class="context-menu" :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }">
      <div class="context-item" @click="ctxAction('edit')">
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" width="14" height="14"><path d="M11 2L14 5L6 13H3V10L11 2Z"/></svg>
        编辑标题
      </div>
      <div class="context-item" @click="ctxAction('move', 1)">
        <svg viewBox="0 0 16 16" fill="none" stroke-width="1.5" width="14" height="14"><circle cx="8" cy="8" r="3" fill="oklch(62% 0.14 4)" stroke="none"/></svg>
        移至：重要且紧急
      </div>
      <div class="context-item" @click="ctxAction('move', 2)">
        <svg viewBox="0 0 16 16" fill="none" stroke-width="1.5" width="14" height="14"><circle cx="8" cy="8" r="3" fill="oklch(54% 0.13 138)" stroke="none"/></svg>
        移至：重要不紧急
      </div>
      <div class="context-item" @click="ctxAction('move', 3)">
        <svg viewBox="0 0 16 16" fill="none" stroke-width="1.5" width="14" height="14"><circle cx="8" cy="8" r="3" fill="oklch(56% 0.12 205)" stroke="none"/></svg>
        移至：紧急不重要
      </div>
      <div class="context-item" @click="ctxAction('move', 4)">
        <svg viewBox="0 0 16 16" fill="none" stroke-width="1.5" width="14" height="14"><circle cx="8" cy="8" r="3" fill="oklch(54% 0.01 0)" stroke="none"/></svg>
        移至：不重要不紧急
      </div>
      <div class="context-sep"></div>
      <div class="context-item danger" @click="ctxAction('delete')">
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" width="14" height="14"><path d="M3 4h10M6 4V2.5a.5.5 0 0 1 .5-.5h3a.5.5 0 0 1 .5.5V4M5 4l.5 8.5h5L11 4"/></svg>
        删除任务
      </div>
    </div>

    <!-- Sync status -->
    <div class="sync-status" :class="{ offline: !syncStore.online, syncing: syncStore.syncing, conflict: conflictCount > 0 }">
      <span v-if="conflictCount > 0" class="sync-dot conflict"></span>
      <span v-else-if="!syncStore.online" class="sync-dot offline"></span>
      <span v-else-if="syncStore.syncing" class="sync-dot syncing"></span>
      <span v-else class="sync-dot online"></span>
      <span class="sync-text">
        {{ conflictCount > 0 ? `${conflictCount} 个冲突` : !syncStore.online ? '离线' : syncStore.syncing ? '同步中…' : '已同步' }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, onMounted, onUnmounted, provide } from 'vue'
import { useRoute } from 'vue-router'
import { useTaskStore } from '@/stores/taskStore'
import { useSyncStore } from '@/stores/syncStore'
import Sidebar from '@/components/Sidebar.vue'
import QuadrantCard from '@/components/QuadrantCard.vue'
import DetailPanel from '@/components/DetailPanel.vue'
import ReportsView from '@/views/ReportsView.vue'
import SummaryView from '@/views/SummaryView.vue'
import SettingsView from '@/views/SettingsView.vue'

const store = useTaskStore()
const syncStore = useSyncStore()
const route = useRoute()
const panelOpen = ref(true)
const isSettingsRoute = computed(() => route.path === '/settings')
const isReportsView = computed(() => !isSettingsRoute.value && store.currentView === 'reports')
const isSummaryView = computed(() => !isSettingsRoute.value && store.currentView === 'summary')
const isFullView = computed(() => isReportsView.value || isSummaryView.value)
const showTaskChrome = computed(() => !isSettingsRoute.value)

// ─── Window Dragging ───
// Tauri v2 official approach: listen to mousedown on the header element by ID,
// call startDragging() directly (no await, no .catch(), must be synchronous).
// See: https://v2.tauri.app/learn/window-customization/
let appWindow: any = null

async function initDrag() {
  try {
    const { getCurrentWindow } = await import('@tauri-apps/api/window')
    appWindow = getCurrentWindow()
  } catch {
    return // browser dev mode, no dragging needed
  }

  const header = document.getElementById('app-header')
  if (!header) return

  header.addEventListener('mousedown', (e: MouseEvent) => {
    // Only left mouse button (e.buttons: 1 = primary button held down)
    if (e.buttons !== 1) return
    // Skip if clicking interactive elements (search bar, buttons)
    const t = e.target as HTMLElement
    if (t.closest('.header-actions') || t.tagName === 'INPUT' || t.tagName === 'BUTTON') return
    // Double-click → maximize/restore
    if (e.detail === 2) {
      appWindow.toggleMaximize()
      return
    }
    // Single click → drag (must be called synchronously inside mousedown)
    appWindow.startDragging()
  })
}

// ─── Stats ───
const allVisible = computed(() => {
  const q = store.searchQuery.toLowerCase()
  return store.activeTasks.filter(t => !q || t.title.toLowerCase().includes(q))
})
const doneVisible = computed(() => allVisible.value.filter(t => t.done))
const conflictCount = computed(() => store.conflictTasks.length)
const progressPct = computed(() => {
  const total = allVisible.value.length
  return total ? Math.round(doneVisible.value.length / total * 100) : 0
})
const focusSummary = computed(() => {
  const urgentImportant = store.quadrantTasks(1).filter(t => !t.done).length
  if (urgentImportant > 0) return `${urgentImportant} 项需要优先处理`
  const importantPlanned = store.quadrantTasks(2).filter(t => !t.done).length
  if (importantPlanned > 0) return `${importantPlanned} 项值得安排到计划里`
  return '当前节奏很干净'
})

// ─── Context Menu ───
const contextMenu = reactive({ visible: false, x: 0, y: 0, clientId: '' })

function showContextMenu(e: MouseEvent, clientId: string) {
  e.preventDefault()
  contextMenu.visible = true
  contextMenu.x = e.clientX
  contextMenu.y = e.clientY
  contextMenu.clientId = clientId
}

function hideContextMenu() {
  contextMenu.visible = false
}

function ctxAction(action: string, quadrant?: number) {
  const cid = contextMenu.clientId
  if (action === 'edit') {
    store.selectTask(cid)
  } else if (action === 'move' && quadrant) {
    store.updateTask(cid, { quadrant })
  } else if (action === 'delete') {
    store.removeTask(cid)
  }
  hideContextMenu()
}

function clearDone() {
  const done = store.activeTasks.filter(t => t.done)
  done.forEach(t => store.removeTask(t.clientId))
}

// Expose showContextMenu for child components
provide('showContextMenu', showContextMenu)

onMounted(async () => {
  document.addEventListener('click', hideContextMenu)
  // Init window dragging
  await initDrag()
  // Try fetching from server
  store.fetchTasks().then(() => {
    syncStore.startAutoSync()
  }).catch(() => {
    // Offline — use local cache, that's fine
  })
})

onUnmounted(() => {
  document.removeEventListener('click', hideContextMenu)
  syncStore.stopAutoSync()
})
</script>

<style scoped>
.app {
  display: grid;
  grid-template-columns: var(--sidebar-width) 1fr;
  grid-template-rows: var(--header-height) minmax(0, 1fr);
  height: 100vh;
  overflow: hidden;
}
.header {
  grid-column: 1 / -1;
  background: linear-gradient(180deg, oklch(99% 0.003 240), var(--surface));
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  padding: 0 14px;
  gap: 10px;
  z-index: 20;
  /* Make header a drag target via cursor, actual drag via JS startDragging() */
  cursor: default;
  -webkit-user-select: none;
  user-select: none;
}
/* Traffic light spacer: room for macOS close/minimize/zoom buttons */
.traffic-light-spacer {
  width: 48px;
  flex-shrink: 0;
  height: 100%;
}
.header-logo { display: flex; align-items: center; justify-content: center; padding: 0 2px; }
.header-logo svg { display: block; width: 22px; height: 22px; }
.header-divider { width: 1px; height: 20px; background: var(--border-subtle); margin: 0 1px; }
.header-title {
  font-family: 'DM Serif Display', serif;
  font-size: 20px;
  color: var(--text-primary);
  letter-spacing: -0.28px;
  line-height: 1.05;
}
.header-brand {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.header-subtitle { font-size: 12px; color: var(--text-muted); line-height: 1.1; }
.header-spacer { flex: 1; min-width: 0; }
/* All interactive elements: normal cursor, no drag */
.header-actions {
  display: flex;
  align-items: center;
  gap: 3px;
  cursor: default;
  -webkit-user-select: auto;
  user-select: auto;
}
.btn-icon {
  width: 30px; height: 30px; border-radius: var(--radius-sm);
  border: none; background: transparent; cursor: pointer;
  display: grid; place-items: center; color: var(--text-secondary);
  transition: background var(--transition), color var(--transition);
}
.btn-icon:hover { background: var(--surface-mid); color: var(--text-primary); }
.btn-icon.btn-danger { color: oklch(58% 0.16 20); }
.btn-icon.btn-danger:hover { background: oklch(96% 0.02 20); color: oklch(48% 0.18 20); }
.search-bar {
  display: flex; align-items: center; gap: 6px;
  background: var(--surface-mid); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm); padding: 5px 12px; width: 268px;
  transition: border-color var(--transition), box-shadow var(--transition);
}
.search-bar:focus-within {
  border-color: oklch(60% 0.12 240);
  box-shadow: 0 0 0 3px oklch(60% 0.12 240 / 0.12);
}
.search-bar input {
  background: none; border: none; outline: none;
  font: inherit; font-size: 14px; color: var(--text-primary); width: 100%;
}
.search-bar input::placeholder { color: var(--text-muted); }

/* ─── Main Content ─── */
.main {
  display: grid;
  grid-template-columns: 1fr 260px;
  grid-template-rows: minmax(0, 1fr);
  overflow: hidden;
  min-height: 0;
  transition: grid-template-columns 220ms cubic-bezier(0.2, 0, 0, 1);
}
.main.panel-hidden { grid-template-columns: 1fr 0; }
.main.reports-active { grid-template-columns: 1fr 0; }

.matrix-area {
  padding: 6px 16px 28px;
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  overflow: visible;
}

/* ─── Stats Bar ─── */
.stats-bar {
  display: flex; align-items: center; gap: 14px;
  padding: 0 0 8px; flex-shrink: 0;
  border-bottom: 1px solid oklch(88% 0.01 240 / 0.55);
  margin-bottom: 6px;
}
.stats-kicker {
  display: flex;
  align-items: baseline;
  gap: 8px;
  min-width: 220px;
}
.stats-kicker-label {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
}
.stats-kicker strong {
  font-size: 13px;
  color: var(--text-primary);
}
.stat-item { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--text-muted); }
.stat-dot { width: 7px; height: 7px; border-radius: 50%; }
.stat-item strong { color: var(--text-secondary); font-weight: 600; }
.progress-bar-wrap { flex: 1; height: 5px; background: var(--border-subtle); border-radius: 999px; overflow: hidden; }
.progress-bar-fill { height: 100%; background: oklch(60% 0.12 240); border-radius: 2px; transition: width 0.4s cubic-bezier(0.2, 0, 0, 1); }

/* ─── Axis Container: flexbox-based for reliable equal-height rows ─── */
.axis-container {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 7px;
  padding-bottom: 28px;
}

.axis-row-top {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  flex-shrink: 0;
  padding-left: 22px;
  height: 18px;
}
.axis-sublabel-row {
  flex: 1;
  display: flex;
  justify-content: space-between;
  padding: 0 2px;
}
.axis-sublabel-row span { font-size: 11px; font-weight: 500; color: var(--text-muted); }
.axis-vlabel span { font-size: 11px; font-weight: 500; color: var(--text-muted); }

.matrix-row {
  display: flex;
  gap: 10px;
  flex: 1;
  min-height: 0;
}

.axis-vlabel-spacer {
  width: 22px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.axis-vlabel-spacer span {
  font-size: 11px; font-weight: 500; color: var(--text-muted);
  writing-mode: vertical-lr; transform: rotate(180deg);
}

/* ─── Context Menu ─── */
.context-menu {
  position: fixed; background: var(--surface); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md); box-shadow: var(--shadow-panel);
  padding: 4px; z-index: 1000; min-width: 160px;
}
.context-item {
  display: flex; align-items: center; gap: 8px;
  padding: 7px 10px; border-radius: var(--radius-sm);
  cursor: pointer; font-size: 14px; color: var(--text-primary);
  transition: background var(--transition);
}
.context-item:hover { background: var(--surface-mid); }
.context-item.danger { color: oklch(50% 0.18 20); }
.context-item.danger:hover { background: oklch(96% 0.02 20); }
.context-sep { height: 1px; background: var(--border-subtle); margin: 3px 0; }

/* ─── Sync Status ─── */
.sync-status {
  position: fixed; bottom: 12px; right: 12px;
  display: flex; align-items: center; gap: 6px;
  padding: 6px 11px; border-radius: 999px;
  background: oklch(99% 0.003 240 / 0.94); border: 1px solid var(--border-subtle);
  font-size: 12px; color: var(--text-muted); z-index: 100;
  box-shadow: 0 8px 24px oklch(0% 0 0 / 0.05);
}
.sync-status.offline { border-color: oklch(65% 0.15 45); color: oklch(55% 0.12 45); }
.sync-status.conflict { border-color: oklch(65% 0.15 35); color: oklch(50% 0.14 35); }
.sync-dot { width: 6px; height: 6px; border-radius: 50%; }
.sync-dot.online { background: oklch(60% 0.15 145); }
.sync-dot.offline { background: oklch(65% 0.15 45); }
.sync-dot.conflict { background: oklch(60% 0.16 35); }
.sync-dot.syncing { background: oklch(62% 0.12 240); animation: pulse 1s ease-in-out infinite; }
@keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:0.5; } }

/* Panel transition */
.panel-enter-active { transition: opacity 160ms cubic-bezier(0.2, 0, 0, 1); }
.panel-leave-active { transition: opacity 160ms cubic-bezier(0.2, 0, 0, 1); }
.panel-enter-from, .panel-leave-to { opacity: 0; }
</style>
