import { CircleHelp } from 'lucide-react'
import { createRoot } from 'react-dom/client'

import './index.css'
import { installDemoApi } from './demo-api'

declare global {
  interface Window {
    __IDIM_DEMO_MODE__?: boolean
  }
}

// The shared app router reads this flag while its modules load and switches to hash URLs. That keeps
// every real route navigable from a static GitHub Pages deployment at /demo/.
window.__IDIM_DEMO_MODE__ = true
installDemoApi()

const { default: App } = await import('../../frontend/src/App.tsx')

function Demo() {
  return (
    <div className="flex h-svh flex-col overflow-hidden">
      <div className="flex shrink-0 items-center justify-center gap-2 border-b border-warning/30 bg-warning px-4 py-2 text-center text-xs font-medium text-warning-foreground shadow-xs">
        <CircleHelp className="size-3.5 shrink-0" />
        <span>
          <strong>Demo mode.</strong> This is a read-only preview with mock data.
        </span>
      </div>
      <div className="min-h-0 flex-1 [&>div]:h-full">
        <App />
      </div>
    </div>
  )
}

createRoot(document.getElementById('root')!).render(<Demo />)
