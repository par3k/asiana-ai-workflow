# CLAUDE.md

이 파일은 Claude Code가 세션마다 자동으로 읽는 프로젝트 지침입니다.
사용자가 요청한 작업 방식과 규칙을 여기에 누적해서 기록합니다. 새 규칙이 생기면 이 파일에 추가하세요.

## 프로젝트 개요
- FastAPI 기반 쇼핑몰 백엔드 + AI 챗봇 (멀티캠퍼스 AI 에이전트 실습 프로젝트)
- 원격 저장소: https://github.com/par3k/asiana-ai-workflow.git (origin, 기본 브랜치 `main`)
- 기능 상세는 [README.md](README.md) 참고

## 기술 스택
- 웹/DB: FastAPI, SQLAlchemy, PostgreSQL(pgvector), JWT(python-jose, bcrypt), Pydantic
- AI: OpenAI(gpt-4.1-mini, 임베딩 text-embedding-3-large), LangChain, LangGraph(+PostgresSaver checkpointer), BM25 하이브리드 검색, Ollama(sLLM), Redis Stack(시맨틱 캐시)
- 관측: LangSmith, Langfuse (키는 `.env`)

## 코드 구조 (`app/`)
- `main.py`: 앱 진입점. 시작 시 `setup_logging()`과 `create_all`, 종료 시 action_graph의 checkpointer 커넥션 풀 close
- `middleware.py`: 모든 API 요청을 `api.access` 로그로 기록(요청ID, method, path+query, member_id, client, 상태코드, 소요시간). 비밀번호 등이 있을 수 있어 요청 body와 토큰 값은 기록하지 않는다. 응답 헤더에 `X-Request-ID`
- 라우터별 업무 로그(`api.member/order/product/document/chat`): 가입·로그인 성공/실패, 주문 생성/취소, 상품 등록/수정/조회, 문서 추가/수정, 챗 질문(100자)·분류·응답길이
- `logging_config.py`: 로그 파일 롤링. `logs/app.log`(10MB x 5개 보관), `print()`·uvicorn·root 로거를 함께 기록. 위치는 `LOG_DIR`로 변경 가능. 실행되는 SQL(`sqlalchemy.engine`)도 파일에만 기록하며, 바인딩 파라미터는 `database.py`의 `hide_parameters`로 숨기고(`SQL_LOG_PARAMS=true`면 표시), 한 건이 1500자를 넘으면 잘라서 기록한다. `SQL_LOG=false`로 끌 수 있다
- `routers/`: member(`/members` 가입/로그인/me), product, order, document, chat(`/chats`)
- `services/`: auth, chat_service, order_service, product_service
- `models/`, `schemas/`, `database.py`, `dependencies.py`: ORM, Pydantic, DB 세션, 인증 의존성
- `ai/llm_use/`: LLM 호출 (OpenAI 직접 호출 `llm_calling_simple`, LangChain/Ollama `llm_calling_langchain`, 분류 목록)
- `ai/rag/`: retriever(하이브리드 검색), vector_store, memory(대화 이력), semantic_cache(Redis)
- `ai/api_use/`: 1차 분류 후 get_api 처리
  - `chat_classify.py`, `intent_list.py`: QUERY / ACTION / GENERAL 2차 분류
  - `query/`: SQL 생성(generator) → 검증(validator) → 실행(executor) → 응답(response), `schema_context`
  - `action/`: tool calling 기반 주문/상품 액션 (`registry`, `order_actions`, `product_actions`, `action_pipeline`)
- `ai/langgraph/`: 위 파이프라인의 LangGraph 버전
  - `main_graph`(최상위), `get_api_graph`(서브), `sql_graph`, `action_graph`(HITL interrupt + PostgresSaver), `state`, `parallel_reducer_streaming`(reducer 실습용)
- `ai/langsmith/`: 평가 데이터셋(jsonl)과 실행 스크립트
- `ai/sllm_pinetunning/`: sLLM LoRA 파인튜닝 스크립트 1~4 + Modelfile (디렉터리명 오타 `pinetunning`은 원본 그대로)

