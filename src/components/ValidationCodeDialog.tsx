import { useEffect, useState } from 'react'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { LockKey } from '@phosphor-icons/react'

interface ValidationCodeDialogProps {
  open: boolean
  title: string
  description: string
  confirmLabel?: string
  onCancel: () => void
  onConfirm: (code: string) => void
}

export function ValidationCodeDialog({
  open,
  title,
  description,
  confirmLabel = 'Confirmar',
  onCancel,
  onConfirm,
}: ValidationCodeDialogProps) {
  const [code, setCode] = useState('')

  useEffect(() => {
    if (open) setCode('')
  }, [open])

  const submit = () => {
    const trimmed = code.trim()
    if (!trimmed) return
    onConfirm(trimmed)
  }

  return (
    <Dialog open={open} onOpenChange={isOpen => !isOpen && onCancel()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <LockKey size={20} weight="fill" />
            {title}
          </DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          <Label htmlFor="validation-code-dialog-input">Código de validación</Label>
          <Input
            id="validation-code-dialog-input"
            type="password"
            value={code}
            onChange={event => setCode(event.target.value)}
            onKeyDown={event => event.key === 'Enter' && submit()}
            autoComplete="off"
            autoFocus
          />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onCancel}>Cancelar</Button>
          <Button onClick={submit} disabled={!code.trim()}>{confirmLabel}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
