"""벡터 스토어 베이스 프로토콜"""
from typing import Protocol, Any, Dict, List, Optional
import numpy as np


class VectorStore(Protocol):
    """벡터 스토어 인터페이스"""
    
    async def ensure(self) -> None:
        """컬렉션/인덱스 확인 및 생성"""
        ...
        
    async def upsert(
        self, 
        vid: str, 
        vector: np.ndarray, 
        payload: Dict[str, Any]
    ) -> None:
        """벡터 업서트 (삽입/업데이트)"""
        ...
        
    async def delete(self, vid: str) -> bool:
        """벡터 삭제"""
        ...
        
    async def search(
        self, 
        vector: np.ndarray, 
        k: int = 5,
        flt: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """벡터 검색
        
        Returns:
            List of {"id": str, "score": float, "payload": dict}
        """
        ...
