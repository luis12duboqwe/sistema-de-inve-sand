import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Keyboard, Package, ShoppingCart, UserCircle, MagnifyingGlass, Gear } from '@phosphor-icons/react'
import { Separator } from '@/components/ui/separator'

interface KeyboardShortcutsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

interface ShortcutGroup {
  title: string
  icon: React.ReactNode
  shortcuts: Array<{
    keys: string[]
    description: string
  }>
}

export function KeyboardShortcutsDialog({ open, onOpenChange }: KeyboardShortcutsDialogProps) {
  const shortcutGroups: ShortcutGroup[] = [
    {
      title: 'General',
      icon: <Keyboard size={18} weight="duotone" />,
      shortcuts: [
        { keys: ['Shift', '?'], description: 'Mostrar atajos de teclado' },
        { keys: ['Ctrl', 'K'], description: 'Enfocar búsqueda' },
        { keys: ['Ctrl', ','], description: 'Abrir configuración' },
      ]
    },
    {
      title: 'Navegación',
      icon: <Package size={18} weight="duotone" />,
      shortcuts: [
        { keys: ['1'], description: 'Ir a Productos' },
        { keys: ['2'], description: 'Ir a Órdenes' },
        { keys: ['3'], description: 'Ir a Perfiles' },
      ]
    },
    {
      title: 'Acciones',
      icon: <ShoppingCart size={18} weight="duotone" />,
      shortcuts: [
        { keys: ['Ctrl', 'N'], description: 'Crear nuevo elemento' },
        { keys: ['Ctrl', 'E'], description: 'Exportar a CSV' },
        { keys: ['Ctrl', 'I'], description: 'Importar desde CSV' },
        { keys: ['Ctrl', 'B'], description: 'Modo selección múltiple' },
      ]
    },
    {
      title: 'Búsqueda y Filtros',
      icon: <MagnifyingGlass size={18} weight="duotone" />,
      shortcuts: [
        { keys: ['Esc'], description: 'Limpiar búsqueda' },
        { keys: ['Ctrl', 'A'], description: 'Seleccionar todos (en modo bulk)' },
      ]
    }
  ]

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3 text-2xl">
            <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center">
              <Keyboard size={28} weight="duotone" className="text-primary" />
            </div>
            <div>
              <div>Atajos de Teclado</div>
              <DialogDescription className="mt-1">
                Domina el sistema con estos atajos para trabajar más rápido
              </DialogDescription>
            </div>
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
                {group.shortcuts.map((shortcut, shortcutIndex) => (
                  <div 
                    key={shortcutIndex} 
                    className="flex items-center justify-between p-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors"
                  >
                    <span className="text-sm text-foreground flex-1">
                      {shortcut.description}
                    </span>
                    <div className="flex gap-1 ml-4">
                      {shortcut.keys.map((key, keyIndex) => (
                        <kbd 
                          key={keyIndex}
                          className="px-2 py-1 text-xs font-semibold text-foreground bg-background border border-border rounded shadow-sm min-w-[28px] text-center"
                        >
                          {key}
                        </kbd>
                      ))}
                    </div>
                  </div>
                ))}
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
          </ul>
        </div>

        <div className="text-center pt-2">
          <p className="text-xs text-muted-foreground">
            Presiona <kbd className="px-2 py-0.5 text-xs font-semibold bg-background border border-border rounded mx-1">Shift</kbd> + <kbd className="px-2 py-0.5 text-xs font-semibold bg-background border border-border rounded mx-1">?</kbd> en cualquier momento para ver esta ayuda
          </p>
        </div>
      </DialogContent>
    </Dialog>
  )
}
