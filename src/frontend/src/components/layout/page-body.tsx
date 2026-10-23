import type { ReactNode } from 'react'

/** Main content area under a PageHeader, with the standard responsive gutters. */
export function PageBody({ children }: { children: ReactNode }) {
  return <div className="px-4 py-6 md:px-10 md:py-8">{children}</div>
}
