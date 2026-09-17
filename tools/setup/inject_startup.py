"""Inject startup/shortcut functions into ModernDesktopApp.py"""

STARTUP_CODE = r"""
    # =====================================================================
    # === BASLANGIC / KISAYOL YONETIMI ===
    # =====================================================================

    def add_to_windows_startup(self):
        """Pc acildiginda programi otomatik baslatir (Registry)."""
        try:
            import winreg
            if getattr(sys, 'frozen', False):
                exe_path = os.path.abspath(sys.executable)
            else:
                script = os.path.abspath(__file__)
                exe_path = '"{}" "{}"'.format(sys.executable, script)
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            reg_key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(reg_key, "AYECPro", 0, winreg.REG_SZ, exe_path)
            winreg.CloseKey(reg_key)
            try:
                self.db.set_setting("startup_enabled", "1")
            except Exception:
                pass
            logger.info("AYEC Pro baslatma listesine eklendi.")
            return True
        except Exception as e:
            logger.error("Baslangica eklenemedi: %s", e)
            return False

    def remove_from_windows_startup(self):
        """Programi Windows baslangicindan kaldirir."""
        try:
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            reg_key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            try:
                winreg.DeleteValue(reg_key, "AYECPro")
            except FileNotFoundError:
                pass
            winreg.CloseKey(reg_key)
            try:
                self.db.set_setting("startup_enabled", "0")
            except Exception:
                pass
            logger.info("AYEC Pro baslangicindan kaldirildi.")
            return True
        except Exception as e:
            logger.error("Baslangictan cikarilamadi: %s", e)
            return False

    def is_in_windows_startup(self):
        """Programin Windows baslatma listesinde olup olmadigini kontrol eder."""
        try:
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            reg_key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
            try:
                winreg.QueryValueEx(reg_key, "AYECPro")
                winreg.CloseKey(reg_key)
                return True
            except FileNotFoundError:
                winreg.CloseKey(reg_key)
                return False
        except Exception:
            return False

    def _create_shortcut_win32(self, shortcut_path, target, arguments="", icon_path="", description=""):
        """Creates a .lnk shortcut using win32com if available, else creates a .bat launcher."""
        try:
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
            sc = shell.CreateShortCut(shortcut_path)
            sc.Targetpath = target
            if arguments:
                sc.Arguments = arguments
            sc.WorkingDirectory = os.path.dirname(target)
            if icon_path and os.path.exists(icon_path):
                sc.IconLocation = icon_path
            if description:
                sc.Description = description
            sc.save()
            return True
        except ImportError:
            bat_path = os.path.splitext(shortcut_path)[0] + ".bat"
            with open(bat_path, 'w', encoding='utf-8') as f_bat:
                if arguments:
                    f_bat.write('@echo off\nstart "" "{}" {}\n'.format(target, arguments))
                else:
                    f_bat.write('@echo off\nstart "" "{}"\n'.format(target))
            return True
        except Exception as e:
            logger.error("Kisayol olusturulamadi: %s", e)
            return False

    def create_desktop_shortcut(self):
        """Masaustu kisayolu olusturur."""
        try:
            import winreg
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
                desktop_path = winreg.QueryValueEx(key, "Desktop")[0]
                winreg.CloseKey(key)
            except Exception:
                pass

            shortcut_path = os.path.join(desktop_path, "AYEC Pro.lnk")
            target = os.path.abspath(sys.executable)
            arguments = '"{}"'.format(os.path.abspath(__file__)) if not getattr(sys, 'frozen', False) else ""
            icon_path = resource_path(os.path.join("assets", "app_icon.ico"))
            if not os.path.exists(icon_path):
                icon_path = resource_path(os.path.join("assets", "app_icon.png"))
            ok = self._create_shortcut_win32(shortcut_path, target, arguments, icon_path, "AYEC Pro Servis Yonetimi")
            if ok:
                logger.info("Masaustu kisayolu olusturuldu: %s", shortcut_path)
            return ok
        except Exception as e:
            logger.error("Masaustu kisayolu: %s", e)
            return False

    def create_start_menu_shortcut(self):
        """Windows Baslangic Menusu'ne AYEC Pro klasoru ve kisayolu ekler."""
        try:
            import winreg
            programs_path = os.path.join(
                os.environ.get("APPDATA", os.path.expanduser("~")),
                "Microsoft", "Windows", "Start Menu", "Programs")
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
                programs_path = winreg.QueryValueEx(key, "Programs")[0]
                winreg.CloseKey(key)
            except Exception:
                pass
            ayec_folder = os.path.join(programs_path, "AYEC Pro")
            os.makedirs(ayec_folder, exist_ok=True)
            shortcut_path = os.path.join(ayec_folder, "AYEC Pro.lnk")
            target = os.path.abspath(sys.executable)
            arguments = '"{}"'.format(os.path.abspath(__file__)) if not getattr(sys, 'frozen', False) else ""
            icon_path = resource_path(os.path.join("assets", "app_icon.ico"))
            if not os.path.exists(icon_path):
                icon_path = resource_path(os.path.join("assets", "app_icon.png"))
            ok = self._create_shortcut_win32(shortcut_path, target, arguments, icon_path, "AYEC Pro Servis Yonetimi")
            if ok:
                logger.info("Baslangic Menusu kisayolu: %s", shortcut_path)
            return ok
        except Exception as e:
            logger.error("Baslangic Menusu kisayolu: %s", e)
            return False

    def toggle_windows_startup(self, enabled):
        """Baslangic kaydini ac/kapat ve kullaniciya sonucu bildir."""
        if enabled:
            ok = self.add_to_windows_startup()
            if ok:
                self.show_notification("Program Windows baslangicinaa eklendi. Her acilisda otomatik calisacak.", "success")
            else:
                self.show_notification("Baslangiaca eklenemedi. Yonetici yetkisi gerekebilir.", "error")
        else:
            ok = self.remove_from_windows_startup()
            if ok:
                self.show_notification("Program Windows baslangictan cikarildi.", "info")
            else:
                self.show_notification("Baslangictan cikarilamadi.", "error")
        return ok

"""

path = r"C:\Users\Admin\Desktop\AYEC Pro\ModernDesktopApp.py"
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = "    def is_setup_completed(self):\n"
idx = content.find(target)
if idx >= 0:
    content = content[:idx] + STARTUP_CODE + content[idx:]
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: Startup/shortcut functions injected")
else:
    print("FAILED: insert point not found")
