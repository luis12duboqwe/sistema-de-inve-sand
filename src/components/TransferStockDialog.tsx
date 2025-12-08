import { useState, useEffect } from 'react'
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { toast } from 'sonner'
import type { ProductWithStock, Profile, CreateStockTransferRequest } from '@/lib/types'
import { ArrowRightLeft, AlertCircle } from 'lucide-react'

interface TransferStockDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  product: ProductWithStock | null
  currentProfile: Profile
  profiles: Profile[]
  onTransferComplete: () => void
}

export function TransferStockDialog({
  open,
  onOpenChange,
  product,
  currentProfile,
  profiles,
  onTransferComplete
}: TransferStockDialogProps) {
  const [toProfileSlug, setToProfileSlug] = useState('')
  const [cantidad, setCantidad] = useState('')
  const [notas, setNotas] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Filtrar perfiles para no incluir el actual
  const availableProfiles = profiles.filter(p => p.id !== currentProfile.id && p.active)

  useEffect(() => {
    if (open && product) {
      // Reset form when dialog opens
      setToProfileSlug(availableProfiles.length > 0 ? availableProfiles[0].slug : '')
      setCantidad('')
      setNotas('')
    }
  }, [open, product, availableProfiles])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!product) {
      toast.error('No hay producto seleccionado')
      return
    }

    if (!toProfileSlug) {
      toast.error('Selecciona un perfil de destino')
      return
    }

    const cantidadNum = parseInt(cantidad)
    if (isNaN(cantidadNum) || cantidadNum <= 0) {
      toast.error('La cantidad debe ser mayor a 0')
      return
    }

    if (cantidadNum > product.stock_disponible) {
      toast.error(`Stock insuficiente. Disponible: ${product.stock_disponible}`)
      return
    }

    setIsSubmitting(true)

    try {
      const transferData: CreateStockTransferRequest = {
        product_id: product.id,
        from_profile_slug: currentProfile.slug,
        to_profile_slug: toProfileSlug,
        cantidad: cantidadNum,
        notas: notas.trim() || undefined,
        created_by: 'Sistema' // Puedes cambiar esto si tienes autenticación de usuario
      }

      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/stock-transfers`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(transferData)
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Error al transferir stock')
      }

      const destProfile = profiles.find(p => p.slug === toProfileSlug)
      toast.success(
        `Transferencia creada exitosamente. Esperando confirmación de "${destProfile?.name || toProfileSlug}".`,
        { duration: 5000 }
      )

      onTransferComplete()
      onOpenChange(false)
    } catch (error) {
      console.error('Error al transferir stock:', error)
      toast.error(error instanceof Error ? error.message : 'Error al transferir stock')
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!product) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ArrowRightLeft className="h-5 w-5" />
            Transferir Stock
          </DialogTitle>
          <DialogDescription>
            Transfiere stock de este producto a otro perfil
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit}>
          <div className="space-y-4 py-4">
            {/* Información del producto */}
            <div className="rounded-lg border p-3 bg-muted/50">
              <div className="font-medium text-sm">{product.nombre}</div>
              <div className="text-xs text-muted-foreground mt-1">
                SKU: {product.sku} • Stock actual: {product.stock_disponible} unidades
              </div>
            </div>

            {/* Perfil de origen */}
            <div className="grid gap-2">
              <Label>Desde (Perfil Actual)</Label>
              <Input value={currentProfile.name} disabled />
            </div>

            {/* Perfil de destino */}
            <div className="grid gap-2">
              <Label htmlFor="to_profile">Hacia (Perfil Destino) *</Label>
              {availableProfiles.length === 0 ? (
                <div className="flex items-center gap-2 p-3 rounded-lg border border-yellow-200 bg-yellow-50 text-yellow-800">
                  <AlertCircle className="h-4 w-4" />
                  <span className="text-sm">
                    No hay otros perfiles activos disponibles para transferencia
                  </span>
                </div>
              ) : (
                <Select value={toProfileSlug} onValueChange={setToProfileSlug}>
                  <SelectTrigger id="to_profile">
                    <SelectValue placeholder="Selecciona un perfil" />
                  </SelectTrigger>
                  <SelectContent>
                    {availableProfiles.map(profile => (
                      <SelectItem key={profile.id} value={profile.slug}>
                        {profile.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </div>

            {/* Cantidad */}
            <div className="grid gap-2">
              <Label htmlFor="cantidad">Cantidad a Transferir *</Label>
              <Input
                id="cantidad"
                type="number"
                min="1"
                max={product.stock_disponible}
                value={cantidad}
                onChange={e => setCantidad(e.target.value)}
                placeholder="0"
                required
                disabled={availableProfiles.length === 0}
              />
              <p className="text-xs text-muted-foreground">
                Máximo: {product.stock_disponible} unidades
              </p>
            </div>

            {/* Notas */}
            <div className="grid gap-2">
              <Label htmlFor="notas">Notas (Opcional)</Label>
              <Textarea
                id="notas"
                value={notas}
                onChange={e => setNotas(e.target.value)}
                placeholder="Razón de la transferencia, observaciones, etc."
                rows={3}
                disabled={availableProfiles.length === 0}
              />
            </div>

            {/* Advertencia */}
            <div className="flex items-start gap-2 p-3 rounded-lg border border-blue-200 bg-blue-50 text-blue-800">
              <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
              <div className="text-xs">
                <strong>Importante:</strong> La transferencia quedará en estado <strong>pendiente</strong> hasta 
                que el perfil destino la confirme. El stock se descontará de tu inventario al momento de la confirmación.
                Mientras esté pendiente, el stock permanece en tu perfil.
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isSubmitting}
            >
              Cancelar
            </Button>
            <Button
              type="submit"
              disabled={isSubmitting || availableProfiles.length === 0}
            >
              {isSubmitting ? 'Transfiriendo...' : 'Transferir Stock'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
