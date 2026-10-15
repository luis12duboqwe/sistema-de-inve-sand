/** Phone sales and explicitly serialized accessories require physical identity. */
export function requiresSerialTracking(
  product: { categoria?: string; is_serialized?: boolean } | null | undefined,
): boolean {
  return Boolean(product?.is_serialized || product?.categoria === 'celular')
}

/** Keep UI compatible with backend warranty contract: numeric 14-17 digits. */
export function isValidWarrantySerial(value: string, isPhone: boolean): boolean {
  return isPhone ? /^\d{15}$/.test(value) : /^\d{14,17}$/.test(value)
}
