from typing import Dict, List, Optional, AsyncGenerator
from openai import OpenAI
from dotenv import load_dotenv
from .database.adapters.sqlalchemy_adapter import SQLAlchemyAdapter
from .database.models import ChatBot, ChatSession, ChatMessage
import os
from .instructions import Instructions

class Agent:
    def __init__(self, db: SQLAlchemyAdapter):
        load_dotenv()
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("MODEL_NAME", "gpt-4-turbo-preview")
        self.max_tokens = int(os.getenv("MAX_TOKENS", "2000"))
        self.temperature = float(os.getenv("TEMPERATURE", "0.7"))
        self.db = db

    async def get_or_create_session(self, chatbot_id: int, session_name: Optional[str] = None) -> Dict:
        """Get existing session or create a new one"""
        if session_name:
            sessions = await self.db.list_chat_sessions(chatbot_id)
            session = next((s for s in sessions if s["session_name"] == session_name), None)
            if session:
                return session

        # Create new session
        session = await self.db.create_chat_session(chatbot_id, session_name)
        return session

    async def generate_session_name(self, query: str) -> str:
        """Create session name from the user given question"""
         # Use the API to generate a concise session name
        name_prompt = f"""
        {Instructions.session_name_instructions()}
        
        Question: {query}
        """
        
        name_messages = [
            {"role": "system", "content": "You are a helpful assistant that generates concise, objective names for questions."},
            {"role": "user", "content": name_prompt}
        ]
        
        name_response = await self.create_session_name(
            messages=name_messages,
            temperature=0.3,  # Lower temperature for more consistent naming
            max_tokens=20
        )
        
        if name_response["status"] == "success":
            # Clean the generated name
            topic = name_response["content"].strip().lower()
            topic = "".join(c if c.isalnum() or c.isspace() else "_" for c in topic)
            topic = topic.replace(" ", "_")            
            session_name = f"{topic}"

        else:
            # Fallback to simple name generation if API fails
            words = query.lower().split()
            topic = "_".join(words[:3]) if len(words) > 3 else "_".join(words)
            topic = "".join(c if c.isalnum() or c.isspace() else "_" for c in topic)
            topic = topic.replace(" ", "_")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            session_name = f"{topic}_{timestamp}"
        return session_name

    async def create_chat_completion(
        self,
        messages: List[Dict[str, str]],
        chatbot_id: int,
        session_name: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict:
        """Create a chat completion using the OpenAI API with database-stored instructions"""
        try:
            # Get chatbot configuration
            chatbot = await self.db.get_chatbot(chatbot_id)
            if not chatbot:
                return {
                    "status": "error",
                    "error": f"Chatbot with ID {chatbot_id} not found"
                }

            # Get or create chat session
            session = await self.get_or_create_session(chatbot_id, session_name)

            # Add system instructions if not present
            if not any(m.get("role") == "system" for m in messages):
                messages.insert(0, {"role": "system", "content": chatbot["system_instructions"]})

            # Store messages in database
            for message in messages:
                await self.db.create_chat_message(
                    session_id=session["id"],
                    role=message["role"],
                    content=message["content"]
                )

            # Get completion from OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens
            )

            # Store assistant's response
            await self.db.create_chat_message(
                session_id=session["id"],
                role="assistant",
                content=response.choices[0].message.content
            )

            return {
                "status": "success",
                "content": response.choices[0].message.content,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                "session_id": session["id"]
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    async def create_session_name(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict:
        """Create a session name using the OpenAI API with database-stored instructions"""
        try:
            # Get completion from OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens
            )

            return {
                "status": "success",
                "content": response.choices[0].message.content
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    async def create_streaming_chat_completion(
        self,
        messages: List[Dict[str, str]],
        chatbot_id: int,
        session_name: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> AsyncGenerator[Dict, None]:
        """Create a streaming chat completion using the OpenAI API"""
        try:
            # Get chatbot configuration
            chatbot = await self.db.get_chatbot(chatbot_id)
            if not chatbot:
                yield {
                    "status": "error",
                    "error": f"Chatbot with ID {chatbot_id} not found"
                }
                return

            # Get or create chat session
            session = await self.get_or_create_session(chatbot_id, session_name)

            # Add system instructions if not present
            if not any(m.get("role") == "system" for m in messages):
                messages.insert(0, {"role": "system", "content": chatbot["system_instructions"]})

            # Store messages in database
            for message in messages:
                await self.db.create_chat_message(
                    session_id=session["id"],
                    role=message["role"],
                    content=message["content"]
                )

            # Initialize variables for collecting streaming response
            full_response = ""
            
            # Get streaming completion from OpenAI
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                stream=True
            )

            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield {
                        "status": "success",
                        "content": content,
                        "session_id": session["id"]
                    }

            # Store complete response in database
            await self.db.create_chat_message(
                session_id=session["id"],
                role="assistant",
                content=full_response
            )

        except Exception as e:
            yield {
                "status": "error",
                "error": str(e)
            } 