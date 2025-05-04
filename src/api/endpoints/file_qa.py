from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import shutil
import os

from ...file_qa import FileQA
from ...database import get_db, Document
from ...auth import get_current_user
from ...database.adapters.sqlalchemy_adapter import SQLAlchemyAdapter

router = APIRouter()

class KnowledgeBaseQuery(BaseModel):
    query: str
    k: int = 5
    # document_ids: Optional[List[str]] = None
    use_knowledge_base: bool = True
    chatbot_id: int

@router.post("/knowledge-base/upload")
async def upload_document(
    files: List[UploadFile],
    chatbot_id: Optional[int] = Form(None),
    db: SQLAlchemyAdapter = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Upload documents to the knowledge base"""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
        
    if chatbot_id is None:
        raise HTTPException(status_code=400, detail="chatbot_id is required")
        
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
                    chatbot_id=chatbot_id
                )
                document_ids.append(document["document_id"])
            except Exception as e:
                print(f"Error processing file {file.filename}: {str(e)}")
                continue

    return {
        "status": "success",
        "document_ids": document_ids,
        "total_files_processed": len(document_ids)
    }

@router.post("/knowledge-base/query")
async def query_knowledge_base(
    request: KnowledgeBaseQuery,
    db: SQLAlchemyAdapter = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Query the knowledge base"""
    file_qa = FileQA()
    
    # Get chatbot configuration
    chatbot = await db.get_chatbot(request.chatbot_id)
    if not chatbot:
        raise HTTPException(status_code=404, detail=f"Chatbot with ID {request.chatbot_id} not found")
            
    # Get document IDs
    documents = await db.list_documents(request.chatbot_id)
    if documents:        
        document_ids = [doc["document_id"] for doc in documents]

    else:        
        raise HTTPException(status_code=404, detail="No documents found for this chatbot")
    
    # Query the knowledge base
    response = file_qa.query_knowledge_base(
        query=request.query,
        k=request.k,
        document_ids=document_ids,
        chatbot_id=request.chatbot_id
    )
    
    return {
        "status": "success",
        "response": response
    }

@router.get("/knowledge-base/documents")
async def list_documents(
    chatbot_id: Optional[int] = None,
    db: SQLAlchemyAdapter = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List all documents in the knowledge base"""    
    print(chatbot_id)
    documents = await db.list_documents(chatbot_id)
    if not documents:    
        raise HTTPException(status_code=404, detail="No documents found for this chatbot")
    
    return {
        "status": "success",
        "documents": [
            {
                "id": doc["document_id"],
                "file_name": doc["file_name"],
                "chatbot_id": doc["chatbot_id"],
                "created_at": doc["created_at"]
            }
            for doc in documents
        ]
    } 