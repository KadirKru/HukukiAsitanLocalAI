# llm baglantisi
# openai veya ollamaya istek atiyor
from typing import Optional
import re
from loguru import logger
from app.config import settings


SYSTEM_PROMPT = """Sen uzman bir Türk hukuk danışmanısın. Kullanıcıların hukuki sorularını yanıtlarken:

1. Sağlanan kanun maddelerine ve Yargıtay kararlarına dayanarak cevap ver.
2. Her iddiayı kaynaklarla destekle: "TCK Madde X'e göre...", "Yargıtay X. Dairesi kararına göre..."
3. Hukuki terimleri açıkla, anlaşılır Türkçe kullan.
4. Cevabın sonunda önemli uyarıları ekle (örn. avukat tavsiyesi).
5. Sağlanan bağlamda cevap bulamazsan bunu açıkça belirt.
6. Spekülasyon yapma; verilen kaynaklara sadık kal.

Cevap formatı:
- Ana cevap (kanun ve kararlara dayalı)
- İlgili yasal düzenlemeler
- Emsal kararlar (varsa)
- Öneriler ve uyarılar
"""


class LLMClient:
    # providera gore model secer

    def __init__(self):
        self.provider = settings.llm_provider
        self.model = settings.get_llm_model()
        logger.info(f"LLM istemcisi başlatıldı: provider={self.provider}, model={self.model}")

    def _call_openai(self, messages: list, temperature: float, max_tokens: int, provider: str) -> str:
        from openai import OpenAI
        if provider == "ollama":
            client = OpenAI(
                base_url=f"{settings.ollama_base_url}/v1",
                api_key="ollama"
            )
            model_to_use = settings.ollama_model
        else:
            client = OpenAI(api_key=settings.openai_api_key)
            model_to_use = settings.openai_model

        response = client.chat.completions.create(
            model=model_to_use,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            frequency_penalty=0.5  # Tekrarları (loop) engellemek için
        )
        return response.choices[0].message.content.strip()

    def _call_gemini(self, messages: list, temperature: float, max_tokens: int, provider: str) -> str:
        import google.generativeai as genai
        genai.configure(api_key=settings.gemini_api_key)
        
        # Gemini expects system instructions in the model init, and history in generate_content or chat session
        system_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
        history = []
        for m in messages:
            if m["role"] == "system": continue
            role = "model" if m["role"] == "assistant" else "user"
            history.append({"role": role, "parts": [m["content"]]})
            
        model = genai.GenerativeModel(
            model_name=self.model,
            system_instruction=system_msg,
            generation_config=genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens
            )
        )
        
        chat = model.start_chat(history=history[:-1] if len(history) > 1 else [])
        last_user_msg = history[-1]["parts"][0] if history else ""
        response = chat.send_message(last_user_msg)
        return response.text.strip()

    def _generate(self, messages: list, temperature: float = 0.2, max_tokens: int = 1500, override_provider: Optional[str] = None) -> str:
        # asil uretim yapan kisim
        provider_to_use = override_provider if override_provider else self.provider
        try:
            if provider_to_use == "gemini":
                return self._call_gemini(messages, temperature, max_tokens, provider_to_use)
            else:
                return self._call_openai(messages, temperature, max_tokens, provider_to_use)
        except Exception as e:
            logger.error(f"LLM hatası ({provider_to_use}): {e}")
            raise RuntimeError(f"LLM cevap üretemedi: {str(e)}")

    def generate_answer(self, question: str, context: str,
                        temperature: float = 0.2, max_tokens: int = 4000,
                        override_provider: Optional[str] = None,
                        chat_history: list = None,
                        query_type: str = "general") -> str:
        # baglami alip soruya cevap verir
        
        if query_type == "drafting":
            temperature = 0.5  # Taslak üretimi için biraz daha yaratıcılık ve loop engelleme
            user_message = f"""Aşağıdaki hukuki kaynakları kullanarak istenen hukuki metnin taslağını oluştur:

=== HUKUK KAYNAKLARI ===
{context}
========================

İSTENEN TASLAK: {question}

GÖREVİN: İstenen taslağın türünü (Adli Dava, İdari Dava, Ceza Şikayeti veya İhtarname) otomatik analiz et ve aşağıdaki 4 yasal şablondan en uygun olanını KESİNLİKLE birebir kullanarak resmi bir hukuki metin üret.

1) ADLİ YARGI (HMK Madde 119) DAVA DİLEKÇESİ ŞABLONU:
[...] MAHKEMESİ HAKİMLİĞİ'NE
DAVACI: [Ad Soyad, T.C. Kimlik No, Adres]
VEKİLİ: [Avukat Adı ve Adresi]
DAVALI: [Ad Soyad, T.C. Kimlik No/Vergi No, Adres]
KONU: [Dava konusu ve değeri]
AÇIKLAMALAR:
1- [Vakıalar...]
HUKUKİ NEDENLER: [Kanun maddeleri]
HUKUKİ DELİLLER: [Deliller listesi]
SONUÇ VE İSTEM: [Açık talep]
[Tarih]
DAVACI VEKİLİ [İmza Alanı]

2) İDARİ YARGI (İYUK Madde 3) DAVA DİLEKÇESİ ŞABLONU:
[...] İDARE/VERGİ MAHKEMESİ BAŞKANLIĞI'NA
DAVACI: [Ad Soyad, T.C. Kimlik No, Adres]
DAVALI: [İlgili Kamu Kurumu Adı, Adres]
TEBLİĞ TARİHİ: [İdari işlemin tebliğ edildiği tarih]
KONU: [İptali istenen idari işlemin tarih ve sayısı, davanın konusu]
AÇIKLAMALAR:
1- [Olay özeti ve hukuka aykırılık nedenleri]
HUKUKİ NEDENLER: [Kanunlar]
HUKUKİ DELİLLER: [İdari İşlem belgesi vb.]
SONUÇ VE İSTEM: [İptal talebi]
[Tarih]
DAVACI [İmza Alanı]

3) CEZA HUKUKU (CMK) SUÇ DUYURUSU ŞABLONU:
[...] CUMHURİYET BAŞSAVCILIĞI'NA
MÜŞTEKİ/ŞİKAYETÇİ: [Ad Soyad, T.C. Kimlik No, Adres]
ŞÜPHELİ: [Biliniyorsa Ad Soyad, T.C. Kimlik No, Adres - Bilinmiyorsa 'Faili Meçhul']
SUÇ: [İsnat edilen suç]
SUÇ TARİHİ VE YERİ: [Tarih ve Yer]
AÇIKLAMALAR:
1- [Olayın detayı]
HUKUKİ NEDENLER: TCK, CMK ve ilgili mevzuat.
DELİLLER: [Tanık, Kamera, Belge vb.]
SONUÇ VE İSTEM: Şüpheli hakkında soruşturma yürütülerek kamu davası açılması talebidir.
[Tarih]
MÜŞTEKİ [İmza Alanı]

4) İHTARNAME ŞABLONU (Noter):
[...] NOTERLİĞİ'NE
İHTAR EDEN: [Ad Soyad, T.C. Kimlik No, Adres]
MUHATAP: [Ad Soyad, T.C. Kimlik No/Unvan, Adres]
KONU: [İhtarın özeti]
AÇIKLAMALAR:
1- [Olay]
SONUÇ VE İSTEM: ...
[Tarih]
İHTAR EDEN [İmza Alanı]

KURALLAR:
1. Ürettiğin metin KESİNLİKLE yukarıdaki 4 yasal şablondan birinin yapısında olmalıdır.
2. Çıktın DOĞRUDAN makam/noter/başlık ismi ile başlamalıdır. Hiçbir giriş veya selamlama KULLANMA.
3. Metnin sonuna HİÇBİR kapanış cümlesi VEYA UYARI YAZMA. İmza alanından sonra metni BİTİR.
4. SADECE TÜRKÇE kullan."""
            system_prompt = "Sen uzman bir Türk avukatsın. Sadece doğrudan resmi dilekçe, ihtarname ve sözleşme metinleri yazarsın. Yazdığın metinler tam bir avukat elinden çıkmış gibi resmi, soğuk ve hukuki jargonla doludur. Asla bir yapay zeka asistanı gibi davranmaz, sohbet etmezsin."
        else:
            user_message = f"""Aşağıdaki hukuki kaynakları kullanarak soruyu yanıtla:

=== HUKUK KAYNAKLARI ===
{context}
========================

SORU: {question}

Lütfen kaynaklara dayanarak kapsamlı ve doğru bir yanıt ver."""
            system_prompt = SYSTEM_PROMPT

        messages = [{"role": "system", "content": system_prompt}]
        if chat_history:
            messages.extend(chat_history)
        messages.append({"role": "user", "content": user_message})

        answer = self._generate(messages, temperature, max_tokens, override_provider)
        
        # Taslak modu için post-processing (Yapay zekanın gereksiz ingilizce başını/sonunu kes)
        if query_type == "drafting":
            answer = self._clean_draft_output(answer)
            
        logger.debug(f"LLM cevabı üretildi ({len(answer)} karakter)")
        return answer

    def _clean_draft_output(self, text: str) -> str:
        # ai sacmalamasin diye bastan sondan kirpiyoz
        cleaned = text.replace("**", "")
        
        # 1. Başlangıcı bul (Noter, İhtar Eden, Davacı vb. ilk nerede geçiyorsa oradan itibaren al)
        match_start = re.search(r'(?i)(\[?\s*\.?\s*\.?\s*\.?\s*(NOTERLİĞİ\'NE|İHTAR EDEN|DAVACI|TARAFLAR|MÜŞTEKİ|ŞİKAYETÇİ|HİZMET SÖZLEŞMESİ|MAHKEMESİ|BAŞSAVCILIĞI\'NA|BAŞKANLIĞI\'NA))', cleaned)
        if match_start:
            cleaned = cleaned[match_start.start():]
            
        # 2. Bitişi bul (İmza alanından sonrasını at)
        match_end = re.search(r'(?i)(\[İsim ve İmza Alanı\]|\[İmza Alanı\]|\[İmza\]|İmza:|İHTAR EDEN VEKİLİ|DAVACI VEKİLİ|MÜŞTEKİ)', cleaned)
        if match_end:
            # Eşleşen kelimenin sonuna kadar al
            end_idx = match_end.end()
            cleaned = cleaned[:end_idx]
            
        return cleaned.strip()

    def analyze_pdf_content(self, pdf_text: str, analysis_type: str = "general") -> str:
        # pdf textini ai ile ozetliyoruz
        type_prompts = {
            "general":   "Bu hukuki belgeyi analiz et ve önemli noktaları özetle.",
            "contract":  "Bu sözleşmeyi analiz et: taraflar, yükümlülükler, riskler ve önemli maddeler.",
            "decision":  "Bu mahkeme kararını analiz et: karar özeti, gerekçe ve emsal değeri.",
            "petition":  "Bu dilekçeyi analiz et: talep, dayanak ve eksiklikler."
        }
        prompt = type_prompts.get(analysis_type, type_prompts["general"])
        truncated = pdf_text[:6000] if len(pdf_text) > 6000 else pdf_text
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"{prompt}\n\n=== BELGE İÇERİĞİ ===\n{truncated}"}
        ]
        return self._generate(messages, temperature=0.1, max_tokens=1200)

    def estimate_confidence(self, answer: str, sources_count: int) -> str:
        # kac tane source bulduysa ona gore guven firlatiyo
        if sources_count >= 4:
            return "high"
        elif sources_count >= 2:
            return "medium"
        return "low"

    def reformulate_query(self, user_query: str) -> str:
        # kullanicinin normal dilini resmi kanun terimlerine cevir (arama motoru icin)
        system_prompt = "Sen bir arama motoru optimizatörüsün. Kullanıcının günlük dildeki hukuki sorusunu, vektör veritabanında aratılmak üzere (kanun ve yargıtay kararları bulmak için) tamamen resmi hukuki terimlere çevir. Asla cevap verme, sadece aranacak resmi anahtar kelimeleri veya kavramları (maksimum 15 kelime) yan yana yaz."
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query}
        ]
        reformulated = self._generate(messages, temperature=0.1, max_tokens=60)
        logger.info(f"Orijinal sorgu: '{user_query}' -> Aranacak Hukuki Terimler: '{reformulated}'")
        return reformulated


# Singleton
llm_client = LLMClient()
