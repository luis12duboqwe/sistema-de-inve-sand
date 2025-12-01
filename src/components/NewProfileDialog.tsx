import { useState, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Info, CheckCircle, WarningCircle } from '@phosphor-icons/react'

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
    if (!open) {
      resetForm()
    }
  }, [open])

  const generateSlug = (text: string): string => {
    if (!text) return ''
    return String(text)
      .toLowerCase()
      .trim()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '')
  }

  const validateSlug = (slug: string): boolean => {
    if (!slug) return false
    if (slug.length < 2) return false
    const validSlugRegex = /^[a-z0-9]+(-[a-z0-9]+)*$/
    return validSlugRegex.test(slug)
  }

  const handleNameChange = (value: string) => {
    setName(value)
    setError('')
    if (!manualSlugEdit) {
      setSlug(generateSlug(value))
    }
  }

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

  const isValid = name.trim() && slug.trim() && validateSlug(slug.trim())

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Crear Nuevo Perfil</DialogTitle>
          <DialogDescription>
            Crea un nuevo perfil de negocio para gestionar productos y órdenes de forma independiente
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {error && (
            <Alert variant="destructive">
              <WarningCircle size={16} className="mt-0.5" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <div className="space-y-2">
            <Label htmlFor="name">Nombre del Perfil *</Label>
            <Input
              id="name"
              value={name}
              onChange={e => handleNameChange(e.target.value)}
              placeholder="Mi Tienda de Celulares"
              autoComplete="off"
              disabled={isSubmitting}
            />
            <p className="text-xs text-muted-foreground">
              El nombre que se mostrará en la interfaz
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="slug">Slug *</Label>
            <div className="relative">
              <Input
                id="slug"
                value={slug}
                onChange={e => handleSlugChange(e.target.value)}
                placeholder="mi-tienda-celulares"
                autoComplete="off"
                disabled={isSubmitting}
                className={slug && !validateSlug(slug) ? 'border-destructive' : ''}
              />
              {slug && validateSlug(slug) && (
                <CheckCircle 
                  size={18} 
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-accent" 
                  weight="fill"
                />
              )}
            </div>
            <p className="text-xs text-muted-foreground">
              Identificador único (solo letras minúsculas, números y guiones)
            </p>
          </div>

          <Alert>
            <Info size={16} className="mt-0.5" />
            <AlertDescription>
              El slug no se puede modificar después de crear el perfil. Asegúrate de que sea correcto.
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
            {isSubmitting ? 'Creando...' : 'Crear Perfil'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
