"""Realizer 모듈 - 최종 텍스트 생성"""
import re
from typing import List, Dict, Any, Optional
from loguru import logger

from ..schemas import PlannerOutput
from ..config.loader import config_loader
from ..model_clients.openai_compat import OpenAICompatClient


class Realizer:
    """최종 텍스트 생성기"""
    
    # 금지어 리스트
    FORBIDDEN_WORDS = [
        "한 문장으로", "체크인", "루틴", "목표", "리프레이밍",
        "다음 단계", "23:00", "어떤 기분", "어떤 감정",
        "도움이 필요하시면", "제가 도와드릴", "함께 해결",
        "단계별로", "체계적으로", "구체적으로"
    ]
    
    def __init__(self):
        self.config = config_loader.get_model_config()
        self.client = OpenAICompatClient(self.config)
        
    async def generate(
        self,
        user_text: str,
        planner_output: PlannerOutput,
        conversation_history: List[Dict[str, str]] = None
    ) -> str:
        """최종 텍스트 생성"""
        
        # 프롬프트 조합
        system_prompt = self._build_system_prompt()
        
        # 메시지 구성
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # 대화 히스토리 추가 (있으면)
        if conversation_history:
            messages.extend(conversation_history[-6:])  # 최근 6개만
            
        # 현재 요청 추가
        user_message = f"""사용자: {user_text}

플랜 초안: {planner_output.draft}
선택된 전술: {[op.get('channel', '') + '.' + op.get('op', '') for op in planner_output.ops]}

위 정보를 참고하여 자연스러운 한국어로 응답하세요. 
- 사람 대 사람 톤
- 과도한 공감 표현 자제
- 간결하고 진솔하게"""
        
        messages.append({"role": "user", "content": user_message})
        
        try:
            # LLM 호출
            response = await self.client.chat_completion(
                messages=messages,
                temperature=0.7,
                max_tokens=300
            )
            
            # Humanizer 필터 적용
            final_text = self._humanize(response)
            
            logger.info(f"AI 응답 (생성 전): {response}")
            logger.info(f"AI 응답 (Humanizer 후): {final_text}")
            logger.info(f"텍스트 생성 완료: {len(final_text)}자")
            return final_text
            
        except Exception as e:
            logger.error(f"텍스트 생성 오류: {e}")
            # 플래너 초안 사용
            return self._humanize(planner_output.draft)
            
    def _build_system_prompt(self) -> str:
        """시스템 프롬프트 조합"""
        prompts = []
        
        # 코어 페르소나
        core = config_loader.get_prompt("core.persona.ko")
        if core:
            prompts.append(core)
            
        # 런타임 규칙
        runtime = config_loader.get_prompt("runtime.rules")
        if runtime:
            prompts.append(runtime)
            
        # 환경 제약
        env = config_loader.get_prompt("env.constraints")
        if env:
            prompts.append(env)
            
        # 기본값
        if not prompts:
            prompts.append(self._get_default_system_prompt())
            
        return "\n\n".join(prompts)
        
    def _humanize(self, text: str) -> str:
        """Humanizer 필터 - 금지어 제거 및 톤 조정"""
        
        # 금지어 제거/치환
        for word in self.FORBIDDEN_WORDS:
            text = text.replace(word, "")
            
        # 과도한 존댓말 축소
        text = re.sub(r'하시겠어요\?', '할래?', text)
        text = re.sub(r'하실래요\?', '할래?', text)
        text = re.sub(r'드릴게요', '줄게', text)
        text = re.sub(r'드려요', '줘', text)
        
        # 상담사 말투 제거
        text = re.sub(r'^\s*네,?\s*', '', text)  # 문장 시작 "네," 제거
        text = re.sub(r'그렇군요[\.!]?', '그렇구나.', text)
        text = re.sub(r'이해합니다[\.!]?', '알겠어.', text)
        
        # 연속 공백/줄바꿈 정리
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # 문장 길이 체크 (너무 길면 자르기)
        sentences = text.split('.')
        if len(sentences) > 3:
            text = '.'.join(sentences[:3]) + '.'
            
        return text
        
    def _get_default_system_prompt(self) -> str:
        """기본 시스템 프롬프트"""
        return """너는 텍스트 기반 감정 파트너다. 자연스러운 한국어로 대화한다.

원칙:
- 사람처럼 대화 (상담사/봇 말투 금지)
- 반말 사용 (친근한 톤)
- 간결하고 진솔하게
- 과도한 공감 표현 자제
- 목록이나 단계별 설명 지양"""
        
    async def close(self):
        """클라이언트 종료"""
        await self.client.close()
