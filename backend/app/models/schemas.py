"""
Pydantic şema modelleri - API request/response tipleri
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class QueryType(str, Enum):
    GENERAL = "general"
    CASE_ANALYSIS = "case_analysis"
    LAW_SEARCH = "law_search"
    PRECEDENT_SEARCH = "precedent_search"
    DRAFTING = "drafting"

class Message(BaseModel):
    role: str = Field(..., description="Mesajı gönderen: 'user' veya 'assistant'")
    content: str = Field(..., description="Mesaj içeriği")


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=5, max_length=2000,
                          description="Hukuki soru veya durum açıklaması")
    query_type: QueryType = Field(default=QueryType.GENERAL,
                                  description="Sorgu türü")
    top_k: int = Field(default=5, ge=1, le=20,
                       description="Getirilecek kaynak sayısı")
    session_id: Optional[str] = Field(default=None,
                                       description="Oturum kimliği")
    llm_provider: Optional[str] = Field(default=None,
                                       description="Hangi modelin kullanılacağı: 'gemini', 'ollama' vs.")
    chat_history: List[Message] = Field(default_factory=list,
                                       description="Sohbet geçmişi (önceki mesajlar)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "question": "İş sözleşmesi haksız fesih durumunda işçinin hakları nelerdir?",
                "query_type": "general",
                "top_k": 5
            }
        }
    }


class SourceDocument(BaseModel):
    document_id: str = Field(..., description="Belge kimliği")
    source_type: str = Field(..., description="Kaynak türü: 'kanun' veya 'yargitay_karari'")
    title: str = Field(..., description="Kaynak başlığı (kanun adı / dava no)")
    content: str = Field(..., description="İlgili metin parçası")
    article_number: Optional[str] = Field(default=None, description="Madde numarası")
    metadata: dict = Field(default_factory=dict, description="Ek metadata")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Alaka skoru")


class QueryResponse(BaseModel):
    answer: str = Field(..., description="AI tarafından üretilen cevap")
    sources: List[SourceDocument] = Field(default_factory=list,
                                           description="Referans gösterilen kaynaklar")
    query_type: QueryType = Field(..., description="Kullanılan sorgu türü")
    model_used: str = Field(..., description="Kullanılan LLM modeli")
    processing_time_ms: float = Field(..., description="İşlem süresi (ms)")
    confidence_level: str = Field(default="medium",
                                   description="Güven seviyesi: low/medium/high")


class UploadPDFResponse(BaseModel):
    file_name: str = Field(..., description="Yüklenen dosya adı")
    pages_processed: int = Field(..., description="İşlenen sayfa sayısı")
    chunks_created: int = Field(..., description="Oluşturulan parça sayısı")
    indexed: bool = Field(..., description="Vector DB'ye indexlendi mi?")
    message: str = Field(..., description="İşlem sonuç mesajı")
    doc_id: str = Field(..., description="Belge kimliği")


class IndexDataRequest(BaseModel):
    data_type: str = Field(default="all",
                           description="İndexlenecek veri türü: 'kanun'/'yargitay'/'all'")
    force_reindex: bool = Field(default=False,
                                description="Mevcut indexi sıfırlayıp yeniden oluştur")


class IndexDataResponse(BaseModel):
    total_documents: int
    kanun_count: int
    yargitay_count: int
    message: str
    success: bool


class HealthResponse(BaseModel):
    status: str
    version: str
    llm_provider: str
    vector_db_status: str
    embedding_model: str
