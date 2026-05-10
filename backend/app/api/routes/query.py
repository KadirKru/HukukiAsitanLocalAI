"""
Query Route
POST /query - Hukuki soru cevap
"""
from fastapi import APIRouter, HTTPException
from app.models.schemas import QueryRequest, QueryResponse
from app.core.rag_pipeline import rag_pipeline
from loguru import logger

router = APIRouter(prefix="/query", tags=["Query"])


@router.post("", response_model=QueryResponse)
async def query_legal(request: QueryRequest):
    """
    Hukuki soruyu RAG pipeline ile yanıtlar.
    Vector DB'den ilgili kanun ve kararları getirir, LLM ile cevap üretir.
    
    - **question**: Hukuki soru veya durum açıklaması (min 5 karakter)
    - **query_type**: general | law_search | precedent_search | case_analysis
    - **top_k**: Getirilecek kaynak sayısı (1-20)
    """
    try:
        logger.info(f"Query isteği alındı: type={request.query_type}, q='{request.question[:50]}'")
        response = rag_pipeline.run(request)
        return response
    except Exception as e:
        logger.error(f"Query endpoint hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Sorgu işlenemedi: {str(e)}")
