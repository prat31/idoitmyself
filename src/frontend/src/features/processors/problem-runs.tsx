import { EmailLink, emailRowClass } from '@/features/emails/email-link'
import { formatDateTime, formatSender } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { RunPage } from './api'
import { InputDialog } from './input-dialog'
import { RunStatusBadge } from './run-status-badge'

/** Runs that wrote nothing (failed, skipped, waiting for input), with why. */
export function ProblemRuns({ data }: { data: RunPage }) {
  if (data.total === 0) return null
  return (
    <section className="rounded-xl border bg-card shadow-xs">
      <header className="border-b px-4 py-3 sm:px-5">
        <h3 className="text-sm font-medium">Needs a look</h3>
      </header>
      <ul className="divide-y">
        {data.items.map((run) => (
          <li
            key={run.id}
            className={cn('flex flex-col gap-2 px-4 py-3 sm:flex-row sm:items-start sm:gap-4 sm:px-5', emailRowClass)}
          >
            <div className="min-w-0 flex-1 space-y-0.5">
              <div className="flex flex-wrap items-center gap-2">
                <RunStatusBadge status={run.status} />
                <p className="min-w-0 truncate text-sm font-medium" title={run.from_address ?? undefined}>
                  {formatSender(run.from_address)}
                </p>
              </div>
              <p className="truncate text-sm">
                <EmailLink url={run.open_url}>{run.subject || '(no subject)'}</EmailLink>
              </p>
              {run.error && <p className="text-xs text-muted-foreground">{run.error}</p>}
            </div>
            <div className="relative z-10 flex shrink-0 items-center gap-3 sm:flex-col sm:items-end sm:gap-1.5">
              <time className="text-xs tabular-nums text-muted-foreground" dateTime={run.sent_at}>
                {formatDateTime(run.sent_at)}
              </time>
              {run.status === 'needs_input' && run.input_name && run.input_scope && (
                <InputDialog
                  name={run.input_name}
                  scope={run.input_scope}
                  prompt={run.input_prompt ?? run.input_name}
                  wrong={run.error?.includes("didn't work")}
                />
              )}
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}
