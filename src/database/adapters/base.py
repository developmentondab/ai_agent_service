from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

class DatabaseAdapter(ABC):
    """Base interface for database adapters"""
    
    @abstractmethod
    async def connect(self) -> None:
        """Connect to the database"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the database"""
        pass
    
    @abstractmethod
    async def create_chatbot(self, name: str, system_instructions: str, description: Optional[str] = None) -> Dict[str, Any]:
        """Create a new chatbot"""
        pass
    
    @abstractmethod
    async def get_chatbot(self, chatbot_id: int) -> Optional[Dict[str, Any]]:
        """Get a chatbot by ID"""
        pass
    
    @abstractmethod
    async def list_chatbots(self) -> List[Dict[str, Any]]:
        """List all chatbots"""
        pass
    
    @abstractmethod
    async def create_chat_session(self, chatbot_id: int, session_name: Optional[str] = None) -> Dict[str, Any]:
        """Create a new chat session"""
        pass
    
    @abstractmethod
    async def get_chat_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Get a chat session by ID"""
        pass
    
    @abstractmethod
    async def list_chat_sessions(self, chatbot_id: int) -> List[Dict[str, Any]]:
        """List all chat sessions for a chatbot"""
        pass
    
    @abstractmethod
    async def create_chat_message(self, session_id: int, role: str, content: str) -> Dict[str, Any]:
        """Create a new chat message"""
        pass
    
    @abstractmethod
    async def get_chat_messages(self, session_id: int) -> List[Dict[str, Any]]:
        """Get all messages for a session"""
        pass
    
    @abstractmethod
    async def create_document(self, file_name: str, file_path: str, chatbot_id: int) -> Dict[str, Any]:
        """Create a new document"""
        pass
    
    @abstractmethod
    async def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get a document by ID"""
        pass
    
    @abstractmethod
    async def list_documents(self, chatbot_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """List all documents"""
        pass
    
    @abstractmethod
    async def update_chatbot(self, chatbot_id: int, **kwargs) -> Optional[Dict[str, Any]]:
        """Update a chatbot"""
        pass
    
    @abstractmethod
    async def delete_chatbot(self, chatbot_id: int) -> bool:
        """Delete a chatbot"""
        pass
    
    @abstractmethod
    async def delete_document(self, document_id: str) -> bool:
        """Delete a document"""
        pass 