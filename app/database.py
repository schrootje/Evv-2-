import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Railway mounts a persistent volume at /data when configured
_db_dir = os.environ.get("DB_DIR", ".")
os.makedirs(_db_dir, exist_ok=True)
SQLALCHEMY_DATABASE_URL = f"sqlite:///{_db_dir}/training.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
