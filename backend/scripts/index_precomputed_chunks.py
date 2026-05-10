"""
Veri İndexleme Scripti (Precomputed Chunks)
data_collector tarafından üretilen, işlenmiş chunk'ları (tam_veri_seti.json)
doğrudan ChromaDB'ye ekler (eklenmiş ID'ler üzerinden çakışmadan).
"""
import sys
import json
import argparse
from pathlib import Path
from loguru import logger
from tqdm import tqdm

# Proje kökünü Python path'e ekle
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import settings
from app.db.vector_store import vector_store
from app.core.embedder import EmbeddingService

def load_json(filepath: Path) -> list:
    """JSON dosyasını yükler."""
    if not filepath.exists():
        logger.error(f"Dosya bulunamadı: {filepath}")
        return []
    with open(filepath, encoding="utf-8") as f:
        return json.load(f)

def index_chunks(force: bool = False):
    """Chunk'ları ChromaDB'ye yerleştirir."""
    data_file = ROOT.parent / "legal_data" / "chunks" / "tam_veri_seti.json"
    
    chunks = load_json(data_file)
    if not chunks:
        return 0

    if force:
        logger.warning("Koleksiyonlar sıfırlanıyor...")
        vector_store.reset_collection(settings.kanunlar_collection)
        vector_store.reset_collection(settings.yargitay_collection)

    embedder = EmbeddingService()
    
    # Türlerine göre ayır kanun vs karar
    kanun_chunks = [c for c in chunks if c.get("tur") == "kanun"]
    yargitay_chunks = [c for c in chunks if c.get("tur") != "kanun"]

    total_added = 0
    batch_size = 256

    def process_batch(chunk_list, collection_name, desc):
        # Tekilleştirmek (ID çakışmasını engellemek) için dictionary kullan
        unique_chunks = {}
        for c in chunk_list:
            if c["id"] not in unique_chunks:
                unique_chunks[c["id"]] = c
            else:
                # Append a suffix if ID already exists (just in case we don't want to lose data)
                new_id = f"{c['id']}_{len(unique_chunks)}"
                c["id"] = new_id
                unique_chunks[new_id] = c
                
        chunk_list = list(unique_chunks.values())
        
        added_count = 0
        for i in tqdm(range(0, len(chunk_list), batch_size), desc=desc):
            batch = chunk_list[i:i + batch_size]
            
            texts = [c["metin"] for c in batch]
            ids = [c["id"] for c in batch]
            metadatas = [c.get("metadata", {}) for c in batch]

            embeddings = embedder.embed_texts(texts, batch_size=batch_size, show_progress=False)

            added = vector_store.add_documents(
                collection_name=collection_name,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            added_count += added
        return added_count

    if kanun_chunks:
        logger.info(f"{len(kanun_chunks)} Kanun chunk işleniyor...")
        total_added += process_batch(kanun_chunks, settings.kanunlar_collection, "Kanunlar")

    if yargitay_chunks:
        logger.info(f"{len(yargitay_chunks)} Karar chunk işleniyor...")
        total_added += process_batch(yargitay_chunks, settings.yargitay_collection, "Kararlar")

    return total_added

def main():
    parser = argparse.ArgumentParser(description="Precomputed Chunks İndexleme Aracı")
    parser.add_argument("--force", action="store_true", help="Mevcut indexi sıfırlayıp yeniden oluştur")
    args = parser.parse_args()

    logger.info("=" * 50)
    logger.info("RAG Indexer - Precomputed JSON")
    logger.info("=" * 50)

    total_added = index_chunks(force=args.force)

    stats = vector_store.get_collection_stats()
    logger.info("=" * 50)
    logger.info("İndexleme tamamlandı!")
    logger.info(f"Oturumda eklenen: {total_added} chunk")
    logger.info(f"Kanun koleksiyonu: {stats['kanunlar']}")
    logger.info(f"Yargıtay koleksiyonu: {stats['yargitay_kararlari']}")
    logger.info("=" * 50)

if __name__ == "__main__":
    main()
