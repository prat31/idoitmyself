import { CaseSensitive, Plus, X } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { MultiSelect } from '@/components/ui/multi-select'
import { Select, SelectContent, SelectGroup, SelectItem, SelectLabel, SelectTrigger, SelectValue } from '@/components/ui/select'
import { providerById } from '@/features/inboxes/providers'
import { cn } from '@/lib/utils'
import { AddAiConditionButton, AiConditionCard } from './ai-condition'
import type { FieldCatalogue, Join, MailboxType } from './api'
import {
  countAiConditions,
  fieldsFor,
  isAiCondition,
  newAiCondition,
  newCondition,
  newGroup,
  operatorsFor,
  withField,
  type ConditionDraft,
  type DraftErrors,
  type GroupDraft,
  type RuleDraft,
} from './rule-draft'

/** The AND / OR between an item and the one before it: a two-way toggle on the connector line. */
function JoinToggle({ value, onChange }: { value: Join; onChange: (join: Join) => void }) {
  return (
    <div className="flex items-center gap-2 py-1 pl-3">
      <div role="radiogroup" aria-label="Join with the item above" className="inline-flex rounded-md border bg-card p-0.5">
        {(['and', 'or'] as const).map((option) => (
          <button
            key={option}
            type="button"
            role="radio"
            aria-checked={value === option}
            onClick={() => onChange(option)}
            className={cn(
              'rounded px-2 py-0.5 text-[10px] font-semibold tracking-wide transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring/50',
              value === option ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground',
            )}
          >
            {option.toUpperCase()}
          </button>
        ))}
      </div>
    </div>
  )
}

/** The join a new item gets: the same as the last one in the list (so a run of ORs stays ORs). */
function nextJoin(items: { join: Join }[]): Join {
  return items.length > 1 ? items[items.length - 1].join : 'and'
}

type ConditionRowProps = {
  draft: ConditionDraft
  catalogue: FieldCatalogue
  mailboxTypes: MailboxType[]
  error?: string
  onChange: (next: ConditionDraft) => void
  onRemove?: () => void
}

/** A condition: a field condition, or an AI (natural-language) one in its own card. */
function AnyCondition(props: ConditionRowProps) {
  return isAiCondition(props.draft) ? (
    <AiConditionCard draft={props.draft} error={props.error} onChange={props.onChange} onRemove={props.onRemove} />
  ) : (
    <ConditionRow {...props} />
  )
}

