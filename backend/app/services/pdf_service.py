"""
PDF Analiz Servisi
PyMuPDF ile PDF'ten metin çıkarır, chunk'layıp geçici indexler.
"""
import fitz  # PyMuPDF
import uuid
import tempfile
import os
from typing import List, Tuple, Dict, Any, Optional
from loguru import logger
from app.services.text_chunker import chunker, TextChunk
from app.core.embedder import EmbeddingService
from app.db.vector_store import vector_store
from app.config import settings


class PDFService:
    """
    PDF dosyalarını işler:
    1. Metin çıkarma (sayfa bazlı)
    2. Metni chunk'lara bölme
    3. Embedding oluşturma
    4. ChromaDB'ye geçici indexleme (PDF koleksiyonu)
    """

    def __init__(self):
        self.embedder = EmbeddingService()

    def extract_text(self, pdf_bytes: bytes) -> Tuple[str, int, List[Dict]]:
        """
        PDF byte'larından metin çıkarır.
        
        Returns:
            (full_text, page_count, page_texts)
            page_texts: [{"page": 1, "text": "..."}]
        """
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page_count = len(doc)
        page_texts = []
        full_text_parts = []

        for page_num in range(page_count):
            page = doc[page_num]
            text = page.get_text("text")
            text = self._clean_text(text)
            if text.strip():
                page_texts.append({"page": page_num + 1, "text": text})
                full_text_parts.append(f"[Sayfa {page_num + 1}]\n{text}")

        doc.close()
        full_text = "\n\n".join(full_text_parts)
        logger.info(f"PDF işlendi: {page_count} sayfa, {len(full_text)} karakter")
        return full_text, page_count, page_texts

    def _clean_text(self, text: str) -> str:
        """PDF'ten çıkarılan metni temizler."""
        import re
        # Fazla boşlukları temizle
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        # Sayfa numarası gibi tek satır sayıları kaldır
        text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
        return text.strip()

    def process_and_index(
        self,
        pdf_bytes: bytes,
        file_name: str,
        collection_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        PDF'i işler ve vector database'e indexler.
        
        Returns:
            {
                "doc_id": str,
                "pages_processed": int,
                "chunks_created": int,
                "indexed": bool,
                "full_text": str
            }
        """
        doc_id = f"pdf_{uuid.uuid4().hex[:12]}"
        coll = collection_name or "pdf_documents"

        # 1. Metin çıkar
        full_text, page_count, page_texts = self.extract_text(pdf_bytes)

        if not full_text.strip():
            return {
                "doc_id": doc_id,
                "pages_processed": page_count,
                "chunks_created": 0,
                "indexed": False,
                "full_text": "",
                "error": "PDF'ten metin çıkarılamadı (taranmış görüntü olabilir)."
            }

        # 2. Sayfa bazlı chunk oluştur
        all_chunks: List[TextChunk] = []
        for page_info in page_texts:
            page_chunks = chunker.chunk_pdf_text(
                text=page_info["text"],
                doc_id=f"{doc_id}_p{page_info['page']}",
                file_name=file_name,
                page_number=page_info["page"],
                base_metadata={"doc_id": doc_id, "file_name": file_name}
            )
            all_chunks.extend(page_chunks)

        if not all_chunks:
            return {
                "doc_id": doc_id,
                "pages_processed": page_count,
                "chunks_created": 0,
                "indexed": False,
                "full_text": full_text
            }

        # 3. Embedding oluştur
        texts = [c.text for c in all_chunks]
        embeddings = self.embedder.embed_texts(texts)

        # 4. PDF koleksiyonunu oluştur/kullan
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings
            client = chromadb.PersistentClient(
                path=settings.chroma_db_path,
                settings=ChromaSettings(anonymized_telemetry=False)
            )
            pdf_collection = client.get_or_create_collection(
                name=coll,
                metadata={"hnsw:space": "cosine"}
            )
            pdf_collection.add(
                documents=texts,
                embeddings=embeddings,
                metadatas=[c.metadata for c in all_chunks],
                ids=[c.chunk_id for c in all_chunks]
            )
            indexed = True
            logger.info(f"PDF indexlendi: {len(all_chunks)} chunk → {coll}")
        except Exception as e:
            logger.error(f"PDF indexleme hatası: {e}")
            indexed = False

        return {
            "doc_id": doc_id,
            "pages_processed": page_count,
            "chunks_created": len(all_chunks),
            "indexed": indexed,
            "full_text": full_text
        }

    def get_pdf_metadata(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """PDF meta verilerini çıkarır."""
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        meta = doc.metadata
        doc.close()
        return {
            "title": meta.get("title", ""),
            "author": meta.get("author", ""),
            "subject": meta.get("subject", ""),
            "creator": meta.get("creator", ""),
            "page_count": len(fitz.open(stream=pdf_bytes, filetype="pdf"))
        }


# Singleton
pdf_service = PDFService()
