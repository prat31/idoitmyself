import type { ComponentType } from 'react'
import { Cable, Compass, History, Inbox, LayoutDashboard, Tag, type LucideIcon } from 'lucide-react'

import { RunsActivityIndicator } from '@/features/runs/runs-activity-indicator'

/**
 * Sidebar navigation has at most two levels. A top-level section is either a link itself (`path`, no
 * sub-sections) or a heading over its sub-sections. Sub-sections cannot have children — the types
 * enforce this, so no deeper hierarchy is possible.
 */
export type NavSubSection = {
  id: string
  label: string
  icon: LucideIcon
  /** Route path this sub-section opens. */
  path: string
  /** Optional live status shown at the end of the item (e.g. a spinner while work is in progress). */
  indicator?: ComponentType
}

type NavSectionBase = {
  id: string
  label: string
  icon: LucideIcon
}

export type NavSection =
  | (NavSectionBase & { path: string; subSections?: never }) // a link, e.g. Dashboard
  | (NavSectionBase & { subSections: NavSubSection[]; path?: never }) // a heading over its pages

export const navSections: NavSection[] = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    icon: LayoutDashboard,
    path: '/dashboard',
  },
  {
    id: 'discovery',
    label: 'Discovery',
    icon: Compass,
    subSections: [
      {
        id: 'discovery.runs',
        label: 'Runs',
        icon: History,
        path: '/discovery/runs',
        indicator: RunsActivityIndicator,
      },
      { id: 'discovery.labels', label: 'Labels', icon: Tag, path: '/discovery/labels' },
    ],
  },
  {
    id: 'connections',
    label: 'Connections',
    icon: Cable,
    subSections: [{ id: 'connections.inbox', label: 'Inboxes', icon: Inbox, path: '/connections/inbox' }],
  },
]
