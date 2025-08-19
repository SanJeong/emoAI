"""일일 컨텍스트 관리"""
from typing import Optional, Dict, Any, List
from datetime import date
from sqlmodel import select
from loguru import logger
import json

from .db import AsyncSession, DailyContext


class DailyMemory:
    """일일 컨텍스트 메모리 관리자"""
    
    # 캐시 (메모리 내)
    _cache: Dict[str, DailyContext] = {}
    
    @classmethod
    async def get_or_create(
        cls,
        session: AsyncSession,
        day: str,
        session_id: str
    ) -> DailyContext:
        """일일 컨텍스트 조회 또는 생성"""
        
        # 캐시 확인
        if day in cls._cache:
            return cls._cache[day]
            
        # DB 조회
        result = await session.execute(
            select(DailyContext).where(DailyContext.day == day)
        )
        context = result.scalar_one_or_none()
        
        if not context:
            # 새로 생성
            context = DailyContext(
                day=day,
                session_id=session_id,
                rolling_summary="",
                highlights=json.dumps([]),
                pinned_facts=json.dumps({}),
                style_snapshot=json.dumps({})
            )
            session.add(context)
            await session.commit()
            await session.refresh(context)
            logger.info(f"일일 컨텍스트 생성: {day}")
            
        # 캐시 저장
        cls._cache[day] = context
        return context
        
    @staticmethod
    async def update(
        session: AsyncSession,
        day: str,
        rolling_summary: Optional[str] = None,
        highlights: Optional[List[str]] = None,
        pinned_facts: Optional[Dict[str, Any]] = None,
        style_snapshot: Optional[Dict[str, Any]] = None
    ) -> DailyContext:
        """일일 컨텍스트 업데이트"""
        
        result = await session.execute(
            select(DailyContext).where(DailyContext.day == day)
        )
        context = result.scalar_one_or_none()
        
        if not context:
            logger.error(f"일일 컨텍스트 없음: {day}")
            raise ValueError(f"DailyContext not found for day: {day}")
            
        if rolling_summary is not None:
            context.rolling_summary = rolling_summary
            
        if highlights is not None:
            context.highlights = json.dumps(highlights)
            
        if pinned_facts is not None:
            context.pinned_facts = json.dumps(pinned_facts)
            
        if style_snapshot is not None:
            context.style_snapshot = json.dumps(style_snapshot)
            
        await session.commit()
        await session.refresh(context)
        
        # 캐시 업데이트
        if day in DailyMemory._cache:
            DailyMemory._cache[day] = context
            
        logger.debug(f"일일 컨텍스트 업데이트: {day}")
        return context
        
    @staticmethod
    def parse_context(context: DailyContext) -> Dict[str, Any]:
        """DailyContext를 딕셔너리로 파싱"""
        return {
            "day": context.day,
            "session_id": context.session_id,
            "rolling_summary": context.rolling_summary or "",
            "highlights": json.loads(context.highlights or "[]"),
            "pinned_facts": json.loads(context.pinned_facts or "{}"),
            "style_snapshot": json.loads(context.style_snapshot or "{}")
        }
