import { useState, useEffect } from 'react'
import { Plus, X, Camera, PaperPlaneTilt } from '@phosphor-icons/react'
import { toast } from 'sonner'
import { Button } from './ui/button'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from './ui/dialog'
import { Input } from './ui/input'
import { Label } from './ui/label'
import { Badge } from './ui/badge'
import { apiClient } from '@/lib/apiClient'
import type { PhotoRequest } from '@/lib/types'

export function PhotoRequestsDashboard() {
  const [pendingRequests, setPendingRequests] = useState<PhotoRequest[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedRequest, setSelectedRequest] = useState<PhotoRequest | null>(null)
  const [mediaUrl, setMediaUrl] = useState('')
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [uploading, setUploading] = useState(false)

  useEffect(() => {
    void loadPendingRequests()
    const intervalId = window.setInterval(() => {
      void loadPendingRequests(false)
    }, 15000)

    return () => window.clearInterval(intervalId)
  }, [])

  const loadPendingRequests = async (showSpinner = true) => {
    try {
      if (showSpinner) setLoading(true)
      const requests = await apiClient.getPhotoRequests({ assigned_to_me: true })
      setPendingRequests(requests)
    } catch (error) {
      toast.error('Error al cargar solicitudes de fotos')
      console.error(error)
    } finally {
      if (showSpinner) setLoading(false)
    }
  }

  const handleOpenRequest = async (request: PhotoRequest) => {
    try {
      setSelectedRequest(request)
      if (request.status === 'pending') {
        await apiClient.claimPhotoRequest(request.id)
      }
      const updatedRequest = await apiClient.getPhotoRequest(request.id)
      setSelectedRequest(updatedRequest)
      await loadPendingRequests(false)
    } catch (error) {
      console.error(error)
      toast.error('Error al reclamar la solicitud')
    }
  }

  const handleUploadMedia = async (requestId: number) => {
    if (!mediaUrl.trim() && selectedFiles.length === 0) {
      toast.error('Ingresa una URL o selecciona archivo(s)')
      return
    }

    try {
      setUploading(true)

      const uploadPromises: Promise<any>[] = []

      if (selectedFiles.length > 0) {
        for (const file of selectedFiles) {
          uploadPromises.push(apiClient.uploadPhotoFile(requestId, file))
        }
      }

      if (mediaUrl.trim()) {
        const urls = mediaUrl.split(',').map(u => u.trim()).filter(Boolean)
        for (const url of urls) {
          uploadPromises.push(apiClient.uploadPhotoMedia(requestId, {
            media_url: url,
            media_type: 'photo'
          }))
        }
      }

      await Promise.all(uploadPromises)

      toast.success('Foto(s) cargada(s) exitosamente')
      setMediaUrl('')
      setSelectedFiles([])

      if (selectedRequest?.id === requestId) {
        const updatedRequest = await apiClient.getPhotoRequest(requestId)
        setSelectedRequest(updatedRequest)
      }

      await loadPendingRequests()
    } catch (error) {
      toast.error('Error al cargar foto')
      console.error(error)
    } finally {
      setUploading(false)
    }
  }

  const handleSendToCustomer = async (requestId: number) => {
    try {
      setUploading(true)
      await apiClient.sendPhotosToCustomer(requestId)

      toast.success('Fotos enviadas al cliente')
      if (selectedRequest?.id === requestId) {
        setSelectedRequest(null)
      }
      await loadPendingRequests()
    } catch (error) {
      toast.error('Error al enviar fotos')
      console.error(error)
    } finally {
      setUploading(false)
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'pending':
        return <Badge variant="destructive">Pendiente</Badge>
      case 'claimed':
        return <Badge variant="secondary">Tomada</Badge>
      case 'awaiting_upload':
        return <Badge variant="outline">Esperando carga</Badge>
      case 'in_progress':
        return <Badge variant="secondary">En progreso</Badge>
      case 'completed':
        return <Badge variant="secondary">Completado</Badge>
      default:
        return <Badge>{status}</Badge>
    }
  }

  if (loading) {
    return <div className="p-4">Cargando solicitudes...</div>
  }

  if (pendingRequests.length === 0) {
    return (
      <div className="p-8 text-center">
        <Camera size={48} className="mx-auto text-gray-300 mb-2" />
        <p className="text-gray-500">No hay solicitudes de fotos pendientes</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold">📸 Solicitudes de Fotos Pendientes</h2>

      {pendingRequests.map((request) => {
        const activeRequest = selectedRequest?.id === request.id ? selectedRequest : request

        return (
          <Dialog key={request.id}>
            <DialogTrigger asChild>
              <div
                className="border rounded-lg p-4 cursor-pointer hover:bg-gray-50 transition"
                onClick={() => { void handleOpenRequest(request) }}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="font-semibold">{activeRequest.product_name}</div>
                    <div className="text-sm text-gray-600">
                      Cliente: {activeRequest.customer_name || activeRequest.customer_id}
                      {activeRequest.color_requested && ` • Color: ${activeRequest.color_requested}`}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      Canal: {activeRequest.origin_channel || 'no definido'}
                      {typeof activeRequest.priority_score === 'number' && ` • Prioridad ${activeRequest.priority_score}`}
                      {activeRequest.sla_breached && ' • SLA vencido'}
                      {activeRequest.csat_score !== undefined && ` • CSAT: ${activeRequest.csat_score}/5`}
                    </div>
                    <div className="text-xs text-gray-400 mt-1">
                      Solicitado hace:{' '}
                      {new Date(activeRequest.created_at).toLocaleDateString('es-ES', {
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {getStatusBadge(activeRequest.status)}
                  </div>
                </div>
              </div>
            </DialogTrigger>

            <DialogContent className="max-w-2xl">
              <DialogHeader>
                <DialogTitle>📸 {activeRequest.product_name}</DialogTitle>
                <DialogDescription>
                  Solicitud de {activeRequest.customer_name || activeRequest.customer_id}
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-4 max-h-[60vh] overflow-y-auto">
                <div className="grid grid-cols-2 gap-4 p-4 bg-gray-50 rounded">
                  <div>
                    <Label className="text-gray-600">Color solicitado</Label>
                    <p className="font-medium">{activeRequest.color_requested || 'No especificó'}</p>
                  </div>
                  <div>
                    <Label className="text-gray-600">Tamaño/Variante</Label>
                    <p className="font-medium">{activeRequest.size_requested || 'No especificó'}</p>
                  </div>
                  <div>
                    <Label className="text-gray-600">Cliente</Label>
                    <p className="font-medium">{activeRequest.customer_name || activeRequest.customer_id}</p>
                  </div>
                  <div>
                    <Label className="text-gray-600">Canal</Label>
                    <p className="font-medium">{activeRequest.origin_channel || 'No especificó'}</p>
                  </div>
                </div>

                {activeRequest.media_items && activeRequest.media_items.length > 0 && (
                  <div>
                    <Label>Fotos cargadas ({activeRequest.media_items.length})</Label>
                    <div className="grid grid-cols-2 gap-2 mt-2">
                      {activeRequest.media_items.map((media) => (
                        <div key={media.id} className="border rounded p-2">
                          <img
                            src={media.media_url}
                            alt="Photo"
                            className="w-full h-32 object-cover rounded mb-2"
                          />
                          <div className="text-xs text-gray-600">
                            {media.media_type}
                            {media.sent_to_customer_at && (
                              <div className="text-green-600 font-medium">✓ Enviado</div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {activeRequest.status !== 'completed' && (
                  <div className="space-y-2">
                    <Label>Cargar foto</Label>
                    <div className="flex gap-2">
                      <Input
                        placeholder="URLs de imagen separadas por coma"
                        value={mediaUrl}
                        onChange={(e) => setMediaUrl(e.target.value)}
                        disabled={uploading}
                      />
                      <Button
                        onClick={() => handleUploadMedia(activeRequest.id)}
                        disabled={uploading || (!mediaUrl.trim() && selectedFiles.length === 0)}
                        size="sm"
                      >
                        {uploading ? '⟳' : <Plus size={16} />}
                      </Button>
                    </div>
                    <Input
                      type="file"
                      accept="image/*,video/*"
                      multiple
                      disabled={uploading}
                      onChange={(e) => setSelectedFiles(Array.from(e.target.files || []))}
                    />
                    {selectedFiles.length > 0 && (
                      <div className="text-xs text-gray-500 mt-1">
                        Archivos seleccionados: {selectedFiles.length}
                        <ul className="list-disc pl-4 mt-1">
                          {selectedFiles.map((f, i) => (
                            <li key={i} className="truncate">{f.name}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}

                <div className="flex gap-2 pt-4 border-t">
                  {activeRequest.status !== 'completed' && activeRequest.media_items && activeRequest.media_items.length > 0 && (
                    <Button
                      onClick={() => handleSendToCustomer(activeRequest.id)}
                      className="flex-1"
                      variant="default"
                    >
                      <PaperPlaneTilt size={16} className="mr-2" />
                      Enviar fotos al cliente
                    </Button>
                  )}

                  <Button
                    onClick={() => {
                      void (async () => {
                        try {
                          setUploading(true)
                          await apiClient.updatePhotoRequest(activeRequest.id, {
                            status: 'declined',
                            completion_notes: 'Solicitud rechazada por agente'
                          })
                          toast.success('Solicitud rechazada')
                          await loadPendingRequests()
                        } catch (error) {
                          toast.error('Error al rechazar solicitud')
                          console.error(error)
                        } finally {
                          setUploading(false)
                        }
                      })()
                    }}
                    variant="outline"
                  >
                    <X size={16} className="mr-2" />
                    Rechazar
                  </Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>
        )
      })}
    </div>
  )
}
