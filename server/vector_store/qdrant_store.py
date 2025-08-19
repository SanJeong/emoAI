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
        import httpx
        from qdrant_client.http.exceptions import UnexpectedResponse
        
        try:
            # 컬렉션 존재 확인
            try:
                collections = self.client.get_collections().collections
                exists = any(c.name == self.collection_name for c in collections)
                
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                logger.error(f"Qdrant 서버 연결 실패: {e}")
                raise ConnectionError(f"Qdrant 서버에 연결할 수 없습니다: {self.url}")
                
            except UnexpectedResponse as e:
                logger.error(f"Qdrant API 응답 오류: {e}")
                if "401" in str(e) or "403" in str(e):
                    raise PermissionError("Qdrant API 키가 잘못되었습니다")
                raise
            
            if not exists:
                try:
                    # 컬렉션 생성
                    self.client.create_collection(
                        collection_name=self.collection_name,
                        vectors_config=VectorParams(
                            size=self.dim,
                            distance=Distance.COSINE if self.distance == "cosine" else Distance.EUCLID
                        )
                    )
                    logger.info(f"Qdrant 컬렉션 생성: {self.collection_name}")
                    
                except UnexpectedResponse as e:
                    if "already exists" in str(e).lower():
                        logger.info(f"Qdrant 컬렉션 이미 존재: {self.collection_name}")
                    else:
                        raise
            else:
                logger.info(f"Qdrant 컬렉션 존재: {self.collection_name}")
                
        except (ConnectionError, PermissionError):
            raise
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
        import httpx
        from qdrant_client.http.exceptions import UnexpectedResponse
        
        try:
            # 입력 검증
            if vector is None:
                logger.error(f"벡터가 None: {vid}")
                return
                
            if not isinstance(vector, np.ndarray):
                logger.error(f"벡터가 numpy 배열이 아님: {type(vector)}")
                return
                
            if vector.shape[0] != self.dim:
                logger.error(f"벡터 차원 불일치 {vid}: 예상={self.dim}, 실제={vector.shape[0]}")
                return
            
            # 벡터를 리스트로 변환 (JSON 직렬화 가능한 형태)
            try:
                vector_list = vector.tolist()
            except Exception as e:
                logger.error(f"벡터 직렬화 실패 {vid}: {e}")
                return
            
            point = PointStruct(
                id=vid,
                vector=vector_list,
                payload=payload
            )
            
            try:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=[point]
                )
                logger.debug(f"벡터 업서트: {vid} (kind={payload.get('kind')})")
                
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                logger.error(f"Qdrant 연결 실패 {vid}: {e}")
                raise ConnectionError(f"Qdrant 서버 연결 실패: {e}")
                
            except UnexpectedResponse as e:
                logger.error(f"Qdrant API 오류 {vid}: {e}")
                if "404" in str(e):
                    raise ValueError(f"컬렉션을 찾을 수 없음: {self.collection_name}")
                raise
            
        except (ConnectionError, ValueError):
            raise
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
        import httpx
        from qdrant_client.http.exceptions import UnexpectedResponse
        
        try:
            # 입력 검증
            if vector is None:
                logger.error("검색 벡터가 None입니다")
                return []
                
            if not isinstance(vector, np.ndarray):
                logger.error(f"벡터가 numpy 배열이 아님: {type(vector)}")
                return []
                
            if vector.shape[0] != self.dim:
                logger.error(f"벡터 차원 불일치: 예상={self.dim}, 실제={vector.shape[0]}")
                return []
                
            if k <= 0:
                logger.warning(f"잘못된 k 값: {k}")
                return []
                
            # 벡터 직렬화
            try:
                vector_list = vector.tolist()
            except Exception as e:
                logger.error(f"벡터 직렬화 실패: {e}")
                return []
                
            # 필터 구성
            query_filter = None
            if flt:
                try:
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
                        
                except Exception as e:
                    logger.error(f"필터 구성 실패: {e}")
                    # 필터 없이 검색 진행
                    
            # 검색 실행
            try:
                results = self.client.search(
                    collection_name=self.collection_name,
                    query_vector=vector_list,
                    limit=k,
                    query_filter=query_filter
                )
                
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                logger.error(f"Qdrant 연결 실패: {e}")
                raise ConnectionError(f"Qdrant 서버 연결 실패: {e}")
                
            except UnexpectedResponse as e:
                logger.error(f"Qdrant 검색 API 오류: {e}")
                if "404" in str(e):
                    raise ValueError(f"컬렉션을 찾을 수 없음: {self.collection_name}")
                return []
            
            # 결과 변환
            hits = []
            for hit in results:
                try:
                    hits.append({
                        "id": str(hit.id),  # ID를 문자열로 확실히 변환
                        "score": float(hit.score),  # 점수를 float로 변환
                        "payload": dict(hit.payload) if hit.payload else {}  # 페이로드를 dict로 변환
                    })
                except Exception as e:
                    logger.warning(f"검색 결과 변환 실패: {e}, hit={hit}")
                    continue
                    
            logger.debug(f"벡터 검색 완료: {len(hits)}개 결과")
            return hits
            
        except (ConnectionError, ValueError):
            raise
        except Exception as e:
            logger.error(f"벡터 검색 실패: {e}")
            return []
