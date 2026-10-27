import { useState } from 'react'
import { Menu } from 'lucide-react'

import { Logo } from '@/components/brand/logo'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from '@/components/ui/sheet'
import { NotificationsBell } from '@/features/notifications/notifications-bell'
import { SidebarContent } from './app-sidebar'

/** Phone-only (below md) header: a menu button that opens the sidebar as a drawer, the logo, and the
 *  notifications bell. */
export function MobileTopBar() {
  const [open, setOpen] = useState(false)

  return (
    <header className="sticky top-0 z-40 flex h-14 shrink-0 items-center gap-2 border-b border-sidebar-border bg-sidebar px-2 md:hidden">
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetTrigger asChild>
          <Button variant="ghost" size="icon" aria-label="Open menu">
            <Menu className="size-5" />
          </Button>
        </SheetTrigger>
        <SheetContent>
          <SheetTitle className="sr-only">Navigation</SheetTitle>
          <SidebarContent onNavigate={() => setOpen(false)} bell={false} />
        </SheetContent>
      </Sheet>
      <Logo showTagline={false} className="[&_img]:h-6" />
      <div className="ml-auto pr-1">
        <NotificationsBell align="end" />
      </div>
    </header>
  )
}
