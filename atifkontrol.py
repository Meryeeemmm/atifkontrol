import json #JSON işlemleri için
import os #dosya işlemleri için
import random #rastgele seçim için
import time #zaman işlemleri için
from typing import List, Dict, Any #tip ipuçları için
import sys #sistem işlemleri için
import ctypes #Windows API çağrıları için
# Önceki hata log dosyasını sil
if os.path.exists("gemini_errors.log"):
    os.remove("gemini_errors.log")

if sys.platform == "win32": # Windows sisteminde ekranın kapanmasını engellemek için
    ES_CONTINUOUS = 0x80000000 # sürekli etkinlik bayrağı
    ES_SYSTEM_REQUIRED = 0x00000001 # sistem etkinliği bayrağı
    ES_DISPLAY_REQUIRED = 0x00000002 # ekran etkinliği bayrağı
    ctypes.windll.kernel32.SetThreadExecutionState( 
        ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
    ) #ekranın kapanmasını engelle

FATAL_GEMINI_ERROR = False #fatal gemini hatası durumu
FATAL_GEMINI_REASON = "" #fatal gemini hata sebebi
FALLBACK_LOG_FILE = "fallback.log" #yedek log dosyası

try: #google-generativeai kütüphanesini içe aktarıyor
    import google.generativeai as genai #google generative ai modülü
except ImportError: #google-generativeai modülü yüklü değilse hata veriyor
    print("google-generativeai kurulu değil") #uyarı mesajı
    exit(1) #programdan çıkış yapıyor

try: #çevresel değişkenden GEMINI_API_KEY alınmaya çalışılıyor
    API_KEY = os.environ["GEMINI_API_KEY"] #çevresel değişkenden GEMINI_API_KEY alınmaya çalışılıyor
except KeyError: #çevresel değişkende GEMINI_API_KEY yoksa
    API_KEYS: List[str] = [
        "API_ANAHTAR_1",
        "API_ANAHTAR_2",
    ] #API_KEYS listesini tanımlıyor
    API_KEY = random.choice(API_KEYS) #API_KEYS listesinden rastgele bir API anahtarı seçiliyor

genai.configure(api_key=API_KEY) #google generative ai modülü yapılandırılıyor

MAX_RETRIES = 2 #maksimum deneme sayısı
RETRY_DELAY = 5 #denemeler arasındaki gecikme süresi

SYSTEM_PROMPT = """
Sen katı kurallarla çalışan bir veri sınıflandırma sistemisin.

Görevin:
Sana verilen TEK BİR KAYDA AİT BİRDEN FAZLA ALANI analiz edip,
bu kaydın GENEL olarak "atıflı" mı yoksa "temiz" mi olduğunu belirlemektir.

DEĞERLENDİRME ŞEKLİ
- Her alanı AYRI AYRI değerlendir.
- Alanlardan BİR TANESİ BİLE atıflıysa, GENEL SONUÇ ATIFLIDIR.
- Hiçbir alan atıflı değilse sonuç TEMİZDİR.

TEMEL TANIM
ATIF:
Bir alanın, başka bir metne, belgeye, kaynağa veya
aynı kayıt içindeki başka bir alana gönderme yapmasıdır.

KESİN ATIF SAYILIR
- bk., bakınız, kaynak, referans vb. ifadeler
- kitap, makale, web sitesi, yazı, eser yönlendirmeleri
- “yukarıda belirtildiği gibi”, “ana cevapta geçtiği üzere” tarzında yönlendirmeler
- aynı kayıt içindeki başka bir alana (özellikle full_answer) açık veya örtük gönderme
- başka bir metne dayanarak hüküm kurma
- Alan kendi başına anlamlı değilse ATIF VAR SAY.
⚠️ “bu metin”, “ilk soruda”, “daha önce değinildi” gibi bağlam referansları
içeren alanlar ATIFLI kabul edilir.

KESİN ATIF SAYILMAZ
- Ayetler
- Hadisler
- Sahabe veya âlim görüşleri
- Fıkhî analizler
- Alanın kendi içinde tutarlı ve bağımsız olması

⚠️ DİNİ DELİLLER (ayet, hadis) HİÇBİR ŞEKİLDE ATIF DEĞİLDİR.
⚠️ DİNİ AÇIKLAMALAR veya konuyu pekiştiren metinler ATIF DEĞİLDİR.

KURALLAR
- Alanları SADECE kendi içeriğine göre değerlendir.
- Alanlar arası ilişki kurma, sadece açık gönderme varsa atıf say.
- Yorum ekleme.
- Açıklama yapma.
- Tahmin yürütme.
- ŞÜPHE VARSA MUTLAKA TEMİZ DE.

ÇIKTI KURALI
EĞER KAYIT ATIFLI İSE:
Sadece şu formatta yaz:
atıflı | alan_adı: kısa neden

EĞER KAYIT TEMİZ İSE:
Sadece şu kelimeyi yaz:
temiz

Bunun dışında HİÇBİR ŞEY yazma.
"""

