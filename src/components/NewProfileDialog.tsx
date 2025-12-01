import { useState, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Info, Check } from '@phosphor-icons/react'

interface NewProfileDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (name: string, slug: string) => Promise<void>
}

export function NewProfileDialog({
  open,
  onOpenChange,
  onSubmit
}: NewProfileDialogProps) {
  const [name, setName] = useState('')
  const [slug, setSlug] = useState('')
  const [manualSlugEdit, setManualSlugEdit] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!manualSlugEdit && name) {
      const generatedSlug = name
        .toLowerCase()
        .trim()
        .replace(/[^a-z0-9\s-]/g, '')
        .replace(/\s+/g, '-')
        .replace(/-+/g, '-')
      setSlug(generatedSlug)
    }
  }, [name, manualSlugEdit])

  useEffect(() => {
    if (!open) {
      resetForm()
    }
  }, [open])

  const validateSlug = (value: string) => {
    if (value.length < 2) return false
    return /^[a-z0-9-]+$/.test(value)
  }

  const isValid = name.trim() && slug.trim() && validateSlug(slug.trim())

  const handleSlugChange = (value: string) => {
    setManualSlugEdit(true)
    setSlug(value.toLowerCase())
    setError('')
  }

  const resetForm = () => {
    setName('')
    setSlug('')
    setManualSlugEdit(false)
    setError('')
    setIsSubmitting(false)
  }

  const handleSubmit = async () => {
    const trimmedName = name.trim()
    const trimmedSlug = slug.trim()

    if (!trimmedName) {
      setError('El nombre del perfil es requerido')
      return
    }

    if (!trimmedSlug) {
      setError('El slug es requerido')
      return
    }

    if (!validateSlug(trimmedSlug)) {
      setError('El slug debe contener solo letras minúsculas, números y guiones (mínimo 2 caracteres)')
      return
    }

    setIsSubmitting(true)
    setError('')
    
    try {
      await onSubmit(trimmedName, trimmedSlug)
      resetForm()
    } catch (error) {
      console.error('Error submitting profile:', error)
      if (error instanceof Error) {
        setError(error.message)
      } else {
        setError('Error al crear el perfil. Por favor intenta de nuevo.')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Crear Nuevo Perfil</DialogTitle>
          <DialogDescription>
            Crea un nuevo perfil de negocio para organizar tus productos y órdenes
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="name">Nombre del Perfil *</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => {
                setName(e.target.value)
                setError('')
              }}
              placeholder="Mi Negocio"
              disabled={isSubmitting}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="slug">Slug (identificador único) *</Label>
            <Input
              id="slug"
              value={slug}
              onChange={(e) => handleSlugChange(e.target.value)}
              placeholder="mi-negocio"
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
            <Info size={16} className="mt-0.5" />
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
            disabled={isSubmitting || !isValid}
          >
            {isSubmitting ? 'Creando...' : (
              <>
                <Check size={18} className="mr-2" />
                Crear Perfil
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
