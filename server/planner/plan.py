"""플래너 모듈"""
import json
from typing import Dict, Any, List
from datetime import datetime
from loguru import logger

from ..schemas import PlannerOutput, MemoryContext
from ..config.loader import config_loader
from ..model_clients.openai_compat import OpenAICompatClient


class Planner:
    """B/I/T/E 전술 플래너"""
    
    def __init__(self):
        self.config = config_loader.get_model_config()
        self.client = OpenAICompatClient(self.config)
        
    async def plan(
        self,
        user_text: str,
        memory_context: MemoryContext,
        session_id: str
    ) -> PlannerOutput:
        """플래닝 실행"""
        
        # 시스템 프롬프트
        system_prompt = config_loader.get_prompt("planner.bite")
        if not system_prompt:
            system_prompt = self._get_default_planner_prompt()
            
        # 컨텍스트 구성
        context = self._build_context(memory_context)
        
        # 메시지 구성
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"""
현재 상태:
{context}

사용자 입력: {user_text}

위 정보를 바탕으로 B/I/T/E 전술을 선택하고 JSON 형식으로 응답하세요.
"""}
        ]
        
        try:
            # LLM 호출
            response = await self.client.chat_completion(
                messages=messages,
                temperature=0.5,
                response_format={"type": "json_object"}
            )
            
            # JSON 파싱
            plan_data = json.loads(response)
            
            # PlannerOutput 생성
            output = PlannerOutput(
                plan_id=f"{datetime.now().timestamp()}#{session_id}",
                ops=plan_data.get("ops", []),
                draft=plan_data.get("draft", ""),
                risk_flags=plan_data.get("risk_flags", {
                    "overspeed": False,
                    "boundary_touch": False
                })
            )
            
            # 검증 및 정규화
            output = self._validate_and_normalize(output)
            
            logger.info(f"플래너 JSON 응답: {response}")
            logger.info(f"플래너 초안: '{output.draft}'")
            ops_list = [f"{op.get('channel', '')}.{op.get('op', '')}" for op in output.ops]
            logger.info(f"선택된 오퍼레이터: {ops_list}")
            logger.info(f"플래닝 완료: {len(output.ops)} ops")
            return output
            
        except Exception as e:
            logger.error(f"플래닝 오류: {e}")
            # 기본 응답
            return PlannerOutput(
                plan_id=f"{datetime.now().timestamp()}#{session_id}",
                ops=[],
                draft="음... 그렇구나.",
                risk_flags={"overspeed": False, "boundary_touch": False}
            )
            
    def _build_context(self, memory: MemoryContext) -> str:
        """컨텍스트 문자열 구성"""
        parts = []
        
        if memory.today_context:
            parts.append(f"오늘 컨텍스트: {memory.today_context[:500]}")
            
        if memory.highlights:
            parts.append(f"하이라이트: {', '.join(memory.highlights[:5])}")
            
        if memory.pinned_facts:
            parts.append(f"고정 사실: {json.dumps(memory.pinned_facts, ensure_ascii=False)[:200]}")
            
        return "\n".join(parts) if parts else "컨텍스트 없음"
        
    def _validate_and_normalize(self, output: PlannerOutput) -> PlannerOutput:
        """플랜 검증 및 정규화"""
        
        # 오퍼레이터 2개 제한
        if len(output.ops) > 2:
            logger.warning(f"오퍼레이터 과다: {len(output.ops)} -> 2개로 제한")
            output.ops = output.ops[:2]
            
        # 금지 조합 체크 (depth + step_up)
        ops_types = [op.get("op", "") for op in output.ops]
        if "depth" in ops_types and "step_up" in ops_types:
            logger.warning("금지 조합 감지: depth + step_up")
            # step_up 제거
            output.ops = [op for op in output.ops if op.get("op") != "step_up"]
            output.risk_flags["boundary_touch"] = True
            
        return output
        
    def _get_default_planner_prompt(self) -> str:
        """기본 플래너 프롬프트"""
        return """임무: 입력과 상태요약을 바탕으로 B/I/T/E 전술 1~2개를 고르고, JSON을 산출한다.

B (Build): 관계 구축, 공감, 신뢰
I (Inquire): 탐색, 질문, 이해
T (Transform): 전환, 재구성, 관점 변화  
E (Empower): 임파워먼트, 자율성, 행동

출력 형식:
{
  "plan_id": "timestamp#session",
  "ops": [
    {"channel": "E", "op": "tentative_label", "args": {"label": "감정", "intensity": "mid"}, "why": "이유"}
  ],
  "draft": "자연어 응답 초안 2-4문장",
  "risk_flags": {"overspeed": false, "boundary_touch": false}
}

규칙:
- 오퍼레이터는 최대 2개
- depth와 step_up 동시 사용 금지
- 사용자에게 내부 결정 노출 금지"""
        
    async def close(self):
        """클라이언트 종료"""
        await self.client.close()
