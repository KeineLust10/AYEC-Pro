"""
Fix non-ASCII characters in stock_mixin.py that cause SyntaxError.
Specifically replaces Turkish characters in docstrings.
"""
content = open(r"src\db\mixins\stock_mixin.py", "rb").read()

# Fix the problematic docstring lines (use_part function)
bad = (
    b'        """Par\xc3\xa7a kullan  -  stok d\xc3\xbc\xc5\x9fer, used_parts\'a kay\xc4\xb1t eklenir.\r\n'
    b"        Not: Par\xc3\xa7a maliyeti zaten 'Stok Al\xc4\xb1m\xc4\xb1' Gider kayd\xc4\xb1 ile muhasebele\xc5\x9ftirilmi\xc5\x9ftir.\r\n"
    b'        Gelir kayd\xc4\xb1, cihaz teslim edildi\xc4\x9finde olu\xc5\x9fturulur."""\r\n'
)
good = (
    b'        """Parca kullan - stok dusum, used_parts kaydedilir.\r\n'
    b"        Not: Parca maliyeti zaten 'Stok Alimi' Gider kaydi ile muhasebeleştirilmistir.\r\n"
    b'        Gelir kaydi, cihaz teslim edildiginde olusturulur."""\r\n'
)
if bad in content:
    content = content.replace(bad, good, 1)
    open(r"src\db\mixins\stock_mixin.py", "wb").write(content)
    print("FIXED docstring")
else:
    print("Pattern not found, trying partial replacement...")
    # Try line by line
    old1 = b'        """Par\xc3\xa7a kullan  -  stok d\xc3\xbc\xc5\x9fer, used_parts\'a kay\xc4\xb1t eklenir.\r\n'
    new1 = b'        """Parca kullan - stok dusum, used_parts kaydedilir.\r\n'
    if old1 in content:
        content = content.replace(old1, new1, 1)
        print("Fixed line 1")
    old2 = b"        Not: Par\xc3\xa7a maliyeti zaten 'Stok Al\xc4\xb1m\xc4\xb1' Gider kayd\xc4\xb1 ile muhasebele\xc5\x9ftirilmi\xc5\x9ftir.\r\n"
    new2 = b"        Not: Parca maliyeti zaten Gider kaydi ile muhasebeleştirilmistir.\r\n"
    if old2 in content:
        content = content.replace(old2, new2, 1)
        print("Fixed line 2")
    old3 = b'        Gelir kayd\xc4\xb1, cihaz teslim edildi\xc4\x9finde olu\xc5\x9fturulur."""\r\n'
    new3 = b'        Gelir kaydi, cihaz teslim edildiginde olusturulur."""\r\n'
    if old3 in content:
        content = content.replace(old3, new3, 1)
        print("Fixed line 3")
    open(r"src\db\mixins\stock_mixin.py", "wb").write(content)
    print("Saved")
