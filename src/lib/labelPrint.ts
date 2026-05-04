import JsBarcode from 'jsbarcode'

export type LabelPresetId = '50x25' | '58x30' | '80x50' | 'custom'
export type LabelOrientation = 'horizontal' | 'vertical'

export interface LabelPrintSettings {
  preset: LabelPresetId
  widthMm: number
  heightMm: number
  orientation: LabelOrientation
  edgeMarginMm: number
  offsetXmm: number
  offsetYmm: number
  labelsPerPage: 1 | 3
}

export interface PrintableLabelData {
  productName: string
  sku: string
  imei: string
  color?: string
  capacity?: string
}

export const LABEL_SIZE_PRESETS: Record<Exclude<LabelPresetId, 'custom'>, { label: string; widthMm: number; heightMm: number }> = {
  '50x25': { label: '50 x 25 mm', widthMm: 50, heightMm: 25 },
  '58x30': { label: '58 x 30 mm', widthMm: 58, heightMm: 30 },
  '80x50': { label: '80 x 50 mm', widthMm: 80, heightMm: 50 },
}

export const DEFAULT_LABEL_PRINT_SETTINGS: LabelPrintSettings = {
  preset: '50x25',
  widthMm: 50,
  heightMm: 25,
  orientation: 'horizontal',
  edgeMarginMm: 1.5,
  offsetXmm: 0,
  offsetYmm: 0,
  labelsPerPage: 1,
}

const escapeHtml = (value: string): string =>
  value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')

const formatDetails = (label: PrintableLabelData): string =>
  [label.color, label.capacity].filter(Boolean).join(' • ')

const getBarcodeSvgHeight = (heightMm: number, labelsPerPage: 1 | 3): number => {
  if (labelsPerPage === 3) return 18
  if (heightMm <= 25) return 34
  if (heightMm <= 30) return 40
  return 56
}

const getBarcodeModuleWidth = (heightMm: number, labelsPerPage: 1 | 3): number => {
  if (labelsPerPage === 3) return 1.2
  if (heightMm <= 25) return 1.5
  if (heightMm <= 30) return 1.6
  return 2.0
}

const getNameFontSize = (heightMm: number): number => {
  if (heightMm <= 25) return 10
  if (heightMm <= 30) return 11
  return 14
}

const getSecondaryFontSize = (heightMm: number): number => {
  if (heightMm <= 25) return 8
  if (heightMm <= 30) return 9
  return 11
}

/**
 * Genera un SVG CODE128 inline usando jsbarcode instalado localmente.
 * Sin CDN, sin internet — funciona siempre.
 */
function generateBarcodeSvgInline(
  value: string,
  barHeight: number,
  moduleWidth: number,
): string {
  try {
    const svgEl = document.createElementNS('http://www.w3.org/2000/svg', 'svg')

    JsBarcode(svgEl, value, {
      format: 'CODE128',
      displayValue: false,
      lineColor: '#000000',
      background: '#FFFFFF',
      margin: 2,
      marginTop: 2,
      marginBottom: 2,
      marginLeft: 4,
      marginRight: 4,
      width: moduleWidth,
      height: barHeight,
    })

    // Hacer el SVG responsivo
    const w = svgEl.getAttribute('width')
    const h = svgEl.getAttribute('height')
    if (w && h && !svgEl.getAttribute('viewBox')) {
      svgEl.setAttribute('viewBox', `0 0 ${w} ${h}`)
    }
    svgEl.setAttribute('preserveAspectRatio', 'none')
    svgEl.removeAttribute('width')
    svgEl.removeAttribute('height')
    svgEl.setAttribute('class', 'barcode-svg')
    svgEl.setAttribute('style', `display:block;width:100%;max-width:100%;height:${barHeight}px;`)

    return svgEl.outerHTML
  } catch (err) {
    console.error('Error generando barcode SVG:', err)
    return `<svg class="barcode-svg" style="display:block;width:100%;height:${barHeight}px;background:#fff;"></svg>`
  }
}

