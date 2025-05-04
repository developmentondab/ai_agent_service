from typing import List, Optional, Dict, Any
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, update, delete
from datetime import datetime

from .base import DatabaseAdapter
from ..models import ChatBot, ChatSession, ChatMessage, Document
from ...config import get_config

class SQLAlchemyAdapter(DatabaseAdapter):
    def __init__(self):
        self.config = get_config()
        self.engine = None
        self.session_factory = None
        self.session = None

    async def connect(self) -> None:
        """Connect to the database"""
        self.engine = create_async_engine(
            self.config.database.database_url,
            echo=self.config.database.echo,
            pool_size=self.config.database.pool_size,
            max_overflow=self.config.database.max_overflow,
            pool_timeout=self.config.database.pool_timeout,
            pool_recycle=self.config.database.pool_recycle
        )
        self.session_factory = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        self.session = self.session_factory()

    async def disconnect(self) -> None:
        """Disconnect from the database"""
        if self.session:
            await self.session.close()
        if self.engine:
            await self.engine.dispose()

    async def create_chatbot(self, name: str, system_instructions: str, description: Optional[str] = None, enable_web_browsing: Optional[bool] = False) -> Dict[str, Any]:
        """Create a new chatbot""" 
        chatbot = ChatBot(
            name=name,
            system_instructions=system_instructions,
            description=description,
            enable_web_browsing=enable_web_browsing
        )
        self.session.add(chatbot)
        await self.session.commit()
        await self.session.refresh(chatbot)
        return chatbot.to_dict()

    async def get_chatbot(self, chatbot_id: int) -> Optional[Dict[str, Any]]:
        """Get a chatbot by ID"""
        result = await self.session.execute(
            select(ChatBot).where(ChatBot.id == chatbot_id)
        )
        chatbot = result.scalar_one_or_none()
        return chatbot.to_dict() if chatbot else None

    async def list_chatbots(self) -> List[Dict]:
        """List all chatbots"""
        result = await self.session.execute(select(ChatBot))
        chatbots = result.scalars().all()
        return [chatbot.to_dict() for chatbot in chatbots]

    async def create_chat_session(self, chatbot_id: int, session_name: Optional[str] = None) -> Dict[str, Any]:
        """Create a new chat session"""
        session = ChatSession(
            chatbot_id=chatbot_id,
            session_name=session_name
        )
        self.session.add(session)
        await self.session.commit()
        await self.session.refresh(session)
        return session.to_dict()

    async def get_chat_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Get a chat session by ID"""
        result = await self.session.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        return session.to_dict() if session else None

    async def list_chat_sessions(self, chatbot_id: int) -> List[Dict[str, Any]]:
        """List all chat sessions for a chatbot"""
        result = await self.session.execute(
            select(ChatSession).where(ChatSession.chatbot_id == chatbot_id)
        )
        sessions = result.scalars().all()
        return [session.to_dict() for session in sessions]

    async def create_chat_message(self, session_id: int, role: str, content: str) -> Dict[str, Any]:
        """Create a new chat message"""
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content
        )
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        return message.to_dict()

    async def get_chat_messages(self, session_id: int) -> List[Dict[str, Any]]:
        """Get all messages for a session"""
        result = await self.session.execute(
            select(ChatMessage).where(ChatMessage.session_id == session_id)
        )
        messages = result.scalars().all()
        return [message.to_dict() for message in messages]

    async def create_document(self, file_name: str, file_path: str, chatbot_id: int) -> Dict[str, Any]:
        """Create a new document"""
        document = Document(
            file_name=file_name,
            file_path=file_path,
            chatbot_id=chatbot_id
        )
        self.session.add(document)
        await self.session.commit()
        await self.session.refresh(document)
        return document.to_dict()

    async def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get a document by ID"""
        result = await self.session.execute(
            select(Document).where(Document.document_id == document_id)
        )
        document = result.scalar_one_or_none()
        return document.to_dict() if document else None

    async def list_documents(self, chatbot_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """List all documents"""
        query = select(Document)
        if chatbot_id is not None:
            query = query.where(Document.chatbot_id == chatbot_id)
        result = await self.session.execute(query)
        documents = result.scalars().all()
        return [document.to_dict() for document in documents]

    async def update_chatbot(self, chatbot_id: int, **kwargs) -> Optional[Dict[str, Any]]:
        """Update a chatbot"""
        stmt = (
            update(ChatBot)
            .where(ChatBot.id == chatbot_id)
            .values(**kwargs)
            .returning(ChatBot)
        )
        result = await self.session.execute(stmt)
        chatbot = result.scalar_one_or_none()
        if chatbot:
            await self.session.commit()
            return chatbot.to_dict()
        return None

    async def delete_chatbot(self, chatbot_id: int) -> bool:
        """Delete a chatbot"""
        stmt = delete(ChatBot).where(ChatBot.id == chatbot_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def delete_document(self, document_id: str) -> bool:
        """Delete a document"""
        stmt = delete(Document).where(Document.document_id == document_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0 