import { useState, type ReactNode } from 'react'
import { ArrowLeft, Loader2, Plus } from 'lucide-react'
import { Link, useNavigate, useParams } from 'react-router'
import { toast } from 'sonner'

import { FieldError, FormError, Optional } from '@/components/form/field'
import { ErrorBanner } from '@/components/layout/error-banner'
import { PageBody } from '@/components/layout/page-body'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label as FieldLabel } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import { useInboxes, type Inbox } from '@/features/inboxes/api'
import { AddLabelDialog } from '@/features/labels/add-label-dialog'
import { useLabels, type Label } from '@/features/labels/api'
import { LabelDot } from '@/features/labels/label-dot'
import {
  useCreateFilter,
  useFieldCatalogue,
  useFilter,
  useUpdateFilter,
  type FieldCatalogue,
  type Filter,
  type FilterInput,
  type FilterStatus,
} from './api'
import { coveredTypes, scopeToDraft, type ScopeDraft } from './scope'
import { ScopeSelect } from './scope-select'
import { DeleteFilterDialog } from './delete-filter-dialog'
import { RuleBuilder } from './rule-builder'
import { emptyDraft, fromDraft, toDraft, validateDraft, type DraftErrors, type RuleDraft } from './rule-draft'

const NAME_MAX = 100
const DESCRIPTION_MAX = 500

const backLink = (
  <Link
    to="/automation/filters"
    className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
  >
    <ArrowLeft className="size-4" />
    Filters
  </Link>
)

/** Create (`/automation/filters/new`) or edit (`/automation/filters/:filterId`) a filter. */
export function FilterEditorPage() {
  const { filterId } = useParams()
  const filter = useFilter(filterId)
  const catalogue = useFieldCatalogue()
  const labels = useLabels()
  const inboxes = useInboxes()

  const failed = [filter, catalogue, labels, inboxes].find((q) => q.isError)
  const ready = catalogue.data && labels.data && inboxes.data && (!filterId || filter.data)

  return (
    <>
      <header className="space-y-4 border-b px-4 pb-5 pt-6 md:px-10 md:pb-6 md:pt-8">
        {backLink}
        <div className="space-y-1.5">
          <h1 className="font-serif text-2xl font-semibold tracking-tight md:text-3xl">
            {filterId ? (filter.data?.name ?? 'Filter') : 'New filter'}
          </h1>
          <p className="text-sm text-muted-foreground">
            A filter applies to emails scanned while it's active. Editing it never removes labels it already added.
          </p>
        </div>
      </header>
      <PageBody>
        {failed ? (
          <ErrorBanner message={`Couldn't load the filter: ${failed.error?.message}`} onRetry={() => failed.refetch()} />
        ) : ready ? (
          <FilterForm
            key={filterId ?? 'new'}
            filter={filter.data}
            catalogue={catalogue.data}
            labels={labels.data}
            inboxes={inboxes.data}
          />
        ) : (
          <div className="space-y-4">
            <Skeleton className="h-40 rounded-xl" />
            <Skeleton className="h-56 rounded-xl" />
          </div>
        )}
      </PageBody>
    </>
  )
}

function Section({ title, description, children }: { title: string; description?: string; children: ReactNode }) {
  return (
    <section className="rounded-xl border bg-card p-4 shadow-xs sm:p-5">
      <div className="mb-4 space-y-0.5">
        <h2 className="text-sm font-semibold">{title}</h2>
        {description && <p className="text-xs text-muted-foreground">{description}</p>}
      </div>
      {children}
    </section>
  )
}

type FormErrors = { name?: string; description?: string; scope?: string; label?: string; rule: DraftErrors }

