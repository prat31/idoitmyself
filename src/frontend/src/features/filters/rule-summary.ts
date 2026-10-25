import type { Condition, FieldCatalogue, Rule } from './api'

function describeCondition(c: Condition, catalogue: FieldCatalogue | undefined): string {
  const field = catalogue?.fields.find((f) => f.key === c.field)
  const op = field && catalogue?.operators[field.type].find((o) => o.key === c.op)
  const fieldLabel = field ? (c.argument ? `${field.label} ${c.argument}` : field.label) : c.field
  const optionLabel = (v: string) => field?.options.find((o) => o.value === v)?.label ?? v
  let value = ''
  if (Array.isArray(c.value)) value = ` ${c.value.map(optionLabel).join(', ')}`
  else if (typeof c.value === 'string') value = field?.type === 'enum' ? ` ${optionLabel(c.value)}` : ` “${c.value}”`
  else if (typeof c.value === 'number') value = ` ${c.value}`
  return `${fieldLabel} ${op?.label ?? c.op}${value}`
}

function joined<T extends { join?: 'and' | 'or' }>(items: T[], describe: (item: T) => string): string {
  return items.map((item, i) => (i === 0 ? '' : item.join === 'or' ? ' OR ' : ' AND ') + describe(item)).join('')
}

/** One-line reading of a rule, e.g. Sender domain is “hdfcbank.net” AND (Subject contains “bill” OR …). */
export function summarizeRule(rule: Rule, catalogue: FieldCatalogue | undefined): string {
  return joined(rule.items, (item) =>
    item.type === 'condition'
      ? describeCondition(item, catalogue)
      : `(${joined(item.items, (c) => describeCondition(c, catalogue))})`,
  )
}