export function normalizeLabelPrintSettings(settings?: Partial<LabelPrintSettings>): LabelPrintSettings {
  const merged = { ...DEFAULT_LABEL_PRINT_SETTINGS, ...settings }
  return {
    preset: merged.preset,
    widthMm: Number.isFinite(merged.widthMm) ? Math.max(20, Math.min(120, merged.widthMm)) : DEFAULT_LABEL_PRINT_SETTINGS.widthMm,
    heightMm: Number.isFinite(merged.heightMm) ? Math.max(10, Math.min(80, merged.heightMm)) : DEFAULT_LABEL_PRINT_SETTINGS.heightMm,
    orientation: merged.orientation === 'vertical' ? 'vertical' : 'horizontal',
    edgeMarginMm: Number.isFinite(merged.edgeMarginMm) ? Math.max(0, Math.min(6, merged.edgeMarginMm)) : DEFAULT_LABEL_PRINT_SETTINGS.edgeMarginMm,
    offsetXmm: Number.isFinite(merged.offsetXmm) ? Math.max(-10, Math.min(10, merged.offsetXmm)) : DEFAULT_LABEL_PRINT_SETTINGS.offsetXmm,
    offsetYmm: Number.isFinite(merged.offsetYmm) ? Math.max(-10, Math.min(10, merged.offsetYmm)) : DEFAULT_LABEL_PRINT_SETTINGS.offsetYmm,
    labelsPerPage: merged.labelsPerPage === 3 ? 3 : 1,
  }
}

