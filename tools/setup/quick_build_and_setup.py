#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AYEC Pro - Hizli Setup ve Derleme v69.0.3
"""

import os
import sys
import shutil
import subprocess
import time

class Colors:
    CYAN = ''
    GREEN = ''
    YELLOW = ''
    RED = ''
    BOLD = ''
    END = ''

def print_header():
    print("\n" + "="*70)
    print("  AYEC Pro v69.0.3 - Hizli Kurulum ve Derleme")
    print("="*70 + "\n")

def run_command(cmd, description):
    """Komutu calistir ve sonuclari goster"""
    print(f"[STATUS] {description}...")
    try:
        # Use active virtual environment for execution if possible
        result = subprocess.run(cmd, shell=True, capture_output=False, text=True)
        if result.returncode == 0:
            print(f"[OK] {description} tamamlandi\n")
            return True
        else:
            print(f"[ERROR] Hata (Kod: {result.returncode})\n")
            return False
    except Exception as e:
        print(f"[ERROR] Hata: {e}\n")
        return False

def main():
    print_header()
    
    base_dir = os.getcwd()
    
    # Sanal ortam python yolunu tespit et
    python_path = os.path.join(base_dir, ".venv_active", "Scripts", "python.exe")
    if not os.path.exists(python_path):
        python_path = "python"
    
    # 1. Bagimliliklari yukle
    print("[1/4] Python Bagimliliklari Yukleniyor")
    if not run_command(
        f'"{python_path}" -m pip install -r requirements.txt --upgrade -q',
        "Bagimliliklar yukleniyor"
    ):
        print("[ERROR] Bagimliliklar yuklenemedi. Kurulum durduruldu.")
        return False

    # Fail before packaging if the security dependency is not available.
    if not run_command(
        f'"{python_path}" -c "import bcrypt; print(bcrypt.__version__)"',
        "bcrypt dogrulamasi"
    ):
        print("[ERROR] bcrypt yuklenemedi. Kurulum durduruldu.")
        return False
    
    # 2. EXE Olustur
    print("[2/4] Desktop Uygulamasi Derleniyor")
    if os.path.exists("AYECPro_App.spec"):
        print("PyInstaller calistiriliyor (bu 1-2 dakika surebilir)...")
        run_command(
            f'"{python_path}" -m PyInstaller --clean --noconfirm AYECPro_App.spec',
            "EXE Olusturma"
        )
        built_exe = os.path.join(base_dir, "dist", "AYECPro_App", "AYECPro_App.exe")
        installer_exe = os.path.join(base_dir, "dist", "AYECPro_App", "AYECPro.exe")
        if os.path.isfile(built_exe):
            shutil.copy2(built_exe, installer_exe)
            print("[OK] Installer giris adi AYECPro.exe olarak hazirlandi")
    else:
        print("[ERROR] AYECPro_App.spec bulunamadi\n")
        return False
    
    # 3. Setup Calistir
    print("[3/4] Setup Yapilandirmasi Uygulaniyor")
    run_command(
        f'"{python_path}" tools/setup/setup_ayecpro.py --console',
        "Setup"
    )

    # 4. Inno Setup (Installer Olustur)
    print("[4/4] Kurulum Dosyasi (Installer) Olusturuluyor")
    inno_path = r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    
    if os.path.exists(inno_path):
        if os.path.exists("AYECPro_Modern_Setup.iss"):
            run_command(f'"{inno_path}" AYECPro_Modern_Setup.iss', "Inno Setup Derlemesi")
        else:
            print("[ERROR] AYECPro_Modern_Setup.iss dosyasi bulunamadi. Lutfen olusturun.\n")
    else:
        print("[WARNING] Inno Setup yukli degil veya yolu farkli. Installer olusturulamadi.")
        print("   Indirme Linki: https://jrsoftware.org/isdl.php\n")
    
    # Son kontrol
    print("="*70)
    print("KURULUM TAMAMLANDI!")
    print("="*70 + "\n")
    
    # Ozet
    install_dir = r"C:\Program Files (x86)\AYEC Pro"
    
    print("Kurulum Ozeti:")
    print(f"  Kurulum Dizini: {install_dir} (Varsayilan)")
    print("  Veritabani: ayecpro.db")
    print("  Giris: admin / admin123\n")
    
    print("Baslamak Icin:")
    if os.path.exists("Setup_Output"):
        setup_files = [f for f in os.listdir("Setup_Output") if f.endswith(".exe")]
        if setup_files:
            print(f"  Kurulum Dosyasi: Setup_Output\\{setup_files[0]}")
    print("  1. Masaustundeki 'AYEC Pro' kisayoluna cift tiklayin")
    print(f"  2. Veya: {install_dir}\\AYECPro.exe\n")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
