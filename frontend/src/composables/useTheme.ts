import { ref, watch, onMounted } from 'vue'

export type ThemeMode = 'light' | 'dark' | 'system'

const STORAGE_KEY = 'focus-task-theme'

const mode = ref<ThemeMode>(localStorage.getItem(STORAGE_KEY) as ThemeMode || 'system')

const systemIsDark = ref(window.matchMedia('(prefers-color-scheme: dark)').matches)

// Watch system preference changes
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
  systemIsDark.value = e.matches
  applyTheme()
})

function applyTheme() {
  const html = document.documentElement
  const shouldBeDark = mode.value === 'dark' || (mode.value === 'system' && systemIsDark.value)
  html.classList.toggle('theme-dark', shouldBeDark)
  html.classList.toggle('theme-light', mode.value === 'light' && !shouldBeDark)
}

watch(mode, () => {
  localStorage.setItem(STORAGE_KEY, mode.value)
  applyTheme()
})

export function useTheme() {
  onMounted(() => applyTheme())

  return {
    mode,
    setMode: (m: ThemeMode) => { mode.value = m },
    isDark: () => mode.value === 'dark' || (mode.value === 'system' && systemIsDark.value),
  }
}
