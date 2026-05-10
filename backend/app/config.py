"""
Uygulama konfigürasyonu - .env dosyasından okunur
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Literal
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # Uygulama
    app_name: str = "Hukuki Danışman AI API"
    app_version: str = "1.0.0"
    debug: bool = False

    # LLM
    llm_provider: Literal["openai", "ollama", "gemini"] = "openai"
    openai_api_key: str = "sk-your-api-key-here"
    openai_model: str = "gpt-4o-mini"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3-flash-preview"

    # Embedding
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"

    # ChromaDB
    chroma_db_path: str = "C:/Users/kuru2/LegalAppDB"
    kanunlar_collection: str = "kanunlar"
    yargitay_collection: str = "yargitay_kararlari"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # RAG Parametreleri
    top_k_results: int = 5
    max_context_length: int = 4000
    chunk_size: int = 512
    chunk_overlap: int = 50

    # CORS
    allowed_origins: list[str] = ["*"]

    class Config:
        env_file = str(BASE_DIR / ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"

    def get_llm_model(self) -> str:
        """Aktif LLM model adını döndürür."""
        if self.llm_provider == "openai":
            return self.openai_model
        if self.llm_provider == "gemini":
            return self.gemini_model
        return self.ollama_model


# Singleton settings nesnesi
settings = Settings()
