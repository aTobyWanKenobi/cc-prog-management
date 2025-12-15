from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class Unita(Base):
    __tablename__ = "unita"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    sottocampo = Column(String)

    pattuglie = relationship("Pattuglia", back_populates="unita")

class Pattuglia(Base):
    __tablename__ = "pattuglie"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    capo_pattuglia = Column(String)
    unita_id = Column(Integer, ForeignKey("unita.id"))
    
    # Denormalized score for easier sorting, or computed? 
    # Let's compute it or update it on completion to keep reads fast.
    # For simplicity in this stack, we can compute on the fly or update a field.
    # Let's keep a field for easy sorting in the DB.
    current_score = Column(Integer, default=0)

    unita = relationship("Unita", back_populates="pattuglie")
    completions = relationship("Completion", back_populates="pattuglia")

class Challenge(Base):
    __tablename__ = "challenges"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String)
    points = Column(Integer)
    is_fungo = Column(Boolean, default=False)
    reward_tokens = Column(Integer, default=0)

    completions = relationship("Completion", back_populates="challenge")

class Completion(Base):
    __tablename__ = "completions"

    id = Column(Integer, primary_key=True, index=True)
    pattuglia_id = Column(Integer, ForeignKey("pattuglie.id"))
    challenge_id = Column(Integer, ForeignKey("challenges.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)

    pattuglia = relationship("Pattuglia", back_populates="completions")
    challenge = relationship("Challenge", back_populates="completions")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String) # 'unit', 'tech', 'admin'
    unita_id = Column(Integer, ForeignKey("unita.id"), nullable=True)

    unita = relationship("Unita")

class Terreno(Base):
    __tablename__ = "terreni"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    tags = Column(String) # Comma-separated tags: SPORT, CERIMONIA, BOSCO, AC, NOTTURNO
    center_lat = Column(String) # Storing as string to avoid float precision issues if needed, or Float
    center_lon = Column(String)
    polygon = Column(String) # JSON string of coordinates

    prenotazioni = relationship("Prenotazione", back_populates="terreno")

class Prenotazione(Base):
    __tablename__ = "prenotazioni"

    id = Column(Integer, primary_key=True, index=True)
    terreno_id = Column(Integer, ForeignKey("terreni.id"))
    unita_id = Column(Integer, ForeignKey("unita.id"))
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    duration = Column(Integer) # Hours (1-4)
    status = Column(String, default="PENDING") # PENDING, APPROVED

    terreno = relationship("Terreno", back_populates="prenotazioni")
    unita = relationship("Unita")
