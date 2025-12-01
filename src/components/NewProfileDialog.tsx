import { useState, useEffect } from 'react'
import {
  DialogC
  DialogTitle,
  DialogFooter
import { Butto
import { Label } fro
import { Info 
interface NewProfileDialogProps
  onOpenChange: (open: boolean) => void
}
function validateSlug(slug: string): boolean 
}
function generateSlug(name: string): string 

    .replace(/[\u0300-\u036f]/g, 
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
    if (op
    }

    setName(value)
  }
  const handleSlugChange = (value: string) => {
    setSlug(value.toLowerCase())

  useEffect(() => {
    if (!manualSlugEdit && name) {
      setSlug(generateSlug(name))
    c
  }, [name, manualSlugEdit])

  useEffect(() => {
    if (open) {
      resetForm()
     
  }, [open])

  const handleNameChange = (value: string) => {
    setName(value)
    setError('')
   

    }


    <Dialog open
   

          </DialogDescripti

          <div 
            <Input
              va
              placeholder=
   

            <Label htmlFor="slug">Sl
              id="slug"
              onChange={(e) => hand

            <p classNam
            </p>

     


            <Info className="h-4 w-4" 
            
     

          <Button 
            onClick={() => onOpenChange(false)}
          >
     

          >
          </Butt
    
  )














  const isValid = name.trim() && slug.trim() && validateSlug(slug.trim())






          <DialogDescription>
            Crea un nuevo perfil de negocio para organizar tus productos y órdenes.
          </DialogDescription>








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


            <Info className="h-4 w-4" />

              El slug se usa para identificar de forma única este perfil en el sistema.
            </AlertDescription>
          </Alert>




            variant="outline" 
            onClick={() => onOpenChange(false)}
            disabled={isSubmitting}
          >
            Cancelar
          </Button>
          <Button 
            onClick={handleSubmit}

          >
            {isSubmitting ? 'Creando...' : 'Crear Perfil'}
          </Button>

      </DialogContent>

  )

