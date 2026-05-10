"""
Metin Parçalama Servisi
Hukuki metinleri (kanun maddeleri, kararlar) anlamlı chunk'lara böler.
"""
import re
from typing import List, Dict, Any, Optional
from loguru import logger
from app.config import settings


class TextChunk:
    """Bir metin parçasını metadata ile birlikte tutar."""

    def __init__(
        self,
        text: str,
        chunk_id: str,
        metadata: Dict[str, Any],
        chunk_index: int = 0,
        total_chunks: int = 1
    ):
        self.text = text.strip()
        self.chunk_id = chunk_id
        self.metadata = {**metadata, "chunk_index": chunk_index, "total_chunks": total_chunks}

    def __repr__(self):
        return f"TextChunk(id={self.chunk_id}, len={len(self.text)})"


class LegalTextChunker:
    """
    Hukuki metinleri madde bazlı veya sabit boyutlu chunk'lara böler.
    Kanun metinleri → madde bazlı bölme (öncelikli)
    Uzun metinler → kayan pencere (sliding window)
    """

    # Madde başlığı pattern'i: "Madde 1-", "MADDE 1 –", "m.1", "Md. 15"
    ARTICLE_PATTERN = re.compile(
        r'(?:^|\n)\s*(?:MADDE|Madde|m\.|Md\.)\s*(\d+)\s*[-–—]?\s*',
        re.MULTILINE
    )

    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None
    ):
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap

    def chunk_kanun(
        self,
        text: str,
        kanun_adi: str,
        kanun_no: str,
        base_metadata: Optional[Dict] = None
    ) -> List[TextChunk]:
        """
        Kanun metnini madde bazlı parçalara böler.
        Her madde ayrı bir chunk olarak işlenir.
        """
        metadata = base_metadata or {}
        metadata.update({"kanun_adi": kanun_adi, "kanun_no": kanun_no})

        # Madde bazlı bölme
        chunks = self._split_by_articles(text, kanun_adi, kanun_no, metadata)

        # Madde bulunamazsa sliding window uygula
        if not chunks:
            logger.warning(f"Madde yapısı bulunamadı, sliding window uygulanıyor: {kanun_adi}")
            chunks = self._sliding_window_chunk(text, f"kanun_{kanun_no}", metadata)

        logger.info(f"{kanun_adi}: {len(chunks)} chunk oluşturuldu")
        return chunks

    def chunk_yargitay_karar(
        self,
        text: str,
        daire: str,
        esas_no: str,
        karar_no: str,
        karar_tarihi: str,
        konu: str,
        base_metadata: Optional[Dict] = None
    ) -> List[TextChunk]:
        """
        Yargıtay kararını mantıklı parçalara böler.
        Kısa kararlar tek chunk; uzunlar sliding window ile.
        """
        metadata = base_metadata or {}
        metadata.update({
            "daire": daire,
            "esas_no": esas_no,
            "karar_no": karar_no,
            "karar_tarihi": karar_tarihi,
            "konu": konu,
            "source_type": "yargitay_karari"
        })

        doc_id = f"yargitay_{esas_no.replace('/', '_').replace(' ', '_')}"

        if len(text) <= self.chunk_size * 3:
            # Kısa karar → tek chunk
            return [TextChunk(
                text=text,
                chunk_id=f"{doc_id}_0",
                metadata=metadata,
                chunk_index=0,
                total_chunks=1
            )]
        else:
            # Uzun karar → bölme
            return self._sliding_window_chunk(text, doc_id, metadata)

    def chunk_pdf_text(
        self,
        text: str,
        doc_id: str,
        file_name: str,
        page_number: Optional[int] = None,
        base_metadata: Optional[Dict] = None
    ) -> List[TextChunk]:
        """PDF'den çıkarılan metni chunk'lara böler."""
        metadata = base_metadata or {}
        metadata.update({
            "source_type": "pdf",
            "file_name": file_name,
            "page_number": page_number
        })
        return self._sliding_window_chunk(text, doc_id, metadata)

    def _split_by_articles(
        self,
        text: str,
        kanun_adi: str,
        kanun_no: str,
        metadata: Dict
    ) -> List[TextChunk]:
        """Madde başlıklarına göre metin böler."""
        chunks = []
        matches = list(self.ARTICLE_PATTERN.finditer(text))

        if not matches:
            return []

        for i, match in enumerate(matches):
            madde_no = match.group(1)
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            article_text = text[start:end].strip()

            if len(article_text) < 20:
                continue

            # Çok uzun maddeyi alt parçalara böl
            if len(article_text) > self.chunk_size * 2:
                sub_chunks = self._sliding_window_chunk(
                    article_text,
                    f"kanun_{kanun_no}_m{madde_no}",
                    {**metadata, "madde_no": madde_no}
                )
                chunks.extend(sub_chunks)
            else:
                chunk_id = f"kanun_{kanun_no}_m{madde_no}"
                chunks.append(TextChunk(
                    text=article_text,
                    chunk_id=chunk_id,
                    metadata={**metadata, "madde_no": madde_no},
                    chunk_index=0,
                    total_chunks=1
                ))
        return chunks

    def _sliding_window_chunk(
        self,
        text: str,
        doc_id: str,
        metadata: Dict
    ) -> List[TextChunk]:
        """Kayan pencere yöntemiyle sabit boyutlu chunk oluşturur."""
        words = text.split()
        chunks = []
        i = 0
        chunk_idx = 0

        while i < len(words):
            chunk_words = words[i:i + self.chunk_size]
            chunk_text = " ".join(chunk_words)

            if len(chunk_text.strip()) < 30:
                break

            chunks.append(TextChunk(
                text=chunk_text,
                chunk_id=f"{doc_id}_c{chunk_idx}",
                metadata=metadata,
                chunk_index=chunk_idx
            ))
            i += self.chunk_size - self.chunk_overlap
            chunk_idx += 1

        # total_chunks güncelle
        for chunk in chunks:
            chunk.metadata["total_chunks"] = len(chunks)

        return chunks


# Singleton
chunker = LegalTextChunker()
