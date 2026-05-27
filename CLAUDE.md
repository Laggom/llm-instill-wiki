# CLAUDE.md — LLM Wiki Operating Schema

This file is the **schema** for this wiki. It defines the structure, format, and workflows the LLM must follow when maintaining and extending the wiki. Based on Karpathy's [LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

> Principle: the human curates, asks, and sets direction. The LLM writes and maintains the entire wiki.

---

## 0. Language

- This schema is written in English for token efficiency and broad agent compatibility across tools.
- **Respond to the user in Korean (존댓말 — polite form)** unless explicitly told otherwise.
- Wiki page titles, claims, and content may be in any language — match the source. The schema (this file, page frontmatter keys, scheduler IDs) stays in English.
- User commands listed in §9 are in Korean by convention but the LLM should also recognize obvious English equivalents (`ingest X`, `query Q`, `lint`, etc.).

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
│   └── instill_sched.py   # FSRS-5 scheduler (stdlib only)
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

Runtime artifacts not part of the schema layout: `.venv/` and `.python-policy` may appear at the repo root once §8 is exercised (both gitignored).

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

**The user gives you a path, not a finished raw file.** The user may point you at any source — a file in Downloads, a path inside `raw/`, even a URL — and say "ingest this". Your job is to normalize it into `raw/<slug>.md` and then run the ingest steps below.

**`raw/` stores markdown only.** The repo intentionally has no Python conversion dependency, so the normalization step depends on the host tool's native capabilities:

- **Source is already markdown** → move/copy it into `raw/<slug>.md` (or leave it in place if already there).
- **Source is a format your host tool can read natively** (Claude Code and recent Cursor read PDFs natively; many tools read HTML/text) → read it, write a clean markdown version to `raw/<slug>.md`, then proceed.
- **Source is a format your host tool cannot read** → a Python converter package (e.g., `markitdown`, `pypdf`, `pandoc` bindings) may be installed. Before the first such install, follow the Python environment policy in §8 — that section governs the venv-vs-system prompt and prevents repeating the question every session. After install, convert to markdown, write to `raw/<slug>.md`, then proceed.

Choose `<slug>` as a short kebab-case identifier matching what the source page in `wiki/sources/` will use. If the user proposes a slug, honor it.

**Ingest steps** (run once `raw/<slug>.md` exists):

1. Open the raw file **read-only** and extract the key content.
2. Create `wiki/sources/<slug>.md` with summary, key claims, and quotable lines.
3. For each concept, person, or tool mentioned, create or update a page under `wiki/concepts/` or `wiki/entities/`.
4. If new information contradicts something on another page, leave a note on both sides (`> ⚠ YYYY-MM-DD: conflicts with source X, needs reconciliation`).
5. Add new pages to `wiki/index.md`.
6. **Instill card extraction** — for each new or updated page, populate the `instill:` array in its frontmatter with atomic claims (cards). Each card needs `id` (wiki-globally unique, e.g., `cc-mem-001`), `claim` (one line, testable), `importance` (high/med/low), and `solo-target` (recall/uni/multi/relational/transfer). For each new card, call `python tools/instill_sched.py enroll --id <id> --importance <h/m/l> --topic <topic>` to register it in the scheduler.
7. Append an entry to `wiki/log.md` (include new card count).

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
- **Orphan instill cards** — card IDs in `instill/_deck.json` whose corresponding `claim` no longer exists in any wiki page's frontmatter (e.g., the page was deleted or the `instill:` entry was removed). Report each and ask the user whether to `skip` them via the scheduler.

Record findings in `wiki/log.md` under a `lint` entry. Auto-fix the mechanical issues (e.g., add a backlink for an orphan). Surface judgment calls (contradictions) to the user.

### 4.4 Instill — pushing knowledge into the user (FSRS + SOLO)

**Trigger**: the user says `instill` (mixed deck) or `instill <topic>` (topic-scoped).

**How it differs from query**: in query, the LLM answers. In instill, **the user answers and the LLM grades**.

**Foundations (learning science)**:
- **Testing effect** — retrieval beats re-reading (Roediger & Karpicke 2006).
- **Spacing effect** — spaced practice retains more than massed (Cepeda et al. 2008). Scheduling uses **FSRS-5** (the algorithm family Anki adopted in 2024+).
- **Desirable difficulties** — interleave topics; aim for a small failure rate (Bjork).
- **Mastery learning** — one correct retrieval ≠ mastered. Multiple successes across spaced sessions are required.
- **SOLO taxonomy** — five levels of depth: recall / uni / multi / relational / transfer (Biggs).

**Scheduler**: `tools/instill_sched.py` owns all FSRS math. The LLM only calls the CLI — never compute stability/difficulty in-context.

**Session flow**:

