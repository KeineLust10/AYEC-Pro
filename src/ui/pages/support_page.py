# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, QFrame, 
                             QHBoxLayout, QGridLayout, QTabWidget, QTextBrowser, QGraphicsDropShadowEffect)
from src.utils.toast_notification import show_success, show_error, show_warning, show_info
from src.utils.theme_colors import theme_qss
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QFont, QIcon, QColor, QAction

class SupportPage(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.init_ui()

    def init_ui(self):
        # Main Layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Create Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #e0e0e0; border-radius: 8px; background: white; }
            QTabBar::tab {
                background: #f1f5f9;
                color: #64748b;
                padding: 10px 20px;
                border: 1px solid #e2e8f0;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                min-width: 120px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: white;
                color: #2563eb;
                border-bottom: 2px solid #2563eb;
            }
        """)

        # Tab 1: Contact & Support (Existing Content)
        self.tabs.addTab(self.create_contact_tab(), "📞 İletişim ve Destek")

        # Tab 2: User Manual (New Content)
        self.tabs.addTab(self.create_manual_tab(), "📚 Kullanım Kılavuzu")

        main_layout.addWidget(self.tabs)

    def create_contact_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(25)
        layout.setContentsMargins(30, 30, 30, 30)

        # 1. Hero Content
        hero = QFrame()
        hero.setObjectName("HeroCard")
        hero.setStyleSheet(theme_qss("""
            QFrame#HeroCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 @surface, stop:1 @surface_alt);
                border: 1px solid @border;
                border-radius: 16px;
            }
        """))
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0,0,0,50))
        shadow.setOffset(0,10)
        hero.setGraphicsEffect(shadow)

        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(40, 40, 40, 40)
        
        info_layout = QVBoxLayout()
        title = QLabel("Teknik Destek Merkezi")
        title.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        title.setStyleSheet(theme_qss("border: none; color: @text; background: transparent;"))
        
        desc = QLabel("Cozum ortaginiz olarak her zaman yaninizdayiz.\\nAsagidaki kanallardan bize 7/24 ulasabilirsiniz.")
        desc.setFont(QFont("Segoe UI", 13, QFont.Weight.Medium))
        desc.setStyleSheet(theme_qss("color: @text_muted; border: none; background: transparent;"))
        
        info_layout.addWidget(title)
        info_layout.addWidget(desc)
        
        # Support Number (Big)
        number_lbl = QLabel("Telefon: 0534 878 10 47")
        number_lbl.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        number_lbl.setStyleSheet(theme_qss("color: @success; border: none; background: transparent;"))
        number_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        hero_layout.addLayout(info_layout)
        hero_layout.addStretch()
        hero_layout.addWidget(number_lbl)
        
        layout.addWidget(hero)

        # 2. Action Grid
        grid_layout = QGridLayout()
        grid_layout.setSpacing(20)

        # Helper to create action card
        def create_action_card(title, desc, color, icon_text, func):
            # Revert to QFrame approach for card
            f = QFrame()
            f.setObjectName("ActionCard")
            f.setCursor(Qt.CursorShape.PointingHandCursor)
            def click_handler(event):
                func()
            f.mousePressEvent = click_handler
            f.setStyleSheet(theme_qss(f"""
                QFrame#ActionCard {{
                    background-color: @surface;
                    border: 1px solid @border;
                    border-radius: 12px;
                }}
                QFrame#ActionCard:hover {{
                    border: 2px solid {color};
                    background-color: @surface_alt;
                }}
            """))
            sh = QGraphicsDropShadowEffect()
            sh.setBlurRadius(15)
            sh.setColor(QColor(0,0,0,10))
            sh.setOffset(0,4)
            f.setGraphicsEffect(sh)
            
            l = QVBoxLayout(f)
            l.setContentsMargins(22, 20, 22, 20)
            l.setSpacing(8)
            
            icon_lbl = QLabel(icon_text)
            icon_lbl.setStyleSheet(theme_qss(f"font-size: 24px; color: {color}; background: transparent; border: none;"))
            
            t_lbl = QLabel(title)
            t_lbl.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
            t_lbl.setStyleSheet(theme_qss("color: @text; background: transparent; border: none;"))
            
            d_lbl = QLabel(desc)
            d_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Medium))
            d_lbl.setStyleSheet(theme_qss("color: @text_muted; background: transparent; border: none;"))
            
            l.addWidget(icon_lbl)
            l.addWidget(t_lbl)
            l.addWidget(d_lbl)
            
            return f

        # WhatsApp Card
        grid_layout.addWidget(create_action_card(
            "WhatsApp Destek", 
            "Canlı sohbete bağlanın ve\\nhızlı yanıt alın.",
            "#25D366", "💬",
            lambda: QDesktopServices.openUrl(QUrl("https://wa.me/905348781047"))
        ), 0, 0)

        # Email Card
        grid_layout.addWidget(create_action_card(
            "Resmi Web Sitesi",
            "www.ayecpro.com",
            "#3b82f6", "WEB",
            lambda: QDesktopServices.openUrl(QUrl("https://www.ayecpro.com"))
        ), 2, 0)

        grid_layout.addWidget(create_action_card(
            "E-Posta Gönder",
            "Detaylı sorun bildirimleri\\niçin mail atın.",
            "#3b82f6", "📧",
            lambda: QDesktopServices.openUrl(QUrl("mailto:destek@ayecpro.com"))
        ), 0, 1)

        # AnyDesk Card
        grid_layout.addWidget(create_action_card(
            "AnyDesk İndir",
            "Uzaktan bağlantı için\\ngereklidir.",
            "#ef4444", "🔴",
            lambda: QDesktopServices.openUrl(QUrl("https://anydesk.com"))
        ), 1, 0)
        
        # TeamViewer Card
        grid_layout.addWidget(create_action_card(
            "TeamViewer İndir",
            "Alternatif uzaktan\\nbağlantı aracı.",
            "#0284c7", "🔵",
            lambda: QDesktopServices.openUrl(QUrl("https://www.teamviewer.com"))
        ), 1, 1)

        layout.addLayout(grid_layout)
        layout.addStretch()
        
        return widget

    def create_manual_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setStyleSheet("""
            QTextBrowser {
                background-color: white;
                border: none;
                padding: 20px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
                color: #2c3e50;
            }
        """)
        
        html_content = """
        <h1 style="color: #2563eb;">🤖 JARVIS NEURAL CORE - KULLANIM KILAVUZU</h1>
        <p>Bu kılavuz, AYEC Pro tarafından geliştirilen yapay zeka destekli otonom yönetim sisteminin özelliklerini ve sorun giderme adımlarını içerir.</p>
 
        <hr>
 
        <h2 style="color: #334155;">1. 🚀 Başlangıç ve Bağlantı Ayarları</h2>
        <p>Sistemin zekasını (Jarvis) aktif etmek için ilk durak <b>Ayarlar > Jarvis</b> menüsüdür.</p>
        <ul>
            <li><b>API Anahtarı Havuzu:</b> Jarvis'in kesintisiz çalışması için buraya birden fazla API anahtarı girebilirsiniz. Her anahtarı yeni bir satıra yazın.</li>
            <li><b>Bağlantı Testi:</b> "API Havuzunu Test Et" butonuna bastığınızda sistem anahtarları kontrol eder. Buton Yeşil (SİSTEM ÇEVRİMİÇİ) yanıyorsa Jarvis emirlerinize hazırdır.</li>
            <li><b>Zeka Modeli Seçimi:</b> ComboBox (Açılır Menü) yanındaki "GÜNCELLE" butonuna basarak Google sunucularındaki en güncel modelleri (Gemini 2.0 Flash vb.) otomatik olarak listeleyebilirsiniz.</li>
        </ul>
 
        <h2 style="color: #334155;">2. 🧠 Jarvis ile Etkileşim</h2>
        <p>Jarvis, asenkron (arka plan) çalışma yapısı sayesinde sistemi yormadan yanıt verir.</p>
        <ul>
            <li><b>Metin Tabanlı Sorgu:</b> Dashboard üzerindeki giriş alanına komutlarınızı yazın. Jarvis düşünürken sistem donmaz, diğer sekmelerde çalışmaya devam edebilirsiniz.</li>
            <li><b>Sesli Geri Bildirim:</b> Ayarlardan bu özelliği aktif ederseniz, Jarvis yanıtlarını size sesli olarak okur. Bu özellik özellikle analiz raporlarını dinlerken kolaylık sağlar.</li>
            <li><b>Akıllı Yanıtlar:</b> Jarvis sadece sohbet etmez; sistem hatalarını analiz eder ve çözüm önerileri sunar.</li>
        </ul>
 
        <h2 style="color: #334155;">3. 🛠️ Otonom Yetenekler ve Bakım</h2>
        <p>Sistem, kendi kendini denetleyen modüllerle donatılmıştır.</p>
        <ul>
            <li><b>Otomatik Yedekleme:</b> Her gün saat 02:00'de veritabanınız otomatik olarak yedeklenir. Yedekleme durumu günlük dosyasında (log) "[OK]" ibaresiyle raporlanır.</li>
            <li><b>Kota Yönetimi (Smart Rotate):</b> Eğer bir API anahtarının kotası dolarsa (429 Hatası), Jarvis kullanıcıya hissettirmeden havuzdaki bir sonraki anahtara geçiş yapar.</li>
            <li><b>Hata İzleyici:</b> Sistem kritik bir hata aldığında, teknik detaylar yerine size "İnternet bağlantınızı kontrol edin" veya "Model güncellemesi yapın" gibi kullanıcı dostu uyarılar verir.</li>
        </ul>
 
        <h2 style="color: #334155;">4. ❓ Sıkça Sorulan Sorular (S.S.S)</h2>
        <table border="1" style="border-collapse: collapse; width: 100%; border-color: #e2e8f0;">
            <tr style="background-color: #f1f5f9; text-align: left;">
                <th style="padding: 10px;">Sorun</th>
                <th style="padding: 10px;">Çözüm</th>
            </tr>
            <tr>
                <td style="padding: 10px; color: #e74c3c; font-weight: bold;">Bağlantı Hatası (Kırmızı/Turuncu)</td>
                <td style="padding: 10px;">API anahtarlarınızı kontrol edin veya "GÜNCELLE" butonuna basarak yeni bir model seçin.</td>
            </tr>
            <tr>
                <td style="padding: 10px; color: #e67e22; font-weight: bold;">Jarvis Çok Yavaş Cevap Veriyor</td>
                <td style="padding: 10px;">\u00dccretsiz kota limitlerinde gecikme ya\u015f\u0131yorsan\u0131z gemini-3.5-flash-lite modelini deneyin.</td>
            </tr>
             <tr>
                <td style="padding: 10px; color: #34495e; font-weight: bold;">Ses Gelmiyor</td>
                <td style="padding: 10px;">Ayarlar menüsünden "Sesli Geri Bildirim" anahtarının açık olduğundan ve bilgisayar sesinin açık olduğundan emin olun.</td>
            </tr>
        </table>
 
        <h2 style="color: #334155;">5. ⚠️ Teknik Notlar</h2>
        <ul>
            <li><b>Karakter Desteği:</b> Sistem UTF-8 standartlarında çalışır. Log dosyalarında veya terminalde özel semboller yerine standart metinler kullanılır.</li>
            <li><b>Performans:</b> AI sorguları arka planda (QThread) işlenir, bu sayede ana arayüzün akıcılığı korunur.</li>
        </ul>
 
        <h2 style="color: #334155;">6. 🛠️ TEKNİK HATA VE MÜDAHALE REHBERİ (KRİTİK NOTLAR)</h2>
        <p>Aşağıdaki notlar, sistemin kararlılığını korumak ve karşılaşılan hataları anında gidermek için hazırlanmıştır.</p>
 
        <h3 style="color: #e67e22;">6.1. API ve Kota Hataları (429 & 404)</h3>
        <ul>
            <li><b>429 RESOURCE_EXHAUSTED:</b> Bu hata sistemin çok ağır çalıştığı veya donduğu anlamına gelmez; sadece Google'ın ücretsiz kullanım sınırına ulaştığınızı belirtir.<br>
            <i>Müdahale:</i> Sistem otomatik olarak havuzdaki diğer anahtara geçer. Eğer tüm anahtarlar doluysa, 60 saniye beklemek sorunu %100 çözecektir.</li>
            <li><b>404 MODEL_NOT_FOUND:</b> Seçili AI motorunun artık desteklenmediğini veya bölgenizde kapandığını gösterir.<br>
            <i>M\u00fcdahale:</i> Ayarlar men\u00fcs\u00fcndeki "Modelleri G\u00fcncelle" butonuna bas\u0131n ve listeden g\u00fcncel bir model (\u00d6rn: gemini-3.6-flash) se\u00e7in.</li>
        </ul>
 
        <h3 style="color: #e67e22;">6.2. Karakter ve Arayüz Çökmeleri (Unicode)</h3>
        <ul>
            <li><b>Log ve Terminal Hataları:</b> Terminalde "UnicodeEncodeError" veya "charmap" hatası alırsanız, bu sistemin özel bir sembolü (✓, ❌ gibi) görüntüleyemediğini gösterir.<br>
            <i>Not:</i> Geliştirme sürecimizde bu sembolleri [OK] ve [HATA] metinleriyle değiştirdik. Yeni bir log mesajı eklerken sadece standart İngilizce/Türkçe karakterler kullanmaya özen gösterin.</li>
        </ul>
 
        <h3 style="color: #e67e22;">6.3. Performans ve "Ağır Çalışma" Algısı</h3>
        <ul>
            <li><b>Donma Önleyici (Async):</b> Jarvis bir soruya yanıt verirken uygulama ekranı donuyorsa, asenkron (arka plan) işleyicisi devre dışı kalmış olabilir.<br>
            <i>Müdahale:</i> JarvisWorker sınıfının aktif olduğundan ve AI sorgusunun ana thread (ana kanal) dışında yapıldığından emin olun.</li>
            <li><b>H\u0131zland\u0131rma \u0130pucu:</b> Genel kullan\u0131m i\u00e7in gemini-3.6-flash, d\u00fc\u015f\u00fck gecikme ve maliyet i\u00e7in gemini-3.5-flash-lite modelini tercih edin.</li>
        </ul>
 
        <h3 style="color: #e67e22;">6.4. Veritabanı ve Yedekleme Notları</h3>
        <ul>
            <li><b>Yedekleme Çakışması:</b> Gece 02:00'deki otomatik yedekleme sırasında uygulama açıksa, veritabanı "Locked" (Kilitli) hatası verebilir.<br>
            <i>Çözüm:</i> Sistem bu durumu otomatik algılar ve 5 dakika sonra tekrar dener. Manuel müdahaleye gerek yoktur.</li>
        </ul>
        <br><br>
        <div style="text-align: center; color: #94a3b8; font-size: 12px;">AYEC Pro © 2026 - Tum Haklari Saklidir.</div>
        """
        
        browser.setHtml(html_content)
        layout.addWidget(browser)
        return widget
