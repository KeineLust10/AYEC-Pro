"""Add startup/shortcut functions to ModernDesktopApp.py before is_setup_completed."""

path = r"C:\Users\Admin\Desktop\AYEC Pro\ModernDesktopApp.py"
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

startup_shortcut_code = '''
    # =====================================================================
    # === BAŞLANGIÇ / KISAYOL YÖNETİMİ ===
    # =====================================================================

    def add_to_windows_startup(self):
        """Programı Windows başlangıcına ekler (Registry)."""
        try:
            import winreg
            exe_path = os.path.abspath(sys.executable)
            # If frozen (PyInstaller), use the actual .exe
            if getattr(sys, 'frozen', False):
                exe_path = os.path.abspath(sys.executable)
            else:
                # In dev mode, use ModernDesktopApp.py with python
                script = os.path.abspath(__file__)
                exe_path = f'"{sys.executable}" "{script}"'

            key_path = r"Software\\Microsoft\\Windows\\CurrentVersion\\Run"
            reg_key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, key_path,
                0, winreg.KEY_SET_VALUE
            )
            winreg.SetValueEx(reg_key, "AYECPro", 0, winreg.REG_SZ, exe_path)
            winreg.CloseKey(reg_key)
            self.db.set_setting("startup_enabled", "1")
            logger.info("AYEC Pro başlangıca eklendi.")
            return True
        except Exception as e:
            logger.error(f"Başlangıca eklenemedi: {e}")
            return False

    def remove_from_windows_startup(self):
        """Programı Windows başlangıcından çıkarır."""
        try:
            import winreg
            key_path = r"Software\\Microsoft\\Windows\\CurrentVersion\\Run"
            reg_key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, key_path,
                0, winreg.KEY_SET_VALUE
            )
            try:
                winreg.DeleteValue(reg_key, "AYECPro")
            except FileNotFoundError:
                pass  # Zaten yoksa sorun değil
            winreg.CloseKey(reg_key)
            self.db.set_setting("startup_enabled", "0")
            logger.info("AYEC Pro başlangıçtan çıkarıldı.")
            return True
        except Exception as e:
            logger.error(f"Başlangıçtan çıkarılamadı: {e}")
            return False

    def is_in_windows_startup(self):
        """Programın başlangıçta çalışıp çalışmadığını kontrol eder."""
        try:
            import winreg
            key_path = r"Software\\Microsoft\\Windows\\CurrentVersion\\Run"
            reg_key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, key_path,
                0, winreg.KEY_READ
            )
            try:
                winreg.QueryValueEx(reg_key, "AYECPro")
                winreg.CloseKey(reg_key)
                return True
            except FileNotFoundError:
                winreg.CloseKey(reg_key)
                return False
        except Exception:
            return False

    def create_desktop_shortcut(self):
        """Masaüstünde AYEC Pro kısayolu oluşturur."""
        try:
            import winreg
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
            # Try shell folder registry for localized Desktop path
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Shell Folders"
                )
                desktop_path = winreg.QueryValueEx(key, "Desktop")[0]
                winreg.CloseKey(key)
            except Exception:
                pass

            shortcut_path = os.path.join(desktop_path, "AYEC Pro.lnk")
            target = os.path.abspath(sys.executable)
            icon_path = resource_path(os.path.join("assets", "app_icon.ico"))
            if not os.path.exists(icon_path):
                icon_path = resource_path(os.path.join("assets", "app_icon.png"))

            try:
                import win32com.client
                shell = win32com.client.Dispatch("WScript.Shell")
                shortcut = shell.CreateShortCut(shortcut_path)
                shortcut.Targetpath = target
                if not getattr(sys, 'frozen', False):
                    shortcut.Arguments = f'"{os.path.abspath(__file__)}"'
                shortcut.WorkingDirectory = os.path.dirname(target)
                if os.path.exists(icon_path):
                    shortcut.IconLocation = icon_path
                shortcut.Description = "AYEC Pro Servis Yönetimi"
                shortcut.save()
                logger.info(f"Masaüstü kısayolu oluşturuldu: {shortcut_path}")
                return True
            except ImportError:
                # win32com yoksa .bat ile kısayol metni yaz
                bat_path = os.path.join(desktop_path, "AYEC Pro.bat")
                with open(bat_path, 'w', encoding='utf-8') as f:
                    if getattr(sys, 'frozen', False):
                        f.write(f'@echo off\\nstart "" "{target}"\\n')
                    else:
                        script = os.path.abspath(__file__)
                        f.write(f'@echo off\\nstart "" "{target}" "{script}"\\n')
                logger.info(f"Masaüstü başlatıcı oluşturuldu: {bat_path}")
                return True
        except Exception as e:
            logger.error(f"Masaüstü kısayolu oluşturulamadı: {e}")
            return False

    def create_start_menu_shortcut(self):
        """Başlangıç Menüsü'ne AYEC Pro kısayolu ekler."""
        try:
            import winreg
            programs_path = os.path.join(
                os.environ.get("APPDATA", ""),
                "Microsoft", "Windows", "Start Menu", "Programs"
            )
            # Try registry for localized path
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Shell Folders"
                )
                programs_path = winreg.QueryValueEx(key, "Programs")[0]
                winreg.CloseKey(key)
            except Exception:
                pass

            ayec_folder = os.path.join(programs_path, "AYEC Pro")
            os.makedirs(ayec_folder, exist_ok=True)
            shortcut_path = os.path.join(ayec_folder, "AYEC Pro.lnk")
            target = os.path.abspath(sys.executable)
            icon_path = resource_path(os.path.join("assets", "app_icon.ico"))
            if not os.path.exists(icon_path):
                icon_path = resource_path(os.path.join("assets", "app_icon.png"))

            try:
                import win32com.client
                shell = win32com.client.Dispatch("WScript.Shell")
                shortcut = shell.CreateShortCut(shortcut_path)
                shortcut.Targetpath = target
                if not getattr(sys, 'frozen', False):
                    shortcut.Arguments = f'"{os.path.abspath(__file__)}"'
                shortcut.WorkingDirectory = os.path.dirname(target)
                if os.path.exists(icon_path):
                    shortcut.IconLocation = icon_path
                shortcut.Description = "AYEC Pro Servis Yönetimi"
                shortcut.save()
                logger.info(f"Başlangıç Menüsü kısayolu: {shortcut_path}")
                return True
            except ImportError:
                bat_path = os.path.join(ayec_folder, "AYEC Pro.bat")
                with open(bat_path, 'w', encoding='utf-8') as f:
                    if getattr(sys, 'frozen', False):
                        f.write(f'@echo off\\nstart "" "{target}"\\n')
                    else:
                        script = os.path.abspath(__file__)
                        f.write(f'@echo off\\nstart "" "{target}" "{script}"\\n')
                logger.info(f"Başlangıç Menüsü başlatıcı: {bat_path}")
                return True
        except Exception as e:
            logger.error(f"Başlangıç Menüsü kısayolu oluşturulamadı: {e}")
            return False

    def toggle_windows_startup(self, enabled: bool):
        """Başlangıç kaydını aç/kapat ve sonucu bildir."""
        if enabled:
            ok = self.add_to_windows_startup()
            if ok:
                self.show_notification("Program Windows başlangıcına eklendi.", "success")
            else:
                self.show_notification("Başlangıca eklenemedi. Yönetici yetkisi gerekebilir.", "error")
        else:
            ok = self.remove_from_windows_startup()
            if ok:
                self.show_notification("Program Windows başlangıcından çıkarıldı.", "info")
            else:
                self.show_notification("Başlangıçtan çıkarılamadı.", "error")
        return ok

'''

target = '''    def is_setup_completed(self):
        """Setup tamamlanmış mı kontrol et\""""

if target in content:
    content = content.replace(target, startup_shortcut_code + target, 1)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: Startup/shortcut functions added")
else:
    print("FAILED: target not found")
    # Try a simpler approach - find by line
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if 'def is_setup_completed' in line:
            print(f"Found at line {i+1}: {line}")
            break
