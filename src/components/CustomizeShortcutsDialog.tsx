import { useState } from 'react'
import { useKV } from '@github/spark/hooks'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { toast } from 'sonner'
import { Keyboard, ArrowCounterClockwise, PencilSimple, Check, X, Warning } from '@phosphor-icons/react'
import {
  DEFAULT_SHORTCUTS,
  CATEGORY_LABELS,
  formatShortcutKeys,
  checkShortcutConflict,
  initializeShortcutPreferences,
  type ShortcutPreferences,
  type ShortcutBinding
} from '@/lib/keyboardShortcuts'

interface CustomizeShortcutsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function CustomizeShortcutsDialog({ open, onOpenChange }: CustomizeShortcutsDialogProps) {
  const [preferences, setPreferences] = useKV<ShortcutPreferences>('keyboard-shortcuts', initializeShortcutPreferences())
  const [editingId, setEditingId] = useState<string | null>(null)
  const [recordedKeys, setRecordedKeys] = useState<ShortcutBinding | null>(null)
  const [conflictError, setConflictError] = useState<string | null>(null)

  const handleStartRecording = (id: string) => {
    setEditingId(id)
    setRecordedKeys(null)
    setConflictError(null)

    const handleKeyDown = (event: KeyboardEvent) => {
      event.preventDefault()
      event.stopPropagation()

      if (event.key === 'Escape') {
        setEditingId(null)
        setRecordedKeys(null)
        setConflictError(null)
        window.removeEventListener('keydown', handleKeyDown)
        return
      }

      const newBinding: ShortcutBinding = {
        id,
        key: event.key,
        ctrlKey: event.ctrlKey,
        shiftKey: event.shiftKey,
        altKey: event.altKey,
        metaKey: event.metaKey
      }

      const conflict = checkShortcutConflict(newBinding, preferences || {}, id)
      if (conflict) {
        setConflictError(`Conflicto con: ${conflict}`)
        setRecordedKeys(newBinding)
      } else {
        setConflictError(null)
        setRecordedKeys(newBinding)
      }
    }

    window.addEventListener('keydown', handleKeyDown, { once: false })

    setTimeout(() => {
      window.removeEventListener('keydown', handleKeyDown)
    }, 30000)
  }

  const handleSaveBinding = () => {
    if (!editingId || !recordedKeys || conflictError) return

    setPreferences((current) => ({
      ...current,
      [editingId]: recordedKeys
    }))

    toast.success('Atajo actualizado')
    setEditingId(null)
    setRecordedKeys(null)
    setConflictError(null)
  }

  const handleCancelEdit = () => {
    setEditingId(null)
    setRecordedKeys(null)
    setConflictError(null)
  }

  const handleResetAll = () => {
    setPreferences(initializeShortcutPreferences())
    toast.success('Atajos restaurados a valores predeterminados')
  }

  const handleResetSingle = (id: string) => {
    const defaultBinding = DEFAULT_SHORTCUTS.find(s => s.id === id)
    if (!defaultBinding) return

    setPreferences((current) => ({
      ...current,
      [id]: {
        id,
        key: defaultBinding.key,
        ctrlKey: defaultBinding.ctrlKey,
        shiftKey: defaultBinding.shiftKey,
        altKey: defaultBinding.altKey,
        metaKey: defaultBinding.metaKey
      }
    }))

    toast.success('Atajo restaurado')
  }

