"""백그라운드 작업 큐"""
import asyncio
from typing import Any, Dict
from loguru import logger

from ..memory.db import AsyncSessionLocal
from ..memory.atoms import AtomMemory
from ..memory.daily import DailyMemory
from ..memory.ledger import LedgerMemory


class BackgroundQueue:
    """비동기 백그라운드 작업 큐"""
    
    def __init__(self):
        self.queue: asyncio.Queue = asyncio.Queue()
        self.running = False
        self.worker_task = None
        
    async def start(self):
        """워커 시작"""
        if self.running:
            return
            
        self.running = True
        self.worker_task = asyncio.create_task(self._worker())
        logger.info("백그라운드 큐 시작")
        
    async def stop(self):
        """워커 정지"""
        self.running = False
        if self.worker_task:
            await self.queue.put(None)  # 종료 신호
            await self.worker_task
        logger.info("백그라운드 큐 정지")
        
    async def _worker(self):
        """워커 루프"""
        while self.running:
            try:
                task = await self.queue.get()
                if task is None:  # 종료 신호
                    break
                    
                await self._process_task(task)
                
            except Exception as e:
                logger.error(f"백그라운드 작업 오류: {e}")
                
    async def _process_task(self, task: Dict[str, Any]):
        """작업 처리"""
        task_type = task.get("type")
        
        try:
            if task_type == "save_atom":
                await self._save_atom(task)
            elif task_type == "update_daily":
                await self._update_daily(task)
            elif task_type == "log_ledger":
                await self._log_ledger(task)
            else:
                logger.warning(f"알 수 없는 작업 타입: {task_type}")
                
        except Exception as e:
            logger.error(f"작업 처리 오류 [{task_type}]: {e}")
            
    async def _save_atom(self, task: Dict[str, Any]):
        """Atom 저장"""
        async with AsyncSessionLocal() as session:
            atom = await AtomMemory.create(
                session=session,
                day=task["day"],
                author=task["author"],
                text_raw=task["text_raw"],
                text_final=task.get("text_final"),
                ctx=task.get("ctx"),
                affect=task.get("affect"),
                style=task.get("style"),
                levers=task.get("levers"),
                salience=task.get("salience", 0.5)
            )
            
            # 벡터 저장 (있으면)
            from server.main import vector_jobs
            if vector_jobs and atom:
                atom_dict = {
                    "id": atom.id,
                    "session_id": task.get("session_id", ""),
                    "day": atom.day,
                    "ts": atom.ts,
                    "author": atom.author,
                    "text_raw": atom.text_raw,
                    "text_final": atom.text_final,
                    "affect": atom.affect,
                    "salience": atom.salience,
                    "episode_id": atom.episode_id
                }
                await vector_jobs.upsert_atom(atom_dict)
            
    async def _update_daily(self, task: Dict[str, Any]):
        """일일 컨텍스트 업데이트"""
        async with AsyncSessionLocal() as session:
            # 현재 요약에 추가
            context = await DailyMemory.get_or_create(
                session=session,
                day=task["day"],
                session_id=task["session_id"]
            )
            
            # 롤링 요약 업데이트
            current_summary = context.rolling_summary or ""
            new_text = task.get("text", "")
            
            if new_text:
                # 새로운 요약 생성
                updated_summary = self._create_rolling_summary(current_summary, new_text)
                
                # UTF-8 바이트 길이 기준 제한 (MySQL TEXT 타입은 65,535 바이트, 안전하게 50,000 바이트로 제한)
                max_bytes = 50000
                updated_bytes = updated_summary.encode('utf-8')
                
                if len(updated_bytes) > max_bytes:
                    # 바이트 길이 기준으로 자르기 (맨 앞 부분을 잘라내어 최신 내용 유지)
                    truncated_bytes = updated_bytes[-max_bytes:]
                    # UTF-8 문자가 중간에 잘리지 않도록 조정
                    try:
                        updated_summary = truncated_bytes.decode('utf-8')
                    except UnicodeDecodeError:
                        # 잘린 부분 때문에 디코딩 오류가 발생하면, 조금 더 자르기
                        for i in range(1, 4):  # UTF-8에서 최대 3바이트이므로
                            try:
                                updated_summary = truncated_bytes[i:].decode('utf-8')
                                break
                            except UnicodeDecodeError:
                                continue
                        else:
                            # 그래도 안되면 새 텍스트만 사용
                            updated_summary = new_text[:1000]  # 새 텍스트를 1000자로 제한
                    
                await DailyMemory.update(
                    session=session,
                    day=task["day"],
                    rolling_summary=updated_summary
                )

    def _create_rolling_summary(self, current_summary: str, new_text: str) -> str:
        """롤링 요약 생성 - 의미있는 대화 흐름 요약"""
        
        # 새 텍스트가 너무 길면 요약
        if len(new_text) > 200:
            # U: ... A: ... 패턴에서 핵심 내용만 추출
            try:
                parts = new_text.split("A: ")
                if len(parts) == 2:
                    user_part = parts[0].replace("U: ", "").strip()
                    agent_part = parts[1].strip()
                    
                    # 감정 키워드 추출
                    emotions = ["우울", "슬픔", "기쁨", "화남", "불안", "걱정", "행복", "힘들"]
                    
                    # 사용자 메시지 요약
                    user_summary = user_part[:50] + "..." if len(user_part) > 50 else user_part
                    for emotion in emotions:
                        if emotion in user_part:
                            user_summary = f"({emotion}) {user_summary}"
                            break
                    
                    # 에이전트 메시지 요약  
                    agent_summary = agent_part[:50] + "..." if len(agent_part) > 50 else agent_part
                    
                    new_summary = f"사용자: {user_summary} → 응답: {agent_summary}"
                else:
                    new_summary = new_text[:100] + "..." if len(new_text) > 100 else new_text
            except Exception:
                # 파싱 실패시 단순 요약
                new_summary = new_text[:100] + "..." if len(new_text) > 100 else new_text
        else:
            new_summary = new_text
        
        # 기존 요약과 결합
        if current_summary:
            # 기존 요약이 너무 길면 압축
            if len(current_summary) > 10000:  # 10000자 이상이면 압축
                # 최근 부분만 유지 (뒤쪽 5000자)
                current_summary = "...(이전 대화 요약)..." + current_summary[-5000:]
            
            # 중복 패턴 제거
            lines = current_summary.split("\n")
            new_lines = [line for line in lines if line.strip()]
            
            # 유사한 패턴 제거 (같은 인사말 등)
            filtered_lines = []
            for line in new_lines:
                # 단순 인사말 중복 제거
                if any(greeting in line for greeting in ["안녕", "어떻게 지내", "괜찮"]) and len(filtered_lines) > 0:
                    similar_found = False
                    for existing in filtered_lines[-3:]:  # 최근 3줄과 비교
                        if any(greeting in existing for greeting in ["안녕", "어떻게 지내", "괜찮"]):
                            similar_found = True
                            break
                    if not similar_found:
                        filtered_lines.append(line)
                else:
                    filtered_lines.append(line)
            
            current_summary = "\n".join(filtered_lines[-20:])  # 최근 20줄만 유지
            
            return f"{current_summary}\n{new_summary}"
        else:
            return new_summary
                
    async def _log_ledger(self, task: Dict[str, Any]):
        """원장 기록"""
        async with AsyncSessionLocal() as session:
            await LedgerMemory.log(
                session=session,
                session_id=task["session_id"],
                operators=task.get("operators", []),
                user_reaction=task.get("user_reaction"),
                reward_proxy=task.get("reward_proxy", 0.0)
            )
            
    async def enqueue(self, task: Dict[str, Any]):
        """작업 추가"""
        await self.queue.put(task)
        logger.debug(f"작업 큐 추가: {task.get('type')}")
        
        
# 전역 큐 인스턴스
background_queue = BackgroundQueue()
