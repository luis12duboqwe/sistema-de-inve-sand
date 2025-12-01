import { useState, useEffect } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Alert, AlertDescription } from '@/co
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'

interface NewProfileDialogProps {

  onOpenChange: (open: boolean) => void

}

    .replace(/[^a-z0-9\s-]/g, '')
    .replace(/\s+/g, '-')
}

  onOpenChange,
}: NewProfile
    .toLowerCase()
  const [isSubmitting
    .replace(/[\u0300-\u036f]/g, '')
      setName('')
      setEr
    }

 

      setSlug('')
  open,

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

  }, [open])

  const handleNameChange = (value: string) => {
    setName(value)
    if (value.trim()) {
      setSlug(generateSlug(value))
    } else {
      setSlug('')
    }
    setError('')
   

  const handleSlugChange = (value: string) => {
    setSlug(value.toLowerCase())
    setError('')
  }

  const isValid = name.trim() && slug.trim() && validateSlug(slug.trim())

          </div>
    if (!name.trim()) {
              <AlertDescription>{error}<
      return
    }

          </Alert>

      return
     

          </Button>
            onClick={handleSubmit}
          >
     

  )
    try {

      setName('')
      setSlug('')
      setError('')




    }















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



              Los perfiles te permiten gestionar múltiples negocios o líneas de productos de forma independiente.
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

