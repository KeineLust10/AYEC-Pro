"""Move redundant DB files from workspace root into backups/deleted_<timestamp>.

This script will:
- Identify any .db files in the project root.
- Exclude the AppData target DB (ayecpro.db in AppData) from deletion.
- Move redundant DB files into Setup_Files/backups/deleted_<timestamp>/ for safe recovery.

This avoids permanent deletion while making the AppData DB the single active DB.
"""

import os
import shutil
from datetime import datetime

ROOT = os.path.abspath(os.getcwd())
APPDATA = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~\\AppData\\Local')), 'AYEC Pro')
TARGET_NAME = 'ayecpro.db'
TARGET_PATH = os.path.join(APPDATA, TARGET_NAME)

BACKUP_DIR = os.path.join(ROOT, 'Setup_Files', 'backups')
os.makedirs(BACKUP_DIR, exist_ok=True)

TS = datetime.now().strftime('%Y%m%d_%H%M%S')
DELETED_DIR = os.path.join(BACKUP_DIR, f'deleted_{TS}')
os.makedirs(DELETED_DIR, exist_ok=True)

moved = []
skipped = []
for name in os.listdir(ROOT):
    if not name.lower().endswith('.db'):
        continue
    path = os.path.join(ROOT, name)
    # skip the target AppData DB if someone put a copy in AppData and not root
    # we want to remove root copies (keep AppData target)
    # If the root file is the same as target path, skip
    if os.path.abspath(path) == os.path.abspath(TARGET_PATH):
        skipped.append(path)
        continue
    # Move the file into deleted backups
    try:
        dest = os.path.join(DELETED_DIR, name)
        shutil.move(path, dest)
        moved.append((path, dest))
    except Exception as e:
        print(f'Failed to move {path}: {e}')

print('Moved files:')
for s,d in moved:
    print(' -', s, '->', d)
print('\nSkipped (kept):')
for s in skipped:
    print(' -', s)
print('\nBackups/Deleted stored in:', DELETED_DIR)
