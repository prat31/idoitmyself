import { useState } from 'react'
import { CalendarRange, Check } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label as FieldLabel } from '@/components/ui/label'
import { MultiSelect } from '@/components/ui/multi-select'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { useInboxes } from '@/features/inboxes/api'
import { useLabels } from '@/features/labels/api'
import { labelColorClass } from '@/features/labels/colors'
import { formatDate } from '@/lib/format'
import { cn } from '@/lib/utils'
import { RANGE_PRESETS, type RangeId } from './date-filter'

export type FilterState = {
  range: RangeId
  from: string | null
  to: string | null
  inboxId: string | null
  labelIds: string[]
}

function rangeLabel(state: FilterState): string {
  if (state.range === 'custom' && state.from && state.to) {
    return `${formatDate(`${state.from}T00:00`)} – ${formatDate(`${state.to}T00:00`)}`
  }
  const preset = RANGE_PRESETS.find((p) => p.id === state.range)
  return preset ? (preset.days === null ? preset.label : `Last ${preset.label}`) : 'Date range'
}

function DateRangePicker({ state, onChange }: { state: FilterState; onChange: (next: Partial<FilterState>) => void }) {
  const [open, setOpen] = useState(false)
  const [from, setFrom] = useState(state.from ?? '')
  const [to, setTo] = useState(state.to ?? '')
  const customValid = !!from && !!to && from <= to

  return (
    <Popover
      open={open}
      onOpenChange={(next) => {
        setOpen(next)
        if (next) {
          setFrom(state.from ?? '')
          setTo(state.to ?? '')
        }
      }}
    >
      <PopoverTrigger asChild>
        <Button variant="outline" className="justify-start font-normal">
          <CalendarRange className="text-muted-foreground" />
          {rangeLabel(state)}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-64 p-1">
        <ul role="listbox" aria-label="Date range">
          {RANGE_PRESETS.map((preset) => {
            const selected = state.range === preset.id
            return (
              <li key={preset.id}>
                <button
                  type="button"
                  role="option"
                  aria-selected={selected}
                  onClick={() => {
                    onChange({ range: preset.id, from: null, to: null })
                    setOpen(false)
                  }}
                  className="flex w-full items-center justify-between rounded-md px-2.5 py-1.5 text-sm hover:bg-accent/60"
                >
                  {preset.days === null ? preset.label : `Last ${preset.label}`}
                  {selected && <Check className="size-4" strokeWidth={2.5} />}
                </button>
              </li>
            )
          })}
        </ul>
        <div className="mt-1 space-y-2 border-t p-2">
          <p className="text-xs font-medium text-muted-foreground">Custom range</p>
          <div className="grid grid-cols-2 gap-2">
            <div className="space-y-1">
              <FieldLabel htmlFor="ov-from" className="text-[11px] text-muted-foreground">
                From
              </FieldLabel>
              <Input id="ov-from" type="date" className="h-8 px-2 text-xs" value={from} onChange={(e) => setFrom(e.target.value)} />
            </div>
            <div className="space-y-1">
              <FieldLabel htmlFor="ov-to" className="text-[11px] text-muted-foreground">
                To
              </FieldLabel>
              <Input id="ov-to" type="date" className="h-8 px-2 text-xs" value={to} onChange={(e) => setTo(e.target.value)} />
            </div>
          </div>
          <Button
            size="sm"
            className="w-full"
            disabled={!customValid}
            onClick={() => {
              onChange({ range: 'custom', from, to })
              setOpen(false)
            }}
          >
            Apply range
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  )
}

/** One row of filters above everything they scope: date range first, then inbox and labels. */
export function OverviewFilters({ state, onChange }: { state: FilterState; onChange: (next: Partial<FilterState>) => void }) {
  const { data: inboxes = [] } = useInboxes()
  const { data: labels = [] } = useLabels()

  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
      <DateRangePicker state={state} onChange={onChange} />
      <select
        aria-label="Inbox"
        value={state.inboxId ?? ''}
        onChange={(e) => onChange({ inboxId: e.target.value || null })}
        className={cn(
          'h-9 min-w-0 truncate rounded-md border border-input bg-card px-2.5 text-sm shadow-xs outline-none sm:w-52',
          'focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/30',
        )}
      >
        <option value="">All inboxes</option>
        {inboxes.map((inbox) => (
          <option key={inbox.id} value={inbox.id}>
            {inbox.name}
          </option>
        ))}
      </select>
      <div className="sm:w-72">
        <MultiSelect
          mono
          value={state.labelIds}
          onChange={(labelIds) => onChange({ labelIds })}
          placeholder="All labels"
          searchPlaceholder="Search labels"
          options={labels.map((label) => ({
            value: label.id,
            label: label.name,
            icon: <span className={cn('size-2 shrink-0 rounded-full', labelColorClass[label.color])} aria-hidden="true" />,
          }))}
        />
      </div>
    </div>
  )
}
