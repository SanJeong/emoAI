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
        
    def _detect_play_intent(self, user_text: str) -> bool:
        """놀이 인텐트 감지"""
        play_keywords = ["수수께끼", "퀴즈", "농담", "맞혀봐", "밈", "장난", "놀이", "게임"]
        return any(keyword in user_text for keyword in play_keywords)
        
    def _get_bite_catalog(self):
        """BITE v2 카탈로그 반환"""
        return {
            "B": {
                "sync_rhythm": "대화 리듬 미세 조절(짧게/한두 문장)",
                "invite_microaction": "아주 가벼운 선택지 2개",
                "playful_gap": "짧은 간격 후 한 줄",
                "shared_ritual_light": "가벼운 반복 장치(의무화 금지)"
            },
            "I": {
                "curiosity_gap": "기만 없이 호기심 여는 반문/단서",
                "self_reveal_min": "자기 정보 한 스푼",
                "callback_ref": "이전 요소 콜백",
                "boundary_hint": "오해 방지 안전레일 한 줄"
            },
            "T": {
                "quick_reframe": "한 줄 재프레이밍(장문/분석 금지)",
                "yes_and": "받아치며 확장",
                "alt_choice": "가벼운 대안 2택",
                "micro_story": "1–2문장 상상 시나리오"
            },
            "E": {
                "affect_match": "톤 맞추기(낮/중/높)",
                "warm_ping": "짧은 온기/칭찬(과잉 금지)",
                "tempo_shift": "말속도/길이 전환 1문장"
            }
        }
        
    def _get_allowed_ops(self, play_intent: bool):
        """허용된 오퍼레이터 반환"""
        if play_intent:
            # 놀이 모드에서 허용된 전술만
            return [
                ("T", "yes_and"),
                ("T", "quick_reframe"),
                ("I", "curiosity_gap"),
                ("B", "invite_microaction"),
                ("E", "affect_match")
            ]
        else:
            # 전체 카탈로그
            catalog = self._get_bite_catalog()
            ops = []
            for channel, tactics in catalog.items():
                for tactic in tactics.keys():
                    ops.append((channel, tactic))
            return ops

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
        
        # 놀이 인텐트 감지
        play_intent = self._detect_play_intent(user_text)
        logger.info(f"놀이 인텐트 감지: {play_intent}")
        
        # 허용된 오퍼레이터 조회
        allowed_ops = self._get_allowed_ops(play_intent)
        max_ops = 1 if play_intent else 2
        
        # 메시지 구성
        intent_info = "놀이/장난 모드" if play_intent else "일반 모드"
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"""
현재 상태:
{context}

사용자 입력: {user_text}

모드: {intent_info}
허용된 전술 (최대 {max_ops}개 선택):
{self._format_allowed_ops(allowed_ops)}

위 정보를 바탕으로 B/I/T/E 전술을 선택하고 JSON 형식으로 응답하세요.
"""}
        ]
        
        try:
            # LLM 호출
            response = await self.client.chat_completion(
                messages=messages,
                temperature=0.7,
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
            
            # 검증 및 정규화 (놀이 모드 정보 전달)
            output = self._validate_and_normalize(output, play_intent, max_ops)
            
            logger.info(f"플래너 JSON 응답: {response}")
            logger.info(f"플래너 초안: '{output.draft}'")
            ops_list = [f"{op.get('channel', '')}.{op.get('op', '')}" for op in output.ops]
            logger.info(f"선택된 오퍼레이터: {ops_list}")
            logger.info(f"플래닝 완료: {len(output.ops)} ops, 놀이모드: {play_intent}")
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
        
    def _format_allowed_ops(self, allowed_ops):
        """허용된 오퍼레이터를 문자열로 포맷팅"""
        result = []
        for channel, op in allowed_ops:
            result.append(f"  {channel}.{op}")
        return "\n".join(result)
        
    def _validate_and_normalize(self, output: PlannerOutput, play_intent: bool = False, max_ops: int = 2) -> PlannerOutput:
        """플랜 검증 및 정규화"""
        
        # 오퍼레이터 개수 제한
        if len(output.ops) > max_ops:
            logger.warning(f"오퍼레이터 과다: {len(output.ops)} -> {max_ops}개로 제한")
            output.ops = output.ops[:max_ops]
            
        # 놀이 모드에서 허용되지 않은 전술 체크
        if play_intent:
            allowed_ops = self._get_allowed_ops(True)
            allowed_set = set(allowed_ops)
            filtered_ops = []
            
            for op in output.ops:
                channel = op.get("channel", "")
                op_name = op.get("op", "")
                if (channel, op_name) in allowed_set:
                    filtered_ops.append(op)
                else:
                    logger.warning(f"놀이 모드에서 허용되지 않은 전술 제거: {channel}.{op_name}")
                    
            output.ops = filtered_ops
            
            # 놀이 모드에서 공감 라벨링 체크
            for op in output.ops:
                if "label" in op.get("args", {}) or "empathy" in op.get("op", ""):
                    logger.warning("놀이 모드에서 공감 라벨링 감지")
                    output.risk_flags["boundary_touch"] = True
        else:
            # 기존 금지 조합 체크 (일반 모드에서만)
            ops_types = [op.get("op", "") for op in output.ops]
            if "depth" in ops_types and "step_up" in ops_types:
                logger.warning("금지 조합 감지: depth + step_up")
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
