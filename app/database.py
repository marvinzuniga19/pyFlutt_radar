import os
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


DATABASE_URL = os.getenv("DATABASE_URL", "")

# Si Render proporciona una URL con "postgres://",
# hay que cambiarla a "postgresql://" para SQLAlchemy.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://",
        "postgresql://",
        1,
    )

# Si no hay variable de entorno, usar SQLite local.
if not DATABASE_URL:
    Path("data").mkdir(exist_ok=True)
    DATABASE_URL = "sqlite:///./data/radar.db"


class Base(DeclarativeBase):
    pass


# check_same_thread solo aplica para SQLite.
connect_args = {}

if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


def obtener_base_datos() -> Generator[Session, None, None]:
    base_datos = SessionLocal()

    try:
        yield base_datos
    finally:
        base_datos.close()