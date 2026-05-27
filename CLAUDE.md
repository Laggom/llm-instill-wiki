# CLAUDE.md — LLM Wiki Operating Schema

This file is the **schema** for this wiki. It defines the structure, format, and workflows the LLM must follow when maintaining and extending the wiki. Based on Karpathy's [LLM Wiki pattern](https://gist.github.com/karpathy).

> Principle: the human curates, asks, and sets direction. The LLM writes and maintains the entire wiki.

---

## 0. Language

- This schema is written in English for token efficiency and broad agent compatibility across tools.
- **Respond to the user in Korean (존댓말 — polite form)** unless explicitly told otherwise.
- Wiki page titles, claims, and content may be in any language — match the source. The schema (this file, page frontmatter keys, scheduler IDs) stays in English.
- User commands listed in §8 are in Korean by convention but the LLM should also recognize obvious English equivalents (`ingest X`, `query Q`, `lint`, etc.).

---

## 1. Directory layout

```
.
├── CLAUDE.md          # this file — schema / operating rules (source of truth)
├── AGENTS.md          # pointer → CLAUDE.md (auto-loaded by Cursor / Codex)
├── GEMINI.md          # pointer → CLAUDE.md (auto-loaded by Gemini CLI)
├── README.md          # human-facing intro + agent installation guide
├── install.sh         # setup script (macOS / Linux / WSL)
├── install.ps1        # setup script (Windows PowerShell)
├── tools/
│   └── instill_sched.py   # FSRS-4.5 scheduler (stdlib only)
├── raw/               # source clippings (IMMUTABLE — never edit or delete)
│   ├── *.md           # articles, papers, notes
│   └── assets/        # images / attachments (create if needed)
├── wiki/              # LLM-maintained markdown (mutable)
│   ├── index.md       # full page catalog
│   ├── log.md         # append-only activity log
│   ├── sources/       # one page per raw source
│   ├── concepts/      # ideas, theories, patterns
│   └── entities/      # people, tools, orgs, products
└── instill/           # learning state
    ├── _deck.json     # FSRS card state (machine-owned)
    └── <topic>.md     # narrative coaching notes per topic (lazy-load)
```

New categories such as `wiki/comparisons/` or `wiki/timelines/` may be added later. When adding a category, update this file in the same change.

---

## 2. Page format

### 2.1 YAML frontmatter (required)

```yaml
---
title: Page title
type: source | concept | entity
tags: [tag1, tag2]
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: 1            # how many raw/ sources back this page
status: stub | draft | stable
instill:              # optional — see §4.4
  - id: cc-mem-001
    claim: "single-line testable assertion"
    importance: high | med | low
    solo-target: recall | uni | multi | relational | transfer
    skip: false
---
```

- `type` must match the directory the page sits in.
- For `entities/` pages, add `kind: person | tool | org | product`.
- Bump `updated` and `sources` whenever a new raw source extends the page.

### 2.2 Body structure

```markdown
# Page title

## TL;DR
One sentence summary of what this page covers.

## Body
Free structure. Use subheadings as fits the topic.

## Related
- [[concepts/foo]] — one-line note on the relation
- [[entities/bar]] — one-line note on the relation

## Sources
- [karpathy-llm-wiki](../../raw/karpathy-llm-wiki.md) — what was cited
```

Both Obsidian-style `[[wiki/path/page]]` and plain markdown `[text](path)` are allowed. Be consistent within a page.

---

## 3. Naming

- File names: `kebab-case.md` (ASCII slug). Eases search and linking.
- `title:` in frontmatter may be in any language.
- People pages: `entities/firstname-lastname.md` (e.g., `entities/andrej-karpathy.md`).
- Source pages: file slug must match the raw file 1:1.

---

## 4. Workflows

### 4.1 Ingest — adding a new source

**raw/ stores markdown only.** Non-markdown sources (PDF, HTML, EPUB, etc.) must be converted to markdown before they live in `raw/`. The repo intentionally has no Python conversion dependency.

When the user hands you a non-markdown source, follow this fallback chain:

1. **If your host tool can natively read the format** (Claude Code reads PDFs natively; recent Cursor also does), read it directly and write the markdown into `raw/<slug>.md` yourself. Then proceed with the normal ingest steps below.
2. **If your host tool cannot read the format**, do NOT pip-install anything. Stop and tell the user: "I can't read this file type in this environment. Please convert it to markdown first (e.g., with `pandoc`, `markitdown`, or any web converter) and place it as `raw/<slug>.md`, then ask me again." Resume ingest only after the markdown is in place.

Steps:

