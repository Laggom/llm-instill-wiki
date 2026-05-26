# Instill v2 — 학습과학 기반 재설계

> 작성일: 2026-05-27
> 대상 변경: `CLAUDE.md §4.3` 의 instill 워크플로우 전면 개정.

---

## 1. 문제 정의

v1 instill (현 CLAUDE.md §4.3) 의 한계:

1. **질문 선택이 ad-hoc** — LLM 이 그때그때 판단. 같은 사용자도 세션마다 다른 흐름.
2. **마스터 판정이 직관 기반** — "잘 답했다" 한 번이면 ✅. 단발 정답 ≠ 장기기억.
3. **재학습/간격 없음** — 한 번 마스터하면 다시 안 묻음. Ebbinghaus 망각곡선 무시.
4. **깊이 조절 모호** — 표면적 답에 만족할지 push 할지 일관성 없음.
5. **규모 비대응** — wiki 가 커지면 사람이 모든 걸 instill 할 수 없음. 우선순위·예산 개념 부재.

## 2. 설계 원칙

학습과학 연구 기반:

- **Testing effect** (Roediger & Karpicke 2006) — retrieval 이 재학습보다 우월. instill 은 무조건 능동 retrieval.
- **Spacing effect** (Cepeda et al. 2008) — 간격 두면 정착률 ↑. 최적 간격 ≈ 목표 retention 의 10–20%.
- **Desirable difficulties** (Bjork) — 너무 쉬우면 학습 효과 ↓. 약간 실패할 정도가 적정. 인터리빙 > 블록.
- **Mastery learning** (Bloom) — 마스터 = 간격을 둔 다수 성공.
- **SOLO taxonomy** (Biggs) — 이해의 깊이 5단계 (Pre / Uni / Multi / Relational / Extended abstract).

이를 다음 결정으로 구체화:

| 영역 | 채택 방식 |
|---|---|
| 스케줄링 | **FSRS** (Anki 2024+ 기본). SM-2 의 다음 세대, neural memory model 기반. |
| 단위 | **카드(원자적 주장)**. 페이지 단위 아님. |
| 평가 | **4단 grade** (Again / Hard / Good / Easy) — FSRS 표준. |
| 깊이 | 카드별 SOLO target level. 박스 후반일수록 더 높은 SOLO 질문. |
| 예산 | 세션당 **최대 8장** (≈ 5분). |
| 신규 throttle | 세션당 신규 ≤ 3장. |
| 풀 구성 | ingest 시 LLM 자동 추출. 세션 시작 시 사용자가 drop 가능. |
| 인터리빙 | `instill` (인자 없음) = 모든 토픽 혼합 deck (기본). 토픽 한정도 지원. |

## 3. 아키텍처

### 3.1 데이터 모델

**(a) 카드 정의** — 원본 wiki 페이지 frontmatter 에 박힘:

```yaml
---
title: cc-memory
type: concept
...
instill:
  - id: cc-mem-001
    claim: "CLAUDE.md 는 system prompt 가 아니라 첫 user message 로 들어간다"
    importance: high
    solo-target: relational
    skip: false
  - id: cc-mem-002
    claim: "scope 우선순위는 좁은 것이 이긴다"
    importance: med
    solo-target: multi
---
```

- `id` 는 wiki 전역 unique (e.g., `cc-mem-001`).
- `claim` 은 한 줄. retrieval 정답의 기준.
- `importance: high|med|low` — backlog 폭주 시 우선순위.
- `solo-target` — 이 카드가 도달해야 할 SOLO 레벨. `recall|uni|multi|relational|transfer`.
- `skip: true` — 사용자가 drop 한 카드. 다시 제안되지 않음.

**(b) 스케줄 상태** — `instill/_deck.md` 한 파일에 모인다:

