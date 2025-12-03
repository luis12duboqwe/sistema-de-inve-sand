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
import { Keyboard, Package, ShoppingCart, UserCircle, MagnifyingGlass, Gear, Wrench } from '@phosphor-icons/react'
import { Separator } from '@/components/ui/separator'
import { CustomizeShortcutsDialog } from './CustomizeShortcutsDialog'
import { formatShortcutKeys, initializeShortcutPreferences, type ShortcutPreferences } from '@/lib/keyboardShortcuts'

interface KeyboardShortcutsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

interface ShortcutGroup {
  title: string
  icon: React.ReactNode
  category: string
}

export function KeyboardShortcutsDialog({ open, onOpenChange }: KeyboardShortcutsDialogProps) {
  const [preferences] = useKV<ShortcutPreferences>('keyboard-shortcuts', initializeShortcutPreferences())
  const [showCustomize, setShowCustomize] = useState(false)

  const shortcutGroups: ShortcutGroup[] = [
    {
      title: 'General',
      icon: <Keyboard size={18} weight="duotone" />,
      category: 'general'
    },
    {
      title: 'Navegación',
      icon: <Package size={18} weight="duotone" />,
      category: 'navigation'
    },
    {
      title: 'Acciones',
      icon: <ShoppingCart size={18} weight="duotone" />,
      category: 'actions'
    },
    {
      title: 'Búsqueda y Filtros',
      icon: <MagnifyingGlass size={18} weight="duotone" />,
      category: 'search'
    }
  ]

  const shortcutsByCategory: Record<string, Array<{ id: string; description: string }>> = {
    general: [
      { id: 'show-help', description: 'Mostrar atajos de teclado' },
      { id: 'focus-search', description: 'Enfocar búsqueda' },
      { id: 'open-settings', description: 'Abrir configuración' },
    ],
    navigation: [
      { id: 'nav-products', description: 'Ir a Productos' },
      { id: 'nav-orders', description: 'Ir a Órdenes' },
      { id: 'nav-profiles', description: 'Ir a Perfiles' },
    ],
    actions: [
      { id: 'create-new', description: 'Crear nuevo elemento' },
      { id: 'export-csv', description: 'Exportar a CSV' },
      { id: 'import-csv', description: 'Importar desde CSV' },
      { id: 'bulk-mode', description: 'Modo selección múltiple' },
    ],
    search: [
      { id: 'clear-search', description: 'Limpiar búsqueda' },
      { id: 'select-all', description: 'Seleccionar todos (en modo bulk)' },
    ]
  }

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center justify-between text-2xl">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center">
                  <Keyboard size={28} weight="duotone" className="text-primary" />
                </div>
                <div>
                  <div>Atajos de Teclado</div>
                  <DialogDescription className="mt-1">
                    Domina el sistema con estos atajos para trabajar más rápido
                  </DialogDescription>
                </div>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowCustomize(true)}
                className="flex items-center gap-2"
              >
                <Wrench size={16} />
                Personalizar
              </Button>
            </DialogTitle>
          </DialogHeader>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-4">
            {shortcutGroups.map((group, groupIndex) => (
              <div key={groupIndex} className="space-y-3">
                <div className="flex items-center gap-2 text-sm font-semibold text-foreground mb-3">
                  <div className="w-8 h-8 rounded-md bg-accent/50 flex items-center justify-center">
                    {group.icon}
                  </div>
                  {group.title}
                </div>
                <div className="space-y-2">
                  {shortcutsByCategory[group.category]?.map((shortcut, shortcutIndex) => {
                    const binding = preferences?.[shortcut.id]
                    const keys = binding ? formatShortcutKeys(binding) : []

                    return (
                      <div 
                        key={shortcutIndex} 
                        className="flex items-center justify-between p-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors"
                      >
                        <span className="text-sm text-foreground flex-1">
                          {shortcut.description}
                        </span>
                        <div className="flex gap-1 ml-4">
                          {keys.map((key, keyIndex) => (
                            <kbd 
                              key={keyIndex}
                              className="px-2 py-1 text-xs font-semibold text-foreground bg-background border border-border rounded shadow-sm min-w-[28px] text-center"
                            >
                              {key}
                            </kbd>
                          ))}
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
              <Gear size={18} weight="duotone" className="text-primary" />
              Consejos Pro
            </div>
            <ul className="text-xs text-muted-foreground space-y-1 ml-6">
              <li>• Los atajos funcionan en cualquier parte del sistema</li>
              <li>• Usa el modo selección múltiple (Ctrl+B) para acciones masivas</li>
              <li>• La búsqueda filtra en tiempo real mientras escribes</li>
              <li>• Presiona Esc en cualquier diálogo para cerrarlo</li>
              <li>• Haz clic en "Personalizar" para cambiar los atajos</li>
            </ul>
          </div>

          <div className="text-center pt-2">
            <p className="text-xs text-muted-foreground">
              Presiona <kbd className="px-2 py-0.5 text-xs font-semibold bg-background border border-border rounded mx-1">Shift</kbd> + <kbd className="px-2 py-0.5 text-xs font-semibold bg-background border border-border rounded mx-1">?</kbd> en cualquier momento para ver esta ayuda
            </p>
          </div>
        </DialogContent>
      </Dialog>

      <CustomizeShortcutsDialog
        open={showCustomize}
        onOpenChange={setShowCustomize}
      />
    </>
  )
}
