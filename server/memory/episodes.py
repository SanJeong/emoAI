"""에피소드 메모리 관리"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlmodel import select
from loguru import logger
import json

from .db import AsyncSession, Episode


class EpisodeMemory:
    """에피소드 메모리 관리자"""
    
    @staticmethod
    async def create(
        session: AsyncSession,
        day: str,
        time_start: datetime,
        title: Optional[str] = None,
        nodes: Optional[Dict[str, Any]] = None,
        edges: Optional[Dict[str, Any]] = None
    ) -> Episode:
        """에피소드 생성"""
        episode = Episode(
            day=day,
            time_start=time_start,
            title=title,
            nodes=json.dumps(nodes) if nodes else None,
            edges=json.dumps(edges) if edges else None
        )
        
        session.add(episode)
        await session.commit()
        await session.refresh(episode)
        
        logger.debug(f"에피소드 생성: {episode.id} - {title}")
        return episode
        
    @staticmethod
    async def close(
        session: AsyncSession,
        episode_id: int,
        time_end: datetime
    ) -> Episode:
        """에피소드 종료"""
        result = await session.execute(
            select(Episode).where(Episode.id == episode_id)
        )
        episode = result.scalar_one_or_none()
        
        if not episode:
            raise ValueError(f"Episode not found: {episode_id}")
            
        episode.time_end = time_end
        await session.commit()
        await session.refresh(episode)
        
        logger.debug(f"에피소드 종료: {episode_id}")
        return episode
        
    @staticmethod
    async def get_recent(
        session: AsyncSession,
        limit: int = 3
    ) -> List[Episode]:
        """최근 에피소드 조회"""
        result = await session.execute(
            select(Episode)
            .order_by(Episode.time_start.desc())
            .limit(limit)
        )
        episodes = result.scalars().all()
        return list(episodes)
        
    @staticmethod
    async def get_by_day(
        session: AsyncSession,
        day: str
    ) -> List[Episode]:
        """특정 날짜의 에피소드 조회"""
        result = await session.execute(
            select(Episode)
            .where(Episode.day == day)
            .order_by(Episode.time_start)
        )
        episodes = result.scalars().all()
        return list(episodes)
