#!/usr/bin/env python3
"""OpenAI API 테스트 스크립트"""
import os
import asyncio
import httpx
import json
from pathlib import Path

async def test_openai_api():
    """OpenAI API 직접 테스트"""
    
    # .env 파일에서 API 키 읽기
    env_path = Path(".env")
    api_key = None
    
    if env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                if line.startswith("OPENAI_API_KEY="):
                    api_key = line.split("=", 1)[1].strip()
                    if api_key.startswith('"') and api_key.endswith('"'):
                        api_key = api_key[1:-1]
                    break
    
    if not api_key:
        print("❌ API 키를 찾을 수 없음")
        return
        
    print(f"✅ API 키 발견: {api_key[:15]}...")
    
    # 간단한 API 요청
    payload = {
        "model": "gpt-5-mini",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, how are you?"}
        ],
        "max_completion_tokens": 50
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            print("🔄 OpenAI API 호출 중...")
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                json=payload,
                headers=headers
            )
            
            print(f"📊 응답 상태: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ API 호출 성공!")
                print(f"📄 전체 응답: {json.dumps(data, indent=2, ensure_ascii=False)}")
                
                if "choices" in data and len(data["choices"]) > 0:
                    content = data["choices"][0]["message"]["content"]
                    print(f"💬 응답 내용: '{content}'")
                else:
                    print("❌ choices가 없거나 비어있음")
            else:
                print(f"❌ API 오류: {response.status_code}")
                print(f"📄 오류 내용: {response.text}")
                
    except Exception as e:
        print(f"❌ 예외 발생: {e}")

if __name__ == "__main__":
    asyncio.run(test_openai_api())
