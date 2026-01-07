import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import type { Profile } from '@/lib/types'
import { CheckCircle, XCircle, Gear } from '@phosphor-icons/react'

interface ProfilesConfigSummaryProps {
  profiles: Profile[]
}

export function ProfilesConfigSummary({ profiles }: ProfilesConfigSummaryProps) {
  const configuredProfiles = profiles.filter(p => p.settings && Object.keys(p.settings).length > 0)
  const unconfiguredProfiles = profiles.filter(p => !p.settings || Object.keys(p.settings).length === 0)

  if (profiles.length === 0) {
    return null
  }

  return (
    <Card className="p-6 bg-gradient-to-r from-primary/5 to-accent/5">
      <div className="flex items-center gap-3 mb-4">
        <Gear size={24} className="text-primary" weight="duotone" />
        <h3 className="font-semibold text-lg">Estado de Configuración</h3>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="text-center p-4 bg-background rounded-lg">
          <p className="text-3xl font-bold text-primary mb-1">{profiles.length}</p>
          <p className="text-xs text-muted-foreground">Perfiles Totales</p>
        </div>
        
        <div className="text-center p-4 bg-background rounded-lg">
          <div className="flex items-center justify-center gap-2 mb-1">
            <CheckCircle size={24} className="text-accent" weight="fill" />
            <p className="text-3xl font-bold text-accent">{configuredProfiles.length}</p>
          </div>
          <p className="text-xs text-muted-foreground">Configurados</p>
        </div>
        
        <div className="text-center p-4 bg-background rounded-lg">
          <div className="flex items-center justify-center gap-2 mb-1">
            <XCircle size={24} className="text-muted-foreground" />
            <p className="text-3xl font-bold text-muted-foreground">{unconfiguredProfiles.length}</p>
          </div>
          <p className="text-xs text-muted-foreground">Sin Configurar</p>
        </div>
      </div>

      {configuredProfiles.length > 0 && (
        <div className="mt-4 pt-4 border-t">
          <p className="text-xs font-medium text-muted-foreground mb-2">Perfiles configurados:</p>
          <div className="flex flex-wrap gap-2">
            {configuredProfiles.map(profile => (
              <Badge key={profile.id} variant="outline" className="gap-1">
                <CheckCircle size={12} className="text-accent" weight="fill" />
                {profile.name}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {unconfiguredProfiles.length > 0 && (
        <div className="mt-3">
          <p className="text-xs font-medium text-muted-foreground mb-2">Pendientes de configurar:</p>
          <div className="flex flex-wrap gap-2">
            {unconfiguredProfiles.map(profile => (
              <Badge key={profile.id} variant="secondary" className="gap-1">
                <XCircle size={12} className="text-muted-foreground" />
                {profile.name}
              </Badge>
            ))}
          </div>
        </div>
      )}
    </Card>
  )
}
