# -*- coding: utf-8 -*-
"""
AYEC Pro - Nuitka Machine Language Compiler Script
Compiles python scripts to native C++ binary and builds Setup installer.
"""

import os
import sys
import shutil
import subprocess
import sysconfig
from importlib import metadata
from pathlib import Path

from packaging.requirements import Requirement

DYNAMIC_PAGE_MODULES = (
    "src.ui.pages.dashboard_page",
    "src.ui.pages.automotive_stock_page",
    "src.ui.pages.personnel_page",
    "src.ui.pages.appointments_page",
    "src.ui.pages.accounting_page",
    "src.ui.pages.finance.bank_page",
    "src.ui.pages.finance.check_note_page",
    "src.ui.pages.invoice_page",
    "src.ui.pages.settings_page",
    "src.ui.pages.support_page",
    "src.ui.pages.audit_log_page",
    "src.ui.pages.backup_page",
    "src.ui.pages.user_manual_page",
    "src.ui.pages.services_page",
    "src.ui.pages.service_board_page",
    "src.ui.pages.technical_stock_page",
    "src.ui.pages.stock_locations_page",
    "src.ui.pages.brands_page",
    "src.ui.pages.product_groups_page",
    "src.ui.pages.report_templates_page",
    "src.ui.pages.external_tracking_page",
    "src.ui.pages.loaner_devices_page",
    "src.ui.pages.job_service_tracking_page",
    "src.ui.pages.vehicle_maintenance_page",
    "src.ui.pages.sales_hub_page",
    "src.ui.pages.customers_page",
    "src.ui.pages.customers_page_parts",
    "src.ui.pages.contracts_page",
    "src.ui.pages.reminders_page",
    "src.ui.pages.knowledge_base_page",
    "src.ui.pages.ai_assistant_page",
    "src.ui.pages.announcements_page",
    "src.ui.pages.field_service_page",
    "src.ui.pages.project_management.projects_page",
    "src.ui.pages.project_management.project_archive_page",
    "src.ui.pages.mobile_guide_page",
    "src.ui.pages.offer_pages",
)

RUNTIME_PACKAGE_ROOTS = (
    "bcrypt",
    "certifi",
    "cryptography",
    "cv2",
    "dateutil",
    "easyocr",
    "edge_tts",
    "dotenv",
    "fitz",
    "fastapi",
    "google",
    "numpy",
    "openpyxl",
    "paddle",
    "paddleocr",
    "pandas",
    "passlib",
    "PIL",
    "pdf2docx",
    "pdfminer",
    "pdfplumber",
    "pymupdf",
    "pytesseract",
    "pytz",
    "pyaudio",
    "pyaudiowpatch",
    "pyttsx3",
    "pydantic",
    "qrcode",
    "reportlab",
    "requests",
    "scipy",
    "skimage",
    "speech_recognition",
    "sqlalchemy",
    "torch",
    "torchvision",
    "torchgen",
    "tzdata",
    "urllib3",
    "uvicorn",
)

COMPILED_RUNTIME_DISTRIBUTIONS = set()
RUNTIME_DISTRIBUTIONS = ("protobuf",)

def print_banner():
    print("\n" + "="*70)
    print("   AYEC Pro - NUITKA MAKINE DILI DERLEME SISTEMI")
    print("="*70 + "\n")

def collect_and_copy_runtime_resources(dest_dir):
    print("[*] Runtime resources are being copied...")

    for folder in ["assets"]:
        if os.path.exists(folder):
            shutil.copytree(folder, os.path.join(dest_dir, folder), dirs_exist_ok=True)
            print(f"  [OK] {folder} copied")

    for f in ["version.txt"]:
        if os.path.exists(f):
            shutil.copy2(f, os.path.join(dest_dir, f))
            print(f"  [OK] {f} copied")

    plugin_source = "plugins"
    if os.path.isdir(plugin_source):
        shutil.copytree(
            plugin_source,
            os.path.join(dest_dir, plugin_source),
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.bak"),
        )
        print("  [OK] plugin discovery source copied")

    for folder in ["src", "backend", "core", "interfaces"]:
        if os.path.exists(folder):
            for root, dirs, files in os.walk(folder):
                if "__pycache__" in dirs:
                    dirs.remove("__pycache__")
                for file in files:
                    if not file.endswith(".py") and not file.endswith(".pyc") and not file.endswith(".bak"):
                        src_file = os.path.join(root, file)
                        rel_dir = os.path.relpath(root, os.path.dirname(folder))
                        dest_folder = os.path.join(dest_dir, rel_dir)
                        os.makedirs(dest_folder, exist_ok=True)
                        shutil.copy2(src_file, os.path.join(dest_folder, file))
                        print(f"  [OK] {src_file} -> {os.path.join(rel_dir, file)}")


