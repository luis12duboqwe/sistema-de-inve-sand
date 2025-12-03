import { useEffect, useRef } from 'react'
import { useKV } from '@github/spark/hooks'
import type { KeyboardShortcut, ShortcutPreferences } from '@/lib/keyboardShortcuts'
import { initializeShortcutPreferences } from '@/lib/keyboardShortcuts'

export function useKeyboardShortcuts(shortcuts: KeyboardShortcut[]) {
  const [preferences] = useKV<ShortcutPreferences>('keyboard-shortcuts', initializeShortcutPreferences())
  const shortcutsRef = useRef(shortcuts)

  useEffect(() => {
    shortcutsRef.current = shortcuts
  }, [shortcuts])

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement
      
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
        const allowedKeys = ['Escape']
        if (!allowedKeys.includes(event.key)) {
          return
        }
      }

      for (const shortcut of shortcutsRef.current) {
        const binding = preferences?.[shortcut.id]
        if (!binding) continue

        const ctrlOrMeta = event.ctrlKey || event.metaKey
        
        const ctrlMatch = binding.ctrlKey ? ctrlOrMeta : !ctrlOrMeta
        const shiftMatch = binding.shiftKey ? event.shiftKey : !event.shiftKey
        const altMatch = binding.altKey ? event.altKey : !event.altKey
        
        const keyMatch = event.key.toLowerCase() === binding.key.toLowerCase()

        if (ctrlMatch && shiftMatch && altMatch && keyMatch) {
          event.preventDefault()
          event.stopPropagation()
          shortcut.action()
          break
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [preferences])
}

export { type KeyboardShortcut, type ShortcutPreferences }
