"""
Ana Orkestratör - Tüm veri toplama işlemini yönetir.

Kullanım:
    python main.py               → Tümünü çalıştır
    python main.py --kanunlar    → Sadece kanunlar
    python main.py --aym         → Sadece AYM kararları
    python main.py --yargitay    → Sadece Yargıtay kararları
    python main.py --chunk       → Sadece chunk oluştur (veri zaten varsa)
    python main.py --hizli       → Hızlı test (az veri)
"""

import os
import sys
import io
import time
import json
import logging
import argparse
from datetime import datetime

# Windows terminal encoding fix
if sys.stdout.encoding and sys.stdout.encoding.lower() in ('cp1254', 'cp1252', 'ascii'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ─── Logging Kurulumu ────────────────────────────────────────────────────────
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_collector.log"),
            encoding="utf-8"
        ),
    ]
)
logger = logging.getLogger(__name__)


def check_dependencies():
    """Gerekli kutuphanelerin kurulu oldugunu kontrol eder."""
    required = {
        "requests": "requests",
        "bs4": "beautifulsoup4",
        "pdfplumber": "pdfplumber",
    }
    missing = []
    for module, package in required.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(package)

    if missing:
        logger.error("[HATA] Eksik kutuphaneler: %s", ', '.join(missing))
        logger.error("Yuklemek icin: pip install %s", ' '.join(missing))
        sys.exit(1)

    logger.info("[OK] Tum bagimliliklar mevcut")


def run_all(hizli_mod: bool = False):
    """Tüm veri toplama adımlarını çalıştırır."""

    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info("🚀 YASAL VERİ TOPLAMA SİSTEMİ BAŞLATILDI")
    logger.info(f"   Başlangıç: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"   Mod: {'Hızlı Test' if hizli_mod else 'Tam'}")
    logger.info("=" * 60)

    check_dependencies()

    # Import'lar burada yapılır (bağımlılık kontrolü sonrası)
    from scrapers.mevzuat_scraper import run_mevzuat_scraper
    from scrapers.aym_scraper import run_aym_scraper
    from scrapers.yargitay_scraper import run_yargitay_scraper
    from processors.chunker import run_chunker
    from config import OUTPUT_DIR, CHUNKS_DIR

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    sonuclar = {
        "baslangic": start_time.isoformat(),
        "adimlar": {}
    }

    # ─── ADIM 1: Kanunlar ──────────────────────────────────────────────────
    logger.info("\n" + "─" * 50)
    logger.info("ADIM 1/4: Kanunlar (mevzuat.gov.tr)")
    logger.info("─" * 50)

    if hizli_mod:
        # Hızlı modda sadece 3 temel kanun
        hedef_kanunlar = ["anayasa", "turk_ceza_kanunu", "turk_borclar_kanunu"]
        mevzuat_sonuc = run_mevzuat_scraper(target_kanunlar=hedef_kanunlar)
    else:
        mevzuat_sonuc = run_mevzuat_scraper()

    sonuclar["adimlar"]["kanunlar"] = mevzuat_sonuc

    # ─── ADIM 2: AYM Kararları ─────────────────────────────────────────────
    logger.info("\n" + "─" * 50)
    logger.info("ADIM 2/4: AYM Kararları (anayasa.gov.tr)")
    logger.info("─" * 50)

    max_karar = 50 if hizli_mod else 500
    aym_sonuc = run_aym_scraper(max_karar=max_karar)
    sonuclar["adimlar"]["aym"] = aym_sonuc

    # ─── ADIM 3: Yargıtay Kararları ────────────────────────────────────────
    logger.info("\n" + "─" * 50)
    logger.info("ADIM 3/4: Yargıtay Kararları (emsal.yargitay.gov.tr)")
    logger.info("─" * 50)

    max_per_daire = 10 if hizli_mod else 50
    yargitay_sonuc = run_yargitay_scraper(max_per_daire=max_per_daire)
    sonuclar["adimlar"]["yargitay"] = yargitay_sonuc

    # ─── ADIM 4: Chunk Oluşturma ────────────────────────────────────────────
    logger.info("\n" + "─" * 50)
    logger.info("ADIM 4/4: RAG Chunk Oluşturma")
    logger.info("─" * 50)

    chunks = run_chunker()
    sonuclar["adimlar"]["chunking"] = {
        "toplam_chunk": len(chunks),
        "dosya": os.path.join(CHUNKS_DIR, "tam_veri_seti.json")
    }

    # ─── ÖZET ──────────────────────────────────────────────────────────────
    end_time = datetime.now()
    sure = end_time - start_time
    sonuclar["bitis"] = end_time.isoformat()
    sonuclar["sure_dakika"] = round(sure.total_seconds() / 60, 1)

    logger.info("\n" + "=" * 60)
    logger.info("🎉 TAMAMLANDI!")
    logger.info(f"   Süre: {sonuclar['sure_dakika']} dakika")
    logger.info(f"   Toplam chunk: {len(chunks)}")
    logger.info(f"\n   📁 Veriler şuraya kaydedildi:")
    logger.info(f"   {OUTPUT_DIR}")
    logger.info("\n   RAG pipeline için kullanılacak dosya:")
    logger.info(f"   {os.path.join(CHUNKS_DIR, 'tam_veri_seti.json')}")
    logger.info("=" * 60)

    # Sonuç raporunu kaydet
    rapor_yolu = os.path.join(OUTPUT_DIR, "toplama_raporu.json")
    with open(rapor_yolu, "w", encoding="utf-8") as f:
        json.dump(sonuclar, f, ensure_ascii=False, indent=2)

    return sonuclar


def main():
    parser = argparse.ArgumentParser(description="Yasal Veri Toplama Sistemi")
    parser.add_argument("--kanunlar", action="store_true", help="Sadece kanunları çek")
    parser.add_argument("--aym", action="store_true", help="Sadece AYM kararlarını çek")
    parser.add_argument("--yargitay", action="store_true", help="Sadece Yargıtay kararlarını çek")
    parser.add_argument("--chunk", action="store_true", help="Sadece chunk oluştur")
    parser.add_argument("--hizli", action="store_true", help="Hızlı test modu (az veri)")
    parser.add_argument("--max-karar", type=int, default=500, help="Max karar sayısı")

    args = parser.parse_args()

    check_dependencies()

    # Belirli adım seçildiyse sadece onu çalıştır
    if args.kanunlar:
        from scrapers.mevzuat_scraper import run_mevzuat_scraper
        hedef = ["anayasa", "turk_ceza_kanunu", "turk_borclar_kanunu"] if args.hizli else None
        run_mevzuat_scraper(target_kanunlar=hedef)

    elif args.aym:
        from scrapers.aym_scraper import run_aym_scraper
        run_aym_scraper(max_karar=50 if args.hizli else args.max_karar)

    elif args.yargitay:
        from scrapers.yargitay_scraper import run_yargitay_scraper
        run_yargitay_scraper(max_per_daire=10 if args.hizli else 50)

    elif args.chunk:
        from processors.chunker import run_chunker
        run_chunker()

    else:
        # Tümünü çalıştır
        run_all(hizli_mod=args.hizli)


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    main()
