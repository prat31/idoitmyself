import { createBrowserRouter, createHashRouter, Navigate } from 'react-router'

import { AppShell } from '@/components/layout/app-shell'
import { DashboardPage } from '@/features/dashboards/dashboard-page'
import { DashboardsPage } from '@/features/dashboards/dashboards-page'
import { HomePage } from '@/features/home/home-page'
import { FilterEditorPage } from '@/features/filters/filter-editor-page'
import { FiltersPage } from '@/features/filters/filters-page'
import { InboxesPage } from '@/features/inboxes/inboxes-page'
import { LabelDetailPage } from '@/features/labels/label-detail-page'
import { LabelsPage } from '@/features/labels/labels-page'
import { ProcessorDetailPage } from '@/features/processors/processor-detail-page'
import { ProcessorsPage } from '@/features/processors/processors-page'
import { ScansPage } from '@/features/scans/scans-page'

const routes = [
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <Navigate to="/home" replace /> },
      { path: 'home', element: <HomePage /> },
      { path: 'dashboards', element: <DashboardsPage /> },
      { path: 'dashboards/:dashboardId', element: <DashboardPage /> },
      { path: 'connections/inbox', element: <InboxesPage /> },
      { path: 'automation/filters', element: <FiltersPage /> },
      { path: 'automation/filters/new', element: <FilterEditorPage /> },
      { path: 'automation/filters/:filterId', element: <FilterEditorPage /> },
      { path: 'automation/labels', element: <LabelsPage /> },
      { path: 'automation/labels/:labelId', element: <LabelDetailPage /> },
      { path: 'automation/processors', element: <ProcessorsPage /> },
      { path: 'automation/processors/:processorId', element: <ProcessorDetailPage /> },
      { path: 'automation/scans', element: <ScansPage /> },
      { path: '*', element: <Navigate to="/" replace /> },
    ],
  },
]

/** The public read-only demo uses hash URLs so its static GitHub Pages artifact needs no server-side
 * route fallback. The normal self-hosted application always uses ordinary browser URLs. */
export const router = window.__IDIM_DEMO_MODE__ ? createHashRouter(routes) : createBrowserRouter(routes)