```yaml
---
type: instill-deck
updated: 2026-05-27
fsrs:
  request_retention: 0.9
  maximum_interval: 365
---

# Deck

## Active

| id | stability | difficulty | due | reps | lapses | last-grade |
|---|---|---|---|---|---|---|
| cc-mem-001 | 12.4 | 5.2 | 2026-06-08 | 3 | 0 | Good |
| cc-mem-002 | 2.1  | 7.8 | 2026-05-28 | 1 | 1 | Hard |
| cc-mem-003 | —    | —   | new        | 0 | 0 | — |

## Skipped

- cc-mem-099 (drop 2026-05-27)
```

- `stability`, `difficulty` — FSRS 의 핵심 상태. 스크립트가 계산.
- `due` — 다음 retrieval 예정일. 세션 시작 시 `due ≤ today` 인 것만 후보.
- `last-grade` — Again / Hard / Good / Easy.

**(c) 토픽별 진척 메모** — `instill/<topic>.md` (v1 와 같은 위치):
- "마스터한 개념", "약점/강점" 같은 *서사적 메모*. FSRS 의 정량 상태와 별개로 LLM 의 코칭 노트.
- 카드별 정량은 `_deck.md` 가 단일 소스. `<topic>.md` 는 사람 가독용.

### 3.2 스케줄러 — `tools/instill_sched.py`

FSRS 의 stability/difficulty 업데이트 수식은 LLM 이 매번 계산하면 오류 발생 위험. 결정론적 스크립트로 분리.

**인터페이스** (CLI):

```bash
# 세션 시작 시 오늘의 큐 산출
python tools/instill_sched.py today
# → JSON: { "due": [...], "new_candidates": [...] }

# retrieval 결과 기록
python tools/instill_sched.py review --id cc-mem-001 --grade good
# → _deck.md 의 해당 row 갱신

# 카드 신규 등록 (ingest 시 자동 호출)
python tools/instill_sched.py enroll --id cc-mem-007 --importance high

# 카드 영구 스킵
python tools/instill_sched.py skip --id cc-mem-099

# 상태 확인
python tools/instill_sched.py stats
# → 총 카드 수, due 수, 신규 후보 수, 평균 stability 등
```

**구현**: `py-fsrs` 라이브러리 사용 (FSRS 알고리즘 공식 Python 구현). 의존성 1개. 또는 자체 구현 — 100 LoC 정도.

**테스트**: pytest 로 알고리즘 정확성 검증 (FSRS 공식 테스트 벡터 사용).

### 3.3 세션 흐름

**`instill` (인자 없음) 입력 시 LLM 동작**:

1. `python tools/instill_sched.py today` 호출. `due` + `new_candidates` 받음.
2. due > 6 이면 우선순위로 6장 추림: `lapses > 0` → 가장 overdue → `importance: high`.
3. new_candidates 가 있으면 사용자에게 보여줌:
   > "오늘 due 6장 + 신규 후보 4장입니다. 신규 중 빼고 싶은 게 있나요?"
   > - cc-mem-005: "..."
   > - cc-mem-006: "..."
   > - ...
4. 사용자 응답 → drop 한 것은 `skip` 호출. 남은 신규 중 최대 3장이 이번 세션 deck 에 들어감.
5. 세션 시작: 인터리빙 순서로 8장 진행.
6. 카드마다:
   - SOLO target level 에 맞는 질문 유형 선택 (e.g., target=relational → "X 와 Y 가 어떻게 연결되나?")
   - 사용자 답 → LLM 이 grade 판정 (Again/Hard/Good/Easy)
   - **grade 기준** (rubric):
     - **Again**: 핵심 누락 또는 오답. → SOLO 레벨 한 단계 낮춰 다음 세션.
     - **Hard**: 부분적, 힌트 필요. → 같은 레벨 유지, 짧은 간격.
     - **Good**: 정확. → 같은 레벨, 표준 간격.
     - **Easy**: 정확 + 연결/응용 자발적. → 한 단계 올리거나 큰 간격.
   - `python tools/instill_sched.py review --id X --grade good`
7. 8장 끝 → "오늘 끝. 더 할래?" → `more` 면 +4장.
8. 세션 종료: `instill/<touched-topics>.md` 의 서사 메모 갱신, `wiki/log.md` 에 1줄.

