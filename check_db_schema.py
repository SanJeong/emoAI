#!/usr/bin/env python3
"""데이터베이스 스키마 확인 스크립트"""
import os
import sys
sys.path.append('.')

# .env 로드
from dotenv import load_dotenv
load_dotenv()

async def check_db():
    try:
        # MySQL 연결 시도
        import pymysql
        
        connection = pymysql.connect(
            host=os.getenv('MYSQL_HOST', 'localhost'),
            port=int(os.getenv('MYSQL_PORT', 3306)),
            user=os.getenv('MYSQL_USER', 'root'),
            password=os.getenv('MYSQL_PASSWORD', 'jsjs1016'),
            database=os.getenv('MYSQL_DATABASE', 'emoai'),
            charset='utf8mb4'
        )
        
        print("✅ MySQL 연결 성공!")
        
        with connection.cursor() as cursor:
            # daily_context 테이블 스키마 확인
            cursor.execute("SHOW CREATE TABLE daily_context")
            result = cursor.fetchone()
            print("\n📋 daily_context 테이블 스키마:")
            print(result[1])
            
            # rolling_summary 컬럼 정보 확인
            cursor.execute("""
                SELECT COLUMN_NAME, COLUMN_TYPE, CHARACTER_MAXIMUM_LENGTH 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'daily_context' 
                AND COLUMN_NAME = 'rolling_summary'
            """, (os.getenv('MYSQL_DATABASE', 'emoai'),))
            
            column_info = cursor.fetchone()
            if column_info:
                print(f"\n📏 rolling_summary 컬럼 정보:")
                print(f"- 컬럼명: {column_info[0]}")
                print(f"- 타입: {column_info[1]}")
                print(f"- 최대 길이: {column_info[2]}")
            
            # 현재 데이터 길이 확인
            cursor.execute("SELECT day, CHAR_LENGTH(rolling_summary) as length FROM daily_context WHERE rolling_summary IS NOT NULL ORDER BY length DESC LIMIT 5")
            lengths = cursor.fetchall()
            print(f"\n📊 현재 rolling_summary 데이터 길이 TOP 5:")
            for day, length in lengths:
                print(f"- {day}: {length}자")
        
        connection.close()
        
    except Exception as e:
        print(f"❌ 데이터베이스 연결 실패: {e}")
        print("\n📋 SQLite로 대신 확인해보겠습니다...")
        
        # SQLite로 대체 확인
        import sqlite3
        try:
            conn = sqlite3.connect('emoai.db')
            cursor = conn.cursor()
            
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='daily_context'")
            schema = cursor.fetchone()
            if schema:
                print("SQLite daily_context 스키마:")
                print(schema[0])
            
            cursor.execute("SELECT day, LENGTH(rolling_summary) as length FROM daily_context WHERE rolling_summary IS NOT NULL ORDER BY length DESC LIMIT 5")
            lengths = cursor.fetchall()
            print(f"\nSQLite rolling_summary 데이터 길이 TOP 5:")
            for day, length in lengths:
                print(f"- {day}: {length}자")
                
            conn.close()
            
        except Exception as sqlite_e:
            print(f"❌ SQLite도 실패: {sqlite_e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(check_db())
