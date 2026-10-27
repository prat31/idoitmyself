import { useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { Loader2 } from 'lucide-react'
import { Controller, useForm, useWatch } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

import { FieldError, FormError, Optional } from '@/components/form/field'
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
import { MultiSelect } from '@/components/ui/multi-select'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { useLabels } from '@/features/labels/api'
import { LabelDot } from '@/features/labels/label-dot'
import { useCreateProcessor, useProcessorKinds, useUpdateProcessor, type Processor } from './api'

const schema = z.object({
  name: z.string().trim().min(1, 'Give it a name').max(100),
  description: z.string().trim().max(2000),
  labelIds: z.array(z.string()).min(1, 'Pick at least one label'),
  kind: z.string().min(1, 'Pick what it does'),
})

type FormValues = z.infer<typeof schema>

/** Adds a processor, or (with `processor`) edits its name, description and labels. The kind is fixed. */
export function ProcessorDialog({ trigger, processor }: { trigger: React.ReactNode; processor?: Processor }) {
  const [open, setOpen] = useState(false)
  const create = useCreateProcessor()
  const update = useUpdateProcessor()
  const mutation = processor ? update : create
  const labels = useLabels()
  const kinds = useProcessorKinds()
  const initial: FormValues = {
    name: processor?.name ?? '',
    description: processor?.description ?? '',
    labelIds: processor?.labels.map((l) => l.id) ?? [],
    kind: processor?.kind ?? '',
  }
  const form = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: initial })
  const { errors } = form.formState
  const kindKey = useWatch({ control: form.control, name: 'kind' })
  const kind = kinds.data?.find((k) => k.key === kindKey)

  const onOpenChange = (next: boolean) => {
    if (mutation.isPending) return
    setOpen(next)
    if (next) form.reset(initial)
    else mutation.reset()
  }

  const onSubmit = form.handleSubmit(({ name, description, labelIds, kind }) => {
    const done = (saved: Processor) => {
      toast.success(`Processor "${saved.name}" ${processor ? 'saved' : 'created'}`)
      onOpenChange(false)
    }
    if (processor) {
      update.mutate(
        { id: processor.id, changes: { name, description: description || null, label_ids: labelIds } },
        { onSuccess: done },
      )
    } else {
      create.mutate({ name, description: description || null, label_ids: labelIds, kind }, { onSuccess: done })
    }
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{processor ? 'Edit processor' : 'Add processor'}</DialogTitle>
          <DialogDescription>
            It runs on every email that gets any of its labels from now on.
            {!processor && " What it does can't change later."}
          </DialogDescription>
        </DialogHeader>

        <form id="processor-form" onSubmit={onSubmit} className="space-y-5" noValidate>
          <div className="space-y-2">
            <Label htmlFor="processor-name">Name</Label>
            <Input id="processor-name" placeholder="Credit card bills" {...form.register('name')} aria-invalid={!!errors.name} />
            <FieldError message={errors.name?.message} />
          </div>

          {!processor && (
            <div className="space-y-2">
              <Label htmlFor="processor-kind">What it does</Label>
              <Controller
                control={form.control}
                name="kind"
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger id="processor-kind" className="w-full" aria-invalid={!!errors.kind}>
                      <SelectValue placeholder={kinds.isPending ? 'Loading…' : 'Pick a processor'} />
                    </SelectTrigger>
                    <SelectContent>
                      {kinds.data?.map((k) => (
                        <SelectItem key={k.key} value={k.key}>
                          {k.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
              {kind && (
                <p className="text-xs text-muted-foreground">
                  {kind.description} Writes {kind.writes.map((d) => d.title.toLowerCase()).join(' and ')}.
                </p>
              )}
              <FieldError message={errors.kind?.message} />
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="processor-labels">Runs on emails labelled</Label>
            <Controller
              control={form.control}
              name="labelIds"
              render={({ field }) => (
                <MultiSelect
                  id="processor-labels"
                  value={field.value}
                  onChange={field.onChange}
                  invalid={!!errors.labelIds}
                  placeholder={labels.isPending ? 'Loading labels…' : 'Pick labels'}
                  searchPlaceholder="Search labels…"
                  options={(labels.data ?? []).map((label) => ({
                    value: label.id,
                    label: label.display_name,
                    icon: <LabelDot color={label.color} />,
                  }))}
                />
              )}
            />
            <p className="text-xs text-muted-foreground">Any of them triggers it, once per email.</p>
            <FieldError message={errors.labelIds?.message} />
          </div>

          <div className="space-y-2">
            <Label htmlFor="processor-description">
              Description <Optional />
            </Label>
            <Textarea id="processor-description" rows={2} {...form.register('description')} />
          </div>

          {mutation.isError && <FormError message={`Couldn't save the processor: ${mutation.error.message}`} />}
        </form>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={mutation.isPending}>
            Cancel
          </Button>
          <Button type="submit" form="processor-form" disabled={mutation.isPending}>
            {mutation.isPending && <Loader2 className="animate-spin" />}
            {processor ? 'Save' : 'Create processor'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