1. The user drops (or you create from a converted source) a file at `raw/<slug>.md`.
2. The LLM opens the raw file **read-only** and extracts the key content.
3. Create `wiki/sources/<slug>.md` with summary, key claims, and quotable lines.
4. For each concept, person, or tool mentioned, create or update a page under `wiki/concepts/` or `wiki/entities/`.
5. If new information contradicts something on another page, leave a note on both sides (`> ⚠ YYYY-MM-DD: conflicts with source X, needs reconciliation`).
6. Add new pages to `wiki/index.md`.
7. **Instill card extraction** — for each new or updated page, populate the `instill:` array in its frontmatter with atomic claims (cards). Each card needs `id` (wiki-globally unique, e.g., `cc-mem-001`), `claim` (one line, testable), `importance` (high/med/low), and `solo-target` (recall/uni/multi/relational/transfer). For each new card, call `python tools/instill_sched.py enroll --id <id> --importance <h/m/l> --topic <topic>` to register it in the scheduler.
8. Append an entry to `wiki/log.md` (include new card count).

Touching 10–15 pages during one ingest is normal. Card extraction is automatic and needs no user approval — the user can drop unwanted cards at the start of the next instill session (see §4.4).

### 4.2 Query — answering a question

1. Read `wiki/index.md` first to identify relevant pages.
2. Read those pages and synthesize an answer. Cite every claim with `[[concepts/foo]]` or similar links.
3. **If the synthesized answer has reuse value, promote it to a wiki page.** Comparison tables, analyses, newly discovered connections — save to `wiki/concepts/<topic>-vs-<topic>.md` or `wiki/concepts/<insight>.md` and update index + log.
4. Append an entry to `wiki/log.md`.

### 4.3 Lint — periodic housekeeping

Triggered by `lint` or `wiki 점검해줘`. Detect:

- **Contradictions** — two pages making opposing claims about the same fact.
- **Stale claims** — old claims that a newer source would update.
- **Orphan pages** — pages not linked from anywhere.
- **Missing pages** — concepts mentioned repeatedly without a dedicated page.
- **Missing cross-refs** — two pages clearly related but with no link between them.
- **Data gaps** — holes that a web search could fill.

Record findings in `wiki/log.md` under a `lint` entry. Auto-fix the mechanical issues (e.g., add a backlink for an orphan). Surface judgment calls (contradictions) to the user.

### 4.4 Instill — pushing knowledge into the user (FSRS + SOLO)

**Trigger**: the user says `instill` (mixed deck) or `instill <topic>` (topic-scoped).

**How it differs from query**: in query, the LLM answers. In instill, **the user answers and the LLM grades**.

**Foundations (learning science)**:
- **Testing effect** — retrieval beats re-reading (Roediger & Karpicke 2006).
- **Spacing effect** — spaced practice retains more than massed (Cepeda et al. 2008). Scheduling uses **FSRS-4.5** (the algorithm Anki adopted in 2024).
- **Desirable difficulties** — interleave topics; aim for a small failure rate (Bjork).
- **Mastery learning** — one correct retrieval ≠ mastered. Multiple successes across spaced sessions are required.
- **SOLO taxonomy** — five levels of depth: recall / uni / multi / relational / transfer (Biggs).

**Scheduler**: `tools/instill_sched.py` owns all FSRS math. The LLM only calls the CLI — never compute stability/difficulty in-context.

**Session flow**:

1. **Pull today's queue**: `python tools/instill_sched.py today [--topic X] --limit 8 --new-limit 3`. Receives JSON with `due` and `new_candidates`.
2. **New-card drop step**: if `new_candidates` is non-empty, show the list to the user and ask "any you'd like to skip?". For each dropped card, call `python tools/instill_sched.py skip --id X`.
3. **Begin the session**: up to 8 cards (due + new ≤ 3). Interleave the order.
4. **Per card**:
   - Pick a question type matching the card's current SOLO level (see table below).
   - User answers. Keep the LLM side short — one card = one question's worth of exchange.
   - LLM assigns a grade, then calls `python tools/instill_sched.py review --id X --grade {again,hard,good,easy}`.
5. **After 8 cards**: ask whether to continue. If the user signals "keep going" (any natural phrasing — "더 해줘", "조금 더", "more", etc.), add 4 more cards. Otherwise end.
6. **Session end**: update `instill/<topic>.md` for each touched topic with narrative notes (mastered, in-progress, weaknesses, strengths). Append one line to `wiki/log.md`.

**Grade rubric**:

| Grade | Criterion | Effect |
|---|---|---|
| **Again** | Core missed or wrong. Still wrong after a counter-question/hint. | lapse +1, short re-interval. Candidate for SOLO target one step lower. |
| **Hard** | Partial; got it after one hint. | Same SOLO target, slightly longer interval. |
| **Good** | Correct. | Same target, standard interval. |
| **Easy** | Correct + unprompted connection or application. | Candidate for SOLO target one step higher. Long interval. |

**SOLO ↔ question type**:

| SOLO | Description | Example question |
|---|---|---|
| recall | factual recall | "What is X?" |
| uni | one aspect | "Name one key property of X." |
| multi | multiple aspects | "Describe the two stages of X." |
| relational | relations, distinctions, rationale | "How does X differ from Y? Why is it designed that way?" |
| transfer | application | "How would you use X in a new situation Z?" |

A card's `solo-target` is the *final* depth to reach. Start at recall and climb toward the target as grades trend upward.

