# instill

**LLM wiki + active recall.** LLM이 직접 유지하는 개인 지식 베이스 위에, 그 지식을 *사용자의 머릿속으로 옮기는* 학습 루프를 얹은 Claude Code 운영 schema.

기반:
- Andrej Karpathy의 [LLM Wiki 패턴](https://gist.github.com/karpathy/...) — LLM이 raw 소스를 한 번 읽고 결과를 wiki에 누적.
- Active recall — 정보 전달이 아니라 사용자가 답하고 LLM이 평가하는 루프로 내재화.

## 무엇이 다른가

대부분의 "LLM 노트" 도구는 **읽기/검색** 까지다. RAG든 wiki든 LLM이 답하고 사람이 읽고 끝. 이 repo의 핵심은 **3번째 모드**:

| 모드 | 누가 답하나 | 목적 |
|---|---|---|
| ingest | LLM | raw → wiki |
| query | LLM | wiki → 답변 |
| **instill** | **사용자** | **wiki → 사용자 머릿속** |

instill 모드에서 LLM은 강의하지 않는다. 사용자에게 묻고, 답을 평가하고, 빈 곳에 반례·후속 질문을 던진다. 한 sub-topic 이 견고해지면 다음으로 넘어간다. 세션 진척도는 `instill/<topic>.md` 에 저장돼 다음 세션에서 이어진다.

## 구조

```
.
├── CLAUDE.md       # ← 운영 schema 전체. 가장 먼저 읽을 것.
├── raw/            # 원본 소스 (immutable)
├── wiki/           # LLM이 작성·유지하는 페이지
│   ├── index.md
│   ├── log.md
│   ├── sources/  concepts/  entities/
└── instill/        # 주제별 학습 진척도 (lazy-load)
    └── <topic>.md
```

`CLAUDE.md` 가 모든 워크플로우(ingest / query / instill / lint)의 규칙을 정의한다. Claude Code는 이 파일을 시스템 프롬프트처럼 읽고 동작한다.

## 사용

1. Claude Code 를 이 디렉터리에서 실행한다.
2. `raw/<slug>.md` 에 글·논문·노트를 떨어뜨리고 `raw/<slug>.md ingest 해줘`.
3. 질문은 자연어로 — `X 에 대해 wiki 에 뭐가 있어?`
4. 학습하고 싶을 때 — `instill <주제>`. LLM이 질문하기 시작한다. `stop` 으로 종료.
5. 가끔 `wiki 점검해줘` 로 lint.

세부 명령은 [CLAUDE.md §8](CLAUDE.md) 참조.

## 시작하기

이 repo 자체는 schema 만 담는다 (`CLAUDE.md` + `README.md`). 본인의 `raw/`, `wiki/`, `instill/` 은 clone 후 본인 콘텐츠로 채운다 — `.gitignore` 에 이미 제외돼 있다.

```bash
git clone <this-repo> my-wiki
cd my-wiki
mkdir raw wiki instill
# raw/ 에 첫 소스를 떨어뜨리고 Claude Code 실행
```

## 권장

- **Obsidian** — `wiki/` 를 vault 로 열면 그래프 뷰·백링크·검색을 얻는다.
- **git** — 개인 wiki 자체는 private repo 로 따로 관리하면 좋다.
