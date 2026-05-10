import sys
from pathlib import Path
from loguru import logger
from tqdm import tqdm

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import settings
from app.db.vector_store import vector_store
from app.core.embedder import EmbeddingService
from app.services.text_chunker import LegalTextChunker

def index_txt():
    logger.info("TXT belgeleri indexleniyor...")
    belge_dir = ROOT / "data" / "raw" / "belgeler"
    txt_files = list(belge_dir.glob("*.txt"))

    if not txt_files:
        logger.warning("Belge TXT dosyası bulunamadı!")
        return 0

    embedder = EmbeddingService()
    chunker = LegalTextChunker()
    total_chunks = 0

    for txt_path in txt_files:
        with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()

        logger.info(f"Yüklendi: {txt_path.name}")
        
        # Kanun bazlı chunker'ı ANAYASA ve diğer txt belgeler için kullanalım
        # Çünkü TextChunker Madde/MADDE vb formlarını ayırabiliyor
        chunks = chunker.chunk_kanun(
            text=text,
            kanun_adi=txt_path.stem,
            kanun_no="Belge",
            base_metadata={"source_type": "kanun_txt"}
        )

        if not chunks:
            continue

        texts = [c.text for c in chunks]
        embeddings = embedder.embed_texts(texts)

        added = vector_store.add_documents(
            collection_name=settings.kanunlar_collection,
            documents=texts,
            embeddings=embeddings,
            metadatas=[c.metadata for c in chunks],
            ids=[c.chunk_id for c in chunks]
        )
        total_chunks += added

    logger.info(f"TXT indexleme tamamlandı: {total_chunks} chunk_eklendi")
    return total_chunks

if __name__ == "__main__":
    index_txt()
