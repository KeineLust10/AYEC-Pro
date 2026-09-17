# -*- coding: utf-8 -*-

"""
AYEC Pro - Kapsamlı Ürün Test Verisi
=====================================
Kategoriler:
  1. Bilgisayar Güvenlik Sistemleri  (50+ ürün)
  2. Akıllı Ev Sistemleri            (50+ ürün)
  3. Bilgisayar Bileşenleri          (50+ ürün)

Çalıştır: python scripts/seed_urun_test_data.py
"""

import sys
import os

# Proje kök dizini
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import sqlite3
from datetime import datetime
from src.utils.path_helper import PathHelper

# ─── Bağlantı ──────────────────────────────────────────────────────────────────
DB_PATH = PathHelper.get_db_path("ayecpro.db")
NOW     = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ─── Ürün Kataloğu ─────────────────────────────────────────────────────────────

# fmt: off
GUVENLIK_SISTEMLERI = [
    # (isim, alt_kategori, stok, alış_fiyatı, satış_fiyatı, raf, kod, açıklama)
    ("Hikvision DS-2CD2143G2 4MP Dome IP Kamera",    "IP Kamera",        25, 1850, 2750, "KAM-01", "HK-4MP-DOME",  "H.265+, WDR, IP67, IK10, PoE"),
    ("Hikvision DS-2CD2T47G2 4MP Bullet IP Kamera",  "IP Kamera",        20, 2100, 3200, "KAM-02", "HK-4MP-BUL",   "4MP, 60m IR, H.265+, IP67"),
    ("Dahua IPC-HDW3849H 8MP Eyeball Kamera",        "IP Kamera",        15, 2950, 4400, "KAM-03", "DAH-8MP-EYE",  "8MP 4K, AI, Fixed Lens"),
    ("Hikvision DS-2DE4425IW-DE 4MP PTZ Kamera",     "PTZ Kamera",        8, 8500,12500, "KAM-04", "HK-4MP-PTZ",   "25x optik zoom, H.265+, PoE+"),
    ("Dahua SD49425XB-HNR 4MP PTZ Kamera",           "PTZ Kamera",        6, 9200,13800, "KAM-05", "DAH-4MP-PTZ",  "25x optik zoom, AI, SMD Plus"),
    ("Axis P3245-V Fixed Dome Kamera",               "IP Kamera",        10, 4200, 6500, "KAM-06", "AXS-FIX-DOM",  "2MP, HDTV 1080p, Lightfinder"),
    ("Reolink RLC-810A 4K Kamera",                   "IP Kamera",        18, 1400, 2100, "KAM-07", "REO-4K",       "8MP, kişi/araç algılama, PoE"),
    ("Uniview IPC3614SB-ADF40KM 4MP Kamera",         "IP Kamera",        12, 1750, 2650, "KAM-08", "UNV-4MP",      "LightHunter, H.265, Smart IR"),

    ("Hikvision DS-7608NXI-K2 8 Kanal NVR",         "NVR / DVR",        10, 3200, 4800, "NVR-01", "HK-8CH-NVR",   "4K, 80Mbps, 2HDD, Deep Learning"),
    ("Dahua NVR4116HS-EI 16 Kanal NVR",             "NVR / DVR",         8, 3800, 5700, "NVR-02", "DAH-16CH-NVR", "16 CH, 4K, WizSense AI, 1HDD"),
    ("Hikvision DS-7216HGHI-K2 16 Kanal DVR",       "NVR / DVR",        10, 2900, 4350, "NVR-03", "HK-16CH-DVR",  "TurboHD 4.0, 1080p Lite, 2HDD"),
    ("Dahua XVR5116H-I3 16 Kanal Pentabrid DVR",    "NVR / DVR",         7, 3400, 5100, "NVR-04", "DAH-16CH-DVR", "5MP, WizSense, 1HDD"),

    ("Seagate SkyHawk 2TB Güvenlik HDD",             "Depolama",         30, 1200, 1800, "DEP-01", "SEA-SH-2TB",   "7200 RPM, 256MB, CCTV için"),
    ("WD Purple 4TB Gözetleme HDD",                  "Depolama",         20, 2200, 3300, "DEP-02", "WD-PUR-4TB",   "AllFrame 4K, 64 kamera desteği"),
    ("Seagate SkyHawk AI 8TB HDD",                   "Depolama",         10, 5500, 8250, "DEP-03", "SEA-SH-8TB",   "AI NVR için, 16 akış desteği"),

    ("Paradox MG5050 Hırsız Alarm Paneli",           "Alarm Paneli",     12, 1850, 2800, "ALR-01", "PAR-MG5050",   "8 zon, 32'ye kadar genişleme"),
    ("DSC PC1832 Alarm Merkezi",                     "Alarm Paneli",      8, 2100, 3150, "ALR-02", "DSC-PC1832",   "8-32 zon, PowerSeries"),
    ("Paradox PMD2 Hareket Sensörü PIR",             "Sensör",           50, 180,   280, "SEN-01", "PAR-PIR",      "12m, 90°, pet bağışıklığı"),
    ("Bosch Blue Line PIR Sensörü",                  "Sensör",           40, 220,   340, "SEN-02", "BSH-PIR",      "12m, 90°, Blue Line Gen2"),
    ("DSC LC-100-PI Dual Tec Sensörü",               "Sensör",           30, 320,   490, "SEN-03", "DSC-DUAL",     "PIR+Mikro, 12m, False Alarm Onayı"),
    ("Paradox NV80 Dijital Hareket Sensörü",         "Sensör",           35, 250,   385, "SEN-04", "PAR-NV80",     "80° geniş açı, 12m"),
    ("DSC WS4939 Kablosuz Duman Dedektörü",          "Yangın",           25, 420,   650, "YNG-01", "DSC-DUMAN",    "Kablosuz, PowerSeries uyumlu"),
    ("Bosch FAP-462-TD Adresli Duman Sensörü",       "Yangın",           20, 680, 1020, "YNG-02", "BSH-DUMAN",    "Adresli, izolasyon modülü"),
    ("Manyetik Kontak MC-02 Kapı/Pencere Sensörü",  "Sensör",          100,  45,    75, "SEN-05", "MC-02",        "Recessed mount, ABS gövde"),

    ("Hikvision DS-K1T671TM Yüz Tanıma Terminal",   "Geçiş Kontrol",     5,12000,18000, "GEÇ-01", "HK-FACE-TRM",  "2MP, 2000 yüz, -30°C~+60°C"),
    ("ZKTeco SpeedFace-V5L Yüz+Iris Terminal",       "Geçiş Kontrol",     4,14500,21750, "GEÇ-02", "ZKT-FACE-V5L", "30000 yüz, 10000 iris, PoE"),
    ("Suprema BioStation A2 Parmak İzi Terminal",    "Geçiş Kontrol",     6, 8500,12750, "GEÇ-03", "SUP-BSA2",     "1:N parmakizi+kart+yüz"),
    ("HID iCLASS SE RK40 RFID Okuyucu",             "Geçiş Kontrol",    15, 1850, 2775, "GEÇ-04", "HID-RK40",     "125kHz+13.56MHz çoklu teknoloji"),
    ("Hikvision DS-K2801 Kart Erişim Kontrol",       "Geçiş Kontrol",    10, 2200, 3300, "GEÇ-05", "HK-K2801",     "2 kapı, 100.000 kart, RS-485"),

    ("BenQ LW500 5000 Lümen Lazer Projeksiyon",      "Monitör/Ekran",     5, 9800,14700, "EKR-01", "BNQ-LW500",    "WXGA, %20.000 saat, %240 parlaklık"),
    ("Samsung 32\" QHD Güvenlik Monitörü",           "Monitör/Ekran",     8, 4500, 6750, "EKR-02", "SAM-32-QHD",   "2560x1440, IPS, HDMI/DP, CCTV"),
    ("Hanwha QNV-8080R Vandal Dome 5MP",             "IP Kamera",        12, 2800, 4200, "KAM-09", "HNW-5MP-DOM",  "5MP, IR 30m, IP66, IK10, NEMA4X"),

    ("APC SMT1500I UPS 1500VA",                      "UPS/Güç",          10, 5500, 8250, "UPS-01", "APC-SMT1500",  "1500VA/1000W, Smart-UPS, LCD"),
    ("Powerware 5115 1000VA UPS",                    "UPS/Güç",          12, 3200, 4800, "UPS-02", "PWR-1000VA",   "1000VA, 6 çıkış, USB/RS-232"),
    ("12V 7Ah Bakımsız Akü",                         "UPS/Güç",          50,  185,  290, "AKU-01", "BAT-12V7AH",   "VRLA, alarm sistemleri için"),
    ("12V 18Ah Bakımsız Akü",                        "UPS/Güç",          30,  380,  570, "AKU-02", "BAT-12V18AH",  "VRLA, derin deşarj"),

    ("CAT6 UTP Kablo 305m Bobin",                   "Kablo",            15,  650,  975, "KBL-01", "CAT6-305M",    "23AWG, 4 çift, LSZH"),
    ("RG59 Koaksiyel Kablo 100m",                    "Kablo",            20,  280,  420, "KBL-02", "RG59-100M",    "75Ohm, CCTV kablo"),
    ("Screened CAT6A SFTP 305m Bobin",               "Kablo",            10, 1050, 1575, "KBL-03", "CAT6A-305M",   "10Gbps, %100 bakır, LSZH"),
    ("BNC Konnektör Sıkıştırma Tip (100'lü)",       "Aksesuar",         30,  190,  285, "AKS-01", "BNC-100",      "RG59/RG6 uyumlu, altın kaplama"),
    ("Dağıtım Kutusu 12'li Kamera Güç Kaynağı",     "Aksesuar",         15,  580,  870, "AKS-02", "PWR-12CH",     "12x1A, 12VDC, sigortalı"),

    ("Hikvision DS-KV6113-WPE1 Video Intercom",     "Interkom",          8, 4200, 6300, "INT-01", "HK-VID-INT",   "2MP, IP, WiFi, IR, IP65"),
    ("Commax CDV-70H Video Kapı Zili",               "Interkom",         12, 2800, 4200, "INT-02", "CMX-VID70",    "7\" dokunmatik, gece görüş"),
    ("Fermax MARINE 3471 4+N Sistemi",               "Interkom",         10, 3500, 5250, "INT-03", "FRM-MRN3471",  "4+N bus, hands-free, entegre"),

    ("Safire SF-IPDOM8803IHA-2U8 8MP Kamera",        "IP Kamera",        14, 3200, 4800, "KAM-10", "SAF-8MP",      "4K, AcuSense, 60m IR"),
    ("Mobotix M73 Hemisferik 180° Kamera",           "IP Kamera",         5, 8500,12750, "KAM-11", "MOB-M73",      "4K hemisferik, 180°, -55°C"),
    ("Wisenet QNO-8080R 5MP IP Bullet Kamera",       "IP Kamera",        10, 3400, 5100, "KAM-12", "WNT-5MP-BUL",  "5MP, 50m IR, IP66, NEMA"),
    ("Vivotek IB9388-EHT 5MP Bullet Kamera",         "IP Kamera",         8, 4200, 6300, "KAM-13", "VVT-5MP-BUL",  "5MP, -55°C~+60°C, IP66, IK10"),
    ("Genetec Security Center Sunucu Lisansı",       "Yazılım",           5,15000,22500, "YZL-01", "GNT-SC-LIC",   "5 kamera, 1 yıl destek dahil"),
    ("Milestone XProtect Essential+ VMS Lisansı",   "Yazılım",           5,12000,18000, "YZL-02", "MLS-XPE-LIC",  "8 kanal, süresiz lisans"),
]

