# -*- coding: utf-8 -*-

# AYEC Pro Özel Mail Şablonlar

AYEC_LISANS_SABLONU = """
<html>
    <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: black; background-color: whitesmoke; padding: 20px;">
        <div style="max-width: 600px; margin: auto; background-color: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border: 1px solid lightgray;">
            
            <div style="background: linear-gradient(135deg, black 0%, dimgray 100%); padding: 30px; text-align: center;">
                <h1 style="color: white; margin: 0; font-size: 24px; letter-spacing: 1px;">AYEC Pro</h1>
                <p style="color: slategray; margin: 5px 0 0 0; font-size: 14px;">Bilişim ve Güvenlik Sistemleri</p>
            </div>

            <div style="padding: 30px;">
                <h2 style="color: dimgray; font-size: 20px;">Sayın {user_name},</h2>
                <p style="color: slategray; line-height: 1.6;">
                    AYEC Pro Teknik Servis yazılımımızı tercih ettiğiniz için teşekkür ederiz. 
                    Üyeliğiniz onaylanmış olup, yazılımınızı tam sürüm olarak kullanabilmeniz için gereken lisans anahtarınız aşağıda sunulmuştur.
                </p>

                <div style="background-color: aliceblue; border: 2px dashed dodgerblue; border-radius: 8px; padding: 20px; text-align: center; margin: 30px 0;">
                    <span style="display: block; color: royalblue; font-size: 12px; font-weight: bold; margin-bottom: 8px; text-transform: uppercase;">LİSANS ANAHTARINIZ</span>
                    <code style="font-size: 22px; color: dodgerblue; font-family: monospace; font-weight: bold;">{license_key}</code>
                </div>

                <p style="color: slategray; font-size: 15px;">
                    <strong>Nasıl Aktive Edilir?</strong><br>
                    1. Programı çalıştırın ve giriş yapın.<br>
                    2. Ayarlar > Güvenlik ve Lisans sekmesine gidin.<br>
                    3. Yukarıdaki anahtarı kutucuğa yapıştırıp "Onayla" butonuna basın.
                </p>
            </div>

            <div style="background-color: whitesmoke; padding: 20px; text-align: center;">
                <p style="margin: 0; color: gray; font-size: 12px;">
                    © 2026 AYEC Pro<br>
                    Balıkesir, Türkiye | Destek: destek@ayecpro.com
                </p>
            </div>
        </div>
    </body>
</html>
"""

BULUT_LISANS_SABLONU = AYEC_LISANS_SABLONU

