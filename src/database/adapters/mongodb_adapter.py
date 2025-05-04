from typing import List, Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import uuid

from .base import DatabaseAdapter
from ...config import get_config

class MongoDBAdapter(DatabaseAdapter):
    def __init__(self):
        self.config = get_config()
        self.client = None
        self.db = None

    async def connect(self) -> None:
        """Connect to the MongoDB database"""
        self.client = AsyncIOMotorClient(self.config.database.database_url)
        self.db = self.client[self.config.database.database_name]

    async def disconnect(self) -> None:
        """Disconnect from the MongoDB database"""
        if self.client:
            self.client.close()

    async def create_chatbot(self, name: str, system_instructions: str, description: Optional[str] = None, enable_web_browsing: Optional[bool] = False) -> Dict[str, Any]:
        """Create a new chatbot"""
        chatbot = {
            "name": name,
            "system_instructions": system_instructions,
            "description": description,
            "enable_web_browsing": enable_web_browsing,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "is_active": True
        }
        result = await self.db.chatbots.insert_one(chatbot)
        chatbot["id"] = str(result.inserted_id)
        return chatbot

    async def get_chatbot(self, chatbot_id: str) -> Optional[Dict[str, Any]]:
        """Get a chatbot by ID"""
        chatbot = await self.db.chatbots.find_one({"_id": chatbot_id})
        if chatbot:
            chatbot["id"] = str(chatbot["_id"])
            del chatbot["_id"]
        return chatbot

    async def list_chatbots(self) -> List[Dict[str, Any]]:
        """List all chatbots"""
        chatbots = []
        async for chatbot in self.db.chatbots.find():
            chatbot["id"] = str(chatbot["_id"])
            del chatbot["_id"]
            chatbots.append(chatbot)
        return chatbots

    async def create_chat_session(self, chatbot_id: str, session_name: Optional[str] = None) -> Dict[str, Any]:
        """Create a new chat session"""
        session = {
            "chatbot_id": chatbot_id,
            "session_name": session_name,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        result = await self.db.chat_sessions.insert_one(session)
        session["id"] = str(result.inserted_id)
        return session

    async def get_chat_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a chat session by ID"""
        session = await self.db.chat_sessions.find_one({"_id": session_id})
        if session:
            session["id"] = str(session["_id"])
            del session["_id"]
        return session

    async def list_chat_sessions(self, chatbot_id: str) -> List[Dict[str, Any]]:
        """List all chat sessions for a chatbot"""
        sessions = []
        async for session in self.db.chat_sessions.find({"chatbot_id": chatbot_id}):
            session["id"] = str(session["_id"])
            del session["_id"]
            sessions.append(session)
        return sessions

    async def create_chat_message(self, session_id: str, role: str, content: str) -> Dict[str, Any]:
        """Create a new chat message"""
        message = {
            "session_id": session_id,
            "role": role,
            "content": content,
            "created_at": datetime.utcnow()
        }
        result = await self.db.chat_messages.insert_one(message)
        message["id"] = str(result.inserted_id)
        return message

    async def get_chat_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all messages for a session"""
        messages = []
        async for message in self.db.chat_messages.find({"session_id": session_id}):
            message["id"] = str(message["_id"])
            del message["_id"]
            messages.append(message)
        return messages

    async def create_document(self, file_name: str, file_path: str, chatbot_id: str) -> Dict[str, Any]:
        """Create a new document"""
        document = {
            "document_id": str(uuid.uuid4()),
            "chatbot_id": chatbot_id,
            "file_name": file_name,
            "file_path": file_path,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        result = await self.db.documents.insert_one(document)
        document["id"] = str(result.inserted_id)
        return document

    async def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get a document by ID"""
        document = await self.db.documents.find_one({"document_id": document_id})
        if document:
            document["id"] = str(document["_id"])
            del document["_id"]
        return document

    async def list_documents(self, chatbot_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all documents"""
        query = {} if chatbot_id is None else {"chatbot_id": chatbot_id}
        documents = []
        async for document in self.db.documents.find(query):
            document["id"] = str(document["_id"])
            del document["_id"]
            documents.append(document)
        return documents

    async def update_chatbot(self, chatbot_id: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Update a chatbot"""
        kwargs["updated_at"] = datetime.utcnow()
        result = await self.db.chatbots.find_one_and_update(
            {"_id": chatbot_id},
            {"$set": kwargs},
            return_document=True
        )
        if result:
            result["id"] = str(result["_id"])
            del result["_id"]
        return result

    async def delete_chatbot(self, chatbot_id: str) -> bool:
        """Delete a chatbot"""
        result = await self.db.chatbots.delete_one({"_id": chatbot_id})
        return result.deleted_count > 0

    async def delete_document(self, document_id: str) -> bool:
        """Delete a document"""
        result = await self.db.documents.delete_one({"document_id": document_id})
        return result.deleted_count > 0 