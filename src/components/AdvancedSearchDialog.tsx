import { useState } from 'react'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Calendar } from '@/components/ui/calendar'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { CalendarBlank, MagnifyingGlass, X } from '@phosphor-icons/react'
import { format } from 'date-fns'
import type { AdvancedSearchFilters, DateRange } from '@/lib/types'

interface AdvancedSearchDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSearch: (filters: AdvancedSearchFilters) => void
  onClear: () => void
}

export function AdvancedSearchDialog({
  open,
  onOpenChange,
  onSearch,
  onClear
}: AdvancedSearchDialogProps) {
  const [dateRange, setDateRange] = useState<DateRange | undefined>()
  const [minAmount, setMinAmount] = useState('')
  const [maxAmount, setMaxAmount] = useState('')
  const [customerName, setCustomerName] = useState('')
  const [customerPhone, setCustomerPhone] = useState('')

  const handleSearch = () => {
    const filters: AdvancedSearchFilters = {}

    if (dateRange) {
      filters.dateRange = dateRange
    }

    if (minAmount) {
      filters.minAmount = parseFloat(minAmount)
    }

    if (maxAmount) {
      filters.maxAmount = parseFloat(maxAmount)
    }

    if (customerName.trim()) {
      filters.customerName = customerName.trim()
    }

    if (customerPhone.trim()) {
      filters.customerPhone = customerPhone.trim()
    }

    onSearch(filters)
    onOpenChange(false)
  }

  const handleClear = () => {
    setDateRange(undefined)
    setMinAmount('')
    setMaxAmount('')
    setCustomerName('')
    setCustomerPhone('')
    onClear()
    onOpenChange(false)
  }

  const hasActiveFilters = dateRange || minAmount || maxAmount || customerName || customerPhone

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <MagnifyingGlass size={24} />
            Búsqueda Avanzada
          </DialogTitle>
          <DialogDescription>
            Filtra órdenes por fecha, monto, cliente o teléfono.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label>Rango de Fechas</Label>
            <Popover>
              <PopoverTrigger asChild>
                <Button variant="outline" className="w-full justify-start text-left font-normal">
                  <CalendarBlank size={16} className="mr-2" />
                  {dateRange?.from ? (
                    dateRange.to ? (
                      <>
                        {format(dateRange.from, 'dd/MM/yyyy')} - {format(dateRange.to, 'dd/MM/yyyy')}
                      </>
                    ) : (
                      format(dateRange.from, 'dd/MM/yyyy')
                    )
                  ) : (
                    <span className="text-muted-foreground">Seleccionar rango</span>
                  )}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0" align="start">
                <Calendar
                  mode="range"
                  selected={dateRange as any}
                  onSelect={(range: any) => setDateRange(range)}
                  numberOfMonths={2}
                />
              </PopoverContent>
            </Popover>
            {dateRange && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setDateRange(undefined)}
                className="w-full"
              >
                <X size={16} className="mr-2" />
                Limpiar fechas
              </Button>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="min-amount">Monto Mínimo</Label>
              <Input
                id="min-amount"
                type="number"
                placeholder="0.00"
                value={minAmount}
                onChange={(e) => setMinAmount(e.target.value)}
                min="0"
                step="0.01"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="max-amount">Monto Máximo</Label>
              <Input
                id="max-amount"
                type="number"
                placeholder="0.00"
                value={maxAmount}
                onChange={(e) => setMaxAmount(e.target.value)}
                min="0"
                step="0.01"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="customer-name">Nombre del Cliente</Label>
            <Input
              id="customer-name"
              placeholder="Buscar por nombre..."
              value={customerName}
              onChange={(e) => setCustomerName(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="customer-phone">Teléfono del Cliente</Label>
            <Input
              id="customer-phone"
              placeholder="Buscar por teléfono..."
              value={customerPhone}
              onChange={(e) => setCustomerPhone(e.target.value)}
            />
          </div>
        </div>

        <div className="flex gap-2">
          {hasActiveFilters && (
            <Button variant="outline" onClick={handleClear} className="flex-1">
              <X size={16} className="mr-2" />
              Limpiar
            </Button>
          )}
          <Button onClick={handleSearch} className="flex-1">
            <MagnifyingGlass size={16} className="mr-2" />
            Buscar
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
