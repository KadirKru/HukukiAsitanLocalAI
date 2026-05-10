"""
Veri İndexleme Scripti
data/raw/ klasöründeki kanun ve Yargıtay kararlarını ChromaDB'ye indexler.
Kullanım: python scripts/index_data.py [--data-type all|kanun|yargitay] [--force]
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
from app.services.text_chunker import LegalTextChunker


def load_json(filepath: Path) -> list:
    """JSON dosyasını yükler."""
    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


def index_kanunlar(force: bool = False) -> int:
    """Kanun maddelerini indexler. Returns: indexlenen chunk sayısı"""
    logger.info("Kanun maddeleri indexleniyor...")

    kanun_dir = ROOT / "data" / "raw" / "kanunlar"
    json_files = list(kanun_dir.glob("*.json"))

    if not json_files:
        logger.warning("Kanun JSON dosyası bulunamadı!")
        return 0

    if force:
        logger.info("Kanunlar koleksiyonu sıfırlanıyor...")
        vector_store.reset_collection(settings.kanunlar_collection)

    embedder = EmbeddingService()
    chunker = LegalTextChunker()
    total_chunks = 0

    for json_path in json_files:
        kanunlar = load_json(json_path)
        logger.info(f"Yüklendi: {json_path.name} ({len(kanunlar)} kanun)")

        for kanun in tqdm(kanunlar, desc=f"  {json_path.stem}"):
            kanun_adi = kanun.get("kanun_adi", "Bilinmeyen Kanun")
            kanun_no = kanun.get("kanun_no", "0")
            maddeler = kanun.get("maddeler", [])

            for madde in maddeler:
                madde_no = madde.get("madde_no", "?")
                icerik = madde.get("icerik", "")
                baslik = madde.get("baslik", "")
                kisim = madde.get("kisim", "")
                bolum = madde.get("bolum", "")

                if not icerik.strip():
                    continue

                # Madde metnini chunk'la
                full_text = f"{baslik}\n{icerik}"
                chunks = chunker.chunk_kanun(
                    text=full_text,
                    kanun_adi=kanun_adi,
                    kanun_no=kanun_no,
                    base_metadata={
                        "madde_no": madde_no,
                        "baslik": baslik,
                        "kisim": kisim,
                        "bolum": bolum,
                        "source_type": "kanun"
                    }
                )

                if not chunks:
                    # Chunk oluşturulamazsa direkt ekle
                    from app.services.text_chunker import TextChunk
                    chunks = [TextChunk(
                        text=full_text,
                        chunk_id=f"kanun_{kanun_no}_m{madde_no}",
                        metadata={
                            "kanun_adi": kanun_adi,
                            "kanun_no": kanun_no,
                            "madde_no": madde_no,
                            "baslik": baslik,
                            "kisim": kisim,
                            "bolum": bolum,
                            "source_type": "kanun"
                        }
                    )]

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

    logger.info(f"Kanun indexleme tamamlandı: {total_chunks} chunk eklendi")
    return total_chunks


def index_yargitay(force: bool = False) -> int:
    """Yargıtay kararlarını indexler. Returns: indexlenen chunk sayısı"""
    logger.info("Yargıtay kararları indexleniyor...")

    yargitay_dir = ROOT / "data" / "raw" / "yargitay"
    json_files = list(yargitay_dir.glob("*.json"))

    if not json_files:
        logger.warning("Yargıtay JSON dosyası bulunamadı!")
        return 0

    if force:
        logger.info("Yargıtay koleksiyonu sıfırlanıyor...")
        vector_store.reset_collection(settings.yargitay_collection)

    embedder = EmbeddingService()
    chunker = LegalTextChunker()
    total_chunks = 0

    for json_path in json_files:
        kararlar = load_json(json_path)
        logger.info(f"Yüklendi: {json_path.name} ({len(kararlar)} karar)")

        for karar in tqdm(kararlar, desc=f"  {json_path.stem}"):
            daire = karar.get("daire", "Yargıtay")
            esas_no = karar.get("esas_no", "")
            karar_no = karar.get("karar_no", "")
            karar_tarihi = karar.get("karar_tarihi", "")
            konu = karar.get("konu", "")
            ozet = karar.get("ozet", "")
            karar_metni = karar.get("karar_metni", "")

            # Özet + metin birleştir
            full_text = f"KONU: {konu}\nÖZET: {ozet}\n\nKARAR METNİ:\n{karar_metni}"

            chunks = chunker.chunk_yargitay_karar(
                text=full_text,
                daire=daire,
                esas_no=esas_no,
                karar_no=karar_no,
                karar_tarihi=karar_tarihi,
                konu=konu
            )

            texts = [c.text for c in chunks]
            embeddings = embedder.embed_texts(texts)

            added = vector_store.add_documents(
                collection_name=settings.yargitay_collection,
                documents=texts,
                embeddings=embeddings,
                metadatas=[c.metadata for c in chunks],
                ids=[c.chunk_id for c in chunks]
            )
            total_chunks += added

    logger.info(f"Yargıtay indexleme tamamlandı: {total_chunks} chunk eklendi")
    return total_chunks


def main():
    parser = argparse.ArgumentParser(description="Hukuki veri indexleme aracı")
    parser.add_argument(
        "--data-type",
        choices=["all", "kanun", "yargitay"],
        default="all",
        help="Hangi veri türünün indexleneceği"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Mevcut indexi sıfırlayıp yeniden oluştur"
    )
    args = parser.parse_args()

    logger.info("=" * 50)
    logger.info("Hukuki Veri İndexleme Başlıyor")
    logger.info(f"Veri türü: {args.data_type} | Force: {args.force}")
    logger.info("=" * 50)

    total = 0
    if args.data_type in ("all", "kanun"):
        total += index_kanunlar(force=args.force)

    if args.data_type in ("all", "yargitay"):
        total += index_yargitay(force=args.force)

    # Sonuç istatistikleri
    stats = vector_store.get_collection_stats()
    logger.info("=" * 50)
    logger.info(f"İndexleme tamamlandı!")
    logger.info(f"  Bu oturumda eklenen: {total} chunk")
    logger.info(f"  Kanunlar toplamı   : {stats['kanunlar']}")
    logger.info(f"  Yargıtay toplamı   : {stats['yargitay_kararlari']}")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