AKILLI_EV = [
    ("Samsung SmartThings Hub v3",                   "Merkez Hub",       15, 1200, 1800, "HUB-01", "SMS-STH-V3",   "Zigbee, Z-Wave, WiFi, BT 4.2"),
    ("Amazon Echo 4. Nesil Akıllı Hoparlör",         "Ses Asistanı",     20,  850, 1280, "SES-01", "AMZ-ECH4",     "Alexa, 360° ses, Zigbee Hub"),
    ("Google Nest Hub 2. Nesil",                     "Ses Asistanı",     15,  950, 1425, "SES-02", "GGL-NHUB2",    "7\" ekran, Google Assistant"),
    ("Apple HomePod mini",                           "Ses Asistanı",     12, 1450, 2175, "SES-03", "APL-HPDMINI",  "Siri, HomeKit hub, S5 çip"),
    ("Philips Hue Bridge v2",                        "Aydınlatma Hub",   20,  680, 1020, "AYD-01", "PHL-HUE-BRG",  "Zigbee, 50 ışık, uzak erişim"),

    ("Philips Hue White A60 E27 Akıllı Ampul",       "Akıllı Aydınlatma",50,  280,  420, "AYD-02", "PHL-HUE-A60",  "9W, 806lm, 2700K, Bluetooth"),
    ("LIFX BR30 Renkli Akıllı Ampul",                "Akıllı Aydınlatma",40,  380,  570, "AYD-03", "LFX-BR30",     "15W, RGBWW, WiFi, 1100lm"),
    ("Govee RGBICWW LED Şerit 5m",                   "Akıllı Aydınlatma",30,  420,  630, "AYD-04", "GVE-LED5M",    "RGBIC, WiFi+BT, müzik senkron"),
    ("Nanoleaf Shapes Hexagon Başlangıç Seti",       "Akıllı Aydınlatma", 8, 1800, 2700, "AYD-05", "NNL-HEX-9PK",  "9 panel, 16M renk, Matter"),
    ("Yeelight Smart LED Panel 60cm",               "Akıllı Aydınlatma",15,  750, 1125, "AYD-06", "YLT-PNL-60",   "WiFi, Alexa/Google, 24W"),

    ("Nest Learning Thermostat 3. Nesil",            "Termostat",        12, 2800, 4200, "TER-01", "GST-NLTH3",    "WiFi, öğrenen, enerji tasarrufu"),
    ("Honeywell T9 Akıllı Termostat",                "Termostat",        10, 2200, 3300, "TER-02", "HWL-T9",       "WiFi, oda sensörü dahil, RCHT8610"),
    ("Tado Kablosuz Akıllı Termostat",               "Termostat",         8, 1950, 2925, "TER-03", "TAD-WRLSS",    "Coğrafi konum, API, Alexa/Google"),
    ("Sensibo Sky Klima Kontrolcüsü",                "Klima Kontrolü",   20,  980, 1470, "KLM-01", "SEN-SKY",      "IR uyumlu, WiFi, enerji izleme"),
    ("Ambi Climate 2 AI Klima Kontrolü",             "Klima Kontrolü",   15,  850, 1275, "KLM-02", "AMB-CLM2",     "AI öğrenme, WiFi, Alexa/Google"),

    ("TP-Link Tapo P110 Akıllı Priz",                "Akıllı Priz",      50,  280,  420, "PRZ-01", "TPL-P110",     "Enerji izleme, WiFi, 2300W"),
    ("Meross MSS310 Akıllı Priz",                    "Akıllı Priz",      40,  250,  375, "PRZ-02", "MRS-MSS310",   "WiFi, HomeKit, Alexa, 16A"),
    ("Shelly Plus 1PM Akıllı Röle",                  "Akıllı Röle",      35,  380,  570, "ROL-01", "SHY-P1PM",     "WiFi, enerji izleme, 16A, DIN"),
    ("Sonoff ZBMINI-L Zigbee Röle",                  "Akıllı Röle",      40,  220,  330, "ROL-02", "SNF-ZBMINI",   "Nötr yok, Zigbee 3.0, kompakt"),
    ("NOUS A1T WiFi Akıllı Priz Çoklayıcı",          "Akıllı Priz",      25,  320,  480, "PRZ-03", "NUS-A1T",      "3 çıkış, 3 USB, enerji izleme"),

    ("Yale Assure Lock SL YRD256 Akıllı Kilit",      "Akıllı Kilit",      8, 4200, 6300, "KLT-01", "YAL-YRD256",   "Z-Wave, klavye, HomeKit"),
    ("Schlage Encode BE489WB Akıllı Kilit",          "Akıllı Kilit",      6, 4800, 7200, "KLT-02", "SCH-BE489WB",  "WiFi, 100 kod, alarm entegre"),
    ("August Smart Lock Pro AUG-SL05 4. Nesil",      "Akıllı Kilit",      8, 3600, 5400, "KLT-03", "AUG-SL05",     "Z-Wave+, August Connect WiFi"),
    ("Nuki Smart Lock 3.0 Pro",                      "Akıllı Kilit",      7, 3800, 5700, "KLT-04", "NUK-SL3P",     "WiFi, Matter, Nuki Opener uyum"),
    ("Reolink Argus 3 Pro Güneş Enerjili Kamera",    "Akıllı Kamera",    18, 1450, 2175, "KMR-01", "REO-ARG3P",    "4MP, güneş paneli, 2 yönlü ses"),

    ("Ring Video Doorbell Pro 2",                    "Akıllı Zil",       10, 2800, 4200, "ZIL-01", "RNG-VDB-PRO2", "1536p HDR, head-to-toe görüş"),
    ("Nest Doorbell (Wired, 2. Nesil)",              "Akıllı Zil",       10, 2600, 3900, "ZIL-02", "GST-DRBL2",    "1080p HDR, gece görüş, paket"),
    ("Eufy Security Video Doorbell E340",            "Akıllı Zil",       12, 2200, 3300, "ZIL-03", "EUF-E340",     "2K+, çift kamera, pil"),
    ("Aqara G4 Akıllı Video Zil",                    "Akıllı Zil",       15, 1800, 2700, "ZIL-04", "AQR-G4",       "1080p, HomeKit Secure Video"),

    ("Ecovacs Deebot T20 Omni Robot Süpürge",        "Akıllı Ev Aletleri",6, 8500,12750, "RBT-01", "ECV-T20OMNI",  "5000Pa, öz temizlik, YIKO ses"),
    ("iRobot Roomba j7+ Robot Süpürge",              "Akıllı Ev Aletleri",5, 9800,14700, "RBT-02", "IRB-J7PLUS",   "PrecisionVision, engel kaçınma"),
    ("Miele Scout RX3 Robot Süpürge",                "Akıllı Ev Aletleri",4,11500,17250, "RBT-03", "MIL-RX3",      "3D kamera, WLAN, uygulama"),
    ("Arlo Pro 4 XL Kablosuz Kamera",                "Akıllı Kamera",    12, 2400, 3600, "KMR-02", "ARL-PRO4XL",   "2K HDR, renkli gece görüş, WiFi"),
    ("Eve Energy Akıllı Priz HomeKit",               "Akıllı Priz",      30,  680, 1020, "PRZ-04", "EVE-ENR-PRZ",  "HomeKit, enerji izleme, Thread"),
    ("Wemo Stage Sahne Kontrolcüsü",                 "Otomasyon",        20,  580,  870, "OTO-01", "WMO-STAGE",    "HomeKit, 4 düğme, pil yok"),

    ("Aqara Hub M2",                                 "Merkez Hub",       18,  950, 1425, "HUB-02", "AQR-HUB-M2",   "Zigbee 3.0, Bluetooth, IR blaster"),
    ("Homey Pro 2023 Akıllı Ev Hub",                 "Merkez Hub",        6, 4800, 7200, "HUB-03", "HMY-PRO23",    "Zigbee, Z-Wave, Matter, Thread"),
    ("IKEA DIRIGERA Akıllı Ev Hub",                  "Merkez Hub",       15,  680, 1020, "HUB-04", "IKA-DIRIGERA", "Matter, Zigbee 3.0, SDK"),
    ("Sonoff NSPanel Pro Akıllı Panel",              "Kontrol Paneli",   20, 1250, 1875, "PNL-01", "SNF-NSPRO",    "3.95\" dokunmatik, Zigbee, WiFi"),
    ("Loxone Miniserver Gen 2",                      "Kontrol Paneli",    4,12000,18000, "PNL-02", "LXN-MINI-G2",  "Tam akıllı ev, KNX, PoE"),

    ("Fibaro Motion Sensor FGMS-001",                "Sensör",           35,  680, 1020, "SNS-01", "FIB-FGMS",     "Z-Wave+, PIR+sıcaklık+aydınlık"),
    ("Aqara Kapı/Pencere Sensörü P2",                "Sensör",           60,  250,  375, "SNS-02", "AQR-DW-P2",    "Zigbee, Matter, IP67"),
    ("Eve Door Kapı Sensörü HomeKit",                "Sensör",           40,  480,  720, "SNS-03", "EVE-DOOR",     "HomeKit, Thread, hız algılama"),
    ("Shelly H&T Gen3 Sıcaklık Sensörü",             "Sensör",           30,  380,  570, "SNS-04", "SHY-HT-G3",    "WiFi, battery/USB, MQTT"),
    ("Bosch Smart Home Sızıntı Sensörü",             "Sensör",           25,  680, 1020, "SNS-05", "BSH-LEAK",     "Zemin tipi, anında uyarı"),
    ("Netatmo Hava İstasyonu Akıllı Termometre",     "Sensör",           15, 1800, 2700, "SNS-06", "NTM-AIR-STN",  "İç/dış modül, CO2, hava nem"),

    ("Shelly Pro 3EM Enerji Sayacı",                 "Enerji Yönetimi",  12, 1850, 2775, "ENR-01", "SHY-P3EM",     "3 faz, 120A, WiFi, MQTT"),
    ("Schneider Electric Wiser Enerji Hub",          "Enerji Yönetimi",   8, 4200, 6300, "ENR-02", "SCH-WISER",    "Zigbee, 63A, gerçek zamanlı"),
    ("EVSE Pro 22kW AC EV Şarj İstasyonu",           "EV Şarj",           5,12500,18750, "EV-01",  "EVSE-PRO22",   "22kW, Tip 2, RFID, WiFi, OCPP"),
    ("Easee Home EV Şarj Cihazı 22kW",              "EV Şarj",           4,11800,17700, "EV-02",  "ESE-HOME22",   "22kW, Bluetooth, Easee Cloud"),
]

