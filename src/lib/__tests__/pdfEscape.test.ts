import { describe, expect, it } from 'vitest'
import { escapePrintHtml } from '../pdfExport'

describe('printed business data', () => {
  it('renders executable-looking text as escaped text', () => {
    expect(escapePrintHtml('<img src=x onerror="alert(1)">'))
      .toBe('&lt;img src=x onerror=&quot;alert(1)&quot;&gt;')
  })
  it('keeps customer notes and bank names neutral in HTML', () => {
    expect(escapePrintHtml('BAC & "Promerica"')).toBe('BAC &amp; &quot;Promerica&quot;')
    expect(escapePrintHtml('</script>')).toBe('&lt;/script&gt;')
    expect(escapePrintHtml(null)).toBe('')
  })
})
