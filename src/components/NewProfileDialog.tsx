import { useState, useEffect } from 'react'
  Dialog
  DialogD
  DialogTitle,
} from '@/components
import { Input 
import { Alert

  open: boolean
  onSubmit: (name: string, slug: string) => Pro

  return /^[a-z0-9][a-z0-9-]*[a-z0-9]$/.test(

  return name

    .replace(/[^a-z0-9\s-]/g, '')
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
    setName('')
    setManualSlugEdit(fa
 

    if (open) {
    }

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
   

      return
    setIsSubmit
      await onSub
    }
    } finall

  useEffect(() => {
    if (!manualSlugEdit && name) {
      setSlug(generateSlug(name))
    }
  }, [name, manualSlugEdit])

        <DialogHeader>
          <DialogD
          </Dial
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


























          <Alert>

            <AlertDescription>



        </div>

        <DialogFooter>
          <Button 








            disabled={!isValid || isSubmitting}



        </DialogFooter>

    </Dialog>

}