BILGISAYAR_BILESENLERI = [
    # Anakartlar
    ("ASUS ROG STRIX B650E-F GAMING Anakart",        "Anakart",          8, 6800, 10200, "MBD-01", "ASS-B650EF",   "AM5, DDR5, PCIe 5.0, WiFi 6E"),
    ("MSI MAG B760 TOMAHAWK WiFi D5 Anakart",        "Anakart",         10, 5200,  7800, "MBD-02", "MSI-B760TW",   "LGA1700, DDR5, ATX, WiFi 6E"),
    ("Gigabyte Z790 AORUS Elite AX Anakart",         "Anakart",          6, 7500, 11250, "MBD-03", "GBT-Z790AX",   "LGA1700, DDR5, PCIe 5.0, WiFi 6E"),
    ("ASRock B550M Steel Legend Anakart",            "Anakart",         12, 3200,  4800, "MBD-04", "ASR-B550M",    "AM4, DDR4, mATX, 2x M.2"),
    ("ASUS TUF GAMING B450M-PLUS II Anakart",        "Anakart",         15, 2800,  4200, "MBD-05", "ASS-B450MP",   "AM4, DDR4, mATX, USB 3.2"),
    ("MSI PRO B760M-P DDR4 Anakart",                "Anakart",         14, 2600,  3900, "MBD-06", "MSI-B760MP4",  "LGA1700, DDR4, mATX, iş"),
    ("Gigabyte B450 AORUS M Anakart",                "Anakart",         10, 2400,  3600, "MBD-07", "GBT-B450AM",   "AM4, DDR4, mATX, RGB Fusion"),

    # İşlemciler
    ("AMD Ryzen 5 7600X İşlemci",                    "İşlemci",         10, 5800,  8700, "CPU-01", "AMD-R5-7600X", "6C/12T, 4.7/5.3GHz, AM5, 105W"),
    ("Intel Core i5-13600K İşlemci",                 "İşlemci",         10, 5600,  8400, "CPU-02", "INT-I5-13600K","14C/20T, 3.5/5.1GHz, LGA1700"),
    ("AMD Ryzen 7 7700X İşlemci",                    "İşlemci",          8, 8500, 12750, "CPU-03", "AMD-R7-7700X", "8C/16T, 4.5/5.4GHz, AM5, 105W"),
    ("Intel Core i7-13700K İşlemci",                 "İşlemci",          6, 9800, 14700, "CPU-04", "INT-I7-13700K","16C/24T, 3.4/5.4GHz, LGA1700"),
    ("AMD Ryzen 9 7900X İşlemci",                    "İşlemci",          4,14500, 21750, "CPU-05", "AMD-R9-7900X", "12C/24T, 4.7/5.6GHz, AM5, 170W"),
    ("Intel Core i9-13900K İşlemci",                 "İşlemci",          3,20000, 30000, "CPU-06", "INT-I9-13900K","24C/32T, 3.0/5.8GHz, LGA1700"),
    ("AMD Ryzen 5 5600G APU İşlemci",               "İşlemci",         15, 3800,  5700, "CPU-07", "AMD-R5-5600G", "6C/12T, Vega 7, AM4, 65W"),

    # RAM
    ("Corsair Vengeance DDR5 32GB 5600MHz",          "RAM",             20, 3200,  4800, "RAM-01", "CRS-VNG-D5-32","2x16GB, DDR5-5600, CL36"),
    ("G.Skill Trident Z5 DDR5 32GB 6000MHz",         "RAM",             15, 3800,  5700, "RAM-02", "GSK-TRZ5-32",  "2x16GB, DDR5-6000, CL36, RGB"),
    ("Kingston Fury Beast DDR4 32GB 3200MHz",        "RAM",             25, 2200,  3300, "RAM-03", "KNG-FBT-D4-32","2x16GB, DDR4-3200, CL16"),
    ("Corsair Vengeance DDR4 16GB 3600MHz",          "RAM",             30, 1450,  2175, "RAM-04", "CRS-VNG-D4-16","2x8GB, DDR4-3600, CL18"),
    ("G.Skill Ripjaws V DDR4 16GB 3200MHz",          "RAM",             30, 1250,  1875, "RAM-05", "GSK-RPW-D4-16","2x8GB, DDR4-3200, CL16"),
    ("Crucial DDR4 8GB 3200MHz SODIMM",              "RAM",             40,  680,  1020, "RAM-06", "CRC-D4-8-SO",  "Laptop, DDR4-3200, 1.2V"),
    ("Samsung DDR4 16GB 3200MHz ECC",                "RAM",             15, 2100,  3150, "RAM-07", "SAM-D4-16-ECC","Sunucu, ECC Unbuffered, 1Rx8"),

    # SSD / Depolama
    ("Samsung 980 PRO 2TB NVMe M.2 SSD",             "SSD - M.2",       20, 4200,  6300, "SSD-01", "SAM-980P-2TB", "PCIe 4.0, 7000/5100MB/s"),
    ("WD Black SN850X 2TB NVMe M.2 SSD",             "SSD - M.2",       15, 4500,  6750, "SSD-02", "WD-SN850X-2TB","PCIe 4.0, 7300/6600MB/s"),
    ("Seagate FireCuda 530 2TB NVMe SSD",             "SSD - M.2",       12, 4800,  7200, "SSD-03", "SGT-FC530-2TB","PCIe 4.0, 7300/6900MB/s, PS5"),
    ("Sabrent Rocket 4 Plus 1TB NVMe SSD",           "SSD - M.2",       18, 2200,  3300, "SSD-04", "SBR-RK4P-1TB", "PCIe 4.0, 7100/6600MB/s"),
    ("Kingston A2000 1TB NVMe M.2 SSD",              "SSD - M.2",       25, 1800,  2700, "SSD-05", "KNG-A2K-1TB",  "PCIe 3.0, 2200/2000MB/s"),
    ("Samsung 870 EVO 1TB SATA SSD",                 "SSD - SATA",      20, 1650,  2475, "SSD-06", "SAM-870E-1TB", "SATA 6Gb/s, 560/530MB/s"),
    ("Crucial MX500 2TB SATA SSD",                   "SSD - SATA",      15, 2800,  4200, "SSD-07", "CRC-MX5-2TB",  "SATA 6Gb/s, 560/510MB/s"),
    ("Seagate Barracuda 2TB 3.5\" HDD",              "HDD",             25,  950,  1425, "HDD-01", "SGT-BAR-2TB",  "7200RPM, 256MB, SATA 6Gb/s"),
    ("WD Blue 4TB 3.5\" HDD",                        "HDD",             20, 1800,  2700, "HDD-02", "WD-BLU-4TB",   "5400RPM, 256MB, SATA 6Gb/s"),

    # Ekran Kartları
    ("NVIDIA RTX 4070 Ti SUPER 16GB",                "Ekran Kartı",      5,24000, 36000, "GPU-01", "NVD-4070TIS",  "16GB GDDR6X, DLSS 3, ADA"),
    ("AMD RX 7900 GRE 16GB",                         "Ekran Kartı",      4,20000, 30000, "GPU-02", "AMD-7900GRE",  "16GB GDDR6, Ray Tracing, RDNA3"),
    ("NVIDIA RTX 4060 8GB GDDR6",                    "Ekran Kartı",      8,12000, 18000, "GPU-03", "NVD-4060",     "8GB GDDR6, 115W, DLSS 3"),
    ("AMD RX 7600 8GB GDDR6",                        "Ekran Kartı",      8,10500, 15750, "GPU-04", "AMD-7600",     "8GB GDDR6, RDNA3, AV1 enc/dec"),
    ("NVIDIA RTX 4090 24GB GDDR6X",                  "Ekran Kartı",      2,55000, 82500, "GPU-05", "NVD-4090",     "24GB GDDR6X, 450W, ADA Lovelace"),

    # İşlemci Soğutucu
    ("Noctua NH-D15 Çift Kulelı CPU Soğutucu",       "İşlemci Soğutucu",12, 2800,  4200, "CLR-01", "NCT-NH-D15",   "165mm, 2x NF-A15, AM5/LGA1700"),
    ("be quiet! Dark Rock Pro 4",                    "İşlemci Soğutucu",10, 2600,  3900, "CLR-02", "BEQ-DRP4",     "250W TDP, 135+120mm, LGA1700"),
    ("DeepCool AK620 Çift Kule",                     "İşlemci Soğutucu",15, 1800,  2700, "CLR-03", "DPC-AK620",    "260W TDP, 2x120mm, AM5/LGA1700"),
    ("ARCTIC Liquid Freezer III 360 AIO",            "İşlemci Soğutucu", 8, 4200,  6300, "CLR-04", "ARC-LF3-360",  "360mm, ARGB, MX-6, VRM fan"),
    ("Corsair iCUE H150i Elite Capellix 360 AIO",   "İşlemci Soğutucu", 6, 5500,  8250, "CLR-05", "CRS-H150I-ELC","360mm, XT Pump, iCUE uyumlu"),
    ("Cooler Master Hyper 212 Black Edition",        "İşlemci Soğutucu",20, 1100,  1650, "CLR-06", "CLM-H212-BLK", "150W TDP, 120mm, AM5/LGA1700"),

    # Güç Kaynakları
    ("Corsair RM1000x SHIFT 1000W 80+ Gold",         "Güç Kaynağı",      8, 4800,  7200, "PSU-01", "CRS-RM1000XS", "Modüler, ATX 3.0, PCIe 5.0"),
    ("be quiet! Straight Power 11 850W Platinum",   "Güç Kaynağı",      8, 4500,  6750, "PSU-02", "BEQ-SP11-850P","Modüler, 80+ Platinum, fanless"),
    ("Seasonic FOCUS GX-850 850W 80+ Gold",          "Güç Kaynağı",      8, 3800,  5700, "PSU-03", "SSN-FGX-850",  "Modüler, 10 yıl garanti"),
    ("MSI MAG A750GL PCIE5 750W",                    "Güç Kaynağı",     10, 3200,  4800, "PSU-04", "MSI-A750GL",   "Modüler, ATX 3.0, 80+ Gold"),
    ("Antec NeoECO Gold Modular 750W",               "Güç Kaynağı",     12, 2800,  4200, "PSU-05", "ATC-NEO750G",  "Modüler, 80+ Gold, 5 yıl garanti"),

    # Kasalar
    ("Fractal Design Define 7 ATX Kasa",             "Kasa",             6, 4200,  6300, "CSE-01", "FRC-DEF7",     "ATX, ses yalıtımı, 2x 3.5 HDD"),
    ("NZXT H7 Flow Mid-Tower ATX Kasa",              "Kasa",             8, 3800,  5700, "CSE-02", "NZX-H7-FLOW",  "ATX, mesh panel, 2x140mm fan"),
    ("Lian Li PC-O11 Dynamic EVO ATX Kasa",          "Kasa",             6, 4500,  6750, "CSE-03", "LLA-O11-EVO",  "ATX/mATX/ITX, dual-chamber"),
    ("Cooler Master MasterBox TD500 Mesh V2",        "Kasa",            10, 2800,  4200, "CSE-04", "CLM-TD500-MV2","ATX, ARGB, mesh ön panel"),
    ("Phanteks Eclipse P500A Mesh",                  "Kasa",             8, 3200,  4800, "CSE-05", "PHT-P500A",    "ATX, DRGB, D-RGB headers"),
]
# fmt: on

