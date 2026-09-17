# -*- coding: utf-8 -*-

import pyinstaller_versionfile
import sys
import os

def create_version_file(version, outfile="file_version_info.txt"):
    # Split version "1.2.3" -> (1, 2, 3, 0)
    parts = version.split('.')
    while len(parts) < 4:
        parts.append('0')
    
    ver_tuple = tuple(map(int, parts[:4]))
    
    pyinstaller_versionfile.create_versionfile(
        output_file=outfile,
        version=version,
        company_name="AYEC Pro",
        file_description="AYEC Pro Yönetim Sistemi",
        internal_name="AYECPro",
        legal_copyright="© 2026 AYEC Pro. Tüm hakları saklıdır.",
        original_filename="AYECPro_App.exe",
        product_name="AYEC Pro"
    )
    print(f"Created version resource file: {outfile} ({version})")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Read from version.txt if not provided
        try:
            with open("version.txt", "r") as f:
                version = f.read().strip()
        except:
            version = "1.0.0.0"
    else:
        version = sys.argv[1]
        
    create_version_file(version)
