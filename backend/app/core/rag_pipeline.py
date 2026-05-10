import time
from typing import Optional
from loguru import logger
from app.core.embedder import EmbeddingService
from app.core.retriever import retriever
from app.core.llm_client import llm_client
from app.models.schemas import QueryRequest, QueryResponse, QueryType
from app.config import settings


class RAGPipeline:

    def __init__(self):
        self.embedder = EmbeddingService()
        self.retriever = retriever
        self.llm = llm_client

    def run(self, request: QueryRequest) -> QueryResponse:
        start_time = time.time()
        logger.info(f"RAG Pipeline başladı: '{request.question[:60]}...'")

        try:
            search_flags = self._get_search_flags(request.query_type)
            sources = self.retriever.retrieve(
                query=request.question,
                top_k=request.top_k,
                **search_flags
            )

            context = self.retriever.build_context_string(sources)

            if len(context) > settings.max_context_length:
                context = context[:settings.max_context_length] + "\n...[kaynak kısaltıldı]"
                logger.debug("Bağlam max uzunlukta kesildi")

            if not sources:
                answer = (
                    "Sorunuzla ilgili veri tabanımda yeterli bilgi bulunamadı. "
                    "Lütfen sorunuzu daha ayrıntılı ifade edin veya ilgili PDF belgesini yükleyin."
                )
            else:
                chat_history_dicts = [{"role": m.role, "content": m.content} for m in request.chat_history]
                answer = self.llm.generate_answer(
                    question=request.question,
                    context=context,
                    override_provider=request.llm_provider,
                    chat_history=chat_history_dicts,
                    query_type=request.query_type.value
                )

            processing_time = (time.time() - start_time) * 1000
            confidence = self.llm.estimate_confidence(answer, len(sources))

            logger.info(f"RAG Pipeline tamamlandı: {processing_time:.0f}ms, {len(sources)} kaynak")

            return QueryResponse(
                answer=answer,
                sources=sources,
                query_type=request.query_type,
                model_used=settings.get_llm_model(),
                processing_time_ms=round(processing_time, 2),
                confidence_level=confidence
            )

        except Exception as e:
            logger.error(f"RAG Pipeline hatası: {e}")
            processing_time = (time.time() - start_time) * 1000
            return QueryResponse(
                answer=f"Bir hata oluştu: {str(e)}. Lütfen tekrar deneyin.",
                sources=[],
                query_type=request.query_type,
                model_used=settings.get_llm_model(),
                processing_time_ms=round(processing_time, 2),
                confidence_level="low"
            )

    def _get_search_flags(self, query_type: QueryType) -> dict:
        flags = {
            QueryType.GENERAL: {"search_kanunlar": True, "search_yargitay": True},
            QueryType.LAW_SEARCH: {"search_kanunlar": True, "search_yargitay": False},
            QueryType.PRECEDENT_SEARCH: {"search_kanunlar": False, "search_yargitay": True},
            QueryType.CASE_ANALYSIS: {"search_kanunlar": True, "search_yargitay": True},
            QueryType.DRAFTING: {"search_kanunlar": True, "search_yargitay": False},
        }
        return flags.get(query_type, {"search_kanunlar": True, "search_yargitay": True})

    def analyze_pdf_with_rag(
        self,
        full_text: str,
        analysis_type: str = "general",
        override_provider: str = None
    ) -> str:
        """
        PDF içeriğini LLM ile analiz eder.
        Hem LLM analizi hem de ilgili kanunları birleştirir.
        """
        logger.info(f"PDF RAG analizi başlıyor: {analysis_type}")

        # 1. PDF metninden keyword oluştur (ilk 500 karakter)
        summary_query = full_text[:500]
        sources = self.retriever.retrieve(query=summary_query, top_k=3)
        law_context = self.retriever.build_context_string(sources)

        # 2. PDF analizi + ilgili kanunlar
        combined_context = f"=== İLGİLİ KANUNLAR ===\n{law_context}\n\n=== PDF BELGE İÇERİĞİ ===\n{full_text[:3000]}"

        return self.llm.generate_answer(
            question=f"Bu {analysis_type} türündeki hukuki belgeyi analiz et.",
            context=combined_context,
            override_provider=override_provider
        )


# Singleton
rag_pipeline = RAGPipeline()
