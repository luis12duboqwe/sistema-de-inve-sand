import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Storefront } from '@phosphor-icons/react'
import type { Profile } from '@/lib/types'

interface ProfileCardProps {
  profile: Profile
  productCount?: number
  orderCount?: number
}

export function ProfileCard({ profile, productCount = 0, orderCount = 0 }: ProfileCardProps) {
  return (
    <Card className="p-6 hover:shadow-lg transition-shadow">
      <div className="flex flex-col gap-4">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-3 flex-1">
            <div className="p-3 bg-primary/10 rounded-lg">
              <Storefront size={32} className="text-primary" weight="duotone" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-lg text-card-foreground">
                {profile.name}
              </h3>
              <p className="text-sm text-muted-foreground font-mono">
                {profile.slug}
              </p>
            </div>
          </div>
          {profile.active && (
            <Badge className="bg-accent text-accent-foreground">
              Activo
            </Badge>
          )}
        </div>

        <div className="grid grid-cols-2 gap-4 pt-4 border-t">
          <div className="text-center">
            <p className="text-2xl font-bold text-primary">{productCount}</p>
            <p className="text-xs text-muted-foreground">Productos</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-accent">{orderCount}</p>
            <p className="text-xs text-muted-foreground">Órdenes</p>
          </div>
        </div>
      </div>
    </Card>
  )
}
