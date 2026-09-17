import os
import json
import re
import sys
import shutil
import subprocess
from datetime import datetime
try:
    from scripts.create_version_info import create_version_file
except ImportError:
    # If running from root
    sys.path.append(os.path.join(os.getcwd(), 'scripts'))
    from create_version_info import create_version_file

class ReleaseManager:
    def __init__(self):
        self.root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.version_file = os.path.join(self.root_dir, "version.txt")
        self.iss_file = os.path.join(self.root_dir, "AYECPro_Modern_Setup.iss")
        self.dist_dir = os.path.join(self.root_dir, "dist")
        self.output_dir = os.path.join(self.root_dir, "Setup_Output")
        
    def get_current_version(self):
        if os.path.exists(self.version_file):
            with open(self.version_file, "r") as f:
                return f.read().strip()
        return "0.0.0"

    def bump_version(self, type="patch"):
        current = self.get_current_version()
        major, minor, patch = map(int, current.split("."))
        
        if type == "major":
            major += 1
            minor = 0
            patch = 0
        elif type == "minor":
            minor += 1
            patch = 0
        else:
            patch += 1
            
        new_version = f"{major}.{minor}.{patch}"
        print(f"Bumping version: {current} -> {new_version}")
        
        # Update version.txt
        with open(self.version_file, "w") as f:
            f.write(new_version)
            
        # Update ISS file
        self.update_iss_version(new_version)
        
        return new_version

    def update_iss_version(self, version):
        with open(self.iss_file, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Replace MyAppVersion "..."
        new_content = re.sub(r'#define MyAppVersion ".*?"', f'#define MyAppVersion "{version}"', content)
        
        with open(self.iss_file, "w", encoding="utf-8") as f:
            f.write(new_content)

    def build_project(self):
        # Generate version info file for PyInstaller
        current_ver = self.get_current_version()
        print(f"Generating version info for {current_ver}...")
        create_version_file(current_ver)
        
        print("Building project...")
        subprocess.run(["powershell", "-File", os.path.join(self.root_dir, "BuildAYECPro.ps1")], check=True)

    def create_release_artifacts(self, version, notes="", critical=False):
        print("Creating release artifacts...")
        release_dir = os.path.join(self.root_dir, "Releases", f"v{version}")
        os.makedirs(release_dir, exist_ok=True)
        
        # Copy Setup
        setup_file = f"AYECPro_Setup_v{version}.exe"
        src_setup = os.path.join(self.output_dir, setup_file)
        dst_setup = os.path.join(release_dir, setup_file)
        
        if os.path.exists(src_setup):
            shutil.copy2(src_setup, dst_setup)
            # Create generic name for easy linking
            shutil.copy2(src_setup, os.path.join(release_dir, "setup.exe"))
        else:
            print(f"Warning: Setup file not found: {src_setup}")

        # Create version.json
        manifest = {
            "version": version,
            "url": f"http://85.117.239.60:8000/Releases/v{version}/setup.exe",
            "release_date": datetime.now().isoformat(),
            "critical": critical,
            "notes": notes
        }
        
        with open(os.path.join(release_dir, "version.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=4)
            
        print(f"Release v{version} created at {release_dir}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python release_manager.py [major|minor|patch] [notes]")
        sys.exit(1)
        
    bump_type = sys.argv[1]
    notes = sys.argv[2] if len(sys.argv) > 2 else "Bug fixes and improvements"
    
    manager = ReleaseManager()
    new_ver = manager.bump_version(bump_type)
    manager.build_project()
    manager.create_release_artifacts(new_ver, notes)
