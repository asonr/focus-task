<template>
  <div
    class="quadrant"
    :class="['q' + quadrant, { 'drag-over': isDragOver }, { 'q-dimmed': isDimmed }]"
    @dragover="onDragOver"
    @dragleave="onDragLeave"
    @drop="onDrop"
  >
    <div class="quadrant-header">
      <div class="quadrant-dot"></div>
      <span class="quadrant-title">{{ title }}</span>
      <span class="quadrant-count">{{ undoneCount }}</span>
      <button class="quadrant-add" @click="showInlineAdd" title="添加任务">+</button>
    </div>
    <div class="task-list">
      <TaskItem
        v-for="task in visibleTasks"
        :key="task.clientId"
        :task="task"
        :quadrant="quadrant"
        :selected="task.clientId === store.selectedTaskId"
        compact
        @select="store.selectTask(task.clientId)"
        @toggle="store.toggleDone(task.clientId)"
        @contextmenu="onItemContext($event, task.clientId)"
        @dragstart="onDragStart(task.clientId, $event)"
      />
      <div v-if="visibleTasks.length === 0" class="empty-state visible">
        <div class="empty-state-icon">
          <!-- Q1: target -->
          <svg v-if="quadrant === 1" width="22" height="22" viewBox="0 0 24 24" fill="none" :stroke="q1Color" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="4"/><line x1="12" y1="2" x2="12" y2="6"/><line x1="12" y1="18" x2="12" y2="22"/><line x1="2" y1="12" x2="6" y2="12"/><line x1="18" y1="12" x2="22" y2="12"/>
          </svg>
          <!-- Q2: chart -->
          <svg v-else-if="quadrant === 2" width="22" height="22" viewBox="0 0 24 24" fill="none" :stroke="q2Color" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <rect x="2" y="2" width="20" height="20" rx="3"/><line x1="2" y1="16" x2="22" y2="16"/><polyline points="10,16 10,10 14,10 14,6 18,6"/>
          </svg>
          <!-- Q3: inbox -->
          <svg v-else-if="quadrant === 3" width="22" height="22" viewBox="0 0 24 24" fill="none" :stroke="q3Color" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="22,12 16,12 14,15 10,15 8,12 2,12"/><path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A1 1 0 0 0 17.67 5H6.33a1 1 0 0 0-.88.55z"/>
          </svg>
          <!-- Q4: leaf -->
          <svg v-else width="22" height="22" viewBox="0 0 24 24" fill="none" :stroke="q4Color" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M11 18c4 0 7-3.5 7-7.5 0-2-1.5-3.5-3.5-3.5H13v-3c0-1.1-.9-2-2-2H8v4h2l-4 10a5 5 0 0 0 5 2z"/>
          </svg>
        </div>
        <p>{{ emptyText }}</p>
      </div>
    </div>
    <!-- Inline Add -->
    <div v-if="addVisible" class="inline-add visible">
      <div class="inline-add-dot"></div>
      <input
        ref="addInputEl"
        v-model="addTitle"
        class="inline-add-input"
        placeholder="添加任务，回车确认…"
        @input="onAddInput"
        @keydown.enter="confirmAdd"
        @keydown.escape="cancelAdd"
        @blur="cancelAdd"
      />
    </div>
    <!-- Footer bar: always visible, provides bottom cap like the header -->
    <div class="quadrant-footer"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, inject } from 'vue'
import { useTaskStore } from '@/stores/taskStore'
import { useTaskFilter } from '@/composables/useTaskFilter'
import TaskItem from './TaskItem.vue'

const props = defineProps<{ quadrant: number }>()
const store = useTaskStore()
const { filterForQuadrant } = useTaskFilter()
const showContextMenu: any = inject('showContextMenu', () => {})

const addVisible = ref(false)
const addTitle = ref('')
const addInputEl = ref<HTMLInputElement | null>(null)
const isDragOver = ref(false)

const titles: Record<number, string> = {
  1: '重要 · 紧急', 2: '重要 · 不紧急', 3: '紧急 · 不重要', 4: '不重要 · 不紧急',
}
const emptyTexts: Record<number, string> = {
  1: '立即处理的要事', 2: '规划未来的重要事项', 3: '可委托他人的事务', 4: '可考虑删除的事项',
}

