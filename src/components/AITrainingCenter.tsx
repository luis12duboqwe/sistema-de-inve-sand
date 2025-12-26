import { useState, useEffect } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog'
import { Button } from './ui/button'
import { Textarea } from './ui/textarea'
import { Badge } from './ui/badge'
import { apiClient } from '../lib/apiClient'
import { TrainingQueueItem } from '../lib/types'
import { toast } from 'sonner'
import { Spinner, CheckCircle, XCircle, BookOpen, Robot, ListDashes } from '@phosphor-icons/react'
import { ManageFAQsDialog } from './ManageFAQsDialog'

interface AITrainingCenterProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function AITrainingCenter({ open, onOpenChange }: AITrainingCenterProps) {
  const [items, setItems] = useState<TrainingQueueItem[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedItem, setSelectedItem] = useState<TrainingQueueItem | null>(null)
  const [correction, setCorrection] = useState('')
  const [processing, setProcessing] = useState(false)
  const [showFAQs, setShowFAQs] = useState(false)

  useEffect(() => {
    if (open) {
      loadItems()
    }
  }, [open])

  const loadItems = async () => {
    setLoading(true)
    try {
      const data = await apiClient.getTrainingQueue('pending')
      setItems(data)
    } catch {
      toast.error('Error al cargar cola de entrenamiento')
    } finally {
      setLoading(false)
    }
  }

  const handleResolve = async (action: 'approve' | 'reject' | 'convert_to_faq') => {
    if (!selectedItem) return
    if (action === 'convert_to_faq' && !correction.trim()) {
      toast.error('Debes escribir una respuesta correcta para crear la FAQ')
      return
    }

    setProcessing(true)
    try {
      await apiClient.resolveTrainingItem(selectedItem.id, action, correction)
      toast.success(
        action === 'convert_to_faq' 
          ? 'FAQ creada y aprendizaje registrado' 
          : 'Item procesado correctamente'
      )
      setSelectedItem(null)
      setCorrection('')
      loadItems()
    } catch {
      toast.error('Error al procesar item')
    } finally {
      setProcessing(false)
    }
  }

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-4xl h-[80vh] flex flex-col">
          <DialogHeader>
            <div className="flex justify-between items-center">
              <DialogTitle className="flex items-center gap-2">
                <BookOpen className="h-5 w-5 text-blue-600" />
                Centro de Entrenamiento IA
              </DialogTitle>
              <Button variant="outline" size="sm" onClick={() => setShowFAQs(true)}>
                <ListDashes className="mr-2 h-4 w-4" />
                Gestionar FAQs
              </Button>
            </div>
            <DialogDescription>
              Revisa las preguntas que la IA no supo responder y enséñale la respuesta correcta.
            </DialogDescription>
          </DialogHeader>

          <div className="flex flex-1 gap-4 overflow-hidden mt-4">
          {/* Lista de Items */}
          <div className="w-1/3 border-r pr-4 overflow-y-auto space-y-2">
            {loading ? (
              <div className="flex justify-center py-8">
                <Spinner className="h-6 w-6 animate-spin text-gray-400" />
              </div>
            ) : items.length === 0 ? (
              <div className="text-center py-8 text-gray-500 text-sm">
                ¡Todo al día! No hay preguntas pendientes.
              </div>
            ) : (
              items.map((item) => (
                <div
                  key={item.id}
                  onClick={() => setSelectedItem(item)}
                  className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                    selectedItem?.id === item.id
                      ? 'bg-blue-50 border-blue-200'
                      : 'hover:bg-gray-50 border-gray-200'
                  }`}
                >
                  <div className="flex justify-between items-start mb-1">
                    <Badge variant="outline" className="text-xs">
                      {item.sales_profile?.name || 'Bot'}
                    </Badge>
                    <span className="text-xs text-gray-400">
                      {new Date(item.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <p className="text-sm font-medium line-clamp-2">{item.customer_question}</p>
                </div>
              ))
            )}
          </div>

          {/* Detalle y Acción */}
          <div className="flex-1 pl-4 flex flex-col overflow-y-auto">
            {selectedItem ? (
              <div className="space-y-6">
                <div className="bg-gray-50 p-4 rounded-lg">
                  <h4 className="text-sm font-semibold text-gray-500 mb-1">Pregunta del Cliente</h4>
                  <p className="text-lg">{selectedItem.customer_question}</p>
                </div>

                {selectedItem.ai_proposed_answer && (
                  <div className="bg-yellow-50 p-4 rounded-lg border border-yellow-100">
                    <h4 className="text-sm font-semibold text-yellow-700 mb-1 flex items-center gap-2">
                      <Robot className="h-4 w-4" />
                      Intento de la IA
                    </h4>
                    <p className="text-gray-700">{selectedItem.ai_proposed_answer}</p>
                  </div>
                )}

                <div className="space-y-2">
                  <h4 className="text-sm font-semibold">Tu Respuesta Correcta (Enseñanza)</h4>
                  <Textarea
                    value={correction}
                    onChange={(e) => setCorrection(e.target.value)}
                    placeholder="Escribe aquí la respuesta ideal. Esto se convertirá en una FAQ."
                    className="min-h-[150px]"
                  />
                </div>

                <div className="flex gap-3 justify-end pt-4 border-t">
                  <Button
                    variant="outline"
                    onClick={() => handleResolve('reject')}
                    disabled={processing}
                    className="text-red-600 hover:text-red-700 hover:bg-red-50"
                  >
                    <XCircle className="mr-2 h-4 w-4" />
                    Ignorar
                  </Button>
                  <Button
                    onClick={() => handleResolve('convert_to_faq')}
                    disabled={processing || !correction.trim()}
                    className="bg-green-600 hover:bg-green-700"
                  >
                    {processing ? (
                      <Spinner className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <CheckCircle className="mr-2 h-4 w-4" />
                    )}
                    Guardar y Crear FAQ
                  </Button>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-gray-400">
                <BookOpen className="h-12 w-12 mb-2 opacity-20" />
                <p>Selecciona una pregunta para revisarla</p>
              </div>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>

    <ManageFAQsDialog 
      open={showFAQs} 
      onOpenChange={setShowFAQs} 
    />
    </>
  )
}
