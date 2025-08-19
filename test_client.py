#!/usr/bin/env python3
"""WebSocket 테스트 클라이언트"""
import asyncio
import json
import websockets
from datetime import datetime

async def test_client():
    """테스트 메시지 전송"""
    
    # WebSocket 연결
    session_id = f"test-{int(datetime.now().timestamp())}"
    uri = f"ws://localhost:8787/ws/chat?session_id={session_id}"
    
    try:
        async with websockets.connect(uri) as websocket:
            print(f"WebSocket 연결 성공: {session_id}")
            
            # 세션 열기
            await websocket.send(json.dumps({
                "type": "open_session",
                "session_id": session_id
            }))
            
            # 응답 받기
            response = await websocket.recv()
            print(f"세션 열기 응답: {response}")
            
            # 사용자 메시지 전송
            test_message = "테스트 메시지입니다"
            await websocket.send(json.dumps({
                "type": "user_message",
                "text": test_message
            }))
            
            print(f"전송한 메시지: {test_message}")
            
            # 응답들 받기
            for i in range(5):  # 최대 5개 응답
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    response_data = json.loads(response)
                    print(f"응답 {i+1}: {response_data}")
                    
                    if response_data.get("type") == "eot":
                        break
                        
                except asyncio.TimeoutError:
                    print("응답 타임아웃")
                    break
                except Exception as e:
                    print(f"응답 처리 오류: {e}")
                    break
    
    except Exception as e:
        print(f"연결 오류: {e}")

if __name__ == "__main__":
    asyncio.run(test_client())
