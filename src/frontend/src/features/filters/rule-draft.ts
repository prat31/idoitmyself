import type { Condition, FieldCatalogue, FieldSpec, Join, MailboxType, OperatorSpec, Rule, SubGroup } from './api'

/** Editable form of a rule. Inputs hold strings (numbers are parsed on save); `key` is a stable React
 *  key. Mirrors the API's two-level shape: the root holds conditions and groups of conditions. Every
 *  item carries a `join` to the item before it; the first item's is ignored. */
export type ConditionDraft = {
  key: string
  type: 'condition'
  join: Join
  field: string
  op: string
  value: string
  /** For the "in" operator of enum fields. */
  values: string[]
  argument: string
  caseSensitive: boolean
}

export type GroupDraft = { key: string; type: 'group'; join: Join; items: ConditionDraft[] }

export type RuleDraft = { items: (ConditionDraft | GroupDraft)[] }

let nextKey = 0
const newKey = () => `k${++nextKey}`

/** Fields usable for a scope covering these mailbox types: common fields always; a provider's own
 *  fields only when every covered type has them (mirrors the server's check). */
export function fieldsFor(catalogue: FieldCatalogue, mailboxTypes: MailboxType[]): FieldSpec[] {
  return catalogue.fields.filter(
    (f) => f.mailbox_types === null || (mailboxTypes.length > 0 && mailboxTypes.every((t) => f.mailbox_types!.includes(t))),
  )
}

export function operatorsFor(catalogue: FieldCatalogue, field: FieldSpec | undefined): OperatorSpec[] {
  return field ? catalogue.operators[field.type] : []
}

export function newCondition(catalogue: FieldCatalogue, mailboxTypes: MailboxType[], join: Join = 'and'): ConditionDraft {
  const field = fieldsFor(catalogue, mailboxTypes)[0]
  return withField(
    { key: newKey(), type: 'condition', join, field: '', op: '', value: '', values: [], argument: '', caseSensitive: false },
    catalogue,
    field,
  )
}

/** The condition switched to another field: first operator of its type, value reset. */
export function withField(draft: ConditionDraft, catalogue: FieldCatalogue, field: FieldSpec): ConditionDraft {
  return {
    ...draft,
    field: field.key,
    op: operatorsFor(catalogue, field)[0]?.key ?? '',
    value: '',
    values: [],
    argument: '',
  }
}

export function newGroup(catalogue: FieldCatalogue, mailboxTypes: MailboxType[], join: Join = 'and'): GroupDraft {
  return { key: newKey(), type: 'group', join, items: [newCondition(catalogue, mailboxTypes)] }
}

function conditionToDraft(c: Condition): ConditionDraft {
  return {
    key: newKey(),
    type: 'condition',
    join: c.join ?? 'and',
    field: c.field,
    op: c.op,
    value: Array.isArray(c.value) || c.value === undefined ? '' : String(c.value),
    values: Array.isArray(c.value) ? c.value : [],
    argument: c.argument ?? '',
    caseSensitive: c.case_sensitive ?? false,
  }
}

export function toDraft(rule: Rule): RuleDraft {
  return {
    items: rule.items.map((item) =>
      item.type === 'condition'
        ? conditionToDraft(item)
        : { key: newKey(), type: 'group', join: item.join ?? 'and', items: item.items.map(conditionToDraft) },
    ),
  }
}

export function emptyDraft(catalogue: FieldCatalogue, mailboxTypes: MailboxType[]): RuleDraft {
  return { items: [newCondition(catalogue, mailboxTypes)] }
}

/** A problem with one condition, keyed by its draft key. */
export type DraftErrors = Record<string, string>

export function validateDraft(draft: RuleDraft, catalogue: FieldCatalogue, mailboxTypes: MailboxType[]): DraftErrors {
  const errors: DraftErrors = {}
  const available = new Set(fieldsFor(catalogue, mailboxTypes).map((f) => f.key))
  const check = (c: ConditionDraft) => {
    const field = catalogue.fields.find((f) => f.key === c.field)
    const op = operatorsFor(catalogue, field).find((o) => o.key === c.op)
    if (!field || !op) errors[c.key] = 'Choose a field and an operator'
    else if (!available.has(field.key)) errors[c.key] = `${field.label} isn't available for every selected inbox`
    else if (field.argument_label && !c.argument.trim()) errors[c.key] = `Enter the ${field.argument_label.toLowerCase()}`
    else if (!op.takes_value) return
    else if (field.type === 'number' && (c.value.trim() === '' || Number.isNaN(Number(c.value))))
      errors[c.key] = 'Enter a number'
    else if (field.type === 'enum' && (c.op === 'in' ? c.values.length === 0 : !c.value))
      errors[c.key] = 'Choose a value'
    // Regexes are checked by the server: they use Python's syntax, which differs from JavaScript's.
    else if ((field.type === 'text' || field.type === 'text_list') && !c.value) errors[c.key] = 'Enter a value'
  }
  for (const item of draft.items) {
    if (item.type === 'condition') check(item)
    else item.items.forEach(check)
  }
  return errors
}

function conditionFromDraft(c: ConditionDraft, catalogue: FieldCatalogue, first: boolean): Condition {
  const field = catalogue.fields.find((f) => f.key === c.field)!
  const op = catalogue.operators[field.type].find((o) => o.key === c.op)!
  const condition: Condition = { type: 'condition', field: c.field, op: c.op }
  if (!first) condition.join = c.join
  if (field.argument_label) condition.argument = c.argument.trim()
  if (op.takes_value) {
    if (field.type === 'number') condition.value = Number(c.value)
    else if (field.type === 'enum' && c.op === 'in') condition.value = c.values
    else condition.value = c.value
  }
  if ((field.type === 'text' || field.type === 'text_list') && c.caseSensitive) condition.case_sensitive = true
  return condition
}

/** The API rule for a draft that passed validateDraft. The first item of each list has no join. */
export function fromDraft(draft: RuleDraft, catalogue: FieldCatalogue): Rule {
  return {
    type: 'group',
    items: draft.items.map((item, index): Condition | SubGroup => {
      if (item.type === 'condition') return conditionFromDraft(item, catalogue, index === 0)
      const group: SubGroup = {
        type: 'group',
        items: item.items.map((c, i) => conditionFromDraft(c, catalogue, i === 0)),
      }
      if (index > 0) group.join = item.join
      return group
    }),
  }
}
