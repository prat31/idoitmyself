import { createBrowserRouter, Navigate } from 'react-router'

import { AppShell } from '@/components/layout/app-shell'
import { DashboardPage } from '@/features/dashboard/dashboard-page'
import { InboxesPage } from '@/features/inboxes/inboxes-page'
import { LabelDetailPage } from '@/features/labels/label-detail-page'
import { LabelsPage } from '@/features/labels/labels-page'
import { RunDetailPage } from '@/features/runs/run-detail-page'
import { RunsPage } from '@/features/runs/runs-page'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: 'dashboard', element: <DashboardPage /> },
      // Old Overview links land on the Dashboard, which replaced it.
      { path: 'discovery/overview', element: <Navigate to="/dashboard" replace /> },
      { path: 'connections/inbox', element: <InboxesPage /> },
      { path: 'discovery/labels', element: <LabelsPage /> },
      { path: 'discovery/labels/:labelId', element: <LabelDetailPage /> },
      { path: 'discovery/runs', element: <RunsPage /> },
      { path: 'discovery/runs/:runId', element: <RunDetailPage /> },
      { path: '*', element: <Navigate to="/" replace /> },
    ],
  },
])
