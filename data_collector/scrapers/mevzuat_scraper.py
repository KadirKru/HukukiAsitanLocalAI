"""
mevzuat.gov.tr Scraper
Türkiye Cumhuriyeti mevzuatını (kanunlar, yönetmelikler) çeker ve JSON olarak kaydeder.
"""

import os
import re
import sys
import time
import json
import logging
import requests
import pdfplumber
from io import BytesIO
from typing import Optional, Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    KANUNLAR, KANUNLAR_DIR, PDF_CACHE_DIR,
    REQUEST_TIMEOUT, REQUEST_DELAY, MAX_RETRIES, HEADERS
)

logger = logging.getLogger(__name__)


def _pdf_url(mevzuat_no: int, tertip: int) -> str:
    """mevzuat.gov.tr PDF indirme URL'si oluşturur."""
    return f"https://www.mevzuat.gov.tr/MevzuatMetin/1.{tertip}.{mevzuat_no}.pdf"


def _alternative_pdf_url(mevzuat_no: int, tertip: int) -> str:
    """Alternatif URL formatı."""
    return f"https://www.mevzuat.gov.tr/MevzuatMetin/{tertip}.{mevzuat_no}.pdf"


def download_pdf(mevzuat_no: int, tertip: int, isim: str) -> Optional[bytes]:
    """PDF'i indirir, önce cache'e bakar."""
    os.makedirs(PDF_CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(PDF_CACHE_DIR, f"{isim}.pdf")

    # Cache'den oku
    if os.path.exists(cache_path):
        logger.info(f"  📁 Cache'den okunuyor: {isim}")
        with open(cache_path, "rb") as f:
            return f.read()

    # URL'leri dene
    urls = [
        _pdf_url(mevzuat_no, tertip),
        _alternative_pdf_url(mevzuat_no, tertip),
        f"https://www.mevzuat.gov.tr/MevzuatMetin/1.{tertip}.{mevzuat_no}20.pdf",
    ]

    for attempt in range(MAX_RETRIES):
        for url in urls:
            try:
                logger.info(f"  ⬇️  İndiriliyor: {url}")
                response = requests.get(
                    url,
                    headers=HEADERS,
                    timeout=REQUEST_TIMEOUT,
                    stream=True
                )
                if response.status_code == 200 and b"%PDF" in response.content[:10]:
                    pdf_data = response.content
                    with open(cache_path, "wb") as f:
                        f.write(pdf_data)
                    logger.info(f"  ✅ İndirildi: {isim} ({len(pdf_data)//1024} KB)")
                    return pdf_data
            except requests.RequestException as e:
                logger.warning(f"  ⚠️  İstek hatası ({url}): {e}")

        if attempt < MAX_RETRIES - 1:
            time.sleep(REQUEST_DELAY * (attempt + 1))

    logger.error(f"  ❌ İndirilemedi: {isim} (No:{mevzuat_no})")
    return None


def extract_text_from_pdf(pdf_data: bytes) -> str:
    """PDF'ten temiz metin çıkarır."""
    text_parts = []
    try:
        with pdfplumber.open(BytesIO(pdf_data)) as pdf:
            for page_num, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

        full_text = "\n".join(text_parts)
        return _clean_text(full_text)
    except Exception as e:
        logger.error(f"  ❌ PDF metin çıkarma hatası: {e}")
        return ""


def _clean_text(text: str) -> str:
    """Ham metni temizler."""
    # Birden fazla boşlukları tek boşluğa indir
    text = re.sub(r" {2,}", " ", text)
    # 3'ten fazla newline'ı 2'ye indir
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Sayfa numarası kalıplarını temizle
    text = re.sub(r"^\s*\d+\s*$", "", text, flags=re.MULTILINE)
    # Tireleri temizle (PDF'lerde kelime bölünmesi)
    text = re.sub(r"-\n(\w)", r"\1", text)
    # Başlangıç ve bitiş boşluklarını temizle
    return text.strip()


def parse_kanun_structure(text: str, isim: str) -> Dict:
    """Metni madde madde parse eder."""
    articles = []
    current_article = None
    current_content = []

    # Madde kalıpları: "Madde 1-", "MADDE 1.", "Md. 1 –" vb.
    article_pattern = re.compile(
        r"^(?:MADDE|Madde|Md\.?)\s+(\d+)\s*[–\-\.:]?\s*(.*)$",
        re.MULTILINE
    )

    lines = text.split("\n")
    for line in lines:
        match = article_pattern.match(line.strip())
        if match:
            # Önceki maddeyi kaydet
            if current_article is not None:
                articles.append({
                    "madde_no": current_article,
                    "icerik": "\n".join(current_content).strip()
                })
            current_article = int(match.group(1))
            baslik = match.group(2).strip()
            current_content = [baslik] if baslik else []
        elif current_article is not None:
            current_content.append(line)

    # Son maddeyi kaydet
    if current_article is not None:
        articles.append({
            "madde_no": current_article,
            "icerik": "\n".join(current_content).strip()
        })

    return {
        "isim": isim,
        "tam_metin": text,
        "maddeler": articles,
        "madde_sayisi": len(articles)
    }


def scrape_kanun(isim: str, mevzuat_no: int, tertip: int, kategori: str) -> Optional[Dict]:
    """Tek bir kanunu çeker ve işler."""
    logger.info(f"\n📖 İşleniyor: {isim} (No: {mevzuat_no})")

    pdf_data = download_pdf(mevzuat_no, tertip, isim)
    if not pdf_data:
        return None

    text = extract_text_from_pdf(pdf_data)
    if not text or len(text) < 100:
        logger.error(f"  ❌ Yetersiz metin: {isim}")
        return None

    kanun_data = parse_kanun_structure(text, isim)
    kanun_data.update({
        "mevzuat_no": mevzuat_no,
        "tertip": tertip,
        "kategori": kategori,
        "kaynak": f"https://www.mevzuat.gov.tr/MevzuatMetin/1.{tertip}.{mevzuat_no}.pdf",
    })

    logger.info(f"  ✅ Tamamlandı: {kanun_data['madde_sayisi']} madde çıkarıldı")
    return kanun_data


def save_kanun(kanun_data: Dict, isim: str):
    """Kanunu JSON olarak kaydeder."""
    os.makedirs(KANUNLAR_DIR, exist_ok=True)
    output_path = os.path.join(KANUNLAR_DIR, f"{isim}.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(kanun_data, f, ensure_ascii=False, indent=2)
    logger.info(f"  💾 Kaydedildi: {output_path}")


def run_mevzuat_scraper(target_kanunlar=None):
    """
    Ana scraper fonksiyonu.
    target_kanunlar: Belirli kanunları seçmek için isim listesi.
                     None ise tüm kanunlar çekilir.
    """
    kanunlar = KANUNLAR
    if target_kanunlar:
        kanunlar = [k for k in KANUNLAR if k[0] in target_kanunlar]

    logger.info(f"🚀 Mevzuat scraper başlatılıyor... ({len(kanunlar)} kanun)")
    results = {"basarili": [], "basarisiz": []}

    for i, (isim, mevzuat_no, tertip, kategori) in enumerate(kanunlar):
        # Zaten indirilmişse atla
        output_path = os.path.join(KANUNLAR_DIR, f"{isim}.json")
        if os.path.exists(output_path):
            logger.info(f"  ⏭️  Zaten mevcut, atlanıyor: {isim}")
            results["basarili"].append(isim)
            continue

        kanun_data = scrape_kanun(isim, mevzuat_no, tertip, kategori)
        if kanun_data:
            save_kanun(kanun_data, isim)
            results["basarili"].append(isim)
        else:
            results["basarisiz"].append(isim)

        # Rate limiting - her 3 kanunda bir biraz daha bekle
        if (i + 1) % 3 == 0:
            time.sleep(REQUEST_DELAY * 2)
        else:
            time.sleep(REQUEST_DELAY)

    logger.info(f"\n{'='*50}")
    logger.info(f"✅ Başarılı: {len(results['basarili'])} kanun")
    logger.info(f"❌ Başarısız: {len(results['basarisiz'])} kanun")
    if results["basarisiz"]:
        logger.info(f"   Başarısızlar: {', '.join(results['basarisiz'])}")

    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    run_mevzuat_scraper()