# ─── Yardımcı fonksiyonlar ────────────────────────────────────────────────────

def temizle_parca_verileri(cur, conn):
    """Mevcut test verilerini (tüm parts + hareketleri) temizler."""
    print("\n🗑️  Mevcut ürün/stok verileri temizleniyor...")
    cur.execute("DELETE FROM stock_movements")
    cur.execute("DELETE FROM parts")
    conn.commit()
    print("   ✓ parts ve stock_movements tabloları temizlendi.")


def parca_ekle(cur, conn, urunler, kategori_adi):
    """Ürün listesini veritabanına ekler ve stok hareketi oluşturur."""
    print(f"\n📦 {kategori_adi} ürünleri ekleniyor ({len(urunler)} adet)...")
    eklenen = 0
    for (isim, alt_kat, stok, alis, satis, raf, kod, aciklama) in urunler:
        try:
            cur.execute(
                """
                INSERT INTO parts
                    (name, category, stock, price, purchase_price, currency,
                     code, shelf_number, description, min_stock, created_at, is_deleted)
                VALUES (?, ?, ?, ?, ?, 'TRY', ?, ?, ?, 5, ?, 0)
                """,
                (isim, alt_kat, stok, satis, alis, kod, raf, aciklama, NOW),
            )
            part_id = cur.lastrowid

            # Stok hareketi
            try:
                cur.execute(
                    """
                    INSERT INTO stock_movements
                        (part_id, movement_type, amount, new_stock, description, created_at)
                    VALUES (?, 'Giriş', ?, ?, ?, ?)
                    """,
                    (part_id, stok, stok, f"Test verisi - Başlangıç stoku: {isim}", NOW),
                )
            except Exception:
                # Eski şema desteği
                try:
                    cur.execute(
                        """
                        INSERT INTO stock_movements
                            (part_id, type, amount, current_stock, description, date)
                        VALUES (?, 'Giriş', ?, ?, ?, ?)
                        """,
                        (part_id, stok, stok, f"Test verisi: {isim}", NOW),
                    )
                except Exception:
                    pass  # stok_movements kaydı kritik değil

            eklenen += 1
        except sqlite3.IntegrityError as e:
            print(f"   ⚠ Atlandı (unique/integrity): {isim[:40]} — {e}")
        except Exception as e:
            print(f"   ✗ HATA: {isim[:40]} — {e}")

    conn.commit()
    print(f"   ✓ {eklenen} / {len(urunler)} ürün eklendi.")
    return eklenen


