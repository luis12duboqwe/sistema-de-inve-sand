import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog'
import { PhotoRequestsDashboard } from './PhotoRequestsDashboard'

interface PhotoRequestsDashboardDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function PhotoRequestsDashboardDialog({
  open,
  onOpenChange,
}: PhotoRequestsDashboardDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Solicitudes de Fotos</DialogTitle>
        </DialogHeader>
        <PhotoRequestsDashboard />
      </DialogContent>
    </Dialog>
  )
}
