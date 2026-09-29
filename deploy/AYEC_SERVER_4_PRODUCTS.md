# AYEC dört ürün sunucu yerleşimi

Sunucuda her ürün aynı Web Arayuzu API'sini kullanır; lisans, tenant, cihaz ve yedek kapsamı `product_code` ile ayrılır.

| Ürün | product_code | Sunucu klasörü | Veritabanı | Yedek klasörü |
|---|---|---|---|---|
| AYEC Pro Teknik Servis | `teknik_servis` | `AYEC Pro Teknik Servis` | `Teknik-Servis-AYEC.db` | `Teknik-Servis-AYEC` |
| AYEC Pro Barkod Okuyucu | `barkod_okuyucu` | `AYEC Pro Barkod Okuyucu` | `Barkod-AYEC.db` | `Barkod-AYEC` |
| AYEC Pro Elek | `elek` | `AYEC Pro Elek` | `Elek-AYEC.db` | `Elek-AYEC` |
| AYEC Pro Ciro | `ciro` | `AYEC Pro Ciro` | `Ciro-AYEC.db` | `Ciro-AYEC` |

Her kurulum kendi `tenant_id`, `installation_id` ve `hardware_id` değerine sahip olur. Admin panelinde ürün filtresi bu dört kodu ayrı ayrı göstermelidir. Aynı firma birden fazla ürün kullanabilir; tenant ve cihaz kimliği ürün koduyla birlikte eşleştirilir.

## Yayınlama

1. AYEC Pro `Web_Arayuzu` kaynakları sunucuya kopyalanır.
2. `ecosystem/products.json` güncel dosya olarak dağıtılır.
3. Web Arayuzu servisi yeniden başlatılır.
4. IIS/ARR `lisans.ayecpro.com` HTTPS binding'i aynı Web Arayuzu servisine yönlendirir.
5. Her ürün kendi masaüstü paketini ayrı klasörde çalıştırır.

## Doğrulama

`https://lisans.ayecpro.com/api/license/catalog` katalog döndürmelidir. Cihaz lisans talebi `POST /api/license/orders/device` ile `201` dönmeli; Admin panelinde `product_code` filtresine göre görünmelidir. Bu dosya sunucu kaynaklarını değiştirmez; yayın öncesi paket ve veritabanı yedeği alınmalıdır.
