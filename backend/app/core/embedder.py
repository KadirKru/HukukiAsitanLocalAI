"""
Embedding Servisi
sentence-transformers ile Türkçe destekli çok dilli embedding üretir.
"""
from sentence_transformers import SentenceTransformer
from typing import List, Union
from loguru import logger
from app.config import settings
import numpy as np


class EmbeddingService:
    """
    Metin ve belge listelerini dense vector'lere dönüştürür.
    Modeli ilk kullanımda yükler (lazy loading).
    """
    _model: SentenceTransformer = None

    @classmethod
    def _load_model(cls):
        """Modeli yükler (bir kez)."""
        if cls._model is None:
            logger.info(f"Embedding modeli yükleniyor: {settings.embedding_model}")
            cls._model = SentenceTransformer(settings.embedding_model)
            logger.info("Embedding modeli yüklendi.")

    @classmethod
    def embed_text(cls, text: str) -> List[float]:
        """Tek bir metni embedding vektörüne çevirir."""
        cls._load_model()
        embedding = cls._model.encode(
            text,
            normalize_embeddings=True,
            show_progress_bar=False
        )
        return embedding.tolist()

    @classmethod
    def embed_texts(
        cls,
        texts: List[str],
        batch_size: int = 32,
        show_progress: bool = False
    ) -> List[List[float]]:
        """
        Birden fazla metni toplu hâlde embed'ler.
        Büyük veri setleri için batch_size optimize edilebilir.
        """
        cls._load_model()
        if not texts:
            return []

        logger.info(f"{len(texts)} metin embed'leniyor (batch_size={batch_size})...")
        embeddings = cls._model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=show_progress
        )
        logger.info("Embedding işlemi tamamlandı.")
        return embeddings.tolist()

    @classmethod
    def get_embedding_dimension(cls) -> int:
        """Model embedding boyutunu döndürür."""
        cls._load_model()
        return cls._model.get_sentence_embedding_dimension()

    @classmethod
    def compute_similarity(
        cls,
        text1: str,
        text2: str
    ) -> float:
        """İki metin arasındaki cosine benzerliğini hesaplar (0-1)."""
        emb1 = np.array(cls.embed_text(text1))
        emb2 = np.array(cls.embed_text(text2))
        similarity = float(np.dot(emb1, emb2))  # normalize edildiği için dot product = cosine
        return round(similarity, 4)


# Kolayca import edilebilecek singleton referansı
embedder = EmbeddingService()
