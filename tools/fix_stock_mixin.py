import sys

path = r"src\db\mixins\stock_mixin.py"
content = open(path, "rb").read()

bad_lines = (
    b"                    category,\r\n"
    b"                    price,\r\n"
    b"                    purchase_price,\r\n"
    b"                    currency,\r\n"
    b"                    desc,\r\n"
    b"                    min_stock,\r\n"
    b"                    code,\r\n"
    b"                    shelf,\r\n"
    b"                    photo_path,\r\n"
    b"                    oem_code,\r\n"
    b"                    equivalent_code,\r\n"
    b"                    compatible_models,\r\n"
)
marker_start = b"    ):\n"
marker_end = b'        """Parca bilgilerini guncelle."""\n'

bad = marker_start + bad_lines + marker_end
good = marker_start + marker_end

if bad in content:
    new_content = content.replace(bad, good, 1)
    open(path, "wb").write(new_content)
    print("FIXED OK")
else:
    print("Pattern not found, checking near update_part...")
    idx = content.find(b"def update_part(")
    print(repr(content[idx:idx+200]))