def degerlendir_metni(metin: str) -> Dict[str, str]: #metni değerlendiriyor
    global FATAL_GEMINI_ERROR, FATAL_GEMINI_REASON #global değişkenler

    if not metin or not metin.strip(): #metin boşsa
        return {"etiket": "temiz", "neden": ""} #temiz olarak işaretliyor

    model = genai.GenerativeModel("gemini-1.0-flash")  # doğru ad
    prompt = f"{SYSTEM_PROMPT}\nMetin:\n{metin}" #istem oluşturuluyor

    ETIKET_TEMIZ = "temiz" 
    ETIKET_ATIFLI = "atıflı" #atıflı etiket

    def temiz_sonuc(): #temiz sonuç döndürüyor
        return {"etiket": ETIKET_TEMIZ, "neden": ""} 

    for attempt in range(MAX_RETRIES): #maksimum deneme sayısı kadar deniyor
        try: #deneme bloğu
            response = model.generate_content(prompt) #modelden yanıt alınıyor
            text = (getattr(response, "text", "") or "").strip().lower() #yanıt metni alınıyor ve işleniyor

            # fallback – boş cevap
            if not text: #yanıt boşsa
                print("⚠️ boş cevap → temiz") #boş cevap uyarısı
                return temiz_sonuc() #temiz sonuç döndürüyor

            if text.startswith(ETIKET_ATIFLI): #yanıt atıflı ise
                _, _, neden = text.partition("|") #neden kısmını ayırıyor
                return {"etiket": ETIKET_ATIFLI, "neden": neden.strip()} #atıflı olarak işaretliyor

            if text == ETIKET_TEMIZ: #yanıt temiz ise
                return temiz_sonuc() #temiz olarak işaretliyor

            # format dışı her şey → temiz
            print(f"⚠️ format dışı cevap → temiz: {text}") #format dışı cevap uyarısı
            return temiz_sonuc() #temiz olarak işaretliyor

        except Exception as e: #hata bloğu
            with open("gemini_errors.log", "a", encoding="utf-8") as log_file: #hata log dosyası
                log_file.write(
                    f"[{attempt+1}/{MAX_RETRIES}] {repr(e)}\n\n"
                ) #hata kaydını log dosyasına yazıyor

            if attempt < MAX_RETRIES - 1: #henüz deneme hakkı varsa
                print(
                    f"⚠️ GEMINI HATASI ({attempt+1}/{MAX_RETRIES}): "
                    f"{str(e).splitlines()[0]} → {RETRY_DELAY}s sonra tekrar"
                ) #hata uyarısı
                time.sleep(RETRY_DELAY) #belirli bir süre bekliyor
            else: #son deneme hakkıysa
                FATAL_GEMINI_ERROR = True #fatal hata durumunu işaretliyor
                FATAL_GEMINI_REASON = str(e).splitlines()[0] #fatal hata sebebini kaydediyor
                print(
                    f"⛔ GEMINI FATAL ERROR nedeniyle işlem durduruldu: "
                    f"{FATAL_GEMINI_REASON}"
                ) #fatal hata uyarısı
                return temiz_sonuc() #temiz olarak işaretliyor

