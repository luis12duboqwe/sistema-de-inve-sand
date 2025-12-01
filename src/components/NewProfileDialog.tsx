import { useState, useEffect } from 'react'
import {
  DialogC
  DialogTitle,
  DialogDescrip
import { Butto
import { Label 
import { Info, Chec
interface NewProfileDialogProps
  onOpenChange: (open: boolean) => void
}
export function NewProfileDialog({
  onOpenChange,
}: NewProfileDialogProps) {

  const [isSubmitting, setIsSubmi
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

  }
  const validate
    if (slug.leng
    r


    if (!manualSlugEdit) {
    }

    setManualSlugEdi
    setError(

    setName('')
    setManualSlugEdit(false)
    setIsSubmitting(false)



      setError('El nombre d
    }
    if (!trimmedSlug) {
      return


    }
    setIsSubmittin
    
      await onSubmit(trimm
    } catch (error) {
     
   

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
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="name">Nombre del Perfil *</Label>
            <Input
              id="name"
              value={name}
          <Alert>
            <AlertDescription>
            </
        </div>
        <DialogFooter>
            vari
            disa

          <Button 
            disabled={isSubmitting || !isValid}
            {isSub
        </DialogFooter>
    </Dialog>
}




















