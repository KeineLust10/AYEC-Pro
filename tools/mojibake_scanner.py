#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.absolute()
TARGET_EXTENSIONS = {'.py', '.json', '.txt', '.html', '.css', '.js', '.md', '.yml', '.yaml'}
EXCLUDE_DIRS = {'.venv_ai', '__pycache__', '.git', '.claude', 'backups', 'dist', 'build', 'node_modules'}

MOJIBAKE_PATTERNS = {
    'Ã§': 'ç', 'Ã¶': 'ö', 'Ã¼': 'ü', 'ÅŸ': 'ş', 'Ä±': 'ı', 'Ä°': 'İ',
    'Ã‡': 'Ç', 'Ã–': 'Ö', 'Ãœ': 'Ü', 'Åž': 'Ş', 'ÄŸ': 'ğ', 'Äž': 'Ğ',
}

def should_process(path):
    s = str(path)
    for ex in EXCLUDE_DIRS:
        if ex in s: return False
    return path.suffix.lower() in TARGET_EXTENSIONS

def fix_text(text):
    fixed, changes = text, []
    for bad, good in MOJIBAKE_PATTERNS.items():
        if bad in fixed:
            cnt = fixed.count(bad)
            fixed = fixed.replace(bad, good)
            changes.append(bad + " -> " + good + " (" + str(cnt) + "x)")
    return fixed, changes

def process(fp, dry=True):
    try:
        with open(fp, 'r', encoding='utf-8', errors='replace') as f:
            orig = f.read()
        fixed, chg = fix_text(orig)
        if not chg: return None
        res = {'file': str(fp.relative_to(PROJECT_ROOT)), 'changes': chg}
        if not dry:
            with open(fp, 'w', encoding='utf-8') as f: f.write(fixed)
            res['fixed'] = True
        return res
    except Exception as e:
        return {'file': str(fp.relative_to(PROJECT_ROOT)), 'error': str(e)}

def scan(dry=True):
    results, n, bad = [], 0, 0
    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for fn in files:
            fp = Path(root) / fn
            if not should_process(fp): continue
            n += 1
            r = process(fp, dry)
            if r: bad += 1; results.append(r)
    print("Dosya: " + str(n) + ", Sorunlu: " + str(bad))
    for r in results:
        print("\n" + r['file'])
        if 'error' in r: print("  HATA: " + r['error'])
        else:
            for c in r['changes']: print('  ' + c)
            if r.get('fixed'): print('  DUZELTILDI')
    return results

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--fix', action='store_true')
    a = p.parse_args()
    scan(dry=not a.fix)
