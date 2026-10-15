export interface PublicProduct {
  id: number
  nombre: string
  marca: string
  modelo: string
  categoria: string
  condicion: string
  precio: number
  moneda: string
  capacidad?: string
  color?: string
  in_stock: boolean
}

interface PublicCatalogOptions {
  search?: string
  category?: string
  signal?: AbortSignal
}

/** Load all public pages without operator tokens, local KV or localhost defaults. */
export async function fetchAllPublicCatalogProducts(
  { search, category, signal }: PublicCatalogOptions,
): Promise<PublicProduct[]> {
  const configured = String(import.meta.env.VITE_API_BASE_URL || '/api').trim()
  const base = configured.startsWith('/') && !configured.startsWith('//')
    ? configured.replace(/\/$/, '') : '/api'
  const products: PublicProduct[] = []
  let page = 1

  while (page <= 100) {
    const params = new URLSearchParams({ per_page: '100', page: String(page) })
    if (search) params.set('search', search)
    if (category && category !== 'all') params.set('category', category)
    const response = await fetch(`${base}/public/catalog?${params}`, { signal })
    if (!response.ok) throw new Error('Error al cargar el catálogo público')
    const payload: { items?: PublicProduct[], pages?: number } = await response.json()
    if (!Array.isArray(payload.items)) throw new Error('Respuesta inválida del catálogo')
    products.push(...payload.items)
    if (payload.items.length < 100 || page >= (payload.pages ?? page)) break
    page += 1
  }
  return products
}
