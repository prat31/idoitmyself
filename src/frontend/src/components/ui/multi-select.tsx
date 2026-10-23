import { useMemo, useState, type ReactNode } from 'react'
import { Check, ChevronsUpDown, Search, X } from 'lucide-react'

import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { cn } from '@/lib/utils'

export type MultiSelectOption = {
  value: string
  label: string
  /** Optional leading visual (e.g. a colour dot) and secondary line. */
  icon?: ReactNode
  description?: string
  disabled?: boolean
  disabledReason?: string
}

type MultiSelectProps = {
  options: MultiSelectOption[]
  value: string[]
  onChange: (value: string[]) => void
  placeholder?: string
  searchPlaceholder?: string
  emptyText?: string
  id?: string
  invalid?: boolean
  /** Render selected items in a monospace font (e.g. label names). */
  mono?: boolean
}

/** Dropdown with checkable options, a search box, and the selection shown as removable chips. */
export function MultiSelect({
  options,
  value,
  onChange,
  placeholder = 'Select…',
  searchPlaceholder = 'Search…',
  emptyText = 'No matches',
  id,
  invalid,
  mono,
}: MultiSelectProps) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const selected = useMemo(() => options.filter((o) => value.includes(o.value)), [options, value])
  const visible = options.filter((o) => o.label.toLowerCase().includes(query.trim().toLowerCase()))
  const selectable = options.filter((o) => !o.disabled)

  const toggle = (option: MultiSelectOption) => {
    if (option.disabled) return
    onChange(value.includes(option.value) ? value.filter((v) => v !== option.value) : [...value, option.value])
  }

  return (
    <Popover
      open={open}
      onOpenChange={(next) => {
        setOpen(next)
        if (!next) setQuery('')
      }}
    >
      <PopoverTrigger asChild>
        <button
          id={id}
          type="button"
          role="combobox"
          aria-expanded={open}
          aria-invalid={invalid || undefined}
          className={cn(
            'flex min-h-9 w-full items-center gap-2 rounded-md border border-input bg-card px-2.5 py-1.5 text-left text-sm shadow-xs transition-[color,box-shadow] outline-none',
            'focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/30',
            'aria-invalid:border-destructive aria-invalid:ring-destructive/20',
          )}
        >
          <span className="flex min-w-0 flex-1 flex-wrap gap-1.5">
            {selected.length === 0 ? (
              <span className="px-0.5 text-muted-foreground/70">{placeholder}</span>
            ) : (
              selected.map((option) => (
                <span
                  key={option.value}
                  className="inline-flex max-w-full items-center gap-1.5 rounded-md bg-secondary py-0.5 pl-2 pr-1 text-xs font-medium text-secondary-foreground"
                >
                  {option.icon}
                  <span className={cn('truncate', mono && 'font-mono')}>{option.label}</span>
                  <span
                    role="button"
                    tabIndex={-1}
                    aria-label={`Remove ${option.label}`}
                    className="rounded-sm p-0.5 text-muted-foreground hover:bg-accent hover:text-foreground"
                    onPointerDown={(e) => e.stopPropagation()}
                    onClick={(e) => {
                      e.stopPropagation()
                      toggle(option)
                    }}
                  >
                    <X className="size-3" />
                  </span>
                </span>
              ))
            )}
          </span>
          <ChevronsUpDown className="size-4 shrink-0 text-muted-foreground" />
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-(--radix-popover-trigger-width) p-0">
        <div className="flex items-center gap-2 border-b px-3">
          <Search className="size-4 shrink-0 text-muted-foreground" />
          <input
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={searchPlaceholder}
            className="h-9 flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground/70"
          />
          {selectable.length > 1 && (
            <button
              type="button"
              className="shrink-0 text-xs font-medium text-muted-foreground hover:text-foreground"
              onClick={() => onChange(value.length === selectable.length ? [] : selectable.map((o) => o.value))}
            >
              {value.length === selectable.length ? 'Clear' : 'All'}
            </button>
          )}
        </div>
        <ul role="listbox" aria-multiselectable="true" className="max-h-64 overflow-y-auto p-1">
          {visible.length === 0 && <li className="px-2 py-6 text-center text-sm text-muted-foreground">{emptyText}</li>}
          {visible.map((option) => {
            const isSelected = value.includes(option.value)
            return (
              <li
                key={option.value}
                role="option"
                aria-selected={isSelected}
                aria-disabled={option.disabled || undefined}
                tabIndex={option.disabled ? -1 : 0}
                onClick={() => toggle(option)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    toggle(option)
                  }
                }}
                className={cn(
                  'flex cursor-pointer items-start gap-2.5 rounded-md px-2 py-2 outline-none',
                  'hover:bg-accent focus-visible:bg-accent',
                  option.disabled && 'cursor-not-allowed opacity-50 hover:bg-transparent',
                )}
              >
                <span
                  className={cn(
                    'mt-0.5 flex size-4 shrink-0 items-center justify-center rounded-[4px] border border-input',
                    isSelected && 'border-primary bg-primary text-primary-foreground',
                  )}
                >
                  {isSelected && <Check className="size-3" strokeWidth={3} />}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex items-center gap-2">
                    {option.icon}
                    <span className={cn('truncate text-sm font-medium', mono && 'font-mono')}>{option.label}</span>
                  </span>
                  {(option.disabled ? option.disabledReason : option.description) && (
                    <span className="mt-0.5 line-clamp-1 text-xs text-muted-foreground">
                      {option.disabled ? option.disabledReason : option.description}
                    </span>
                  )}
                </span>
              </li>
            )
          })}
        </ul>
      </PopoverContent>
    </Popover>
  )
}
