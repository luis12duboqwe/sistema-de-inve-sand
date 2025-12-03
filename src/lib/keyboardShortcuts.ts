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
  search: 'Búsqueda'
}

export const CATEGORY_ICONS: Record<string, string> = {
  general: 'gear',
  navigation: 'package',
  actions: 'lightning',
  search: 'magnifying-glass'
}

export function formatShortcut(binding: ShortcutBinding): string {
  const parts: string[] = []
  
  if (binding.ctrlKey) parts.push('Ctrl')
  if (binding.shiftKey) parts.push('Shift')
  if (binding.altKey) parts.push('Alt')
  if (binding.metaKey) parts.push('Cmd')
  
  parts.push(formatKey(binding.key))
  
  return parts.join(' + ')
}

export function formatKey(key: string): string {
  const keyMap: Record<string, string> = {
    'ArrowUp': '↑',
    'ArrowDown': '↓',
    'ArrowLeft': '←',
    'ArrowRight': '→',
    'Escape': 'Esc'
  }
  
  return keyMap[key] || key.toUpperCase()
}

export function checkShortcutConflict(
  binding: ShortcutBinding,
  currentId: string,
  allShortcuts: Record<string, ShortcutBinding>
): string | null {
  for (const [id, shortcut] of Object.entries(allShortcuts)) {
    if (id === currentId) continue
    
    if (
      shortcut.key === binding.key &&
      shortcut.ctrlKey === binding.ctrlKey &&
      shortcut.shiftKey === binding.shiftKey &&
      shortcut.altKey === binding.altKey &&
      shortcut.metaKey === binding.metaKey
    ) {
      const conflicting = DEFAULT_SHORTCUTS.find(s => s.id === id)
      return conflicting?.description || id
    }
  }
  
  return null
}

export function getDefaultBinding(id: string): ShortcutBinding | null {
  const defaultShortcut = DEFAULT_SHORTCUTS.find(s => s.id === id)
  if (!defaultShortcut) return null
  
  return {
    id,
    key: defaultShortcut.key,
    ctrlKey: defaultShortcut.ctrlKey,
    shiftKey: defaultShortcut.shiftKey,
    altKey: defaultShortcut.altKey,
    metaKey: defaultShortcut.metaKey
  }
}

export function loadShortcutPreferences(): Record<string, ShortcutBinding> {
  const preferences: Record<string, ShortcutBinding> = {}
  
  DEFAULT_SHORTCUTS.forEach(shortcut => {
    preferences[shortcut.id] = {
      id: shortcut.id,
      key: shortcut.key,
      ctrlKey: shortcut.ctrlKey,
      shiftKey: shortcut.shiftKey,
      altKey: shortcut.altKey,
      metaKey: shortcut.metaKey
    }
  })
  
  return preferences
}

export function initializeShortcutPreferences(): Record<string, ShortcutBinding> {
  return loadShortcutPreferences()
}
