from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Union
from pydantic import BaseModel
from datetime import datetime
import shutil
import os

from ...agent import Agent
from ...instructions import Instructions
from ...file_qa import FileQA
from ...database import get_db, ChatBot, ChatSession, Document, db_adapter
from ...database.adapters.sqlalchemy_adapter import SQLAlchemyAdapter
from ...auth import get_current_user

router = APIRouter()

class ChatRequest(BaseModel):
    query: str
    chatbot_id: int
    session_id: Optional[int] = None
    session_name: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None

class ChatBotCreate(BaseModel):
    name: str
    system_instructions: str
    description: Optional[str] = None
    enable_web_browsing: Optional[bool] = False
    files: Optional[List[UploadFile]] = None

@router.post("/chatbots")
async def create_chatbot(
    name: str = Form(...),
    system_instructions: str = Form(...),
    description: Optional[str] = Form(None),
    enable_web_browsing: Optional[bool] = Form(False),
    files: List[UploadFile] = File(None),
    db: SQLAlchemyAdapter = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new chatbot with custom instructions and optional files"""
    try:
        # Create the chatbot
        chatbot = await db.create_chatbot(
            name=name,
            system_instructions=system_instructions,
            description=description,
            enable_web_browsing=enable_web_browsing
        )

        # Process files if provided
        document_ids = []
        if files:
            # Convert single file to list if needed
            if not isinstance(files, list):
                files = [files]
                
            file_qa = FileQA()
            # Ensure knowledge_base/documents directory exists
            documents_dir = "knowledge_base/documents"
            os.makedirs(documents_dir, exist_ok=True)

            for file in files:
                try:
                    # Create a unique filename to avoid conflicts
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    unique_filename = f"{timestamp}_{file.filename}"
                    file_path = os.path.join(documents_dir, unique_filename)
                    
                    # Save the file
                    with open(file_path, "wb") as buffer:
                        shutil.copyfileobj(file.file, buffer)
                    
                    # Add to knowledge base
                    document = await db.create_document(
                        file_name=file.filename,
                        file_path=file_path,
                        chatbot_id=chatbot["id"]
                    )
                    document_ids.append(document["document_id"])
                except Exception as e:
                    print(f"Error processing file {file.filename}: {str(e)}")
                    continue

        return {
            "status": "success",
            "chatbot": {
                "id": chatbot["id"],
                "name": chatbot["name"],
                "description": chatbot["description"]
            },
            "document_ids": document_ids,
            "total_files_processed": len(document_ids)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/chatbots")
async def list_chatbots(
    chatbot_id: Optional[int] = None,
    db: SQLAlchemyAdapter = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List all available chatbots with their associated documents or get a specific chatbot by ID"""
    try:
        if chatbot_id is not None:
            # Get specific chatbot
            chatbot = await db.get_chatbot(chatbot_id)
            if not chatbot:
                raise HTTPException(status_code=404, detail=f"Chatbot with ID {chatbot_id} not found")
            
            return {
                "status": "success",
                "chatbot": {
                    "id": chatbot["id"],
                    "name": chatbot["name"],
                    "description": chatbot["description"],
                    "system_instructions": chatbot["system_instructions"],
                    "document_ids": [doc["document_id"] for doc in await db.list_documents(chatbot_id)]
                }
            }
        
        # List all chatbots
        chatbots = await db.list_chatbots()
        return {
            "status": "success",
            "chatbots": [
                {
                    "id": bot["id"],
                    "name": bot["name"],
                    "description": bot["description"],
                    "document_ids": [doc["document_id"] for doc in await db.list_documents(bot["id"])]
                }
                for bot in chatbots
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/chatbots/{chatbot_id}/sessions")
async def list_sessions(
    chatbot_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List all chat sessions for a specific chatbot"""
    sessions = await db.list_chat_sessions(chatbot_id)
    return {
        "status": "success",
        "sessions": [
            {
                "id": session["id"],
                "name": session["session_name"],
                "created_at": session["created_at"],
                "last_interaction": session["updated_at"]
            }
            for session in sessions
        ]
    }

@router.get("/chatbots/sessions/{session_id}/messages")
async def list_session_messages(
    session_id: int,
    db: SQLAlchemyAdapter = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List all chat messages for a specific session Id and chatbot ID"""
    try:
        messages = await db.get_chat_messages(session_id)
        return {
            "status": "success",
            "messages": [
                {
                    "id": message["id"],
                    "name": message["session_id"],
                    "content": message["content"],
                    "created_at": message["created_at"],
                    "is_system": True if message["role"] == 'assistant' else False
                }
                for message in messages                
                if message["role"] != "system"
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat/completion")
async def create_chat_completion(
    request: ChatRequest,
    db: SQLAlchemyAdapter = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a chat completion using database-stored instructions and settings"""
    agent = Agent(db)
    
    # Get chatbot configuration
    chatbot = await db.get_chatbot(request.chatbot_id)
    if not chatbot:
        raise HTTPException(status_code=404, detail=f"Chatbot with ID {request.chatbot_id} not found")

    # Generate session name from user's question if not provided
    if not request.session_id:
        request.session_name = await agent.generate_session_name(request.query)

    else:
       session = await db.get_chat_session(request.session_id)
       if not session:
        raise HTTPException(status_code=404, detail=f"Session with ID {request.session_id} not found")

       request.session_name = f"{session['session_name']}"


    # Prepare messages
    messages = [{"role": "user", "content": request.query}]

    # Prepare context based on settings
    context = ""
    
    # Get knowledge base results if chatbot has documents
    documents = await db.list_documents(request.chatbot_id)
    if documents:
        file_qa = FileQA()
        # Search the knowledge base directly
        search_results = file_qa.search(
            query=request.query,
            k=5,
            document_ids=[doc["document_id"] for doc in documents],
            chatbot_id=chatbot["id"]
        )
        if search_results:
            context = "\n\n".join([f"Context {i+1}:\n{result['chunk']}" 
                                 for i, result in enumerate(search_results)])

    # Prepare the final messages with combined instructions
    final_messages = messages.copy()
    
    # Combine system instructions
    combined_instructions = f"""
    {chatbot["system_instructions"]}
    """
    
    # Add web browsing capability if enabled in chatbot settings
    if chatbot.get("enable_web_browsing"):
        combined_instructions = f"""
        {combined_instructions}

        
    {Instructions.get_web_browsing_instructions()}
    """

    # Add custom self-introduction instructions
    combined_instructions = f"""
    {combined_instructions}

    When asked about your identity or who developed you, respond with:
    "I am {chatbot["name"]}, a custom AI assistant created specifically for this application. I am designed to help with {chatbot["description"] if chatbot["description"] else 'various tasks'}."

    Do not mention OpenAI or any other AI development company in your responses.
    """
    
    # Add system message with combined instructions and context
    final_messages.insert(0, {
        "role": "system",
        "content": f"{combined_instructions}\n\nUse the following context to answer the user's question:\n{context}" if context else combined_instructions
    })

    # Get the final response using chatbot's default settings
    response = await agent.create_chat_completion(
        messages=final_messages,
        chatbot_id=request.chatbot_id,
        session_name=request.session_name,
        temperature=request.temperature,
        max_tokens=request.max_tokens
    )
    
    if response["status"] == "error":
        raise HTTPException(status_code=500, detail=response["error"])
        
    return response

@router.post("/chat/completion/stream")
async def create_streaming_chat_completion(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a streaming chat completion"""
    agent = Agent(db)
    
    # Get chatbot configuration
    chatbot = await db.get_chatbot(request.chatbot_id)
    if not chatbot:
        raise HTTPException(status_code=404, detail=f"Chatbot with ID {request.chatbot_id} not found")

    # Prepare messages
    messages = [{"role": "user", "content": request.query}]

    # Add system instructions
    messages.insert(0, {"role": "system", "content": chatbot["system_instructions"]})

    # Create streaming response
    return StreamingResponse(
        agent.create_streaming_chat_completion(
            messages=messages,
            chatbot_id=request.chatbot_id,
            session_name=request.session_name,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        ),
        media_type="text/event-stream"
    ) 