# ⚖️ RAG Tabanlı Hukuki Danışman AI

Bilgisayar Mühendisliği Bitirme Projesi

## Sistem Mimarisi

```
C# WPF Masaüstü Uygulaması
        ↓ HTTP/REST
Python FastAPI Servisi (:8000)
        ↓
   RAG Pipeline
   ├─ ChromaDB (Vector Store)
   ├─ Sentence Transformers (Embedding)
   └─ OpenAI / Ollama (LLM)
```

## Klasör Yapısı

```
prjdnme/
├── backend/              # Python AI Servisi
│   ├── app/
│   │   ├── main.py           # FastAPI uygulaması
│   │   ├── config.py         # Konfigürasyon
│   │   ├── api/routes/       # Endpoint'ler
│   │   ├── core/             # RAG pipeline, embedder, LLM
│   │   ├── db/               # ChromaDB wrapper
│   │   ├── services/         # PDF, text chunker
│   │   └── models/           # Pydantic şemalar
│   ├── data/raw/             # Kanun + Yargıtay verileri
│   ├── scripts/              # İndexleme araçları
│   └── tests/                # Pytest testleri
│
└── frontend/             # C# WPF Uygulaması
    └── LegalAdvisorWPF/
        ├── Models/           # API veri modelleri
        ├── ViewModels/       # MVVM ViewModel'lar
        ├── Services/         # ApiService (HttpClient)
        ├── Converters/       # WPF değer dönüştürücüler
        └── Views/            # XAML pencereler
```

## Kurulum ve Çalıştırma

### 1. Python Backend

```powershell
cd backend

# Sanal ortam kur
python -m venv venv
.\venv\Scripts\Activate.ps1

# Paketleri yükle
pip install -r requirements.txt

# Env dosyasını düzenle
Copy-Item .env.example .env
# .env içinde OPENAI_API_KEY girin
# (veya LLM_PROVIDER=ollama yapın)

# Veriyi indexle
python scripts/index_data.py --data-type all

# API'yi başlat
uvicorn app.main:app --reload --port 8000
```

### 2. C# WPF Frontend

```powershell
cd frontend\LegalAdvisorWPF
dotnet run --project LegalAdvisorWPF\LegalAdvisorWPF.csproj
```

Ya da Visual Studio ile `LegalAdvisorWPF.sln` açılıp F5.

---

## API Endpoint'leri

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/health` | Sistem durumu |
| POST | `/query` | Hukuki soru sor |
| POST | `/documents/upload-pdf` | PDF yükle & indexle |
| POST | `/documents/analyze-pdf` | PDF analiz et |
| GET | `/documents/stats` | İstatistikler |
| GET | `/docs` | Swagger UI |

## RAG Pipeline Akışı

1. Kullanıcı sorusunu embedding'e çevir
2. ChromaDB'den kanun + Yargıtay kararlarını getir
3. Bağlam metni oluştur
4. LLM (GPT-4o-mini / llama3) ile cevap üret
5. Kaynaklar + cevap WPF UI'da göster

## Testler

```powershell
cd backend
pytest tests/ -v
```
