import { useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { Loader2 } from 'lucide-react'
import { Controller, useForm, useWatch } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

import { FormError } from '@/components/form/field'
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
import { ApiError } from '@/lib/api'
import { useCreateLabel, type Label } from './api'
import { ColorPicker } from './color-picker'
import { labelColors } from './colors'
import { LabelNameField } from './label-name-field'
import { displayNameSchema } from './name'

const schema = z.object({ displayName: displayNameSchema, color: z.enum(labelColors) })

type FormValues = z.infer<typeof schema>

const defaultValues: FormValues = { displayName: '', color: 'gray' }

export function AddLabelDialog({
  trigger,
  initialName = '',
  onCreated,
}: {
  trigger: React.ReactNode
  /** Prefills the name (e.g. what was typed in a label picker). */
  initialName?: string
  onCreated?: (label: Label) => void
}) {
  const [open, setOpen] = useState(false)
  const createLabel = useCreateLabel()
  const form = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues })
  const { errors } = form.formState
  const displayName = useWatch({ control: form.control, name: 'displayName' })

  const onOpenChange = (next: boolean) => {
    if (createLabel.isPending) return
    setOpen(next)
    if (next) form.reset({ displayName: initialName, color: 'gray' })
    else createLabel.reset()
  }

  const onSubmit = form.handleSubmit(({ displayName, color }) => {
    createLabel.mutate({ displayName, color }, {
      onSuccess: (label) => {
        toast.success(`Label "${label.display_name}" created`)
        onCreated?.(label)
        onOpenChange(false)
      },
      onError: (error) => {
        if (error instanceof ApiError && error.status === 409) {
          form.setError('displayName', { message: 'A label with this name already exists' })
        }
      },
    })
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add label</DialogTitle>
          <DialogDescription>Filters add labels to the emails they match. A label is just a unique name.</DialogDescription>
        </DialogHeader>

        <form
          id="add-label-form"
          onSubmit={(event) => {
            event.stopPropagation() // may sit inside another form (the filter editor)
            void onSubmit(event)
          }}
          className="space-y-5"
          noValidate
        >
          <LabelNameField
            id="label-display-name"
            registration={form.register('displayName')}
            value={displayName}
            error={errors.displayName?.message}
          />
          <fieldset className="space-y-2">
            <legend className="mb-2 text-sm font-medium">Colour</legend>
            <Controller
              control={form.control}
              name="color"
              render={({ field }) => <ColorPicker value={field.value} onChange={field.onChange} />}
            />
          </fieldset>
          {createLabel.isError && !(createLabel.error instanceof ApiError && createLabel.error.status === 409) && (
            <FormError message={`Couldn't create the label: ${createLabel.error.message}`} />
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
