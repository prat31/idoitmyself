import { useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { Loader2, Pencil } from 'lucide-react'
import { Controller, useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

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
import { Label as FieldLabel } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'
import { useUpdateLabel, type Label } from './api'
import { ColorPicker } from './color-picker'
import { labelColorClass } from './colors'
import { FILTER_CONDITION_HELP, FILTER_CONDITION_PLACEHOLDER } from './filter-condition'
import { FieldError, Optional, ThresholdField } from './label-fields'
import { editableLabelFields } from './label-schema'

const schema = z.object(editableLabelFields)

type FormValues = z.infer<typeof schema>

function valuesFor(label: Label): FormValues {
  return {
    description: label.description ?? '',
    color: label.color,
    filterCondition: label.filter_condition ?? '',
    matchThreshold: label.match_threshold,
  }
}

/** Edits a label's description, colour and filter condition. The name is immutable. */
export function EditLabelDialog({ label }: { label: Label }) {
  const [open, setOpen] = useState(false)
  const update = useUpdateLabel()
  const form = useForm<FormValues>({ resolver: zodResolver(schema), values: valuesFor(label) })
  const { errors } = form.formState

  const onOpenChange = (next: boolean) => {
    if (update.isPending) return
    setOpen(next)
    if (!next) {
      form.reset(valuesFor(label))
      update.reset()
    }
  }

  const onSubmit = form.handleSubmit(({ description, color, filterCondition, matchThreshold }) => {
    update.mutate(
      {
        id: label.id,
        changes: {
          description: description || null,
          color,
          filter_condition: filterCondition || null,
          match_threshold: matchThreshold,
        },
      },
      {
        onSuccess: () => {
          toast.success(`Label "${label.name}" updated`)
          onOpenChange(false)
        },
      },
    )
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="size-8 text-muted-foreground hover:text-foreground"
          aria-label={`Edit label ${label.name}`}
        >
          <Pencil />
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit label</DialogTitle>
          <DialogDescription>Update the description, filter condition, threshold or colour.</DialogDescription>
        </DialogHeader>

        <form id="edit-label-form" onSubmit={onSubmit} className="space-y-5" noValidate>
          <div className="flex items-center gap-2 rounded-lg border bg-muted/40 px-3 py-2.5 text-sm">
            <span className={cn('size-2.5 shrink-0 rounded-full', labelColorClass[label.color])} aria-hidden="true" />
            <code className="truncate font-mono font-medium">{label.name}</code>
            <span className="ml-auto shrink-0 text-xs text-muted-foreground">Name can't be changed</span>
          </div>

          <div className="space-y-2">
            <FieldLabel htmlFor="edit-label-description">
              Description <Optional />
            </FieldLabel>
            <Textarea
              id="edit-label-description"
              placeholder="What belongs under this label"
              rows={2}
              aria-invalid={!!errors.description}
              {...form.register('description')}
            />
            <FieldError message={errors.description?.message} />
          </div>

          <div className="space-y-2">
            <FieldLabel htmlFor="edit-label-filter-condition">
              Filter condition <Optional />
            </FieldLabel>
            <Textarea
              id="edit-label-filter-condition"
              placeholder={FILTER_CONDITION_PLACEHOLDER}
              rows={4}
              aria-invalid={!!errors.filterCondition}
              aria-describedby="edit-label-filter-condition-help"
              {...form.register('filterCondition')}
            />
            {errors.filterCondition ? (
              <FieldError message={errors.filterCondition.message} />
            ) : (
              <p id="edit-label-filter-condition-help" className="text-xs text-muted-foreground">
                {FILTER_CONDITION_HELP}
              </p>
            )}
          </div>

          <ThresholdField
            id="edit-label-threshold"
            registration={form.register('matchThreshold', { valueAsNumber: true })}
            error={errors.matchThreshold?.message}
          />

          <fieldset className="space-y-2">
            <legend className="mb-2 text-sm font-medium">Colour</legend>
            <Controller
              control={form.control}
              name="color"
              render={({ field }) => <ColorPicker value={field.value} onChange={field.onChange} />}
            />
          </fieldset>

          {update.isError && (
            <p className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
              Couldn't save: {update.error.message}
            </p>
          )}
        </form>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={update.isPending}>
            Cancel
          </Button>
          <Button type="submit" form="edit-label-form" disabled={update.isPending || !form.formState.isDirty}>
            {update.isPending && <Loader2 className="animate-spin" />}
            Save changes
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
