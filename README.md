# EmoAI

텍스트 기반 감정 대화 에이전트 플랫폼

## 개요

EmoAI는 Electron 프론트엔드와 FastAPI 백엔드로 구성된 텍스트 대화형 감정 에이전트입니다. B/I/T/E 전술 기반의 플래닝 시스템과 벡터 검색 메모리를 통해 자연스러운 한국어 대화를 제공합니다.

## 시스템 아키텍처

### 전체 구성

```
┌─────────────────┐    WebSocket    ┌─────────────────┐
│   Electron App  │◄──────────────►│   FastAPI       │
│                 │                 │   Backend       │
│  React/TypeScript│                 │   Python        │
└─────────────────┘                 └─────────────────┘
                                              │
                                    ┌─────────┼─────────┐
                                    │         │         │
                              ┌─────▼───┐ ┌──▼────┐ ┌──▼────┐
                              │ Vector  │ │ MySQL │ │ Model │
                              │ Store   │ │   DB  │ │Client │
                              └─────────┘ └───────┘ └───────┘
```

### 메인 로직 파이프라인

#### 2-콜 모드 (기본)
```
User Input → Vector Highlights → Planner (B/I/T/E) → Realizer → Response
     │                                                             │
     └─────────────── Background Jobs (Memory/Vector) ─────────────┘
```

#### 1-콜 모드
```
User Input → Direct Generation → Response
     │                             │
     └─── Background Jobs ─────────┘
```

## 디렉토리 구조

```
emoai/
├── app/electron/              # Electron 클라이언트
│   ├── main.js               # Electron 메인 프로세스
│   ├── preload.js            # Preload 스크립트
│   └── renderer/             # React 렌더러
│       ├── components/       # UI 컴포넌트
│       │   ├── ChatPane.tsx
│       │   ├── MessageBubble.tsx
│       │   ├── SessionList.tsx
│       │   └── TypingBubble.tsx
│       ├── services/         # 서비스 레이어
│       │   └── wsClient.ts
│       ├── store/            # 상태 관리
│       │   └── useSessions.ts
│       └── lib/              # 유틸리티
│           └── typingEffect.ts
├── server/                   # FastAPI 백엔드
│   ├── main.py              # 애플리케이션 진입점
│   ├── ws.py                # WebSocket 핸들러
│   ├── schemas.py           # 데이터 스키마
│   ├── memory/              # 메모리 시스템
│   │   ├── db.py           # 데이터베이스 모델
│   │   ├── atoms.py        # 원자 단위 기록
│   │   ├── episodes.py     # 대화 에피소드
│   │   ├── daily.py        # 일일 컨텍스트
│   │   ├── semantic.py     # 시맨틱 메모리
│   │   ├── ledger.py       # 영향력 원장
│   │   └── search_api.py   # 검색 API
│   ├── vector_store/        # 벡터 검색 엔진
│   │   ├── base.py         # 기본 인터페이스
│   │   ├── qdrant_store.py # Qdrant 구현
│   │   ├── faiss_store.py  # FAISS 구현
│   │   ├── embeddings.py   # 임베딩 클라이언트
│   │   ├── hybrid.py       # 하이브리드 검색
│   │   └── selectors.py    # 필터링/선택
│   ├── planner/             # B/I/T/E 플래너
│   │   └── plan.py         # 전술 계획 수립
│   ├── realizer/            # 텍스트 생성
│   │   └── generate.py     # 최종 응답 생성
│   ├── pipeline/            # 파이프라인 훅
│   │   └── hooks.py        # 벡터 검색 통합
│   ├── background/          # 백그라운드 작업
│   │   ├── queue.py        # 작업 큐 관리
│   │   └── vector_jobs.py  # 벡터 작업
│   ├── model_clients/       # LLM 클라이언트
│   │   └── openai_compat.py
│   └── config/              # 설정 로더
│       └── loader.py
├── config/                  # 시스템 설정
│   ├── models/              # 모델 엔드포인트
│   │   └── endpoints.yml
│   ├── prompts/             # 시스템 프롬프트
│   │   ├── core.persona.ko.yml
│   │   ├── runtime.rules.yml
│   │   ├── env.constraints.yml
│   │   ├── planner.bite.yml
│   │   └── memory.io.yml
│   ├── ab/                  # A/B 테스트
│   │   └── experiments.yml
│   └── vector.yml           # 벡터 검색 설정
├── data/                    # 벡터 데이터
└── logs/                    # 애플리케이션 로그
```

## 핵심 컴포넌트

### 메모리 시스템

