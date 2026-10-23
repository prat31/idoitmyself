import { Check } from 'lucide-react'

import { cn } from '@/lib/utils'
import { labelColorClass, labelColorName, labelColors, type LabelColor } from './colors'

export function ColorPicker({ value, onChange }: { value: LabelColor; onChange: (color: LabelColor) => void }) {
  return (
    <div role="radiogroup" aria-label="Colour" className="flex flex-wrap gap-2">
      {labelColors.map((color) => {
        const selected = value === color
        return (
          <button
            key={color}
            type="button"
            role="radio"
            aria-checked={selected}
            aria-label={labelColorName[color]}
            title={labelColorName[color]}
            onClick={() => onChange(color)}
            className={cn(
              'flex size-7 items-center justify-center rounded-full ring-offset-2 ring-offset-card transition-shadow outline-none',
              'focus-visible:ring-2 focus-visible:ring-ring',
              labelColorClass[color],
              selected && 'ring-2 ring-foreground',
            )}
          >
            {selected && <Check className="size-3.5 text-primary-foreground" strokeWidth={3} />}
          </button>
        )
      })}
    </div>
  )
}
