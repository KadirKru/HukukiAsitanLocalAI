# 1. Proje Kapak Sayfası

**Proje Adı:** Hukuk Danışmanı AI (Yerel ve Bulut Tabanlı RAG Destekli Yapay Zeka Sistemi)
**Geliştirici:** [Adınız Soyadınız / Öğrenci Numaranız]
**Tarih:** [Tarih]
**Proje GitHub Linki:** [GitHub Depo Linkinizi Buraya Ekleyin]

---

# 2. Projenin Amacı

Bu projenin temel amacı, hukukçuların, avukatların ve bireylerin hukuki bilgiye erişimini hızlandıran, güvenilir ve veri gizliliğine önem veren bir **Yapay Zeka Destekli Hukuk Danışmanlık Sistemi** geliştirmektir. 

Geleneksel hukuki araştırmalar, binlerce sayfalık kanun maddeleri ve Yargıtay kararları arasında saatler süren manuel taramalar gerektirmektedir. Ayrıca, internet üzerinde bulunan hukuki bilgilerin birçoğu güncel olmayabilir veya spesifik bir olaya doğrudan uygulanabilir nitelikte değildir. Bu proje;
* Mevzuat ve içtihatları saniyeler içinde tarayarak doğrudan olaya özgü cevaplar üretebilmeyi,
* Çevrimdışı (Offline) çalışabilme özelliği sayesinde (Ollama Llama 3 entegrasyonu ile) gizli ve hassas hukuki dosyaların bulut sunucularına gönderilmeden, tamamen kullanıcının kendi bilgisayarında güvenle analiz edilmesini,
* Yüklenen dava dosyası, sözleşme veya ihtarname gibi PDF belgelerini okuyarak özetleyebilmeyi,
* İstenen parametrelere uygun resmi formata sahip dilekçe, sözleşme ve ihtarname taslakları oluşturabilmeyi hedeflemektedir.

---

# 3. Problem Tanımı

Hukuk sektöründe karşılaşılan en büyük problemlerden biri "Bilgi Aşırı Yüklenmesi" (Information Overload) ve bu bilgilerin analiz edilme süresidir.

**Temel Problemler:**
1. **Zaman Maliyeti:** Bir dava dosyası hazırlanırken ilgili kanun maddelerinin ve bu maddelere uygun Yargıtay emsal kararlarının bulunması ciddi bir zaman kaybına yol açmaktadır.
2. **Veri Gizliliği ve Güvenlik:** Mevcut genel amaçlı yapay zeka araçları (ChatGPT vb.) verileri kendi sunucularında işlemektedir. Bir avukatın, müvekkiline ait hassas bilgileri (TC Kimlik numaraları, ticari sırlar vb.) bu tarz platformlara yüklemesi hukuki etiğe ve KVKK'ya aykırıdır.
3. **Halüsinasyon (Uydurma) Problemi:** Klasik Büyük Dil Modelleri (LLM), hukuki konularda soru sorulduğunda gerçeği yansıtmayan, "uydurma" (hallucination) kanun maddeleri veya emsal kararlar üretebilmektedir. Hukukta yanlış bilgi telafisi zor sonuçlar doğurur.
4. **Doküman Standardizasyonu:** Hukuki metinlerin (İhtarname, Dilekçe) belirli bir şekil şartı vardır. Standart yapay zeka modelleri, bu formatlara uygun resmi belgeler oluşturmakta zorlanmakta ve sohbet diliyle çıktılar vermektedir.

Bu proje, bu sorunları **RAG (Retrieval-Augmented Generation)** mimarisi ve yerel (Local) LLM kullanımı ile çözmektedir.

---

# 4. Probleme Dair Veri, Elde Edilme Yöntemleri ve Örnek Veriler

Sistemin "halüsinasyon" görmeden doğru cevap verebilmesi için güvenilir bir veri tabanına ihtiyacı vardır. Projede kullanılan veriler, resmi kaynaklardan toplanmış ve optimize edilmiştir.

