import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import type { Profile } from '@/lib/types'
import { ProfileSettingsSummary } from './ProfileSettingsSummary'
import { Storefront, Gear, PencilSimple } from '@phosphor-icons/react'

interface ProfileDetailsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  profile: Profile
  productCount: number
  orderCount: number
  onEdit: (profile: Profile) => void
  onSettings: (profile: Profile) => void
}

export function ProfileDetailsDialog({
  open,
  onOpenChange,
  profile,
  productCount,
  orderCount,
  onEdit,
  onSettings
}: ProfileDetailsDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div className="p-3 bg-primary/10 rounded-lg">
              <Storefront size={32} className="text-primary" weight="duotone" />
            </div>
            <div className="flex-1">
              <DialogTitle className="text-2xl">{profile.name}</DialogTitle>
              <DialogDescription className="font-mono">{profile.slug}</DialogDescription>
            </div>
            {profile.active ? (
              <Badge className="bg-accent text-accent-foreground">Activo</Badge>
            ) : (
              <Badge variant="secondary">Inactivo</Badge>
            )}
          </div>
        </DialogHeader>

        <div className="space-y-6 mt-6">
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 bg-primary/5 rounded-lg text-center">
              <p className="text-3xl font-bold text-primary">{productCount}</p>
              <p className="text-sm text-muted-foreground">Productos activos</p>
            </div>
            <div className="p-4 bg-accent/5 rounded-lg text-center">
              <p className="text-3xl font-bold text-accent">{orderCount}</p>
              <p className="text-sm text-muted-foreground">Órdenes totales</p>
            </div>
          </div>

          <ProfileSettingsSummary profile={profile} />

          <div className="flex gap-3 pt-4">
            <Button
              variant="outline"
              className="flex-1"
              onClick={() => {
                onEdit(profile)
                onOpenChange(false)
              }}
            >
              <PencilSimple size={18} className="mr-2" />
              Editar Perfil
            </Button>
            <Button
              className="flex-1"
              onClick={() => {
                onSettings(profile)
                onOpenChange(false)
              }}
            >
              <Gear size={18} className="mr-2" />
              Configuración
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
