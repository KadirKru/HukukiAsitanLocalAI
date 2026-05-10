"""
Metin İşleme ve RAG Chunk Oluşturucu
Toplanan verileri RAG pipeline'a hazır parçalara böler.
"""

import os
import re
import sys
import json
import logging
from typing import List, Dict, Generator
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    KANUNLAR_DIR, KARARLAR_DIR, CHUNKS_DIR,
    CHUNK_SIZE, CHUNK_OVERLAP, MIN_CHUNK_SIZE
)

logger = logging.getLogger(__name__)


# ─── Metin Temizleme ─────────────────────────────────────────────────────────

def clean_legal_text(text: str) -> str:
    """Hukuki metni RAG için temizler."""
    if not text:
        return ""

    # Unicode normalize
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Gereksiz boşlukları temizle
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # PDF artifact'larını temizle
    text = re.sub(r"^\s*\d+\s*$", "", text, flags=re.MULTILINE)  # Sayfa numaraları
    text = re.sub(r"Sayfa \d+ / \d+", "", text)
    text = re.sub(r"\f", "\n", text)  # Form feed

    # Hukuki kısaltmaları normalize et
    replacements = {
        "m.": "madde",
        "f.": "fıkra",
        "b.": "bent",
        "vd.": "ve devamı",
        "bkz.": "bakınız",
        "RG": "Resmî Gazete",
    }
    # Not: Bu replacements akıllıca yapılmalı (context gerektirir)

    return text.strip()


# ─── Chunk Oluşturma Stratejileri ────────────────────────────────────────────

def chunk_by_madde(kanun_data: Dict) -> List[Dict]:
    """
    Kanunu madde madde chunk'lara böler.
    Her madde bir chunk olur (çok uzunsa bölünür).
    """
    chunks = []
    isim = kanun_data.get("isim", "bilinmiyor")
    kategori = kanun_data.get("kategori", "")
    mevzuat_no = kanun_data.get("mevzuat_no", "")

    for madde in kanun_data.get("maddeler", []):
        madde_no = madde.get("madde_no", 0)
        icerik = madde.get("icerik", "").strip()

        if not icerik or len(icerik) < MIN_CHUNK_SIZE:
            continue

        # Uzun maddeler için alt bölümlere ayır
        if len(icerik) > CHUNK_SIZE:
            sub_chunks = split_text(icerik, CHUNK_SIZE, CHUNK_OVERLAP)
            for i, sub in enumerate(sub_chunks):
                chunks.append({
                    "id": f"{isim}_madde_{madde_no}_part_{i+1}",
                    "kaynak": isim,
                    "kategori": kategori,
                    "tur": "kanun",
                    "mevzuat_no": mevzuat_no,
                    "madde_no": madde_no,
                    "part": i + 1,
                    "toplam_part": len(sub_chunks),
                    "metin": f"[{isim.upper().replace('_', ' ')} - Madde {madde_no}]\n{sub}",
                    "metadata": {
                        "kanun": isim,
                        "madde": madde_no,
                        "kategori": kategori,
                    }
                })
        else:
            chunks.append({
                "id": f"{isim}_madde_{madde_no}",
                "kaynak": isim,
                "kategori": kategori,
                "tur": "kanun",
                "mevzuat_no": mevzuat_no,
                "madde_no": madde_no,
                "metin": f"[{isim.upper().replace('_', ' ')} - Madde {madde_no}]\n{icerik}",
                "metadata": {
                    "kanun": isim,
                    "madde": madde_no,
                    "kategori": kategori,
                }
            })

    return chunks


def chunk_kanun_tam_metin(kanun_data: Dict) -> List[Dict]:
    """
    Madde ayrıştırma başarısız olduğunda tam metni chunk'lar.
    """
    chunks = []
    isim = kanun_data.get("isim", "bilinmiyor")
    kategori = kanun_data.get("kategori", "")
    tam_metin = kanun_data.get("tam_metin", "")

    if not tam_metin:
        return chunks

    cleaned = clean_legal_text(tam_metin)
    sub_chunks = split_text(cleaned, CHUNK_SIZE, CHUNK_OVERLAP)

    for i, sub in enumerate(sub_chunks):
        if len(sub) < MIN_CHUNK_SIZE:
            continue
        chunks.append({
            "id": f"{isim}_chunk_{i+1}",
            "kaynak": isim,
            "kategori": kategori,
            "tur": "kanun",
            "chunk_index": i + 1,
            "toplam_chunk": len(sub_chunks),
            "metin": f"[{isim.upper().replace('_', ' ')}]\n{sub}",
            "metadata": {
                "kanun": isim,
                "kategori": kategori,
                "chunk_index": i + 1,
            }
        })

    return chunks


