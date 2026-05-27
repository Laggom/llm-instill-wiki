# CLAUDE.md — LLM Wiki 운영 규칙

이 파일은 본 wiki의 **schema**다. Claude Code가 이 wiki를 유지·확장할 때 따라야 할 구조, 형식, 워크플로우를 정의한다. Karpathy의 [LLM Wiki 패턴](raw/karpathy-llm-wiki.md)을 기반으로 한다.

> 원칙: 사람은 큐레이션·질문·방향 설정만 한다. LLM이 wiki 전체를 작성·유지한다.

---

## 1. 디렉터리 구조

```
.
├── CLAUDE.md          # 이 파일 — schema/운영 규칙
├── README.md          # 사람을 위한 안내
├── raw/               # 원본 소스 (immutable, 수정 금지)
│   ├── *.md           # 클리핑한 글, 논문, 노트
│   └── assets/        # 이미지·첨부 (필요 시 생성)
├── wiki/              # LLM이 작성/유지하는 마크다운 (mutable)
│   ├── index.md       # 전체 페이지 카탈로그
│   ├── log.md         # 시간순 작업 기록 (append-only)
│   ├── sources/       # 소스별 요약 페이지 (1 source = 1 page)
│   ├── concepts/      # 개념 페이지 (idea, theory, pattern)
│   └── entities/      # 사람·도구·조직·제품 페이지
└── instill/           # instill 세션 진척도 (lazy-load, 주제별 1파일)
    └── <topic>.md     # 예: cc-memory.md
```

향후 필요하면 `wiki/comparisons/`, `wiki/timelines/` 등을 추가할 수 있다. 새 카테고리를 만들 때는 이 파일을 함께 갱신한다.

---

## 2. 페이지 형식

### 2.1 YAML frontmatter (필수)

```yaml
---
title: 페이지 제목
type: source | concept | entity
tags: [tag1, tag2]
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: 1            # 이 페이지를 뒷받침하는 raw/ 소스 개수
status: stub | draft | stable
---
```

- `type` 은 페이지가 위치한 디렉터리와 일치해야 한다.
- `entities/` 의 경우 `kind: person | tool | org | product` 를 추가로 둘 수 있다.
- 새 소스로 페이지를 갱신할 때마다 `updated` 와 `sources` 를 손본다.

### 2.2 본문 구조

```markdown
# 페이지 제목

## 한 줄 요약
페이지가 무엇을 다루는지 한 문장으로.

## 본문
자유 구조. 소제목은 페이지 성격에 맞춰 자유롭게.

## 관련 페이지
- [[concepts/foo]] — 왜 관련 있는지 한 줄
- [[entities/bar]] — 왜 관련 있는지 한 줄

## 출처
- [karpathy-llm-wiki](../../raw/karpathy-llm-wiki.md) — 어느 부분에서 인용
```

링크는 Obsidian-style `[[wiki/path/page]]` 와 일반 마크다운 `[text](path)` 둘 다 허용한다. 한 페이지 안에서는 일관되게 쓴다.

---

## 3. 명명 규칙

- 파일명: `kebab-case.md` (영문 슬러그). 검색·링크 편의 때문.
- 제목(`title`)은 한국어 가능.
- 사람 페이지: `entities/firstname-lastname.md` (예: `entities/andrej-karpathy.md`).
- 소스 페이지 파일명: raw 파일과 1:1 매칭되도록 같은 슬러그 사용.

---

## 4. 워크플로우

### 4.1 Ingest — 새 소스 추가

