"""데이터베이스 연결 및 테이블 정의"""
from sqlmodel import SQLModel, Field, create_engine, Session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Text
from typing import Optional, Dict, Any
from datetime import datetime
import json
from pathlib import Path


class Atom(SQLModel, table=True):
    """원자 단위 대화 기록"""
    __tablename__ = "atoms"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    ts: datetime = Field(default_factory=datetime.utcnow)
    day: str  # YYYY-MM-DD
    author: str  # user/agent
    text_raw: str = Field(sa_column=Column(Text))
    text_final: Optional[str] = Field(default=None, sa_column=Column(Text))
    ctx: Optional[str] = Field(default=None, sa_column=Column(Text))  # JSON
    affect: Optional[str] = Field(default=None, sa_column=Column(Text))  # JSON
    style: Optional[str] = Field(default=None, sa_column=Column(Text))  # JSON
    levers: Optional[str] = Field(default=None, sa_column=Column(Text))  # JSON
    salience: float = 0.5
    episode_id: Optional[int] = None
    

class Event(SQLModel, table=True):
    """이벤트 기록"""
    __tablename__ = "events"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    ts: datetime = Field(default_factory=datetime.utcnow)
    day: str
    type: str
    payload: Optional[str] = Field(default=None, sa_column=Column(Text))  # JSON
    

class Episode(SQLModel, table=True):
    """에피소드"""
    __tablename__ = "episodes"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    day: str
    time_start: datetime
    time_end: Optional[datetime] = None
    title: Optional[str] = None
    nodes: Optional[str] = Field(default=None, sa_column=Column(Text))  # JSON
    edges: Optional[str] = Field(default=None, sa_column=Column(Text))  # JSON
    

class DailyContext(SQLModel, table=True):
    """일일 컨텍스트"""
    __tablename__ = "daily_context"
    
    day: str = Field(primary_key=True)
    session_id: str
    rolling_summary: Optional[str] = Field(default=None, sa_column=Column(Text))
    highlights: Optional[str] = Field(default=None, sa_column=Column(Text))  # JSON
    pinned_facts: Optional[str] = Field(default=None, sa_column=Column(Text))  # JSON
    style_snapshot: Optional[str] = Field(default=None, sa_column=Column(Text))  # JSON
    

class Semantic(SQLModel, table=True):
    """시맨틱 메모리"""
    __tablename__ = "semantic"
    
    key: str = Field(primary_key=True)
    value: Optional[str] = Field(default=None, sa_column=Column(Text))  # JSON
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    

class Ledger(SQLModel, table=True):
    """영향력 원장"""
    __tablename__ = "ledger"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    ts: datetime = Field(default_factory=datetime.utcnow)
    session_id: str
    operators: Optional[str] = Field(default=None, sa_column=Column(Text))  # JSON
    user_reaction: Optional[str] = Field(default=None, sa_column=Column(Text))  # JSON
    reward_proxy: float = 0.0


# 데이터베이스 엔진
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 환경변수에서 MySQL 설정 가져오기
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "emoai")

# MySQL URL 구성 (aiomysql 사용)
DATABASE_URL = f"mysql+aiomysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
async_engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
    pool_recycle=3600
)

AsyncSessionLocal = sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def init_db():
    """데이터베이스 초기화"""
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        

async def get_session() -> AsyncSession:
    """세션 생성"""
    async with AsyncSessionLocal() as session:
        yield session
