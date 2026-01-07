import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Gear, Lightbulb } from '@phosphor-icons/react'
import type { Profile } from '@/lib/types'

interface ProfileConfigPromptProps {
  profile: Profile
  onConfigure: (profile: Profile) => void
}

export function ProfileConfigPrompt({ profile, onConfigure }: ProfileConfigPromptProps) {
  const hasSettings = profile.settings && Object.keys(profile.settings).length > 0

  if (hasSettings) {
    return null
  }

  return (
    <Card className="p-6 bg-gradient-to-br from-primary/5 to-accent/5 border-primary/20">
      <div className="flex flex-col md:flex-row items-start md:items-center gap-4">
        <div className="p-3 bg-primary/10 rounded-lg">
          <Lightbulb size={32} className="text-primary" weight="duotone" />
        </div>
        <div className="flex-1">
          <h3 className="font-semibold text-lg mb-1">
            💡 Configura tu Perfil de Negocio
          </h3>
          <p className="text-sm text-muted-foreground">
            Personaliza la moneda, impuestos, alertas de stock y más para <strong>{profile.name}</strong>
          </p>
          <ul className="mt-3 space-y-1 text-xs text-muted-foreground">
            <li>✓ Establece tu moneda y formato de precios</li>
            <li>✓ Configura cálculo automático de impuestos</li>
            <li>✓ Define umbrales de stock bajo</li>
            <li>✓ Añade información de contacto del negocio</li>
          </ul>
        </div>
        <Button 
          onClick={() => onConfigure(profile)}
          size="lg"
          className="shrink-0"
        >
          <Gear size={18} className="mr-2" />
          Configurar Ahora
        </Button>
      </div>
    </Card>
  )
}
