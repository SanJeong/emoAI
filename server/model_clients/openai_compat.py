"""OpenAI 호환 모델 클라이언트"""
import httpx
import json
from typing import Dict, Any, List, Optional
from loguru import logger


class OpenAICompatClient:
    """OpenAI 호환 API 클라이언트"""
    
    def __init__(self, config: Dict[str, Any]):
        self.base_url = config.get("base_url", "https://api.openai.com/v1")
        self.api_key = config.get("api_key", "")
        self.model = config.get("model", "gpt-5-mini")
        self.temperature = config.get("temperature", None)  # None으로 설정해서 모델 기본값 사용
        self.stream = config.get("stream", False)
        
        # 최신 모델들의 파라미터 제한 사항 체크
        self.supports_temperature = not self.model.startswith("gpt-5")  # gpt-5 모델들은 temperature 변경 불가
        self.use_completion_tokens = self.model.startswith("gpt-5") or self.model.startswith("gpt-4")  # 최신 모델들은 max_completion_tokens 사용
        
        # HTTP 클라이언트
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            timeout=60.0
        )
        
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None
    ) -> str:
        """채팅 완성 요청"""
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False  # 스트리밍 비활성화
        }
        
        # temperature 설정 (모델이 지원하는 경우에만)
        if self.supports_temperature:
            temp_value = temperature or self.temperature or 1.0
            payload["temperature"] = temp_value
        
        # max_tokens 설정 (모델에 따라 다른 파라미터 사용)
        if max_tokens:
            if self.use_completion_tokens:
                payload["max_completion_tokens"] = max_tokens
            else:
                payload["max_tokens"] = max_tokens
            
        if response_format:
            payload["response_format"] = response_format
            
        try:
            # 요청 페이로드 로깅
            logger.info(f"OpenAI API 요청 페이로드: {json.dumps(payload, ensure_ascii=False, indent=2)}")
            
            response = await self.client.post(
                "/chat/completions",
                json=payload
            )
            response.raise_for_status()
            
            data = response.json()
            
            # 전체 응답 구조 로깅 (디버깅용)
            logger.info(f"OpenAI API 전체 응답: {json.dumps(data, ensure_ascii=False, indent=2)}")
            
            # choices 배열 확인
            if not data.get("choices") or len(data["choices"]) == 0:
                logger.error("OpenAI API 응답에 choices가 없음")
                return ""
            
            choice = data["choices"][0]
            message = choice.get("message", {})
            content = message.get("content", "")
            
            logger.info(f"추출된 content: '{content}' (타입: {type(content)}, 길이: {len(content) if content else 0})")
            
            # finish_reason 확인
            finish_reason = choice.get("finish_reason", "unknown")
            logger.info(f"완료 이유: {finish_reason}")
            
            # 사용량 로깅 (있는 경우)
            if "usage" in data:
                logger.debug(f"토큰 사용: {data['usage']}")
                
            return content or ""
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP 오류: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"API 호출 오류: {e}")
            raise
            
    async def close(self):
        """클라이언트 종료"""
        await self.client.aclose()
