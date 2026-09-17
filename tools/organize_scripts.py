#!/usr/bin/env python3
"""
Script to organize root-level utility scripts into appropriate directories.
This is a one-time organization tool.
"""

import os
import shutil
from pathlib import Path

# Define organization rules
ORGANIZATION_RULES = {
    'tools/database/': [
        'fix_*.py',
        'migrate_*.py',
        'repair_*.py',
        'db_*.py',
        'check_*.py',
        'verify_*.py',
        'dump_*.py',
        'normalize_*.py',
        'reset_*.py',
        'clean_*.py',
        'wipe_*.py',
        'clear_*.py',
        'deep_*.py',
        'audit_*.py',
        'upgrade_*.py',
        'revert_*.py',
        'replace_*.py',
        'analyze_*.py',
        'create_currency_*.py',
        'add_security_*.py',
        'cleanup_*.py',
        'sanity_*.py',
        'table_*.py',
        'update_auth_*.py',
        'init_db_*.py',
    ],
    'tools/debug/': [
        'debug_*.py',
        'find_*.py',
        'test_*.py',
        'diag_*.py',
        'list_*.py',
    ],
    'tools/setup/': [
        'setup_*.py',
        'generate_*.py',
        'keygen.py',
        'LicenseGenerator.py',
        'ModernSetup.py',
        'sunucu_hazirla.py',
        'inject_*.py',
        'add_startup_*.py',
        'quick_build_*.py',
    ],
    'tools/cleanup/': [
        'ForceCleanup.py',
        'nuclear_reset.py',
        'total_wipe.py',
        'kokten_cozum.py',
        'final_restore.py',
    ],
    'tools/build/': [
        'build_*.py',
        'convert_*.py',
        'compile_*.py',
    ],
}

# Files to keep in root (essential entry points)
KEEP_IN_ROOT = [
    'Main.py',
    'requirements.txt',
    'requirements-dev.txt',
    'setup.py',
    'pyproject.toml',
    'README.md',
    'LICENSE',
    '.gitignore',
]

def organize_scripts():
    """Organize scripts according to rules."""
    root_dir = Path(__file__).parent.parent
    print(f"Organizing scripts in: {root_dir}")

    # Create directories
    for directory in ORGANIZATION_RULES.keys():
        (root_dir / directory).mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {directory}")

    moved_count = 0
    skipped_count = 0

    # Get all Python files in root
    py_files = [f for f in root_dir.glob('*.py') if f.is_file()]

    for file_path in py_files:
        file_name = file_path.name

        # Skip files that should stay in root
        if file_name in KEEP_IN_ROOT:
            print(f"  [KEEP] {file_name}")
            skipped_count += 1
            continue

        # Find matching category
        moved = False
        for target_dir, patterns in ORGANIZATION_RULES.items():
            for pattern in patterns:
                if match_pattern(file_name, pattern):
                    target_path = root_dir / target_dir / file_name
                    if target_path.exists():
                        print(f"  [SKIP] {file_name} (already exists in {target_dir})")
                        skipped_count += 1
                    else:
                        shutil.move(str(file_path), str(target_path))
                        print(f"  [MOVE] {file_name} -> {target_dir}")
                        moved_count += 1
                    moved = True
                    break
            if moved:
                break

        if not moved:
            print(f"  [?] {file_name} (no category matched)")
            skipped_count += 1

    print(f"\nSummary:")
    print(f"  Moved: {moved_count}")
    print(f"  Skipped: {skipped_count}")
    print(f"  Total: {moved_count + skipped_count}")

def match_pattern(filename, pattern):
    """Simple glob-like pattern matching."""
    if pattern.endswith('*.py'):
        prefix = pattern[:-5]  # Remove '*.py'
        return filename.startswith(prefix) and filename.endswith('.py')
    else:
        return filename == pattern

if __name__ == '__main__':
    organize_scripts()
