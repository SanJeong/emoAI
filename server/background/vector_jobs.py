"""백그라운드 벡터 작업"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger
import json


class VectorJobs:
    """벡터 관련 백그라운드 작업"""
    
    def __init__(self, vector_store, embedding_client):
        self.vector_store = vector_store
        self.embeddings = embedding_client
        
    async def upsert_atom(self, atom: Dict[str, Any]) -> None:
        """Atom 벡터 업서트"""
        try:
            # 텍스트 추출
            if atom.get("author") == "user":
                text = atom.get("text_raw", "")
            else:  # agent
                text = atom.get("text_final") or atom.get("text_raw", "")
                
            if not text:
                return
                
            # 임베딩 생성
            vector = await self.embeddings.get_embedding(text)
            
            # 페이로드 구성
            payload = {
                "kind": "atom",
                "id": str(atom.get("id")),
                "session_id": atom.get("session_id", ""),
                "day": atom.get("day", ""),
                "ts": atom.get("ts", datetime.utcnow()).isoformat() + "Z",
                "author": atom.get("author", ""),
                "episode_id": f"ep:{atom.get('episode_id')}" if atom.get("episode_id") else None,
                "text": text[:500],  # 텍스트 미리보기 저장
                "salience": atom.get("salience", 0.5),
                "boundary": False,
                "len": len(text)
            }
            
            # 레이블/토픽 추출 (있으면)
            if atom.get("affect"):
                try:
                    affect = json.loads(atom["affect"]) if isinstance(atom["affect"], str) else atom["affect"]
                    if "labels" in affect:
                        payload["labels"] = affect["labels"]
                except:
                    pass
                    
            # 벡터 저장
            await self.vector_store.upsert(
                vid=f"atom:{atom.get('id')}",
                vector=vector,
                payload=payload
            )
            
            logger.debug(f"Atom 벡터 업서트: {atom.get('id')}")
            
        except Exception as e:
            logger.error(f"Atom 벡터 업서트 실패: {e}")
            
    async def upsert_episode(self, episode: Dict[str, Any]) -> None:
        """Episode 벡터 업서트"""
        try:
            # 제목과 요약 구성
            title = episode.get("title", "")
            summary = episode.get("summary", "")
            
            if not title and not summary:
                return
                
            text = f"{title}. {summary}" if summary else title
            
            # 임베딩 생성
            vector = await self.embeddings.get_embedding(text)
            
            # 페이로드 구성
            payload = {
                "kind": "episode",
                "id": f"ep:{episode.get('id')}",
                "session_id": episode.get("session_id", ""),
                "day": episode.get("day", ""),
                "range": [
                    episode.get("time_start", datetime.utcnow()).isoformat() + "Z",
                    episode.get("time_end", datetime.utcnow()).isoformat() + "Z"
                ],
                "title": title,
                "summary": summary[:500],
                "tone": episode.get("tone", []),
                "topics": episode.get("topics", [])
            }
            
            # 벡터 저장
            await self.vector_store.upsert(
                vid=f"ep:{episode.get('id')}",
                vector=vector,
                payload=payload
            )
            
            logger.debug(f"Episode 벡터 업서트: {episode.get('id')}")
            
        except Exception as e:
            logger.error(f"Episode 벡터 업서트 실패: {e}")
            
    async def upsert_pin(self, pin: Dict[str, Any]) -> None:
        """Pin (고정 사실/경계) 벡터 업서트"""
        try:
            text = pin.get("text", "")
            if not text:
                return
                
            # 임베딩 생성
            vector = await self.embeddings.get_embedding(text)
            
            # 페이로드 구성
            pin_type = pin.get("type", "fact")
            is_boundary = pin_type == "boundary"
            
            payload = {
                "kind": "pin",
                "id": f"pin:{pin.get('id')}",
                "session_id": pin.get("session_id", ""),
                "day": pin.get("day", datetime.utcnow().strftime("%Y-%m-%d")),
                "type": pin_type,
                "text": text,
                "priority": pin.get("priority", 0.5),
                "boundary": is_boundary
            }
            
            # 벡터 저장
            await self.vector_store.upsert(
                vid=f"pin:{pin.get('id')}",
                vector=vector,
                payload=payload
            )
            
            logger.debug(f"Pin 벡터 업서트: {pin.get('id')} ({pin_type})")
            
        except Exception as e:
            logger.error(f"Pin 벡터 업서트 실패: {e}")
            
    async def delete_vector(self, vid: str) -> bool:
        """벡터 삭제"""
        try:
            result = await self.vector_store.delete(vid)
            logger.debug(f"벡터 삭제: {vid}")
            return result
            
        except Exception as e:
            logger.error(f"벡터 삭제 실패 {vid}: {e}")
            return False
            
    async def search_similar(
        self,
        text: str,
        session_id: Optional[str] = None,
        kind: Optional[str] = None,
        k: int = 5,
        since_days: int = 14
    ) -> List[Dict[str, Any]]:
        """유사 벡터 검색"""
        try:
            from .selectors import scope_filter
            
            # 임베딩 생성
            vector = await self.embeddings.get_embedding(text)
            
            # 필터 구성
            flt = scope_filter(
                session_id=session_id,
                since_days=since_days,
                same_session_only=bool(session_id),
                kind=kind
            )
            
            # 검색
            hits = await self.vector_store.search(
                vector=vector,
                k=k,
                flt=flt
            )
            
            return hits
            
        except Exception as e:
            logger.error(f"유사 검색 실패: {e}")
            return []