export function buildLabelsPrintHtml(
  title: string,
  labels: PrintableLabelData[],
  settingsInput?: Partial<LabelPrintSettings>,
): string {
  const settings = normalizeLabelPrintSettings(settingsInput)
  const pageWidthMm  = settings.orientation === 'vertical' ? settings.heightMm : settings.widthMm
  const pageHeightMm = settings.orientation === 'vertical' ? settings.widthMm  : settings.heightMm

  const textReferenceMm = Math.min(pageWidthMm, pageHeightMm)
  const itemHeightMm    = pageHeightMm / settings.labelsPerPage

  const barcodeSvgHeight   = getBarcodeSvgHeight(textReferenceMm, settings.labelsPerPage)
  const barcodeModuleWidth = getBarcodeModuleWidth(textReferenceMm, settings.labelsPerPage)
  const nameFontSize       = getNameFontSize(textReferenceMm)
  const secondaryFontSize  = getSecondaryFontSize(textReferenceMm)

  const topPaddingMm    = settings.edgeMarginMm
  const sidePaddingMm   = settings.edgeMarginMm
  const bottomPaddingMm = settings.labelsPerPage === 3
    ? Math.max(0, settings.edgeMarginMm - 0.2)
    : settings.edgeMarginMm

  const perItemReferenceMm = Math.min(pageWidthMm, itemHeightMm)
  const perItemBarcodeSvgHeight = settings.labelsPerPage === 3
    ? Math.max(12, Math.round(getBarcodeSvgHeight(perItemReferenceMm, settings.labelsPerPage) * 0.85))
    : barcodeSvgHeight
  const perItemBarcodeModuleWidth = settings.labelsPerPage === 3
    ? Math.max(0.6, Number((getBarcodeModuleWidth(perItemReferenceMm, settings.labelsPerPage) * 0.92).toFixed(2)))
    : barcodeModuleWidth
  const perItemNameFontSize = settings.labelsPerPage === 3
    ? Math.max(7, Math.round(getNameFontSize(perItemReferenceMm) * 0.88))
    : nameFontSize
  const perItemSecondaryFontSize = settings.labelsPerPage === 3
    ? Math.max(6, Math.round(getSecondaryFontSize(perItemReferenceMm) * 0.9))
    : secondaryFontSize

  const groupedLabels = labels.reduce<PrintableLabelData[][]>((acc, label, index) => {
    const groupIndex = Math.floor(index / settings.labelsPerPage)
    if (!acc[groupIndex]) acc[groupIndex] = []
    acc[groupIndex].push(label)
    return acc
  }, [])

  // Generar SVG inline para cada IMEI único (sin CDN, sin internet)
  const svgsByImei = new Map<string, string>()
  for (const label of labels) {
    if (!svgsByImei.has(label.imei)) {
      svgsByImei.set(
        label.imei,
        generateBarcodeSvgInline(label.imei, perItemBarcodeSvgHeight, perItemBarcodeModuleWidth),
      )
    }
  }

  return `
    <html>
      <head>
        <title>${escapeHtml(title)}</title>
        <meta charset="utf-8" />
        <style>
          @page {
            size: ${pageWidthMm}mm ${pageHeightMm}mm;
            margin: 0;
          }

          * {
            box-sizing: border-box;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
          }

          html, body {
            margin: 0;
            padding: 0;
            width: ${pageWidthMm}mm;
            background: #fff;
            font-family: Arial, Helvetica, sans-serif;
          }

          body { overflow: hidden; }

          .label-page {
            position: relative;
            width: ${pageWidthMm}mm;
            height: ${pageHeightMm}mm;
            overflow: hidden;
            page-break-after: always;
            break-after: page;
          }

          .label-page:last-child {
            page-break-after: auto;
            break-after: auto;
          }

          .label-container {
            position: absolute;
            inset: 0;
            padding: ${topPaddingMm}mm ${sidePaddingMm}mm ${bottomPaddingMm}mm;
            display: flex;
            flex-direction: column;
            transform: translate(${settings.offsetXmm}mm, ${settings.offsetYmm}mm);
            overflow: hidden;
          }

          .label-items {
            display: flex;
            flex-direction: column;
            width: 100%;
            height: 100%;
            ${settings.labelsPerPage === 1 ? 'justify-content: center;' : 'justify-content: stretch;'}
            gap: ${settings.labelsPerPage === 1 ? '0' : '0.6mm'};
          }

          .label-item {
            flex: 1;
            min-height: 0;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: ${settings.labelsPerPage === 1 ? '0.4mm' : '0.1mm'};
            overflow: hidden;
            ${settings.labelsPerPage === 3 ? 'border-bottom: 0.2mm dashed #ddd;' : ''}
          }

          .label-item:last-child { border-bottom: none; }

          .product-name {
            width: 100%;
            text-align: center;
            font-size: ${perItemNameFontSize}px;
            font-weight: 700;
            line-height: 1.05;
            display: -webkit-box;
            -webkit-line-clamp: ${settings.labelsPerPage === 3 ? 2 : 3};
            -webkit-box-orient: vertical;
            overflow: hidden;
            word-break: break-word;
          }

          .details {
            min-height: ${perItemSecondaryFontSize + 1}px;
            width: 100%;
            text-align: center;
            font-size: ${perItemSecondaryFontSize}px;
            line-height: 1;
            color: #222;
            overflow: hidden;
            ${settings.labelsPerPage === 3
              ? 'white-space: nowrap; text-overflow: ellipsis;'
              : 'display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; white-space: normal; word-break: break-word;'}
          }

          .barcode-wrap {
            width: 100%;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 0 1mm;
            overflow: hidden;
          }

          .barcode-svg {
            display: block;
            width: 100%;
            max-width: 100%;
            height: ${perItemBarcodeSvgHeight}px;
          }

          .imei-text {
            width: 100%;
            text-align: center;
            font-size: ${perItemSecondaryFontSize + 1}px;
            font-family: monospace;
            line-height: 1;
            font-weight: 700;
          }

          .sku {
            width: 100%;
            text-align: center;
            font-size: ${Math.max(6, perItemSecondaryFontSize - 1)}px;
            color: #555;
            line-height: 1;
            overflow: hidden;
            white-space: nowrap;
            text-overflow: ellipsis;
          }

          @media screen {
            body {
              min-height: 100vh;
              display: flex;
              flex-direction: column;
              align-items: center;
              justify-content: flex-start;
              gap: 12px;
              padding: 12px;
              background: #f5f5f5;
            }

            .label-page {
              box-shadow: 0 1px 4px rgba(0,0,0,0.18);
            }
          }
        </style>
      </head>
      <body>
        ${groupedLabels.map(group => `
          <div class="label-page">
            <div class="label-container">
              <div class="label-items">
                ${group.map(label => `
                  <div class="label-item">
                    <div class="product-name">${escapeHtml(label.productName)}</div>
                    <div class="details">${escapeHtml(formatDetails(label))}</div>
                    <div class="barcode-wrap">
                      ${svgsByImei.get(label.imei) ?? ''}
                    </div>
                    <div class="imei-text">${escapeHtml(label.imei)}</div>
                    <div class="sku">${escapeHtml(label.sku)}</div>
                  </div>
                `).join('')}
              </div>
            </div>
          </div>
        `).join('')}
        <script>
          /* SVG ya embebido — solo disparar impresión */
          window.onload = () => {
            const go = () => setTimeout(() => { window.print(); window.close() }, 120)
            if (document.fonts && document.fonts.ready) {
              document.fonts.ready.then(go).catch(go)
            } else {
              go()
            }
          }
        </script>
      </body>
    </html>
  `
}
