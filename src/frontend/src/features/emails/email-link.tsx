import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

/** Row classes for an email list item whose subject is an `EmailLink`: positions the stretched link
 *  and gives the row a hover state. */
export const emailRowClass = 'relative transition-colors hover:bg-accent/40 has-[a:focus-visible]:bg-accent/40'

/** The email's subject, linking to the message in its provider's web UI (new tab). Stretched over
 *  the whole row (the row needs `emailRowClass`); other links in the row need `relative z-10`. */
export function EmailLink({ url, children, className }: { url: string | null; children: ReactNode; className?: string }) {
  if (!url) return <span className={className}>{children}</span>
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      title="Open the email in a new tab"
      className={cn('outline-none after:absolute after:inset-0', className)}
    >
      {children}
    </a>
  )
}
