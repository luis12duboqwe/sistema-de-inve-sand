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

export const DEFAULT_SHORTCUTS: Omit<KeyboardShortcut, 'action'>[

    shiftKey: true,
   
  {
    key: 'k',
    description: 'E
  },
    id: 'open-settings'
    
   
  {
    key: '1',
    category: 'nav
  {
    key: '2',
    
  {
    key: '3',
    category:
  {
    key: 'n',
    description: 'Crear
  },
   
    ctrlKey: true,
    category:
  {
    key: 'i',
    
  }
    id: 'bulk-mode',
    ctrlKey: 
    category: 'actions'
  {
    
   
  {
    key: 'a',
    description: 'Seleccionar tod
  }

  g
  actions: 'Acciones'
}
export const CATEG
  navigation: 'package',
  search: 'magnifying-g

  c
  if (binding.ctrlKey
  if (binding
  
  
}
expo
   
    'ArrowDown': '↓',
    'ArrowRig
  }
  return keyMap[key] || key.toUpperCas

  re

  binding: ShortcutB
  currentId: 
  for (const [id, 
    
      shortcut.key === 
    
   
      const conflicting
    }
  
}
expo
  i
  return {
    key: defa
    shiftKey: defa
    metaKey: defaultShortcut.metaKey
}
exp
 

      key: shortcut.key,
      shiftKey: short
      metaKey: shortcut.met
  }
  return preferences




























































































