import { useState, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Info } from '@phosphor-icons/react'

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
  const [manualSlugEdit, setManualSlugEdit] = useState(false)
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const resetForm = () => {
    setName('')
    setSlug('')
    setManualSlugEdit(false)
    setError('')
    setIsSubmitting(false)
  }

  useEffect(() => {
    if (open) {
      resetForm()
    }
  }, [open])

  useEffect(() => {
    if (!manualSlugEdit && name) {
      setSlug(generateSlug(name))
    }
  }, [name, manualSlugEdit])

  const handleNameChange = (value: string) => {
    setName(value)
    setError('')
  }

  const handleSlugChange = (value: string) => {
    setSlug(value.toLowerCase())
    setManualSlugEdit(true)
    setError('')
  }

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
      resetForm()
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Error al crear el perfil')
    } finally {
      setIsSubmitting(false)
    }
  }

  const isValid = name.trim() && slug.trim() && validateSlug(slug.trim())

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Crear Nuevo Perfil</DialogTitle>
          <DialogDescription>
            Crea un nuevo perfil de negocio para organizar tus productos y órdenes.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="name">Nombre del Perfil *</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => handleNameChange(e.target.value)}
              placeholder="Ej: Mi Tienda Principal"
              disabled={isSubmitting}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="slug">Slug (Identificador único) *</Label>
            <Input
              id="slug"
              value={slug}
              onChange={(e) => handleSlugChange(e.target.value)}
              placeholder="mi-tienda-principal"
              disabled={isSubmitting}
            />
            <p className="text-xs text-muted-foreground">
              Solo letras minúsculas, números y guiones. Mínimo 2 caracteres.
            </p>
          </div>

          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <Alert>
            <Info className="h-4 w-4" />
            <AlertDescription>
              El slug se usa para identificar de forma única este perfil en el sistema.
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
