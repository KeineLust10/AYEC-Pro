# -*- coding: utf-8 -*-

import os
import sys
import shutil
import winreg
import subprocess
import time
import ctypes

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def kill_process(process_name):
    try:
        subprocess.run(f'taskkill /F /IM "{process_name}"', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        pass

def delete_key(hive, subkey):
    try:
        winreg.DeleteKey(hive, subkey)
        print(f"  [OK] Registry key deleted: {subkey}")
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"  [!] Failed to delete registry key {subkey}: {e}")

def delete_tree(hive, subkey):
    try:
        # Recursively delete a key
        try:
            with winreg.OpenKey(hive, subkey, 0, winreg.KEY_ALL_ACCESS) as key:
                while True:
                    try:
                        child_name = winreg.EnumKey(key, 0)
                        delete_tree(hive, f"{subkey}\\{child_name}")
                    except OSError:
                        break
        except FileNotFoundError:
            pass
            
        winreg.DeleteKey(hive, subkey)
        print(f"  [OK] Registry key deleted: {subkey}")
    except FileNotFoundError:
        pass
    except Exception as e:
        pass # Ignore permission errors or non-empty keys if recursive logic missed something

def get_install_path():
    path = None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\AYEC Pro Teknoloji\AYEC Pro") as key:
            path, _ = winreg.QueryValueEx(key, "InstallPath")
    except:
        pass
    
    if not path:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\AYEC Pro Teknoloji\AYEC Pro Server") as key:
                path, _ = winreg.QueryValueEx(key, "InstallPath")
        except:
            pass
            
    return path

def main():
    os.system("title AYEC Pro - Tam Temizlik Aracı")
    os.system("color 0C") # Red text
    
    print("\n  #######################################################")
    print("  #                                                     #")
    print("  #       PREMIUM BULUT - TAM KALDIRMA ARACI            #")
    print("  #                                                     #")
    print("  #  UYARI: Bu islem tum verileri, veritabanini ve      #")
    print("  #   ayarlari KALICI OLARAK SILECEKTIR!                 #")
    print("  #                                                     #")
    print("  #######################################################\n")

    if not is_admin():
        # Re-run the program with admin rights
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()

    time.sleep(1)
    
    print("  [1/5] Calisan uygulamalar kapatiliyor...")
    kill_process("AYECPro_App.exe")
    kill_process("AYECPro_Server.exe")
    kill_process("StartServer.cmd") # Usually runs in cmd.exe, might need to kill by window title but generic kill is safer
    print("  [OK] Uygulamalar sonlandirildi.\n")

    print("  [2/5] Kurulum konumu tespit ediliyor...")
    install_path = get_install_path()
    
    paths_to_check = [
        install_path,
        r"C:\Program Files (x86)\AYEC Pro",
        r"C:\Program Files\AYEC Pro"
    ]

    found = False
    print("  [3/5] Dosyalar siliniyor...")
    for path in paths_to_check:
        if path and os.path.exists(path):
            try:
                shutil.rmtree(path)
                print(f"  [OK] Klasor silindi: {path}")
                found = True
            except Exception as e:
                print(f"  [!] Klasor silinemedi {path}: {e}")
    
    if not found:
        print("  [i] Silinecek klasor bulunamadi.")
    print()

    print("  [4/5] Kayit Defteri (Registry) temizleniyor...")
    delete_tree(winreg.HKEY_CURRENT_USER, r"Software\AYEC Pro Teknoloji")
    delete_tree(winreg.HKEY_LOCAL_MACHINE, r"Software\AYEC Pro Teknoloji")
    delete_key(winreg.HKEY_CLASSES_ROOT, r".pbbackup")
    delete_tree(winreg.HKEY_CLASSES_ROOT, r"AYECProBackup")
    print("  [OK] Temizlendi.\n")

    print("  [5/5] Kisayollar temizleniyor...")
    shortcuts = [
        os.path.join(os.environ["PUBLIC"], "Desktop", "AYEC Pro.lnk"),
        os.path.join(os.environ["USERPROFILE"], "Desktop", "AYEC Pro.lnk"),
        os.path.join(os.environ["PUBLIC"], "Desktop", "AYEC Pro Sunucu.lnk"),
        os.path.join(os.environ["USERPROFILE"], "Desktop", "AYEC Pro Sunucu.lnk"),
    ]
    
    for sc in shortcuts:
        if os.path.exists(sc):
            try:
                os.remove(sc)
                print(f"  [OK] Kisayol silindi: {sc}")
            except:
                pass

    # Start Menu
    start_menus = [
        os.path.join(os.environ["ProgramData"], "Microsoft", "Windows", "Start Menu", "Programs", "AYEC Pro"),
        os.path.join(os.environ["AppData"], "Microsoft", "Windows", "Start Menu", "Programs", "AYEC Pro")
    ]
    
    for sm in start_menus:
        if os.path.exists(sm):
            try:
                shutil.rmtree(sm)
                print(f"  [OK] Baslat menusu klasoru silindi: {sm}")
            except:
                pass

    print("\n  =======================================================")
    print("   ISLEM TAMAMLANDI!")
    print("   AYEC Pro sistemden tamamen kaldirildi.")
    print("  =======================================================\n")
    input("  Cikmak icin bir tusa basin...")

if __name__ == "__main__":
    main()
