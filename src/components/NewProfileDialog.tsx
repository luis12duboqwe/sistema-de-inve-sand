import { useState, useEffect } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'

interface NewProfileDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (name: string, slug: string) => Promise<void>
}

function validateSlug(slug: string): boolean {
  return /^[a-z0-9][a-z0-9-]*[a-z0-9]$/.test(slug) && slug.length >= 2
}

function generateSlug(name: string): string {
  return name
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9\s-]/g, '')
    .trim()
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
}

export function NewProfileDialog({
  open,
  onOpenChange,
  onSubmit
}: NewProfileDialogProps) {
  const [name, setName] = useState('')
  const [slug, setSlug] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    if (!open) {
      setName('')
      setSlug('')
      setError('')
      setIsSubmitting(false)
    }
  }, [open])

  const handleNameChange = (value: string) => {
    setName(value)
    if (value.trim()) {
      setSlug(generateSlug(value))
    } else {
      setSlug('')
    }
    setError('')
  }

  const handleSlugChange = (value: string) => {
    setSlug(value.toLowerCase())
    setError('')
  }

  const isValid = name.trim() && slug.trim() && validateSlug(slug.trim())

  const handleSubmit = async () => {
    if (!name.trim()) {
      setError('El nombre es requerido')
      return
    }

    if (!slug.trim()) {
      setError('El slug es requerido')
      return
    }

    if (!validateSlug(slug.trim())) {
      setError('El slug debe contener solo letras minúsculas, números y guiones, con mínimo 2 caracteres')
      return
    }

    setIsSubmitting(true)
    try {
      await onSubmit(name.trim(), slug.trim())
      setName('')
      setSlug('')
      setError('')
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Error al crear el perfil')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Crear Nuevo Perfil</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="name">Nombre del Perfil *</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => handleNameChange(e.target.value)}
              disabled={isSubmitting}
              placeholder="Mi Negocio"
              autoFocus
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="slug">Slug (identificador único) *</Label>
            <Input
              id="slug"
              value={slug}
              onChange={(e) => handleSlugChange(e.target.value)}
              disabled={isSubmitting}
              placeholder="mi-negocio"
            />
            <p className="text-xs text-muted-foreground">
              Solo letras minúsculas, números y guiones. Se genera automáticamente.
            </p>
          </div>

          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <Alert>
            <AlertDescription>
              Los perfiles te permiten gestionar múltiples negocios o líneas de productos de forma independiente.
            </AlertDescription>
          </Alert>
        </div>

        <DialogFooter>
          <Button 
            variant="outline" 
            onClick={() => onOpenChange(false)}
            disabled={isSubmitting}
          >
            Cancelar
          </Button>
          <Button 
            onClick={handleSubmit}
            disabled={!isValid || isSubmitting}
          >
            {isSubmitting ? 'Creando...' : 'Crear Perfil'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
