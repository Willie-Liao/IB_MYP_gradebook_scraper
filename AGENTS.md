# IB MYP Gradebook Scraper — Agent Instructions

## Refactor goal

Single **GUI-only** entry point (`python -m src.gui`): login, two-page scrape, student picker, Excel export.

### Login

Follow the login pattern (URL-derived school, env credentials):

- User supplies a ManageBac URL, email, and password (or `MANAGEBAC_EMAIL` / `MANAGEBAC_PASSWORD` env vars).
- Derive `school_code` and domain from the URL via `parse_school_from_url` — do **not** require a separate school-code field.
- Authenticate with `requests` + CSRF; reuse or align with `src/auth.py` session handling where practical.

### Data to scrape (two pages)

After login, fetch data from the **term gradebook** for a class/term. Navigation:

| Page | Link pattern | Purpose |
|------|--------------|---------|
| **Term Grades** | `/teacher/classes/{class_id}/gradebook/term/{term_id}/myp-term-grades` | Per-student final grade + criterion A–D scores |
| **Tasks** | `/teacher/classes/{class_id}/gradebook/term/{term_id}/tasks` | Assessment columns, per-student criterion scores and comments |

#### Term Grades page (`myp-term-grades`)

For **each student** (repeat for all `.fusion-card.student-grade` cards):

| Field | Selector hint |
|-------|----------------|
| Student name | `h4.student-name a.text-break` (e.g. `AN, CHENGCHENG`) |
| Final grade (out of 8) | `div.final-grade p.js-final-grade-final` (e.g. `7`) |
| Criterion A | `.criteria-grade .form-group` containing `A:` |
| Criterion B | `.criteria-grade .form-group` containing `B:` |
| Criterion C | `.criteria-grade .form-group` containing `C:` |
| Criterion D | `.criteria-grade .form-group` containing `D:` |

Each criterion block lists scores `N/A 0 1 2 3 4 5 6 7 8` — extract the **selected** value.

#### Tasks page (`tasks`)

- Task headers: `.grid-table.gradebook-tasks .task-panel` / `.task-name` (e.g. *Criteria A Dancing*, *Criterion B&C Dancing*, *Criterion D Reflection*, *10th Grade Culture Trip*).
- Per student row: criterion scores and **comments** tied to each task column (existing `ScoreExtractor` / task-grid logic may be reusable).

### Export

Produce Excel (or equivalent) with: student name, final term grade, criterion A–D from term-grades page, plus per-task criterion scores and comments from the tasks page.

### Out of scope for the refactor

- CLI entry point (`python -m src.main`) — removed; GUI only.
- Scraping only the tasks page without term-grades criterion data.

---

## Hook: GitNexus code intelligence

**Trigger:** The user's question is related to **code** — including reading, understanding, modifying, debugging, refactoring, testing, or architecture of this repository.

**Action:** Before answering or editing, use the **GitNexus MCP** server (`user-gitnexus`). Follow the rules in the block below. Prefer `query` and `context` over blind grepping; run `impact` before edits; run `detect_changes` before commits.

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **IB_MYP_gradebook_scraper** (520 symbols, 874 relationships, 29 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> Index stale? Run `node .gitnexus/run.cjs analyze` from the project root — it auto-selects an available runner. No `.gitnexus/run.cjs` yet? `npx gitnexus analyze` (npm 11 crash → `npm i -g gitnexus`; #1939).

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows. For regression review, compare against the default branch: `detect_changes({scope: "compare", base_ref: "main"})`.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `rename` which understands the call graph.
- NEVER commit changes without running `detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/IB_MYP_gradebook_scraper/context` | Codebase overview, check index freshness |
| `gitnexus://repo/IB_MYP_gradebook_scraper/clusters` | All functional areas |
| `gitnexus://repo/IB_MYP_gradebook_scraper/processes` | All execution flows |
| `gitnexus://repo/IB_MYP_gradebook_scraper/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