function ConditionRow({ draft, catalogue, mailboxTypes, error, onChange, onRemove }: ConditionRowProps) {
  // AI conditions have their own card and button, not a place in the field list.
  const fields = fieldsFor(catalogue, mailboxTypes).filter((f) => f.type !== 'ai')
  // The condition's field may no longer suit the scope (e.g. a Gmail-only field after another
  // provider's inbox was added); keep showing it, flagged, rather than silently changing the rule.
  const field = catalogue.fields.find((f) => f.key === draft.field)
  const unavailable = field && !fields.includes(field) ? field : undefined
  const operators = operatorsFor(catalogue, field)
  const operator = operators.find((o) => o.key === draft.op)
  const common = fields.filter((f) => f.mailbox_types === null)
  const own = fields.filter((f) => f.mailbox_types !== null)
  const isText = field?.type === 'text' || field?.type === 'text_list'

  const setOp = (op: string) => {
    const next = operators.find((o) => o.key === op)
    onChange({ ...draft, op, ...(next?.takes_value ? {} : { value: '', values: [] }) })
  }

  return (
    <div className="space-y-1">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start">
        <div className="grid flex-1 gap-2 sm:grid-cols-[minmax(0,11rem)_minmax(0,10rem)_minmax(0,1fr)]">
          <Select
            value={draft.field}
            onValueChange={(key) => onChange(withField(draft, catalogue, fields.find((f) => f.key === key)!))}
          >
            <SelectTrigger aria-label="Field" title={field?.description}>
              <SelectValue placeholder="Field" />
            </SelectTrigger>
            <SelectContent>
              <SelectGroup>
                <SelectLabel>Any mailbox</SelectLabel>
                {common.map((f) => (
                  <SelectItem key={f.key} value={f.key}>
                    {f.label}
                  </SelectItem>
                ))}
              </SelectGroup>
              {own.length > 0 && (
                <SelectGroup>
                  <SelectLabel>{providerById[mailboxTypes[0]].label} only</SelectLabel>
                  {own.map((f) => (
                    <SelectItem key={f.key} value={f.key}>
                      {f.label}
                    </SelectItem>
                  ))}
                </SelectGroup>
              )}
              {unavailable && (
                <SelectGroup>
                  <SelectLabel>Not available for this scope</SelectLabel>
                  <SelectItem value={unavailable.key} disabled>
                    {unavailable.label}
                  </SelectItem>
                </SelectGroup>
              )}
            </SelectContent>
          </Select>

          <Select value={draft.op} onValueChange={setOp}>
            <SelectTrigger aria-label="Operator">
              <SelectValue placeholder="Operator" />
            </SelectTrigger>
            <SelectContent>
              {operators.map((o) => (
                <SelectItem key={o.key} value={o.key}>
                  {o.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <div className="flex min-w-0 gap-2">
            {field?.argument_label && (
              <Input
                aria-label={field.argument_label}
                placeholder={field.argument_label}
                value={draft.argument}
                onChange={(e) => onChange({ ...draft, argument: e.target.value })}
                className="sm:max-w-36"
              />
            )}
            {operator?.takes_value &&
              (field?.type === 'enum' ? (
                draft.op === 'in' ? (
                  <MultiSelect
                    options={field.options}
                    value={draft.values}
                    onChange={(values) => onChange({ ...draft, values })}
                    placeholder="Choose values"
                    invalid={!!error}
                  />
                ) : (
                  <Select value={draft.value} onValueChange={(value) => onChange({ ...draft, value })}>
                    <SelectTrigger aria-label="Value" aria-invalid={!!error || undefined}>
                      <SelectValue placeholder="Value" />
                    </SelectTrigger>
                    <SelectContent>
                      {field.options.map((o) => (
                        <SelectItem key={o.value} value={o.value}>
                          {o.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )
              ) : (
                <Input
                  aria-label="Value"
                  type={field?.type === 'number' ? 'number' : 'text'}
                  inputMode={field?.type === 'number' ? 'decimal' : undefined}
                  placeholder={draft.op.endsWith('matches_regex') ? 'Regular expression' : 'Value'}
                  value={draft.value}
                  aria-invalid={!!error}
                  onChange={(e) => onChange({ ...draft, value: e.target.value })}
                  className={cn(draft.op.endsWith('matches_regex') && 'font-mono')}
                />
              ))}
          </div>
        </div>

        <div className="flex shrink-0 items-center justify-end gap-1">
          {isText && operator?.takes_value && (
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className={cn('size-9', draft.caseSensitive ? 'bg-accent text-foreground' : 'text-muted-foreground')}
              aria-pressed={draft.caseSensitive}
              aria-label="Match case"
              title={draft.caseSensitive ? 'Case-sensitive' : 'Case-insensitive (click to match case)'}
              onClick={() => onChange({ ...draft, caseSensitive: !draft.caseSensitive })}
            >
              <CaseSensitive />
            </Button>
          )}
          {onRemove && (
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="size-9 text-muted-foreground hover:text-destructive"
              aria-label="Remove condition"
              onClick={onRemove}
            >
              <X />
            </Button>
          )}
        </div>
      </div>
      {error ? (
        <p className="text-xs text-destructive">{error}</p>
      ) : (
        field && <p className="text-xs text-muted-foreground">{field.description}</p>
      )}
    </div>
  )
}

type GroupCardProps = {
  group: GroupDraft
  /** AI conditions in the whole rule (the limit is per rule). */
  aiCount: number
  catalogue: FieldCatalogue
  mailboxTypes: MailboxType[]
  errors: DraftErrors
  onChange: (next: GroupDraft) => void
  onRemove: () => void
}

function GroupCard({ group, aiCount, catalogue, mailboxTypes, errors, onChange, onRemove }: GroupCardProps) {
  const setItem = (index: number, next: ConditionDraft) =>
    onChange({ ...group, items: group.items.map((c, i) => (i === index ? next : c)) })
  return (
    <div className="space-y-2 rounded-lg border border-dashed bg-muted/30 p-3">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted-foreground">
        <span className="font-medium">Group</span>
        <span className="text-xs">( … ) brackets</span>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="ml-auto text-muted-foreground hover:text-destructive"
          onClick={onRemove}
        >
          Remove group
        </Button>
      </div>
      {group.items.map((condition, index) => (
        <div key={condition.key}>
          {index > 0 && <JoinToggle value={condition.join} onChange={(join) => setItem(index, { ...condition, join })} />}
          <AnyCondition
            draft={condition}
            catalogue={catalogue}
            mailboxTypes={mailboxTypes}
            error={errors[condition.key]}
            onChange={(next) => setItem(index, next)}
            onRemove={
              group.items.length > 1
                ? () => onChange({ ...group, items: group.items.filter((_, i) => i !== index) })
                : undefined
            }
          />
        </div>
      ))}
      <div className="flex flex-wrap gap-1">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() =>
            onChange({ ...group, items: [...group.items, newCondition(catalogue, mailboxTypes, nextJoin(group.items))] })
          }
        >
          <Plus />
          Condition
        </Button>
        <AddAiConditionButton
          compact
          keyConfigured={catalogue.ai_enabled}
          count={aiCount}
          onAdd={() => onChange({ ...group, items: [...group.items, newAiCondition(nextJoin(group.items))] })}
        />
      </div>
    </div>
  )
}

/** Edits a rule: conditions and groups (brackets), each joined to the item above by its own AND / OR.
 *  AND binds tighter than OR. Two levels at most. */
export function RuleBuilder({
  draft,
  catalogue,
  mailboxTypes,
  errors,
  onChange,
}: {
  draft: RuleDraft
  catalogue: FieldCatalogue
  mailboxTypes: MailboxType[]
  errors: DraftErrors
  onChange: (next: RuleDraft) => void
}) {
  const setItem = (index: number, next: ConditionDraft | GroupDraft) =>
    onChange({ ...draft, items: draft.items.map((item, i) => (i === index ? next : item)) })
  const remove = (index: number) => onChange({ ...draft, items: draft.items.filter((_, i) => i !== index) })
  const canRemove = draft.items.length > 1
  const aiCount = countAiConditions(draft)

  return (
    <div className="space-y-3">
      <p className="text-xs text-muted-foreground">
        AND binds tighter than OR: <span className="font-medium">A OR B AND C</span> means A OR (B AND C). Use a group
        for other brackets.
      </p>

      <div>
        {draft.items.map((item, index) => (
          <div key={item.key}>
            {index > 0 && <JoinToggle value={item.join} onChange={(join) => setItem(index, { ...item, join })} />}
            {item.type === 'condition' ? (
              <AnyCondition
                draft={item}
                catalogue={catalogue}
                mailboxTypes={mailboxTypes}
                error={errors[item.key]}
                onChange={(next) => setItem(index, next)}
                onRemove={canRemove ? () => remove(index) : undefined}
              />
            ) : (
              <GroupCard
                group={item}
                aiCount={aiCount}
                catalogue={catalogue}
                mailboxTypes={mailboxTypes}
                errors={errors}
                onChange={(next) => setItem(index, next)}
                onRemove={() =>
                  canRemove ? remove(index) : onChange({ ...draft, items: [newCondition(catalogue, mailboxTypes)] })
                }
              />
            )}
          </div>
        ))}
      </div>

      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() =>
            onChange({ ...draft, items: [...draft.items, newCondition(catalogue, mailboxTypes, nextJoin(draft.items))] })
          }
        >
          <Plus />
          Condition
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() =>
            onChange({ ...draft, items: [...draft.items, newGroup(catalogue, mailboxTypes, nextJoin(draft.items))] })
          }
        >
          <Plus />
          Group
        </Button>
        <AddAiConditionButton
          keyConfigured={catalogue.ai_enabled}
          count={aiCount}
          onAdd={() => onChange({ ...draft, items: [...draft.items, newAiCondition(nextJoin(draft.items))] })}
        />
      </div>
    </div>
  )
}