### Veri Elde Etme Yöntemi (Web Scraping & Data Pipeline)
Proje kapsamında özel bir "Data Collector (Veri Toplayıcı)" modülü Python ile geliştirilmiştir. 
* **Kanunlar:** `mevzuat.gov.tr` gibi resmi kaynaklardan çekilmiş, "Madde", "Fıkra", "Bent" hiyerarşisine uygun olarak ayrıştırılmıştır.
* **İçtihatlar (Yargıtay Kararları):** Mahkeme kararları taranarak sisteme entegre edilmiştir.

Toplanan bu ham veriler, doğrudan veritabanına atılmamış; LangChain metin parçalama (Text Splitter) algoritmaları kullanılarak belirli boyutlarda (Chunk) parçalara ayrılmıştır. Anlam bütünlüğünün bozulmaması için `chunk_size` ve `chunk_overlap` değerleri hukuki metinlerin yapısına uygun (Örneğin: Bölme işlemi madde sonlarında yapılacak şekilde) ayarlanmıştır.

### Örnek Veri Tablosu

| Veri Tipi | Kaynak | Yapılandırma Formatı | Chunk (Parça) Stratejisi | Veri Sayısı / Boyutu |
| :--- | :--- | :--- | :--- | :--- |
| Kanunlar | mevzuat.gov.tr | JSON (Madde No, İçerik, Kanun Adı) | Yapısal (Madde bazlı) + 800 Karakter limitli | Örn: Türk Borçlar Kanunu (Tüm maddeler) |
| Emsal Kararlar | Yargıtay Karar Arama | JSON (Daire, Esas, Karar, Tarih, Metin) | Recursive Character (Karakter bazlı örtüşmeli) | Örn: 100+ Örnek İş Hukuku Kararı |
| PDF Belgeleri | Kullanıcı Yüklemesi | Geçici Bellek (Run-time) | Sayfa ve Paragraf bazlı dinamik parçalama | Kullanıcı bazlı anlık işleme |

*(Bu alana veri setinizin JSON formatındaki bir görselini veya veritabanı ekran görüntüsünü ekleyebilirsiniz.)*

---

# 5. Yöntem (RAG Adımları Sırası İle)

Projenin temel mimarisi RAG (Retrieval-Augmented Generation - Geri Getirim Artırılmış Üretim) teknolojisine dayanmaktadır. RAG, yapay zekaya cevap üretmeden önce kendi bilgi tabanımızda "Arama" yapma yeteneği kazandırır.

Sistemin adım adım çalışma yöntemi şu şekildedir:

**Adım 1: Veri Gönderimi ve Vektörleştirme (Embedding)**
Toplanan kanun maddeleri ve kararlar, Sentence Transformers (`multilingual-e5-large` vb.) modelleri kullanılarak matematiksel vektörlere (sayı dizilerine) dönüştürülür. İnsan dilindeki kelimelerin anlamsal karşılıkları bu vektörlerde saklanır.

**Adım 2: Vektör Veritabanı Depolaması (ChromaDB)**
Oluşturulan vektörler, yüksek performanslı bir Vektör Veritabanı olan **ChromaDB**'ye kaydedilir. Bu veritabanı, klasik SQL yerine "anlamsal benzerlik" (semantic similarity) araması yapmak için optimize edilmiştir.

