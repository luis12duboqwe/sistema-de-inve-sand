import { useState } from 'react'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Upload, Download, CheckCircle, WarningCircle, FileArrowDown } from '@phosphor-icons/react'
import { parseProductsCSV, downloadCSVTemplate } from '@/lib/importUtils'
import type { Profile, ProductWithStock } from '@/lib/types'

interface ImportProductsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  profiles: Profile[]
  onImport: (products: Partial<ProductWithStock>[]) => Promise<void>
}

export function ImportProductsDialog({ open, onOpenChange, profiles, onImport }: ImportProductsDialogProps) {
  const [selectedProfileId, setSelectedProfileId] = useState<number | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [importing, setImporting] = useState(false)
  const [previewResult, setPreviewResult] = useState<{
    success: boolean
    message: string
    importedCount: number
    errors: { row: number; error: string }[]
    products: Partial<ProductWithStock>[]
  } | null>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    try {
      const selectedFile = e.target.files?.[0]
      if (selectedFile) {
        setFile(selectedFile)
        setPreviewResult(null)
      }
    } catch (error) {
      console.error('Error handling file change:', error)
    }
  }

  const handlePreview = async () => {
    try {
      if (!file || !selectedProfileId) return

      const text = await file.text()
      const result = parseProductsCSV(text, selectedProfileId)
      setPreviewResult(result)
    } catch (error) {
      console.error('Error previewing CSV:', error)
      setPreviewResult({
        success: false,
        message: `Error al leer el archivo: ${error instanceof Error ? error.message : 'Error desconocido'}`,
        importedCount: 0,
        errors: [],
        products: []
      })
    }
  }

  const handleImport = async () => {
    if (!previewResult?.products || previewResult.products.length === 0) return

    setImporting(true)
    try {
      await onImport(previewResult.products)
      onOpenChange(false)
      setFile(null)
      setPreviewResult(null)
      setSelectedProfileId(null)
    } catch (error) {
      console.error('Error importing products:', error)
      setPreviewResult({
        ...previewResult,
        success: false,
        message: `Error al importar: ${error instanceof Error ? error.message : 'Error desconocido'}`
      })
    } finally {
      setImporting(false)
    }
  }

  const handleClose = () => {
    try {
      if (!importing) {
        onOpenChange(false)
        setFile(null)
        setPreviewResult(null)
        setSelectedProfileId(null)
      }
    } catch (error) {
      console.error('Error closing dialog:', error)
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Upload size={24} className="text-primary" />
            Importar Productos desde CSV
          </DialogTitle>
          <DialogDescription>
            Sube un archivo CSV con productos para importar en masa
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={downloadCSVTemplate}
              className="flex items-center gap-2"
            >
              <Download size={18} />
              Descargar Plantilla CSV
            </Button>
            <p className="text-sm text-muted-foreground">
              Usa esta plantilla como guía
            </p>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Perfil de destino</label>
            <Select
              value={selectedProfileId?.toString()}
              onValueChange={(value) => setSelectedProfileId(parseInt(value))}
            >
              <SelectTrigger>
                <SelectValue placeholder="Selecciona un perfil" />
              </SelectTrigger>
              <SelectContent>
                {profiles.map(profile => (
                  <SelectItem key={profile.id} value={profile.id.toString()}>
                    {profile.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Archivo CSV</label>
            <div className="flex items-center gap-2">
              <input
                type="file"
                accept=".csv"
                onChange={handleFileChange}
                className="flex-1 text-sm text-muted-foreground file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-primary file:text-primary-foreground hover:file:bg-primary/90"
              />
              {file && (
                <Badge variant="secondary" className="flex items-center gap-1">
                  <FileArrowDown size={14} />
                  {file.name}
                </Badge>
              )}
            </div>
          </div>

          {file && selectedProfileId && !previewResult && (
            <Button
              onClick={handlePreview}
              className="w-full"
              variant="secondary"
            >
              Vista Previa de Importación
            </Button>
          )}

          {previewResult && (
            <div className="space-y-4">
              <Alert className={previewResult.success ? 'border-green-500' : 'border-destructive'}>
                <div className="flex items-start gap-2">
                  {previewResult.success ? (
                    <CheckCircle size={20} className="text-green-500 mt-0.5" weight="fill" />
                  ) : (
                    <WarningCircle size={20} className="text-destructive mt-0.5" weight="fill" />
                  )}
                  <div className="flex-1">
                    <AlertDescription>
                      <p className="font-semibold mb-1">{previewResult.message}</p>
                      {previewResult.importedCount > 0 && (
                        <p className="text-sm">
                          {previewResult.importedCount} productos válidos listos para importar
                        </p>
                      )}
                      {previewResult.errors.length > 0 && (
                        <p className="text-sm text-destructive mt-1">
                          {previewResult.errors.length} filas con errores
                        </p>
                      )}
                    </AlertDescription>
                  </div>
                </div>
              </Alert>

              {previewResult.errors.length > 0 && (
                <div className="max-h-48 overflow-y-auto border rounded-md p-3 bg-muted/50">
                  <h4 className="text-sm font-semibold mb-2">Errores de validación:</h4>
                  <ul className="space-y-1 text-sm">
                    {previewResult.errors.map((error, index) => (
                      <li key={index} className="text-destructive">
                        Fila {error.row}: {error.error}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {previewResult.products.length > 0 && (
                <div className="max-h-64 overflow-y-auto border rounded-md p-3">
                  <h4 className="text-sm font-semibold mb-2">
                    Productos a importar ({previewResult.products.length}):
                  </h4>
                  <div className="space-y-2">
                    {previewResult.products.slice(0, 10).map((product, index) => (
                      <div key={index} className="text-sm p-2 bg-muted/50 rounded">
                        <div className="flex items-center justify-between">
                          <span className="font-medium">{product.nombre}</span>
                          <Badge variant="outline">{product.categoria}</Badge>
                        </div>
                        <div className="text-xs text-muted-foreground mt-1">
                          SKU: {product.sku} | {product.marca} {product.modelo} | Stock: {product.stock_disponible}
                        </div>
                      </div>
                    ))}
                    {previewResult.products.length > 10 && (
                      <p className="text-xs text-muted-foreground text-center">
                        ... y {previewResult.products.length - 10} más
                      </p>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={importing}>
            Cancelar
          </Button>
          {previewResult?.success && previewResult.products.length > 0 && (
            <Button onClick={handleImport} disabled={importing}>
              {importing ? 'Importando...' : `Importar ${previewResult.importedCount} Productos`}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
