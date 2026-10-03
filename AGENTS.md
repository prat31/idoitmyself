# Agent Guidelines

Welcome to `idoitmyself`. This document defines the operating rules, repository map, and placement guidelines for AI coding assistants working in this repository.

## Repository Map & File Placement

Always respect the directory boundaries outlined below when creating or modifying files:

| Directory / File | Responsibility | What Belongs Here |
| :--- | :--- | :--- |
| `README.md` | Human-facing project overview | Quickstart, installation, setup instructions, project goals. |
| `AGENTS.md` | AI operating manual | Operational guidelines, repository map, agent rules (this file). |
| `.ai/` | Agent context & design guidelines | Machine-readable context for AI assistants. |
| `.ai/architecture.md` | System design & structure | High-level architecture, module boundaries, data flow. |
| `.ai/conventions.md` | Coding standards | Style guides, naming conventions, patterns, error handling rules. |
| `.ai/decisions/` | Architectural Decision Records | ADRs documenting why key decisions were made. |
| `docs/` | Human documentation | Long-form documentation for maintainers and users. |
| `docs/architecture/` | Deep technical specifications | In-depth technical specs, component diagrams, schema contracts. |
| `docs/guides/` | Developer and user guides | Onboarding, deployment, contributing, recipes, tutorials. |
| `src/` | Production source code | Core application logic, domain models, CLI/API entry points. |
| `tests/` | Automated test suites | Unit tests, integration tests, end-to-end tests, and fixtures. |
| `scripts/` | Developer tooling & automation | Setup, build, migration, linting, and release helper scripts. |

## Core Rules for Agents

1. **Strict File Placement**: Never dump temporary scripts or test files in the root directory. Source code belongs in `src/`, automated tests in `tests/`, and helper scripts in `scripts/`.
2. **Consult `.ai/` Context First**: Before making architectural changes or introducing patterns, review [.ai/architecture.md](file:///Users/prat/repos/idoitmyself/.ai/architecture.md) and [.ai/conventions.md](file:///Users/prat/repos/idoitmyself/.ai/conventions.md).
3. **Document Major Decisions**: When introducing significant libraries, architectural changes, or new paradigms, record the rationale in `.ai/decisions/` as a lightweight ADR.
4. **Maintain Documentation Parity**: Keep `README.md`, `docs/`, and `.ai/` files synchronized with code changes. If a CLI command, configuration, or API changes, update the relevant documentation immediately.
5. **Test Coverage**: Accompany all new logic in `src/` with corresponding tests in `tests/`.
