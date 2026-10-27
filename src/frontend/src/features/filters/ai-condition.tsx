import { Sparkles, X } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'
import { MAX_AI_CONDITIONS, MAX_AI_PROMPT_LENGTH, type ConditionDraft } from './rule-draft'

const SUGGESTIONS = [
  'A bill or statement that says how much I owe and when it is due',
  'A receipt or order confirmation for something I bought',
  'A flight, train or hotel booking',
  'A person (not a newsletter) asking me a question that needs a reply',
]

/** Gradient text in the AI colours. */
function AiText({ className, children }: { className?: string; children: React.ReactNode }) {
  return (
    <span className={cn('bg-linear-to-r from-ai-1 via-ai-2 to-ai-3 bg-clip-text text-transparent', className)}>
      {children}
    </span>
  )
}

const MATCH_OPTIONS = [
  ['matches', 'Matches'],
  ['not_matches', "Doesn't match"],
] as const

function MatchToggle({ value, onChange }: { value: string; onChange: (op: string) => void }) {
  return (
    <div role="radiogroup" aria-label="Match or exclude" className="inline-flex rounded-md border bg-card p-0.5">
      {MATCH_OPTIONS.map(([op, label]) => (
        <button
          key={op}
          type="button"
          role="radio"
          aria-checked={value === op}
          onClick={() => onChange(op)}
          className={cn(
            'rounded px-2 py-0.5 text-xs font-medium whitespace-nowrap transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring/50',
            value === op
              ? 'bg-linear-to-r from-ai-1 to-ai-2 text-primary-foreground'
              : 'text-muted-foreground hover:text-foreground',
          )}
        >
          {label}
        </button>
      ))}
    </div>
  )
}

/** A natural-language condition: the user describes the emails, and Jev (TypeSafe's System One
 *  model) decides per email. Styled apart from field conditions, with the AI gradient. */
export function AiConditionCard({
  draft,
  error,
  onChange,
  onRemove,
}: {
  draft: ConditionDraft
  error?: string
  onChange: (next: ConditionDraft) => void
  onRemove?: () => void
}) {
  const id = `ai-${draft.key}`
  return (
    <div className="rounded-xl bg-linear-to-br from-ai-1/60 via-ai-2/40 to-ai-3/60 p-px shadow-xs">
      <div className="relative overflow-hidden rounded-[calc(var(--radius-xl)-1px)] bg-card">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 bg-linear-to-br from-ai-1/8 via-transparent to-ai-3/8"
        />
        <div className="relative space-y-3 p-3 sm:p-4">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
            <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-linear-to-br from-ai-1 via-ai-2 to-ai-3 text-primary-foreground shadow-xs">
              <Sparkles className="size-4" />
            </span>
            <div className="min-w-48 flex-1">
              <label htmlFor={id} className="block text-sm font-semibold">
                <AiText>In plain English</AiText>
              </label>
              <p className="text-xs text-muted-foreground">Decided by Jev, TypeSafe’s System One model</p>
            </div>
            <div className="ml-auto flex items-center gap-1">
              <MatchToggle value={draft.op} onChange={(op) => onChange({ ...draft, op })} />
              {onRemove && (
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="size-8 text-muted-foreground hover:text-destructive"
                  aria-label="Remove AI condition"
                  onClick={onRemove}
                >
                  <X />
                </Button>
              )}
            </div>
          </div>

          <Textarea
            id={id}
            value={draft.value}
            maxLength={MAX_AI_PROMPT_LENGTH}
            rows={2}
            placeholder="Describe the emails this should match, e.g. “a bill or statement that says how much I owe”"
            aria-invalid={!!error}
            onChange={(e) => onChange({ ...draft, value: e.target.value })}
            className="min-h-16 resize-none bg-background/60 field-sizing-content focus-visible:border-ai-1/60 focus-visible:ring-ai-1/20"
          />

          {!draft.value.trim() && (
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-xs text-muted-foreground">Try</span>
              {SUGGESTIONS.map((text) => (
                <button
                  key={text}
                  type="button"
                  onClick={() => onChange({ ...draft, value: text })}
                  className="max-w-full truncate rounded-full border bg-card px-2.5 py-0.5 text-xs text-muted-foreground transition-colors outline-none hover:border-ai-1/50 hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring/50"
                >
                  {text}
                </button>
              ))}
            </div>
          )}

          <div className="flex items-start justify-between gap-3 text-xs">
            {error ? (
              <p className="text-destructive">{error}</p>
            ) : (
              <p className="text-muted-foreground">
                Jev reads the sender, recipients, subject, attachment names and body. It’s only asked when the other
                conditions leave the result open.
              </p>
            )}
            <span className="shrink-0 text-muted-foreground tabular-nums">
              {draft.value.length}/{MAX_AI_PROMPT_LENGTH}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}

/** Adds an AI condition. Disabled at the per-rule limit. Without a server key it still works, with a note
 *  that scans skip the filter until the key is set. */
export function AddAiConditionButton({
  keyConfigured,
  count,
  onAdd,
  compact,
}: {
  /** OPENROUTER_API_KEY is set on the server. */
  keyConfigured: boolean
  count: number
  onAdd: () => void
  compact?: boolean
}) {
  const reason = count >= MAX_AI_CONDITIONS ? `At most ${MAX_AI_CONDITIONS} AI conditions per rule` : undefined
  const note = keyConfigured ? undefined : "OPENROUTER_API_KEY isn't set: scans skip filters with AI conditions"
  return (
    <span className="inline-flex flex-wrap items-center gap-2" title={reason ?? note}>
      <Button
        type="button"
        variant={compact ? 'ghost' : 'outline'}
        size="sm"
        disabled={!!reason}
        onClick={onAdd}
        className={cn(!compact && 'border-ai-1/40 bg-linear-to-r from-ai-1/8 to-ai-3/8 hover:border-ai-1/70')}
      >
        <Sparkles className="text-ai-1" />
        <AiText className="font-medium">Describe in plain English</AiText>
      </Button>
      {!compact && (reason ?? note) && <span className="text-xs text-muted-foreground">{reason ?? note}</span>}
    </span>
  )
}
