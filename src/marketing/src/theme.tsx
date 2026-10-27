import { Moon, Sun } from 'lucide-react'
import { useEffect, useState } from 'react'

export function useTheme() {
  const [dark, setDark] = useState(() => localStorage.getItem('idim-theme') === 'dark')
  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
    localStorage.setItem('idim-theme', dark ? 'dark' : 'light')
  }, [dark])
  return { dark, setDark }
}

/** Day/night toggle: sun icon on left, switch in middle, moon icon on right. */
export function ThemeToggle({
  dark,
  setDark,
  className = '',
}: {
  dark: boolean
  setDark: (dark: boolean) => void
  className?: string
}) {
  return (
    <div className={`flex items-center gap-2.5 ${className}`.trim()}>
      <Sun
        aria-hidden="true"
        className={`size-4 transition-colors ${dark ? 'text-muted-foreground' : 'text-foreground'}`}
        strokeWidth={1.75}
      />
      <button
        type="button"
        role="switch"
        aria-checked={dark}
        aria-label="Dark mode"
        onClick={() => setDark(!dark)}
        className={`peer inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full border border-transparent shadow-xs transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring ${
          dark ? 'bg-primary' : 'bg-muted-foreground/40'
        }`}
      >
        <span
          className={`pointer-events-none block size-5 rounded-full bg-background shadow-sm ring-0 transition-transform ${
            dark ? 'translate-x-5' : 'translate-x-0.5'
          }`}
        />
      </button>
      <Moon
        aria-hidden="true"
        className={`size-4 transition-colors ${dark ? 'text-foreground' : 'text-muted-foreground'}`}
        strokeWidth={1.75}
      />
    </div>
  )
}
