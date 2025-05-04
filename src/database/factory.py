from typing import Type
from .adapters.base import DatabaseAdapter
from .adapters.sqlalchemy_adapter import SQLAlchemyAdapter
from .adapters.mongodb_adapter import MongoDBAdapter
from ..config import get_config

class DatabaseFactory:
    @staticmethod
    def get_adapter() -> Type[DatabaseAdapter]:
        """Get the appropriate database adapter based on configuration"""
        config = get_config()
        
        if config.database.database_type.lower() == "mysql":
            return SQLAlchemyAdapter
        elif config.database.database_type.lower() == "mongodb":
            return MongoDBAdapter
        else:
            raise ValueError(f"Unsupported database type: {config.database.database_type}") 