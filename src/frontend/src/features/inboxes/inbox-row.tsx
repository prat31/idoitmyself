import { Figure, ItemRow } from '@/components/layout/item-list'
import { Badge } from '@/components/ui/badge'
import { formatDate } from '@/lib/format'
import type { Inbox } from './api'
import { providerById } from './providers'

/** One inbox as a list row: name, provider and address; notes; tags; connected date on the right. */
export function InboxRow({ inbox }: { inbox: Inbox }) {
  const provider = providerById[inbox.provider]
  const Icon = provider.icon

  return (
    <ItemRow
      leading={
        <span className="flex size-9 items-center justify-center rounded-lg bg-secondary">
          <Icon className="size-[18px]" strokeWidth={1.75} />
        </span>
      }
      title={inbox.name}
      badges={
        <Badge variant="outline" className="text-muted-foreground">
          {provider.label}
        </Badge>
      }
      figures={
        <Figure
          value={
            <span className="inline-flex items-center gap-1.5">
              <span className="size-1.5 rounded-full bg-success" aria-hidden="true" />
              {formatDate(inbox.connected_at)}
            </span>
          }
          label="Connected"
        />
      }
      meta={
        inbox.tags.length > 0 && (
          <span className="flex flex-wrap gap-1.5">
            {inbox.tags.map((tag) => (
              <Badge key={tag.id}>{tag.name}</Badge>
            ))}
          </span>
        )
      }
    >
      <p className="truncate text-sm text-muted-foreground">{inbox.email_address}</p>
      {inbox.notes && <p className="line-clamp-2 text-sm text-muted-foreground">{inbox.notes}</p>}
    </ItemRow>
  )
}
