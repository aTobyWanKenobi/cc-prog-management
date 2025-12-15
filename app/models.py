from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Unita(Base):
    __tablename__ = "unita"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(unique=True, index=True)
    sottocampo: Mapped[str] = mapped_column()

    pattuglie: Mapped[list["Pattuglia"]] = relationship(back_populates="unita")


class Pattuglia(Base):
    __tablename__ = "pattuglie"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(unique=True, index=True)
    capo_pattuglia: Mapped[str] = mapped_column()
    unita_id: Mapped[int] = mapped_column(ForeignKey("unita.id"))

    current_score: Mapped[int] = mapped_column(default=0)

    unita: Mapped["Unita"] = relationship(back_populates="pattuglie")
    completions: Mapped[list["Completion"]] = relationship(back_populates="pattuglia")


class Challenge(Base):
    __tablename__ = "challenges"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(unique=True, index=True)
    description: Mapped[str] = mapped_column()
    points: Mapped[int] = mapped_column()
    is_fungo: Mapped[bool] = mapped_column(default=False)
    reward_tokens: Mapped[int] = mapped_column(default=0)

    completions: Mapped[list["Completion"]] = relationship(back_populates="challenge")


class Completion(Base):
    __tablename__ = "completions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    pattuglia_id: Mapped[int] = mapped_column(ForeignKey("pattuglie.id"))
    challenge_id: Mapped[int] = mapped_column(ForeignKey("challenges.id"))
    timestamp: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    pattuglia: Mapped["Pattuglia"] = relationship(back_populates="completions")
    challenge: Mapped["Challenge"] = relationship(back_populates="completions")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(unique=True, index=True)
    password_hash: Mapped[str] = mapped_column()
    role: Mapped[str] = mapped_column()  # 'unit', 'tech', 'admin'
    unita_id: Mapped[Optional[int]] = mapped_column(ForeignKey("unita.id"), nullable=True)

    unita: Mapped[Optional["Unita"]] = relationship()


class Terreno(Base):
    __tablename__ = "terreni"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(unique=True, index=True)
    tags: Mapped[str] = mapped_column()  # Comma-separated tags
    center_lat: Mapped[str] = mapped_column()
    center_lon: Mapped[str] = mapped_column()
    polygon: Mapped[str] = mapped_column()  # JSON string of coordinates

    prenotazioni: Mapped[list["Prenotazione"]] = relationship(back_populates="terreno")


class Prenotazione(Base):
    __tablename__ = "prenotazioni"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    terreno_id: Mapped[int] = mapped_column(ForeignKey("terreni.id"))
    unita_id: Mapped[int] = mapped_column(ForeignKey("unita.id"))
    start_time: Mapped[datetime] = mapped_column()
    end_time: Mapped[datetime] = mapped_column()
    duration: Mapped[int] = mapped_column()  # Hours (1-4)
    status: Mapped[str] = mapped_column(default="PENDING")  # PENDING, APPROVED

    terreno: Mapped["Terreno"] = relationship(back_populates="prenotazioni")
    unita: Mapped["Unita"] = relationship()