def chunk_karar(karar: Dict) -> List[Dict]:
    """AYM veya Yargıtay kararını chunk'lara böler."""
    chunks = []
    karar_no = karar.get("karar_no", "bilinmiyor")
    karar_tarihi = karar.get("karar_tarihi", "")
    karar_turu = karar.get("karar_turu", "karar")
    konu = karar.get("konu", "")
    kaynak = karar.get("kaynak", "")
    daire = karar.get("daire", "")

    # Tam metin varsa chunk'la
    tam_metin = karar.get("tam_metin", "")
    if tam_metin and len(tam_metin) > MIN_CHUNK_SIZE:
        cleaned = clean_legal_text(tam_metin)
        sub_chunks = split_text(cleaned, CHUNK_SIZE, CHUNK_OVERLAP)

        for i, sub in enumerate(sub_chunks):
            if len(sub) < MIN_CHUNK_SIZE:
                continue
            prefix = f"[KARAR: {karar_no} | Tarih: {karar_tarihi} | Kaynak: {kaynak}"
            if daire:
                prefix += f" {daire}"
            prefix += f"]\nKonu: {konu}\n"

            chunks.append({
                "id": f"karar_{karar_no.replace('/', '_')}_{i+1}",
                "kaynak": kaynak,
                "tur": karar_turu,
                "karar_no": karar_no,
                "karar_tarihi": karar_tarihi,
                "konu": konu,
                "metin": prefix + sub,
                "metadata": {
                    "karar_no": karar_no,
                    "tur": karar_turu,
                    "tarih": karar_tarihi,
                    "daire": daire,
                    "konu": konu,
                }
            })
    else:
        # Sadece özet bilgi varsa onu chunk'la
        ozet = f"{konu}\nSonuç: {karar.get('sonuc', '')}\nİlgili Haklar: {karar.get('ilgili_haklar', '')}"
        ozet = ozet.strip()
        if len(ozet) > MIN_CHUNK_SIZE:
            prefix = f"[KARAR: {karar_no} | Tarih: {karar_tarihi}]\n"
            chunks.append({
                "id": f"karar_{karar_no.replace('/', '_')}",
                "kaynak": kaynak,
                "tur": karar_turu,
                "karar_no": karar_no,
                "karar_tarihi": karar_tarihi,
                "konu": konu,
                "metin": prefix + ozet,
                "metadata": {
                    "karar_no": karar_no,
                    "tur": karar_turu,
                    "tarih": karar_tarihi,
                    "daire": daire,
                    "konu": konu,
                }
            })

    return chunks


def split_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    """
    Metni örtüşmeli parçalara böler.
    Cümle sınırlarını korumaya çalışır.
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        if end >= len(text):
            chunks.append(text[start:])
            break

        # Cümle sonu bul (., !, ? + boşluk)
        best_break = end
        for punct in [".\n", "\n\n", ". ", "! ", "? ", "\n"]:
            pos = text.rfind(punct, start + chunk_size // 2, end)
            if pos != -1:
                best_break = pos + len(punct)
                break

        chunks.append(text[start:best_break].strip())
        start = max(start + 1, best_break - overlap)

    return [c for c in chunks if len(c.strip()) > MIN_CHUNK_SIZE]


# ─── Ana Chunk İşleyici ──────────────────────────────────────────────────────

def process_all_kanunlar() -> List[Dict]:
    """Tüm kanun JSON dosyalarını chunk'lara dönüştürür."""
    all_chunks = []

    if not os.path.exists(KANUNLAR_DIR):
        logger.warning(f"Kanunlar dizini bulunamadı: {KANUNLAR_DIR}")
        return all_chunks

    json_files = [f for f in os.listdir(KANUNLAR_DIR) if f.endswith(".json")]
    logger.info(f"\n📚 {len(json_files)} kanun dosyası işleniyor...")

    for dosya_adi in json_files:
        dosya_yolu = os.path.join(KANUNLAR_DIR, dosya_adi)
        try:
            with open(dosya_yolu, "r", encoding="utf-8") as f:
                kanun_data = json.load(f)

            isim = kanun_data.get("isim", dosya_adi.replace(".json", ""))

            # Önce madde bazlı chunking dene
            chunks = chunk_by_madde(kanun_data)

            # Madde ayrıştırma başarısız olduysa tam metin chunk'la
            if not chunks:
                logger.warning(f"  ⚠️  {isim}: Madde ayrıştırma başarısız, tam metin kullanılıyor")
                chunks = chunk_kanun_tam_metin(kanun_data)

            all_chunks.extend(chunks)
            logger.info(f"  ✅ {isim}: {len(chunks)} chunk")

        except Exception as e:
            logger.error(f"  ❌ {dosya_adi} işlenirken hata: {e}")

    return all_chunks


