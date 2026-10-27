import { useState } from 'react'
import { KeyRound, Loader2 } from 'lucide-react'
import { toast } from 'sonner'

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
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useSaveInput } from './api'

/** Asks for something a processor needs (e.g. a PDF password). Saving it runs the waiting emails again. */
export function InputDialog({
  name,
  scope,
  prompt,
  secret = true,
  wrong,
}: {
  name: string
  scope: string
  /** What to ask, e.g. "PDF password for estatement@yes.bank.in (Credit card bill)". */
  prompt: string
  /** Typed hidden (passwords and the like). */
  secret?: boolean
  /** A saved value didn't work. */
  wrong?: boolean
}) {
  const [open, setOpen] = useState(false)
  const [value, setValue] = useState('')
  const save = useSaveInput()

  const onOpenChange = (next: boolean) => {
    if (save.isPending) return
    setOpen(next)
    setValue('')
    save.reset()
  }

  const onSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    if (!value) return
    save.mutate(
      { name, scope, value },
      {
        onSuccess: ({ queued }) => {
          toast.success('Saved', {
            description: queued === 1 ? 'Running its email again.' : `Running its ${queued} emails again.`,
          })
          onOpenChange(false)
        },
      },
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <KeyRound />
          {wrong ? 'Change' : 'Enter'}
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{prompt}</DialogTitle>
          <DialogDescription asChild>
            <div className="space-y-1">
              <p>A processor needs this to read these emails. It's stored encrypted and only used for them.</p>
              {wrong && <p className="text-warning">The saved one didn't work on the latest email.</p>}
            </div>
          </DialogDescription>
        </DialogHeader>
        <form id="input-form" onSubmit={onSubmit} className="space-y-4" noValidate>
          <div className="space-y-2">
            <Label htmlFor="input-value">{secret ? 'Password' : 'Value'}</Label>
            <Input
              id="input-value"
              type={secret ? 'password' : 'text'}
              autoComplete="off"
              value={value}
              onChange={(event) => setValue(event.target.value)}
              autoFocus
            />
          </div>
          {save.isError && <FormError message={`Couldn't save it: ${save.error.message}`} />}
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={save.isPending}>
            Cancel
          </Button>
          <Button type="submit" form="input-form" disabled={save.isPending || !value}>
            {save.isPending && <Loader2 className="animate-spin" />}
            Save and run again
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
