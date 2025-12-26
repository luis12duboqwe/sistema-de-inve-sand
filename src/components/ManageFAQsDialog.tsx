import { useState, useEffect, useCallback } from 'react'
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
import { Textarea } from '@/components/ui/textarea'
import { toast } from 'sonner'
import type { FAQEntry } from '@/lib/types'
import { Plus, Pencil, Trash2, Search } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { inventoryServiceInstance } from '@/lib/inventoryServiceFactory'
import { Switch } from '@/components/ui/switch'

interface ManageFAQsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function ManageFAQsDialog({
  open,
  onOpenChange
}: ManageFAQsDialogProps) {
  const [faqs, setFaqs] = useState<FAQEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [editingFAQ, setEditingFAQ] = useState<FAQEntry | null>(null)
  
  // Form state
  const [pregunta, setPregunta] = useState('')
  const [respuesta, setRespuesta] = useState('')
  const [categoria, setCategoria] = useState('')
  const [activa, setActiva] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Filter state
  const [searchTerm, setSearchTerm] = useState('')

  const loadFAQs = useCallback(async () => {
    setLoading(true)
    try {
      // Load all active and inactive FAQs
      const response = await inventoryServiceInstance.listFAQs({ per_page: 100, activa: undefined })
      setFaqs(response.items)
    } catch (error) {
      console.error('Error loading FAQs:', error)
      toast.error('Error al cargar FAQs')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (open) {
      loadFAQs()
    }
  }, [open, loadFAQs])

  const resetForm = () => {
    setPregunta('')
    setRespuesta('')
    setCategoria('')
    setActiva(true)
    setEditingFAQ(null)
    setShowForm(false)
  }

  const handleEdit = (faq: FAQEntry) => {
    setEditingFAQ(faq)
    setPregunta(faq.pregunta_clave)
    setRespuesta(faq.respuesta)
    setCategoria(faq.categoria || '')
    setActiva(faq.activa)
    setShowForm(true)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!pregunta.trim() || !respuesta.trim()) {
      toast.error('Pregunta y respuesta son requeridas')
      return
    }

    setIsSubmitting(true)

    try {
      const faqData = {
        pregunta_clave: pregunta.trim(),
        respuesta: respuesta.trim(),
        categoria: categoria.trim() || undefined,
        activa
      }

      if (editingFAQ) {
        await inventoryServiceInstance.updateFAQ(editingFAQ.id, faqData)
        toast.success('FAQ actualizada exitosamente')
      } else {
        await inventoryServiceInstance.createFAQ(faqData)
        toast.success('FAQ creada exitosamente')
      }

      resetForm()
      loadFAQs()
    } catch (error) {
      console.error('Error saving FAQ:', error)
      toast.error('Error al guardar FAQ')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('¿Estás seguro de eliminar esta FAQ?')) return

    try {
      await inventoryServiceInstance.deleteFAQ(id)
      toast.success('FAQ eliminada exitosamente')
      loadFAQs()
    } catch (error) {
      console.error('Error deleting FAQ:', error)
      toast.error('Error al eliminar FAQ')
    }
  }

  const filteredFAQs = faqs.filter(faq => 
    faq.pregunta_clave.toLowerCase().includes(searchTerm.toLowerCase()) ||
    faq.respuesta.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (faq.categoria && faq.categoria.toLowerCase().includes(searchTerm.toLowerCase()))
  )

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Gestión de Preguntas Frecuentes (FAQs)</DialogTitle>
          <DialogDescription>
            Administra las respuestas automáticas del bot de IA.
          </DialogDescription>
        </DialogHeader>

        {showForm ? (
          <form onSubmit={handleSubmit} className="space-y-4 py-4">
            <div className="grid gap-4">
              <div className="grid gap-2">
                <Label htmlFor="pregunta">Pregunta Clave</Label>
                <Input
                  id="pregunta"
                  value={pregunta}
                  onChange={(e) => setPregunta(e.target.value)}
                  placeholder="Ej: ¿Cuál es el horario de atención?"
                  required
                />
              </div>
              
              <div className="grid gap-2">
                <Label htmlFor="respuesta">Respuesta del Bot</Label>
                <Textarea
                  id="respuesta"
                  value={respuesta}
                  onChange={(e) => setRespuesta(e.target.value)}
                  placeholder="Ej: Nuestro horario es de Lunes a Viernes de 9am a 6pm."
                  rows={4}
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="grid gap-2">
                  <Label htmlFor="categoria">Categoría (Opcional)</Label>
                  <Input
                    id="categoria"
                    value={categoria}
                    onChange={(e) => setCategoria(e.target.value)}
                    placeholder="Ej: Horarios, Envíos, Garantía"
                  />
                </div>
                
                <div className="flex items-center space-x-2 pt-8">
                  <Switch
                    id="activa"
                    checked={activa}
                    onCheckedChange={setActiva}
                  />
                  <Label htmlFor="activa">Activa</Label>
                </div>
              </div>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={resetForm}>
                Cancelar
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Guardando...' : (editingFAQ ? 'Actualizar' : 'Crear')}
              </Button>
            </DialogFooter>
          </form>
        ) : (
          <div className="space-y-4">
            <div className="flex justify-between items-center gap-4">
              <div className="relative flex-1">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Buscar FAQs..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-8"
                />
              </div>
              <Button onClick={() => setShowForm(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Nueva FAQ
              </Button>
            </div>

            <div className="space-y-2 max-h-[60vh] overflow-y-auto pr-2">
              {loading ? (
                <div className="text-center py-8 text-muted-foreground">Cargando FAQs...</div>
              ) : filteredFAQs.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">No se encontraron FAQs</div>
              ) : (
                filteredFAQs.map((faq) => (
                  <Card key={faq.id} className="p-4 hover:bg-accent/50 transition-colors">
                    <div className="flex justify-between items-start gap-4">
                      <div className="space-y-1 flex-1">
                        <div className="flex items-center gap-2">
                          <h4 className="font-semibold">{faq.pregunta_clave}</h4>
                          {!faq.activa && (
                            <Badge variant="secondary" className="text-xs">Inactiva</Badge>
                          )}
                          {faq.categoria && (
                            <Badge variant="outline" className="text-xs">{faq.categoria}</Badge>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground whitespace-pre-wrap">{faq.respuesta}</p>
                        <div className="text-xs text-muted-foreground mt-2">
                          Usada {faq.veces_usada} veces
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleEdit(faq)}
                          title="Editar"
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDelete(faq.id)}
                          className="text-destructive hover:text-destructive"
                          title="Eliminar"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </Card>
                ))
              )}
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
