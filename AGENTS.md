# AGENTS.md

Guidance for AI coding agents working in this repository. Read this fully before doing anything.

## Ground rules (non-negotiable)

1. **Never commit or push.** No `git commit`, `git push`, `git stash`, `git reset`, or anything that rewrites history. The owner handles all git operations.
2. **Never change branches.** No `git checkout`/`git switch`/`git branch` to move off the current branch, and no worktrees.
3. **The owner makes all architectural decisions.** The owner is a senior software engineer and the decision-maker; the agent is the implementer.
   - Do not assume. Do not "be smart" by adding unrequested features, abstractions, libraries, patterns, or refactors.
   - If a requirement is ambiguous or a design choice is needed (data model, API shape, folder structure, new dependency, auth approach, etc.), **stop and ask** before implementing.
   - Implement exactly what was asked, nothing more.

## Tech stack

### Backend (fixed by owner)
- **Language:** Python
- **API framework:** FastAPI
- **Task queue:** Celery
- **Message broker:** RabbitMQ
- **Cache / store:** Redis
- **Database:** PostgreSQL

### Frontend (delegated to agent; owner may override)
- **React + TypeScript**, built with **Vite**
- **Tailwind CSS** for styling
- **shadcn/ui** (Radix primitives) for components; **lucide-react** for icons
- Design bar: elegant, beautiful, pleasing, and **consistent** — one design-token set (colors, spacing, radius, typography) used everywhere; light and dark themes; no one-off styles.

Any library beyond the above requires the owner's approval.

## Repository layout (current)

```
src/
  backend/        # Python / FastAPI service
    tests/
  frontend/       # React / Vite app (src/lib/ is intentionally un-ignored in .gitignore)
.env.example      # Env var template — keep in sync when adding config
```

Existing config in `.env.example` references: PostgreSQL, OpenRouter API key, Google OAuth (Gmail/Drive read-only), backend on `http://localhost:8000` (API prefix `/api/v1`), frontend on `http://localhost:5173`.

## Working conventions

- Never read, print, or edit `.env` / `.env.back` (real secrets). Use `.env.example` for reference and add any new variables there.
- Keep this file updated when the owner makes a decision that future sessions need to know.