// Quadrant stroke colors for empty-state SVG icons
const q1Color = 'oklch(62% 0.14 4)'
const q2Color = 'oklch(54% 0.13 138)'
const q3Color = 'oklch(56% 0.12 205)'
const q4Color = 'oklch(50% 0.01 240)'

const title = computed(() => titles[props.quadrant])
const emptyText = computed(() => emptyTexts[props.quadrant])

const visibleTasks = computed(() => filterForQuadrant(store.quadrantTasks(props.quadrant)))

const undoneCount = computed(() => visibleTasks.value.filter(t => !t.done).length)

const isDimmed = computed(() => {
  const fq = store.filterQuadrant
  return fq !== null && fq !== undefined && fq !== props.quadrant
})

// ─── Inline Add ───
let draftId: string | null = null

async function showInlineAdd() {
  addVisible.value = true
  // Create draft task
  const task = await store.addTask(props.quadrant, '')
  draftId = task.clientId
  store.selectTask(task.clientId)
  await nextTick()
  addInputEl.value?.focus()
}

function onAddInput() {
  if (!draftId) return
  const task = store.tasks.find(t => t.clientId === draftId)
  if (task) {
    task.title = addTitle.value
    // The detail panel will pick up the change reactively
  }
}

async function confirmAdd() {
  if (draftId) {
    const title = addTitle.value.trim()
    if (title) {
      await store.updateTask(draftId, { title })
    } else {
      await store.removeTask(draftId)
    }
  }
  addTitle.value = ''
  addVisible.value = false
  draftId = null
}

async function cancelAdd() {
  setTimeout(async () => {
    if (draftId) {
      const title = addTitle.value.trim()
      if (!title) {
        await store.removeTask(draftId)
      }
    }
    addTitle.value = ''
    addVisible.value = false
    draftId = null
  }, 150)
}

// ─── Drag & Drop ───
let dragId = ''

function onDragStart(clientId: string, e: DragEvent) {
  dragId = clientId
  if (e.dataTransfer) e.dataTransfer.effectAllowed = 'move'
}

function onDragOver(e: DragEvent) {
  e.preventDefault()
  if (e.dataTransfer) e.dataTransfer.dropEffect = 'move'
  isDragOver.value = true
}

function onDragLeave() {
  isDragOver.value = false
}

async function onDrop(e: DragEvent) {
  e.preventDefault()
  isDragOver.value = false
  if (dragId) {
    await store.updateTask(dragId, { quadrant: props.quadrant })
    dragId = ''
  }
}

// ─── Context Menu ───
function onItemContext(e: MouseEvent, clientId: string) {
  showContextMenu(e, clientId)
}
</script>

<style scoped>
.quadrant {
  border-radius: var(--radius-lg);
  border: 1px solid;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
  flex: 1;
  transition: box-shadow var(--transition), opacity var(--transition), filter var(--transition), transform var(--transition);
}
.quadrant:hover { box-shadow: 0 18px 36px oklch(0% 0 0 / 0.045); transform: translateY(-1px); }
.q-dimmed { opacity: 0.35; filter: grayscale(30%); }

.q1 { background: var(--q1-bg); border-color: var(--q1-border); }
.q2 { background: var(--q2-bg); border-color: var(--q2-border); }
.q3 { background: var(--q3-bg); border-color: var(--q3-border); }
.q4 { background: var(--q4-bg); border-color: var(--q4-border); }

.drag-over { outline: 2px solid var(--q1-header); outline-offset: -2px; }
.q2.drag-over { outline-color: var(--q2-header); }
.q3.drag-over { outline-color: var(--q3-header); }
.q4.drag-over { outline-color: var(--q4-header); }

.quadrant-header {
  display: flex; align-items: center;
  padding: 9px 11px 8px; gap: 7px;
  border-bottom: 0.5px solid;
  backdrop-filter: blur(12px);
}
.q1 .quadrant-header { border-color: var(--q1-border); }
.q2 .quadrant-header { border-color: var(--q2-border); }
.q3 .quadrant-header { border-color: var(--q3-border); }
.q4 .quadrant-header { border-color: var(--q4-border); }

.quadrant-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.q1 .quadrant-dot { background: var(--q1-header); }
.q2 .quadrant-dot { background: var(--q2-header); }
.q3 .quadrant-dot { background: var(--q3-header); }
.q4 .quadrant-dot { background: var(--q4-header); }

