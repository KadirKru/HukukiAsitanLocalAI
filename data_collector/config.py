"""
Yasal Tavsiye Uygulaması - Veri Toplama Konfigürasyonu
Tüm kanunlar, kaynaklar ve ayarlar burada tanımlıdır.
"""

import os

# ─── Çıktı Dizinleri ────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "legal_data")
KANUNLAR_DIR = os.path.join(OUTPUT_DIR, "kanunlar")
KARARLAR_DIR = os.path.join(OUTPUT_DIR, "kararlar", "aym")
CHUNKS_DIR = os.path.join(OUTPUT_DIR, "chunks")
PDF_CACHE_DIR = os.path.join(OUTPUT_DIR, "_pdf_cache")

# ─── Temel Kanunlar Listesi ──────────────────────────────────────────────────
# Format: (isim, mevzuat_no, tertip, kategori)
KANUNLAR = [
    # Temel Hukuk
    ("anayasa",              2709,  5, "temel_hukuk"),

    # Ceza Hukuku
    ("turk_ceza_kanunu",     5237,  5, "ceza_hukuku"),
    ("ceza_muhakemesi_kanunu", 5271, 5, "ceza_hukuku"),
    ("infaz_kanunu",         5275,  5, "ceza_hukuku"),

    # Medeni & Borçlar Hukuku
    ("turk_medeni_kanunu",   4721,  5, "medeni_hukuk"),
    ("turk_borclar_kanunu",  6098,  5, "medeni_hukuk"),

    # Usul Hukuku
    ("hukuk_muhakemeleri_kanunu", 6100, 5, "usul_hukuku"),
    ("icra_iflas_kanunu",    2004,  3, "usul_hukuku"),

    # İş Hukuku
    ("is_kanunu",            4857,  5, "is_hukuku"),
    ("isci_sagligi_kanunu",  6331,  5, "is_hukuku"),
    ("sosyal_sigortalar_kanunu", 5510, 5, "is_hukuku"),

    # Ticaret Hukuku
    ("turk_ticaret_kanunu",  6102,  5, "ticaret_hukuku"),

    # İdare Hukuku
    ("idari_yargilama_kanunu", 2577, 5, "idare_hukuku"),
    ("kamulastirma_kanunu",  2942,  5, "idare_hukuku"),

    # Vergi Hukuku
    ("vergi_usul_kanunu",     213,  3, "vergi_hukuku"),
    ("gelir_vergisi_kanunu",  193,  3, "vergi_hukuku"),
    ("kdv_kanunu",           3065,  5, "vergi_hukuku"),
    ("kurumlar_vergisi_kanunu", 5520, 5, "vergi_hukuku"),

    # Tüketici & Kişisel Veri
    ("tuketici_koruma_kanunu", 6502, 5, "tuketici_hukuku"),
    ("kvkk",                 6698,  5, "veri_koruma"),

    # Aile Hukuku (TMK içinde ama ayrıca vurgulayalım)
    ("nufus_hizmetleri_kanunu", 5490, 5, "aile_hukuku"),
]

# ─── AYM Karar Kategorileri ─────────────────────────────────────────────────
AYM_KARAR_TURLERI = [
    "bireysel_basvuru",  # İnsan hakları ihlal kararları
    "iptal",             # Kanun iptal kararları
    "itiraz",            # İtiraz yoluyla gelen kararlar
]

# ─── RAG Chunk Ayarları ──────────────────────────────────────────────────────
CHUNK_SIZE = 800         # karakter cinsinden chunk boyutu
CHUNK_OVERLAP = 150      # örtüşme miktarı
MIN_CHUNK_SIZE = 100     # bu boyuttan küçük chunk'lar atılır

# ─── Request Ayarları ────────────────────────────────────────────────────────
REQUEST_TIMEOUT = 30
REQUEST_DELAY = 1.5      # saniye (rate limiting)
MAX_RETRIES = 3

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