- **Atoms**: 원자 단위 대화 기록 (사용자/에이전트 발화)
- **Episodes**: 대화 세션 그룹화
- **DailyContext**: 일일 컨텍스트 요약
- **Semantic**: 키-값 시맨틱 저장소
- **Ledger**: 전술 사용 추적 및 효과성 측정

### B/I/T/E 전술 시스템

- **B (Behavior)**: 
- **I (Information)**: 
- **T (Thought)**: 
- **E (Emotional)**: 

### 벡터 검색

- **Qdrant**: 운영 환경 권장 벡터 데이터베이스
- **FAISS**: 로컬 개발용 백오프
- **하이브리드 검색**: 시맨틱 + 키워드 조합
- **스코프 필터링**: 세션별, 기간별 검색 범위 제한

### 모델 지원

- **OpenAI**: GPT-4o, GPT-4o-mini
- **LM Studio**: 로컬 LLM 호스팅
- **Hot-swap**: 런타임 모델 전환

## 설치 및 실행

### 요구사항

- Python 3.11+
- Node.js 20+
- MySQL 8.0+ (옵션: Docker)
- Qdrant (옵션: Docker)

### 백엔드 설정

```bash
# 가상환경 생성
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 의존성 설치
pip install -r server/requirements.txt

# 환경변수 설정
cp .env.example .env
# OPENAI_API_KEY, MYSQL_* 설정

# 데이터베이스 초기화
python -c "from server.memory.db import init_db; import asyncio; asyncio.run(init_db())"

# 서버 실행
uvicorn server.main:app --host 127.0.0.1 --port 8787 --reload
```

### 프론트엔드 설정

```bash
# Electron 디렉토리 이동
cd app/electron

# 패키지 설치
npm install

# 개발 모드 실행
npm run dev
```

### 일괄 실행

```bash
# macOS/Linux
chmod +x start.sh && ./start.sh

# Windows
start.bat
```

## 설정 관리

### 파이프라인 모드 전환

`config/models/endpoints.yml`:
```yaml
pipeline:
  mode: two_call  # one_call | two_call
```

### 모델 공급자 변경

```yaml
default: openai  # openai | lmstudio
```

### 벡터 검색 설정

`config/vector.yml`:
```yaml
backend: qdrant  # qdrant | faiss
pipeline:
  preplanner_enabled: true
  search_scope_days: 14
  same_session_only: true
```

## API 엔드포인트

### HTTP API

- `GET /` - 서버 상태 확인
- `GET /healthz` - 헬스체크  
- `GET /v1/config` - 시스템 설정 조회
- `POST /v1/memory/search` - 벡터 메모리 검색
- `GET /v1/memory/stats` - 벡터 스토어 통계

### WebSocket API

#### 클라이언트 → 서버

```json
{"type": "open_session", "session_id": "uuid"}
{"type": "user_message", "session_id": "uuid", "message_id": "u-001", "text": "message"}
```

#### 서버 → 클라이언트

```json
{"type": "final_text", "message_id": "a-001", "text": "response"}
{"type": "meta", "used_ops": ["E.affect_match", "T.yes_and"]}
{"type": "eot"}
```

## 개발 가이드

### 새로운 전술 추가

1. `server/planner/plan.py`에서 `_get_bite_catalog()` 수정
2. 프롬프트 `config/prompts/planner.bite.yml` 업데이트
3. 테스트 케이스 추가

### 벡터 스토어 확장

1. `server/vector_store/base.py` 인터페이스 구현
2. `server/main.py`에서 백엔드 등록
3. 설정 파일에 백엔드 추가

### 메모리 스키마 확장

1. `server/memory/db.py`에서 모델 수정
2. 마이그레이션 스크립트 작성
3. 관련 메모리 모듈 업데이트

## 모니터링 및 로깅

- 로그 파일: `logs/emoai_YYYY-MM-DD.log`
- 로그 레벨: 환경변수 `LOG_LEVEL` (DEBUG/INFO/WARNING/ERROR)
- 로그 순환: 일일 순환, 7일 보관
- 메트릭: 플래너 전술 사용량, 벡터 검색 성능

## 문제 해결

### 포트 충돌

환경변수 `SERVER_PORT` (기본: 8787) 또는 `vite.config.ts` 포트 변경

### MySQL 연결 실패

1. MySQL 서비스 상태 확인
2. 환경변수 `MYSQL_*` 설정 검증  
3. 데이터베이스/사용자 권한 확인

### 벡터 검색 비활성화

`config/vector.yml`에서 `pipeline.preplanner_enabled: false`

### LM Studio 연결 오류

1. LM Studio 서버 모드 활성화 확인
2. `config/models/endpoints.yml`의 `base_url` 검증
3. 모델 로드 상태 확인