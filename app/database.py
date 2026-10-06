import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL")

# SQL 로그(logs/app.log)에 바인딩 파라미터(비밀번호 해시 등)가 남지 않도록 기본은 숨김.
# 파라미터까지 보려면 SQL_LOG_PARAMS=true (개발 중 디버깅용)
engine = create_engine(
    DATABASE_URL,
    hide_parameters=os.getenv("SQL_LOG_PARAMS", "false").lower() != "true",
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
