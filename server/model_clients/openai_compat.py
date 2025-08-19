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
        self.temperature = config.get("temperature", 0.7)
        self.stream = config.get("stream", False)
        
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
            "temperature": temperature or self.temperature,
            "stream": False  # 스트리밍 비활성화
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
            
        if response_format:
            payload["response_format"] = response_format
            
        try:
            response = await self.client.post(
                "/chat/completions",
                json=payload
            )
            response.raise_for_status()
            
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            
            # 사용량 로깅 (있는 경우)
            if "usage" in data:
                logger.debug(f"토큰 사용: {data['usage']}")
                
            return content
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP 오류: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"API 호출 오류: {e}")
            raise
            
    async def close(self):
        """클라이언트 종료"""
        await self.client.aclose()
