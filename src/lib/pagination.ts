/** Retrieve every requested page, or explicitly reject a truncated data set. */
export async function loadAllPages<T>(
  fetchPage: (page: number) => Promise<{ items?: T[]; pages?: number } | T[]>,
  maxPages = 1000,
): Promise<T[]> {
  const rows: T[] = []
  for (let page = 1; page <= maxPages; page++) {
    const response = await fetchPage(page)
    if (Array.isArray(response)) return rows.concat(response)
    if (!response || !Array.isArray(response.items)) throw new Error('Invalid pagination response')
    rows.push(...response.items)
    if (page >= (response.pages ?? page) || response.items.length === 0) return rows
  }
  throw new Error(`Exceeded ${maxPages} pages: narrow the search filters`)
}
