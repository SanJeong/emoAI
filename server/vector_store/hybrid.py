"""하이브리드 재랭킹 모듈"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import math
from loguru import logger


def hybrid_score(
    hit: Dict[str, Any],
    now: datetime,
    alpha: float = 1.0,    # cosine weight
    beta: float = 0.15,    # recency weight
    gamma: float = 0.10,   # salience weight
    delta: float = 0.50,   # boundary penalty
    halflife_hours: float = 72
) -> float:
    """하이브리드 점수 계산
    
    score = α*cosine + β*recency + γ*salience - δ*boundary
    """
    
    payload = hit.get("payload", {})
    
    # 1. 코사인 유사도
    cosine = hit.get("score", 0.0)
    
    # 2. 최신성 (exponential decay)
    recency = 0.0
    if "ts" in payload:
        try:
            if isinstance(payload["ts"], str):
                ts = datetime.fromisoformat(payload["ts"].replace("Z", "+00:00"))
            else:
                ts = payload["ts"]
                
            delta_hours = (now - ts).total_seconds() / 3600
            tau = halflife_hours
            recency = math.exp(-delta_hours / tau)
        except Exception as e:
            logger.debug(f"최신성 계산 실패: {e}")
            
    # 3. 중요도
    salience = payload.get("salience", 0.5)
    
    # 4. 경계 페널티
    boundary_penalty = 1.0 if payload.get("boundary", False) else 0.0
    
    # 최종 점수
    score = (
        alpha * cosine +
        beta * recency +
        gamma * salience -
        delta * boundary_penalty
    )
    
    return score


def rerank_hits(
    hits: List[Dict[str, Any]],
    config: Dict[str, Any],
    now: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """검색 결과 재랭킹"""
    
    if not hits:
        return []
        
    if now is None:
        now = datetime.utcnow()
        
    # 설정 값
    alpha = config.get("alpha", 1.0)
    beta = config.get("beta", 0.15)
    gamma = config.get("gamma", 0.10)
    delta = config.get("delta", 0.50)
    halflife = config.get("halflife_hours", 72)
    
    # 점수 계산 및 정렬
    scored_hits = []
    for hit in hits:
        score = hybrid_score(
            hit, now, 
            alpha, beta, gamma, delta, halflife
        )
        scored_hits.append({
            **hit,
            "hybrid_score": score
        })
        
    # 점수 기준 정렬
    scored_hits.sort(key=lambda x: x["hybrid_score"], reverse=True)
    
    return scored_hits
