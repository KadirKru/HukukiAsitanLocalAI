"""
Documents Route
POST /upload-pdf   - PDF yükleme ve indexleme
POST /index-data   - Ham veri indexleme
GET  /stats        - İstatistikler
"""
import os
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from app.models.schemas import UploadPDFResponse, IndexDataRequest, IndexDataResponse
from app.services.pdf_service import pdf_service
from app.core.rag_pipeline import rag_pipeline
from app.db.vector_store import vector_store
from app.config import settings
from loguru import logger

router = APIRouter(prefix="/documents", tags=["Documents"])

MAX_PDF_SIZE_MB = 20


@router.post("/upload-pdf", response_model=UploadPDFResponse)
async def upload_pdf(
    file: UploadFile = File(..., description="Analiz edilecek PDF dosyası"),
    analyze: bool = True
):
    """
    PDF dosyası yükler, metin çıkarır, chunk'lar ve vector DB'ye indexler.
    
    - Maksimum dosya boyutu: 20 MB
    - Desteklenen format: PDF
    - Sadece metin tabanlı PDF'ler desteklenir (taranmış görüntü değil)
    """
    # Doğrulama
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Sadece PDF dosyaları kabul edilir.")

    content = await file.read()

    if len(content) > MAX_PDF_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"Dosya boyutu {MAX_PDF_SIZE_MB} MB'tan büyük olamaz."
        )

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Boş dosya yüklendi.")

    logger.info(f"PDF yükleniyor: {file.filename} ({len(content)/1024:.1f} KB)")

    try:
        result = pdf_service.process_and_index(
            pdf_bytes=content,
            file_name=file.filename
        )

        message = f"PDF başarıyla işlendi: {result['pages_processed']} sayfa, {result['chunks_created']} parça oluşturuldu."
        if not result.get("indexed"):
            message += " (Indexleme başarısız - metin çıkarılamadı olabilir)"

        return UploadPDFResponse(
            file_name=file.filename,
            pages_processed=result["pages_processed"],
            chunks_created=result["chunks_created"],
            indexed=result.get("indexed", False),
            message=message,
            doc_id=result["doc_id"]
        )
    except Exception as e:
        logger.error(f"PDF işleme hatası: {e}")
        raise HTTPException(status_code=500, detail=f"PDF işlenemedi: {str(e)}")


@router.post("/analyze-pdf", response_model=dict)
async def analyze_pdf_content(
    file: UploadFile = File(...),
    analysis_type: str = "general",
    llm_provider: str = "gemini"
):
    """
    PDF dosyasını indexlemek yerine direkt analiz eder.
    
    analysis_type: general | contract | decision | petition
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Sadece PDF dosyaları kabul edilir.")

    content = await file.read()
    full_text, page_count, _ = pdf_service.extract_text(content)

    if not full_text.strip():
        raise HTTPException(status_code=422, detail="PDF'ten metin çıkarılamadı.")

    try:
        analysis = rag_pipeline.analyze_pdf_with_rag(full_text, analysis_type, override_provider=llm_provider)
        return {
            "file_name": file.filename,
            "pages": page_count,
            "analysis_type": analysis_type,
            "analysis": analysis,
            "char_count": len(full_text)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analiz hatası: {str(e)}")


@router.post("/index-data", response_model=IndexDataResponse)
async def index_data(request: IndexDataRequest):
    """
    data/raw/ klasöründeki ham verileri ChromaDB'ye indexler.
    force_reindex=True ile mevcut index sıfırlanır.
    """
    try:
        # index_data.py scriptini çalıştır
        import subprocess, sys
        script_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "..", "scripts", "index_data.py"
        )
        script_path = os.path.normpath(script_path)

        env = os.environ.copy()
        result = subprocess.run(
            [sys.executable, script_path,
             "--data-type", request.data_type,
             "--force" if request.force_reindex else ""],
            capture_output=True, text=True, timeout=300, env=env
        )

        if result.returncode != 0:
            raise Exception(result.stderr or "Script hatası")

        stats = vector_store.get_collection_stats()
        return IndexDataResponse(
            total_documents=stats["kanunlar"] + stats["yargitay_kararlari"],
            kanun_count=stats["kanunlar"],
            yargitay_count=stats["yargitay_kararlari"],
            message="İndexleme tamamlandı.",
            success=True
        )
    except Exception as e:
        logger.error(f"İndexleme hatası: {e}")
        stats = vector_store.get_collection_stats()
        return IndexDataResponse(
            total_documents=stats["kanunlar"] + stats["yargitay_kararlari"],
            kanun_count=stats["kanunlar"],
            yargitay_count=stats["yargitay_kararlari"],
            message=f"İndexleme hatası: {str(e)}",
            success=False
        )


@router.get("/stats")
async def get_stats():
    """Vector DB istatistiklerini döndürür."""
    stats = vector_store.get_collection_stats()
    return {
        "collections": stats,
        "total_documents": sum(stats.values()),
        "chroma_db_path": settings.chroma_db_path
    }
