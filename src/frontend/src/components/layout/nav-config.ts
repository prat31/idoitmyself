import type { ComponentType } from 'react'
import { Cable, Cog, House, Inbox, LayoutDashboard, ListFilter, ScanSearch, Tag, Workflow, type LucideIcon } from 'lucide-react'

import { useFilters } from '@/features/filters/api'
import { useInboxes } from '@/features/inboxes/api'
import { useLabels } from '@/features/labels/api'
import { useProcessors } from '@/features/processors/api'
import { useScans } from '@/features/scans/api'
import { ScansActivityIndicator } from '@/features/scans/scans-activity-indicator'

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
  /** A hook giving how many items the page lists, shown muted at the end of the item (undefined while
   *  loading). */
  useCount?: () => number | undefined
}

type NavSectionBase = {
  id: string
  label: string
  icon: LucideIcon
}

export type NavSection =
  | (NavSectionBase & { path: string; subSections?: never }) // a link, e.g. Home
  | (NavSectionBase & { subSections: NavSubSection[]; path?: never }) // a heading over its pages

export const navSections: NavSection[] = [
  {
    id: 'home',
    label: 'Home',
    icon: House,
    path: '/home',
  },
  {
    id: 'dashboards',
    label: 'Dashboards',
    icon: LayoutDashboard,
    path: '/dashboards',
  },
  {
    id: 'automation',
    label: 'Automation',
    icon: Workflow,
    subSections: [
      {
        id: 'automation.scans',
        label: 'Scans',
        icon: ScanSearch,
        path: '/automation/scans',
        indicator: ScansActivityIndicator,
        // Same query as the Scans page's first page, so the two share the cache.
        useCount: () => useScans(1, 25).data?.total,
      },
      {
        id: 'automation.labels',
        label: 'Labels',
        icon: Tag,
        path: '/automation/labels',
        useCount: () => useLabels().data?.length,
      },
      {
        id: 'automation.filters',
        label: 'Filters',
        icon: ListFilter,
        path: '/automation/filters',
        useCount: () => useFilters().data?.length,
      },
      {
        id: 'automation.processors',
        label: 'Processors',
        icon: Cog,
        path: '/automation/processors',
        useCount: () => useProcessors().data?.length,
      },
    ],
  },
  {
    id: 'connections',
    label: 'Connections',
    icon: Cable,
    subSections: [
      {
        id: 'connections.inbox',
        label: 'Inboxes',
        icon: Inbox,
        path: '/connections/inbox',
        useCount: () => useInboxes().data?.length,
      },
    ],
  },
]
