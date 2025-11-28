import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Trash, Plus } from '@phosphor-icons/

  open: boolean
  products: ProductWithStock[]
  onSubmit: (orderId: number, updates: {
import { toast } from 'sonner'

    items: Array<{
      product_i
    }>
}
interface OrderItemForm {
  product_id: number
}
export function EditOrderD
  const [customerPhone, s
  const [metodoPago, setMetodoPago] =
  const [isSubmitt
  useEffect(() =>
      setCustomerName(or
      setCanal(order.c
      
        product_id: i
 

interface OrderItemForm {
  id?: number
  product_id: number
  cantidad: number
}

    }
    if (!customerPhone.trim()) {
      return
    
  const [metodoPago, setMetodoPago] = useState<Order['metodo_pago']>('efectivo')
  const [items, setItems] = useState<OrderItemForm[]>([])
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {

      setCustomerName(order.customer_name)
      setCustomerPhone(order.customer_phone)
      setCanal(order.canal)
      const originalQuantity = origina
      setItems(order.items.map(item => ({
        id: item.id,
        product_id: item.product_id,
        cantidad: item.cantidad
      })))
    s
  }, [order])

  const handleSubmit = async (e: React.FormEvent) => {
        metodo_pago: m
    
    if (!customerName.trim()) {
      toast.error('Por favor ingresa el nombre del cliente')
      return
    }
    
    if (!customerPhone.trim()) {
      toast.error('Por favor ingresa el teléfono del cliente')
      return
    }
    
      setItems([...items, { p
      toast.error('Por favor agrega al menos un producto')
      return
  con

    const validItems = items.filter(item => item.product_id > 0 && item.cantidad > 0)
    if (validItems.length === 0) {
      toast.error('Por favor agrega productos válidos')
      return
    }

    for (const item of validItems) {
      const product = products.find(p => p.id === item.product_id)
      if (!product) continue
      
      const originalItem = order.items.find(oi => oi.product_id === item.product_id)
      const originalQuantity = originalItem?.cantidad || 0
      const maxAvailable = product.stock_disponible + originalQuantity
      
      if (item.cantidad > maxAvailable) {
        toast.error(`Stock insuficiente para ${product.nombre}. Disponible: ${maxAvailable}`)
        return
      }
    }


    try {
      await onSubmit(order.id, {
        customer_name: customerName,
        customer_phone: customerPhone,
        canal,
        metodo_pago: metodoPago,
        items: validItems
        
    } catch (error) {
      console.error('Error updating order:', error)
          <div 
      setIsSubmitting(false)
     
  }

  const addItem = () => {
              />
      !items.some(item => item.product_id === p.id)
     
    if (availableProduct) {
      setItems([...items, { product_id: availableProduct.id, cantidad: 1 }])
    }
  }

  const removeItem = (index: number) => {
    const newItems = items.filter((_, i) => i !== index)
                  <Sel
  }

  const updateItemProduct = (index: number, productId: number) => {
                </SelectContent
    newItems[index].product_id = productId

   

  const updateItemQuantity = (index: number, cantidad: number) => {
    const newItems = [...items]
    newItems[index].cantidad = cantidad
    setItems(newItems)
   

  const calculateTotal = () => {
    return items.reduce((sum, item) => {
      const product = products.find(p => p.id === item.product_id)
      return sum + (product?.precio || 0) * item.cantidad
    }, 0)
  }

  const getAvailableProducts = (currentProductId?: number) => {
    return products.filter(p => {
      if (p.id === currentProductId) return true
      const isAlreadySelected = items.some(item => item.product_id === p.id)
      return !isAlreadySelected
    })
  }

          
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Editar Orden #{order.id}</DialogTitle>
        </DialogHeader>

                        </div>

                        type="button"
                        size="icon"
                    
                        <Trash size={18
                    </div>
                })}
            )}

            <div
              <spa

          </div>
          <DialogFooter>
              Cancel
            <Button type="submit" disabl
            </Button>
        </form>
    </Dialog>
}




















































































                        </div>

























                      </div>

                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() => removeItem(index)}
                        className="mt-6"
                      >
                        <Trash size={18} className="text-destructive" />
                      </Button>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          <div className="pt-4 border-t">
            <div className="flex items-center justify-between">
              <span className="text-lg font-semibold">Total:</span>
              <span className="text-2xl font-bold text-primary">
                HNL {calculateTotal().toLocaleString()}
              </span>
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancelar
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Guardando...' : 'Guardar Cambios'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
