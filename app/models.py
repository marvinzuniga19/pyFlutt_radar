from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Fuente(Base):
    __tablename__ = "fuentes"

    id: Mapped[int] = mapped_column(primary_key=True)

    nombre: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    url: Mapped[str] = mapped_column(
        String(500),
        unique=True,
        nullable=False,
    )

    categoria: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    activa: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    ultima_revision: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )

    publicaciones: Mapped[list["Publicacion"]] = relationship(
        back_populates="fuente",
        cascade="all, delete-orphan",
    )


class Publicacion(Base):
    __tablename__ = "publicaciones"

    id: Mapped[int] = mapped_column(primary_key=True)

    titulo: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
    )

    url: Mapped[str] = mapped_column(
        String(700),
        unique=True,
        nullable=False,
    )

    resumen: Mapped[str] = mapped_column(
        Text,
        default="",
        nullable=False,
    )

    fecha_publicacion: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )

    fecha_descubrimiento: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    enviada_telegram: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    fecha_envio: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )

    fuente_id: Mapped[int] = mapped_column(
        ForeignKey("fuentes.id"),
        nullable=False,
    )

    fuente: Mapped["Fuente"] = relationship(
        back_populates="publicaciones",
    )