/** Local-mode finance calculations must match the bank-configured rate, including 0%. */
export function validatedLocalFinancingRate(raw: number): number {
  if (typeof raw !== 'number' || !Number.isFinite(raw) || raw < 0 || raw > 1) {
    throw new Error('Tasa de financiamiento inválida (esperado decimal de 0 a 1)')
  }
  return raw
}

/** The original sale total excludes card surcharge and includes trade-in value. */
export function originalLocalSaleTotal(beforeSurchargeAfterTradeIn: number, tradeInValue: number): number {
  if (!Number.isFinite(beforeSurchargeAfterTradeIn) || !Number.isFinite(tradeInValue)) {
    throw new Error('Importe financiero inválido')
  }
  return Number((beforeSurchargeAfterTradeIn + tradeInValue).toFixed(2))
}
