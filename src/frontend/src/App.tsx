import { ParticleBackground } from './components/ParticleBackground'
import { ExternalLink } from 'lucide-react'

function GithubIcon({ className = 'w-4 h-4' }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" />
      <path d="M9 18c-4.51 2-5-2-7-2" />
    </svg>
  )
}

export default function App() {
  return (
    <div className="relative min-h-screen bg-[#050508] text-slate-200 flex flex-col justify-between items-center selection:bg-cyan-400 selection:text-black overflow-hidden px-6 py-8 sm:py-12">
      {/* Subtle Cosmic Particle Field */}
      <ParticleBackground />

      {/* Very subtle focal glow behind center */}
      <div className="pointer-events-none fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-gradient-to-tr from-cyan-950/20 via-indigo-950/25 to-transparent blur-[140px] rounded-full z-0" />

      {/* Top Header */}
      <header className="relative z-10 w-full max-w-4xl flex items-center justify-between text-xs font-mono">
        <div className="flex items-center gap-2.5">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-60"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-400"></span>
          </span>
          <span className="tracking-[0.2em] uppercase font-medium text-slate-300">
            idoitmyself
          </span>
        </div>

        <span className="text-[11px] font-mono tracking-widest text-slate-600 uppercase">
          stealth mode
        </span>
      </header>

      {/* Suspenseful Centerpiece */}
      <main className="relative z-10 flex flex-col items-center justify-center text-center max-w-2xl mx-auto my-auto py-12">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-900/40 border border-slate-800/60 text-[11px] font-mono tracking-[0.25em] text-slate-400 uppercase mb-8 backdrop-blur-md">
          <span className="h-1 w-1 rounded-full bg-cyan-400"></span>
          <span>project in progress</span>
        </div>

        {/* The One-Liner */}
        <h1 className="text-3xl sm:text-5xl md:text-6xl font-extralight tracking-tight text-balance leading-tight text-white mb-6">
          Building in the dark.
        </h1>

        <p className="text-slate-400 text-sm sm:text-base font-light tracking-wide max-w-md text-pretty">
          Silence is where the real work happens.
        </p>
      </main>

      {/* Discreet Minimalist Footer */}
      <footer className="relative z-10 w-full max-w-4xl flex flex-col sm:flex-row items-center justify-between gap-4 text-xs font-mono text-slate-600 border-t border-slate-900/60 pt-6">
        <span className="tracking-wider text-slate-500">idoitmyself.online</span>
        
        <div className="flex items-center gap-5">
          <a
            href="https://github.com/prat31/idoitmyself"
            target="_blank"
            rel="noopener noreferrer"
            className="text-slate-500 hover:text-slate-300 transition-colors flex items-center gap-1.5"
          >
            <GithubIcon className="w-3.5 h-3.5" />
            <span>github</span>
            <ExternalLink className="w-2.5 h-2.5 opacity-50" />
          </a>
          <span className="text-slate-700">&bull;</span>
          <span className="text-slate-500 tracking-wider">soon</span>
        </div>
      </footer>
    </div>
  )
}
