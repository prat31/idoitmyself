import { Outlet } from 'react-router'

import { AppSidebar } from './app-sidebar'
import { MobileTopBar } from './mobile-top-bar'

export function AppShell() {
  return (
    <div className="flex h-svh overflow-hidden bg-background">
      <AppSidebar />
      <main className="flex min-w-0 flex-1 flex-col overflow-y-auto">
        <MobileTopBar />
        <Outlet />
      </main>
    </div>
  )
}