**`instill <topic>` (토픽 한정)**: 같은 흐름이나 `today` 에 `--topic <topic>` 추가. 인터리빙 효과 ↓.

### 3.4 Ingest 변경

CLAUDE.md §4.1 의 ingest 워크플로우 마지막에 한 단계 추가:

> 6.5. 새 페이지/갱신된 페이지의 `instill:` 후보 카드를 LLM 이 추출하고 frontmatter 에 박는다. 각 카드는 `id`, `claim`, `importance`, `solo-target` 을 가진다. `python tools/instill_sched.py enroll --id ... --importance ...` 로 deck 에 등록.

사용자 승인 없음 — 자동.

## 4. SOLO 레벨과 질문 유형 매핑

| SOLO | 설명 | 질문 유형 예 |
|---|---|---|
| recall | 사실 회상 | "X 가 뭐야?" |
| uni | 한 측면 이해 | "X 의 주요 특성 한 가지는?" |
| multi | 다중 측면 | "X 가 작동하는 두 단계를 설명해" |
| relational | 관계·구분 | "X 와 Y 의 차이는? 왜 그렇게 설계됐어?" |
| transfer | 응용·전이 | "Z 라는 새 상황에서 X 를 어떻게 쓸까?" |

카드별 `solo-target` 은 사용자가 *최종적으로* 도달해야 할 레벨. 처음엔 recall 부터 시작해서 grade 추이에 따라 target 까지 올림.

## 5. Backlog 폭주 대응

세션당 due 가 8 초과 시:

1. **우선순위 정렬**: `lapses 많은 것 > 가장 overdue > importance: high > 그 외`.
2. 상위 6장 진행 (신규 3장은 별도 quota).
3. 미진행 due 는 사라지지 않음. 다음 세션에서 더 overdue 가 되어 우선순위 ↑.
4. 사용자에게 안내: "오늘 12장 due 인데 8장만 진행합니다. 나머지는 내일 우선."

FSRS 의 `request_retention` 을 낮추면 (e.g., 0.85) 간격이 길어져 backlog 가 줄어듦 — 향후 옵션.

## 6. 결정 로그

- **B 채택 이유 (vs A Leitner)**: 사용자가 "연구결과 토대" 명시. FSRS 가 가장 가까움. 스크립트 의존 비용은 수용 가능 판단.
- **카드 분해 = 페이지 분해 아님**: 페이지는 보통 여러 주장. 페이지 단위로 retrieval 하면 너무 광범위해서 grade 판정 불가.
- **세션 = 카드 수 cap (시간 cap 아님)**: 시간 추적은 LLM 이 부정확. 카드 수는 결정론적.
- **신규 throttle 별도**: backlog 가 아무리 커도 신규를 무한 도입하면 사용자가 빠짐. Anki 의 "new cards/day" 원리.
- **인터리빙 기본**: Bjork. 토픽 한정도 사용자 선택으로 유지.

## 7. 향후 (현재 범위 밖)

- **사용자 self-grade 모드**: LLM 판정 외에 사용자가 "사실 헷갈렸다" 자체 신고. 메타인지 데이터.
- **카드 합병/분할**: 너무 잘게/너무 크게 만든 카드를 lint 가 감지.
- **Q-bank**: 같은 카드의 질문 표현을 N 가지 캐시해서 다양성 ↑.
- **Ankifying export**: deck 을 .apkg 로 변환해 모바일에서도 학습.

## 8. CLAUDE.md 변경 요약

- §4.3 전면 개정. 새 흐름 (today → drop → 8장 진행 → review 기록) 명시.
- §4.1 ingest 에 카드 추출 단계 추가.
- §8 명령에 `instill` (인자 없음, 혼합 deck) 추가.
- 새 섹션 §10 "Instill 스케줄러" — `tools/instill_sched.py` 명세 요약 + 본 스펙 링크.

---

**다음**: 사용자 검토 → 승인 후 `tools/instill_sched.py` + CLAUDE.md 개정 → gitignore + git init + push.