.quadrant-title { font-size: 14px; font-weight: 600; flex: 1; }
.q1 .quadrant-title { color: var(--q1-header); }
.q2 .quadrant-title { color: var(--q2-header); }
.q3 .quadrant-title { color: var(--q3-header); }
.q4 .quadrant-title { color: var(--q4-header); }

.quadrant-count {
  font-size: 12px; font-weight: 600; border-radius: 20px;
  padding: 1px 7px; opacity: 0.7;
}
.q1 .quadrant-count { background: var(--q1-count-bg); color: var(--q1-header); }
.q2 .quadrant-count { background: var(--q2-count-bg); color: var(--q2-header); }
.q3 .quadrant-count { background: var(--q3-count-bg); color: var(--q3-header); }
.q4 .quadrant-count { background: var(--q4-count-bg); color: var(--q4-header); }

.quadrant-add {
  width: 26px; height: 26px; border-radius: 50%;
  border: 1.5px solid; background: transparent;
  cursor: pointer; display: grid; place-items: center;
  font-size: 18px; font-weight: 300;
  transition: all var(--transition); line-height: 1;
}
.q1 .quadrant-add { border-color: var(--q1-border); color: var(--q1-header); }
.q2 .quadrant-add { border-color: var(--q2-border); color: var(--q2-header); }
.q3 .quadrant-add { border-color: var(--q3-border); color: var(--q3-header); }
.q4 .quadrant-add { border-color: var(--q4-border); color: var(--q4-header); }

.q1 .quadrant-add:hover { background: var(--q1-header); color: white; border-color: var(--q1-header); }
.q2 .quadrant-add:hover { background: var(--q2-header); color: white; border-color: var(--q2-header); }
.q3 .quadrant-add:hover { background: var(--q3-header); color: white; border-color: var(--q3-header); }
.q4 .quadrant-add:hover { background: var(--q4-header); color: white; border-color: var(--q4-header); }

/* ─── Task List ─── */
.task-list {
  flex: 1; overflow-y: auto;
  padding: 6px 7px 0;
  display: flex; flex-direction: column; gap: 3px;
  min-height: 0;
}

.quadrant-footer {
  height: 18px;
  flex-shrink: 0;
  border-top: 0.5px solid;
  opacity: 0.42;
  background: transparent;
  margin: 0 12px 12px;
  border-radius: 999px;
}
.q1 .quadrant-footer { border-color: var(--q1-border); }
.q2 .quadrant-footer { border-color: var(--q2-border); }
.q3 .quadrant-footer { border-color: var(--q3-border); }
.q4 .quadrant-footer { border-color: var(--q4-border); }
.task-list::-webkit-scrollbar { width: 4px; }
.task-list::-webkit-scrollbar-track { background: transparent; }
.task-list::-webkit-scrollbar-thumb { background: var(--border-subtle); border-radius: 2px; }

/* ─── Empty State ─── */
.empty-state {
  flex: 1; display: flex; align-items: center; justify-content: center;
  flex-direction: column; gap: 6px; padding: 18px;
  opacity: 0; transition: opacity 0.3s;
}
.empty-state.visible { opacity: 1; }
.empty-state-icon { font-size: 22px; margin-bottom: 2px; }
.empty-state p {
  font-size: 13px;
  color: var(--text-muted);
  text-align: center;
  line-height: 1.5;
  max-width: 18ch;
}

/* ─── Inline Add ─── */
.inline-add {
  display: none; padding: 6px 8px; gap: 8px; align-items: center;
}
.inline-add.visible { display: flex; }
.inline-add-dot {
  width: 15px; height: 15px; border-radius: 50%;
  border: 1.5px dashed; flex-shrink: 0;
}
.q1 .inline-add-dot { border-color: var(--q1-header); }
.q2 .inline-add-dot { border-color: var(--q2-header); }
.q3 .inline-add-dot { border-color: var(--q3-header); }
.q4 .inline-add-dot { border-color: var(--q4-header); }
.inline-add-input {
  flex: 1; background: none; border: none; outline: none;
  font: inherit; font-size: 14px; color: var(--text-primary);
}
.inline-add-input::placeholder { color: var(--text-muted); }
</style>