## 챗 파이프라인 현황 (중요)
- `routers/chat.py`의 `POST /chats`는 **현재 LangGraph를 쓰지 않는다.** `run_chat_graph` / `run_chat_graph_hitl` 호출은 주석 처리되어 있고, `classify_message`(OpenAI 직접 호출) 기반 if/elif 분기(get_my_orders / get_my_profile / get_policy / 그 외)로 동작한다. get_api 분기도 주석 처리 상태다.
- LangGraph 경로(캐시 → 1차 분류 → get_api(QUERY/ACTION/GENERAL)/profile/policy/general → 캐시 저장)는 `main_graph.py`에 구현되어 있다. 쓰려면 chat.py의 주석을 전환해야 한다.
- ACTION은 실행 전 `interrupt()`로 사용자 확인("예/아니오")을 받는다(HITL). 대기 상태는 `thread_id=member-{id}`로 저장된다.
- `GET /chats/reducer-streaming`은 병렬 노드 + reducer 확인용 테스트 엔드포인트다.
- `classify_message_n8n`은 `http://localhost:5678` n8n 웹훅 호출용이며 현재 사용하지 않는다.
- `main_graph.py`는 임포트 시 그래프 mermaid 구조를 콘솔에 출력한다.

## 작업 규칙 (사용자 지시)

### 언어
- 모든 응답과 설명은 한국어로 작성한다. 코드 식별자와 기술 용어는 원문 그대로 둔다.
- 사용자 전역 설정(`~/.claude/settings.json`)에 `"language": "korean"`이 이미 설정되어 있다.

### Git 작업 방식
- 소스나 설정을 수정할 때는 `main`에 직접 커밋하지 않는다.
  1. 작업마다 새 브랜치를 만든다 (`feature/<작업>`, `chore/<작업>` 등).
  2. 브랜치에서 수정하고 커밋한다.
  3. 로컬 `main`에 `--no-ff`로 머지한다.
- "깃에 올려줘", "푸시해줘"처럼 사용자가 git에 올리라고 요청하면 **원격 push까지 포함**한 것으로 본다. 브랜치 작업 → 커밋 → 로컬 `main` 머지 → `git push origin main`까지 한 번에 진행하고, push 전에 다시 허락을 구하지 않는다.
- 사용자가 올리라고 요청하지 않았는데 push하지는 않는다.
- 변경 전에 매번 허락을 구하지 않고 알아서 진행한다. 단 삭제, force push(`--force`), 원격 브랜치 삭제 같은 되돌리기 어려운 작업은 예외로 먼저 확인한다.
- 커밋 메시지는 한국어로 쓰고, 끝에 Co-Authored-By 줄을 붙인다.
- 이 레포의 git 작성자는 레포 로컬 설정이다 (`user.email=hoijae0194@gmail.com`, `user.name=par3k`).
- 머지하면 작업 폴더의 `.env`가 삭제된 적이 있다. 머지 후에는 `.env`가 남아 있는지 확인한다.
- 이 폴더는 원격과 히스토리를 맞춰 `git init`한 상태다(origin 연결, 기본 브랜치 `main`). 원격에는 과거 커밋의 `.env`가 남아 있다.
- 추적 해제 커밋을 머지하면 `.env`가 삭제된다. 복구하려면 `git show c7b79c1:.env > .env`(과거 값이라 현재 값과 다를 수 있음).

### Docker
- 사용자가 따로 요청하지 않으면 Docker(컨테이너, 이미지)를 조작하지 않는다. (`docker run/exec/stop/rm` 모두 포함)
- 컨테이너 안에서 해야 하는 작업은 명령어만 안내한다.
- 서버를 종료할 때는 이 프로젝트에서 직접 띄운 프로세스만 대상으로 한다. 포트(8000) 점유 프로세스를 PID 확인 없이 종료하지 않는다(사용자가 직접 띄운 서버를 끈 적이 있다). 서버 테스트는 사용자 서버와 겹치지 않게 다른 포트(예: 8001)로 띄우고, 자기가 띄운 PID만 종료한다.

