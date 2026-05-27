# llm-instill-wiki

LLM 이 직접 유지·확장하는 개인 위키 + 그 위에 얹은 **능동적 학습 루프** 입니다. Claude Code 와 함께 쓰는 운영 schema 한 벌이에요.

## 왜 만들었는지

LLM 으로 메모를 쌓아본 분들이라면 한 번쯤 느끼는 답답함이 있습니다. 같은 문서를 매번 다시 읽히고, 같은 질문을 매번 다시 던지고, 어느샌가 LLM 의 검색 능력에만 의존하게 됩니다. 정작 *제 머릿속에는 아무것도 안 남습니다*.

Andrej Karpathy 가 제안한 [LLM Wiki 패턴](https://gist.github.com/karpathy) 은 이 문제의 절반을 풉니다 — LLM 이 원본 소스를 *한 번* 읽고, 결과를 위키로 누적하면 시간이 지날수록 위키 자체가 1차 소스가 됩니다. RAG 와 달리 매번 처음부터 다시 합성하지 않아도 됩니다.

그런데 여전히 절반이 남습니다. 위키가 아무리 잘 정리돼도 그건 **밖에 있는 지식** 입니다. 진짜로 제 것이 되려면 머릿속으로 옮겨야 합니다. 그 과정을 LLM 이 도와줄 수 있다는 게 이 프로젝트의 출발점이에요.

## 세 가지 모드

| 모드 | 누가 답하나요 | 무엇을 하나요 |
|---|---|---|
| ingest | LLM | 원본 소스를 읽고 위키 페이지로 정리합니다 |
| query | LLM | 위키를 뒤져서 질문에 답합니다 |
| **instill** | **사용자** | LLM 이 묻고, **사용자가 답합니다**. 머릿속에 옮기는 과정입니다 |

ingest 와 query 는 흔합니다. instill 이 다른 점이에요.

## instill 이 어떻게 다른가요

학습과학에서 검증된 몇 가지를 그대로 적용했습니다.

- **Testing effect** (Roediger & Karpicke) — 다시 읽기보다 *꺼내 쓰기* 가 장기기억에 훨씬 잘 남습니다. 그래서 instill 은 무조건 사용자가 먼저 답합니다. LLM 은 평가만 합니다.
- **Spacing effect** (Cepeda et al.) — 같은 시간 공부해도 간격을 두면 정착률이 올라갑니다. 카드별로 다음 복습 시점을 계산해서 *오늘 할 것* 만 뽑아냅니다.
- **Desirable difficulties** (Bjork) — 너무 쉬우면 학습이 안 됩니다. 약간 실패할 정도가 적정. 토픽을 섞어 인터리빙으로 진행합니다.
- **SOLO taxonomy** (Biggs) — 이해의 깊이를 5단계로 나눠 (단순 회상 → 응용·전이), 카드가 익숙해질수록 더 깊은 질문을 던집니다.

스케줄링 알고리즘은 **FSRS-4.5** 를 씁니다. Anki 가 2024 부터 기본으로 채택한 최신 알고리즘이에요. 직접 LLM 이 계산하면 오차가 생길 수 있어서 `tools/instill_sched.py` 라는 작은 스크립트로 분리했습니다. Python 표준 라이브러리만 쓰니까 추가 설치는 필요 없습니다.

## 한 세션은 어떻게 흘러가나요

`instill` 한 마디면 시작됩니다.

1. 스케줄러가 오늘 복습할 카드 + 신규 후보를 뽑아 줍니다.
2. 신규 후보 중 빼고 싶은 게 있으면 사용자가 drop 합니다.
3. 최대 8장 (≈5분) 진행합니다. 카드마다 LLM 이 한 줄짜리 질문을 던지고, 사용자가 답하고, LLM 이 Again/Hard/Good/Easy 로 평가합니다.
4. 평가 결과에 따라 다음 복습 시점이 자동으로 계산됩니다.
5. 끝나고 더 하고 싶으면 `more`, 그만하려면 `stop`.

5분이 한도라고 정한 건, 그 이상은 어차피 잘 안 한다는 게 정직한 가정이라서요.

## 디렉터리 구조

```
.
├── CLAUDE.md       ← 운영 규칙. Claude Code 가 이 파일을 시스템 프롬프트처럼 읽습니다.
├── README.md       ← 지금 읽고 계신 이 문서.
├── tools/
│   └── instill_sched.py    ← FSRS 스케줄러 (stdlib only)
├── docs/specs/             ← 설계 결정 기록
├── raw/            ← 본인의 원본 소스 (이 repo 에는 포함 안 됨)
├── wiki/           ← LLM 이 정리한 페이지 (이 repo 에는 포함 안 됨)
└── instill/        ← 카드 스케줄 + 토픽별 학습 노트 (이 repo 에는 포함 안 됨)
```

`raw/`, `wiki/`, `instill/` 은 본인의 개인 콘텐츠라 `.gitignore` 로 빠져 있습니다. clone 하시면 이 디렉터리들은 비어 있을 거예요. 본인의 글·메모를 넣고 채우시면 됩니다.

## 필요한 것

기본적으로 **[Claude Code](https://docs.anthropic.com/en/docs/claude-code)** 에서 동작하도록 만들어졌습니다. Claude Code 는 프로젝트 루트의 `CLAUDE.md` 를 매 세션 시작 시 자동으로 컨텍스트에 주입해주는데, 이 schema 가 그 동작에 기대고 있어요.

다른 코딩 CLI 에서도 쓰실 수 있습니다. 다만 약간의 손이 필요해요.

- **Cursor / Codex / 기타 AGENTS.md 호환 도구** — `CLAUDE.md` 를 `AGENTS.md` 로 복사하거나 심볼릭 링크 거시면 됩니다. 두 파일의 역할이 사실상 같습니다.
  ```bash
  # macOS / Linux
  ln -s CLAUDE.md AGENTS.md
  # Windows (PowerShell, 관리자 권한)
  New-Item -ItemType SymbolicLink -Path AGENTS.md -Target CLAUDE.md
  ```
- **Gemini CLI** — `CLAUDE.md` 를 `GEMINI.md` 로 같은 방식으로 처리.
- **기타 환경** — 자동 컨텍스트 로드가 없는 도구라면 매 세션 시작 시 `CLAUDE.md` 내용을 시스템 프롬프트로 직접 붙여 넣으셔야 합니다. 번거롭지만 동작은 합니다.

`tools/instill_sched.py` 는 **Python 3.10+** 필요합니다. 표준 라이브러리만 쓰니까 별도 패키지 설치는 없어요.

## 시작하는 법

```bash
git clone https://github.com/Laggom/llm-instill-wiki my-wiki
cd my-wiki
mkdir raw wiki instill
```

그리고 이 디렉터리에서 Claude Code 를 실행하시면 됩니다. `CLAUDE.md` 가 자동으로 컨텍스트에 들어가서 운영 규칙이 즉시 적용돼요.

처음에 해볼 만한 흐름은 이렇습니다.

1. 마음에 드는 글·논문·블로그 포스트를 `raw/<이름>.md` 로 떨어뜨려요.
2. Claude Code 에 "`raw/<이름>.md` ingest 해줘" 라고 합니다.
3. LLM 이 위키 페이지를 만들고, 카드를 추출하고, 스케줄러에 등록까지 다 해줍니다.
4. 며칠 후, 학습하고 싶을 때 "instill" 한 마디.

## 함께 쓰면 좋은 도구

- **Obsidian** — `wiki/` 디렉터리를 그대로 vault 로 열면 그래프 뷰, 백링크, 검색을 무료로 얻으실 수 있습니다. 마크다운이라 가능한 일이에요.
- **git** — 본인 위키 자체는 private repo 로 따로 관리하시면 좋습니다. 이 repo 는 schema 만 담는 template 이고요.

## 더 알아보기

- 운영 규칙 전체: [CLAUDE.md](CLAUDE.md)
- instill 의 설계 결정 배경: [docs/specs/2026-05-27-instill-v2-design.md](docs/specs/2026-05-27-instill-v2-design.md)
- 원본 영감: [Karpathy 의 LLM Wiki gist](https://gist.github.com/karpathy)

질문·제안 있으시면 issue 로 남겨주세요.

---

<details>
<summary><b>For LLM agents</b> (click to expand)</summary>

This section is written for coding agents that land in this repo. It mirrors what a human reader gets above, condensed for machine consumption.

## What this repo is

A Claude Code operational schema implementing an LLM-maintained personal wiki layered with an active-recall learning loop. The schema itself is the deliverable; user content (`raw/`, `wiki/`, `instill/`, `chats/`) is gitignored.

## Source of truth

- **`CLAUDE.md`** — the operative schema. Read it first. Defines four workflows: ingest, query, instill, lint. Sections §1–§9 specify directory layout, page format, naming, workflows, principles, and user commands.
- **`docs/specs/2026-05-27-instill-v2-design.md`** — design rationale for the instill v2 loop (FSRS scheduling, SOLO depth ladder, card decomposition, 5-min session budget). Read when modifying instill logic.

If `CLAUDE.md` and this README disagree, `CLAUDE.md` wins.

## Three modes

| Mode | Who answers | Output |
|---|---|---|
| ingest | LLM | raw source → wiki pages + extracted cards enrolled in scheduler |
| query | LLM | synthesized answer from wiki, optionally promoted back to a new wiki page |
| instill | **user** | retrieval practice with FSRS-scheduled cards; LLM grades, never lectures first |

## Layout

```
CLAUDE.md                       schema (operative rules)
README.md                       human + this agent guide
tools/instill_sched.py          FSRS-4.5 scheduler (stdlib only, CLI)
docs/specs/                     design docs
raw/        (gitignored)        immutable source clippings
wiki/       (gitignored)        LLM-maintained pages: sources/, concepts/, entities/, index.md, log.md
instill/    (gitignored)        _deck.json (FSRS state) + per-topic narrative notes
```

## Scheduler CLI

```
python tools/instill_sched.py today [--topic T] [--limit 8] [--new-limit 3]
python tools/instill_sched.py review --id ID --grade {again,hard,good,easy}
python tools/instill_sched.py enroll --id ID [--importance high|med|low] [--topic T]
python tools/instill_sched.py skip --id ID
python tools/instill_sched.py stats
```

Never compute FSRS state in-context. Always shell out to this script. Deck state is at `instill/_deck.json`.

## Card model

Cards live in the wiki page frontmatter:

```yaml
instill:
  - id: cc-mem-001              # globally unique
    claim: "single-line testable assertion"
    importance: high|med|low
    solo-target: recall|uni|multi|relational|transfer
    skip: false
```

IDs must be wiki-globally unique. The scheduler keys off `id` only — it does not parse wiki frontmatter; ingest must call `enroll` explicitly.

## Workflow contract

- **ingest** must (1) read raw, (2) produce/update wiki pages, (3) extract `instill:` cards into frontmatter, (4) call `enroll` per new card, (5) update `wiki/index.md` and `wiki/log.md`. No user approval gate at ingest.
- **query** reads `wiki/index.md` first. Cites every claim with `[[wiki-path]]`. Promote reusable synthesis back to a new concept page.
- **instill** is read-only on `wiki/` and `raw/`. The scheduler may write `instill/_deck.json` and the LLM may write narrative notes to `instill/<topic>.md`. Session budget: ≤ 8 cards, ≤ 3 new cards.
- **lint** detects contradictions, stale claims, orphan pages, missing cross-refs, data gaps. Auto-fix mechanical issues; ask the user about judgment calls.

## Hard constraints

- `raw/` is immutable. Never edit or delete files there. If a clipping is wrong, add a new file and move the old one to `raw/_deprecated/`.
- Every wiki claim needs a source. Unsourced claims must be marked `> ❓ 출처 미확인`.
- Update `wiki/index.md` and `wiki/log.md` on every wiki mutation.
- Korean polite speech (존댓말) is required in user-facing responses per the user's global preference.

## Cross-tool compatibility

`CLAUDE.md` is the canonical schema file. For agents on other platforms, the user may have symlinked or copied it to `AGENTS.md` (Cursor/Codex) or `GEMINI.md` (Gemini CLI). Treat any of those names as equivalent — they point to the same content.

## Commands the user may type

| Input | Action |
|---|---|
| `raw/X.md ingest 해줘` | run ingest workflow including auto card extraction |
| `Q 답해줘` / `Q에 대해 wiki에 뭐가 있어?` | run query workflow |
| `instill` | start mixed-deck instill session (interleaved across topics) |
| `instill <topic>` | start topic-scoped instill session |
| `more` | extend current session by 4 cards |
| `stop` / `그만` / `종료` | end instill session, update narrative notes + `wiki/log.md` |
| `lint` / `wiki 점검해줘` | run lint workflow |

</details>

