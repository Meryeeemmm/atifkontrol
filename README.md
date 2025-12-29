````markdown
# Atıf Kontrol Sistemi

Bu proje, JSON formatında kayıtlı verileri analiz ederek **atıflı** veya **temiz** olarak sınıflandıran bir Python uygulamasıdır. Google Gemini (Generative AI) modeli kullanılarak her bir kayıt, belirtilen alanlar üzerinden değerlendirilmektedir.

---

## Özellikler

- JSON dosyalarındaki kayıtları alan bazında analiz eder.
- Kayıtların “atıflı” mı yoksa “temiz” mi olduğunu belirler.
- Atıflı kayıtlar için neden bilgisini kaydeder.
- Log dosyası oluşturarak hataları takip eder.
- Windows sistemlerde ekranın kapanmasını engelleyen özellik içerir.
- Kullanıcı, işlenen kayıtların ID’lerini sorgulayabilir:
  - `atif` → Atıflı kayıtların ID’leri
  - `temiz` → Temiz kayıtların ID’leri
  - `id <numara>` → Belirli ID’nin tüm verisi

---

## Kullanım

1. Gereksinimler:
   - Python 3.10+
   - `google-generativeai` kütüphanesi
   - GEMINI_API_KEY veya API_KEYS listesi

2. Terminalden virtual environment’i aktifleştirin:

```powershell
& .venv/Scripts/Activate.ps1
````

3. Kodun başında `DOSYA_ADI_GİR.json` yerine analiz edilecek JSON dosyasının adını girin.

4. Programı çalıştırın:

```powershell
python atifkontrol.py
```

5. İşlem tamamlandıktan sonra:

* `atif.json` → Atıflı kayıtlar
* `temiz.json` → Temiz kayıtlar
* `gemini_errors.log` → Hata logları (varsa)

6. Konsol üzerinden log sorgulama modu ile veri detaylarını inceleyebilirsiniz.

---

## Örnek JSON Yapısı

```json
[
  {
    "veri_id": "1",
    "full_answer": "Bu bir örnek metindir.",
    "short_answer": "Örnek",
    "base_question": "Soru 1",
    "alt_question1": "Alt Soru A",
    "alt_question2": "Alt Soru B"
  },
  {
    "veri_id": "2",
    "full_answer": "Başka bir örnek metin.",
    "short_answer": "Örnek 2",
    "base_question": "Soru 2",
    "alt_question1": "",
    "alt_question2": ""
  }
]
```

---

## Alanlar

Kod, aşağıdaki alanları kontrol eder:

* `full_answer`
* `short_answer`
* `base_question`
* `alt_question1`
* `alt_question2`

---

## Önemli Notlar

* Eğer bir alan boş veya yalnızca bağlam referansları içeriyorsa otomatik olarak “temiz” olarak değerlendirilir.
* Dini içerikler (ayet, hadis, sahabe/âlim görüşleri) **atıf sayılmaz**.
* Alanlar arası ilişki kurulmaz, yalnızca açık gönderme varsa atıf kabul edilir.

---

## Örnek Komutlar (Log Sorgulama Modu)

```text
>>> atif     # Atıflı ID’leri gösterir
>>> temiz    # Temiz ID’leri gösterir
>>> id 34    # 34 numaralı kaydın tüm verisini gösterir
>>> q        # Çıkış
```

