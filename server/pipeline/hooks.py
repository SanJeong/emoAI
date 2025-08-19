"""파이프라인 훅 - 벡터 검색 통합"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger


async def vector_highlights_for_planner(
    user_text: str,
    session_id: str,
    vector_store,
    embedding_client,
    config: Dict[str, Any]
) -> List[str]:
    """Planner 전 벡터 하이라이트 보강
    
    사용자 입력과 유사한 과거 컨텍스트를 검색하여
    Planner에게 추가 컨텍스트로 제공
    """
    
    # 설정 확인
    if not config.get("pipeline", {}).get("preplanner_enabled", False):
        return []
        
    if not vector_store or not embedding_client:
        logger.debug("벡터 스토어 비활성화")
        return []
        
    try:
        # 쿼리 임베딩
        query_vector = await embedding_client.get_embedding(user_text)
        
        # 필터 구성
        from ..vector_store.selectors import scope_filter
        
        search_scope_days = config.get("pipeline", {}).get("search_scope_days", 14)
        same_session_only = config.get("pipeline", {}).get("same_session_only", True)
        
        flt = scope_filter(
            session_id=session_id if same_session_only else None,
            since_days=search_scope_days,
            kind="atom"  # Atom만 검색
        )
        
        # 벡터 검색
        hits = await vector_store.search(
            vector=query_vector,
            k=5,
            flt=flt
        )
        
        if not hits:
            return []
            
        # 재랭킹
        from ..vector_store.hybrid import rerank_hits
        ranking_config = config.get("ranking", {})
        hits = rerank_hits(hits, ranking_config)
        
        # 상위 3개 스니펫 추출
        from ..vector_store.selectors import extract_snippets
        snippets = extract_snippets(hits, limit=3, max_length=150)
        
        logger.info(f"Planner 하이라이트 보강: {len(snippets)}개 스니펫")
        return snippets
        
    except Exception as e:
        logger.error(f"벡터 하이라이트 추출 실패: {e}")
        return []


async def check_boundary_proximity(
    user_text: str,
    session_id: str,
    vector_store,
    embedding_client,
    threshold: float = 0.7
) -> Optional[Dict[str, Any]]:
    """경계 근접성 체크
    
    사용자 입력이 설정된 경계(boundary)와 가까운지 확인
    """
    
    if not vector_store or not embedding_client:
        return None
        
    try:
        # 쿼리 임베딩
        query_vector = await embedding_client.get_embedding(user_text)
        
        # Pin 중 boundary만 검색
        from ..vector_store.selectors import scope_filter
        
        flt = scope_filter(
            session_id=session_id,
            kind="pin"
        )
        
        # 벡터 검색
        hits = await vector_store.search(
            vector=query_vector,
            k=3,
            flt=flt
        )
        
        # boundary 타입만 필터링
        boundary_hits = [
            hit for hit in hits
            if hit.get("payload", {}).get("type") == "boundary"
            and hit.get("score", 0) >= threshold
        ]
        
        if boundary_hits:
            # 가장 가까운 경계 반환
            closest = boundary_hits[0]
            logger.warning(
                f"경계 근접 감지: {closest['payload'].get('text', '')} "
                f"(score={closest['score']:.2f})"
            )
            return closest["payload"]
            
        return None
        
    except Exception as e:
        logger.error(f"경계 체크 실패: {e}")
        return None


async def find_novelty_boost(
    user_text: str,
    session_id: str,
    recent_messages: List[str],
    vector_store,
    embedding_client,
    similarity_threshold: float = 0.85
) -> float:
    """신규성 부스트 계산
    
    최근 대화와 유사도가 높으면 novelty_boost를 낮춤
    """
    
    if not vector_store or not embedding_client:
        return 1.0
        
    try:
        # 최근 메시지들과 비교
        for recent in recent_messages[-3:]:
            if not recent:
                continue
                
            # 임베딩 생성
            recent_vec = await embedding_client.get_embedding(recent)
            query_vec = await embedding_client.get_embedding(user_text)
            
            # 코사인 유사도 계산
            import numpy as np
            similarity = np.dot(recent_vec, query_vec) / (
                np.linalg.norm(recent_vec) * np.linalg.norm(query_vec)
            )
            
            if similarity >= similarity_threshold:
                # 반복 감지
                logger.info(f"반복 패턴 감지: 유사도={similarity:.2f}")
                return 0.5  # novelty 감소
                
        return 1.0  # 정상 novelty
        
    except Exception as e:
        logger.error(f"신규성 계산 실패: {e}")
        return 1.0
