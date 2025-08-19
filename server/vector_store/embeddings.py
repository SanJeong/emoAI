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
        
        # HTTP 클라이언트
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            timeout=30.0
        )
        
    async def get_embedding(self, text: str) -> np.ndarray:
        """텍스트를 임베딩 벡터로 변환"""
        
        if not text or not text.strip():
            # 빈 텍스트는 제로 벡터
            return np.zeros(self.dim)
            
        try:
            if self.provider in ["openai", "openai_compatible"]:
                return await self._openai_embedding(text)
            elif self.provider == "local":
                return await self._local_embedding(text)
            else:
                logger.error(f"지원하지 않는 임베딩 프로바이더: {self.provider}")
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
        
        response = await self.client.post(
            "/embeddings",
            json=payload
        )
        response.raise_for_status()
        
        data = response.json()
        embedding = data["data"][0]["embedding"]
        
        return np.array(embedding, dtype=np.float32)
        
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
        await self.client.aclose()
