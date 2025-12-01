import { Card } from '@/components/ui/card'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Info, Lightbulb, CheckCircle } from '@phosphor-icons/react'

export function ProfileSetupGuide() {
  return (
    <div className="space-y-4 max-w-3xl mx-auto">
      <Alert>
        <Info size={20} className="mt-0.5" />
        <AlertTitle>Sistema de Múltiples Perfiles</AlertTitle>
        <AlertDescription>
          Gestiona diferentes negocios, tiendas o líneas de productos desde una sola interfaz. Cada perfil tiene su propio catálogo, órdenes y configuración.
        </AlertDescription>
      </Alert>

      <Card className="p-6">
        <h3 className="font-semibold text-lg mb-4 flex items-center gap-2">
          <Lightbulb size={24} className="text-accent" weight="duotone" />
          Cómo Empezar
        </h3>
        
        <div className="space-y-4">
          <div className="flex gap-3">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
              <span className="text-primary font-bold">1</span>
            </div>
            <div>
              <h4 className="font-medium text-card-foreground">Crear un Perfil</h4>
              <p className="text-sm text-muted-foreground mt-1">
                Haz clic en "Nuevo Perfil" y completa el nombre y slug. El slug es un identificador único que no se puede cambiar después.
              </p>
            </div>
          </div>

          <div className="flex gap-3">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
              <span className="text-primary font-bold">2</span>
            </div>
            <div>
              <h4 className="font-medium text-card-foreground">Configurar el Perfil</h4>
              <p className="text-sm text-muted-foreground mt-1">
                Personaliza moneda, impuestos, umbrales de stock y otra información del negocio en la sección de configuración.
              </p>
            </div>
          </div>

          <div className="flex gap-3">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
              <span className="text-primary font-bold">3</span>
            </div>
            <div>
              <h4 className="font-medium text-card-foreground">Agregar Productos</h4>
              <p className="text-sm text-muted-foreground mt-1">
                Ve a la pestaña de Productos y crea productos asignándolos al perfil correspondiente. Cada producto pertenece a un solo perfil.
              </p>
            </div>
          </div>

          <div className="flex gap-3">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
              <span className="text-primary font-bold">4</span>
            </div>
            <div>
              <h4 className="font-medium text-card-foreground">Crear Órdenes</h4>
              <p className="text-sm text-muted-foreground mt-1">
                Las órdenes se crean seleccionando primero el perfil. Solo productos de ese perfil estarán disponibles.
              </p>
            </div>
          </div>
        </div>
      </Card>

      <Card className="p-6 bg-accent/5 border-accent/20">
        <h3 className="font-semibold text-lg mb-3 flex items-center gap-2">
          <CheckCircle size={24} className="text-accent" weight="duotone" />
          Casos de Uso Comunes
        </h3>
        
        <ul className="space-y-2 text-sm text-muted-foreground">
          <li className="flex items-start gap-2">
            <CheckCircle size={16} className="text-accent mt-0.5 flex-shrink-0" />
            <span><strong>Múltiples Tiendas:</strong> Un perfil por cada ubicación física</span>
          </li>
          <li className="flex items-start gap-2">
            <CheckCircle size={16} className="text-accent mt-0.5 flex-shrink-0" />
            <span><strong>Diferentes Líneas:</strong> Separar productos nuevos de reacondicionados</span>
          </li>
          <li className="flex items-start gap-2">
            <CheckCircle size={16} className="text-accent mt-0.5 flex-shrink-0" />
            <span><strong>Canales de Venta:</strong> Un perfil para retail y otro para mayoreo</span>
          </li>
          <li className="flex items-start gap-2">
            <CheckCircle size={16} className="text-accent mt-0.5 flex-shrink-0" />
            <span><strong>Múltiples Marcas:</strong> Gestionar diferentes marcas o franquicias</span>
          </li>
        </ul>
      </Card>
    </div>
  )
}
