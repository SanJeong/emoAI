"""임베딩 생성 모듈"""
import numpy as np
import httpx
from typing import Dict, Any, List, Optional
from loguru import logger
import asyncio


class EmbeddingClient:
    """임베딩 클라이언트"""
    
    def __init__(self, config: Dict[str, Any]):
        self.provider = config.get("provider", "openai_compatible")
        self.base_url = config.get("base_url", "https://api.openai.com/v1")
        self.model = config.get("model", "text-embedding-3-small")
        self.api_key = config.get("api_key", "")
        self.dim = config.get("dim", 1536)
        self._client = None
        self._is_closed = False
        
    @property
    def client(self) -> httpx.AsyncClient:
        """지연 초기화된 HTTP 클라이언트"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                timeout=30.0,
                limits=httpx.Limits(
                    max_keepalive_connections=5,
                    max_connections=10,
                    keepalive_expiry=30.0
                )
            )
        return self._client
    
    async def __aenter__(self):
        """async context manager 진입"""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """async context manager 종료"""
        await self.close()
        
    async def get_embedding(self, text: str) -> np.ndarray:
        """텍스트를 임베딩 벡터로 변환"""
        
        if self._is_closed:
            logger.error("이미 종료된 클라이언트로 임베딩 요청")
            return np.zeros(self.dim)
        
        if not text or not text.strip():
            logger.warning("빈 텍스트로 임베딩 요청")
            return np.zeros(self.dim)
            
        try:
            if self.provider in ["openai", "openai_compatible"]:
                return await self._openai_embedding(text)
            elif self.provider == "local":
                return await self._local_embedding(text)
            else:
                logger.error(f"지원하지 않는 임베딩 프로바이더: {self.provider}")
                return np.zeros(self.dim)
                
        except httpx.ConnectError as e:
            logger.error(f"임베딩 서버 연결 실패: {e}")
            return np.zeros(self.dim)
        except httpx.TimeoutException as e:
            logger.error(f"임베딩 요청 타임아웃: {e}")
            return np.zeros(self.dim)
        except httpx.HTTPStatusError as e:
            logger.error(f"임베딩 HTTP 오류: {e.response.status_code} - {e.response.text}")
            return np.zeros(self.dim)
        except Exception as e:
            logger.error(f"임베딩 생성 실패: {e}")
            return np.zeros(self.dim)
            
    async def get_embeddings(self, texts: List[str]) -> List[np.ndarray]:
        """여러 텍스트를 임베딩 벡터로 변환 (배치)"""
        
        if not texts:
            return []
            
        try:
            if self.provider in ["openai", "openai_compatible"]:
                return await self._openai_embeddings(texts)
            else:
                # 개별 처리
                tasks = [self.get_embedding(text) for text in texts]
                return await asyncio.gather(*tasks)
                
        except Exception as e:
            logger.error(f"배치 임베딩 생성 실패: {e}")
            return [np.zeros(self.dim) for _ in texts]
            
    async def _openai_embedding(self, text: str) -> np.ndarray:
        """OpenAI API 호출"""
        
        payload = {
            "model": self.model,
            "input": text,
            "encoding_format": "float"
        }
        
        try:
            response = await self.client.post(
                "/embeddings",
                json=payload
            )
            response.raise_for_status()
            
            data = response.json()
            
            # 응답 구조 검증
            if "data" not in data or not data["data"]:
                logger.error("임베딩 응답에 데이터가 없음")
                return np.zeros(self.dim)
                
            if "embedding" not in data["data"][0]:
                logger.error("임베딩 응답에 embedding 필드가 없음")
                return np.zeros(self.dim)
                
            embedding = data["data"][0]["embedding"]
            
            # 차원 검증
            if len(embedding) != self.dim:
                logger.warning(f"임베딩 차원 불일치: 예상={self.dim}, 실제={len(embedding)}")
                
            return np.array(embedding, dtype=np.float32)
            
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"임베딩 응답 파싱 실패: {e}")
            return np.zeros(self.dim)
        
    async def _openai_embeddings(self, texts: List[str]) -> List[np.ndarray]:
        """OpenAI API 배치 호출"""
        
        payload = {
            "model": self.model,
            "input": texts,
            "encoding_format": "float"
        }
        
        response = await self.client.post(
            "/embeddings",
            json=payload
        )
        response.raise_for_status()
        
        data = response.json()
        embeddings = [item["embedding"] for item in data["data"]]
        
        return [np.array(emb, dtype=np.float32) for emb in embeddings]
        
    async def _local_embedding(self, text: str) -> np.ndarray:
        """로컬 모델 사용 (sentence-transformers)"""
        
        # TODO: sentence-transformers 구현
        # 현재는 더미 구현
        logger.warning("로컬 임베딩은 아직 구현되지 않음")
        return np.random.randn(self.dim).astype(np.float32)
        
    async def close(self):
        """클라이언트 종료"""
        if self._is_closed:
            return
            
        try:
            if self._client and not self._client.is_closed:
                await self._client.aclose()
                logger.debug("EmbeddingClient 종료됨")
        except Exception as e:
            logger.error(f"EmbeddingClient 종료 실패: {e}")
        finally:
            self._is_closed = True
            self._client = None