# ─── Ana Akış ─────────────────────────────────────────────────────────────────

def main():
    print("=" * 65)
    print("  AYEC Pro — Kapsamlı Ürün Test Verisi Yükleme Aracı")
    print("=" * 65)
    print(f"  Veritabanı : {DB_PATH}")

    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    cur  = conn.cursor()

    # Şema uyumluluğunu kontrol et — movement_type / new_stock yoksa ekle
    cur.execute("PRAGMA table_info(stock_movements)")
    sm_cols = {r[1] for r in cur.fetchall()}
    if "movement_type" not in sm_cols and "type" in sm_cols:
        try:
            cur.execute("ALTER TABLE stock_movements RENAME COLUMN type TO movement_type")
            conn.commit()
            print("   ✓ stock_movements.type → movement_type yeniden adlandırıldı.")
        except Exception:
            pass
    if "new_stock" not in sm_cols:
        try:
            cur.execute("ALTER TABLE stock_movements ADD COLUMN new_stock REAL DEFAULT 0")
            conn.commit()
        except Exception:
            pass
    if "created_at" not in sm_cols and "date" in sm_cols:
        try:
            cur.execute("ALTER TABLE stock_movements RENAME COLUMN date TO created_at")
            conn.commit()
        except Exception:
            pass

    # Parts tablosuna currency kolonu yoksa ekle
    cur.execute("PRAGMA table_info(parts)")
    parts_cols = {r[1] for r in cur.fetchall()}
    for col, coltype in [("currency", "TEXT"), ("is_deleted", "INTEGER DEFAULT 0"),
                         ("photo_path", "TEXT"), ("part_name", "TEXT")]:
        if col not in parts_cols:
            try:
                cur.execute(f"ALTER TABLE parts ADD COLUMN {col} {coltype}")
                conn.commit()
            except Exception:
                pass

    # ── Temizle ──
    temizle_parca_verileri(cur, conn)

    # ── Ekle ──
    toplam = 0
    toplam += parca_ekle(cur, conn, GUVENLIK_SISTEMLERI,    "Bilgisayar Güvenlik Sistemleri")
    toplam += parca_ekle(cur, conn, AKILLI_EV,              "Akıllı Ev Sistemleri")
    toplam += parca_ekle(cur, conn, BILGISAYAR_BILESENLERI, "Bilgisayar Bileşenleri")

    # ── Özet ──
    cur.execute("SELECT category, COUNT(*) AS n, SUM(stock) AS toplam_stok FROM parts GROUP BY category ORDER BY category")
    rows = cur.fetchall()

    print("\n" + "=" * 65)
    print(f"  ✅ TAMAMLANDI — Toplam {toplam} ürün yüklendi")
    print("=" * 65)
    print(f"\n  {'Alt Kategori':<40} {'Ürün':>6} {'Toplam Stok':>12}")
    print("  " + "-" * 60)
    for r in rows:
        print(f"  {str(r['category']):<40} {r['n']:>6} {r['toplam_stok']:>12}")

    cur.execute("SELECT COUNT(*) FROM parts")
    print("\n  " + "-" * 60)
    print(f"  TOPLAM ÜRÜN (parts tablosu) : {cur.fetchone()[0]}")

    conn.close()
    print("\n  Uygulama yeniden başlatıldığında değişiklikler görünür olacaktır.\n")


if __name__ == "__main__":
    main()
