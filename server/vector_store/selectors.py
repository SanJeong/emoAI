"""필터 및 범위 선택 헬퍼"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from loguru import logger


def scope_filter(
    session_id: Optional[str] = None,
    since_days: int = 14,
    same_session_only: bool = False,
    kind: Optional[str] = None
) -> Dict[str, Any]:
    """검색 범위 필터 생성
    
    Args:
        session_id: 세션 ID
        since_days: 최근 N일
        same_session_only: 같은 세션만
        kind: 벡터 종류 (atom/episode/pin)
        
    Returns:
        필터 딕셔너리
    """
    
    flt = {}
    
    # 세션 필터
    if same_session_only and session_id:
        flt["session_id"] = session_id
        
    # 날짜 범위 필터
    if since_days > 0:
        cutoff_date = datetime.utcnow() - timedelta(days=since_days)
        flt["day_gte"] = cutoff_date.strftime("%Y-%m-%d")
        
    # 종류 필터
    if kind:
        flt["kind"] = kind
        
    return flt


def extract_snippets(
    hits: List[Dict[str, Any]],
    limit: int = 3,
    max_length: int = 200
) -> List[str]:
    """검색 결과에서 텍스트 스니펫 추출
    
    Args:
        hits: 검색 결과
        limit: 최대 개수
        max_length: 스니펫 최대 길이
        
    Returns:
        텍스트 스니펫 리스트
    """
    
    snippets = []
    
    for hit in hits[:limit]:
        payload = hit.get("payload", {})
        
        # kind별 텍스트 추출
        kind = payload.get("kind")
        text = ""
        
        if kind == "atom":
            # Atom은 원문 사용
            text = payload.get("text", "")
            
        elif kind == "episode":
            # Episode는 제목과 요약
            title = payload.get("title", "")
            summary = payload.get("summary", "")
            text = f"{title}: {summary}" if summary else title
            
        elif kind == "pin":
            # Pin은 텍스트 그대로
            text = payload.get("text", "")
            
        # 길이 제한
        if len(text) > max_length:
            text = text[:max_length] + "..."
            
        if text:
            snippets.append(text)
            
    return snippets