function FilterForm({
  filter,
  catalogue,
  labels,
  inboxes,
}: {
  filter: Filter | undefined
  catalogue: FieldCatalogue
  labels: Label[]
  inboxes: Inbox[]
}) {
  const navigate = useNavigate()
  const create = useCreateFilter()
  const update = useUpdateFilter()
  const saving = create.isPending || update.isPending
  const mutationError = create.error ?? update.error

  const [name, setName] = useState(filter?.name ?? '')
  const [description, setDescription] = useState(filter?.description ?? '')
  // New filters start on every inbox of the first mailbox type (today: all Gmail inboxes).
  const [scope, setScope] = useState<ScopeDraft>(() =>
    filter ? scopeToDraft(filter.scope) : { mailboxTypes: catalogue.mailbox_types.slice(0, 1), inboxIds: [] },
  )
  const types = coveredTypes(scope, inboxes)
  const [labelId, setLabelId] = useState(filter?.label.id ?? '')
  const [status, setStatus] = useState<FilterStatus>(filter?.status ?? 'active')
  const [draft, setDraft] = useState<RuleDraft>(() =>
    filter ? toDraft(filter.rule) : emptyDraft(catalogue, catalogue.mailbox_types.slice(0, 1)),
  )
  const [submitted, setSubmitted] = useState(false)

  const validate = (): FormErrors => ({
    name: !name.trim() ? 'Give the filter a name' : name.length > NAME_MAX ? `Keep it under ${NAME_MAX} characters` : undefined,
    description: description.length > DESCRIPTION_MAX ? `Keep it under ${DESCRIPTION_MAX} characters` : undefined,
    scope: scope.mailboxTypes.length || scope.inboxIds.length ? undefined : 'Choose at least one mailbox type or inbox',
    label: labelId ? undefined : 'Choose the label this filter adds',
    rule: validateDraft(draft, catalogue, types),
  })

  // Errors show once the user has tried to save, and update as they fix things.
  const shown: FormErrors = submitted ? validate() : { rule: {} }

  const onSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    setSubmitted(true)
    const found = validate()
    if (found.name || found.description || found.scope || found.label || Object.keys(found.rule).length) return

    const input: FilterInput = {
      name: name.trim(),
      description: description.trim() || null,
      scope: { mailbox_types: scope.mailboxTypes, inbox_ids: scope.inboxIds },
      label_id: labelId,
      rule: fromDraft(draft, catalogue),
      status,
    }
    const done = (saved: Filter) => {
      toast.success(filter ? `Filter "${saved.name}" saved` : `Filter "${saved.name}" created`)
      navigate('/automation/filters')
    }
    if (filter) {
      update.mutate({ id: filter.id, changes: input }, { onSuccess: done })
    } else {
      create.mutate(input, { onSuccess: done })
    }
  }

  return (
    <form onSubmit={onSubmit} className="mx-auto max-w-4xl space-y-4" noValidate>
      <Section title="Details">
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <FieldLabel htmlFor="filter-name">Name</FieldLabel>
            <Input
              id="filter-name"
              placeholder="e.g. HDFC card statements"
              autoComplete="off"
              value={name}
              aria-invalid={!!shown.name}
              onChange={(e) => setName(e.target.value)}
            />
            <FieldError message={shown.name} />
          </div>

          <div className="space-y-2">
            <FieldLabel htmlFor="filter-scope">Applies to</FieldLabel>
            <ScopeSelect
              id="filter-scope"
              value={scope}
              onChange={setScope}
              mailboxTypes={catalogue.mailbox_types}
              inboxes={inboxes}
              invalid={!!shown.scope}
            />
            {shown.scope ? (
              <FieldError message={shown.scope} />
            ) : (
              <p className="text-xs text-muted-foreground">
                A whole mailbox type also covers inboxes connected later. Pick inboxes to limit it.
              </p>
            )}
          </div>

          <div className="space-y-2 sm:col-span-2">
            <FieldLabel htmlFor="filter-description">
              Description <Optional />
            </FieldLabel>
            <Textarea
              id="filter-description"
              rows={2}
              placeholder="What this filter is for"
              value={description}
              aria-invalid={!!shown.description}
              onChange={(e) => setDescription(e.target.value)}
            />
            <FieldError message={shown.description} />
          </div>
        </div>
      </Section>

      <Section title="Conditions" description="Text comparisons ignore case unless you turn on match case (Aa).">
        <RuleBuilder
          draft={draft}
          catalogue={catalogue}
          mailboxTypes={types}
          errors={shown.rule}
          onChange={setDraft}
        />
      </Section>

      <Section title="Then" description="Every email that passes the conditions gets this label.">
        <div className="space-y-5">
          <div className="space-y-2">
            <FieldLabel htmlFor="filter-label">Add label</FieldLabel>
            <div className="flex flex-col gap-2 sm:flex-row">
              <Select value={labelId} onValueChange={setLabelId}>
                <SelectTrigger id="filter-label" className="sm:max-w-xs" aria-invalid={!!shown.label || undefined}>
                  <SelectValue placeholder={labels.length ? 'Choose a label' : 'No labels yet'} />
                </SelectTrigger>
                <SelectContent>
                  {labels.map((label) => (
                    <SelectItem key={label.id} value={label.id}>
                      <span className="flex items-center gap-2">
                        <LabelDot color={label.color} />
                        {label.display_name}
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <AddLabelDialog
                trigger={
                  <Button type="button" variant="outline">
                    <Plus />
                    New label
                  </Button>
                }
                onCreated={(label) => setLabelId(label.id)}
              />
            </div>
            <FieldError message={shown.label} />
          </div>

          <div className="flex items-start gap-3">
            <Switch
              id="filter-active"
              checked={status === 'active'}
              onCheckedChange={(checked) => setStatus(checked ? 'active' : 'inactive')}
            />
            <div className="space-y-0.5">
              <FieldLabel htmlFor="filter-active">Active</FieldLabel>
              <p className="text-xs text-muted-foreground">
                Active filters run on email scanned from now on (every 30 minutes). Emails scanned earlier aren't
                re-checked.
              </p>
            </div>
          </div>
        </div>
      </Section>

      {mutationError && <FormError message={`Couldn't save the filter: ${mutationError.message}`} />}

      <div className="flex flex-col-reverse gap-2 sm:flex-row sm:items-center">
        {filter && <DeleteFilterDialog filter={filter} onDeleted={() => navigate('/automation/filters')} />}
        <div className="flex flex-col-reverse gap-2 sm:ml-auto sm:flex-row">
          <Button type="button" variant="outline" asChild>
            <Link to="/automation/filters">Cancel</Link>
          </Button>
          <Button type="submit" disabled={saving}>
            {saving && <Loader2 className="animate-spin" />}
            {filter ? 'Save filter' : 'Create filter'}
          </Button>
        </div>
      </div>
    </form>
  )
}