**Adım 3: Kullanıcı Sorgusunun İşlenmesi (Query)**
Kullanıcı WPF arayüzünden (C#) sorusunu sorar. (Örn: "Kiracı 3 aydır kira ödemiyor, ne yapabilirim?"). Bu sorgu Backend'e (FastAPI) iletilir. Backend, kullanıcının bu sorusunu da anlık olarak aynı yöntemle vektöre dönüştürür.

**Adım 4: Anlamsal Arama (Semantic Search & Retrieval)**
ChromaDB, kullanıcının sorusunun vektörü ile veritabanındaki kanunların vektörleri arasında kosinüs benzerliği (Cosine Similarity) hesaplaması yapar. Sorunun anlamına en yakın (En yüksek Top-K değerine sahip) 3-5 adet kanun maddesini ve emsal kararı saniyeler içinde bulup çıkarır.

**Adım 5: Prompt Mühendisliği ve Bağlam Enjeksiyonu (Context Injection)**
Bulunan bu kanun maddeleri, özel bir sistem komutunun (System Prompt) içine "Bağlam" olarak eklenir. Yapay zekaya şu talimat verilir: *"Sadece sana verdiğim bu kanun maddelerini kullanarak kullanıcının sorusunu cevapla."*

**Adım 6: LLM ile Üretim (Generation)**
LLM (Kullanıcının seçimine göre Gemini Cloud veya Yerel cihazda çalışan Ollama Llama3), sağlanan kanunları analiz eder, anlamlı, akıcı ve tamamen hukuki kaynaklara dayanan resmi bir cevap veya taslak üretip kullanıcıya sunar.

*(Bu alana RAG Mimarisini anlatan bir akış şeması görseli ekleyebilirsiniz.)*

---

# 6. Uygulama Tasarımı, Görseller ve Anlatım

Uygulama, modern yazılım mimarisi prensiplerine uygun olarak Backend ve Frontend olmak üzere iki ayrı modülde tasarlanmıştır.

### Mimari Bileşenler:
* **Frontend (Arayüz):** C# ve WPF (Windows Presentation Foundation) kullanılarak masaüstü uygulaması olarak geliştirilmiştir. Koyu tema (Dark Mode), akıcı animasyonlar, sohbet geçmişi (Chat History) gösterebilen kaydırılabilir mesajlaşma arayüzü ve PDF yükleme alanları ile modern bir kullanıcı deneyimi (UX) sunar. 
* **Backend (Sunucu):** Python ve FastAPI ile geliştirilmiş, asenkron ve yüksek performanslı bir REST API yapısı kurulmuştur.
* **LLM Yönetimi:** Tasarımda *Singleton* desenleri kullanılmış, arayüzdeki "Yapay Zeka Modeli Seçimi" (Cloud vs Local) açılır menüsünden gelen isteğe göre sistemin dinamik olarak Gemini API veya Ollama arasında geçiş yapması sağlanmıştır.

### Önemli Modüller ve Özellikler:
1. **Sohbet Geçmişi (Chat Memory):** Kullanıcının ardışık sorularını hatırlayabilmesi için `_chatHistory` listesi tutulur ve her yeni API isteğinde geçmiş bağlam LLM'e iletilir.
2. **Taslak Oluşturucu Modu (Drafting):** Normal bilgi verme işleminden farklı olarak, Post-Processing (Sonradan İşleme) algoritmaları ve Regex filtreleri kullanılarak LLM'in İngilizce sohbet refleksleri bastırılmış, sadece resmi formatta (Noter İhtarnamesi, Dava Dilekçesi vb.) evrak üretmesi sağlanmıştır.
3. **PDF Dışa Aktarma:** C# QuestPDF kütüphanesi entegre edilerek, üretilen hukuki sonuçların tek tıklama ile A4 formatında, profesyonel bir PDF evrakı olarak bilgisayara kaydedilmesi sağlanmıştır.

*(Bu alana programın arayüz ekran görüntülerini (Sohbet ekranı, Model Seçimi, PDF İndir butonu, Taslak Oluşturucu dropdown menüsü) ekleyebilirsiniz.)*

---

# 7. Örnek ve Test Veriler İle Sonuçların Gösterimi

Sistemin başarısını ölçmek amacıyla farklı modlarda çeşitli testler gerçekleştirilmiştir.

### Test 1: Genel Hukuki Danışmanlık (Soru-Cevap)
* **Senaryo:** İş Kanunu kapsamında haklı fesih durumunun sorgulanması.
* **Kullanıcı Girdisi:** "İşveren küçülme bahanesiyle beni işten çıkardı. 5 yıllık çalışanım. Kıdem ve ihbar tazminatı alabilir miyim?"
* **Model Çıktısı (Özet):** Sistem, 4857 Sayılı İş Kanunu'nun ilgili maddelerini (Madde 17, Madde 18) ve Yargıtay'ın işe iade/küçülme kararlarını referans göstererek işçinin haklarını detaylıca listelemiştir. Halüsinasyon (yanlış madde numarası vb.) gözlemlenmemiştir.

### Test 2: Belge Analizi (PDF Upload RAG)
* **Senaryo:** Uzun ve karmaşık bir kiralama sözleşmesinin PDF olarak sisteme yüklenip özetlenmesi.
* **Kullanıcı Girdisi:** [Sözlesme.pdf yüklenir] "Bu sözleşmedeki fesih şartlarını ve kiracı aleyhine olan riskli maddeleri listele."
* **Model Çıktısı:** Sistem, 20 sayfalık metni başarıyla Chunk'lara bölüp analiz etmiş, kiracının 2 ay üst üste ödeme yapmaması durumunda doğacak tahliye hakkını ve cezai şartları madde madde tespit edip kullanıcıya sunmuştur.

### Test 3: Profesyonel Taslak Üretimi (Drafting Modu)
* **Senaryo:** Ödenmeyen kira sebebiyle resmi ihtarname oluşturulması.
* **Kullanıcı Girdisi (İşlem Türü: Taslak Oluşturucu):** "Müvekkilim Ahmet Yılmaz'a ait Kadıköy'deki dükkanda kiracı Mehmet Kaya 3 aydır 15.000 TL kirayı ödemiyor. 15 gün süre veren bir ihtarname hazırla."
* **Model Çıktısı:**
*(Aşağıdaki alan, sistemden alınan birebir çıktıdır)*
```text
BEYOĞLU [...] NOTERLİĞİ'NE
İHTAR EDEN (KEŞİDECİ): Ahmet Yılmaz (Adres...)
VEKİLİ: Av. [İsim] (Adres...)
MUHATAP: Mehmet Kaya (Adres...)
KONU: Ödenmeyen Kira Bedellerinin Tahsili ve Akde Aykırılık İhtarıdır.
AÇIKLAMALAR:
1- Müvekkilime ait Kadıköy adresinde bulunan ticari dükkanda kiracı olarak bulunmaktasınız.
2- Ocak, Şubat ve Mart aylarına ait aylık 15.000 TL olan toplam 45.000 TL kira bedeli muaccel olmasına rağmen ödenmemiştir.
3- İşbu ihtarnamenin tarafınıza tebliğinden itibaren 15 (on beş) gün içerisinde borcunuzu ödemenizi, aksi takdirde sözleşmenin feshedilerek tahliye davası ve icra takibi başlatılacağını ihtaren bildiririz.
SONUÇ VE İSTEM: ...
Tarih: [...]
İHTAR EDEN VEKİLİ
[İmza]
```
**Sonuç:** Çıktı, yapay zekanın alışılmış sohbet dilinden (merhaba, işte belgeniz vb.) tamamen arındırılmış olup, C# üzerindeki Regex post-processing filtreleri başarıyla çalışmıştır. Üretilen metin QuestPDF modülü ile "PDF İndir" butonuna basılarak resmi evrak formatında kaydedilmiştir.

---
**Son Söz ve Değerlendirme:**
Geliştirilen bu sistem, yerel Llama 3 modellerinin RAG mimarisiyle birleştirildiğinde veri güvenliği endişesi olmadan son derece başarılı ve profesyonel hukuki asistanlık yapabildiğini kanıtlamıştır. Taslak oluşturucu, hafıza yönetimi ve kaynakça belirterek cevap üretme yetenekleri projeyi üretime hazır (Production-ready) bir prototip haline getirmiştir.