def copy_pymupdf_runtime(dest_dir):
    site_packages = sysconfig.get_paths()["purelib"]
    for package_name in ("pymupdf", "fitz"):
        source = os.path.join(site_packages, package_name)
        if os.path.isdir(source):
            shutil.copytree(
                source,
                os.path.join(dest_dir, package_name),
                dirs_exist_ok=True,
            )

    for entry in os.listdir(site_packages):
        if entry.lower().startswith("pymupdf-") and entry.endswith(".dist-info"):
            shutil.copytree(
                os.path.join(site_packages, entry),
                os.path.join(dest_dir, entry),
                dirs_exist_ok=True,
            )

    python3_dll = os.path.join(sys.base_prefix, "python3.dll")
    if os.path.isfile(python3_dll):
        shutil.copy2(python3_dll, os.path.join(dest_dir, "python3.dll"))
        print("  [OK] PyMuPDF binary runtime copied")


def copy_tesseract_runtime(dest_dir):
    candidates = (
        r"C:\Program Files\Tesseract-OCR",
        r"C:\Program Files (x86)\Tesseract-OCR",
    )
    for source in candidates:
        if os.path.isfile(os.path.join(source, "tesseract.exe")):
            shutil.copytree(
                source,
                os.path.join(dest_dir, "Tesseract-OCR"),
                dirs_exist_ok=True,
            )
            print("  [OK] Tesseract OCR engine copied")
            return
    print("  [WARN] Tesseract OCR engine was not found")


def copy_runtime_package_closure(dest_dir):
    site_packages = os.path.abspath(sysconfig.get_paths()["purelib"])
    package_map = metadata.packages_distributions()
    pending = list(RUNTIME_DISTRIBUTIONS)
    requirements_path = Path("requirements.txt")
    if requirements_path.is_file():
        requirements_bytes = requirements_path.read_bytes()
        requirements_encoding = "utf-16" if requirements_bytes.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
        for raw_line in requirements_bytes.decode(requirements_encoding).splitlines():
            requirement_text = raw_line.strip()
            if not requirement_text or requirement_text.startswith("#"):
                continue
            try:
                requirement = Requirement(requirement_text)
                if requirement.marker and not requirement.marker.evaluate():
                    continue
                pending.append(requirement.name)
            except Exception:
                print(f"  [WARN] Invalid requirement skipped: {requirement_text}")
    for package_name in RUNTIME_PACKAGE_ROOTS:
        pending.extend(package_map.get(package_name, []))

    copied = set()
    while pending:
        distribution_name = pending.pop()
        normalized_name = distribution_name.lower().replace("_", "-")
        if normalized_name in copied or normalized_name in COMPILED_RUNTIME_DISTRIBUTIONS:
            continue
        try:
            distribution = metadata.distribution(distribution_name)
        except metadata.PackageNotFoundError:
            print(f"  [WARN] Runtime distribution not found: {distribution_name}")
            continue

        copied.add(normalized_name)
        for relative_path in distribution.files or ():
            source = os.path.join(site_packages, str(relative_path))
            target = os.path.join(dest_dir, str(relative_path))
            if os.path.isfile(source):
                os.makedirs(os.path.dirname(target), exist_ok=True)
                shutil.copy2(source, target)

        for requirement_text in distribution.requires or ():
            try:
                requirement = Requirement(requirement_text)
                if requirement.marker and not requirement.marker.evaluate():
                    continue
                pending.append(requirement.name)
            except Exception:
                continue

    print(f"  [OK] Runtime dependency closure copied: {len(copied)} distributions")


