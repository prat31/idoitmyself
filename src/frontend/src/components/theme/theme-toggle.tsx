import { Moon, Sun } from 'lucide-react'

import { Switch } from '@/components/ui/switch'
import { cn } from '@/lib/utils'
import { useTheme } from './theme-provider'

/** Day/night toggle: sun icon, switch, moon icon. The icon for the active mode is emphasised. */
export function ThemeToggle({ className }: { className?: string }) {
  const { theme, toggleTheme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <div className={cn('flex items-center gap-2.5', className)}>
      <Sun
        aria-hidden="true"
        className={cn('size-4 transition-colors', isDark ? 'text-muted-foreground' : 'text-foreground')}
        strokeWidth={1.75}
      />
      <Switch checked={isDark} onCheckedChange={toggleTheme} aria-label="Dark mode" />
      <Moon
        aria-hidden="true"
        className={cn('size-4 transition-colors', isDark ? 'text-foreground' : 'text-muted-foreground')}
        strokeWidth={1.75}
      />
    </div>
  )
}