def atiflari_kontrol_et(dosya_yolu: str): #dosyadaki atıfları kontrol ediyor
    if not os.path.exists(dosya_yolu): #dosya yoksa
        print("Dosya bulunamadı") #uyarı veriyor
        return #işlemi sonlandırıyor

    with open(dosya_yolu, "r", encoding="utf-8") as f: #dosyayı açıyor
        try: #dosyadaki verileri yüklüyor
            veriler: List[Dict[str, Any]] = json.load(f) #dosyadaki verileri yüklüyor
        except json.JSONDecodeError as e: #JSON hatası varsa
            print("❌ JSON dosyası bozuk") #uyarı veriyor
            print(f"Hata: {e}") #hata mesajı
            return #işlemi sonlandırıyor

    toplam = len(veriler) #toplam kayıt sayısını alıyor
    print(f"Toplam {toplam} kayıt bulundu\n") #toplam kayıt sayısını yazdırıyor

    atiflar = [] #atıflı kayıtlar için liste
    temizler = [] #temiz kayıtlar için liste

    log = {}        # log için sözlük
    veri_map = {}  # veri haritası için sözlük

    islenen_idler = set()  # işlenen ID'leri tutan küme


    for i, veri in enumerate(veriler, start=1):

        if FATAL_GEMINI_ERROR:
            print("⛔ GEMINI FATAL ERROR nedeniyle işlem durduruldu.")
            print("💾 Şu ana kadar işlenen veriler kaydediliyor...")

            kaydet("atif.json", atiflar)
            kaydet("temiz.json", temizler)

            print(f"⛔ DURDUĞU KAYIT: {i}")
            print(f"⛔ HATA SEBEBİ: {FATAL_GEMINI_REASON}")
            break

        veri_id = str(veri.get("veri_id", i)) #kayıt ID'sini alıyor

        if veri_id in islenen_idler: #tekrar eden ID kontrolü
            print(f"⚠️ Tekrar eden ID atlandı: {veri_id}") #tekrar eden ID uyarısı
            continue #sonraki kayda geçiyor

        islenen_idler.add(veri_id) #işlenen ID'yi kümeye ekliyor

        alanlar = [ 
            ("full_answer", veri.get("full_answer")),
            ("short_answer", veri.get("short_answer")),
            ("base_question", veri.get("base_question")),
            ("alt_question1", veri.get("alt_question1")),
            ("alt_question2", veri.get("alt_question2")),
        ] #alanları tanımlıyor

        etiket = "temiz" #varsayılan etiket
        neden = "" #neden boş

        birlesik_metin = []

        for alan_adi, alan_metni in alanlar:
            if not alan_metni or not alan_metni.strip():
                continue
            birlesik_metin.append(f"[{alan_adi}]\n{alan_metni}")

        if not birlesik_metin:
            sonuc = {"etiket": "temiz", "neden": ""}
        else:
            sonuc = degerlendir_metni("\n\n".join(birlesik_metin))

        etiket = sonuc["etiket"]
        neden = sonuc["neden"]

        log[veri_id] = etiket #log kaydını tutuyor
        veri_map[veri_id] = veri #veri haritasını tutuyor

        print(f"[{i}/{toplam}] ID:{veri_id} -> {etiket.upper()}") #işlem durumunu yazdırıyor
 
        if etiket == "atıflı": #etiket atıflı ise
            veri["atif_gerekcesi"] = neden #neden bilgisini kaydediyor
            atiflar.append(veri) #atıflı listeye ekliyor
        else: #etiket temiz ise
            temizler.append(veri) #temiz listeye ekliyor

    def kaydet(ad, data): #verileri kaydediyor
        with open(ad, "w", encoding="utf-8") as f: #dosyayı açıyor
            json.dump(data, f, ensure_ascii=False, indent=4) #verileri dosyaya yazıyor
        print(f"{ad} kaydedildi ({len(data)} kayıt)") #kaydetme durumunu yazdırıyor

    kaydet("atif.json", atiflar) #atıflı kayıtları kaydediyor
    kaydet("temiz.json", temizler) #temiz kayıtları kaydediyor

    print("\nÖZET") #özet bilgilerini yazdırıyor
    print(f"Toplam : {toplam}") #toplam kayıt sayısı
    print(f"Atıflı : {len(atiflar)}") #atıflı kayıt sayısı
    print(f"Temiz  : {len(temizler)}") #temiz kayıt sayısı
 
    print("\n--- LOG SORGULAMA MODU ---") #log sorgulama modunu başlatıyor
    print("Komutlar:") #komutları yazdırıyor
    print("  atif   → Atıflı kayıtların ID'leri") #atıflı ID'leri komutu
    print("  temiz  → Temiz kayıtların ID'leri") #temiz ID'leri komutu
    print("  id 34  → 34 numaralı kaydın tüm verisi") #id detay komutu
    print("Çıkış için ENTER veya 'q'\n") #çıkış talimatı

    while True: #sonsuz döngü
        komut = input(">>> ").strip().lower() #kullanıcıdan komut alıyor

        # ÇIKIŞ
        if komut == "" or komut == "q": #çıkış komutu
            print("Çıkılıyor.") #çıkış mesajı
            break #döngüyü kırıyor

        # ATIFLI ID'LER
        elif komut == "atif": #atıflı ID'leri komutu
            bulunan = [i for i, e in log.items() if e == "atıflı"] #atıflı ID'leri buluyor
            if bulunan: #atıflı ID'ler varsa
                print("ATIFLI ID'ler:", ", ".join(bulunan)) #atıflı ID'leri yazdırıyor
            else: 
                print("Atıflı kayıt yok.") #atıflı kayıt yok mesajı

        # TEMİZ ID'LER
        elif komut == "temiz": #temiz ID'leri komutu
            bulunan = [i for i, e in log.items() if e == "temiz"] #temiz ID'leri buluyor
            if bulunan: #temiz ID'ler varsa
                print("TEMİZ ID'ler:", ", ".join(bulunan)) #temiz ID'leri yazdırıyor
            else: 
                print("Temiz kayıt yok.") #temiz kayıt yok mesajı
 
        # ID DETAY
        elif komut.startswith("id "): #id detay komutu
            aranan_id = komut.split(" ", 1)[1] #aranan ID'yi alıyor
 
            if aranan_id in veri_map: #aranan ID veri haritasında varsa
                print("\n==============================") #ayırıcı çizgi
                print(f"ID: {aranan_id}") #ID'yi yazdırıyor
                print(f"Durum: {log[aranan_id].upper()}") #durumu yazdırıyor
                print("Veri:") #veri başlığı
                print(json.dumps(veri_map[aranan_id], ensure_ascii=False, indent=4)) #veriyi yazdırıyor
                print("==============================\n") #ayırıcı çizgi
            else: #aranan ID yoksa
                print("❌ ID bulunamadı.") #ID bulunamadı mesajı
 
        else: # geçersiz komut
            print("Geçersiz komut.") #geçersiz komut mesajı

if __name__ == "__main__": #programın ana fonksiyonu
    atiflari_kontrol_et("DOSYA_ADI_GİR.json") 