"""Qdrant 벡터 스토어 구현"""
from typing import Dict, Any, List, Optional
import numpy as np
from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue,
    SearchRequest
)
import uuid


class QdrantStore:
    """Qdrant 벡터 스토어"""
    
    def __init__(self, config: Dict[str, Any]):
        self.url = config.get("url", "http://127.0.0.1:6333")
        self.api_key = config.get("api_key", None)
        self.collection_name = config.get("collection", "memory_v1")
        self.distance = config.get("distance", "cosine")
        self.dim = config.get("dim", 1536)
        
        # Qdrant 클라이언트
        self.client = QdrantClient(
            url=self.url,
            api_key=self.api_key if self.api_key else None,
            timeout=30
        )
        
    async def ensure(self) -> None:
        """컬렉션 확인 및 생성"""
        try:
            # 컬렉션 존재 확인
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            
            if not exists:
                # 컬렉션 생성
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.dim,
                        distance=Distance.COSINE if self.distance == "cosine" else Distance.EUCLID
                    )
                )
                logger.info(f"Qdrant 컬렉션 생성: {self.collection_name}")
            else:
                logger.info(f"Qdrant 컬렉션 존재: {self.collection_name}")
                
        except Exception as e:
            logger.error(f"Qdrant 컬렉션 확인 실패: {e}")
            raise
            
    async def upsert(
        self, 
        vid: str, 
        vector: np.ndarray, 
        payload: Dict[str, Any]
    ) -> None:
        """벡터 업서트"""
        try:
            point = PointStruct(
                id=vid,
                vector=vector.tolist(),
                payload=payload
            )
            
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            logger.debug(f"벡터 업서트: {vid} (kind={payload.get('kind')})")
            
        except Exception as e:
            logger.error(f"벡터 업서트 실패 {vid}: {e}")
            raise
            
    async def delete(self, vid: str) -> bool:
        """벡터 삭제"""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=[vid]
            )
            logger.debug(f"벡터 삭제: {vid}")
            return True
            
        except Exception as e:
            logger.error(f"벡터 삭제 실패 {vid}: {e}")
            return False
            
    async def search(
        self, 
        vector: np.ndarray, 
        k: int = 5,
        flt: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """벡터 검색"""
        try:
            # 필터 구성
            query_filter = None
            if flt:
                conditions = []
                
                # kind 필터
                if "kind" in flt:
                    conditions.append(
                        FieldCondition(
                            key="kind",
                            match=MatchValue(value=flt["kind"])
                        )
                    )
                    
                # session_id 필터
                if "session_id" in flt:
                    conditions.append(
                        FieldCondition(
                            key="session_id",
                            match=MatchValue(value=flt["session_id"])
                        )
                    )
                    
                # day 범위 필터
                if "day_gte" in flt:
                    conditions.append(
                        FieldCondition(
                            key="day",
                            range={"gte": flt["day_gte"]}
                        )
                    )
                    
                if conditions:
                    query_filter = Filter(must=conditions)
                    
            # 검색 실행
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=vector.tolist(),
                limit=k,
                query_filter=query_filter
            )
            
            # 결과 변환
            hits = []
            for hit in results:
                hits.append({
                    "id": hit.id,
                    "score": hit.score,
                    "payload": hit.payload
                })
                
            logger.debug(f"벡터 검색 완료: {len(hits)}개 결과")
            return hits
            
        except Exception as e:
            logger.error(f"벡터 검색 실패: {e}")
            return []
