from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, LogExecution

DATABASE_URL = "sqlite:///./collecteur.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine) 