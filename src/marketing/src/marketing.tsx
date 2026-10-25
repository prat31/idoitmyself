import { ArrowRight, Check, Code2, Database, Mail, Server, ShieldCheck, TimerReset } from 'lucide-react'
import { createRoot } from 'react-dom/client'
import type { LucideIcon } from 'lucide-react'
import './index.css'
import { ThemeToggle, useTheme } from './theme'

const sourceUrl = 'https://github.com/prat31/idoitmyself'

function Wordmark() { return <a href="/" className="font-serif text-2xl font-semibold tracking-tight">IDIM<span className="text-muted-foreground">.</span></a> }

function Marketing() {
  const theme = useTheme()
  return <div className="min-h-screen">
    <header className="sticky top-0 z-20 border-b bg-background/95 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 md:px-8">
        <Wordmark />
        <nav className="hidden items-center gap-6 text-sm text-muted-foreground md:flex"><a href="#how-it-works" className="hover:text-foreground">How it works</a><a href="#architecture" className="hover:text-foreground">Architecture</a><a href="#self-host" className="hover:text-foreground">Self-host</a></nav>
        <ThemeToggle {...theme} />
      </div>
    </header>
    <main>
      <section className="mx-auto grid max-w-6xl gap-12 px-4 py-18 md:grid-cols-[1.08fr_.92fr] md:px-8 md:py-28">
        <div className="flex flex-col justify-center">
          <p className="mb-5 text-sm font-medium text-muted-foreground">Mailbox automation, under your control.</p>
          <h1 className="max-w-3xl font-serif text-5xl leading-[.98] tracking-tight md:text-7xl">Make the inbox work for you.</h1>
          <p className="mt-7 max-w-xl text-lg leading-8 text-muted-foreground">IDIM is a self-hosted mailbox app. Define rules in plain terms, label the email that matters, and see the patterns your inbox has been hiding.</p>
          <div className="mt-9 flex flex-wrap gap-3"><a href="/demo/" className="inline-flex items-center rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:opacity-90">Explore the demo <ArrowRight className="ml-2 size-4" /></a><a href={sourceUrl} target="_blank" rel="noreferrer" className="inline-flex items-center rounded-md border bg-card px-4 py-2.5 text-sm font-medium hover:bg-secondary">View source <Code2 className="ml-2 size-4" /></a></div>
          <p className="mt-4 text-xs text-muted-foreground">No hosted service. Your mailbox, your infrastructure, your rules.</p>
        </div>
        <div className="rounded-xl border bg-card p-4 shadow-sm md:p-5">
          <div className="flex items-center justify-between border-b pb-4 text-sm"><span className="font-medium">Inbox pulse</span><span className="inline-flex items-center gap-2 text-muted-foreground"><span className="size-2 rounded-full bg-success" /> Next scan in 12 min</span></div>
          <div className="grid grid-cols-2 gap-px overflow-hidden rounded-lg border bg-border mt-4"><Metric value="12,482" label="Emails scanned" /><Metric value="1,846" label="Labelled" /><Metric value="8" label="Active filters" /><Metric value="96" label="Scans completed" /></div>
          <div className="mt-4 rounded-lg border p-4"><div className="mb-4 flex items-center justify-between text-sm"><span className="font-medium">Email activity</span><span className="text-muted-foreground">Last 14 days</span></div><div className="flex h-24 items-end gap-1.5">{[28, 40, 32, 60, 46, 74, 54, 86, 65, 78, 52, 91, 70, 82].map((height, i) => <span key={i} className="flex-1 rounded-t-sm bg-primary/85" style={{ height: `${height}%` }} />)}</div></div>
        </div>
      </section>
      <section id="how-it-works" className="border-y bg-card"><div className="mx-auto max-w-6xl px-4 py-20 md:px-8"><p className="text-sm font-medium text-muted-foreground">A calm, deliberate workflow</p><h2 className="mt-3 max-w-2xl font-serif text-4xl tracking-tight md:text-5xl">From incoming mail to useful context.</h2><div className="mt-12 grid gap-8 md:grid-cols-3"><Step icon={Mail} number="01" title="Connect mailboxes" text="Connect the mailboxes you want IDIM to watch. Mailbox types keep integrations separate while the rest of IDIM stays provider-agnostic." /><Step icon={Code2} number="02" title="Define filters" text="Combine sender, subject, attachment, header and provider fields with AND / OR logic. Each matching email gets its label." /><Step icon={TimerReset} number="03" title="See what matters" text="Scheduled scans keep labels fresh. Dashboard trends, breakdowns and exploration turn stored metadata into a clear picture." /></div></div></section>
      <section className="mx-auto max-w-6xl px-4 py-20 md:px-8"><div className="grid gap-12 md:grid-cols-[.8fr_1.2fr]"><div><p className="text-sm font-medium text-muted-foreground">Capabilities</p><h2 className="mt-3 font-serif text-4xl tracking-tight">Built for a mailbox that stays yours.</h2></div><div className="grid gap-x-10 gap-y-7 sm:grid-cols-2"><Capability title="Rules with real logic" text="Nested groups, AND / OR precedence, regexes, boolean and numeric conditions." /><Capability title="Labels, not lock-in" text="Labels belong to IDIM, not a provider. They are reusable across every connected inbox." /><Capability title="Two kinds of scan" text="Scheduled scans handle new mail; deliberate ad hoc scans examine a selected past range." /><Capability title="Practical safeguards" text="Read-only Gmail access, encrypted tokens at rest, quota budgeting and bounded retries." /></div></div></section>
      <section id="architecture" className="border-y bg-card"><div className="mx-auto max-w-6xl px-4 py-20 md:px-8"><p className="text-sm font-medium text-muted-foreground">Architecture</p><h2 className="mt-3 font-serif text-4xl tracking-tight">Self-hosted by design.</h2><p className="mt-4 max-w-2xl leading-7 text-muted-foreground">IDIM keeps the application, its job queue and its data inside your environment. The browser talks to FastAPI; workers scan mail on a fixed cadence.</p><div className="mt-10 grid gap-3 md:grid-cols-4"><Architecture icon={Server} title="Web" body="React · TypeScript · Vite" /><Architecture icon={Code2} title="API" body="FastAPI · SQLAlchemy async" /><Architecture icon={TimerReset} title="Workers" body="Celery · RabbitMQ · Redis" /><Architecture icon={Database} title="Data" body="PostgreSQL · encrypted tokens" /></div></div></section>
      <section id="self-host" className="mx-auto max-w-6xl px-4 py-20 md:px-8"><div className="rounded-xl bg-primary px-6 py-12 text-primary-foreground md:px-12"><ShieldCheck className="size-6" /><h2 className="mt-6 max-w-2xl font-serif text-4xl tracking-tight">Useful automation should not require handing over your mailbox.</h2><p className="mt-4 max-w-xl leading-7 text-primary-foreground/70">Run the complete stack with Docker Compose. Review the code, configure your own OAuth client, and keep operational control from connection to storage.</p><div className="mt-8 flex flex-wrap gap-3"><a href={sourceUrl} target="_blank" rel="noreferrer" className="inline-flex items-center rounded-md bg-card px-4 py-2.5 text-sm font-medium text-foreground">Read the source <Code2 className="ml-2 size-4" /></a><a href="/demo/" className="inline-flex items-center rounded-md border border-primary-foreground/30 px-4 py-2.5 text-sm font-medium hover:bg-card/10">Open demo <ArrowRight className="ml-2 size-4" /></a></div></div></section>
    </main>
    <footer className="border-t"><div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-8 text-sm text-muted-foreground md:flex-row md:items-center md:justify-between md:px-8"><span>© {new Date().getFullYear()} IDIM — I Do It Myself</span><a href={sourceUrl} target="_blank" rel="noreferrer" className="hover:text-foreground">GitHub</a></div></footer>
  </div>
}

function Metric({ value, label }: { value: string; label: string }) { return <div className="bg-card p-4"><p className="font-serif text-2xl">{value}</p><p className="mt-1 text-xs text-muted-foreground">{label}</p></div> }
function Step({ icon: Icon, number, title, text }: { icon: LucideIcon; number: string; title: string; text: string }) { return <div className="border-t pt-5"><div className="flex items-center justify-between"><Icon className="size-5" /><span className="text-sm text-muted-foreground">{number}</span></div><h3 className="mt-8 text-lg font-medium">{title}</h3><p className="mt-2 leading-7 text-muted-foreground">{text}</p></div> }
function Capability({ title, text }: { title: string; text: string }) { return <div><Check className="size-4 text-success" /><h3 className="mt-3 font-medium">{title}</h3><p className="mt-1 text-sm leading-6 text-muted-foreground">{text}</p></div> }
function Architecture({ icon: Icon, title, body }: { icon: LucideIcon; title: string; body: string }) { return <div className="rounded-lg border p-5"><Icon className="size-5" /><p className="mt-8 font-medium">{title}</p><p className="mt-1 text-sm text-muted-foreground">{body}</p></div> }

createRoot(document.getElementById('root')!).render(<Marketing />)