1. 사용자가 `raw/<slug>.md` (또는 PDF 등) 에 파일 저장.
2. LLM은 raw 파일을 **읽기 전용**으로 열고 핵심 내용을 추출한다.
3. `wiki/sources/<slug>.md` 생성. 요약, 핵심 주장, 인용할만한 문장.
4. 등장한 개념·인물·도구별로 `wiki/concepts/`·`wiki/entities/` 페이지를 새로 만들거나 업데이트.
5. 다른 페이지에서 새 정보와 모순되는 부분이 있으면 양쪽에 메모를 남긴다 (`> ⚠ 2026-05-25: source X 와 충돌, 정리 필요`).
6. `wiki/index.md` 에 새 페이지 항목 추가.
7. **Instill 카드 추출** — 새로/갱신된 페이지마다 frontmatter 의 `instill:` 배열에 원자적 주장(카드)을 추가한다. 각 카드는 `id`, `claim` (한 줄), `importance` (high/med/low), `solo-target` (recall/uni/multi/relational/transfer). id 는 wiki 전역 unique (예: `cc-mem-001`). 추출 후 카드마다 `python tools/instill_sched.py enroll --id <id> --importance <h/m/l> --topic <topic>` 호출하여 deck 에 등록.
8. `wiki/log.md` 에 ingest 항목 append (신규 카드 개수 포함).

한 소스 ingest 시 10~15개 페이지를 건드릴 수 있다. 정상이다. 카드 추출은 사용자 승인 없이 자동 — drop 은 instill 세션 시작 시 한다 (§4.3).

### 4.2 Query — 질문 응답

1. `wiki/index.md` 를 먼저 읽고 관련 페이지를 식별한다.
2. 관련 페이지를 읽어 합성된 답변을 만든다. 모든 주장에 인용을 단다 (`[[concepts/foo]]`).
3. **답변이 재사용 가치가 있으면 wiki 페이지로 환원한다.** 비교표·분석·연결 발견 등은 `wiki/concepts/<topic>-vs-<topic>.md` 또는 `wiki/concepts/<insight>.md` 로 저장하고 index·log 갱신.
4. `wiki/log.md` 에 query 항목 append.

### 4.3 Instill — 사용자에게 지식 주입 (v2: FSRS + SOLO)

**언제**: 사용자가 `instill` (혼합 deck) 또는 `instill <주제>` (토픽 한정) 라고 할 때.

**query 와의 차이**: query 는 LLM 이 답한다. instill 은 **사용자가 답하고 LLM 이 평가한다**.

**v2 의 토대 (학습과학)**:
- **Testing effect** — retrieval > 재학습 (Roediger & Karpicke 2006)
- **Spacing effect** — 간격 두면 정착률 ↑ (Cepeda et al. 2008). 스케줄링은 **FSRS-4.5** (Anki 채택).
- **Desirable difficulties** — 인터리빙 기본, 약간 실패할 정도 적정 (Bjork).
- **Mastery learning** — 단발 정답 ≠ 마스터. 간격을 둔 다수 성공.
- **SOLO taxonomy** — 깊이 5단계 (recall / uni / multi / relational / transfer).

**스케줄러**: `tools/instill_sched.py` 가 FSRS 계산 담당. LLM 은 CLI 호출만, 수식 직접 계산 금지.

**세션 흐름**:

1. **오늘의 큐 산출**: `python tools/instill_sched.py today [--topic X] --limit 8 --new-limit 3` 호출. due + new_candidates JSON 받음.
2. **신규 후보 drop 단계**: new_candidates 가 있으면 사용자에게 목록 보여주고 "빼고 싶은 게 있나요?" 묻기. drop 된 것은 `python tools/instill_sched.py skip --id X`.
3. **세션 시작**: 최대 8장 (due + 신규 ≤ 3). 인터리빙 순서.
4. **카드마다**:
   - SOLO target level 에 맞는 질문 유형 (아래 표).
   - 사용자 답 → 답변 길이는 짧게, 한 카드 = 한 질문 호흡.
   - LLM 이 grade 판정 → `python tools/instill_sched.py review --id X --grade {again,hard,good,easy}`.
5. **8장 끝**: "더 할래?" → `more` 면 +4장. 아니면 종료.
6. **세션 종료**: 다룬 토픽별 `instill/<topic>.md` 갱신 (서사 메모 — 마스터, 진행 중, 약점, 강점). `wiki/log.md` 에 1줄.

**Grade rubric**:

