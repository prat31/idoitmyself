import logoUrl from '@/assets/logo.svg'
import { cn } from '@/lib/utils'

/** IDIM wordmark (source: media/logo.svg, viewBox cropped to the letterforms). Inverted in dark mode so the graphite artwork stays visible. */
export function Logo({ className, showTagline = true }: { className?: string; showTagline?: boolean }) {
  return (
    <div className={cn('flex flex-col gap-1.5', className)}>
      <img src={logoUrl} alt="IDIM" className="h-7 w-auto self-start dark:invert" />
      {showTagline && (
        <span className="text-[11px] font-medium tracking-wide text-muted-foreground">I Do It Myself</span>
      )}
    </div>
  )
}
