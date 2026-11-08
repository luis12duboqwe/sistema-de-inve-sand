import { useEffect, useRef, useState } from 'react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { apiClient } from '@/lib/apiClient'
import type { Location } from '@/lib/types'
import {
  repairIssueNames, repairStatusNames,
  type RepairCase, type RepairIssue, type RepairStatus, type RepairTransitionInput
} from '@/lib/repairs'

type Props = { open: boolean; onOpenChange: (open: boolean) => void; locations: Location[] }

const transitions: Record<RepairStatus, RepairStatus[]> = {
  received: ['diagnosing', 'cancelled'],
  diagnosing: ['awaiting_approval', 'cancelled'],
  awaiting_approval: ['approved', 'cancelled'],
  approved: ['awaiting_parts', 'repairing', 'cancelled'],
  awaiting_parts: ['repairing', 'cancelled'],
  repairing: ['quality_check'],
  quality_check: ['ready', 'repairing'],
  ready: ['delivered'],
  delivered: [], cancelled: []
}
const key = () => 'event-' + crypto.randomUUID()

export function RepairIntakeDialog({ open, onOpenChange, locations }: Props) {
  const [cases, setCases] = useState<RepairCase[]>([])
  const [selected, setSelected] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [device, setDevice] = useState('')
  const pendingIntakeKey = useRef<string | null>(null)
  const [location, setLocation] = useState('')
  const [issue, setIssue] = useState<RepairIssue>('screen')
  const [next, setNext] = useState<RepairStatus | ''>('')
  const [quote, setQuote] = useState('')
  const [approval, setApproval] = useState('')
  const [parts, setParts] = useState(false)
  const [quality, setQuality] = useState(false)
  const [tech, setTech] = useState('')
  const current = cases.find(item => item.id === selected) ?? null

  async function refresh() {
    setLoading(true)
    try {
      const rows = await apiClient.getRepairCases()
      setCases(rows)
      setSelected(previous => previous && rows.some(row => row.id === previous) ?
        previous : (rows[0]?.id ?? null))
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'No se pudo consultar el taller')
    } finally { setLoading(false) }
  }
  useEffect(() => { if (open) void refresh() }, [open])
  useEffect(() => {
    setNext('')
    setQuote('')
    setApproval('')
    setParts(false)
    setQuality(false)
    setTech('')
  }, [selected, current?.revision])

  async function createCase() {
    if (!location || device.trim().length < 3) {
      toast.error('Indicá modelo y sucursal')
      return
    }
    const requestKey = pendingIntakeKey.current ?? key()
    pendingIntakeKey.current = requestKey
    setBusy(true)
    try {
      const data = await apiClient.createRepairCase({
        intake_key: requestKey,
        location_id: Number(location), device_model: device.trim(), issue_category: issue
      })
      await refresh()
      setSelected(data.id)
      setDevice('')
      pendingIntakeKey.current = null
      toast.success('Orden registrada')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'No se pudo registrar la orden')
    } finally { setBusy(false) }
  }

  async function updateStatus() {
    if (!current || !next || !transitions[current.status].includes(next)) return
    const data: RepairTransitionInput = {
      next_status: next, expected_revision: current.revision, event_key: key()
    }
    if (next === 'awaiting_approval') data.quote_amount = quote
    if (next === 'approved') data.approval_reference = approval
    if (next === 'awaiting_parts') data.parts_available = false
    if (next === 'repairing' && current.status !== 'quality_check') {
      if (!parts) { toast.error('Confirmá repuestos disponibles'); return }
      data.parts_available = true
    }
    if (next === 'ready') {
      if (!quality) { toast.error('Confirmá el control de calidad'); return }
      data.qa_passed = true
    }
    setBusy(true)
    try {
      await apiClient.transitionRepairCase(current.id, data)
      await refresh()
      toast.success('Cambio registrado en historial')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'No se pudo cambiar el estado')
    } finally { setBusy(false) }
  }

  async function assign() {
    if (!current || !/^[1-9]\d*$/.test(tech)) {
      toast.error('Indicá el ID del técnico activo')
      return
    }
    setBusy(true)
    try {
      await apiClient.assignRepairTechnician(current.id, {
        expected_revision: current.revision, event_key: key(), technician_id: Number(tech)
      })
      await refresh()
      toast.success('Técnico asignado')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'No se pudo asignar el técnico')
    } finally { setBusy(false) }
  }

  return <Dialog open={open} onOpenChange={onOpenChange}>
    <DialogContent className="max-h-[90vh] max-w-5xl overflow-y-auto">
      <DialogHeader>
        <DialogTitle>Reparaciones — taller</DialogTitle>
        <DialogDescription>
          Operación administrativa. No envía WhatsApp, no ejecuta pagos ni mueve inventario.
          La aprobación del cliente debe documentarse y verificarse fuera de este formulario.
        </DialogDescription>
      </DialogHeader>
      <div className="space-y-4">
        <section className="grid gap-3 rounded border p-3 md:grid-cols-3">
          <div className="space-y-1">
            <Label htmlFor="repair-model">Modelo</Label>
            <Input id="repair-model" value={device} maxLength={100}
              onChange={e => { setDevice(e.target.value); pendingIntakeKey.current = null }} placeholder="Ej. iPhone 14 Pro"/>
          </div>
          <div className="space-y-1">
            <Label>Sucursal</Label>
            <Select value={location} onValueChange={v => { setLocation(v); pendingIntakeKey.current = null }}>
              <SelectTrigger><SelectValue placeholder="Elegir" /></SelectTrigger>
              <SelectContent>
                {locations.filter(l => l.activo).map(l => <SelectItem key={l.id} value={String(l.id)}>{l.nombre}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <Label>Falla</Label>
            <Select value={issue} onValueChange={x => { setIssue(x as RepairIssue); pendingIntakeKey.current = null }}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {Object.entries(repairIssueNames).map(([k, name]) =>
                  <SelectItem key={k} value={k}>{name}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <Button disabled={busy || loading} onClick={() => void createCase()}>Registrar equipo</Button>
        </section>

        <div className="flex items-center justify-between">
          <h3 className="font-semibold">Órdenes ({cases.length})</h3>
          <Button variant="outline" disabled={busy || loading} onClick={() => void refresh()}>Actualizar</Button>
        </div>
        <div className="max-h-44 space-y-2 overflow-y-auto">
          {cases.length === 0 && <p className="text-sm text-muted-foreground">Sin órdenes de reparación.</p>}
          {cases.map(item =>
            <button type="button" key={item.id} onClick={() => setSelected(item.id)}
              className={'w-full rounded border p-2 text-left text-sm ' +
                         (selected === item.id ? 'border-primary bg-primary/5' : '')}>
              <strong>{item.external_reference} · {item.device_model}</strong>
              <Badge className="ml-2" variant="secondary">{repairStatusNames[item.status]}</Badge>
            </button>)}
        </div>

        {current && <section className="space-y-3 rounded border p-3">
          <h3 className="font-semibold">{current.external_reference}</h3>
          <div className="grid gap-2 text-sm md:grid-cols-3">
            <span>Estado: {repairStatusNames[current.status]}</span>
            <span>Técnico: {current.technician_id ?? 'Sin asignar'}</span>
            <span>Revisión: {current.revision}</span>
            <span>Presupuesto: {current.quote_amount ?? 'Pendiente'}</span>
            <span>Aprobado: {current.quote_approved ? 'Sí' : 'No'}</span>
            <span>Control de calidad: {current.qa_passed ? 'Aprobado' : 'Pendiente'}</span>
          </div>
          {transitions[current.status].length > 0 && <>
            <div className="flex flex-wrap items-end gap-2">
              <div className="space-y-1">
                <Label>ID de técnico</Label>
                <Input inputMode="numeric" value={tech} onChange={e => setTech(e.target.value)} />
              </div>
              <Button variant="secondary" disabled={busy} onClick={() => void assign()}>Asignar técnico</Button>
            </div>
            <div className="space-y-1">
              <Label>Siguiente estado</Label>
              <Select value={next} onValueChange={v => setNext(v as RepairStatus)}>
                <SelectTrigger><SelectValue placeholder="Elegir" /></SelectTrigger>
                <SelectContent>
                  {transitions[current.status].map(status =>
                    <SelectItem key={status} value={status}>{repairStatusNames[status]}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            {next === 'awaiting_approval' && <div className="space-y-1">
              <Label>Presupuesto en lempiras</Label>
              <Input inputMode="decimal" value={quote} onChange={e => setQuote(e.target.value)} />
            </div>}
            {next === 'approved' && <div className="space-y-1">
              <Label>Referencia de aprobación documentada</Label>
              <Input value={approval} maxLength={64}
                onChange={e => setApproval(e.target.value.toUpperCase())} />
              <p className="text-xs text-muted-foreground">No constituye por sí sola prueba de consentimiento.</p>
            </div>}
            {next === 'repairing' && current.status !== 'quality_check' && <label className="flex gap-2 text-sm">
              <input type="checkbox" checked={parts} onChange={e => setParts(e.target.checked)}/>
              Confirmé manualmente disponibilidad de repuestos
            </label>}
            {next === 'ready' && <label className="flex gap-2 text-sm">
              <input type="checkbox" checked={quality} onChange={e => setQuality(e.target.checked)}/>
              Completé y aprobé el control de calidad
            </label>}
            <Button disabled={!next || busy} onClick={() => void updateStatus()}>Guardar cambio</Button>
          </>}
        </section>}
      </div>
    </DialogContent>
  </Dialog>
}
