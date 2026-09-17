# AYEC Pro gorusme kaydi - 2026-09-13 devam

## Kalici sohbet kurali

Kullanici bundan sonra yeni sohbet penceresi actiginda AYEC Pro\Konusmalar klasorundeki en son tarihli Markdown kaydi okunacak ve verilen prompt bu baglamla ele alinacak.

Hata tespit edildiginde beklemeden duzeltme uygulanacak; kullaniciya en sonda yapilan degisiklikler, testler ve kalan riskler raporlanacak.

## Bu gorusmede yapilanlar

- Canli program ekranlarindan PNG yakalamalari `Web_Arayuzu\web\assets\live-captures` klasorune alindi.
- Canli GIF dosyalari icin `artifacts\AYECPro_Live_GIF_Update_20260913.zip` sunucu paketi hazirlandi.
- `Web_Arayuzu\web\app.js` icinde tanitim medyasi eski yapay GIF referanslarindan canli GIF referanslarina yonlendirildi.
- Dashboard alt filtre kartlarinda ust durum kartlariyla tekrar eden filtreler kaldirildi.
- Dashboard filtre duzeni kalan 9 karti tek satirda gosterecek sekilde guncellendi.
- Randevu ekranindaki Planlama Kanbani ana gorunumden gizlendi; ust bara Planlanan Randevular butonu eklendi.
- Buton, bu haftanin tamamlanmamis ve iptal edilmemis randevularini ayri ModernDialog penceresinde listeliyor.
- Servis listesinden Model veya Urun Grubu hucrelerine cift tiklayinca Teknisyen Paneli acilisinda gorunen kucuk pencere sorunu icin birden fazla acilis kilidi eklendi.
- Ana pencere tarafinda ayni takip numarasina ait panel acilisi 10 saniye boyunca tekrar engelleniyor.
- Satirdan acilista cihaz secim penceresinin yanlislikla acilmasi engellendi.
- Buna ragmen kullanicinin son testinde kucuk pencere 4-5 kez gorunmeye devam ediyor. Bunun animasyon degil, Teknisyen Paneli olusturulurken gorunen gecici top-level pencere veya panel olusturma zincirindeki ayri bir pencere olabilecegi tespit edildi.

## Guncellenen kaynak dosyalari

- `src\ui\pages\dashboard_page.py`
- `src\ui\pages\_dashboard_dialog_mixin.py`
- `src\ui\mixins\_main_window_func_mixin.py`
- `src\ui\pages\appointments_page.py`

## Kontroller

- `python -m py_compile src/ui/pages/dashboard_page.py`
- `python -m py_compile src/ui/pages/_dashboard_dialog_mixin.py`
- `python -m py_compile src/ui/mixins/_main_window_func_mixin.py`
- `python -m py_compile src/ui/pages/appointments_page.py`
- `python tools/mojibake_guard.py`
- `python tools/ascii_diff_guard.py`

Tum kontroller basarili.

## Bekleyen teknik is

Model veya Urun Grubu hucre cift tiklamasinda Teknisyen Paneli acilirken gorunen kucuk pencerenin gercek sinifi kesin olarak tespit edilmeli. `Baslat.bat` dogrudan `.venv_active\Scripts\python.exe Main.py` calistiriyor; bu nedenle yeni exe build gerekmiyor. Sorun kaynak Python calisma akisinda incelenmeye devam etmeli. Pencere tamamen hazirlanmadan gorunuyorsa `ModernDialog` veya `TechnicianPanel` olusturma akisinda gecici gizleme uygulanmali.

## Guvenlik

Parolalar, SMTP sifreleri ve yonetici kimlik bilgileri bu kayda yazilmaz.
