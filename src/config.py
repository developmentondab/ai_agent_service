from typing import Dict, Optional
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from pydantic_settings import BaseSettings
from pathlib import Path

load_dotenv()

class DatabaseConfig(BaseModel):
    """Database configuration settings"""
    database_type: str = os.getenv("DATABASE_TYPE", "mysql")  # "mysql" or "mongodb"
    database_url: str = os.getenv("DATABASE_URL", "mysql+aiomysql://user:password@localhost/custom_gpt")
    database_name: str = os.getenv("DATABASE_NAME", "custom_gptt")
    # MySQL specific settings
    echo: bool = bool(os.getenv("DB_ECHO", False))
    pool_size: int = int(os.getenv("DB_POOL_SIZE", "5"))
    max_overflow: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    pool_timeout: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    pool_recycle: int = int(os.getenv("DB_POOL_RECYCLE", "3600"))

class APIConfig(BaseModel):
    """API configuration settings"""
    host: str = os.getenv("API_HOST", "127.0.0.1")
    port: int = int(os.getenv("API_PORT", "8000"))
    debug: bool = bool(os.getenv("API_DEBUG", False))
    cors_origins: list = os.getenv("CORS_ORIGINS", "*").split(",")

class KnowledgeBaseConfig(BaseModel):
    """Knowledge base configuration settings"""
    storage_dir: str = os.getenv("KB_STORAGE_DIR", "knowledge_base")
    chunk_size: int = int(os.getenv("KB_CHUNK_SIZE", "1000"))
    chunk_overlap: int = int(os.getenv("KB_CHUNK_OVERLAP", "100"))
    search_k: int = int(os.getenv("KB_SEARCH_K", "5"))

class StorageConfig(BaseModel):
    """Storage configuration settings"""
    upload_dir: str = os.getenv("UPLOAD_DIR", str(Path(__file__).parent.parent / "uploads"))

class Config(BaseModel):
    """Main configuration class"""
    database: DatabaseConfig = DatabaseConfig()
    api: APIConfig = APIConfig()
    knowledge_base: KnowledgeBaseConfig = KnowledgeBaseConfig()
    storage: StorageConfig = StorageConfig()
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    model_name: str = os.getenv("MODEL_NAME", "gpt-4-turbo-preview")
    max_tokens: int = int(os.getenv("MAX_TOKENS", "2000"))
    temperature: float = float(os.getenv("TEMPERATURE", "0.7"))

    class Config:
        env_file = ".env"

def get_config() -> Config:
    """Get the application configuration"""
    return Config() 