**Principles**:
- **Ask first, explain second.** Never lecture before the user attempts.
- **If they don't know, give a hint before giving the answer.** Self-correction yields the strongest retention.
- **Confirmations must be specific**: not "correct" but "*synthesizing at ingest time* — that's the key part you nailed."
- **Keep replies short.** No tables or sectioned essays like in query. One or two sentences plus one question.
- **The wiki is read-only during a session.** Scheduler calls only mutate `instill/_deck.json`; `wiki/` and `raw/` are untouched.
- **Interleaving is the default.** Topic-scoped (`instill <topic>`) is allowed but Bjork supports mixing.

**Backlog overflow**: if due > 8, the scheduler sorts by priority (lapses → most overdue → importance) and returns only the top. Untreated due cards do not disappear — they roll forward.

**Narrative notes — `instill/<topic>.md`** (lazy-load):

Separately from the quantitative state in `_deck.json`, per-topic coaching notes live in `instill/<topic>.md` as markdown: mastered concepts, weakness/strength patterns, session log. Normal sessions do NOT read these files — only instill sessions touching the topic do.

**`wiki/log.md` entry format**:

```
## [YYYY-MM-DD] instill | <mixed | topic>
- cards: 8 (due 6 / new 2). grades: 4G/2H/2A.
- topics touched: cc-memory, cc-skills
- strengths: ...
- weaknesses: ...
- end: completed-deck / extended / user-stopped
```

---

## 5. `index.md` format

```markdown
# Index

## Sources
- [[sources/karpathy-llm-wiki]] — the LLM-wiki maintenance pattern (2026-05-25)

## Concepts
- [[concepts/llm-wiki-pattern]] — accumulating KB unlike RAG
- [[concepts/three-layer-architecture]] — raw / wiki / schema

## Entities
- [[entities/obsidian]] — markdown-based PKM
- [[entities/qmd]] — local markdown search engine
```

Group by category; one line per item. Once the wiki grows, introduce alphabetical / topical / date ordering within categories.

---

## 6. `log.md` format

Append-only. The newest entry is at the **bottom**, not the top (chronological). Each entry starts with `## [YYYY-MM-DD] <op> | <one-liner>` so recent activity can be pulled with `grep "^## \[" log.md | tail -10`.

```markdown
## [2026-05-25] ingest | Karpathy — LLM Wiki
- raw: raw/karpathy-llm-wiki.md
- new: [[sources/karpathy-llm-wiki]], [[concepts/llm-wiki-pattern]], [[concepts/three-layer-architecture]], [[entities/obsidian]]
- new cards: 7
- updated: [[index]]

## [2026-05-26] query | RAG vs wiki, key difference?
- referenced: [[concepts/llm-wiki-pattern]], [[sources/karpathy-llm-wiki]]
- result: new [[concepts/rag-vs-wiki]]

## [2026-05-30] lint
- orphans 2: [[entities/marp]], [[entities/dataview]] → added to index
- contradictions 0

## [2026-06-01] instill | mixed
- cards: 8 (due 6 / new 2). grades: 5G/2H/1A.
- topics touched: rag-vs-wiki, llm-wiki-pattern
- strengths: distinguishes synthesis timing
- weaknesses: contradiction detection mechanism
- end: completed-deck
```

---

## 7. Operating principles

1. **`raw/` is immutable.** Never edit or delete. If a clipping is wrong, add a new file and move the old one to `raw/_deprecated/`.
2. **Every wiki claim needs a source.** Mark unsourced claims `> ❓ source unverified`.
3. **Update `index.md` and `log.md` on every wiki mutation.** Skipping these decays the wiki quickly.
4. **Link aggressively.** If two pages seem related, link both ways. Backlinks are the wiki's value.
5. **Short summaries, thorough bodies.** A one-line summary in `index.md` must register meaning within one second of scanning.
6. **No fabrication.** Do not add anything absent from raw sources. If external knowledge is required, flag `web search needed` and ask the user.

---

## 8. Common user commands

Natural language — no slash commands.

- `raw/X.md ingest 해줘` — run ingest (auto card extraction included)
- `Q 답해줘` / `Q에 대해 wiki에 뭐가 있어?` — run query
- `instill` — start instill session with the mixed deck (default, interleaved)
- `instill <주제>` — topic-scoped instill session
- Continue / stop signals during a session are recognized from natural phrasing — no fixed keyword. "더 해줘", "more", "충분해", "그만", "stop" all work. Interpret intent, not literal tokens.
- `lint` / `wiki 점검해줘` — run lint
- `index 보여줘` — print `wiki/index.md`
- `최근 활동` — print the last N entries of `wiki/log.md`

---

## 9. Future extensions (not yet adopted)

- **Search engine**: if pages exceed ~100, consider a local markdown search tool such as [[entities/qmd]].
- **Dataview-style queries**: dynamic tables/lists from frontmatter.
- **Automatic backlinks**: render inbound link lists at the bottom of every page.
- **Git integration**: auto-commit on each ingest / lint.

Add a section here when one is adopted.
