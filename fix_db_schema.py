#!/usr/bin/env python3
"""데이터베이스 스키마 수정 스크립트"""
import os
import sys
sys.path.append('.')

from dotenv import load_dotenv
load_dotenv()

async def fix_db_schema():
    try:
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
            # rolling_summary 컬럼을 TEXT로 변경
            print("🔧 rolling_summary 컬럼을 VARCHAR(255) → TEXT로 변경 중...")
            cursor.execute("""
                ALTER TABLE daily_context 
                MODIFY COLUMN rolling_summary TEXT COLLATE utf8mb4_unicode_ci
            """)
            
            # highlights도 길어질 수 있으니 함께 변경
            print("🔧 highlights 컬럼도 VARCHAR(255) → TEXT로 변경 중...")
            cursor.execute("""
                ALTER TABLE daily_context 
                MODIFY COLUMN highlights TEXT COLLATE utf8mb4_unicode_ci
            """)
            
            # pinned_facts도 함께 변경
            print("🔧 pinned_facts 컬럼도 VARCHAR(255) → TEXT로 변경 중...")
            cursor.execute("""
                ALTER TABLE daily_context 
                MODIFY COLUMN pinned_facts TEXT COLLATE utf8mb4_unicode_ci
            """)
            
            connection.commit()
            print("✅ 스키마 수정 완료!")
            
            # 변경된 스키마 확인
            cursor.execute("SHOW CREATE TABLE daily_context")
            result = cursor.fetchone()
            print("\n📋 수정된 daily_context 테이블 스키마:")
            print(result[1])
        
        connection.close()
        
    except Exception as e:
        print(f"❌ 스키마 수정 실패: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(fix_db_schema())
