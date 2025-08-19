"""영향력 원장 관리"""
from typing import List, Optional, Dict, Any
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
        reward_proxy: float = 0.0,
        plan_data: Optional[Dict[str, Any]] = None
    ) -> Ledger:
        """원장 기록 - 오퍼레이터 기록 확장"""
        
        # operators 리스트를 "채널.오퍼레이터" 형식으로 포맷
        formatted_ops = []
        if plan_data and "ops" in plan_data:
            for op in plan_data["ops"]:
                channel = op.get("channel", "")
                op_name = op.get("op", "")
                formatted_ops.append(f"{channel}.{op_name}")
        elif operators:
            formatted_ops = operators
        
        entry = Ledger(
            session_id=session_id,
            operators=json.dumps(formatted_ops),
            user_reaction=json.dumps(user_reaction) if user_reaction else None,
            reward_proxy=reward_proxy
        )
        
        session.add(entry)
        await session.commit()
        await session.refresh(entry)
        
        # 추가 정보 로깅
        notes = ""
        if plan_data:
            notes = plan_data.get("draft", "")
            if plan_data.get("risk_flags"):
                risk_info = json.dumps(plan_data["risk_flags"], ensure_ascii=False)
                notes += f" [위험플래그: {risk_info}]"
        
        logger.info(f"원장 기록: {entry.id} - ops: {formatted_ops}")
        if notes:
            logger.debug(f"원장 노트: {notes}")
        
        return entry
        
    @staticmethod
    async def log_ledger(
        session: AsyncSession,
        session_id: str,
        plan_output,
        user_reaction: Optional[Dict[str, Any]] = None,
        reward_proxy: float = 0.0
    ) -> Ledger:
        """플래너 출력으로부터 원장 기록 생성"""
        
        plan_data = {
            "plan_id": plan_output.plan_id,
            "ops": plan_output.ops,
            "draft": plan_output.draft,
            "risk_flags": plan_output.risk_flags
        }
        
        # 오퍼레이터 추출
        operators = [f"{op.get('channel', '')}.{op.get('op', '')}" for op in plan_output.ops]
        
        return await LedgerMemory.log(
            session=session,
            session_id=session_id,
            operators=operators,
            user_reaction=user_reaction,
            reward_proxy=reward_proxy,
            plan_data=plan_data
        )
        
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
