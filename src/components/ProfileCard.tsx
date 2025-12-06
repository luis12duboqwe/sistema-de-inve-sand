import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Storefront, PencilSimple, Gear, Package, ShoppingCart } from '@phosphor-icons/react'
import type { Profile } from '@/lib/types'

interface ProfileCardProps {
  profile: Profile
  productCount?: number
  orderCount?: number
  onEdit?: (profile: Profile) => void
  onSettings?: (profile: Profile) => void
  onClick?: (profile: Profile) => void
}

export function ProfileCard({ profile, productCount = 0, orderCount = 0, onEdit, onSettings, onClick }: ProfileCardProps) {
  // Validación de seguridad
  if (!profile || !profile.id) {
    console.error('Invalid profile passed to ProfileCard:', profile)
    return null
  }

  const hasSettings = profile.settings && typeof profile.settings === 'object' && Object.keys(profile.settings).length > 0
  const profileName = profile.name || 'Sin nombre'
  const profileSlug = profile.slug || 'sin-slug'

  return (
    <Card 
      className="p-6 hover:shadow-lg transition-all duration-200 cursor-pointer border-2 hover:border-primary/20"
      onClick={() => onClick?.(profile)}
    >
      <div className="flex flex-col gap-4">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-3 flex-1 min-w-0">
            <div className="p-3 bg-primary/10 rounded-lg shrink-0">
              <Storefront size={32} className="text-primary" weight="duotone" />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="font-semibold text-lg text-card-foreground truncate">
                {profileName}
              </h3>
              <p className="text-sm text-muted-foreground font-mono truncate">
                {profileSlug}
              </p>
            </div>
          </div>
          <div className="flex flex-col items-end gap-1 shrink-0">
            {profile.active ? (
              <Badge className="bg-accent text-accent-foreground">
                Activo
              </Badge>
            ) : (
              <Badge variant="secondary" className="bg-muted text-muted-foreground">
                Inactivo
              </Badge>
            )}
            {hasSettings && (
              <Badge variant="outline" className="text-xs">
                Configurado
              </Badge>
            )}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 pt-4 border-t">
          <div className="flex flex-col items-center gap-1 p-3 bg-primary/5 rounded-lg">
            <div className="flex items-center gap-2">
              <Package size={18} className="text-primary" />
              <p className="text-2xl font-bold text-primary">{productCount}</p>
            </div>
            <p className="text-xs text-muted-foreground">Productos Activos</p>
          </div>
          <div className="flex flex-col items-center gap-1 p-3 bg-accent/5 rounded-lg">
            <div className="flex items-center gap-2">
              <ShoppingCart size={18} className="text-accent" />
              <p className="text-2xl font-bold text-accent">{orderCount}</p>
            </div>
            <p className="text-xs text-muted-foreground">Órdenes Totales</p>
          </div>
        </div>

        {profile.settings && (
          <div className="text-xs text-muted-foreground space-y-1 pt-2 border-t">
            <div className="flex justify-between">
              <span>Moneda:</span>
              <span className="font-medium text-foreground">{profile.settings.currency || 'HNL'}</span>
            </div>
            {profile.settings.lowStockThreshold && (
              <div className="flex justify-between">
                <span>Umbral Stock Bajo:</span>
                <span className="font-medium text-foreground">{profile.settings.lowStockThreshold}</span>
              </div>
            )}
          </div>
        )}

        <div className="flex gap-2 pt-2">
          {onSettings && (
            <Button
              variant="outline"
              size="sm"
              onClick={(e) => {
                e.stopPropagation()
                onSettings(profile)
              }}
              className="flex-1"
            >
              <Gear size={16} className="mr-2" />
              Config
            </Button>
          )}
          {onEdit && (
            <Button
              variant="outline"
              size="sm"
              onClick={(e) => {
                e.stopPropagation()
                onEdit(profile)
              }}
              className="flex-1"
            >
              <PencilSimple size={16} className="mr-2" />
              Editar
            </Button>
          )}
        </div>
      </div>
    </Card>
  )
}
