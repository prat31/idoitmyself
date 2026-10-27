import { ArrowRight, Check, Code2, Database, Mail, Server, ShieldCheck, TimerReset } from 'lucide-react'
import { createRoot } from 'react-dom/client'
import type { LucideIcon } from 'lucide-react'
import { Logo } from '@/components/brand/logo'
import './index.css'
import { ThemeToggle, useTheme } from './theme'

const sourceUrl = 'https://github.com/prat31/idoitmyself'

function Marketing() {
  const theme = useTheme()
  return <div className="min-h-screen">
    <header className="sticky top-0 z-20 border-b bg-background/95 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 md:px-8">
        <a href="/" aria-label="IDIM home"><Logo /></a>
        <nav className="hidden items-center gap-6 text-sm text-muted-foreground md:flex"><a href="#how-it-works" className="hover:text-foreground">How it works</a><a href="#architecture" className="hover:text-foreground">Architecture</a><a href="#self-host" className="hover:text-foreground">Self-host</a></nav>
        <ThemeToggle {...theme} />
      </div>
    </header>
    <main>
      <section className="mx-auto grid max-w-6xl gap-12 px-4 py-18 md:grid-cols-[1.08fr_.92fr] md:px-8 md:py-28">
        <div className="flex flex-col justify-center">
          <p className="mb-5 text-sm font-medium text-muted-foreground">Mailbox automation, under your control.</p>
          <h1 className="max-w-3xl font-serif text-5xl font-semibold leading-[.98] tracking-tight md:text-7xl">Make the inbox work for you.</h1>
          <p className="mt-7 max-w-xl text-lg leading-8 text-muted-foreground">IDIM is a self-hosted mailbox app. Define filters, label what matters, and let deterministic processors turn statements and receipts into dashboards. Your email stays in your infrastructure.</p>
          <div className="mt-9 flex flex-wrap gap-3"><a href="/demo/" className="inline-flex items-center rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:opacity-90">Explore the demo <ArrowRight className="ml-2 size-4" /></a><a href={sourceUrl} target="_blank" rel="noreferrer" className="inline-flex items-center rounded-md border bg-card px-4 py-2.5 text-sm font-medium hover:bg-secondary">View source <GitHubIcon className="ml-2 size-4" /></a></div>
          <p className="mt-4 text-xs text-muted-foreground">No hosted service. Your mailbox, your infrastructure, your rules.</p>
        </div>
        <div className="rounded-xl border bg-card p-4 shadow-sm md:p-5">
          <div className="border-b pb-4 text-sm font-medium">Inbox pulse</div>
          <div className="grid grid-cols-2 gap-px overflow-hidden rounded-lg border bg-border mt-4"><Metric value="12,482" label="Emails scanned" /><Metric value="5" label="Active filters" /><Metric value="1,846" label="Labelled" /><Metric value="96" label="Scans completed" /></div>
          <div className="mt-4 rounded-lg border p-4"><div className="mb-4 flex items-center justify-between text-sm"><span className="font-medium">Email activity</span><span className="text-muted-foreground">Last 14 days</span></div><div className="flex h-24 items-end gap-1.5">{[28, 40, 32, 60, 46, 74, 54, 86, 65, 78, 52, 91, 70, 82].map((height, i) => <span key={i} className="flex-1 rounded-t-sm bg-primary/85" style={{ height: `${height}%` }} />)}</div></div>
        </div>
      </section>
      <section id="how-it-works" className="border-y bg-card"><div className="mx-auto max-w-6xl px-4 py-20 md:px-8"><p className="text-sm font-medium text-muted-foreground">A calm, deliberate workflow</p><h2 className="mt-3 max-w-2xl font-serif text-4xl font-semibold tracking-tight md:text-5xl">From incoming mail to useful context.</h2><div className="mt-12 grid gap-8 md:grid-cols-3"><Step icon={Mail} number="01" title="Connect mailboxes" text="Connect the mailboxes you want IDIM to watch. Mailbox types keep integrations separate while the rest of IDIM stays provider-agnostic." /><Step icon={Code2} number="02" title="Define filters" text="Combine sender, subject, attachment, header and provider fields with AND / OR logic, and choose whole mailbox types or individual inboxes. Each matching email gets its label." /><Step icon={TimerReset} number="03" title="Process and see" text="Deterministic processors read labelled statements and receipts, write records to datasets, and dashboards chart dues, spend and fees. Home shows trends and what needs attention; notifications keep you posted." /></div></div></section>
      <section className="mx-auto max-w-6xl px-4 py-20 md:px-8"><div className="grid gap-12 md:grid-cols-[.8fr_1.2fr]"><div><p className="text-sm font-medium text-muted-foreground">Capabilities</p><h2 className="mt-3 font-serif text-4xl font-semibold tracking-tight">Built for a mailbox that stays yours.</h2></div><div className="grid gap-x-10 gap-y-7 sm:grid-cols-2"><Capability title="Rules with real logic" text="Nested groups, AND / OR precedence, regexes, boolean and numeric conditions. Filters are live when created, can be paused, and apply to whole mailbox types or individual inboxes." /><Capability title="Labels, not lock-in" text="Labels belong to IDIM, not a provider. They are reusable across every connected inbox, with a colour for quick scanning." /><Capability title="Two kinds of scan" text="Scheduled scans run at fixed boundaries (default every 3 hours); deliberate ad hoc scans examine a selected past range." /><Capability title="Processors, not prompts" text="Plain code against a small SDK. When an email gets a processor’s label, it runs once, writes records, can request a notification or ask you for a missing password." /><Capability title="Dashboards from records" text="Every processor gets a dashboard built from its datasets: dues by month, spend by category, top merchants. Home brings trends, breakdowns and what needs attention together, and the Emails window searches the stored emails behind them." /><Capability title="AI only where you ask" text="Natural-language filter conditions are opt-in per filter and decided by Jev, TypeSafe’s System One model. Processors stay deterministic code and never send email to an AI." /><Capability title="Starts with defaults" text="A fresh install already has the credit-card bill label, filter and processor. Edit or pause them; built-in defaults can't be deleted." /><Capability title="Practical safeguards" text="Read-only Gmail access, encrypted tokens at rest, quota budgeting, bounded retries, and in-app notifications (plus Telegram when configured). Bodies are never stored permanently." /></div></div></section>
      <section id="architecture" className="border-y bg-card"><div className="mx-auto max-w-6xl px-4 py-20 md:px-8"><p className="text-sm font-medium text-muted-foreground">Architecture</p><h2 className="mt-3 font-serif text-4xl font-semibold tracking-tight">Self-hosted by design.</h2><p className="mt-4 max-w-2xl leading-7 text-muted-foreground">IDIM keeps the application, its job queue and its data inside your environment. The browser talks to FastAPI; workers scan mail on a fixed cadence.</p><div className="mt-10 grid gap-3 md:grid-cols-4"><Architecture icon={Server} title="Web" body="React · TypeScript · Vite" /><Architecture icon={Code2} title="API" body="FastAPI · SQLAlchemy async" /><Architecture icon={TimerReset} title="Workers" body="Celery · RabbitMQ · Redis" /><Architecture icon={Database} title="Data" body="PostgreSQL · records & encrypted tokens" /></div></div></section>
      <section id="self-host" className="mx-auto max-w-6xl px-4 py-20 md:px-8"><div className="rounded-xl bg-primary px-6 py-12 text-primary-foreground md:px-12"><ShieldCheck className="size-6" /><h2 className="mt-6 max-w-2xl font-serif text-4xl font-semibold tracking-tight">Useful automation should not require handing over your mailbox.</h2><p className="mt-4 max-w-xl leading-7 text-primary-foreground/70">Run the complete stack with Docker Compose. Review the code, configure your own OAuth client, and keep operational control from connection to storage.</p><div className="mt-8 flex flex-wrap gap-3"><a href={sourceUrl} target="_blank" rel="noreferrer" className="inline-flex items-center rounded-md bg-card px-4 py-2.5 text-sm font-medium text-foreground">Read the source <Code2 className="ml-2 size-4" /></a><a href="/demo/" className="inline-flex items-center rounded-md border border-primary-foreground/30 px-4 py-2.5 text-sm font-medium hover:bg-card/10">Open demo <ArrowRight className="ml-2 size-4" /></a></div></div></section>
    </main>
    <footer className="border-t"><div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-8 text-sm text-muted-foreground md:flex-row md:items-center md:justify-between md:px-8"><span>© {new Date().getFullYear()} IDIM — I Do It Myself</span><a href={sourceUrl} target="_blank" rel="noreferrer" className="hover:text-foreground">GitHub</a></div></footer>
  </div>
}

function GitHubIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" className={className}>
      <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.108-.775.418-1.305.762-1.605-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.51 11.51 0 0 1 12 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.91 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222 0 1.606-.014 2.898-.014 3.293 0 .322.216.694.825.576C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12" />
    </svg>
  )
}

function Metric({ value, label }: { value: string; label: string }) { return <div className="bg-card p-4"><p className="text-2xl font-semibold">{value}</p><p className="mt-1 text-xs text-muted-foreground">{label}</p></div> }
function Step({ icon: Icon, number, title, text }: { icon: LucideIcon; number: string; title: string; text: string }) { return <div className="border-t pt-5"><div className="flex items-center justify-between"><Icon className="size-5" /><span className="text-sm text-muted-foreground">{number}</span></div><h3 className="mt-8 text-lg font-medium">{title}</h3><p className="mt-2 leading-7 text-muted-foreground">{text}</p></div> }
function Capability({ title, text }: { title: string; text: string }) { return <div><Check className="size-4 text-success" /><h3 className="mt-3 font-medium">{title}</h3><p className="mt-1 text-sm leading-6 text-muted-foreground">{text}</p></div> }
function Architecture({ icon: Icon, title, body }: { icon: LucideIcon; title: string; body: string }) { return <div className="rounded-lg border p-5"><Icon className="size-5" /><p className="mt-8 font-medium">{title}</p><p className="mt-1 text-sm text-muted-foreground">{body}</p></div> }

createRoot(document.getElementById('root')!).render(<Marketing />)