| Grade | 기준 | 효과 |
|---|---|---|
| **Again** | 핵심 누락·오답. counter-question/힌트 후에도 못 잡음. | lapse +1, 짧은 간격 재등장. SOLO target 한 단계 ↓ 후보. |
| **Hard** | 부분적. 힌트 한 번에 잡음. | 같은 SOLO target, 간격 살짝만 늘림. |
| **Good** | 정확. | 같은 target, 표준 간격. |
| **Easy** | 정확 + 연결·응용 자발적. | 한 단계 ↑ 후보. 큰 간격. |

**SOLO 레벨 ↔ 질문 유형**:

| SOLO | 설명 | 질문 예 |
|---|---|---|
| recall | 사실 회상 | "X 가 뭐야?" |
| uni | 한 측면 | "X 의 주요 특성 하나는?" |
| multi | 다중 측면 | "X 의 두 단계를 설명해" |
| relational | 관계·구분·근거 | "X 와 Y 의 차이는? 왜 그렇게 설계됐어?" |
| transfer | 응용 | "Z 라는 새 상황에서 X 를 어떻게 쓸까?" |

카드의 `solo-target` 은 *최종* 도달점. 처음엔 recall 부터, grade 추이에 따라 target 까지 올림.

**원칙**:
- **먼저 묻고, 그 다음 설명한다.** 강의 금지.
- **모르면 답을 바로 주기 전에 한 단계 힌트.** Self-correct 가 학습 효과 최고.
- **정답 확인은 구체적으로**: "맞다" 가 아니라 "*ingest 시점에 합성한다* 라는 부분이 핵심".
- **답변 길이는 짧게**. query 처럼 표·섹션 X. 한두 문장 + 한 질문.
- **세션 중에 wiki 를 수정하지 않는다.** read-only. (스케줄러 호출은 deck 만 갱신, wiki/raw 는 안 건드림.)
- **인터리빙 기본**. `instill <topic>` 으로 한정도 가능하지만 Bjork 연구는 혼합을 지지.

**Backlog 폭주 대응**: due > 8 이면 스케줄러가 우선순위 정렬 (lapses → 가장 overdue → importance) 후 상위만 반환. 미진행 due 는 사라지지 않고 다음 세션으로 이월.

**서사 메모 — `instill/<topic>.md`** (lazy-load):

FSRS 의 정량 상태(`_deck.json`) 와 별개로, 토픽별 코칭 노트는 `instill/<topic>.md` 에 마크다운으로. 마스터한 개념, 약점/강점 패턴, 세션 로그. 일반 세션에선 LLM 이 읽지 않음 — instill 시작 시에만.

**`wiki/log.md` 항목 형식**:

```
## [YYYY-MM-DD] instill | <혼합 | topic>
- 카드: 8장 (due 6 / 신규 2). grade: 4G/2H/2A.
- 다룬 토픽: cc-memory, cc-skills
- 강점: ...
- 약점: ...
- 종료: 정상 / more / 사용자 stop
```

### 4.4 Lint — 정기 점검

사용자가 "lint" 또는 "wiki 점검" 을 요청하면:

- **모순 (contradictions)** — 같은 사실에 대해 두 페이지가 다르게 말하는 경우
- **stale claims** — 새 소스로 갱신해야 할 오래된 주장
- **orphan pages** — 어디서도 링크되지 않는 페이지
- **missing pages** — 자주 언급되지만 자체 페이지가 없는 개념
- **missing cross-refs** — 두 페이지가 분명히 관련 있는데 서로 링크가 없는 경우
- **data gaps** — 웹 검색으로 채울 수 있는 빈틈

결과는 `wiki/log.md` 에 `lint` 항목으로 기록하고, 자동으로 고칠 수 있는 것 (orphan 페이지에 백링크 추가 등) 은 바로 고친다. 판단이 필요한 것 (모순) 은 사용자에게 물어본다.

---

## 5. index.md 형식

```markdown
# Index

## Sources
- [[sources/karpathy-llm-wiki]] — LLM이 wiki를 유지·확장하는 패턴 (2026-05-25)

## Concepts
- [[concepts/llm-wiki-pattern]] — RAG와 다른, 누적되는 지식 베이스
- [[concepts/three-layer-architecture]] — raw / wiki / schema 세 층

## Entities
- [[entities/obsidian]] — markdown 기반 PKM 도구
- [[entities/qmd]] — 로컬 markdown 검색 엔진
```

