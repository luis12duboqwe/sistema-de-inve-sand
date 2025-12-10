import { useState } from 'react'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { CheckCircle, Warning, Info, Pulse, Wrench, X } from '@phosphor-icons/react'
import type { HealthCheckResult } from '@/lib/healthCheck'

interface HealthCheckDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  result: HealthCheckResult | null
  isRunning: boolean
  onRunCheck: () => void
  onAutoFix: () => void
}

const severityConfig = {
  critical: {
    icon: X,
    color: 'text-destructive',
    bgColor: 'bg-destructive/10',
    borderColor: 'border-destructive/20',
    label: 'Crítico'
  },
  warning: {
    icon: Warning,
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-50',
    borderColor: 'border-yellow-200',
    label: 'Advertencia'
  },
  info: {
    icon: Info,
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    label: 'Info'
  }
}

const categoryLabels = {
  dependency: 'Dependencia',
  integrity: 'Integridad',
  orphan: 'Huérfano',
  duplicate: 'Duplicado',
  consistency: 'Consistencia'
}

export function HealthCheckDialog({
  open,
  onOpenChange,
  result,
  isRunning,
  onRunCheck,
  onAutoFix
}: HealthCheckDialogProps) {
  const [expandedIssues, setExpandedIssues] = useState<Set<string>>(new Set())

  const toggleIssue = (issueId: string) => {
    setExpandedIssues(prev => {
      const next = new Set(prev)
      if (next.has(issueId)) {
        next.delete(issueId)
      } else {
        next.add(issueId)
      }
      return next
    })
  }

  const hasAutoFixableIssues = result?.issues.some(i => i.autoFixable) || false

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-full sm:max-w-3xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Pulse size={24} className="text-primary" weight="duotone" />
            Diagnóstico de Salud del Sistema
          </DialogTitle>
          <DialogDescription>
            Verifica la integridad de datos y dependencias en tu inventario
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="flex gap-2">
            <Button 
              onClick={onRunCheck} 
              disabled={isRunning}
              className="flex-1"
            >
              {isRunning ? (
                <>
                  <Pulse size={18} className="mr-2 animate-pulse" />
                  Analizando...
                </>
              ) : (
                <>
                  <Pulse size={18} className="mr-2" />
                  Ejecutar Diagnóstico
                </>
              )}
            </Button>
            
            {hasAutoFixableIssues && (
              <Button 
                variant="outline" 
                onClick={onAutoFix}
                disabled={isRunning}
              >
                <Wrench size={18} className="mr-2" />
                Reparación Automática
              </Button>
            )}
          </div>

          {result && (
            <>
              <div className="grid grid-cols-3 gap-3">
                <div className="p-4 rounded-lg border bg-card">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Críticos</span>
                    <Badge variant={result.summary.critical > 0 ? "destructive" : "secondary"}>
                      {result.summary.critical}
                    </Badge>
                  </div>
                </div>
                <div className="p-4 rounded-lg border bg-card">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Advertencias</span>
                    <Badge variant={result.summary.warnings > 0 ? "default" : "secondary"}>
                      {result.summary.warnings}
                    </Badge>
                  </div>
                </div>
                <div className="p-4 rounded-lg border bg-card">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Info</span>
                    <Badge variant="secondary">
                      {result.summary.info}
                    </Badge>
                  </div>
                </div>
              </div>

              {result.healthy ? (
                <Alert className="border-green-200 bg-green-50">
                  <CheckCircle size={20} className="text-green-600" weight="fill" />
                  <AlertTitle className="text-green-900">Sistema Saludable</AlertTitle>
                  <AlertDescription className="text-green-700">
                    No se detectaron problemas de integridad o dependencias corruptas.
                  </AlertDescription>
                </Alert>
              ) : (
                <Alert className="border-destructive/20 bg-destructive/10">
                  <Warning size={20} className="text-destructive" weight="fill" />
                  <AlertTitle className="text-destructive">Problemas Detectados</AlertTitle>
                  <AlertDescription className="text-destructive/90">
                    Se encontraron {result.issues.length} problema(s) que requieren atención.
                  </AlertDescription>
                </Alert>
              )}

              {result.issues.length > 0 && (
                <>
                  <Separator />
                  
                  <ScrollArea className="h-[400px] pr-4">
                    <div className="space-y-3">
                      {result.issues.map((issue) => {
                        const config = severityConfig[issue.severity]
                        const Icon = config.icon
                        const isExpanded = expandedIssues.has(issue.id)

                        return (
                          <div
                            key={issue.id}
                            className={`p-4 rounded-lg border ${config.borderColor} ${config.bgColor}`}
                          >
                            <div 
                              className="flex items-start gap-3 cursor-pointer"
                              onClick={() => toggleIssue(issue.id)}
                            >
                              <Icon size={20} className={config.color} weight="fill" />
                              
                              <div className="flex-1 min-w-0">
                                <div className="flex items-start justify-between gap-2 mb-1">
                                  <h4 className={`font-medium ${config.color}`}>
                                    {issue.message}
                                  </h4>
                                  <div className="flex gap-1 shrink-0">
                                    <Badge variant="outline" className="text-xs">
                                      {categoryLabels[issue.category]}
                                    </Badge>
                                    {issue.autoFixable && (
                                      <Badge variant="secondary" className="text-xs">
                                        Auto-reparable
                                      </Badge>
                                    )}
                                  </div>
                                </div>

                                {isExpanded && issue.affectedItems.length > 0 && (
                                  <div className="mt-3 space-y-1">
                                    <p className="text-xs text-muted-foreground font-medium mb-2">
                                      Items afectados:
                                    </p>
                                    <div className="space-y-1 max-h-32 overflow-y-auto">
                                      {issue.affectedItems.map((item, idx) => (
                                        <div 
                                          key={`${item.type}-${item.id}-${idx}`}
                                          className="text-xs p-2 rounded bg-background/50 flex items-center gap-2"
                                        >
                                          <Badge variant="outline" className="text-xs">
                                            {item.type}
                                          </Badge>
                                          <span className="text-muted-foreground">
                                            ID: {item.id}
                                          </span>
                                          {item.name && (
                                            <span className="text-foreground">
                                              {item.name}
                                            </span>
                                          )}
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </ScrollArea>
                </>
              )}

              <div className="text-xs text-muted-foreground text-center">
                Última verificación: {new Date(result.lastCheck).toLocaleString('es-ES')}
              </div>
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
