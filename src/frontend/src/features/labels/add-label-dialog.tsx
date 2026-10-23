import { useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { Loader2 } from 'lucide-react'
import { Controller, useForm, useWatch } from 'react-hook-form'
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
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { ApiError } from '@/lib/api'
import { cn } from '@/lib/utils'
import { useCreateLabel } from './api'
import { ColorPicker } from './color-picker'
import { labelColorClass } from './colors'
import { FILTER_CONDITION_HELP, FILTER_CONDITION_PLACEHOLDER } from './filter-condition'
import { FieldError, Optional, ThresholdField } from './label-fields'
import { DEFAULT_MATCH_THRESHOLD, editableLabelFields } from './label-schema'
import { LABEL_NAME_MAX, normalizeLabelName } from './name'

const schema = z.object({
  name: z
    .string()
    .refine((raw) => normalizeLabelName(raw).length > 0, 'Give the label a name with at least one letter or digit')
    .refine((raw) => normalizeLabelName(raw).length <= LABEL_NAME_MAX, 'Keep the name under 50 characters'),
  ...editableLabelFields,
})

type FormValues = z.infer<typeof schema>

const defaultValues: FormValues = {
  name: '',
  description: '',
  color: 'gray',
  filterCondition: '',
  matchThreshold: DEFAULT_MATCH_THRESHOLD,
}

export function AddLabelDialog({ trigger }: { trigger: React.ReactNode }) {
  const [open, setOpen] = useState(false)
  const createLabel = useCreateLabel()
  const form = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues })
  const { errors } = form.formState

  const onOpenChange = (next: boolean) => {
    if (createLabel.isPending) return
    setOpen(next)
    if (!next) {
      form.reset(defaultValues)
      createLabel.reset()
    }
  }

  const onSubmit = form.handleSubmit(({ name, description, color, filterCondition, matchThreshold }) => {
    createLabel.mutate(
      {
        name,
        description: description || null,
        color,
        filter_condition: filterCondition || null,
        match_threshold: matchThreshold,
      },
      {
        onSuccess: (label) => {
          toast.success(`Label "${label.name}" created`)
          onOpenChange(false)
        },
        onError: (error) => {
          if (error instanceof ApiError && error.status === 409) {
            form.setError('name', { message: 'A label with this name already exists' })
          }
        },
      },
    )
  })

  const selectedColor = useWatch({ control: form.control, name: 'color' })
  const normalizedName = normalizeLabelName(useWatch({ control: form.control, name: 'name' }))

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add label</DialogTitle>
          <DialogDescription>
            Labels classify your email across every inbox. Names are unique and can't be changed later.
          </DialogDescription>
        </DialogHeader>

        <form id="add-label-form" onSubmit={onSubmit} className="space-y-5" noValidate>
          <div className="space-y-2">
            <Label htmlFor="label-name">Name</Label>
            <Input
              id="label-name"
              placeholder="e.g. Credit card bill"
              autoComplete="off"
              aria-invalid={!!errors.name}
              aria-describedby="label-name-help"
              {...form.register('name')}
            />
            {errors.name ? (
              <FieldError message={errors.name.message} />
            ) : (
              <p id="label-name-help" className="text-xs text-muted-foreground">
                {normalizedName ? (
                  <>
                    Saved as <code className="rounded bg-muted px-1 py-0.5 font-mono text-foreground">{normalizedName}</code>
                  </>
                ) : (
                  'Stored in lowercase, with spaces and symbols turned into underscores.'
                )}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="label-description">
              Description <Optional />
            </Label>
            <Textarea
              id="label-description"
              placeholder="What belongs under this label"
              rows={2}
              aria-invalid={!!errors.description}
              {...form.register('description')}
            />
            <FieldError message={errors.description?.message} />
          </div>

          <div className="space-y-2">
            <Label htmlFor="label-filter-condition">
              Filter condition <Optional />
            </Label>
            <Textarea
              id="label-filter-condition"
              placeholder={FILTER_CONDITION_PLACEHOLDER}
              rows={3}
              aria-invalid={!!errors.filterCondition}
              aria-describedby="label-filter-condition-help"
              {...form.register('filterCondition')}
            />
            <p id="label-filter-condition-help" className="text-xs text-muted-foreground">
              {FILTER_CONDITION_HELP} You can add or change it later.
            </p>
            <FieldError message={errors.filterCondition?.message} />
          </div>

          <ThresholdField
            id="label-threshold"
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

          <div className="flex items-center gap-2 rounded-lg border border-dashed px-3 py-2.5 text-sm">
            <span className="text-muted-foreground">Preview</span>
            <span className="ml-auto inline-flex items-center gap-1.5 rounded-md border bg-card px-2 py-0.5 text-xs font-medium">
              <span className={cn('size-2 rounded-full', labelColorClass[selectedColor])} aria-hidden="true" />
              {normalizedName || 'label_name'}
            </span>
          </div>

          {createLabel.isError && !(createLabel.error instanceof ApiError && createLabel.error.status === 409) && (
            <p className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
              Couldn't create the label: {createLabel.error.message}
            </p>
          )}
        </form>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={createLabel.isPending}>
            Cancel
          </Button>
          <Button type="submit" form="add-label-form" disabled={createLabel.isPending}>
            {createLabel.isPending && <Loader2 className="animate-spin" />}
            Create label
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
