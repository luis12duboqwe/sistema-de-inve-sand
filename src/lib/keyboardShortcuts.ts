export interface KeyboardShortcut {
  id: string
  key: string
  ctrlKey?: boolean
  shiftKey?: boolean
  altKey?: boolean
  metaKey?: boolean
  description: string
  category: string
  action: () => void
}

export interface ShortcutBinding {
  id: string
  key: string
  ctrlKey?: boolean
  shiftKey?: boolean
  altKey?: boolean
  metaKey?: boolean
}

export type ShortcutPreferences = Record<string, ShortcutBinding>

export const DEFAULT_SHORTCUTS: Omit<KeyboardShortcut, 'action'>[] = [
  {
    id: 'show-help',
    key: '?',
    shiftKey: true,
    description: 'Mostrar atajos de teclado',
    category: 'general'
  },
  {
    id: 'focus-search',
    key: 'k',
    ctrlKey: true,
    description: 'Enfocar búsqueda',
    category: 'general'
  },
  {
    id: 'open-settings',
    key: ',',
    ctrlKey: true,
    description: 'Abrir configuración',
    category: 'general'
  },
  {
    id: 'nav-products',
    key: '1',
    description: 'Ir a Productos',
    category: 'navigation'
  },
  {
    id: 'nav-orders',
    key: '2',
    description: 'Ir a Órdenes',
    category: 'navigation'
  },
  {
    id: 'nav-profiles',
    key: '3',
    description: 'Ir a Perfiles',
    category: 'navigation'
  },
  {
    id: 'create-new',
    key: 'n',
    ctrlKey: true,
    description: 'Crear nuevo elemento',
    category: 'actions'
  },
  {
    id: 'export-csv',
    key: 'e',
    ctrlKey: true,
    description: 'Exportar a CSV',
    category: 'actions'
  },
  {
    id: 'import-csv',
    key: 'i',
    ctrlKey: true,
    description: 'Importar desde CSV',
    category: 'actions'
  },
  {
    id: 'bulk-mode',
    key: 'b',
    ctrlKey: true,
    description: 'Modo selección múltiple',
    category: 'actions'
  },
  {
    id: 'clear-search',
    key: 'Escape',
    description: 'Limpiar búsqueda',
    category: 'search'
  },
  {
    id: 'select-all',
    key: 'a',
    ctrlKey: true,
    description: 'Seleccionar todos',
    category: 'search'
  }
]

export const CATEGORY_LABELS: Record<string, string> = {
  general: 'General',
  navigation: 'Navegación',
  actions: 'Acciones',
  search: 'Búsqueda y Filtros'
}

export const CATEGORY_ICONS: Record<string, string> = {
  general: 'keyboard',
  navigation: 'package',
  actions: 'shopping-cart',
  search: 'magnifying-glass'
}

export function formatShortcutKeys(binding: ShortcutBinding): string[] {
  const keys: string[] = []
  
  if (binding.ctrlKey) keys.push('Ctrl')
  if (binding.altKey) keys.push('Alt')
  if (binding.shiftKey) keys.push('Shift')
  if (binding.metaKey) keys.push('Cmd')
  
  keys.push(formatKey(binding.key))
  
  return keys
}

export function formatKey(key: string): string {
  const keyMap: Record<string, string> = {
    'Escape': 'Esc',
    'ArrowUp': '↑',
    'ArrowDown': '↓',
    'ArrowLeft': '←',
    'ArrowRight': '→',
    ' ': 'Space'
  }
  
  return keyMap[key] || key.toUpperCase()
}

export function shortcutToString(binding: ShortcutBinding): string {
  return formatShortcutKeys(binding).join('+')
}

export function checkShortcutConflict(
  binding: ShortcutBinding,
  existingShortcuts: ShortcutPreferences,
  currentId: string
): string | null {
  for (const [id, shortcut] of Object.entries(existingShortcuts)) {
    if (id === currentId) continue
    
    if (
      shortcut.key === binding.key &&
      !!shortcut.ctrlKey === !!binding.ctrlKey &&
      !!shortcut.shiftKey === !!binding.shiftKey &&
      !!shortcut.altKey === !!binding.altKey &&
      !!shortcut.metaKey === !!binding.metaKey
    ) {
      const conflictingShortcut = DEFAULT_SHORTCUTS.find(s => s.id === id)
      return conflictingShortcut?.description || 'otro atajo'
    }
  }
  
  return null
}

export function getDefaultBinding(id: string): ShortcutBinding | null {
  const defaultShortcut = DEFAULT_SHORTCUTS.find(s => s.id === id)
  if (!defaultShortcut) return null
  
  return {
    id: defaultShortcut.id,
    key: defaultShortcut.key,
    ctrlKey: defaultShortcut.ctrlKey,
    shiftKey: defaultShortcut.shiftKey,
    altKey: defaultShortcut.altKey,
    metaKey: defaultShortcut.metaKey
  }
}

export function initializeShortcutPreferences(): ShortcutPreferences {
  const preferences: ShortcutPreferences = {}
  
  for (const shortcut of DEFAULT_SHORTCUTS) {
    preferences[shortcut.id] = {
      id: shortcut.id,
      key: shortcut.key,
      ctrlKey: shortcut.ctrlKey,
      shiftKey: shortcut.shiftKey,
      altKey: shortcut.altKey,
      metaKey: shortcut.metaKey
    }
  }
  
  return preferences
}
