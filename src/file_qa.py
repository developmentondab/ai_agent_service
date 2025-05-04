import os
import json
import numpy as np
import faiss
import tiktoken
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import magic
import PyPDF2
import docx2txt
from openai import OpenAI
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from .database.models import Document
from .instructions import Instructions

class FileQA:
    def __init__(self, storage_dir: str = "knowledge_base"):
        load_dotenv()
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.storage_dir = storage_dir
        self.documents_dir = os.path.join(storage_dir, "documents")
        self.indices_dir = os.path.join(storage_dir, "indices")
        self.metadata_path = os.path.join(storage_dir, "metadata.json")
        self.model = os.getenv("MODEL_NAME", "gpt-4-turbo-preview")
        
        # Create necessary directories
        os.makedirs(self.documents_dir, exist_ok=True)
        os.makedirs(self.indices_dir, exist_ok=True)
        
        # Initialize metadata
        self.load_metadata()
        
    def get_index_path(self, chatbot_id: int) -> str:
        """Get the path for a chatbot's FAISS index"""
        return os.path.join(self.indices_dir, f"index_{chatbot_id}.bin")
        
    def get_or_create_index(self, chatbot_id: int) -> faiss.Index:
        """Get existing index or create a new one for a chatbot"""
        index_path = self.get_index_path(chatbot_id)
        dimension = 1536  # OpenAI embedding dimension
        
        if os.path.exists(index_path):
            return faiss.read_index(index_path)
        else:
            index = faiss.IndexFlatL2(dimension)
            faiss.write_index(index, index_path)
            return index
            
    def load_metadata(self):
        """Load document metadata"""
        if os.path.exists(self.metadata_path):
            with open(self.metadata_path, 'r') as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {}
            
    def save_metadata(self):
        """Save document metadata"""
        with open(self.metadata_path, 'w') as f:
            json.dump(self.metadata, f)
            
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for text using OpenAI API"""
        response = self.client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    
    def extract_text_from_file(self, file_path: str) -> str:
        """Extract text from various file formats"""
        mime_type = magic.from_file(file_path, mime=True)
        
        if mime_type == 'application/pdf':
            text = ""
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            return text
            
        elif mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            return docx2txt.process(file_path)
            
        elif mime_type.startswith('text/'):
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
                
        else:
            raise ValueError(f"Unsupported file type: {mime_type}")
    
    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
        """Split text into overlapping chunks"""
        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = start + chunk_size
            if end > text_len:
                end = text_len
            chunk = text[start:end]
            chunks.append(chunk)
            if text_len == end:
                start = end
            else:
                start = end - overlap
            
        return chunks
    
    def add_document(self, file_path: str, document_id: Optional[str] = None, db: Optional[Session] = None, chatbot_id: Optional[int] = None) -> str:
        """Process and add a document to the knowledge base"""
        if chatbot_id is None:
            raise ValueError("chatbot_id is required")
            
        # Generate document ID if not provided
        if document_id is None:
            document_id = f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
        # Extract text from document
        text = self.extract_text_from_file(file_path)
        chunks = self.chunk_text(text)
        
        # Get embeddings for chunks
        chunk_embeddings = []
        for chunk in chunks:
            embedding = self.get_embedding(chunk)
            chunk_embeddings.append(embedding)
            
        # Get or create index for this chatbot
        index = self.get_or_create_index(chatbot_id)
        
        # Add to FAISS index
        embeddings_array = np.array(chunk_embeddings).astype('float32')
        index.add(embeddings_array)
        
        # Save document metadata
        self.metadata[document_id] = {
            'file_path': file_path,
            'chunks': chunks,
            'num_vectors': len(chunks),
            'start_idx': index.ntotal - len(chunks),
            'added_at': datetime.now().isoformat(),
            'chatbot_id': chatbot_id
        }
        
        # Save updated index and metadata
        faiss.write_index(index, self.get_index_path(chatbot_id))
        self.save_metadata()
        
        # Store document in database if db session is provided
        if db is not None:
            document = Document(
                document_id=document_id,
                file_name=os.path.basename(file_path),
                file_path=file_path,
                chatbot_id=chatbot_id
            )
            db.add(document)
            db.commit()
        
        return document_id
    
    def search(self, query: str, k: int = 5, document_ids: Optional[List[str]] = None, chatbot_id: Optional[int] = None) -> List[Dict]:
        """Search the knowledge base for relevant chunks"""
        if chatbot_id is None:
            raise ValueError("chatbot_id is required")
            
        # Get query embedding
        query_embedding = self.get_embedding(query)
        
        # Get chatbot's index
        index = self.get_or_create_index(chatbot_id)
        
        # Search in FAISS index
        D, I = index.search(np.array([query_embedding]).astype('float32'), k)
        
        results = []
        for score, idx in zip(D[0], I[0]):
            # Find which document this chunk belongs to
            for doc_id, meta in self.metadata.items():
                if meta['chatbot_id'] != chatbot_id:
                    continue
                    
                if meta['start_idx'] <= idx < meta['start_idx'] + meta['num_vectors']:
                    # Skip if document_ids is specified and this document is not in the list
                    if document_ids is not None and doc_id not in document_ids:
                        continue
                        
                    chunk_idx = idx - meta['start_idx']
                    results.append({
                        'document_id': doc_id,
                        'chunk': meta['chunks'][chunk_idx],
                        'score': float(score),
                        'file_path': meta['file_path']
                    })
                    break
                    
        return results
    
    def query_knowledge_base(self, query: str, k: int = 5, document_ids: Optional[List[str]] = None, chatbot_id: Optional[int] = None) -> str:
        """Query the knowledge base and generate a response using GPT"""
        # Search for relevant chunks
        search_results = self.search(query, k=k, document_ids=document_ids, chatbot_id=chatbot_id)
        
        if not search_results:
            return "No relevant information found in the knowledge base."
            
        # Prepare context from search results
        context = "\n\n".join([f"Context {i+1}:\n{result['chunk']}" 
                              for i, result in enumerate(search_results)])
                              
        # Prepare messages for GPT
        messages = [
            {"role": "system", "content": f"{Instructions.get_knowledge_base_instructions()}"},
            {"role": "user", "content": f"Using the following context, answer this question: {query}\n\nContext:\n{context}"}
        ]
        
        # Get response from GPT
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        
        return response.choices[0].message.content 