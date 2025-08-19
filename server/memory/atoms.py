"""Atom 메모리 관리"""
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from sqlmodel import select
from loguru import logger
import json

from .db import AsyncSession, Atom


class AtomMemory:
    """Atom 메모리 관리자"""
    
    @staticmethod
    async def create(
        session: AsyncSession,
        day: str,
        author: str,
        text_raw: str,
        text_final: Optional[str] = None,
        ctx: Optional[Dict[str, Any]] = None,
        affect: Optional[Dict[str, Any]] = None,
        style: Optional[Dict[str, Any]] = None,
        levers: Optional[Dict[str, Any]] = None,
        salience: float = 0.5,
        episode_id: Optional[int] = None
    ) -> Atom:
        """Atom 생성"""
        atom = Atom(
            day=day,
            author=author,
            text_raw=text_raw,
            text_final=text_final,
            ctx=json.dumps(ctx) if ctx else None,
            affect=json.dumps(affect) if affect else None,
            style=json.dumps(style) if style else None,
            levers=json.dumps(levers) if levers else None,
            salience=salience,
            episode_id=episode_id
        )
        
        session.add(atom)
        await session.commit()
        await session.refresh(atom)
        
        logger.debug(f"Atom 생성: {atom.id} - {author}")
        return atom
        
    @staticmethod
    async def get_by_day(
        session: AsyncSession,
        day: str,
        limit: int = 100
    ) -> List[Atom]:
        """특정 날짜의 Atom 조회"""
        result = await session.execute(
            select(Atom)
            .where(Atom.day == day)
            .order_by(Atom.ts.desc())
            .limit(limit)
        )
        atoms = result.scalars().all()
        return list(atoms)
        
    @staticmethod
    async def get_recent(
        session: AsyncSession,
        limit: int = 50
    ) -> List[Atom]:
        """최근 Atom 조회"""
        result = await session.execute(
            select(Atom)
            .order_by(Atom.ts.desc())
            .limit(limit)
        )
        atoms = result.scalars().all()
        return list(atoms)
