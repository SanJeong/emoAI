"""영향력 원장 관리"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlmodel import select
from loguru import logger
import json

from .db import AsyncSession, Ledger


class LedgerMemory:
    """영향력 원장 관리자"""
    
    @staticmethod
    async def log(
        session: AsyncSession,
        session_id: str,
        operators: List[str],
        user_reaction: Optional[Dict[str, Any]] = None,
        reward_proxy: float = 0.0
    ) -> Ledger:
        """원장 기록"""
        entry = Ledger(
            session_id=session_id,
            operators=json.dumps(operators),
            user_reaction=json.dumps(user_reaction) if user_reaction else None,
            reward_proxy=reward_proxy
        )
        
        session.add(entry)
        await session.commit()
        await session.refresh(entry)
        
        logger.debug(f"원장 기록: {entry.id} - ops: {operators}")
        return entry
        
    @staticmethod
    async def get_by_session(
        session: AsyncSession,
        session_id: str,
        limit: int = 50
    ) -> List[Ledger]:
        """세션별 원장 조회"""
        result = await session.execute(
            select(Ledger)
            .where(Ledger.session_id == session_id)
            .order_by(Ledger.ts.desc())
            .limit(limit)
        )
        entries = result.scalars().all()
        return list(entries)
        
    @staticmethod
    async def get_recent(
        session: AsyncSession,
        limit: int = 20
    ) -> List[Ledger]:
        """최근 원장 조회"""
        result = await session.execute(
            select(Ledger)
            .order_by(Ledger.ts.desc())
            .limit(limit)
        )
        entries = result.scalars().all()
        return list(entries)
