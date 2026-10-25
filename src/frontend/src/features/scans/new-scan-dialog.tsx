import { useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { Info, Loader2 } from 'lucide-react'
import { Controller, useForm, useWatch } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

import { FieldError, FormError } from '@/components/form/field'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label as FieldLabel } from '@/components/ui/label'
import { MultiSelect } from '@/components/ui/multi-select'
import { useFilters, type Filter } from '@/features/filters/api'
import { providerById } from '@/features/inboxes/providers'
import { formatDate } from '@/lib/format'
import { useCreateAdhocScans, type Scan } from './api'
import { RANGE_PRESETS, lastDayOf, presetRange, toDateInput, toWindow } from './date-range'

const CUSTOM = 'custom'

const schema = z
  .object({
    filterIds: z.array(z.string()).min(1, 'Pick at least one filter'),
    /** A preset's label, or "custom" to use the From/To dates. */
    range: z.string(),
    from: z.string().min(1, 'Pick a start date'),
    to: z.string().min(1, 'Pick an end date'),
  })
  .refine((v) => !v.from || !v.to || v.from <= v.to, { path: ['to'], message: 'End date must be on or after the start' })

type FormValues = z.infer<typeof schema>

function scopeSummary(filter: Filter): string {
  const parts = [
    ...filter.scope.mailbox_types.map((type) => `All ${providerById[type].label}`),
    ...filter.scope.inboxes.map((inbox) => inbox.name),
  ]
  return `Adds ${filter.label.display_name} · ${parts.join(', ')}`
}

function queuedMessage(scans: Scan[]): string {
  return scans
    .map((scan) => `${scan.inbox_name}: ${formatDate(scan.window_start!)} – ${formatDate(lastDayOf(scan.window_end!))}`)
    .join('\n')
}

/** Requests ad hoc scans: chosen active filters over a past date range, in every inbox they cover. */
export function NewScanDialog({ trigger }: { trigger: React.ReactNode }) {
  const [open, setOpen] = useState(false)
  const [today] = useState(() => toDateInput(new Date()))
  const { data: filters = [] } = useFilters()
  const create = useCreateAdhocScans()
  const active = filters.filter((f) => f.status === 'active')

  const freshValues = (): FormValues => ({
    filterIds: [],
    range: RANGE_PRESETS[2].label,
    ...presetRange(RANGE_PRESETS[2]),
  })
  const form = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: freshValues() })
  const { errors } = form.formState
  const range = useWatch({ control: form.control, name: 'range' })
  const custom = range === CUSTOM

  const choose = (next: string) => {
    form.setValue('range', next)
    const preset = RANGE_PRESETS.find((p) => p.label === next)
    if (preset) {
      // Presets fill the (locked) dates so the range is visible; Custom keeps them to edit.
      const dates = presetRange(preset)
      form.setValue('from', dates.from, { shouldValidate: true })
      form.setValue('to', dates.to, { shouldValidate: true })
    }
  }

  const onOpenChange = (next: boolean) => {
    if (create.isPending) return
    setOpen(next)
    if (!next) {
      form.reset(freshValues())
      create.reset()
    }
  }

  const onSubmit = form.handleSubmit(({ filterIds, range, from, to }) => {
    // A preset is resolved at submit time, so it's relative to now even if the dialog sat open.
    const preset = RANGE_PRESETS.find((p) => p.label === range)
    const dates = preset ? presetRange(preset) : { from, to }
    create.mutate(
      { filter_ids: filterIds, ...toWindow(dates.from, dates.to) },
      {
        onSuccess: (scans) => {
          toast.success(scans.length === 1 ? 'Ad hoc scan queued' : `${scans.length} ad hoc scans queued`, {
            description: queuedMessage(scans),
          })
          onOpenChange(false)
        },
      },
    )
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>New scan</DialogTitle>
          <DialogDescription>
            Run filters over past email. Each inbox their scopes cover gets its own scan.
          </DialogDescription>
        </DialogHeader>

        <form id="new-scan-form" onSubmit={onSubmit} className="space-y-6" noValidate>
          <div className="space-y-2">
            <FieldLabel htmlFor="scan-filters">Filters</FieldLabel>
            <Controller
              control={form.control}
              name="filterIds"
              render={({ field }) => (
                <MultiSelect
                  id="scan-filters"
                  value={field.value}
                  onChange={field.onChange}
                  invalid={!!errors.filterIds}
                  placeholder={active.length ? 'Select filters to run' : 'No active filters yet'}
                  searchPlaceholder="Search filters"
                  emptyText="No active filters match"
                  options={active.map((filter) => ({
                    value: filter.id,
                    label: filter.name,
                    description: scopeSummary(filter),
                  }))}
                />
              )}
            />
            <FieldError message={errors.filterIds?.message} />
          </div>

          <fieldset>
            <legend className="mb-2 text-sm font-medium">Sent between</legend>
            <div className="mb-3 flex flex-wrap gap-1.5">
              {[...RANGE_PRESETS.map((p) => p.label), CUSTOM].map((option) => (
                <Button
                  key={option}
                  type="button"
                  size="sm"
                  variant={range === option ? 'default' : 'outline'}
                  aria-pressed={range === option}
                  className="h-7 px-2.5 text-xs"
                  onClick={() => choose(option)}
                >
                  {option === CUSTOM ? 'Custom' : option}
                </Button>
              ))}
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <FieldLabel htmlFor="scan-from" className="text-xs text-muted-foreground">
                  From
                </FieldLabel>
                <Input
                  id="scan-from"
                  type="date"
                  max={today}
                  disabled={!custom}
                  aria-invalid={!!errors.from}
                  {...form.register('from')}
                />
              </div>
              <div className="space-y-1.5">
                <FieldLabel htmlFor="scan-to" className="text-xs text-muted-foreground">
                  To (inclusive)
                </FieldLabel>
                <Input
                  id="scan-to"
                  type="date"
                  max={today}
                  disabled={!custom}
                  aria-invalid={!!errors.to}
                  {...form.register('to')}
                />
              </div>
            </div>
            <FieldError message={errors.from?.message ?? errors.to?.message} />
          </fieldset>

          <p className="flex items-start gap-2 rounded-lg border border-dashed px-3 py-2.5 text-xs text-muted-foreground">
            <Info className="mt-px size-3.5 shrink-0" aria-hidden="true" />
            <span>
              Only emails no scan has stored yet are read. Each inbox's range stops where its scheduled scans take
              over, so new mail always goes through every active filter first.
            </span>
          </p>

          {create.isError && <FormError message={`Couldn't start the scan: ${create.error.message}`} />}
        </form>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={create.isPending}>
            Cancel
          </Button>
          <Button type="submit" form="new-scan-form" disabled={create.isPending || active.length === 0}>
            {create.isPending && <Loader2 className="animate-spin" />}
            Start scan
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
