import { cn } from '@/lib/utils'
import { labelColorClass, labelColors, type LabelColor } from './colors'

/** A label's colour as a small dot beside its name (identity only; never a chart series colour). */
export function LabelDot({ color, className }: { color: string; className?: string }) {
  const known = (labelColors as readonly string[]).includes(color) ? (color as LabelColor) : 'gray'
  return <span className={cn('size-2 shrink-0 rounded-full', labelColorClass[known], className)} aria-hidden="true" />
}
