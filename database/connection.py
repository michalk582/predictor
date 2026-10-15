from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.config import DATABASE_URI

engine = create_engine(DATABASE_URI)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db_connection():
    return engine