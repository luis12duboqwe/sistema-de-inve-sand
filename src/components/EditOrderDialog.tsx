import { useState, useEffect } from 'react'
  Dialog
  DialogH
  DialogFooter
import { Button
import { Label
  Select,
  SelectItem,
  SelectValue
import { Plus, Trash } from '@phosphor-icons/
import { toast } from 'sonner'
interfac
  onOpenC
  products: Prod
    customer_
    canal: Order
    items: {
      cantidad: number
import { Plus, Trash } from '@phosphor-icons/react'
interface OrderItemForm {
  cantidad: number

  open,
  order,
  onSubmit
  const [customerName, 
  const [canal, setCanal] = us
  const [items, setItems] = useState<Ord
      product_id: item.pr
    }))
  const [isSubmitting, se
  useEffect(() => {
    items: {
      setCanal(order.can
      setItems(
    }[]
        }))
 

    setItems([...items, {
  const removeItem =
  }
 

  }
  const
    newItems[in
  }
  const get
      if (
      const availableStock
    })

    return items.reduce((total, item) => {
      if (!product) return total
  const [items, setItems] = useState<OrderItemForm[]>(
    order.items.map(item => ({
      product_id: item.product_id,
      cantidad: item.cantidad
    }))
  )
      toast.error('Por favor ingresa el nombre del client

    if (!customerPh
      return

    if (validItems.length === 0) {
      return

      setItems(
        order.items.map(item => ({
          product_id: item.product_id,
          cantidad: item.cantidad
        }))
      )
    s
      await o

  const addItem = () => {
    setItems([...items, { product_id: 0, cantidad: 1 }])
  }

  const removeItem = (index: number) => {
    setItems(items.filter((_, i) => i !== index))
  }

  const updateItemProduct = (index: number, productId: number) => {
    const newItems = [...items]
    newItems[index].product_id = productId
    setItems(newItems)
  }

  const updateItemQuantity = (index: number, cantidad: number) => {
    const newItems = [...items]
    newItems[index].cantidad = cantidad
    setItems(newItems)
  }

  const getAvailableProducts = (currentProductId: number) => {
    return products.filter(p => {
      if (p.id === currentProductId) return true
      const originalItem = order.items.find(oi => oi.product_id === p.id)
      const availableStock = p.stock_disponible + (originalItem?.cantidad || 0)
      return availableStock > 0
    })
  }

  const calculateTotal = () => {
    return items.reduce((total, item) => {
      const product = products.find(p => p.id === item.product_id)
      if (!product) return total
      return total + product.precio * item.cantidad
    }, 0)
  }

                onChange={(e) => setCustomerPhone(e.ta
              />

          <div className="grid 
              <Label htmlFor="edit-canal">Canal</Label>
            
     

                  <SelectItem va
              </Select>

     

              >
                  <SelectValue />
                <SelectContent>
            
     

          </div>
          <div className="space-y-2">
                <Plus size={16} className="mr-1" />
              </Button>
      const maxAvailable = (product?.stock_disponible || 0) + originalQuantity

                <Button type="button" var
        toast.error(`Stock insuficiente para ${product?.nombre}. Disponible: ${maxAvailable}`)
              
       
     


         
                        <Label c
                          value={ite
                        >
              
                          <Selec
                         
        
      onOpenChange(false)
                     

                        <Label className="text-sm
    } finally {
                          mi
     
   

          
        </DialogFooter>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
}



































































































































                        variant="outline"


                        className="mb-2"

                        <Trash size={18} />


















        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <Button onClick={handleSubmit} disabled={isSubmitting}>
            {isSubmitting ? 'Guardando...' : 'Guardar Cambios'}
          </Button>
        </DialogFooter>




