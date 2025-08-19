"""WebSocket 핸들러"""
import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, date
from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger

from .schemas import (
    MessageType, UserMessage, OpenSession, 
    AgentResponse, PlannerOutput, MemoryContext
)
from .memory.db import AsyncSessionLocal
from .memory.daily import DailyMemory
from .memory.episodes import EpisodeMemory
from .planner.plan import Planner
from .realizer.generate import Realizer
from .background.queue import background_queue
from .config.loader import config_loader


class ChatSession:
    """채팅 세션 관리"""
    
    def __init__(self, session_id: str, websocket: WebSocket):
        self.session_id = session_id
        self.websocket = websocket
        self.planner = Planner()
        self.realizer = Realizer()
        self.conversation_history: List[Dict[str, str]] = []
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.current_episode_id: Optional[int] = None
        
    async def handle_message(self, data: Dict[str, Any]):
        """메시지 처리"""
        msg_type = data.get("type")
        
        try:
            if msg_type == MessageType.OPEN_SESSION:
                await self._handle_open_session(data)
            elif msg_type == MessageType.USER_MESSAGE:
                await self._handle_user_message(data)
            else:
                logger.warning(f"알 수 없는 메시지 타입: {msg_type}")
                
        except Exception as e:
            logger.error(f"메시지 처리 오류: {e}")
            await self._send_error(str(e))
            
    async def _handle_open_session(self, data: Dict[str, Any]):
        """세션 열기 처리"""
        logger.info(f"세션 열림: {self.session_id}")
        
        # 에피소드 생성
        async with AsyncSessionLocal() as session:
            episode = await EpisodeMemory.create(
                session=session,
                day=date.today().isoformat(),
                time_start=datetime.utcnow(),
                title=f"대화 세션 {self.session_id[:8]}"
            )
            self.current_episode_id = episode.id
            
    async def _handle_user_message(self, data: Dict[str, Any]):
        """사용자 메시지 처리"""
        user_msg = UserMessage(**data)
        logger.info(f"사용자 메시지 (전체): {user_msg.text}")
        logger.info(f"사용자 메시지 길이: {len(user_msg.text)}자")
        
        # 대화 히스토리 추가
        self.conversation_history.append({
            "role": "user",
            "content": user_msg.text
        })
        
        # 메모리 컨텍스트 로드
        memory_context = await self._load_memory_context()
        
        # 파이프라인 모드 확인
        pipeline_mode = config_loader.get_pipeline_mode()
        
        if pipeline_mode == "two_call":
            # 2-콜 모드: Planner → Realizer
            await self._two_call_pipeline(user_msg, memory_context)
        else:
            # 1-콜 모드: 직접 생성
            await self._one_call_pipeline(user_msg, memory_context)
            
    async def _two_call_pipeline(self, user_msg: UserMessage, memory: MemoryContext):
        """2-콜 파이프라인"""
        
        # 벡터 하이라이트 보강 (선택)
        from .main import vector_store, embedding_client, vector_config
        if vector_store and vector_config:
            from .pipeline.hooks import vector_highlights_for_planner
            highlights = await vector_highlights_for_planner(
                user_text=user_msg.text,
                session_id=self.session_id,
                vector_store=vector_store,
                embedding_client=embedding_client,
                config=vector_config
            )
            if highlights:
                memory.highlights.extend(highlights[:3])
        
        # 1. 플래닝
        planner_output = await self.planner.plan(
            user_text=user_msg.text,
            memory_context=memory,
            session_id=self.session_id
        )
        
        # 2. 텍스트 생성
        final_text = await self.realizer.generate(
            user_text=user_msg.text,
            planner_output=planner_output,
            conversation_history=self.conversation_history
        )
        
        # 3. 응답 전송
        await self._send_response(final_text, planner_output.ops)
        
        # 4. 백그라운드 작업
        await self._enqueue_background_tasks(
            user_text=user_msg.text,
            agent_text=final_text,
            operators=[f"{op['channel']}.{op['op']}" for op in planner_output.ops]
        )
        
    async def _one_call_pipeline(self, user_msg: UserMessage, memory: MemoryContext):
        """1-콜 파이프라인 (직접 생성)"""
        
        # 더미 플래너 출력
        dummy_planner = PlannerOutput(
            plan_id=f"{datetime.now().timestamp()}#{self.session_id}",
            ops=[],
            draft="",
            risk_flags={"overspeed": False, "boundary_touch": False}
        )
        
        # 직접 텍스트 생성
        final_text = await self.realizer.generate(
            user_text=user_msg.text,
            planner_output=dummy_planner,
            conversation_history=self.conversation_history
        )
        
        # 응답 전송
        await self._send_response(final_text, [])
        
        # 백그라운드 작업
        await self._enqueue_background_tasks(
            user_text=user_msg.text,
            agent_text=final_text,
            operators=[]
        )
        
    async def _load_memory_context(self) -> MemoryContext:
        """메모리 컨텍스트 로드"""
        today = date.today().isoformat()
        
        async with AsyncSessionLocal() as session:
            # 일일 컨텍스트
            daily = await DailyMemory.get_or_create(
                session=session,
                day=today,
                session_id=self.session_id
            )
            daily_dict = DailyMemory.parse_context(daily)
            
            # 최근 에피소드
            episodes = await EpisodeMemory.get_recent(session, limit=3)
            episode_dicts = [
                {
                    "id": ep.id,
                    "title": ep.title,
                    "day": ep.day
                }
                for ep in episodes
            ]
            
            return MemoryContext(
                today_context=daily_dict.get("rolling_summary", ""),
                highlights=daily_dict.get("highlights", []),
                pinned_facts=daily_dict.get("pinned_facts", {}),
                recent_episodes=episode_dicts,
                schema_summary=None
            )
            
    async def _send_response(self, text: str, operators: List[str]):
        """응답 전송"""
        
        logger.info(f"WebSocket으로 전송할 텍스트: '{text}'")
        logger.info(f"전송할 텍스트 길이: {len(text)}자")
        
        # 최종 텍스트 전송
        await self.websocket.send_json({
            "type": MessageType.FINAL_TEXT,
            "message_id": f"a-{datetime.now().timestamp()}",
            "text": text
        })
        
        # 메타 정보 전송 (사용된 오퍼레이터)
        if operators:
            await self.websocket.send_json({
                "type": MessageType.META,
                "used_ops": operators
            })
            
        # EOT 전송
        await self.websocket.send_json({
            "type": MessageType.EOT
        })
        
        # 대화 히스토리 추가
        self.conversation_history.append({
            "role": "assistant",
            "content": text
        })
        
    async def _send_error(self, error: str):
        """에러 전송"""
        await self.websocket.send_json({
            "type": MessageType.ERROR,
            "error": error
        })
        
    async def _enqueue_background_tasks(
        self, 
        user_text: str, 
        agent_text: str,
        operators: List[str]
    ):
        """백그라운드 작업 큐에 추가"""
        today = date.today().isoformat()
        
        # Atom 저장 (사용자)
        await background_queue.enqueue({
            "type": "save_atom",
            "day": today,
            "author": "user",
            "text_raw": user_text,
            "text_final": user_text,
            "episode_id": self.current_episode_id
        })
        
        # Atom 저장 (에이전트)
        await background_queue.enqueue({
            "type": "save_atom",
            "day": today,
            "author": "agent",
            "text_raw": agent_text,
            "text_final": agent_text,
            "levers": {"operators": operators},
            "episode_id": self.current_episode_id
        })
        
        # 일일 컨텍스트 업데이트
        await background_queue.enqueue({
            "type": "update_daily",
            "day": today,
            "session_id": self.session_id,
            "text": f"U: {user_text[:100]}... A: {agent_text[:100]}..."
        })
        
        # 원장 기록
        if operators:
            await background_queue.enqueue({
                "type": "log_ledger",
                "session_id": self.session_id,
                "operators": operators
            })
            
    async def close(self):
        """세션 종료"""
        # 에피소드 종료
        if self.current_episode_id:
            async with AsyncSessionLocal() as session:
                await EpisodeMemory.close(
                    session=session,
                    episode_id=self.current_episode_id,
                    time_end=datetime.utcnow()
                )
                
        # 클라이언트 종료
        await self.planner.close()
        await self.realizer.close()
        
        logger.info(f"세션 종료: {self.session_id}")


class WebSocketManager:
    """WebSocket 연결 관리자"""
    
    def __init__(self):
        self.active_sessions: Dict[str, ChatSession] = {}
        
    async def connect(self, websocket: WebSocket, session_id: str):
        """연결 수락"""
        await websocket.accept()
        session = ChatSession(session_id, websocket)
        self.active_sessions[session_id] = session
        logger.info(f"WebSocket 연결: {session_id}")
        return session
        
    async def disconnect(self, session_id: str):
        """연결 해제"""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            await session.close()
            del self.active_sessions[session_id]
            logger.info(f"WebSocket 해제: {session_id}")
            
            
# 전역 매니저
ws_manager = WebSocketManager()
