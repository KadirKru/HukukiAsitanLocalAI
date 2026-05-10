"""
Health Check Route
GET /health - Sistem durumu kontrolü
"""
from fastapi import APIRouter
from app.models.schemas import HealthResponse
from app.db.vector_store import vector_store
from app.config import settings
from loguru import logger

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", response_model=HealthResponse)
async def health_check():
    """Sistem bileşenlerinin durumunu kontrol eder."""
    try:
        stats = vector_store.get_collection_stats()
        db_status = f"OK (kanunlar: {stats['kanunlar']}, yargıtay: {stats['yargitay_kararlari']})"
    except Exception as e:
        logger.warning(f"Vector DB durumu kontrol hatası: {e}")
        db_status = f"HATA: {str(e)}"

    return HealthResponse(
        status="ok",
        version=settings.app_version,
        llm_provider=settings.llm_provider,
        vector_db_status=db_status,
        embedding_model=settings.embedding_model
    )
