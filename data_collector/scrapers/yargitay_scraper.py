"""
Yargıtay Kararları Scraper
emsal.yargitay.gov.tr'dan içtihat kararlarını çeker.
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

YARGITAY_BASE = "https://emsal.yargitay.gov.tr"
YARGITAY_SEARCH = f"{YARGITAY_BASE}/BilgiBankasiIstemciWeb/yeniArama"

# Hukuk daireleri (en önemli olanlar)
HUKUK_DAIRELERI = {
    "1HD": "1. Hukuk Dairesi",
    "2HD": "2. Hukuk Dairesi (Aile)",
    "4HD": "4. Hukuk Dairesi (Tazminat)",
    "9HD": "9. Hukuk Dairesi (İş)",
    "11HD": "11. Hukuk Dairesi (Ticaret)",
    "12HD": "12. Hukuk Dairesi (İcra)",
    "13HD": "13. Hukuk Dairesi (Tüketici)",
    "HGK": "Hukuk Genel Kurulu",
}

# Ceza daireleri
CEZA_DAIRELERI = {
    "1CD": "1. Ceza Dairesi",
    "2CD": "2. Ceza Dairesi",
    "4CD": "4. Ceza Dairesi",
    "5CD": "5. Ceza Dairesi (Zimmet)",
    "CGK": "Ceza Genel Kurulu",
}


def search_yargitay(
    daire: str,
    kelime: str = "",
    yil: Optional[int] = None,
    sayfa: int = 1
) -> Optional[List[Dict]]:
    """Yargıtay emsal karar arama."""
    params = {
        "daire": daire,
        "arananKelime": kelime,
        "esasYil": yil if yil else "",
        "kararYil": yil if yil else "",
        "pageNo": sayfa,
    }

    try:
        response = requests.post(
            YARGITAY_SEARCH,
            data=params,
            headers={**HEADERS, "Referer": YARGITAY_BASE},
            timeout=REQUEST_TIMEOUT,
            verify=False
        )
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            kararlar = []

            # Karar listesi tablodaki satırlar
            rows = soup.select("table.table tbody tr")
            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 3:
                    link = row.find("a")
                    karar = {
                        "daire": daire,
                        "daire_adi": HUKUK_DAIRELERI.get(daire,
                                     CEZA_DAIRELERI.get(daire, daire)),
                        "esas_no": cols[0].get_text(strip=True) if cols else "",
                        "karar_no": cols[1].get_text(strip=True) if len(cols) > 1 else "",
                        "karar_tarihi": cols[2].get_text(strip=True) if len(cols) > 2 else "",
                        "url": YARGITAY_BASE + link.get("href", "") if link else "",
                        "karar_turu": "hukuk" if "HD" in daire or "HGK" == daire else "ceza",
                        "kaynak": "emsal.yargitay.gov.tr",
                    }
                    kararlar.append(karar)

            return kararlar
    except Exception as e:
        logger.error(f"  ❌ Yargıtay arama hatası ({daire}): {e}")

    return None


def fetch_karar_metni(url: str) -> Optional[str]:
    """Yargıtay kararının tam metnini çeker."""
    if not url:
        return None

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, verify=False)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, "html.parser")

                # Karar metni seçicileri
                selectors = [
                    "div.card-body",
                    "div.karar-text",
                    "pre",
                    "div#kararDetay",
                    "div.row div.col-md-12",
                ]
                for selector in selectors:
                    el = soup.select_one(selector)
                    if el and len(el.get_text(strip=True)) > 100:
                        return el.get_text(separator="\n", strip=True)
        except Exception as e:
            logger.warning(f"  ⚠️  Karar metin hatası (deneme {attempt+1}): {e}")
            time.sleep(REQUEST_DELAY)

    return None


def run_yargitay_scraper(max_per_daire: int = 50) -> Dict:
    """Yargıtay kararlarını çeker."""
    os.makedirs(KARARLAR_DIR, exist_ok=True)
    yargitay_dir = os.path.join(KARARLAR_DIR, "..", "yargitay")
    os.makedirs(yargitay_dir, exist_ok=True)

    all_results = {}

    tum_daireler = {**HUKUK_DAIRELERI, **CEZA_DAIRELERI}

    for daire_kodu, daire_adi in tum_daireler.items():
        logger.info(f"\n⚖️  {daire_adi} ({daire_kodu}) kararları çekiliyor...")

        kararlar = []
        for sayfa in range(1, 4):  # Max 3 sayfa
            result = search_yargitay(daire=daire_kodu, sayfa=sayfa)
            if not result:
                break
            kararlar.extend(result)
            if len(kararlar) >= max_per_daire:
                break
            time.sleep(REQUEST_DELAY)

        kararlar = kararlar[:max_per_daire]
        logger.info(f"  📊 {len(kararlar)} karar bulundu")

        if kararlar:
            # Tam metinleri çek (ilk 20 karar için)
            for i, karar in enumerate(kararlar[:20]):
                if karar.get("url"):
                    metin = fetch_karar_metni(karar["url"])
                    if metin:
                        karar["tam_metin"] = metin
                    time.sleep(REQUEST_DELAY)

            # Kaydet
            dosya_yolu = os.path.join(yargitay_dir, f"{daire_kodu.lower()}_kararlar.json")
            with open(dosya_yolu, "w", encoding="utf-8") as f:
                json.dump(kararlar, f, ensure_ascii=False, indent=2)

            all_results[daire_kodu] = {"adet": len(kararlar), "dosya": dosya_yolu}
            logger.info(f"  💾 Kaydedildi: {dosya_yolu}")

    return all_results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    run_yargitay_scraper(max_per_daire=30)
