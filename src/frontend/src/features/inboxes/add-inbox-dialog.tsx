import { useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { Check, Loader2 } from 'lucide-react'
import { Controller, useForm } from 'react-hook-form'
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
import { TagInput } from '@/components/ui/tag-input'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'
import { useStartGmailAuthorization, useTags } from './api'
import { providers } from './providers'

// Limits mirror the backend's InboxDraft validation.
const schema = z.object({
  provider: z.enum(['gmail']),
  name: z.string().trim().min(1, 'Give this inbox a name').max(100, 'Keep the name under 100 characters'),
  tags: z.array(z.string().trim().min(1).max(50)).max(20, 'Up to 20 tags'),
  notes: z.string().trim().max(2000, 'Keep notes under 2000 characters'),
})

type FormValues = z.infer<typeof schema>

const defaultValues: FormValues = { provider: 'gmail', name: '', tags: [], notes: '' }

function FieldError({ message }: { message?: string }) {
  if (!message) return null
  return <p className="text-xs text-destructive">{message}</p>
}

export function AddInboxDialog({ trigger }: { trigger: React.ReactNode }) {
  const [open, setOpen] = useState(false)
  const { data: existingTags = [] } = useTags()
  const authorize = useStartGmailAuthorization()

  const form = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues })
  const { errors } = form.formState
  const isRedirecting = authorize.isPending || authorize.isSuccess

  const onSubmit = form.handleSubmit(({ name, tags, notes }) => {
    authorize.mutate({ name, tags, notes: notes || null })
  })

  const onOpenChange = (next: boolean) => {
    if (isRedirecting) return
    setOpen(next)
    if (!next) {
      form.reset(defaultValues)
      authorize.reset()
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add inbox</DialogTitle>
          <DialogDescription>Connect an email account. You'll sign in with the provider next.</DialogDescription>
        </DialogHeader>

        <form id="add-inbox-form" onSubmit={onSubmit} className="space-y-5" noValidate>
          <fieldset className="space-y-2">
            <legend className="mb-2 text-sm font-medium">Type</legend>
            <Controller
              control={form.control}
              name="provider"
              render={({ field }) => (
                <div role="radiogroup" className="grid gap-2">
                  {providers.map((provider) => {
                    const selected = field.value === provider.id
                    const Icon = provider.icon
                    return (
                      <button
                        key={provider.id}
                        type="button"
                        role="radio"
                        aria-checked={selected}
                        onClick={() => field.onChange(provider.id)}
                        className={cn(
                          'flex items-center gap-3 rounded-lg border bg-card p-3 text-left transition-colors outline-none',
                          'focus-visible:ring-[3px] focus-visible:ring-ring/50',
                          selected ? 'border-primary ring-1 ring-primary' : 'hover:bg-accent',
                        )}
                      >
                        <span className="flex size-9 items-center justify-center rounded-md bg-secondary">
                          <Icon className="size-[18px]" strokeWidth={1.75} />
                        </span>
                        <span className="flex-1">
                          <span className="block text-sm font-medium">{provider.label}</span>
                          <span className="block text-xs text-muted-foreground">{provider.description}</span>
                        </span>
                        <span
                          className={cn(
                            'flex size-5 items-center justify-center rounded-full border',
                            selected && 'border-primary bg-primary text-primary-foreground',
                          )}
                        >
                          {selected && <Check className="size-3" strokeWidth={3} />}
                        </span>
                      </button>
                    )
                  })}
                </div>
              )}
            />
          </fieldset>

          <div className="space-y-2">
            <Label htmlFor="inbox-name">Name</Label>
            <Input
              id="inbox-name"
              placeholder="e.g. Personal"
              autoComplete="off"
              aria-invalid={!!errors.name}
              {...form.register('name')}
            />
            <FieldError message={errors.name?.message} />
          </div>

          <div className="space-y-2">
            <Label htmlFor="inbox-tags">
              Tags <span className="font-normal text-muted-foreground">(optional)</span>
            </Label>
            <Controller
              control={form.control}
              name="tags"
              render={({ field }) => (
                <TagInput
                  id="inbox-tags"
                  value={field.value}
                  onChange={field.onChange}
                  suggestions={existingTags.map((t) => t.name)}
                  invalid={!!errors.tags}
                />
              )}
            />
            <FieldError message={errors.tags?.message} />
          </div>

          <div className="space-y-2">
            <Label htmlFor="inbox-notes">
              Notes <span className="font-normal text-muted-foreground">(optional)</span>
            </Label>
            <Textarea
              id="inbox-notes"
              placeholder="Anything worth remembering about this inbox"
              rows={3}
              aria-invalid={!!errors.notes}
              {...form.register('notes')}
            />
            <FieldError message={errors.notes?.message} />
          </div>

          {authorize.isError && (
            <p className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
              Couldn't start the connection: {authorize.error.message}
            </p>
          )}
        </form>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isRedirecting}>
            Cancel
          </Button>
          <Button type="submit" form="add-inbox-form" disabled={isRedirecting}>
            {isRedirecting && <Loader2 className="animate-spin" />}
            {isRedirecting ? 'Redirecting to Google…' : 'Continue with Google'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
