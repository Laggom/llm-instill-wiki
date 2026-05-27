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
│   ├── entities/      # people, tools, orgs, products
│   └── _instill/      # append-only session logs (one file per instill session)
└── instill/           # learning state
    ├── _deck.json     # FSRS topic state (machine-owned, keyed by topic tag)
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
---
```

- `type` must match the directory the page sits in.
- For `entities/` pages, add `kind: person | tool | org | product`.
- Bump `updated` and `sources` whenever a new raw source extends the page.
- **No `instill:` block in frontmatter.** Topics (the units of FSRS scheduling, see §4.4) are not pre-extracted at ingest — they emerge during instill sessions from the wiki page itself, are tracked in `instill/_deck.json`, and use kebab-case tags. The wiki page is the *carrier* of questions, not a script of frozen claims.

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
6. Append an entry to `wiki/log.md`.

Touching 10–15 pages during one ingest is normal. **Ingest no longer extracts instill cards** — topics enter the FSRS scheduler only when they surface in actual instill sessions (or via `lint` topic-enroll, §4.3). This keeps the wiki the source of truth for questions and avoids calcifying single-source atomizations before cross-page context develops.

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
- **Topic-tag hygiene** — for the FSRS scheduler (§4.4):
  - **Enroll candidates** — topics that have appeared in recent `wiki/_instill/*.md` session logs but are not in `instill/_deck.json`. Propose to the user grouped by wiki page; on OK call `python tools/instill_sched.py enroll --topic <tag> --importance <h/m/l> --anchor <page-path>`.
  - **Stale topics** — enrolled topics whose wiki anchor page no longer exists (deleted/renamed). Propose `skip` and on OK call `python tools/instill_sched.py skip --topic <tag>`.
  - **Tag duplicates** — two topic tags that clearly mean the same thing (e.g., `kohn-sham-veff` and `kohn-sham-v-eff`). Surface to user; manual reconciliation (silent rename forbidden — kills cumulative history).

Record findings in `wiki/log.md` under a `lint` entry. Auto-fix mechanical issues (e.g., add a backlink for an orphan). Surface judgment calls (contradictions, topic enroll/skip, tag duplicates) to the user.

### 4.4 Instill — pushing knowledge into the user (topic-level FSRS + dynamic questions)

**Trigger**:
- `instill` — mixed deck, interleaved across topics (default).
- `instill <topic-or-page>` — scoped to one topic tag or wiki page.
- `instill --review` / "약점 정리해줘" — weak-topic refresher only, no new topics introduced.

**How it differs from query**: in query, the LLM answers from the wiki. In instill, **the user answers and the LLM grades** — and the LLM's *question* is composed freshly from the wiki page each time, not from a frozen claim text.

**Foundations (learning science)**:
- **Testing effect** — retrieval beats re-reading (Roediger & Karpicke 2006).
- **Spacing effect** — spaced practice retains more (Cepeda et al. 2008). Scheduling uses **FSRS-5** (the Anki algorithm family).
- **Encoding variability** — *varying* the retrieval cue across episodes strengthens memory more than repeating the identical cue (Bjork 1972; Smith & Handy 2014). **This is why the scheduling unit is the *topic*, not a fixed card text** — the same concept is probed from a different angle each session.
- **Desirable difficulties** — interleave topics; aim for a small failure rate; allow generation effort before showing the answer (Bjork).
- **Mastery learning** — one ✓ ≠ mastered. Multiple ✓ across spaced sessions are required.

**Unit of scheduling**: the **topic tag** (kebab-case, e.g., `picd`, `in-situ-acetylation`, `cc-skills-lazy-load`). A topic is a durable concept whose questions can vary forever. Cards/claims are *not* the unit — the wiki page is.

**Scheduler**: `tools/instill_sched.py` owns all FSRS math, keyed by topic. State lives in `instill/_deck.json`. The LLM only calls the CLI — never computes FSRS in-context.

**Session flow**:

1. **Pre-check (dynamic scan)**: scan recent `wiki/_instill/*.md` logs in scope. If the last session left weak topics (verdict ✗ or unresolved ~), offer **once**: "지난 세션에서 약점이었던 토픽 먼저 짚고 갈까요?" Decline → proceed without re-asking.
2. **Pull today's queue**: `python tools/instill_sched.py today [--topic X] --limit 8 --new-limit 3`. Returns JSON with `due` (topics due today, FSRS-prioritized) and `new_candidates` (topics enrolled but never reviewed).
3. **New-topic preview**: if `new_candidates` non-empty, list them by topic name + wiki anchor; ask "skip any?". Skipped topics → `python tools/instill_sched.py skip --topic X`.
4. **Depth mix** (default): **recall 1-2 + reasoning 2-3 + synthesis 1 = 5 questions**. User can override at session start ("recall만", "synthesis 위주", "재출제 우선"). For `instill --review`, all from weak-topic backlog.
5. **Per question**:
   - Topic chosen from the queue (interleaved).
   - **Compose the question fresh from the full wiki page (+ cross-linked pages).** Apply Question Quality rules below. The wiki is the *carrier*; the topic tag is just the address.
   - User answers.
   - Assign **verdict ∈ {✓ correct, ~ partial, ✗ wrong}** and state it explicitly.
   - On ~ or ✗ → **Socratic, up to 1-2 sub-questions** to let the user self-correct. After that, give the wiki-cited explanation. Do not drag Socratic past 2 turns (Bjork: generation effort yes; frustration no).
   - Map verdict → FSRS grade and call `python tools/instill_sched.py review --topic X --grade {again,hard,good,easy}` (mapping below).
6. **After 5 questions**: offer to continue (any phrasing — "더 해줘", "more"). If yes, add 3-5 more (still interleaved).
7. **Reverse mode** (offer 1-2× per session or on user request): user explains a concept in their own words → LLM compares to wiki, scores with the same verdict scheme. This catches mental-model gaps that Q&A doesn't surface.
8. **Session end**:
   - Save `wiki/_instill/<YYYY-MM-DD>-<scope-slug>.md` (format below). Same-day same-scope gets `-2`, `-3` suffix.
   - For each touched topic, update `instill/<topic>.md` narrative coaching notes.
   - If any topic accumulated **≥ 2 cumulative ✗** across history (scan logs), propose adding a `## Common confusion: <topic>` section to its wiki page.
   - Append a one-line summary to `wiki/log.md`.

**Verdict → FSRS grade mapping**:

| Verdict | Criterion | FSRS grade |
|---|---|---|
| ✗ wrong | Core missed; still wrong after Socratic. | **again** (lapse +1, short re-interval) |
| ~ partial | Got it after 1 sub-question, or partial credit. | **hard** (small interval bump) |
| ✓ correct | Clean answer. | **good** (standard interval) |
| ✓ + unprompted connection | Correct *and* spontaneously linked to another concept / proposed an application. | **easy** (long interval) |

**Question types** (depth mix):

| Type | Description | Example |
|---|---|---|
| recall | factual recall | "PICD 의 PI 와 CD 는 각각 무엇의 약자입니까?" |
| reasoning | apply wiki facts to a scenario | "PET 가공 중 비산 모노머가 검출됩니다. [[ionic-liquid-polyester-additive]] 첨가가 왜 효과적일지 메커니즘으로 설명해 보세요." |
| synthesis | combine multiple pages | "PICD 와 PIT 의 내후성 차이를 CHDA vs TPA 의 구조적 출처로 설명해 보세요." |

**Question quality** (the carrier matters — this is what makes questions rich, not thin):

A good instill question is **context-rich, single-answer, and concept-probing**.

Required:
- **Carrier = wiki page(s), not a frozen claim.** Open the relevant wiki page + cross-links *before* composing. The question's information density mirrors the carrier's — short claim → thin question; full page → rich question.
- **Set context in 1-2 sentences** before the question proper. A concrete scenario, an analogy, or a specific comparison anchors the user.
- **Converge on a single defensible answer.** If two well-informed readers could answer differently and both be right, the question is too open. Rephrase until there's one obvious right answer.
- **Probe the concept, not a buzzword.** Don't ask the user to retrieve a term by name — ask them to reason about the mechanism and let the term emerge.

Forbidden:
- Bare interrogatives: "X 가 뭐예요?", "왜 필요해요?", "X 의 핵심이 뭐죠?"
- Unbounded answer-space: "어떻게 생각하세요?", "한 줄로 정리하면?"
- Pure name-recall unless the term itself is the target.

Example transformation:
- ✗ Too thin: "PICD 직접 중합이 왜 안 되나요?"
- ✓ Rich + converging: "ISB 와 CHDA 를 그냥 용융 중합하면 Garaleh 그룹은 Mn 11,000 에서 멈췄어요. 무엇이 그 한계의 출처이고, [[in-situ-acetylation]] 가 어떤 메커니즘으로 그 한계를 푸는지 한 문장으로 답해 보세요."

**Principles**:
- **Ask first, explain second.** Never lecture before the user attempts.
- **Hint before answer.** Socratic 1-2회 후에만 정공법으로.
- **Confirmations must be specific**: not "맞아요" but "*Ac₂O 가 OH 를 활성화해 leaving group 을 만든다* — 그 메커니즘이 핵심이었습니다."
- **Sycophancy 금지.** 모호한 답을 "거의 맞아요"로 ~를 ✓로 밀어 올리지 않는다. 약점 추적이 거짓이 되면 instill 전체 가치가 무너진다. 어조는 존댓말 유지 (단호함과 무례함은 별개).
- **Correction은 wiki 인용 동반.** Chat 안에서만 떠도는 정정은 휘발한다. 정정 시 반드시 `[[concepts/foo]]` 링크 + 메커니즘 설명.
- **User reply 부담 최소화.** 사용자는 *방향·선택·짧은 답*만. 메커니즘·"왜"·연결은 LLM이 follow-up 에 공급.
- **Wiki는 세션 중 read-only.** 스케줄러 호출만 `instill/_deck.json` 갱신. 페이지 편집은 세션 종료 후 Common confusion 추가 시에만.
- **Topic tag discipline.** kebab-case. 새 topic 만들기 전 기존 topic 재사용 우선 (`instill/_deck.json` 의 키 확인). Silent rename 금지 — 누적 추적 망가짐. 모호하면 사용자에게 분류 묻기.
- **Interleaving 기본.** Topic-scope (`instill <topic>`) 가능하지만 mixed 가 default.
- **Lifecycle 침범 금지.** Instill 외부 세션(ingest, query)에서 "이거 약하니 공부하세요" 같은 제안 금지. 학습 lifecycle 은 사용자 영역.

**Session log — `wiki/_instill/<YYYY-MM-DD>-<scope-slug>.md`**:

```yaml
---
type: instill
created: YYYY-MM-DD
scope: concepts/picd.md       # 또는 topic 문자열, 또는 "mixed"
depth_mix: {recall: 2, reasoning: 2, synthesis: 1}
topics_touched: [picd, in-situ-acetylation, isosorbide]
prior_session: 2026-05-26-picd.md   # 연속 세션이면 (선택)
---

## Summary
- ✓ 3 / ~ 1 / ✗ 1
- 약점: in-situ-acetylation (Socratic 후에도 ✗ → 다음 세션 first-up; 누적 ✗ 3회 → Common confusion 후보)
- 호조: picd-monomer-pair (지난 세션 ✗ → 이번 ✓)

## Q&A

### Q1 [reasoning | topic: in-situ-acetylation]
**Q**: ...
**A (user)**: ...
**Verdict**: ✗
**Socratic**:
- sub-Q: ... → sub-A: ... → ~
**Correction**: [[concepts/in-situ-acetylation]] 인용 + 메커니즘 설명.
**Re-test scheduled**: ✓

### Q2 [recall | topic: picd-monomer-pair]
...
```

Verdict 한 글자(✓/~/✗) → grep 으로 약점 집계. Topic tag → 시간순 추적. Wiki 인용은 markdown link 로 (one-click 후속 학습).

**Narrative notes — `instill/<topic>.md`** (lazy-load):

Per-topic 장기 코칭 노트: mastered concepts, weakness/strength patterns, multi-session 누적 메모. 정상 세션은 읽지 않음 — 해당 topic 을 다루는 instill 세션만 읽고 갱신.

**Common confusion (wiki 역방향 갱신)**:

같은 topic 이 누적 ✗ ≥ 2회 → 해당 wiki 페이지에 `## Common confusion: <topic>` 섹션 추가 제안. 사용자가 헷갈렸던 지점·올바른 mental model 을 한국어로 정리. 승인 시 페이지 편집 + 일반 wiki 갱신처럼 log.md 에 기록.

**Backlog overflow**: due > 8 이면 스케줄러가 우선순위(lapses → most overdue → importance)로 상위 N 만 반환. 미처 다루지 못한 due 는 다음 날로 자동 roll forward (FSRS 가 알아서 처리).

**`wiki/log.md` entry format**:

```
## [YYYY-MM-DD] instill | <mixed | scope>
- questions: 5 (recall 2 / reasoning 2 / synthesis 1). verdict: 3✓ / 1~ / 1✗
- topics touched: picd, in-situ-acetylation, isosorbide
- weak: in-situ-acetylation (누적 ✗ 3회 — Common confusion 제안)
- log: [[../_instill/2026-05-27-picd.md]]
- end: completed / extended / user-stopped
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
- updated: [[index]]

## [2026-05-26] query | RAG vs wiki, key difference?
- referenced: [[concepts/llm-wiki-pattern]], [[sources/karpathy-llm-wiki]]
- result: new [[concepts/rag-vs-wiki]]

## [2026-05-30] lint
- orphans 2: [[entities/marp]], [[entities/dataview]] → added to index
- contradictions 0
- topic-hygiene: enroll candidates 3 (picd, in-situ-acetylation, isosorbide), stale 0

## [2026-06-01] instill | mixed
- questions: 5 (recall 2 / reasoning 2 / synthesis 1). verdict: 3✓ / 1~ / 1✗
- topics touched: rag-vs-wiki, llm-wiki-pattern
- weak: contradiction-detection (누적 ✗ 2회 — Common confusion 제안)
- log: [[../_instill/2026-06-01-mixed.md]]
- end: completed
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

- `raw/X.md ingest 해줘` — run ingest (no card extraction; topics emerge during instill sessions)
- `Q 답해줘` / `Q에 대해 wiki에 뭐가 있어?` — run query
- `instill` — start instill session with the mixed deck (default, interleaved)
- `instill <주제-or-page>` — scoped instill session (topic tag or wiki page path)
- `instill --review` / "약점 정리해줘" — weak-topic refresher only
- Continue / stop signals during a session are recognized from natural phrasing — no fixed keyword. "더 해줘", "more", "충분해", "그만", "stop" all work. Interpret intent, not literal tokens.
- `lint` / `wiki 점검해줘` — run lint
- `index 보여줘` — print `wiki/index.md`
- `최근 활동` — print the last N entries of `wiki/log.md`
- `상태` / `progress` / `stats` — run `python tools/instill_sched.py stats` and report deck size (topics), by-state breakdown, due-today count, average stability

---

## 10. Future extensions (not yet adopted)

- **Search engine**: if pages exceed ~100, consider a local markdown search tool such as [[entities/qmd]].
- **Dataview-style queries**: dynamic tables/lists from frontmatter.
- **Automatic backlinks**: render inbound link lists at the bottom of every page.
- **Git integration**: auto-commit on each ingest / lint.

Add a section here when one is adopted.