def main():
    print_banner()
    base_dir = os.getcwd()
    
    python_path = os.path.join(base_dir, ".venv_active", "Scripts", "python.exe")
    if not os.path.exists(python_path):
        python_path = sys.executable

    dependency_check = subprocess.run(
        [python_path, "-c", "import bcrypt; print(bcrypt.__version__)"],
        capture_output=True,
        text=True,
    )
    if dependency_check.returncode != 0:
        print("[ERROR] bcrypt bulunamadi. Once requirements.txt yukleyin.")
        return 1
    print(f"[OK] bcrypt {dependency_check.stdout.strip()} bulundu")
        
    # Nuitka compilation
    print("[1/3] Nuitka ile Makine Diline Derleme Basliyor...")
    print("      (C++ cevirisi ve derleme yapildigi icin birkaç dakika surebilir)\n")
    
    # Clean previous nuitka build
    nuitka_out = os.path.join(base_dir, "nuitka_build")
    if os.path.exists(nuitka_out):
        shutil.rmtree(nuitka_out)
        
    cmd = [
        python_path, "-m", "nuitka",
        "--standalone",
        "--low-memory",
        "--jobs=4",
        "--follow-stdlib",
        "--no-deployment-flag=excluded-module-usage",
        "--module-parameter=torch-disable-jit=yes",
        "--nofollow-import-to=pymupdf",
        "--nofollow-import-to=fitz",
        "--nofollow-import-to=cv2",
        "--nofollow-import-to=easyocr",
        "--nofollow-import-to=edge_tts",
        "--nofollow-import-to=paddle",
        "--nofollow-import-to=paddleocr",
        "--nofollow-import-to=pdf2docx",
        "--nofollow-import-to=pdfminer",
        "--nofollow-import-to=pdfplumber",
        "--nofollow-import-to=pytesseract",
        "--nofollow-import-to=pyaudio",
        "--nofollow-import-to=pyaudiowpatch",
        "--nofollow-import-to=pyttsx3",
        "--nofollow-import-to=scipy",
        "--nofollow-import-to=skimage",
        "--nofollow-import-to=speech_recognition",
        "--nofollow-import-to=torch",
        "--nofollow-import-to=torchvision",
        "--nofollow-import-to=torchgen",
        "--nofollow-import-to=certifi",
        "--nofollow-import-to=dateutil",
        "--nofollow-import-to=numpy",
        "--nofollow-import-to=openpyxl",
        "--nofollow-import-to=pandas",
        "--nofollow-import-to=PIL",
        "--nofollow-import-to=pytz",
        "--nofollow-import-to=reportlab",
        "--nofollow-import-to=requests",
        "--nofollow-import-to=six",
        "--nofollow-import-to=tzdata",
        "--nofollow-import-to=urllib3",
        "--enable-plugin=pyqt6",
        "--assume-yes-for-downloads",
        "--windows-console-mode=disable",
        "--windows-icon-from-ico=assets/app_icon.ico",
        "--include-data-dir=assets=assets",
        "--include-data-file=version.txt=version.txt",
        "--include-module=cProfile",
        "--include-module=doctest",
        "--include-module=profile",
        "--include-module=pstats",
        "--include-module=pydoc",
        "--include-module=site",
        "--include-module=aifc",
        "--include-module=audioop",
        "--include-module=chunk",
        "--include-module=sunau",
        "--include-module=wave",
        "--include-package=unittest",
        "--include-package=google.protobuf",
        "--include-package=src",
        "--include-package=plugins",
        "--include-package=core",
        "--include-package=interfaces",
        "--include-package=backend",
        "--include-package=src.ui.pages.finance",
        "--include-package=src.ui.pages.project_management",
        "--output-filename=AYECPro.Core.exe",
        "--output-dir=nuitka_build",
        "Main.py"
    ]
    cmd[3:3] = [f"--include-module={module}" for module in DYNAMIC_PAGE_MODULES]
    
    try:
        # Run Nuitka
        result = subprocess.run(cmd, check=True)
        print("\n[OK] [2/3] Nuitka derlemesi tamamlandi.")
    except Exception as e:
        print(f"\n[HATA] Nuitka derleme hatasi: {e}")
        return False
        
    # Copy Assets and build professional bin/ layout
    dist_dir = os.path.join(nuitka_out, "Main.dist")
    final_dist = os.path.join(base_dir, "dist", "AYECPro_App")
    final_bin = os.path.join(final_dist, "bin")

    if os.path.exists(dist_dir):
        if os.path.exists(final_dist):
            shutil.rmtree(final_dist)
        os.makedirs(final_bin, exist_ok=True)

        # Move Nuitka compiled C++ runtime to dist/AYECPro_App/bin
        shutil.copytree(dist_dir, final_bin, dirs_exist_ok=True)
        print("\n  [OK] C++ Makine dili ikilileri ve kütüphaneler bin/ altina yerlestirildi.")

        collect_and_copy_runtime_resources(final_bin)
        copy_pymupdf_runtime(final_bin)
        copy_tesseract_runtime(final_bin)
        copy_runtime_package_closure(final_bin)

        # Build clean Launcher (AYECPro.exe) in root folder
        try:
            print("[*] Temiz kök dizin baslaticisi (AYECPro.exe) derleniyor...")
            launcher_src = os.path.join(base_dir, "tools", "setup", "launcher.py")
            cmd_launcher = [
                python_path, "-m", "nuitka",
                "--onefile",
                "--windows-console-mode=disable",
                "--windows-icon-from-ico=assets/app_icon.ico",
                "--output-filename=AYECPro.exe",
                f"--output-dir={final_dist}",
                launcher_src
            ]
            subprocess.run(cmd_launcher, check=True)
            for temporary_name in ("launcher.build", "launcher.dist", "launcher.onefile-build"):
                temporary_path = os.path.join(final_dist, temporary_name)
                if os.path.isdir(temporary_path):
                    shutil.rmtree(temporary_path)
            print("  [OK] AYECPro.exe temiz baslaticisi basariyla derlendi.")
        except Exception as l_err:
            print(f"  [UYARI] Baslatici derlenemedi, varsayilan baslatici kopyalaniyor: {l_err}")
            # Fallback: copy a simple batch/script launcher if onefile fails
            with open(os.path.join(final_dist, "AYECPro.bat"), "w", encoding="utf-8") as f:
                f.write('@echo off\nstart "" "%~dp0bin\\AYECPro.Core.exe" %*\n')

        print("\n  [OK] Derlenen profesyonel paket dist/AYECPro_App altinda hazir.")
    else:
        print("[HATA] Nuitka cikti klasoru bulunamadi!")
        return False
        
    # Compile Installer
    print("\n[3/3] Kurulum Dosyasi (Setup) Olusturuluyor...")
    inno_path = r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    if os.path.exists(inno_path):
        if os.path.exists("AYECPro_Modern_Setup.iss"):
            try:
                subprocess.run([inno_path, "AYECPro_Modern_Setup.iss"], check=True)
                print("\n[OK] SETUP OLUSTURMA BASARIYLA TAMAMLANDI!")
                if os.path.exists("Setup_Output"):
                    setup_files = sorted(
                        (Path("Setup_Output") / name for name in os.listdir("Setup_Output") if name.endswith(".exe")),
                        key=lambda path: path.stat().st_mtime,
                        reverse=True,
                    )
                    if setup_files:
                        print(f"  Kurulum Dosyasi: {setup_files[0]}")
                return True
            except Exception as e:
                print(f"[HATA] Inno Setup derleme hatasi: {e}")
                return False
        else:
            print("[HATA] AYECPro_Modern_Setup.iss bulunamadi!")
            return False
    else:
        print("[UYARI] Inno Setup bulunamadi. Setup derlemesi atlandi.")
        return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
