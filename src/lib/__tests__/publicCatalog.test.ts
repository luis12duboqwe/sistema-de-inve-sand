import { afterEach, describe, expect, it, vi } from 'vitest'
import { fetchAllPublicCatalogProducts } from '../publicCatalog'

describe('public catalog pagination and isolation', () => {
  afterEach(() => { vi.unstubAllGlobals() })

  it('loads every page from same-origin without operator credentials', async () => {
    const firstPage = Array.from({ length: 100 }, (_, i) => ({ id: i + 1 }))
    const fetcher = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ items: firstPage, pages: 2 }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ items: [{ id: 101 }], pages: 2 }), { status: 200 }))
    vi.stubGlobal('fetch', fetcher)

    const result = await fetchAllPublicCatalogProducts({ search: 'Samsung', category: 'celular' })
    expect(result).toHaveLength(101)
    expect(fetcher).toHaveBeenCalledTimes(2)
    expect(fetcher.mock.calls[0][0]).toContain('/api/public/catalog?')
    expect(fetcher.mock.calls[0][0]).toContain('search=Samsung')
    expect(fetcher.mock.calls[1][0]).toContain('page=2')
    expect(fetcher.mock.calls[0][1]).not.toHaveProperty('credentials')
    expect(fetcher.mock.calls[0][1]).not.toHaveProperty('headers')
  })

  it('fails closed on HTTP errors', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 500 })))
    await expect(fetchAllPublicCatalogProducts({})).rejects.toThrow('Error al cargar')
  })

  it('honors abort signals when a search changes', async () => {
    const controller = new AbortController()
    const fetcher = vi.fn().mockImplementation(() => {
      controller.abort()
      return Promise.reject(new DOMException('Aborted', 'AbortError'))
    })
    vi.stubGlobal('fetch', fetcher)
    await expect(fetchAllPublicCatalogProducts({ signal: controller.signal })).rejects.toMatchObject({ name: 'AbortError' })
    expect(fetcher).toHaveBeenCalledTimes(1)
  })
})
