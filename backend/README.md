# Hukuki Danışman AI - Backend Başlatma Kılavuzu

## Gereksinimler
- Python 3.10+
- OpenAI API anahtarı veya yerel Ollama kurulumu

## Kurulum

### 1. Sanal Ortam Oluştur
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Env Dosyası
```powershell
Copy-Item .env.example .env
# .env dosyasını editörde açıp OPENAI_API_KEY'yi girin
```

### 3. Veriyi İndexle
```powershell
python scripts/index_data.py --data-type all
```

### 4. Sunucuyu Başlat
```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. API Dokümantasyonu
http://localhost:8000/docs

## Testler
```powershell
pytest tests/ -v
```

## Ollama Kullanımı (alternatif)
```powershell
# Ollama kurduktan sonra:
ollama pull llama3
# .env dosyasında: LLM_PROVIDER=ollama
```
