"""
Retriever - Semantic search ile ilgili hukuki belgeleri getirir
"""
from typing import List, Dict, Any, Tuple
from loguru import logger
from app.core.embedder import EmbeddingService
from app.db.vector_store import vector_store
from app.config import settings
from app.models.schemas import SourceDocument


class LegalRetriever:
    """
    Kullanıcı sorgusunu embed'leyip vector store'dan
    ilgili kanun maddelerini ve Yargıtay kararlarını getirir.
    """

    def __init__(self):
        self.embedder = EmbeddingService()
        self.store = vector_store

    def retrieve(
        self,
        query: str,
        top_k: int = None,
        search_kanunlar: bool = True,
        search_yargitay: bool = True
    ) -> List[SourceDocument]:
        """
        Sorgu metni için her iki koleksiyonda semantic search yapar.
        
        Args:
            query: Kullanıcı sorusu / metin
            top_k: Her koleksiyondan kaç sonuç getirileceği
            search_kanunlar: Kanun koleksiyonunda arama yapılsın mı?
            search_yargitay: Yargıtay koleksiyonunda arama yapılsın mı?
        
        Returns:
            Puanına göre sıralanmış SourceDocument listesi
        """
        k = top_k or settings.top_k_results
        logger.info(f"Retrieval başlıyor: top_k={k}, query='{query[:60]}...'")

        # Sorguyu embed'le
        query_embedding = self.embedder.embed_text(query)

        results: List[SourceDocument] = []

        # Kanun arama
        if search_kanunlar:
            kanun_hits = self.store.similarity_search(
                settings.kanunlar_collection, query_embedding, top_k=k
            )
            for hit in kanun_hits:
                meta = hit["metadata"]
                results.append(SourceDocument(
                    document_id=hit["id"],
                    source_type="kanun",
                    title=str(meta.get("kanun", meta.get("kanun_adi", "Bilinmeyen Kanun"))).upper().replace("_", " "),
                    content=hit["document"],
                    article_number=str(meta.get("madde", meta.get("madde_no", ""))),
                    metadata={
                        "kanun_no": meta.get("mevzuat_no", meta.get("kanun_no", "")),
                        "kisim": meta.get("kisim", ""),
                        "bolum": meta.get("bolum", ""),
                    },
                    relevance_score=hit["score"]
                ))

        # Yargıtay arama
        if search_yargitay:
            yargitay_hits = self.store.similarity_search(
                settings.yargitay_collection, query_embedding, top_k=k
            )
            for hit in yargitay_hits:
                meta = hit["metadata"]
                results.append(SourceDocument(
                    document_id=hit["id"],
                    source_type="yargitay_karari",
                    title=f"{meta.get('daire', 'Yargıtay')} - {meta.get('esas_no', '')}",
                    content=hit["document"],
                    article_number=None,
                    metadata={
                        "daire": meta.get("daire", ""),
                        "esas_no": meta.get("esas_no", ""),
                        "karar_no": meta.get("karar_no", ""),
                        "karar_tarihi": meta.get("karar_tarihi", ""),
                        "konu": meta.get("konu", "")
                    },
                    relevance_score=hit["score"]
                ))

        # Puana göre sırala (yüksekten düşüğe)
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        logger.info(f"Retrieval tamamlandı: {len(results)} sonuç bulundu")
        return results

    def build_context_string(self, sources: List[SourceDocument]) -> str:
        """
        Kaynak belgelerden LLM için bağlam metni oluşturur.
        """
        if not sources:
            return "İlgili hukuki kaynak bulunamadı."

        context_parts = []
        for i, src in enumerate(sources, 1):
            if src.source_type == "kanun":
                header = f"[{i}] KANUN: {src.title}"
                if src.article_number:
                    header += f" - Madde {src.article_number}"
            else:
                header = f"[{i}] YARGITAY KARARI: {src.title}"
                if src.metadata.get("karar_tarihi"):
                    header += f" ({src.metadata['karar_tarihi']})"
            context_parts.append(f"{header}\n{src.content}")

        return "\n\n---\n\n".join(context_parts)


# Singleton
retriever = LegalRetriever()
