"""
FastAPI Ana Uygulama
Tüm router'ları kayıt eder ve middleware ayarlarını yapar.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from loguru import logger
import sys

from app.config import settings
from app.api.routes import health, query, documents


# Loglama ayarları
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    level="INFO"
)
logger.add(
    "logs/app.log",
    rotation="10 MB",
    retention="7 days",
    level="DEBUG",
    encoding="utf-8"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Uygulama başlangıç ve kapanış olayları."""
    logger.info("=" * 50)
    logger.info(f"🏛️  {settings.app_name} v{settings.app_version} başlatılıyor...")
    logger.info(f"   LLM Provider : {settings.llm_provider} ({settings.get_llm_model()})")
    logger.info(f"   Embedding    : {settings.embedding_model}")
    logger.info(f"   ChromaDB     : {settings.chroma_db_path}")
    logger.info("=" * 50)

    # ChromaDB ve embedding modelini önceden yükle
    try:
        from app.db.vector_store import vector_store
        stats = vector_store.get_collection_stats()
        logger.info(f"Vector DB hazır | Kanunlar: {stats['kanunlar']} | Yargıtay: {stats['yargitay_kararlari']}")
    except Exception as e:
        logger.warning(f"Vector DB yüklenemedi: {e}")

    yield

    logger.info("Uygulama kapatılıyor...")


# FastAPI uygulaması
app = FastAPI(
    title=settings.app_name,
    description="""
    ## RAG Tabanlı Hukuki Danışman API
    
    Türk hukuku kapsamında kanun maddeleri ve Yargıtay kararlarını kullanarak  
    doğal dilde soruları yanıtlayan RAG (Retrieval-Augmented Generation) sistemi.
    
    ### Özellikler
    - 🔍 **Semantic Search**: Kanun maddeleri ve emsal kararlar
    - 📄 **PDF Analiz**: Hukuki belgeler için akıllı analiz  
    - 🤖 **AI Cevap**: Kaynak göstererek LLM tabanlı yanıtlar
    - 📚 **Çok Dilli Embedding**: Türkçe destekli vector search
    """,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Middleware (WPF uygulaması için)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Router kayıtları
app.include_router(health.router)
app.include_router(query.router)
app.include_router(documents.router)


@app.get("/", tags=["Root"])
async def root():
    """API kök endpoint - temel bilgileri döndürür."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health"
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Genel hata yakalayıcı."""
    logger.error(f"Yakalanmamış hata: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Sunucu tarafında bir hata oluştu.", "error": str(exc)}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level="info"
    )
