import { ListFilter, Pencil } from 'lucide-react'
import { Link } from 'react-router'
import { toast } from 'sonner'

import { DefaultBadge } from '@/components/layout/default-badge'
import { Figure, ItemRow, MetaDot } from '@/components/layout/item-list'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { providerById } from '@/features/inboxes/providers'
import { LabelDot } from '@/features/labels/label-dot'
import { formatDateTime, formatNumber, formatRelative } from '@/lib/format'
import { useUpdateFilter, type FieldCatalogue, type Filter } from './api'
import { FilterStatusBadge } from './filter-status-badge'
import { summarizeRule } from './rule-summary'

/** One filter as a list row; the row opens the editor (stretched link), the switch (de)activates it. */
export function FilterRow({ filter, catalogue }: { filter: Filter; catalogue: FieldCatalogue | undefined }) {
  const update = useUpdateFilter()
  const active = filter.status === 'active'
  const types = [...new Set([...filter.scope.mailbox_types, ...filter.scope.inboxes.map((i) => i.provider)])]
  // One provider in scope: its icon; mixed providers: a neutral one.
  const Icon = types.length === 1 ? providerById[types[0]].icon : ListFilter
  const shownInboxes = filter.scope.inboxes.slice(0, 2)
  const moreInboxes = filter.scope.inboxes.length - shownInboxes.length

  const toggle = (checked: boolean) =>
    update.mutate(
      { id: filter.id, changes: { status: checked ? 'active' : 'inactive' } },
      {
        onSuccess: () => toast.success(`“${filter.name}” ${checked ? 'activated' : 'deactivated'}`),
        onError: (error) => toast.error("Couldn't change the filter", { description: error.message }),
      },
    )

  return (
    <ItemRow
      leading={
        <span className="flex size-9 items-center justify-center rounded-lg bg-secondary">
          <Icon className="size-[18px]" strokeWidth={1.75} />
        </span>
      }
      title={
        <Link to={`/automation/filters/${filter.id}`} className="outline-none after:absolute after:inset-0 focus-visible:underline">
          {filter.name}
        </Link>
      }
      badges={
        <>
          <FilterStatusBadge status={filter.status} />
          {filter.is_default && <DefaultBadge />}
          {filter.scope.mailbox_types.map((type) => (
            <Badge key={type} variant="outline" className="text-muted-foreground" title="Every inbox of this type, including future ones">
              All {providerById[type].label}
            </Badge>
          ))}
          {shownInboxes.map((inbox) => (
            <Badge key={inbox.id} variant="outline" className="text-muted-foreground" title={inbox.email_address}>
              {inbox.name}
            </Badge>
          ))}
          {moreInboxes > 0 && (
            <Badge
              variant="outline"
              className="text-muted-foreground"
              title={filter.scope.inboxes.slice(2).map((i) => i.name).join(', ')}
            >
              +{moreInboxes}
            </Badge>
          )}
        </>
      }
      figures={<Figure value={formatNumber(filter.emails_labelled)} label="Labelled" />}
      actions={
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" className="size-8 text-muted-foreground" asChild>
            <Link to={`/automation/filters/${filter.id}`} aria-label={`Edit ${filter.name}`} title="Edit">
              <Pencil />
            </Link>
          </Button>
          <Switch
            checked={active}
            disabled={update.isPending}
            onCheckedChange={toggle}
            aria-label={active ? `Deactivate ${filter.name}` : `Activate ${filter.name}`}
          />
        </div>
      }
      meta={
        <>
          <span className="inline-flex items-center gap-1">
            Adds
            <LabelDot color={filter.label.color} />
            <span className="font-medium text-foreground">{filter.label.display_name}</span>
          </span>
          <MetaDot />
          {filter.last_matched_at ? (
            <span>
              Last match{' '}
              <time dateTime={filter.last_matched_at} title={formatDateTime(filter.last_matched_at)}>
                {formatRelative(filter.last_matched_at)}
              </time>
            </span>
          ) : (
            <span>No matches yet</span>
          )}
        </>
      }
    >
      {filter.description && <p className="truncate text-sm text-muted-foreground">{filter.description}</p>}
      <p className="line-clamp-2 text-xs text-muted-foreground">{summarizeRule(filter.rule, catalogue)}</p>
    </ItemRow>
  )
}
