"""
Anayasa Mahkemesi Kararları Scraper
anayasa.gov.tr'dan AYM bireysel başvuru ve iptal kararlarını çeker.
"""

import os
import re
import sys
import time
import json
import logging
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from typing import Optional, Dict, List
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    KARARLAR_DIR, REQUEST_TIMEOUT, REQUEST_DELAY,
    MAX_RETRIES, HEADERS
)

logger = logging.getLogger(__name__)

# AYM API endpoint'leri
AYM_API_BASE = "https://kararlarbilgibankasi.anayasa.gov.tr"
AYM_SEARCH_API = f"{AYM_API_BASE}/Home/AraJson"
AYM_KARAR_API = f"{AYM_API_BASE}/BB"


def search_aym_kararlar(
    basvuru_turu: str = "BB",  # BB: Bireysel Başvuru, GK: Genel Kurul
    sayfa: int = 1,
    sayfa_boyutu: int = 20,
    yil: Optional[int] = None
) -> Optional[Dict]:
    """AYM karar arama API'sini çağırır."""

    params = {
        "BolumTuru": basvuru_turu,
        "KararTuru": "",
        "BasvuruTarihi": "",
        "KararTarihi": "",
        "ResmiGazeteTarihi": "",
        "page": sayfa,
        "pageSize": sayfa_boyutu,
    }
    if yil:
        params["KararTarihi"] = f"01.01.{yil}-31.12.{yil}"

    try:
        response = requests.post(
            AYM_SEARCH_API,
            data=params,
            headers={**HEADERS, "X-Requested-With": "XMLHttpRequest"},
            timeout=REQUEST_TIMEOUT,
            verify=False
        )
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.error(f"  ❌ AYM arama hatası: {e}")

    return None


def scrape_aym_karar_detail(karar_url: str) -> Optional[str]:
    """Tek bir AYM kararının tam metnini çeker."""
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(
                karar_url,
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT,
                verify=False
            )
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, "html.parser")

                # Karar metni genellikle div.karar-metin veya article içinde
                content_selectors = [
                    "div.karar-metin",
                    "div.karar-icerik",
                    "article",
                    "div#kararMetin",
                    "div.content",
                    "main",
                ]
                for selector in content_selectors:
                    element = soup.select_one(selector)
                    if element:
                        return element.get_text(separator="\n", strip=True)

                # Fallback: body metni
                body = soup.find("body")
                if body:
                    return body.get_text(separator="\n", strip=True)

        except Exception as e:
            logger.warning(f"  ⚠️  Karar detay hatası (deneme {attempt+1}): {e}")
            time.sleep(REQUEST_DELAY * (attempt + 1))

    return None


def fetch_bireysel_basvuru_kararlar(
    max_karar: int = 500,
    baslangic_yili: int = 2017,
    bitis_yili: int = 2024
) -> List[Dict]:
    """
    Bireysel başvuru kararlarını çeker.
    En önemli hak kategorileri öncelendirilir.
    """
    os.makedirs(KARARLAR_DIR, exist_ok=True)
    all_kararlar = []

    # Öncelikli hak kategorileri (Türk AYM pratiğinde en çok karşılaşılanlar)
    ONCELIKLI_HAKLAR = [
        "adil yargılanma",
        "ifade özgürlüğü",
        "kişi özgürlüğü",
        "mülkiyet hakkı",
        "özel hayat",
        "işkence yasağı",
        "etkili başvuru",
    ]

    logger.info(f"📋 AYM bireysel başvuru kararları çekiliyor...")
    logger.info(f"   Yıl aralığı: {baslangic_yili}-{bitis_yili}")
    logger.info(f"   Hedef karar sayısı: {max_karar}")

    for yil in range(baslangic_yili, bitis_yili + 1):
        if len(all_kararlar) >= max_karar:
            break

        logger.info(f"\n  📅 {yil} yılı kararları çekiliyor...")
        sayfa = 1

        while len(all_kararlar) < max_karar:
            result = search_aym_kararlar(yil=yil, sayfa=sayfa)
            if not result or "data" not in result or not result["data"]:
                break

            for karar in result["data"]:
                if len(all_kararlar) >= max_karar:
                    break

                karar_no = karar.get("BasvuruNo", "")
                karar_tarihi = karar.get("KararTarihi", "")
                basvurucu = karar.get("Basvurucu", "")

                karar_data = {
                    "karar_no": karar_no,
                    "karar_tarihi": karar_tarihi,
                    "basvurucu": basvurucu,
                    "konu": karar.get("Konu", ""),
                    "karar_turu": "bireysel_basvuru",
                    "kaynak": "anayasa.gov.tr",
                    "sonuc": karar.get("KararSonucu", ""),
                    "ilgili_haklar": karar.get("IhlalEdilenHaklar", ""),
                }

                all_kararlar.append(karar_data)
                logger.info(f"    ✓ {karar_no} - {basvurucu[:30] if basvurucu else 'N/A'}")

            sayfa += 1
            time.sleep(REQUEST_DELAY)

            # Sonraki sayfa yoksa dur
            toplam = result.get("total", 0)
            if sayfa * 20 >= toplam:
                break

    logger.info(f"\n  📊 Toplam çekilen karar: {len(all_kararlar)}")
    return all_kararlar


