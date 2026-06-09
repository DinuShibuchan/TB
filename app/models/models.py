import json
from sqlalchemy import Column, Integer, String, Text, DateTime, func
from sqlalchemy.types import TypeDecorator
from pgvector.sqlalchemy import Vector
from app.db.database import Base

class SafeVector(TypeDecorator):
    impl = Text
    cache_ok = True

    def __init__(self, dimensions):
        super().__init__()
        self.dimensions = dimensions

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(Vector(self.dimensions))
        else:
            return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == 'postgresql':
            return value
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if dialect.name == 'postgresql':
            return value
        return json.loads(value)

class Destination(Base):
    __tablename__ = 'destinations'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(50), nullable=False)  # 'place', 'food', 'stay'
    embedding = Column(SafeVector(384), nullable=False) # 384 dimensions for all-MiniLM-L6-v2

class ChatHistory(Base):
    __tablename__ = 'chat_history'
    
    id = Column(Integer, primary_key=True, index=True)
    query = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
