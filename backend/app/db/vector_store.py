"""
Vector Store - ChromaDB wrapper sınıfı
Kanun maddeleri ve Yargıtay kararlarını saklar ve semantic search yapar
"""
import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger
from app.config import settings


class VectorStore:
    """
    ChromaDB üzerinde koleksiyon yönetimi ve semantic search sağlar.
    Singleton pattern ile tek örnek kullanılır.
    """
    _instance: Optional["VectorStore"] = None
    _client: Optional[chromadb.PersistentClient] = None

    def __new__(cls) -> "VectorStore":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._client is None:
            self._initialize()

    def _initialize(self):
        """ChromaDB istemcisini ve koleksiyonları başlatır."""
        try:
            self._client = chromadb.PersistentClient(
                path=settings.chroma_db_path,
                settings=ChromaSettings(anonymized_telemetry=False)
            )
            # Koleksiyonları oluştur / bağlan
            self._kanunlar = self._client.get_or_create_collection(
                name=settings.kanunlar_collection,
                metadata={"hnsw:space": "cosine", "description": "Türk Kanun Maddeleri"}
            )
            self._yargitay = self._client.get_or_create_collection(
                name=settings.yargitay_collection,
                metadata={"hnsw:space": "cosine", "description": "Yargıtay Emsal Kararları"}
            )
            logger.info(f"ChromaDB başlatıldı: {settings.chroma_db_path}")
            logger.info(f"Kanunlar koleksiyonu: {self._kanunlar.count()} belge")
            logger.info(f"Yargıtay koleksiyonu: {self._yargitay.count()} belge")
        except Exception as e:
            logger.error(f"ChromaDB başlatma hatası: {e}")
            raise

    def _get_collection(self, collection_name: str):
        """Koleksiyon adına göre koleksiyonu döndürür."""
        if collection_name == settings.kanunlar_collection:
            return self._kanunlar
        elif collection_name == settings.yargitay_collection:
            return self._yargitay
        else:
            raise ValueError(f"Bilinmeyen koleksiyon: {collection_name}")

    def add_documents(
        self,
        collection_name: str,
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]],
        ids: List[str]
    ) -> int:
        """
        Belgeleri embedding'leriyle birlikte koleksiyona ekler.
        Returns: Eklenen belge sayısı
        """
        collection = self._get_collection(collection_name)
        # Var olan ID'leri kontrol et, çakışanları atla
        existing = set(collection.get(ids=ids)["ids"])
        new_ids, new_docs, new_embs, new_metas = [], [], [], []
        for doc_id, doc, emb, meta in zip(ids, documents, embeddings, metadatas):
            if doc_id not in existing:
                new_ids.append(doc_id)
                new_docs.append(doc)
                new_embs.append(emb)
                new_metas.append(meta)

        if new_ids:
            collection.add(
                documents=new_docs,
                embeddings=new_embs,
                metadatas=new_metas,
                ids=new_ids
            )
            logger.debug(f"{len(new_ids)} belge eklendi → {collection_name}")
        return len(new_ids)

    def similarity_search(
        self,
        collection_name: str,
        query_embedding: List[float],
        top_k: int = 5,
        where: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Verilen embedding'e en benzer belgeleri döndürür.
        Returns: [{"id", "document", "metadata", "distance", "score"}, ...]
        """
        collection = self._get_collection(collection_name)
        if collection.count() == 0:
            logger.warning(f"Koleksiyon boş: {collection_name}")
            return []

        query_params = {
            "query_embeddings": [query_embedding],
            "n_results": min(top_k, collection.count()),
            "include": ["documents", "metadatas", "distances"]
        }
        if where:
            query_params["where"] = where

        results = collection.query(**query_params)

        formatted = []
        for i in range(len(results["ids"][0])):
            distance = results["distances"][0][i]
            # Cosine distance'ı benzerlik skoruna çevir (0-1 arası)
            score = max(0.0, 1.0 - distance)
            formatted.append({
                "id": results["ids"][0][i],
                "document": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": distance,
                "score": round(score, 4)
            })
        return formatted

    def multi_collection_search(
        self,
        query_embedding: List[float],
        top_k: int = 5
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Her iki koleksiyonda da arama yapar.
        Returns: (kanun_results, yargitay_results)
        """
        kanun_results = self.similarity_search(
            settings.kanunlar_collection, query_embedding, top_k
        )
        yargitay_results = self.similarity_search(
            settings.yargitay_collection, query_embedding, top_k
        )
        return kanun_results, yargitay_results

    def get_collection_stats(self) -> Dict[str, int]:
        """Her iki koleksiyonun belge sayısını döndürür."""
        return {
            "kanunlar": self._kanunlar.count(),
            "yargitay_kararlari": self._yargitay.count()
        }

    def reset_collection(self, collection_name: str) -> None:
        """Koleksiyonu siler ve yeniden oluşturur."""
        self._client.delete_collection(collection_name)
        if collection_name == settings.kanunlar_collection:
            self._kanunlar = self._client.create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
        elif collection_name == settings.yargitay_collection:
            self._yargitay = self._client.create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
        logger.info(f"Koleksiyon sıfırlandı: {collection_name}")


# Singleton instance
vector_store = VectorStore()