1. **Pull today's queue**: `python tools/instill_sched.py today [--topic X] --limit 8 --new-limit 3`. Receives JSON with `due` and `new_candidates`.
2. **New-card drop step**: if `new_candidates` is non-empty, show the list to the user and ask "any you'd like to skip?". For each dropped card, call `python tools/instill_sched.py skip --id X`.
3. **Begin the session**: up to 8 cards (due + new ≤ 3). Interleave the order.
4. **Per card** (the scheduler returns `id` only — text lives in the wiki):
   - **Look up the card's `claim`** by `id` in the corresponding wiki page's frontmatter `instill:` array. Read the `solo-target` too.
   - Pick a question type appropriate for this card (see SOLO table below).
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

**Question quality** (critical — bad questions kill the session):

A good instill question is **context-rich, single-answer, and concept-probing**. The card's `claim` is the *target understanding* — the question must elicit that specific understanding, not let the user guess at what you're asking.

Required:
- **Set context in 1–2 sentences** before the question proper. A concrete scenario, an analogy, or a specific comparison. Bare interrogatives like "X 가 뭐예요?" or "왜 필요해요?" are too thin — the user has no anchor for what's being probed.
- **Converge on a single defensible answer.** If two well-informed readers could answer differently and both be valid, the question is too open. Rephrase until there is one obvious right answer (the card's claim, or a tight equivalent).
- **Probe the concept, not a buzzword.** Don't ask the user to retrieve a specific term like "active recall" by name — ask them to reason about the underlying mechanism and let the term emerge.

Forbidden:
- Vague open-enders: "왜 X 가 필요한가요?", "X 는 어떤 거예요?", "X 의 핵심이 뭐죠?"
- Questions whose answer-space is unbounded ("어떻게 생각하세요?", "한 줄로 정리하면?")
- Pure name-recall ("이걸 뭐라고 부르죠?") unless the term itself is the card's claim.

Example transformation:
- ✗ Too thin: "instill 이 query 와 별도로 왜 필요한가요?"
- ✓ Rich + converging: "교과서를 5번 정독한 학생 A 와, 1번 읽고 4번은 책 덮고 머릿속에서 꺼내려 노력한 학생 B 가 있어요. 일주일 뒤 누가 더 잘 기억할까요? 그리고 이 결과가 instill 이 query 와 별도 동작인 이유와 어떻게 연결되나요?"

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

Append-only. The newest entry is at the **bottom**, not the top (chronological). Each entry starts with `## [YYYY-MM-DD] <op> | <one-liner>` so recent activity can be pulled with `grep "^## \[" log.md | tail -10` (Unix) or `Select-String "^## \[" log.md | Select-Object -Last 10` (PowerShell).

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

## 8. Python environment

When a workflow legitimately needs a Python package beyond the stdlib (e.g., a PDF/HTML converter during ingest §4.1), the LLM may install it — but never silently.

**First-time prompt**: before the first `pip install` in this repo, ask the user **exactly once**:

> "Need to install `<package>`. Create a `.venv` to isolate it, or install into the system / current Python? (recommendation: venv)"

Honor the choice and **record it** in `.python-policy` at the repo root (one of `venv` or `system`, single line). This file is gitignored. Future install needs read this file and proceed without re-asking.

**If `venv`** is chosen:
1. Run `python -m venv .venv` (if `.venv/` does not already exist).
2. Use the venv's interpreter for all subsequent Python invocations in this repo — including `tools/instill_sched.py`. On Unix: `.venv/bin/python`. On Windows: `.venv/Scripts/python.exe`.
3. Install with `.venv/bin/pip install <package>` (or Windows equivalent).

**If `system`** is chosen:
1. Use whatever Python the user already has on PATH.
2. Install with `pip install --user <package>` when possible to avoid touching system site-packages without permission.

**Rules**:
- Never install a package the workflow does not actually need.
- Surface the install command to the user before running it ("about to run: `pip install markitdown` — OK?") unless the user has explicitly granted blanket permission for that session.
- If `.python-policy` is missing but `.venv/` exists, treat it as `venv` (the venv wins as evidence of past intent).

`.gitignore` already covers `.venv/` and `.python-policy`.

---

## 9. Common user commands

Natural language — no slash commands.

- `raw/X.md ingest 해줘` — run ingest (auto card extraction included)
- `Q 답해줘` / `Q에 대해 wiki에 뭐가 있어?` — run query
- `instill` — start instill session with the mixed deck (default, interleaved)
- `instill <주제>` — topic-scoped instill session
- Continue / stop signals during a session are recognized from natural phrasing — no fixed keyword. "더 해줘", "more", "충분해", "그만", "stop" all work. Interpret intent, not literal tokens.
- `lint` / `wiki 점검해줘` — run lint
- `index 보여줘` — print `wiki/index.md`
- `최근 활동` — print the last N entries of `wiki/log.md`
- `상태` / `progress` / `stats` — run `python tools/instill_sched.py stats` and report deck size, by-state breakdown, due-today count, average stability

---

## 10. Future extensions (not yet adopted)

- **Search engine**: if pages exceed ~100, consider a local markdown search tool such as [[entities/qmd]].
- **Dataview-style queries**: dynamic tables/lists from frontmatter.
- **Automatic backlinks**: render inbound link lists at the bottom of every page.
- **Git integration**: auto-commit on each ingest / lint.

Add a section here when one is adopted.
