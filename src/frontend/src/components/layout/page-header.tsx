import type { ReactNode } from 'react'

type PageHeaderProps = {
  title: ReactNode
  description?: ReactNode
  actions?: ReactNode
}

/** Page title block. On phones the actions stack under the title; from sm up they sit to the right. */
export function PageHeader({ title, description, actions }: PageHeaderProps) {
  return (
    <header className="flex flex-col gap-4 border-b px-4 pb-5 pt-6 sm:flex-row sm:items-end sm:justify-between sm:gap-6 md:px-10 md:pb-6 md:pt-10">
      <div className="space-y-1.5">
        <h1 className="font-serif text-2xl font-semibold tracking-tight md:text-3xl">{title}</h1>
        {description && <p className="text-sm text-muted-foreground">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </header>
  )
}
