import { z } from 'zod'

export const LABEL_NAME_MAX = 50

/** Mirrors the backend's normalize_label_name (the server is authoritative): lowercase, every run of
 *  non-letters/digits becomes "_", no leading/trailing "_". "Credit Card-Bill!" -> "credit_card_bill". */
export function normalizeLabelName(raw: string): string {
  return raw
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, '_')
    .replace(/^_+|_+$/g, '')
}

export const displayNameSchema = z
  .string()
  .trim()
  .refine((raw) => normalizeLabelName(raw).length > 0, 'Give the label a name with at least one letter or digit')
  .refine((raw) => raw.length <= LABEL_NAME_MAX, `Keep the name under ${LABEL_NAME_MAX} characters`)
