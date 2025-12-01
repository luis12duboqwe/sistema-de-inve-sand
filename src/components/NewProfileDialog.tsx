import { useState, useEffect } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
  open: boolean

}
  open: boolean
  return /^[a-z0-9][a-z0-9-]*[a-z0-9]$/
  onSubmit: (name: string, slug: string) => Promise<void>
f

function validateSlug(slug: string): boolean {
  return /^[a-z0-9][a-z0-9-]*[a-z0-9]$/.test(slug) && slug.length >= 2
 

function generateSlug(name: string): string {
  return name
  open,
    .normalize('NFD')
}: NewProfileDialogProps) {
    .replace(/[^a-z0-9\s-]/g, '')
    .trim()
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
}

export function NewProfileDialog({
    set
  onOpenChange,
  }
  const handleSubmit = asyn
      setError('El nombre es requerido
    }
    if (!slug.trim()) {
      return


    }
    setIsSubmit
      await onS
    } catch (error) {
    } finally {
    }
  }

    <Dialog open={o
        <Dialog
        </DialogH
     
            

              onCha
                setError('')
              placeholder="Mi Neg
     


              id="slug"
              onChange={(e) => h
              disabled={isS
            <p c
   

  const handleSubmit = async () => {
            </Alert>
      setError('El nombre es requerido')
            
     

    if (!slug.trim()) {
      setError('El slug es requerido')
            
    }

    if (!validateSlug(slug.trim())) {
      setError('El slug debe contener solo letras minúsculas, números y guiones, con mínimo 2 caracteres')
      return
    }

    setIsSubmitting(true)

      await onSubmit(name.trim(), slug.trim())

    } catch (error) {
      setError(error instanceof Error ? error.message : 'Error al crear el perfil')
    } finally {
      setIsSubmitting(false)

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
