"""Restore missing parts of use_part function in stock_mixin.py"""

content = open(r"src\db\mixins\stock_mixin.py", "rb").read()

sig_end = b"        **kwargs,\n    ):\n"
if sig_end not in content:
    print("ERROR: signature not found")
    exit(1)

idx = content.find(sig_end) + len(sig_end)

# Missing preamble that should appear right after the function signature
preamble = (
    b'        """Parca kullan - stok dusum, used_parts kaydi eklenir."""\n'
    b"        try:\n"
    b"            # Mevcut stoku kontrol et\n"
    b"            self.cursor.execute(\n"
    b"                \"SELECT name, stock, price, purchase_price, COALESCE(currency, 'TRY') FROM parts WHERE id=?\",\n"
    b"                (part_id,),\n"
    b"            )\n"
    b"            result = self.cursor.fetchone()\n"
    b"            if not result:\n"
    b"                return False\n"
    b"\n"
    b"            part_name = result[0] or f\"Parca #{part_id}\"\n"
    b"            current_stock = float(result[1] or 0)\n"
)

# What actually comes after the signature currently
actual_next = content[idx:idx+50]
print("After signature:", repr(actual_next))

content = content[:idx] + preamble + content[idx:]
open(r"src\db\mixins\stock_mixin.py", "wb").write(content)
print("Inserted preamble")
