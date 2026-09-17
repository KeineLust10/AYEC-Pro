# AYEC Pro gorusme kaydi

Tarih: 2026-09-13

## Kalici devam kurali

Kullanici bundan sonra yeni bir konusma penceresi actiginda, projedeki `Konusmalar` klasorunde bulunan en son tarihli Markdown kaydi okunacak ve calismaya bu baglam kullanilarak devam edilecek. Turkce klasor adi da ayni kaydi tasir.

Yeni bir konusma sonunda yapilan onemli degisiklikler, testler, kararlar ve bekleyen isler yine bu klasore yeni bir Markdown kaydi olarak eklenecek.

## Proje ve erisim baglami

- Proje: AYEC Pro
- Yerel calisma klasoru: `C:\Users\yedek\Desktop\yapay zeka\AYEC Pro`
- Ana masaustu/teknik servis uygulamasi: `http://85.117.239.60/`
- Kurumsal web sitesi: `https://ayecpro.com/`
- Web paneli: `https://panel.ayecpro.com/`
- Sunucu tarafinda kullanilan uygulama yolu: `C:\Web\_Arayuzu`
- Veritabani yolu: `C:\Web\_Arayuzu\data\ayecpro.db`

## Daha once yapilan baslica calismalar

- Web sitesi AYEC Pro urun ve tanitim yapisina gore duzenlendi.
- Panel ve ana site icin giris, kayit, programlar ve lisans akislarinin ayni site uzerinden calismasi hedeflendi.
- Yonetici yetkisi yalnizca `ayecpro@gmail.com` hesabina verilecek sekilde duzenlendi; yeni/test kullanicilar yonetici olmamali.
- Resmi gonderici adresi `info@ayecpro.com`, destek adresi `destek@ayecpro.com` olarak belirlendi.
- Turhost SMTP ayarlari sunucuda basariyla dogrulandi. Google OAuth istemci kimligi bos birakildiginda Google ile giris devre disi kabul edildi.
- SSL kurulumu ve DNS dogrulama sureci Turhost/DirectAdmin uzerinden yapildi; `panel.ayecpro.com` icin sertifika uretimi sirasinda IIS binding hatasi goruldu ve sonrasinda yeniden kurulum/test yapildi.
- Sunucu guncelleme komut dosyalari kullanildi; PowerShell calistirma politikasi icin dogru komut:
  `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force`
- Test verileri programa yuklendi: yaklasik 200 musteri, 20 servis cihazi, randevular, 170 stok kalemi ve teklif/finans hareketleri.
- Finans ekraninda test verileri goruldu: toplam gelir, gider, net bakiye ve yuzlerce hareket kaydi.
- Teklif ekraninda 25 test teklifi goruldu.
- Kullanici, program menulerinden gercek ekran goruntulerinin alinmasini ve web/panel/masaustu tanitim alanlarinda GIF olarak kullanilmasini istedi.

## Son yapilan canli ekran yakalamalari

Canli uygulama `http://85.117.239.60/` icinden veri degistirmeden su ekranlar acildi ve ekran goruntuleri alindi:

- Genel bakis / servis operasyonu
- Musteri listesi
- Stok / siparis yonetimi
- Finans ozeti
- Tum teklifler
- Servis yonetimi alt menuleri incelendi; randevular, saha haritasi, servis kayitlari ve teknisyen paneli secenekleri goruldu.

## GIF ve gorsel calismasi icin bekleyen durum

Kullanici eski veya yapay uretilmis gorsellerin kullanilmasini istemiyor. Gorseller canli program ekranlarindan alinmali.

Canli tarayici ekran goruntuleri bu oturumda goruntulendi; ancak guvenli tarayici ortami bu PNG karelerini yerel dosya sistemine aktarmaya izin vermedi. Bu nedenle henuz kalici PNG/GIF dosyasi olusturulup web veya masaustu kaynaklarina eklenmedi.

Mevcut eski varliklar arasinda kullanilmamasi gereken GIF dosyalari bulunuyor:

- `Web_Arayuzu\web\assets\ayec-workflow.gif`
- `Web_Arayuzu\web\assets\ayec-secure-access.gif`
- `Web_Arayuzu\web\assets\ayec-license-center.gif`

Canli yakalamalar icin bos klasor olusturuldu:

- `Web_Arayuzu\web\assets\live-captures`

Bu klasore henuz dosya kaydedilmedi.

## Bir sonraki adim

1. Yeni konusma basladiginda bu kaydi oku.
2. Kullanici canli ekranlari PNG olarak dosya halinde yuklerse, bunlari gercek ekran goruntulerinden GIF'lere donustur.
3. GIF'leri web sitesi, panel ve masaustu uygulamasinda ilgili alanlara yerlestir.
4. Kaynak degisikligi yapildiginda `python tools/mojibake_guard.py` ve `python tools/ascii_diff_guard.py` komutlarini calistir.
5. Sunucuya yayinlama gerekiyorsa olusturulan paketi kullaniciya bildir ve sunucu guncelleme adimlarini ver.

## Guvenlik notu

Parolalar bu kayda yazilmaz. SMTP ve yonetici hesap bilgileri kaynak dosyalara veya Markdown kayitlarina acik metin olarak eklenmemeli.