카테고리별로 묶고, 각 항목은 한 줄. wiki가 커지면 카테고리 내부에서 알파벳·주제·날짜순 정렬을 도입할 수 있다.

---

## 6. log.md 형식

append-only. 항상 가장 최근 항목이 **위**가 아니라 **아래**에 오도록 한다 (시간순). 각 항목은 `## [YYYY-MM-DD] <op> | <한줄>` 헤더로 시작한다 — 이러면 `grep "^## \[" log.md | tail -10` 식으로 최근 활동을 뽑을 수 있다.

```markdown
## [2026-05-25] ingest | Karpathy — LLM Wiki
- raw: raw/karpathy-llm-wiki.md
- 신규: [[sources/karpathy-llm-wiki]], [[concepts/llm-wiki-pattern]], [[concepts/three-layer-architecture]], [[entities/obsidian]]
- 갱신: [[index]]

## [2026-05-26] query | RAG vs wiki, 핵심 차이?
- 참조: [[concepts/llm-wiki-pattern]], [[sources/karpathy-llm-wiki]]
- 결과: [[concepts/rag-vs-wiki]] 신규

## [2026-05-30] lint
- orphan 2: [[entities/marp]], [[entities/dataview]] → index에 추가
- contradiction 0

## [2026-06-01] instill | RAG vs LLM Wiki
- 다룬 페이지: [[concepts/rag-vs-wiki]], [[concepts/llm-wiki-pattern]]
- 강점: 합성 시점 구분 이해
- 약점: 모순 검출 메커니즘 (lint)
- 보강: 반례 + 직접 설명 + 재질문
- 종료: 마스터
```

---

## 7. 운영 원칙

1. **raw/는 절대 수정·삭제하지 않는다.** 출처 무결성. 잘못 클리핑된 경우엔 새 파일로 추가하고 기존 것은 `raw/_deprecated/` 로 옮긴다.
2. **wiki/ 페이지에는 모두 출처가 있어야 한다.** 출처 없는 주장은 `> ❓ 출처 미확인` 로 표시.
3. **변경할 때마다 index.md와 log.md를 함께 업데이트한다.** 빼먹으면 wiki가 빠르게 망가진다.
4. **링크는 적극적으로.** 두 페이지가 관련 있어 보이면 양방향 링크. 백링크가 wiki의 가치.
5. **요약은 짧게, 본문은 충실하게.** 한 줄 요약은 사용자가 index 에서 훑을 때 1초 안에 의미가 잡혀야 한다.
6. **추측 금지.** raw 소스에 없는 내용은 추가하지 않는다. 외부 지식이 필요하면 `web search 필요` 로 표시하고 사용자에게 알린다.

---

## 8. 사용자가 자주 쓸 명령

자연어 — 별도 슬래시 명령 없음.

- `raw/X.md ingest 해줘` — ingest 워크플로우 실행 (자동 카드 추출 포함)
- `Q에 대해 wiki에 뭐가 있어?` 또는 `Q 답해줘` — query 워크플로우
- `instill` — 모든 토픽 혼합 deck 으로 instill 세션 시작 (기본, 인터리빙)
- `instill <주제>` — 토픽 한정 세션
- `more` — 8장 끝났을 때 4장 추가
- `stop` / `그만` / `종료` — 진행 중인 instill 세션 종료
- `wiki 점검해줘` 또는 `lint` — lint 워크플로우
- `index 보여줘` — `wiki/index.md` 출력
- `최근 활동` — `wiki/log.md` 마지막 N개 항목 출력

---

## 9. 향후 확장 (현재는 도입하지 않음)

- **검색 엔진**: 페이지가 ~100개를 넘어가면 [[entities/qmd]] 같은 로컬 검색 도구 도입 검토.
- **Dataview 쿼리**: frontmatter 기반 동적 표·목록.
- **자동 백링크**: 모든 페이지 하단에 inbound link 목록 자동 생성.
- **git 통합**: ingest/lint 마다 자동 commit.

도입할 때 이 파일에 섹션을 추가한다.
