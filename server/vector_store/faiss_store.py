"""FAISS 벡터 스토어 구현 (Fallback)"""
from typing import Dict, Any, List, Optional
import numpy as np
import faiss
import json
import os
from pathlib import Path
from loguru import logger
import pickle


class FaissStore:
    """FAISS 벡터 스토어 (로컬 폴백)"""
    
    def __init__(self, config: Dict[str, Any]):
        self.index_path = Path(config.get("index_path", "~/.murmur/faiss.index")).expanduser()
        self.meta_path = self.index_path.with_suffix('.meta')
        self.dim = config.get("dim", 1536)
        
        # 인덱스와 메타데이터
        self.index = None
        self.metadata = {}  # id -> payload 매핑
        self.id_to_idx = {}  # string id -> faiss index 매핑
        self.idx_to_id = {}  # faiss index -> string id 매핑
        self.next_idx = 0
        
        # 디렉토리 생성
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        
    async def ensure(self) -> None:
        """인덱스 확인 및 생성/로드"""
        try:
            if self.index_path.exists() and self.meta_path.exists():
                # 기존 인덱스 로드
                self.index = faiss.read_index(str(self.index_path))
                
                with open(self.meta_path, 'rb') as f:
                    saved_data = pickle.load(f)
                    self.metadata = saved_data['metadata']
                    self.id_to_idx = saved_data['id_to_idx']
                    self.idx_to_id = saved_data['idx_to_id']
                    self.next_idx = saved_data['next_idx']
                    
                logger.info(f"FAISS 인덱스 로드: {len(self.metadata)}개 벡터")
            else:
                # 새 인덱스 생성
                self.index = faiss.IndexFlatIP(self.dim)  # Inner Product (코사인 유사도용)
                logger.info(f"FAISS 인덱스 생성: dim={self.dim}")
                
        except Exception as e:
            logger.error(f"FAISS 인덱스 초기화 실패: {e}")
            # 새로 생성
            self.index = faiss.IndexFlatIP(self.dim)
            
    async def save(self) -> None:
        """인덱스와 메타데이터 저장"""
        try:
            faiss.write_index(self.index, str(self.index_path))
            
            with open(self.meta_path, 'wb') as f:
                pickle.dump({
                    'metadata': self.metadata,
                    'id_to_idx': self.id_to_idx,
                    'idx_to_id': self.idx_to_id,
                    'next_idx': self.next_idx
                }, f)
                
            logger.debug("FAISS 인덱스 저장 완료")
            
        except Exception as e:
            logger.error(f"FAISS 인덱스 저장 실패: {e}")
            
    async def upsert(
        self, 
        vid: str, 
        vector: np.ndarray, 
        payload: Dict[str, Any]
    ) -> None:
        """벡터 업서트"""
        try:
            # 정규화 (코사인 유사도를 위해)
            norm = np.linalg.norm(vector)
            if norm > 0:
                vector = vector / norm
                
            # 기존 벡터 확인
            if vid in self.id_to_idx:
                # 업데이트는 삭제 후 재삽입
                await self.delete(vid)
                
            # 새 벡터 추가
            idx = self.next_idx
            self.next_idx += 1
            
            self.index.add(vector.reshape(1, -1))
            self.metadata[vid] = payload
            self.id_to_idx[vid] = idx
            self.idx_to_id[idx] = vid
            
            # 주기적 저장 (100개마다)
            if self.next_idx % 100 == 0:
                await self.save()
                
            logger.debug(f"FAISS 벡터 업서트: {vid}")
            
        except Exception as e:
            logger.error(f"FAISS 업서트 실패 {vid}: {e}")
            
    async def delete(self, vid: str) -> bool:
        """벡터 삭제 (메타데이터만 제거, 인덱스는 유지)"""
        try:
            if vid in self.id_to_idx:
                idx = self.id_to_idx[vid]
                del self.metadata[vid]
                del self.id_to_idx[vid]
                del self.idx_to_id[idx]
                
                logger.debug(f"FAISS 벡터 삭제: {vid}")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"FAISS 삭제 실패 {vid}: {e}")
            return False
            
    async def search(
        self, 
        vector: np.ndarray, 
        k: int = 5,
        flt: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """벡터 검색"""
        try:
            # 정규화
            norm = np.linalg.norm(vector)
            if norm > 0:
                vector = vector / norm
                
            # 검색 (더 많이 가져와서 필터링)
            search_k = min(k * 3, self.index.ntotal)
            if search_k == 0:
                return []
                
            distances, indices = self.index.search(vector.reshape(1, -1), search_k)
            
            # 결과 필터링
            hits = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx < 0:  # FAISS가 반환한 무효 인덱스
                    continue
                    
                if idx not in self.idx_to_id:
                    continue
                    
                vid = self.idx_to_id[idx]
                if vid not in self.metadata:
                    continue
                    
                payload = self.metadata[vid]
                
                # 필터 적용
                if flt:
                    if "kind" in flt and payload.get("kind") != flt["kind"]:
                        continue
                    if "session_id" in flt and payload.get("session_id") != flt["session_id"]:
                        continue
                    if "day_gte" in flt and payload.get("day", "") < flt["day_gte"]:
                        continue
                        
                hits.append({
                    "id": vid,
                    "score": float(dist),  # Inner Product 점수
                    "payload": payload
                })
                
                if len(hits) >= k:
                    break
                    
            logger.debug(f"FAISS 검색 완료: {len(hits)}개 결과")
            return hits
            
        except Exception as e:
            logger.error(f"FAISS 검색 실패: {e}")
            return []
