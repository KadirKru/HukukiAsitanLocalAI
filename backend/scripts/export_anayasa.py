import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import settings
from app.db.vector_store import vector_store

def export():
    # ChromaDB'den ANAYASA belgelerini çek
    collection = vector_store._get_collection(settings.kanunlar_collection)
    results = collection.get(
        where={"source_type": "kanun_txt"}
    )
    
    export_data = []
    
    if results and results.get("ids"):
        for i in range(len(results["ids"])):
            export_data.append({
                "chunk_id": results["ids"][i],
                "metadata": results["metadatas"][i],
                "icerik": results["documents"][i]
            })
            
    # Madde numarasına göre mantıklı bir sıralama yapmaya çalışalım (Eğer varsa)
    def parse_chunk_index(item):
        return item["metadata"].get("chunk_index", 0)
        
    export_data.sort(key=parse_chunk_index)

    out_path = ROOT / "data" / "raw" / "belgeler" / "ANAYASA_islenmis.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)
        
    print(f"Başarılı: {len(export_data)} adet madde veya fıkra başarıyla {out_path.name} olarak dışa aktarıldı.")

if __name__ == "__main__":
    export()
