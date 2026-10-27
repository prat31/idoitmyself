import { ArrowLeft, ChartColumn, Loader2, Pencil, Play, RotateCcw } from 'lucide-react'
import { Link, useNavigate, useParams } from 'react-router'
import { toast } from 'sonner'

import { StatTile } from '@/components/charts/stat-tile'
import { DefaultBadge } from '@/components/layout/default-badge'
import { ErrorBanner } from '@/components/layout/error-banner'
import { PageBody } from '@/components/layout/page-body'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Switch } from '@/components/ui/switch'
import { LabelDot } from '@/features/labels/label-dot'
import { formatNumber } from '@/lib/format'
import {
  useProcessor,
  useProcessorKinds,
  useProcessorProblemRuns,
  useRerun,
  useRunExisting,
  useUpdateProcessor,
} from './api'
import { DeleteProcessorDialog } from './delete-processor-dialog'
import { ProblemRuns } from './problem-runs'
import { ProcessorDialog } from './processor-dialog'

export function ProcessorDetailPage() {
  const { processorId = '' } = useParams()
  const navigate = useNavigate()

  const processor = useProcessor(processorId)
  // Refreshes with the processor while runs are queued or running.
  const live = processor.data?.runs.active ? 5_000 : undefined
  const problems = useProcessorProblemRuns(processorId, live)
  const kinds = useProcessorKinds()
  const update = useUpdateProcessor()
  const runExisting = useRunExisting()
  const rerunFailed = useRerun('failed')
  const rerunSkipped = useRerun('skipped')

  const queued = (none: string) => ({
    onSuccess: ({ queued }: { queued: number }) =>
      toast.success(queued ? `Queued ${formatNumber(queued)} ${queued === 1 ? 'email' : 'emails'}` : none),
    onError: (error: Error) => toast.error("Couldn't queue the runs", { description: error.message }),
  })

  const backLink = (
    <Link
      to="/automation/processors"
      className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
    >
      <ArrowLeft className="size-4" />
      Processors
    </Link>
  )

  if (processor.isError) {
    return (
      <PageBody>
        <div className="space-y-4">
          {backLink}
          <ErrorBanner
            message={`Couldn't load the processor: ${processor.error.message}`}
            onRetry={() => processor.refetch()}
          />
        </div>
      </PageBody>
    )
  }

  const data = processor.data
  const kind = kinds.data?.find((k) => k.key === data?.kind)
  return (
    <>
      <header className="space-y-4 border-b px-4 pb-5 pt-6 md:px-10 md:pb-6 md:pt-8">
        {backLink}
        {!data ? (
          <Skeleton className="h-9 w-64" />
        ) : (
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start">
            <div className="min-w-0 flex-1 space-y-1">
              <div className="flex min-w-0 items-center gap-3">
                <h1 className="truncate font-serif text-2xl font-semibold tracking-tight md:text-3xl">{data.name}</h1>
                {data.is_default && <DefaultBadge />}
              </div>
              <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted-foreground">
                {data.kind_name} · runs on
                {data.labels.map((label) => (
                  <Link
                    key={label.id}
                    to={`/automation/labels/${label.id}`}
                    className="inline-flex items-center gap-1 text-foreground underline-offset-2 hover:underline"
                  >
                    <LabelDot color={label.color} />
                    {label.display_name}
                  </Link>
                ))}
              </p>
              {data.description && <p className="text-sm text-muted-foreground">{data.description}</p>}
              {kind && (
                <p className="text-xs text-muted-foreground">
                  Writes {kind.writes.map((d) => d.title.toLowerCase()).join(' and ')}.
                </p>
              )}
            </div>
            <div className="flex shrink-0 flex-wrap items-center gap-2">
              {data.has_dashboard && (
                <Button variant="outline" size="sm" asChild>
                  <Link to={`/dashboards/${data.id}`}>
                    <ChartColumn />
                    Dashboard
                  </Link>
                </Button>
              )}
              <Button
                variant="outline"
                size="sm"
                disabled={runExisting.isPending}
                onClick={() => runExisting.mutate(data.id, queued('Every labelled email has been run already'))}
                title="Run on emails that already carry its labels and were never run through it"
              >
                {runExisting.isPending ? <Loader2 className="animate-spin" /> : <Play />}
                Run on existing emails
              </Button>
              {data.runs.failed > 0 && (
                <Button
                  variant="outline"
                  size="sm"
                  disabled={rerunFailed.isPending}
                  onClick={() => rerunFailed.mutate(data.id, queued('No failed runs'))}
                >
                  {rerunFailed.isPending ? <Loader2 className="animate-spin" /> : <RotateCcw />}
                  Re-run failed
                </Button>
              )}
              {data.runs.skipped > 0 && (
                <Button
                  variant="outline"
                  size="sm"
                  disabled={rerunSkipped.isPending}
                  onClick={() => rerunSkipped.mutate(data.id, queued('No skipped runs'))}
                  title="Run skipped emails again, e.g. after a parser for their sender was added"
                >
                  {rerunSkipped.isPending ? <Loader2 className="animate-spin" /> : <RotateCcw />}
                  Re-run skipped
                </Button>
              )}
              <ProcessorDialog
                processor={data}
                trigger={
                  <Button variant="ghost" size="icon" className="size-8 text-muted-foreground" aria-label="Edit processor">
                    <Pencil />
                  </Button>
                }
              />
              {!data.is_default && (
                <DeleteProcessorDialog processor={data} onDeleted={() => navigate('/automation/processors')} />
              )}
              <Switch
                checked={data.status === 'active'}
                disabled={update.isPending}
                onCheckedChange={(checked) =>
                  update.mutate(
                    { id: data.id, changes: { status: checked ? 'active' : 'inactive' } },
                    { onError: (error) => toast.error("Couldn't change the processor", { description: error.message }) },
                  )
                }
                aria-label={data.status === 'active' ? 'Deactivate' : 'Activate'}
              />
            </div>
          </div>
        )}
      </header>

      <PageBody>
        <div className="space-y-4">
          {data && (
            <dl className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              <StatTile
                label="Emails processed"
                value={formatNumber(data.runs.succeeded)}
                hint={`${formatNumber(data.records)} records written`}
              />
              <StatTile label="In progress" value={formatNumber(data.runs.active)} hint="Queued or running" />
              <StatTile label="Needs input" value={formatNumber(data.runs.needs_input)} hint="E.g. a PDF password" />
              <StatTile
                label="Failed"
                value={formatNumber(data.runs.failed)}
                hint={`${formatNumber(data.runs.skipped)} skipped`}
              />
            </dl>
          )}
          {problems.isError ? (
            <ErrorBanner message={`Couldn't load runs: ${problems.error.message}`} onRetry={() => problems.refetch()} />
          ) : problems.data && problems.data.total > 0 ? (
            <ProblemRuns data={problems.data} />
          ) : (
            data &&
            data.runs.succeeded === 0 && (
              <p className="rounded-xl border bg-card px-5 py-10 text-center text-sm text-muted-foreground">
                Nothing processed yet. It runs on emails that get its labels from now on, or on existing ones on request.
              </p>
            )
          )}
        </div>
      </PageBody>
    </>
  )
}