def process_all_kararlar() -> List[Dict]:
    """Tüm karar JSON dosyalarını chunk'lara dönüştürür."""
    all_chunks = []

    for root, dirs, files in os.walk(os.path.dirname(KARARLAR_DIR)):
        for dosya_adi in files:
            if not dosya_adi.endswith(".json"):
                continue

            dosya_yolu = os.path.join(root, dosya_adi)
            try:
                with open(dosya_yolu, "r", encoding="utf-8") as f:
                    kararlar = json.load(f)

                if not isinstance(kararlar, list):
                    kararlar = [kararlar]

                karar_chunks = []
                for karar in kararlar:
                    karar_chunks.extend(chunk_karar(karar))

                all_chunks.extend(karar_chunks)
                logger.info(f"  ✅ {dosya_adi}: {len(karar_chunks)} chunk")

            except Exception as e:
                logger.error(f"  ❌ {dosya_adi} işlenirken hata: {e}")

    return all_chunks


def save_chunks(chunks: List[Dict], dosya_adi: str):
    """Chunk'ları RAG-ready JSON olarak kaydeder."""
    os.makedirs(CHUNKS_DIR, exist_ok=True)
    output_path = os.path.join(CHUNKS_DIR, dosya_adi)

    # Ana JSON dosyası
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    # Özet istatistik
    stats = {
        "toplam_chunk": len(chunks),
        "olusturulma_tarihi": datetime.now().isoformat(),
        "ortalama_chunk_boyutu": sum(len(c["metin"]) for c in chunks) // max(len(chunks), 1),
        "kategoriler": {}
    }
    for chunk in chunks:
        kat = chunk.get("kategori") or chunk.get("tur", "diger")
        stats["kategoriler"][kat] = stats["kategoriler"].get(kat, 0) + 1

    stats_path = output_path.replace(".json", "_stats.json")
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    logger.info(f"  💾 {len(chunks)} chunk kaydedildi: {output_path}")
    return output_path


def run_chunker():
    """Tüm veriyi işleyip chunk'lara dönüştürür."""
    logger.info("✂️  Chunk oluşturucu başlatılıyor...")

    # Kanunları işle
    kanun_chunks = process_all_kanunlar()
    logger.info(f"\n📊 Kanun chunk'ları: {len(kanun_chunks)}")
    if kanun_chunks:
        save_chunks(kanun_chunks, "kanunlar_chunks.json")

    # Kararları işle
    karar_chunks = process_all_kararlar()
    logger.info(f"📊 Karar chunk'ları: {len(karar_chunks)}")
    if karar_chunks:
        save_chunks(karar_chunks, "kararlar_chunks.json")

    # Birleştirilmiş tam veri seti
    all_chunks = kanun_chunks + karar_chunks
    if all_chunks:
        save_chunks(all_chunks, "tam_veri_seti.json")
        logger.info(f"\n🎉 Toplam: {len(all_chunks)} chunk oluşturuldu!")
        logger.info(f"   RAG pipeline için: {os.path.join(CHUNKS_DIR, 'tam_veri_seti.json')}")

    return all_chunks


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    run_chunker()
