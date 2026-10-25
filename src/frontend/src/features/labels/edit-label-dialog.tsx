import { useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { Loader2, Pencil } from 'lucide-react'
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
import { useUpdateLabel, type Label } from './api'
import { ColorPicker } from './color-picker'
import { labelColors } from './colors'
import { LabelNameField } from './label-name-field'
import { displayNameSchema } from './name'

const schema = z.object({ displayName: displayNameSchema, color: z.enum(labelColors) })

type FormValues = z.infer<typeof schema>

/** Edits a label's display name and colour. Its normalised name never changes. */
export function EditLabelDialog({ label }: { label: Label }) {
  const [open, setOpen] = useState(false)
  const update = useUpdateLabel()
  const current: FormValues = { displayName: label.display_name, color: label.color }
  const form = useForm<FormValues>({ resolver: zodResolver(schema), values: current })
  const { errors } = form.formState
  const displayName = useWatch({ control: form.control, name: 'displayName' })

  const onOpenChange = (next: boolean) => {
    if (update.isPending) return
    setOpen(next)
    if (!next) {
      form.reset(current)
      update.reset()
    }
  }

  const onSubmit = form.handleSubmit(({ displayName, color }) => {
    update.mutate(
      { id: label.id, changes: { display_name: displayName, color } },
      {
        onSuccess: (updated) => {
          toast.success(`Label "${updated.display_name}" saved`)
          onOpenChange(false)
        },
      },
    )
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="icon" className="size-8 text-muted-foreground" aria-label={`Edit label ${label.display_name}`}>
          <Pencil />
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit label</DialogTitle>
          <DialogDescription>Change how the label is shown: its name and colour. Its normalised name is fixed.</DialogDescription>
        </DialogHeader>

        <form id="edit-label-form" onSubmit={onSubmit} className="space-y-5" noValidate>
          <LabelNameField
            id="edit-label-display-name"
            registration={form.register('displayName')}
            value={displayName}
            error={errors.displayName?.message}
            fixedName={label.name}
          />
          <fieldset className="space-y-2">
            <legend className="mb-2 text-sm font-medium">Colour</legend>
            <Controller
              control={form.control}
              name="color"
              render={({ field }) => <ColorPicker value={field.value} onChange={field.onChange} />}
            />
          </fieldset>
          {update.isError && <FormError message={`Couldn't save the label: ${update.error.message}`} />}
        </form>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={update.isPending}>
            Cancel
          </Button>
          <Button type="submit" form="edit-label-form" disabled={update.isPending}>
            {update.isPending && <Loader2 className="animate-spin" />}
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
