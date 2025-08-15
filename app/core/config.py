# app/core/config.py
from pydantic import BaseModel
import os

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, rely on OS env vars


class Settings(BaseModel):
    app_name: str = "M&A Store Normalizer"
    environment: str = os.getenv("ENV", "dev")
    allow_file_write: bool = os.getenv("ALLOW_FILE_WRITE", "true").lower() in {"1", "true", "yes", "y"}
    default_schema_version: str = os.getenv("DEFAULT_SCHEMA_VERSION", "1.0.0")

    neo4j_uri: str = os.getenv("NEO4J_URI", "")
    neo4j_user: str = os.getenv("NEO4J_USER", "")
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "")
    neo4j_database: str = os.getenv("NEO4J_DATABASE", "neo4j")

    @property
    def neo4j_enabled(self) -> bool:
        return bool(self.neo4j_uri.strip())


settings = Settings()