### 보안
- `.env`의 값(API 키, DB 비밀번호)을 출력하거나 문서에 적지 않는다. 키 이름만 언급한다.
- `.env`는 `.gitignore`에 포함되어 있고 git 추적에서도 제외되어 있다. 커밋하지 않는다.
- 사용자 환경변수(`setx`)에는 `OPENAI_API_KEY`만 설정되어 있다. 새 터미널에서는 `.env`보다 이 값이 우선한다.
- 과거 커밋 기록에는 `.env`가 남아 있을 수 있다. 키 재발급은 사용자가 판단한다.

## 개발 환경
- Python 3.13 가상환경: `.venv` (3.14는 일부 패키지 wheel이 없어 사용하지 않음). 새로 받았다면 `py -3.13 -m venv .venv` → `pip install -r requirements.txt`
- 실행: `.venv\Scripts\activate` 후 `uvicorn app.main:app --reload` (기본 포트 8000, 문서 `/docs`)
- DB: 사용자가 Docker로 직접 띄운 PostgreSQL(pgvector) 컨테이너 `postgres-db-with-vector`, 호스트 포트 **5433**, DB 이름 `ai_agent_db`. `action_graph`의 checkpointer도 같은 `DATABASE_URL`로 별도 커넥션 풀을 연다.
- `.env` 키: `DATABASE_URL`, `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `OPENAI_API_KEY`, `USE_SEMANTIC_CACHE`, `LANGSMITH_TRACING`, `LANGSMITH_PROJECT`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_BASE_URL`
- 코드가 읽는 선택 환경변수(`.env`에 없으면 기본값): `REDIS_HOST`(localhost), `REDIS_PORT`(6379), `SEMANTIC_CACHE_TTL`(86400), `LOG_DIR`(프로젝트 루트/logs), `SQL_LOG`(true), `SQL_LOG_PARAMS`(false), `HF_TOKEN`(파인튜닝 전용)
- 로그: 콘솔과 함께 `logs/app.log`에 기록된다(`logs/`는 `.gitignore` 대상). 로그 파일은 `Get-Content -Encoding UTF8`로 읽는다(그냥 열면 한글이 깨져 보인다).
- `USE_SEMANTIC_CACHE=false`이면 Redis Stack 없이도 `/chats`가 동작한다.
- Ollama(로컬 설치, 기본 `localhost:11434`; 설치 여부는 `ollama --version`으로 확인): 프로필 응답과 sLLM 분류기에 `llama3.2:3b`(`llm_calling_langchain.py`), SQL 생성 쪽에 `llama3.1:8b`(`api_use/query/generator.py`)를 쓴다. 파인튜닝 모델 테스트는 `localhost:11434`를 호출한다.
- 앱은 시작할 때 `Base.metadata.create_all`로 테이블을 만든다. 마이그레이션 도구는 쓰지 않는다.
- 파인튜닝 스크립트(`app/ai/sllm_pinetunning`)는 서버 실행과 무관하고 GPU 환경(runpod)에서 돌린다.

## 변경 이력
- 2026-10-06: `.env`를 `.gitignore`에 추가하고 추적 해제, 가상환경 구성, DB 포트를 5433으로 변경, 이 파일 추가
- 2026-10-06: 레포를 새로 받은 상태에 맞춰 최신화 (코드 구조/챗 파이프라인 현황/환경변수 갱신, 존재하지 않는 `chat2`·`text_to_sql` 기술 제거, `.git`·`.venv` 없음 기록). 이어서 `.gitignore`의 `.env` 주석을 풀어 다시 제외 처리, `.venv` 생성 및 서버 기동 확인
- 2026-10-06: 원격과 히스토리를 맞춰 git 재초기화 후 `.env` 추적 해제를 `main`에 push, 로그 파일 롤링(`logging_config.py`) 추가
- 2026-10-06: "깃에 올린다"는 요청은 push까지 포함하며 별도 허락 없이 진행하도록 규칙 변경
- 2026-10-06: API 요청 로그 미들웨어와 라우터별 업무 로그 추가
- 2026-10-06: 실행 SQL 로그(`sqlalchemy.engine`) 추가 (파라미터 숨김, 파일 전용)
