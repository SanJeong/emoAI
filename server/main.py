"""FastAPI 메인 애플리케이션"""
import os
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from dotenv import load_dotenv

from .ws import ws_manager
from .memory.db import init_db
from .background.queue import background_queue
from .config.loader import config_loader
from .memory.search_api import router as memory_router


# 환경변수 로드
load_dotenv()

# 로깅 설정
logger.add(
    "logs/emoai_{time}.log",
    rotation="1 day",
    retention="7 days",
    level=os.getenv("LOG_LEVEL", "INFO")
)

# 전역 벡터 스토어 인스턴스
vector_store = None
embedding_client = None
vector_config = None
vector_jobs = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 생명주기 관리"""
    # 시작
    logger.info("EmoAI 서버 시작...")
    
    # DB 초기화
    await init_db()
    logger.info("데이터베이스 초기화 완료")
    
    # 백그라운드 큐 시작
    await background_queue.start()
    logger.info("백그라운드 큐 시작 완료")
    
    # 설정 로드
    config_loader.reload()
    logger.info("설정 파일 로드 완료")
    
    # 벡터 스토어 초기화
    await init_vector_store()
    
    yield
    
    # 종료
    logger.info("EmoAI 서버 종료...")
    await background_queue.stop()
    
    # 벡터 스토어 정리
    if embedding_client:
        await embedding_client.close()
    if hasattr(vector_store, 'save'):
        await vector_store.save()
    

# FastAPI 앱 생성
app = FastAPI(
    title="EmoAI Backend",
    description="텍스트 대화형 감정 에이전트 백엔드",
    version="0.1.0",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 추가
app.include_router(memory_router)


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "name": "EmoAI Backend",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/healthz")
async def health_check():
    """헬스 체크"""
    return {"status": "healthy"}


@app.get("/v1/config")
async def get_config():
    """설정 조회 (마스킹)"""
    model_config = config_loader.get_model_config()
    
    # API 키 마스킹
    masked_config = {**model_config}
    if "api_key" in masked_config:
        key = masked_config["api_key"]
        if key and len(key) > 8:
            masked_config["api_key"] = key[:4] + "****" + key[-4:]
        else:
            masked_config["api_key"] = "****"
            
    return {
        "pipeline_mode": config_loader.get_pipeline_mode(),
        "model_provider": config_loader._cache.get("models", {}).get("default"),
        "model_config": masked_config
    }


async def init_vector_store():
    """벡터 스토어 초기화"""
    global vector_store, embedding_client, vector_config, vector_jobs
    
    try:
        # 벡터 설정 로드
        vector_config_path = Path("config/vector.yml")
        if not vector_config_path.exists():
            logger.warning("벡터 설정 파일 없음, 벡터 스토어 비활성화")
            return
            
        import yaml
        with open(vector_config_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # 환경변수 치환
        import re
        def replace_env(match):
            var_name = match.group(1)
            default = match.group(3) if match.lastindex >= 3 else ""
            value = os.getenv(var_name, default)
            return value
            
        content = re.sub(r'\$\{([^:}]+)(:-(.*?))?\}', replace_env, content)
        vector_config = yaml.safe_load(content)
        
        # 임베딩 클라이언트 생성
        from .vector_store.embeddings import EmbeddingClient
        embedding_config = vector_config.get("embeddings", {})
        embedding_config["dim"] = embedding_config.get("dim", 1536)
        embedding_client = EmbeddingClient(embedding_config)
        
        # 벡터 스토어 생성
        backend = vector_config.get("backend", "qdrant")
        
        if backend == "qdrant":
            from .vector_store.qdrant_store import QdrantStore
            qdrant_config = vector_config.get("qdrant", {})
            qdrant_config["dim"] = embedding_config["dim"]
            vector_store = QdrantStore(qdrant_config)
        else:  # faiss
            from .vector_store.faiss_store import FaissStore
            faiss_config = vector_config.get("faiss", {})
            faiss_config["dim"] = embedding_config["dim"]
            vector_store = FaissStore(faiss_config)
            
        # 컬렉션/인덱스 확인
        await vector_store.ensure()
        
        # 벡터 작업 헬퍼
        from .background.vector_jobs import VectorJobs
        vector_jobs = VectorJobs(vector_store, embedding_client)
        
        logger.info(f"벡터 스토어 초기화 완료: {backend}")
        
    except Exception as e:
        logger.error(f"벡터 스토어 초기화 실패: {e}")
        vector_store = None
        embedding_client = None


@app.websocket("/ws/chat")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str = None
):
    """WebSocket 채팅 엔드포인트"""
    
    # 세션 ID 생성
    if not session_id:
        import uuid
        session_id = str(uuid.uuid4())
        
    # 연결 수락
    session = await ws_manager.connect(websocket, session_id)
    
    try:
        while True:
            # 메시지 수신
            data = await websocket.receive_json()
            
            # 메시지 처리
            await session.handle_message(data)
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket 연결 끊김: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket 오류: {e}")
    finally:
        await ws_manager.disconnect(session_id)


if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("SERVER_PORT", 8787))
    
    uvicorn.run(
        "server.main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
