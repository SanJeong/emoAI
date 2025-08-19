"""벡터 스토어 입력 검증 유틸리티"""
import numpy as np
from typing import Dict, Any, Optional, Tuple, List
from loguru import logger


def validate_vector(
    vector: np.ndarray, 
    expected_dim: int, 
    vector_id: Optional[str] = None
) -> Tuple[bool, str]:
    """벡터 검증
    
    Args:
        vector: 검증할 벡터
        expected_dim: 예상 차원
        vector_id: 벡터 ID (로그용)
        
    Returns:
        (유효성, 에러 메시지) 튜플
    """
    
    vid_str = f" ({vector_id})" if vector_id else ""
    
    if vector is None:
        return False, f"벡터가 None{vid_str}"
        
    if not isinstance(vector, np.ndarray):
        return False, f"벡터가 numpy 배열이 아님{vid_str}: {type(vector)}"
        
    if vector.dtype not in [np.float32, np.float64]:
        logger.warning(f"벡터 타입이 float가 아님{vid_str}: {vector.dtype}")
        
    if len(vector.shape) != 1:
        return False, f"벡터가 1차원이 아님{vid_str}: {vector.shape}"
        
    if vector.shape[0] != expected_dim:
        return False, f"벡터 차원 불일치{vid_str}: 예상={expected_dim}, 실제={vector.shape[0]}"
        
    # NaN/Inf 체크
    if np.any(np.isnan(vector)):
        return False, f"벡터에 NaN 값 포함{vid_str}"
        
    if np.any(np.isinf(vector)):
        return False, f"벡터에 무한대 값 포함{vid_str}"
        
    # 제로 벡터 경고 (완전히 차단하지는 않음)
    if np.allclose(vector, 0):
        logger.warning(f"제로 벡터 감지{vid_str}")
        
    return True, ""


def validate_payload(payload: Dict[str, Any]) -> Tuple[bool, str]:
    """페이로드 검증
    
    Args:
        payload: 검증할 페이로드
        
    Returns:
        (유효성, 에러 메시지) 튜플
    """
    
    if payload is None:
        return False, "페이로드가 None"
        
    if not isinstance(payload, dict):
        return False, f"페이로드가 dict가 아님: {type(payload)}"
        
    # 필수 필드 체크 (선택적)
    required_fields = ["kind"]  # 필요에 따라 수정
    for field in required_fields:
        if field not in payload:
            logger.warning(f"페이로드에 {field} 필드 누락")
            
    # 값 검증
    for key, value in payload.items():
        # JSON 직렬화 가능성 체크
        try:
            import json
            json.dumps(value)
        except (TypeError, ValueError) as e:
            return False, f"페이로드 값이 JSON 직렬화 불가 ({key}): {e}"
            
    return True, ""


def validate_search_params(
    vector: np.ndarray,
    k: int,
    expected_dim: int,
    flt: Optional[Dict[str, Any]] = None
) -> Tuple[bool, str]:
    """검색 파라미터 검증
    
    Args:
        vector: 검색 벡터
        k: 검색 결과 개수
        expected_dim: 예상 벡터 차원
        flt: 검색 필터
        
    Returns:
        (유효성, 에러 메시지) 튜플
    """
    
    # 벡터 검증
    valid, msg = validate_vector(vector, expected_dim, "search_vector")
    if not valid:
        return False, msg
        
    # k 값 검증
    if not isinstance(k, int):
        return False, f"k가 정수가 아님: {type(k)}"
        
    if k <= 0:
        return False, f"k가 0 이하: {k}"
        
    if k > 1000:  # 합리적인 상한선
        logger.warning(f"k 값이 매우 큼: {k}")
        
    # 필터 검증
    if flt is not None:
        if not isinstance(flt, dict):
            return False, f"필터가 dict가 아님: {type(flt)}"
            
        # 알려진 필터 키 체크
        known_keys = {"kind", "session_id", "day_gte"}
        unknown_keys = set(flt.keys()) - known_keys
        if unknown_keys:
            logger.warning(f"알 수 없는 필터 키: {unknown_keys}")
            
    return True, ""


def sanitize_vector_id(vid: str) -> Tuple[bool, str]:
    """벡터 ID 검증 및 정리
    
    Args:
        vid: 벡터 ID
        
    Returns:
        (유효성, 정리된 ID 또는 에러 메시지) 튜플
    """
    
    if vid is None:
        return False, "벡터 ID가 None"
        
    if not isinstance(vid, str):
        vid = str(vid)
        
    # 공백 제거
    vid = vid.strip()
    
    if not vid:
        return False, "벡터 ID가 빈 문자열"
        
    # 길이 제한
    if len(vid) > 256:
        return False, f"벡터 ID가 너무 김: {len(vid)} 문자"
        
    # 특수 문자 체크 (필요에 따라 수정)
    import re
    if not re.match(r'^[a-zA-Z0-9_\-:.]+$', vid):
        logger.warning(f"벡터 ID에 특수 문자 포함: {vid}")
        
    return True, vid


def check_data_consistency(
    vector_count: int,
    metadata_count: int,
    index_mapping_count: int,
    tolerance: float = 0.1
) -> List[str]:
    """데이터 일관성 검사
    
    Args:
        vector_count: 벡터 개수
        metadata_count: 메타데이터 개수
        index_mapping_count: 인덱스 매핑 개수
        tolerance: 허용 오차 비율
        
    Returns:
        발견된 문제 목록
    """
    
    issues = []
    
    # 개수 일치 확인
    if vector_count != metadata_count:
        diff = abs(vector_count - metadata_count)
        if diff > vector_count * tolerance:
            issues.append(f"벡터-메타데이터 개수 불일치: 벡터={vector_count}, 메타={metadata_count}")
            
    if vector_count != index_mapping_count:
        diff = abs(vector_count - index_mapping_count)
        if diff > vector_count * tolerance:
            issues.append(f"벡터-인덱스 매핑 개수 불일치: 벡터={vector_count}, 매핑={index_mapping_count}")
            
    # 제로 개수 체크
    if vector_count == 0 and (metadata_count > 0 or index_mapping_count > 0):
        issues.append("벡터는 없지만 메타데이터나 매핑이 존재")
        
    return issues
