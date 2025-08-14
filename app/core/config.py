from pydantic import BaseModel
import os

class Settings(BaseModel):
    app_name: str = "M&A Store Normalizer"
    environment: str = os.getenv("ENV", "dev")
    allow_file_write: bool = True
    default_schema_version: str = "1.0.0"

settings = Settings()
