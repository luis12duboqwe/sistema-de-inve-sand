import { useState, useEffect } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from './ui/dialog'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Label } from './ui/label'
import { Textarea } from './ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select'
import { Switch } from './ui/switch'
import { apiClient } from '../lib/apiClient'
import { AIProfileConfig } from '../lib/types'
import { toast } from 'sonner'
import { Spinner, Robot, Sparkle } from '@phosphor-icons/react'

interface AIProfileConfigDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  salesProfileId: number | null
  salesProfileName: string
}

export function AIProfileConfigDialog({ 
  open, 
  onOpenChange, 
  salesProfileId,
  salesProfileName
}: AIProfileConfigDialogProps) {
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  
  const [config, setConfig] = useState<Partial<AIProfileConfig>>({
    model_name: 'gpt-4o',
    temperature: 0.7,
    system_prompt: '',
    initial_greeting: '',
    voice_tone: 'formal',
    is_active: true
  })

  useEffect(() => {
    if (open && salesProfileId) {
      loadConfig(salesProfileId)
    }
  }, [open, salesProfileId])

  const loadConfig = async (id: number) => {
    setLoading(true)
    try {
      const data = await apiClient.getAIProfileConfig(id)
      if (data) {
        setConfig(data)
      } else {
        // Reset to defaults if no config exists
        setConfig({
          sales_profile_id: id,
          model_name: 'gpt-4o',
          temperature: 0.7,
          system_prompt: 'Eres un asistente de ventas útil y amable.',
          initial_greeting: '¡Hola! ¿En qué puedo ayudarte hoy?',
          voice_tone: 'formal',
          is_active: true
        })
      }
    } catch (error) {
      console.error('Error loading AI config:', error)
      toast.error('Error al cargar la configuración de IA')
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    if (!salesProfileId) return

    setSaving(true)
    try {
      await apiClient.updateAIProfileConfig(salesProfileId, {
        ...config,
        sales_profile_id: salesProfileId
      })
      toast.success('Configuración de IA guardada exitosamente')
      onOpenChange(false)
    } catch (error) {
      console.error('Error saving AI config:', error)
      toast.error('Error al guardar la configuración')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Robot className="h-5 w-5 text-purple-600" />
            Configuración de IA - {salesProfileName}
          </DialogTitle>
        </DialogHeader>

        {loading ? (
          <div className="flex justify-center py-8">
            <Spinner className="h-8 w-8 animate-spin text-gray-400" />
          </div>
        ) : (
          <div className="space-y-6 py-4">
            <div className="flex items-center justify-between bg-purple-50 p-4 rounded-lg border border-purple-100">
              <div className="space-y-0.5">
                <Label className="text-base font-medium text-purple-900">Activar Inteligencia Artificial</Label>
                <p className="text-sm text-purple-700">
                  Permite que este perfil responda automáticamente usando n8n + OpenAI
                </p>
              </div>
              <Switch
                checked={config.is_active}
                onCheckedChange={(checked) => setConfig(prev => ({ ...prev, is_active: checked }))}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Modelo de IA</Label>
                <Select 
                  value={config.model_name} 
                  onValueChange={(val) => setConfig(prev => ({ ...prev, model_name: val }))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Seleccionar modelo" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="gpt-4o">GPT-4o (Recomendado)</SelectItem>
                    <SelectItem value="gpt-4-turbo">GPT-4 Turbo</SelectItem>
                    <SelectItem value="gpt-3.5-turbo">GPT-3.5 Turbo (Económico)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Tono de Voz</Label>
                <Select 
                  value={config.voice_tone} 
                  onValueChange={(val) => setConfig(prev => ({ ...prev, voice_tone: val }))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Seleccionar tono" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="formal">Formal y Profesional</SelectItem>
                    <SelectItem value="amigable">Amigable y Cercano</SelectItem>
                    <SelectItem value="entusiasta">Entusiasta y Vendedor</SelectItem>
                    <SelectItem value="tecnico">Técnico y Preciso</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label className="flex items-center gap-2">
                <Sparkle className="h-4 w-4 text-yellow-500" />
                System Prompt (Personalidad)
              </Label>
              <p className="text-xs text-gray-500">
                Instrucciones base que definen cómo se comporta el bot. Sé específico sobre qué puede y no puede hacer.
              </p>
              <Textarea
                value={config.system_prompt}
                onChange={(e) => setConfig(prev => ({ ...prev, system_prompt: e.target.value }))}
                className="min-h-[150px] font-mono text-sm"
                placeholder="Eres un asistente experto en celulares..."
              />
            </div>

            <div className="space-y-2">
              <Label>Saludo Inicial</Label>
              <Input
                value={config.initial_greeting}
                onChange={(e) => setConfig(prev => ({ ...prev, initial_greeting: e.target.value }))}
                placeholder="¡Hola! Bienvenido a nuestra tienda..."
              />
            </div>

            <div className="space-y-2">
              <Label>Temperatura (Creatividad: {config.temperature})</Label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={config.temperature}
                onChange={(e) => setConfig(prev => ({ ...prev, temperature: parseFloat(e.target.value) }))}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-500">
                <span>Preciso (0.0)</span>
                <span>Creativo (1.0)</span>
              </div>
            </div>
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <Button onClick={handleSave} disabled={saving || loading} className="bg-purple-600 hover:bg-purple-700">
            {saving ? (
              <>
                <Spinner className="mr-2 h-4 w-4 animate-spin" />
                Guardando...
              </>
            ) : (
              'Guardar Configuración'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
