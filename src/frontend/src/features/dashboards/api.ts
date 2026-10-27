import { keepPreviousData, useQuery } from '@tanstack/react-query'

import { apiFetch } from '@/lib/api'
import type { LabelColor } from '@/features/labels/colors'

export type FieldType = 'text' | 'number' | 'money' | 'date' | 'datetime' | 'bool'
export type FieldRole = 'dimension' | 'measure' | 'time' | 'text'

export type DatasetField = { name: string; title: string; type: FieldType; role: FieldRole; description: string | null }

/** A typed table processors write records into (e.g. cards.statements). */
export type Dataset = {
  name: string
  title: string
  kind: 'event' | 'snapshot'
  time_field: string
  key_field: string | null
  fields: DatasetField[]
}

export type FieldFilter = { field: string; op?: 'in' | 'not_in'; values: string[] }
export type Bucket = 'day' | 'week' | 'month' | 'year'

export type WidgetQuery = {
  dataset: string
  measure: string | null
  agg: 'sum' | 'avg' | 'min' | 'max' | 'count' | 'latest'
  group_by: string | null
  bucket: Bucket | null
  filters: FieldFilter[]
  limit: number | null
  columns: string[] | null
}

export type WidgetType = 'stat' | 'timeseries' | 'composition' | 'breakdown' | 'table'

export type Widget = {
  id: string
  type: WidgetType
  title: string
  description: string | null
  width: 'full' | 'half' | 'third'
  query: WidgetQuery
}

export type DashboardRange = '3m' | '6m' | '12m' | 'all'

/** A processor's dashboard: its kind's spec over that processor's records. */
export type Dashboard = {
  id: string
  name: string
  description: string | null
  processor_status: 'active' | 'inactive'
  kind: string
  kind_name: string
  labels: { id: string; display_name: string; color: LabelColor }[]
  spec: { default_range: DashboardRange; widgets: Widget[] }
}

/** Where a widget's data comes from: the dashboard's processor and date range. */
export type QueryScope = { processor_ids: string[]; start: string | null; end: string | null }

export type SeriesRow = { bucket: string | null; group: string | null; value: number | null }

export type RecordRow = {
  id: string
  occurred_at: string
  processor_id: string | null
  data: Record<string, unknown>
  email: { id: string; subject: string | null; sent_at: string; open_url: string | null } | null
}

export type RowsResult = { items: RecordRow[]; total: number; page: number; page_size: number }

const key = ['dashboards'] as const

export function useDashboards() {
  return useQuery({ queryKey: key, queryFn: () => apiFetch<Dashboard[]>('/dashboards') })
}

export function useDashboard(id: string) {
  return useQuery({ queryKey: [...key, id], queryFn: () => apiFetch<Dashboard>(`/dashboards/${id}`) })
}

export function useDatasets() {
  return useQuery({ queryKey: ['datasets'], queryFn: () => apiFetch<Dataset[]>('/datasets'), staleTime: Infinity })
}

/** Records change as processors run: refresh now and then. */
const REFRESH = 60_000

export function useSeries(query: WidgetQuery, scope: QueryScope | null) {
  const body = { ...query, columns: undefined, ...scope }
  return useQuery({
    queryKey: ['datasets', 'query', body],
    queryFn: () =>
      apiFetch<{ rows: SeriesRow[] }>('/datasets/query', { method: 'POST', body: JSON.stringify(body) }).then(
        (r) => r.rows,
      ),
    enabled: scope !== null,
    placeholderData: keepPreviousData,
    refetchInterval: REFRESH,
  })
}

export function useRows(query: WidgetQuery, scope: QueryScope, page: number, pageSize: number) {
  const body = { dataset: query.dataset, filters: query.filters, ...scope, page, page_size: pageSize }
  return useQuery({
    queryKey: ['datasets', 'rows', body],
    queryFn: () => apiFetch<RowsResult>('/datasets/rows', { method: 'POST', body: JSON.stringify(body) }),
    placeholderData: keepPreviousData,
    refetchInterval: REFRESH,
  })
}