  const groupedShortcuts = DEFAULT_SHORTCUTS.reduce((acc, shortcut) => {
    if (!acc[shortcut.category]) {
      acc[shortcut.category] = []
    }
    acc[shortcut.category].push(shortcut)
    return acc
  }, {} as Record<string, typeof DEFAULT_SHORTCUTS>)

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center justify-between text-2xl">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center">
                <Keyboard size={28} weight="duotone" className="text-primary" />
              </div>
              <div>
                <div>Personalizar Atajos</div>
                <DialogDescription className="mt-1">
                  Configura los atajos de teclado según tus preferencias
                </DialogDescription>
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleResetAll}
              className="flex items-center gap-2"
            >
              <ArrowCounterClockwise size={16} />
              Restaurar Todo
            </Button>
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-6 mt-4">
          {Object.entries(groupedShortcuts).map(([category, shortcuts]) => (
            <div key={category} className="space-y-3">
              <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <div className="w-8 h-8 rounded-md bg-accent/50 flex items-center justify-center">
                  <Keyboard size={16} weight="duotone" />
                </div>
                {CATEGORY_LABELS[category] || category}
              </h3>

              <div className="space-y-2">
                {shortcuts.map((shortcut) => {
                  const currentBinding = preferences?.[shortcut.id]
                  const isEditing = editingId === shortcut.id
                  const displayBinding = isEditing && recordedKeys ? recordedKeys : currentBinding

                  return (
                    <div
                      key={shortcut.id}
                      className="flex items-center justify-between p-4 rounded-lg bg-card border border-border hover:border-primary/50 transition-colors"
                    >
                      <div className="flex-1">
                        <div className="text-sm font-medium text-foreground">
                          {shortcut.description}
                        </div>
                        {isEditing && (
                          <div className="text-xs text-muted-foreground mt-1">
                            {conflictError ? (
                              <span className="text-destructive flex items-center gap-1">
                                <Warning size={12} />
                                {conflictError}
                              </span>
                            ) : recordedKeys ? (
                              <span className="text-accent">Presiona Enter para guardar o Esc para cancelar</span>
                            ) : (
                              <span className="text-primary animate-pulse">Presiona una combinación de teclas...</span>
                            )}
                          </div>
                        )}
                      </div>

                      <div className="flex items-center gap-2 ml-4">
                        {displayBinding && (
                          <div className="flex gap-1">
                            {formatShortcutKeys(displayBinding).map((key, index) => (
                              <kbd
                                key={index}
                                className={`px-3 py-1.5 text-xs font-semibold ${
                                  isEditing && recordedKeys
                                    ? conflictError
                                      ? 'text-destructive-foreground bg-destructive/10 border-destructive'
                                      : 'text-accent-foreground bg-accent/20 border-accent'
                                    : 'text-foreground bg-background border-border'
                                } border rounded shadow-sm min-w-[32px] text-center transition-colors`}
                              >
                                {key}
                              </kbd>
                            ))}
                          </div>
                        )}

                        {isEditing ? (
                          <div className="flex gap-1">
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={handleSaveBinding}
                              disabled={!recordedKeys || !!conflictError}
                              className="h-8 w-8 p-0"
                              title="Guardar"
                            >
                              <Check size={16} className="text-accent" />
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={handleCancelEdit}
                              className="h-8 w-8 p-0"
                              title="Cancelar"
                            >
                              <X size={16} className="text-muted-foreground" />
                            </Button>
                          </div>
                        ) : (
                          <div className="flex gap-1">
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => handleStartRecording(shortcut.id)}
                              className="h-8 w-8 p-0"
                              title="Editar atajo"
                            >
                              <PencilSimple size={16} />
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => handleResetSingle(shortcut.id)}
                              className="h-8 w-8 p-0"
                              title="Restaurar predeterminado"
                            >
                              <ArrowCounterClockwise size={16} />
                            </Button>
                          </div>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          ))}
        </div>

        <Separator className="my-4" />

        <div className="bg-accent/30 rounded-lg p-4 space-y-2">
          <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
            <Keyboard size={18} weight="duotone" className="text-primary" />
            Consejos
          </div>
          <ul className="text-xs text-muted-foreground space-y-1 ml-6">
            <li>• Haz clic en el ícono de lápiz para cambiar un atajo</li>
            <li>• El sistema detectará automáticamente conflictos</li>
            <li>• Usa el botón de restaurar para volver al atajo predeterminado</li>
            <li>• Los cambios se aplican inmediatamente</li>
            <li>• Presiona Esc mientras grabas para cancelar</li>
          </ul>
        </div>
      </DialogContent>
    </Dialog>
  )
}
