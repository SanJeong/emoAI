"""시맨틱 메모리 관리"""
from typing import Optional, Dict, Any
from datetime import datetime
from sqlmodel import select
from loguru import logger
import json

from .db import AsyncSession, Semantic


class SemanticMemory:
    """시맨틱 메모리 관리자"""
    
    @staticmethod
    async def set(
        session: AsyncSession,
        key: str,
        value: Dict[str, Any]
    ) -> Semantic:
        """시맨틱 메모리 설정"""
        
        # 기존 항목 확인
        result = await session.execute(
            select(Semantic).where(Semantic.key == key)
        )
        semantic = result.scalar_one_or_none()
        
        if semantic:
            # 업데이트
            semantic.value = json.dumps(value)
            semantic.updated_at = datetime.utcnow()
        else:
            # 새로 생성
            semantic = Semantic(
                key=key,
                value=json.dumps(value)
            )
            session.add(semantic)
            
        await session.commit()
        await session.refresh(semantic)
        
        logger.debug(f"시맨틱 메모리 설정: {key}")
        return semantic
        
    @staticmethod
    async def get(
        session: AsyncSession,
        key: str
    ) -> Optional[Dict[str, Any]]:
        """시맨틱 메모리 조회"""
        result = await session.execute(
            select(Semantic).where(Semantic.key == key)
        )
        semantic = result.scalar_one_or_none()
        
        if semantic and semantic.value:
            return json.loads(semantic.value)
        return None
        
    @staticmethod
    async def delete(
        session: AsyncSession,
        key: str
    ) -> bool:
        """시맨틱 메모리 삭제"""
        result = await session.execute(
            select(Semantic).where(Semantic.key == key)
        )
        semantic = result.scalar_one_or_none()
        
        if semantic:
            await session.delete(semantic)
            await session.commit()
            logger.debug(f"시맨틱 메모리 삭제: {key}")
            return True
            
        return False