def fetch_iptal_kararlar() -> List[Dict]:
    """İptal kararlarını çeker (norm denetimi)."""
    os.makedirs(KARARLAR_DIR, exist_ok=True)
    kararlar = []

    logger.info(f"\n📋 AYM iptal kararları çekiliyor...")

    # İptal kararları için farklı endpoint
    url = f"{AYM_API_BASE}/Home/AraJson"
    params = {
        "BolumTuru": "GK",  # Genel Kurul
        "KararTuru": "İptal",
        "page": 1,
        "pageSize": 50,
    }

    for sayfa in range(1, 6):  # Max 5 sayfa = 250 karar
        params["page"] = sayfa
        try:
            response = requests.post(
                url,
                data=params,
                headers={**HEADERS, "X-Requested-With": "XMLHttpRequest"},
                timeout=REQUEST_TIMEOUT,
                verify=False
            )
            if response.status_code == 200:
                result = response.json()
                if not result.get("data"):
                    break

                for karar in result["data"]:
                    kararlar.append({
                        "karar_no": karar.get("EsasNo", ""),
                        "karar_tarihi": karar.get("KararTarihi", ""),
                        "konu": karar.get("Konu", ""),
                        "karar_turu": "iptal",
                        "sonuc": karar.get("KararSonucu", ""),
                        "kaynak": "anayasa.gov.tr",
                        "resmi_gazete": karar.get("ResmiGazeteTarihi", ""),
                    })

                time.sleep(REQUEST_DELAY)
        except Exception as e:
            logger.error(f"  ❌ İptal kararı çekme hatası: {e}")
            break

    logger.info(f"  📊 Toplam iptal kararı: {len(kararlar)}")
    return kararlar


def save_kararlar(kararlar: List[Dict], dosya_adi: str):
    """Kararları JSON olarak kaydeder."""
    os.makedirs(KARARLAR_DIR, exist_ok=True)
    output_path = os.path.join(KARARLAR_DIR, f"{dosya_adi}.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(kararlar, f, ensure_ascii=False, indent=2)

    logger.info(f"  💾 Kaydedildi: {output_path} ({len(kararlar)} karar)")
    return output_path


def run_aym_scraper(max_karar: int = 500):
    """AYM scraper'ı çalıştırır."""
    logger.info("🏛️  AYM Kararları Scraper Başlatılıyor...")

    results = {}

    # 1. Bireysel başvuru kararları
    birey_kararlar = fetch_bireysel_basvuru_kararlar(max_karar=max_karar)
    if birey_kararlar:
        path = save_kararlar(birey_kararlar, "bireysel_basvuru_kararlar")
        results["bireysel_basvuru"] = {"adet": len(birey_kararlar), "dosya": path}

    # 2. İptal kararları
    iptal_kararlar = fetch_iptal_kararlar()
    if iptal_kararlar:
        path = save_kararlar(iptal_kararlar, "iptal_kararlar")
        results["iptal"] = {"adet": len(iptal_kararlar), "dosya": path}

    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    run_aym_scraper(max_karar=200)
