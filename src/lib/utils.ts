import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function calculateLuhnCheckDigit(imei14: string): number {
  if (imei14.length !== 14 || !/^\d+$/.test(imei14)) {
    throw new Error("Input must be 14 digits");
  }

  let sum = 0;
  for (let i = 0; i < 14; i++) {
    let digit = parseInt(imei14.charAt(i));
    // Indices impares (1, 3, 5...) se multiplican por 2
    if (i % 2 !== 0) {
      digit *= 2;
      if (digit > 9) digit -= 9;
    }
    sum += digit;
  }
  
  return (10 - (sum % 10)) % 10;
}

export function validateIMEI(imei: string): boolean {
  if (imei.length !== 15 || !/^\d+$/.test(imei)) return false;
  const imei14 = imei.substring(0, 14);
  const checkDigit = parseInt(imei.charAt(14));
  try {
    return calculateLuhnCheckDigit(imei14) === checkDigit;
  } catch {
    return false;
  }
}
