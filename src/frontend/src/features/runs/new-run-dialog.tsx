import { useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { Loader2 } from 'lucide-react'
import { Controller, useForm, useWatch } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
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
import { useInboxes } from '@/features/inboxes/api'
import { useLabels } from '@/features/labels/api'
import { labelColorClass } from '@/features/labels/colors'
import { cn } from '@/lib/utils'
import { useCreateAdhocRun, useRunCoverage } from './api'
import { CoverageNotice } from './coverage-notice'
import { DATE_PRESETS, lastDays, toDateInput, toWindow } from './date-range'

const schema = z
  .object({
    name: z.string().trim().min(1, 'Give the run a name').max(100, 'Keep the name under 100 characters'),
    labelIds: z.array(z.string()).min(1, 'Pick at least one label'),
    from: z.string().min(1, 'Pick a start date'),
    to: z.string().min(1, 'Pick an end date'),
    inboxIds: z.array(z.string()).min(1, 'Pick at least one inbox'),
    reclassify: z.boolean(),
  })
  .refine((v) => !v.from || !v.to || v.from <= v.to, { path: ['to'], message: 'End date must be on or after the start' })

type FormValues = z.infer<typeof schema>

function FieldError({ message }: { message?: string }) {
  if (!message) return null
  return <p className="text-xs text-destructive">{message}</p>
}

function toggle(list: string[], id: string, on: boolean) {
  return on ? [...list, id] : list.filter((x) => x !== id)
}

function SectionTitle({ children, aside }: { children: React.ReactNode; aside?: React.ReactNode }) {
  return (
    <div className="mb-2 flex items-center justify-between gap-2">
      <legend className="text-sm font-medium">{children}</legend>
      {aside}
    </div>
  )
}

export function NewRunDialog({ trigger }: { trigger: React.ReactNode }) {
  const [open, setOpen] = useState(false)
  const [today] = useState(() => toDateInput(new Date()))
  const { data: labels = [] } = useLabels()
  const { data: inboxes = [] } = useInboxes()
  const createRun = useCreateAdhocRun()

  const usable = labels.filter((label) => label.filter_condition)
  const unusable = labels.filter((label) => !label.filter_condition)

  const freshValues = (): FormValues => ({
    name: '',
    labelIds: [],
    ...lastDays(7),
    inboxIds: inboxes.map((i) => i.id),
    reclassify: false,
  })
  const form = useForm<FormValues>({ resolver: zodResolver(schema), values: freshValues() })
  const { errors } = form.formState
  const [from, to, watchedLabels, watchedInboxes, reclassify] = useWatch({
    control: form.control,
    name: ['from', 'to', 'labelIds', 'inboxIds', 'reclassify'],
  })
  const coverageRequest =
    open && watchedLabels.length && watchedInboxes.length && from && to && from <= to
      ? { label_ids: watchedLabels, inbox_ids: watchedInboxes, ...toWindow(from, to) }
      : null
  const { data: coverage } = useRunCoverage(coverageRequest)

  const onOpenChange = (next: boolean) => {
    if (createRun.isPending) return
    setOpen(next)
    if (!next) {
      form.reset(freshValues())
      createRun.reset()
    }
  }

  const onSubmit = form.handleSubmit(({ name, labelIds, from, to, inboxIds, reclassify }) => {
    createRun.mutate(
      { name, label_ids: labelIds, inbox_ids: inboxIds, ...toWindow(from, to), reclassify },
      {
        onSuccess: (run) => {
          if (run.status === 'failed') toast.error("The run couldn't be queued", { description: run.error ?? undefined })
          else toast.success('Run queued', { description: 'It will appear below and update as it progresses.' })
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
          <DialogTitle>New ad hoc run</DialogTitle>
          <DialogDescription>
            Fetch emails in a date range and ask the model which of the selected labels apply.
          </DialogDescription>
        </DialogHeader>

        <form id="new-run-form" onSubmit={onSubmit} className="space-y-6" noValidate>
          <div className="space-y-2">
            <FieldLabel htmlFor="run-name">Name</FieldLabel>
            <Input
              id="run-name"
              placeholder="e.g. September bills"
              autoComplete="off"
              aria-invalid={!!errors.name}
              {...form.register('name')}
            />
            <FieldError message={errors.name?.message} />
          </div>

          <div className="space-y-2">
            <FieldLabel htmlFor="run-labels">Labels</FieldLabel>
            <Controller
              control={form.control}
              name="labelIds"
              render={({ field }) => (
                <MultiSelect
                  id="run-labels"
                  mono
                  value={field.value}
                  onChange={field.onChange}
                  invalid={!!errors.labelIds}
                  placeholder={usable.length ? 'Select labels to classify with' : 'No labels with a filter condition yet'}
                  searchPlaceholder="Search labels"
                  options={[...usable, ...unusable].map((label) => ({
                    value: label.id,
                    label: label.name,
                    icon: (
                      <span
                        className={cn('size-2 shrink-0 rounded-full', labelColorClass[label.color])}
                        aria-hidden="true"
                      />
                    ),
                    description: label.filter_condition ?? undefined,
                    disabled: !label.filter_condition,
                    disabledReason: 'No filter condition — add one on the Labels page',
                  }))}
                />
              )}
            />
            <FieldError message={errors.labelIds?.message} />
          </div>

          <fieldset>
            <SectionTitle>Timeline</SectionTitle>
            <div className="mb-3 flex flex-wrap gap-1.5">
              {DATE_PRESETS.map((preset) => {
                const range = lastDays(preset.days)
                const active = range.from === from && range.to === to
                return (
                  <Button
                    key={preset.label}
                    type="button"
                    size="sm"
                    variant={active ? 'default' : 'outline'}
                    className="h-7 px-2.5 text-xs"
                    onClick={() => {
                      form.setValue('from', range.from, { shouldValidate: true })
                      form.setValue('to', range.to, { shouldValidate: true })
                    }}
                  >
                    {preset.days === 1 ? preset.label : `Last ${preset.label}`}
                  </Button>
                )
              })}
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <FieldLabel htmlFor="run-from" className="text-xs text-muted-foreground">
                  From
                </FieldLabel>
                <Input id="run-from" type="date" max={today} aria-invalid={!!errors.from} {...form.register('from')} />
              </div>
              <div className="space-y-1.5">
                <FieldLabel htmlFor="run-to" className="text-xs text-muted-foreground">
                  To (inclusive)
                </FieldLabel>
                <Input id="run-to" type="date" max={today} aria-invalid={!!errors.to} {...form.register('to')} />
              </div>
            </div>
            <FieldError message={errors.from?.message ?? errors.to?.message} />
          </fieldset>

          <fieldset>
            <SectionTitle>Inboxes</SectionTitle>
            <Controller
              control={form.control}
              name="inboxIds"
              render={({ field }) => (
                <div className="divide-y rounded-lg border">
                  {inboxes.map((inbox) => (
                    <label key={inbox.id} className="flex cursor-pointer items-center gap-3 px-3 py-2.5 hover:bg-accent/50">
                      <Checkbox
                        checked={field.value.includes(inbox.id)}
                        onCheckedChange={(on) => field.onChange(toggle(field.value, inbox.id, on === true))}
                      />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-medium">{inbox.name}</span>
                        <span className="block truncate text-xs text-muted-foreground">{inbox.email_address}</span>
                      </span>
                    </label>
                  ))}
                </div>
              )}
            />
            <FieldError message={errors.inboxIds?.message} />
          </fieldset>

          {coverageRequest && coverage && (
            <CoverageNotice
              coverage={coverage}
              reclassify={reclassify}
              onReclassifyChange={(value) => form.setValue('reclassify', value)}
            />
          )}

          {createRun.isError && (
            <p className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
              Couldn't start the run: {createRun.error.message}
            </p>
          )}
        </form>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={createRun.isPending}>
            Cancel
          </Button>
          <Button type="submit" form="new-run-form" disabled={createRun.isPending || usable.length === 0}>
            {createRun.isPending && <Loader2 className="animate-spin" />}
            Start run
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
