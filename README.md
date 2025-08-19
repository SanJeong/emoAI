# EmoAI - 텍스트 대화형 감정 에이전트

Electron(프론트엔드) + FastAPI(백엔드) 기반의 텍스트 대화형 감정 에이전트 MVP

## 🚀 주요 특징

- **듀얼 파이프라인**: 2-콜(Planner → Realizer) 또는 1-콜 모드 전환 가능
- **자연스러운 대화**: 상담사/시스템 말투가 아닌 사람 대 사람 톤
- **메모리 시스템**: Atoms/Events/Episodes/DailyContext/Semantic/Ledger 구조
- **벡터 검색**: Qdrant/FAISS 기반 의미 검색 및 컨텍스트 보강
- **타이핑 효과**: 프론트엔드에서 자연스러운 타자 효과 구현
- **모델 전환**: OpenAI ↔ LMStudio 즉시 전환 가능
- **설정 관리**: YAML 기반 Hot-swap 가능한 설정

## 📁 프로젝트 구조

```
emoai/
├── app/
│   └── electron/        # Electron + React 프론트엔드
│       ├── main.ts      # Electron 메인 프로세스
│       ├── renderer/    # React 앱
│       │   ├── components/
│       │   ├── services/
│       │   └── store/
│       └── package.json
├── server/              # FastAPI 백엔드
│   ├── main.py         # FastAPI 앱
│   ├── ws.py           # WebSocket 핸들러
│   ├── memory/         # 메모리 관리
│   ├── vector_store/   # 벡터 검색 (Qdrant/FAISS)
│   ├── planner/        # B/I/T/E 플래너
│   ├── realizer/       # 텍스트 생성
│   ├── pipeline/       # 파이프라인 훅
│   ├── background/     # 백그라운드 작업 처리
│   ├── model_clients/  # 모델 클라이언트
│   └── requirements.txt
├── config/             # 설정 파일
│   ├── models/         # 모델 엔드포인트
│   ├── prompts/        # 시스템 프롬프트
│   └── ab/            # A/B 테스트
├── data/               # 벡터 데이터 저장소
└── logs/               # 애플리케이션 로그
```

## 🛠 설치 및 실행

### 사전 요구사항

- Python 3.11+
- Node.js 20+ (⚠️ 중요: Node 18 이상 필수, Vite 5 요구사항)
- npm 또는 yarn

### 1. 환경 설정

```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 편집하여 OpenAI API 키 설정
# OPENAI_API_KEY=your_api_key_here
```

### 2. 백엔드 실행

```bash
# Python 가상환경 생성
python -m venv .venv

# 가상환경 활성화 (macOS/Linux)
source .venv/bin/activate

# 가상환경 활성화 (Windows)
# .venv\Scripts\activate

# 패키지 설치
pip install -r server/requirements.txt

# 서버 실행
uvicorn server.main:app --host 127.0.0.1 --port 8787 --reload
```

백엔드가 http://127.0.0.1:8787 에서 실행됩니다.

### 3. 프론트엔드 실행

새 터미널에서:

```bash
# Electron 디렉토리로 이동
cd app/electron

# 패키지 설치
npm install

# 개발 모드 실행
npm run dev
```

Electron 앱이 자동으로 실행되며, http://localhost:5173 의 개발 서버를 로드합니다.
ls
## ⚙️ 설정 변경

### 모델 전환 (OpenAI ↔ LMStudio)

`config/models/endpoints.yml` 파일 수정:

```yaml
default: lmstudio  # openai 또는 lmstudio
```

### 파이프라인 모드 변경

```yaml
pipeline:
  mode: one_call  # two_call 또는 one_call
```

### 프롬프트 수정

`config/prompts/` 디렉토리의 YAML 파일들을 수정하여 시스템 프롬프트 변경 가능:

- `core.persona.ko.yml`: 기본 페르소나
- `runtime.rules.yml`: 런타임 규칙
- `env.constraints.yml`: 환경 제약
- `planner.bite.yml`: 플래너 프롬프트
- `memory.io.yml`: 메모리 I/O 형식

## 🔧 개발 가이드

### 백엔드 API 엔드포인트

- `GET /`: 루트 상태 확인
- `GET /healthz`: 헬스 체크
- `GET /v1/config`: 설정 조회 (API 키 마스킹)
- `POST /v1/memory/search`: 벡터 기반 메모리 검색
- `GET /v1/memory/stats`: 벡터 스토어 통계
- `WS /ws/chat`: WebSocket 채팅

### WebSocket 프로토콜

**클라이언트 → 서버:**
```json
{"type": "open_session", "session_id": "abc"}
{"type": "user_message", "session_id": "abc", "message_id": "u-001", "text": "안녕"}
```

**서버 → 클라이언트:**
```json
{"type": "final_text", "message_id": "a-001", "text": "응답 텍스트"}
{"type": "meta", "used_ops": ["E.tentative_label"]}
{"type": "eot"}
```

### 메모리 스키마

- **Atoms**: 원자 단위 대화 기록
- **Events**: 이벤트 로그
- **Episodes**: 대화 에피소드
- **DailyContext**: 일일 컨텍스트
- **Semantic**: 시맨틱 메모리
- **Ledger**: 영향력 원장

## 🚀 빠른 시작

### macOS/Linux
```bash
# 실행 권한 부여 (최초 1회)
chmod +x start.sh

# 실행
./start.sh
```

### Windows
```cmd
start.bat
```

## ✅ 실행 확인

- **백엔드 상태**: http://127.0.0.1:8787/
  - 정상 응답: `{"name":"EmoAI Backend","version":"0.1.0","status":"running"}`
- **프론트엔드**: Electron 앱이 자동으로 실행됨
- **WebSocket 연결**: 새 대화 시작 시 자동 연결

## 🔍 벡터 검색 설정

### Qdrant 사용 (권장)

1. Qdrant 실행:
```bash
docker run -p 6333:6333 qdrant/qdrant
```

2. `config/vector.yml`에서 backend를 `qdrant`로 설정

### FAISS 사용 (로컬 폴백)

`config/vector.yml`에서 backend를 `faiss`로 설정하면 자동으로 로컬 인덱스 사용

### 벡터 검색 비활성화

`config/vector.yml`의 `pipeline.preplanner_enabled`를 `false`로 설정

## 🐛 문제 해결

### 포트 충돌

기본 포트가 사용 중인 경우:
- 백엔드: `.env`의 `SERVER_PORT` 변경
- 프론트엔드: `vite.config.ts`의 `server.port` 변경

### LMStudio 연결 실패

1. LMStudio가 실행 중인지 확인
2. 서버 모드가 활성화되어 있는지 확인
3. `config/models/endpoints.yml`의 `base_url` 확인

### 타이핑 효과 문제

구형 브라우저에서 `Intl.Segmenter`를 지원하지 않는 경우, `grapheme-splitter` 폴백이 자동으로 사용됩니다.

### Node.js 버전 오류

Vite 5는 Node.js 18 이상이 필요합니다. 버전 확인:
```bash
node --version  # v18.0.0 이상이어야 함
```

### Python 패키지 오류

SQLAlchemy async 사용을 위해 greenlet이 필요합니다:
```bash
pip install greenlet
```

## 📝 라이선스

MIT License

## 🤝 기여

이슈 및 PR을 환영합니다!
