import { NavLink } from 'react-router'

import { Logo } from '@/components/brand/logo'
import { ThemeToggle } from '@/components/theme/theme-toggle'
import { NotificationsBell } from '@/features/notifications/notifications-bell'
import { cn } from '@/lib/utils'
import { navSections, type NavSection, type NavSubSection } from './nav-config'

/** How many items a sub-section's page lists, muted at the end of the item. Nothing while loading. */
function NavCount({ useCount }: { useCount: () => number | undefined }) {
  const count = useCount()
  if (count === undefined) return null
  return <span className="text-xs tabular-nums text-muted-foreground">{count.toLocaleString()}</span>
}

function SubSectionLink({ item, onNavigate }: { item: NavSubSection; onNavigate?: () => void }) {
  const Icon = item.icon
  const Indicator = item.indicator
  return (
    <NavLink
      to={item.path}
      onClick={onNavigate}
      className={({ isActive }) =>
        cn(
          'group flex w-full items-center gap-2.5 rounded-md px-2.5 py-1.5 text-sm transition-colors',
          'outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring/60',
          isActive
            ? 'bg-sidebar-accent font-medium text-sidebar-accent-foreground'
            : 'text-sidebar-foreground/80 hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground',
        )
      }
    >
      {({ isActive }) => (
        <>
          <Icon
            className={cn('size-4 shrink-0', isActive ? 'text-foreground' : 'text-muted-foreground')}
            strokeWidth={1.75}
          />
          <span className="truncate">{item.label}</span>
          {(item.useCount || Indicator) && (
            <span className="ml-auto flex shrink-0 items-center gap-2">
              {Indicator && <Indicator />}
              {item.useCount && <NavCount useCount={item.useCount} />}
            </span>
          )}
        </>
      )}
    </NavLink>
  )
}

function Section({ section, onNavigate }: { section: NavSection; onNavigate?: () => void }) {
  const Icon = section.icon
  if (section.path !== undefined) {
    // A top-level section that is itself a page (no sub-sections).
    return (
      <NavLink
        to={section.path}
        onClick={onNavigate}
        className={({ isActive }) =>
          cn(
            'flex w-full items-center gap-2.5 rounded-md px-2.5 py-1.5 text-sm font-semibold transition-colors',
            'outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring/60',
            isActive
              ? 'bg-sidebar-accent text-sidebar-accent-foreground'
              : 'text-sidebar-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground',
          )
        }
      >
        {({ isActive }) => (
          <>
            <Icon
              className={cn('size-4 shrink-0', isActive ? 'text-foreground' : 'text-muted-foreground')}
              strokeWidth={1.75}
            />
            <span className="truncate">{section.label}</span>
          </>
        )}
      </NavLink>
    )
  }
  return (
    <div className="space-y-1">
      <div className="flex items-center gap-2.5 px-2.5 py-1.5 text-sm font-semibold text-sidebar-foreground">
        <Icon className="size-4 shrink-0 text-muted-foreground" strokeWidth={1.75} />
        <span className="truncate">{section.label}</span>
      </div>
      {section.subSections.length > 0 && (
        <div className="ml-[17px] space-y-0.5 border-l border-sidebar-border pl-2">
          {section.subSections.map((sub) => (
            <SubSectionLink key={sub.id} item={sub} onNavigate={onNavigate} />
          ))}
        </div>
      )}
    </div>
  )
}

/** Logo (with the notifications bell), navigation and theme toggle. Rendered in the desktop sidebar and
 *  in the mobile drawer, where the bell lives in the top bar instead. */
export function SidebarContent({ onNavigate, bell = true }: { onNavigate?: () => void; bell?: boolean }) {
  return (
    <div className="flex h-full flex-col bg-sidebar text-sidebar-foreground">
      <div className="flex items-start justify-between gap-2 pb-4 pl-5 pr-3 pt-5">
        <Logo />
        {bell && <NotificationsBell />}
      </div>

      <nav className="flex-1 space-y-4 overflow-y-auto px-3 py-2">
        {navSections.map((section) => (
          <Section key={section.id} section={section} onNavigate={onNavigate} />
        ))}
      </nav>

      <div className="border-t border-sidebar-border px-5 py-4">
        <ThemeToggle />
      </div>
    </div>
  )
}

/** Fixed sidebar for tablet and desktop (md and up). On phones the same content lives in a drawer. */
export function AppSidebar() {
  return (
    <aside className="hidden h-full w-64 shrink-0 border-r border-sidebar-border md:block">
      <SidebarContent />
    </aside>
  )
}
