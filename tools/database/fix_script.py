import sys

path = r'c:\Users\engin\Desktop\yapay zeka\AYEC Pro\src\ui\dialogs\bank_detail_transactions_mixin.py'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
in_func = False
for line in lines:
    if line.startswith('    def _build_tx_query'):
        in_func = True
    
    if in_func:
        line = line.replace('(bank_account_id =  OR related_account_id = )', '(bank_account_id = ? OR related_account_id = ?)')
        line = line.replace('(description LIKE  OR CAST(id AS TEXT) LIKE )', '(description LIKE ? OR CAST(id AS TEXT) LIKE ?)')
        line = line.replace('"type = "', '"type = ?"')
        line = line.replace('"payment_method LIKE "', '"payment_method LIKE ?"')
        line = line.replace('"description LIKE "', '"description LIKE ?"')
        line = line.replace('(category LIKE  OR description LIKE )', '(category LIKE ? OR description LIKE ?)')
        line = line.replace('"date >=  AND date <= "', '"date >= ? AND date <= ?"')
        line = line.replace('"ABS(amount) >= "', '"ABS(amount) >= ?"')
        line = line.replace('"ABS(amount) <= "', '"ABS(amount) <= ?"')
        line = line.replace('" LIMIT  OFFSET "', '" LIMIT ? OFFSET ?"')
        if 'def _load_transactions' in line:
            in_func = False
            
    new_lines.append(line)

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

# Fix bare exceptions in stock_page.py
path_stock = r'c:\Users\engin\Desktop\yapay zeka\AYEC Pro\src\ui\pages\stock_page.py'
with open(path_stock, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("except:\n", "except Exception as e:\n")
content = content.replace("except: pass", "except Exception as e: pass")
content = content.replace("except: return ", "except Exception as e: return ")
content = content.replace("except: continue", "except Exception as e: continue")

with open(path_stock, 'w', encoding='utf-8') as f:
    f.write(content)

# Fix bare exceptions in services_page.py
path_services = r'c:\Users\engin\Desktop\yapay zeka\AYEC Pro\src\ui\pages\services_page.py'
with open(path_services, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("except:\n", "except Exception as e:\n")
content = content.replace("except: pass", "except Exception as e: pass")
content = content.replace("except: return ", "except Exception as e: return ")

with open(path_services, 'w', encoding='utf-8') as f:
    f.write(content)

print('Repaired SQL placeholders and bare exceptions!')
