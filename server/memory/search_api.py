"""메모리 검색 API"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import select
from loguru import logger

from ..memory.db import AsyncSession, get_session, Atom, Episode
from ..vector_store.hybrid import rerank_hits
from ..vector_store.selectors import extract_snippets


router = APIRouter(prefix="/v1/memory", tags=["memory"])


class SearchRequest(BaseModel):
    """검색 요청"""
    query: str = Field(..., description="검색 쿼리")
    session_id: Optional[str] = Field(None, description="세션 ID")
    kind: Optional[str] = Field(None, description="종류 필터 (atom/episode/pin)")
    k: int = Field(8, description="반환할 결과 수")
    days: Optional[int] = Field(14, description="검색 범위 (일)")
    rerank: bool = Field(True, description="재랭킹 여부")
    

class SearchResult(BaseModel):
    """검색 결과"""
    id: str
    kind: str
    score: float
    text: str
    metadata: Dict[str, Any]
    

class SearchResponse(BaseModel):
    """검색 응답"""
    query: str
    results: List[SearchResult]
    count: int
    

@router.post("/search", response_model=SearchResponse)
async def search_memory(
    request: SearchRequest,
    session: AsyncSession = Depends(get_session)
) -> SearchResponse:
    """메모리 검색
    
    벡터 유사도 검색 후 하이브리드 재랭킹
    """
    
    try:
        # 벡터 스토어와 임베딩 클라이언트 가져오기
        from ..main import vector_store, embedding_client, vector_config
        
        if not vector_store or not embedding_client:
            raise HTTPException(
                status_code=503,
                detail="벡터 검색 서비스를 사용할 수 없습니다"
            )
            
        # 쿼리 임베딩
        query_vector = await embedding_client.get_embedding(request.query)
        
        # 필터 구성
        from ..vector_store.selectors import scope_filter
        flt = scope_filter(
            session_id=request.session_id,
            since_days=request.days or 14,
            same_session_only=bool(request.session_id),
            kind=request.kind
        )
        
        # 벡터 검색
        hits = await vector_store.search(
            vector=query_vector,
            k=request.k * 2,  # 재랭킹을 위해 더 많이 가져옴
            flt=flt
        )
        
        # 재랭킹
        if request.rerank and vector_config:
            ranking_config = vector_config.get("ranking", {})
            hits = rerank_hits(hits, ranking_config)
            
        # 상위 k개 선택
        hits = hits[:request.k]
        
        # 결과 구성
        results = []
        for hit in hits:
            payload = hit.get("payload", {})
            kind = payload.get("kind", "unknown")
            
            # 원본 데이터 조회 (필요시)
            metadata = await _fetch_metadata(session, kind, payload.get("id"))
            
            # 텍스트 추출
            text = payload.get("text", "")
            if kind == "episode":
                text = f"{payload.get('title', '')}: {payload.get('summary', '')}"
                
            results.append(SearchResult(
                id=payload.get("id", ""),
                kind=kind,
                score=hit.get("hybrid_score", hit.get("score", 0.0)),
                text=text,
                metadata={
                    **payload,
                    **metadata
                }
            ))
            
        return SearchResponse(
            query=request.query,
            results=results,
            count=len(results)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"메모리 검색 오류: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"검색 중 오류가 발생했습니다: {str(e)}"
        )
        

async def _fetch_metadata(
    session: AsyncSession,
    kind: str,
    item_id: str
) -> Dict[str, Any]:
    """원본 메타데이터 조회"""
    
    metadata = {}
    
    try:
        if kind == "atom" and item_id:
            # Atom ID에서 숫자 추출
            atom_id = item_id.replace("atom:", "")
            if atom_id.isdigit():
                result = await session.execute(
                    select(Atom).where(Atom.id == int(atom_id))
                )
                atom = result.scalar_one_or_none()
                if atom:
                    metadata["created_at"] = atom.ts.isoformat()
                    metadata["author"] = atom.author
                    
        elif kind == "episode" and item_id:
            # Episode ID에서 숫자 추출
            ep_id = item_id.replace("ep:", "")
            if ep_id.isdigit():
                result = await session.execute(
                    select(Episode).where(Episode.id == int(ep_id))
                )
                episode = result.scalar_one_or_none()
                if episode:
                    metadata["created_at"] = episode.time_start.isoformat()
                    if episode.time_end:
                        metadata["ended_at"] = episode.time_end.isoformat()
                        
    except Exception as e:
        logger.debug(f"메타데이터 조회 실패: {e}")
        
    return metadata


@router.get("/stats")
async def memory_stats() -> Dict[str, Any]:
    """메모리 통계"""
    
    try:
        from ..main import vector_store
        
        if not vector_store:
            return {
                "status": "unavailable",
                "message": "벡터 스토어를 사용할 수 없습니다"
            }
            
        # Qdrant의 경우 컬렉션 정보 조회
        if hasattr(vector_store, 'client'):
            try:
                info = vector_store.client.get_collection(
                    vector_store.collection_name
                )
                return {
                    "status": "available",
                    "backend": "qdrant",
                    "collection": vector_store.collection_name,
                    "vectors_count": info.vectors_count,
                    "indexed_vectors_count": info.indexed_vectors_count
                }
            except:
                pass
                
        # FAISS의 경우
        if hasattr(vector_store, 'index'):
            return {
                "status": "available",
                "backend": "faiss",
                "vectors_count": len(vector_store.metadata),
                "index_size": vector_store.index.ntotal if vector_store.index else 0
            }
            
        return {
            "status": "unknown",
            "message": "벡터 스토어 상태를 확인할 수 없습니다"
        }
        
    except Exception as e:
        logger.error(f"메모리 통계 조회 오류: {e}")
        return {
            "status": "error",
            "message": str(e)
        }
