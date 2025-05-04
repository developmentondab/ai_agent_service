from .models import ChatBot, ChatSession, ChatMessage, Document
from .factory import DatabaseFactory
from fastapi import Depends
from typing import AsyncGenerator

# Create a single instance of the adapter using the factory
AdapterClass = DatabaseFactory.get_adapter()
db_adapter = AdapterClass()

async def get_db() -> AsyncGenerator[AdapterClass, None]:
    """Dependency for getting database session"""
    try:
        await db_adapter.connect()
        yield db_adapter
    finally:
        await db_adapter.disconnect()

__all__ = ['ChatBot', 'ChatSession', 'ChatMessage', 'Document', 'get_db', 'db_adapter'] 