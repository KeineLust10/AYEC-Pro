import os
import json
import importlib.util

fp = os.path.join(os.getcwd(), 'src', 'utils', 'path_helper.py')
spec = importlib.util.spec_from_file_location('path_helper', fp)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
PathHelper = mod.PathHelper

pref = {'preferred': 'appdata'}
path = os.path.join(PathHelper.get_app_data_dir(), 'db_preference.json')
with open(path, 'w', encoding='utf-8') as f:
    json.dump(pref, f)
print('Wrote preference to', path)
