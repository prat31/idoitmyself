import { useState, type KeyboardEvent, type ReactNode } from 'react'
import { Check, ChevronsUpDown, Minus, X } from 'lucide-react'

import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import type { Inbox } from '@/features/inboxes/api'
import { providerById } from '@/features/inboxes/providers'
import { cn } from '@/lib/utils'
import type { MailboxType } from './api'
import type { ScopeDraft } from './scope'

type CheckState = boolean | 'partial'

function CheckMark({ state }: { state: CheckState }) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        'flex size-4 shrink-0 items-center justify-center rounded-[4px] border border-input',
        state && 'border-primary bg-primary text-primary-foreground',
      )}
    >
      {state === 'partial' ? <Minus className="size-3" strokeWidth={3} /> : state && <Check className="size-3" strokeWidth={3} />}
    </span>
  )
}

function OptionRow({
  state,
  onToggle,
  indent,
  children,
}: {
  state: CheckState
  onToggle: () => void
  indent?: boolean
  children: ReactNode
}) {
  const onKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      onToggle()
    }
  }
  return (
    <li
      role="option"
      aria-selected={state === true}
      aria-checked={state === 'partial' ? 'mixed' : state}
      tabIndex={0}
      onClick={onToggle}
      onKeyDown={onKeyDown}
      className={cn(
        'flex cursor-pointer items-start gap-2.5 rounded-md px-2 py-2 outline-none hover:bg-accent focus-visible:bg-accent',
        indent && 'ml-6',
      )}
    >
      <span className="mt-0.5">
        <CheckMark state={state} />
      </span>
      <span className="min-w-0 flex-1">{children}</span>
    </li>
  )
}

/** Hierarchical picker: each mailbox type ("All Gmail inboxes") with its inboxes underneath. Ticking a
 *  type selects it as a whole; unticking one of its inboxes then switches to the type's other inboxes,
 *  chosen one by one. */
export function ScopeSelect({
  id,
  value,
  onChange,
  mailboxTypes,
  inboxes,
  invalid,
}: {
  id?: string
  value: ScopeDraft
  onChange: (next: ScopeDraft) => void
  mailboxTypes: MailboxType[]
  inboxes: Inbox[]
  invalid?: boolean
}) {
  const [open, setOpen] = useState(false)
  const inboxesOf = (type: MailboxType) => inboxes.filter((i) => i.provider === type)

  const typeState = (type: MailboxType): CheckState => {
    if (value.mailboxTypes.includes(type)) return true
    return inboxesOf(type).some((i) => value.inboxIds.includes(i.id)) ? 'partial' : false
  }

  const toggleType = (type: MailboxType) => {
    const ofType = new Set(inboxesOf(type).map((i) => i.id))
    const inboxIds = value.inboxIds.filter((inboxId) => !ofType.has(inboxId))
    onChange(
      typeState(type) === true
        ? { mailboxTypes: value.mailboxTypes.filter((t) => t !== type), inboxIds }
        : { mailboxTypes: [...value.mailboxTypes, type], inboxIds },
    )
  }

  const toggleInbox = (inbox: Inbox) => {
    if (value.mailboxTypes.includes(inbox.provider)) {
      // Leave "all of this type" for its other inboxes, chosen one by one.
      const others = inboxesOf(inbox.provider).filter((i) => i.id !== inbox.id).map((i) => i.id)
      onChange({
        mailboxTypes: value.mailboxTypes.filter((t) => t !== inbox.provider),
        inboxIds: [...value.inboxIds, ...others],
      })
    } else if (value.inboxIds.includes(inbox.id)) {
      onChange({ ...value, inboxIds: value.inboxIds.filter((i) => i !== inbox.id) })
    } else {
      onChange({ ...value, inboxIds: [...value.inboxIds, inbox.id] })
    }
  }

  const chips = [
    ...value.mailboxTypes.map((type) => ({
      key: `type-${type}`,
      label: `All ${providerById[type].label} inboxes`,
      remove: () => toggleType(type),
    })),
    ...inboxes
      .filter((i) => value.inboxIds.includes(i.id))
      .map((inbox) => ({ key: inbox.id, label: inbox.name, remove: () => toggleInbox(inbox) })),
  ]

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          id={id}
          type="button"
          role="combobox"
          aria-expanded={open}
          aria-invalid={invalid || undefined}
          className={cn(
            'flex min-h-9 w-full items-center gap-2 rounded-md border border-input bg-card px-2.5 py-1.5 text-left text-sm shadow-xs transition-[color,box-shadow] outline-none',
            'focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/30',
            'aria-invalid:border-destructive aria-invalid:ring-destructive/20',
          )}
        >
          <span className="flex min-w-0 flex-1 flex-wrap gap-1.5">
            {chips.length === 0 ? (
              <span className="px-0.5 text-muted-foreground/70">Choose mailbox types or inboxes</span>
            ) : (
              chips.map((chip) => (
                <span
                  key={chip.key}
                  className="inline-flex max-w-full items-center gap-1.5 rounded-md bg-secondary py-0.5 pl-2 pr-1 text-xs font-medium text-secondary-foreground"
                >
                  <span className="truncate">{chip.label}</span>
                  <span
                    role="button"
                    tabIndex={-1}
                    aria-label={`Remove ${chip.label}`}
                    className="rounded-sm p-0.5 text-muted-foreground hover:bg-accent hover:text-foreground"
                    onPointerDown={(e) => e.stopPropagation()}
                    onClick={(e) => {
                      e.stopPropagation()
                      chip.remove()
                    }}
                  >
                    <X className="size-3" />
                  </span>
                </span>
              ))
            )}
          </span>
          <ChevronsUpDown className="size-4 shrink-0 text-muted-foreground" />
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-(--radix-popover-trigger-width) p-0">
        <ul role="listbox" aria-multiselectable="true" className="max-h-72 overflow-y-auto p-1">
          {mailboxTypes.map((type) => {
            const provider = providerById[type]
            const Icon = provider.icon
            const children = inboxesOf(type)
            const whole = value.mailboxTypes.includes(type)
            return (
              <li key={type} role="presentation">
                <ul role="group" aria-label={provider.label}>
                  <OptionRow state={typeState(type)} onToggle={() => toggleType(type)}>
                    <span className="flex items-center gap-2">
                      <Icon className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                      <span className="truncate text-sm font-medium">All {provider.label} inboxes</span>
                    </span>
                    <span className="mt-0.5 block text-xs text-muted-foreground">Includes {provider.label} inboxes connected later</span>
                  </OptionRow>
                  {children.length === 0 ? (
                    <li className="ml-6 px-2 py-1.5 text-xs text-muted-foreground">No {provider.label} inboxes connected yet</li>
                  ) : (
                    children.map((inbox) => (
                      <OptionRow
                        key={inbox.id}
                        indent
                        state={whole || value.inboxIds.includes(inbox.id)}
                        onToggle={() => toggleInbox(inbox)}
                      >
                        <span className="block truncate text-sm">{inbox.name}</span>
                        <span className="block truncate text-xs text-muted-foreground">{inbox.email_address}</span>
                      </OptionRow>
                    ))
                  )}
                </ul>
              </li>
            )
          })}
        </ul>
      </PopoverContent>
    </Popover>
  )
}
